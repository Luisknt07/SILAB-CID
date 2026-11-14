"""Panel privado del centro: fragmentos para el modal y formularios sin Django admin."""
from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, router, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from apps.centros_id.identidades import identidad_de

from apps.centros_id.gestion_catalogo import CAMPOS_CENTRO, PANELES, REGISTROS
from .views import _centro


def url_gestion(centro, **parametros):
    return reverse('gestion_centro_id', args=[centro.slug]) + ('?' + urlencode(parametros) if parametros else '')


def _modelo(nombre):
    return apps.get_model('centros_id', nombre)


def _alcance(modelo):
    if modelo.__name__ == 'CentroID':
        return 'pk'
    if any(f.name == 'centro' for f in modelo._meta.fields):
        return 'centro'
    return {'EquipoCentro': 'componente__centro', 'HabilitacionEquipo': 'equipo__componente__centro',
            'HitoProyecto': 'proyecto__centro', 'RecursoCentro': 'carpeta__centro',
            'SesionAcompanamiento': 'solicitud__centro', 'TareaSolicitud': 'solicitud__centro',
            'PasoProceso': 'proceso__componente__centro', 'ProcesoArea': 'componente__centro'}[modelo.__name__]


def _consulta(modelo, centro):
    return modelo.objects.filter(**{_alcance(modelo): centro.pk})


def _revision(objeto):
    if not objeto.pk:
        return ''
    valores = [(f.name, str(getattr(objeto, f.attname))) for f in objeto._meta.concrete_fields]
    valores += [(f.name, list(getattr(objeto, f.name).order_by('pk').values_list('pk', flat=True)))
                for f in objeto._meta.many_to_many]
    return salted_hmac('centros_id.gestion.revision', repr(valores)).hexdigest()


class FormularioGestion(forms.ModelForm):
    revision = forms.CharField(required=False, widget=forms.HiddenInput)

    def _post_clean(self):
        if not self._errors:
            super()._post_clean()

    def _update_errors(self, errors):
        # Las reglas del dominio pueden nombrar campos que esta ficha no edita.
        if hasattr(errors, 'error_dict'):
            corregidos = {}
            for campo, detalles in errors.error_dict.items():
                corregidos.setdefault(campo if campo in self.fields else '__all__', []).extend(detalles)
            errors = ValidationError(corregidos)
        super()._update_errors(errors)


def _formulario(modelo, campos, centro, objeto, datos=None, archivos=None):
    from .gestion_opciones import acotar_relacion, preparar_opciones

    campos = list(campos)
    if hasattr(objeto, 'fuente_validacion'):
        campos.append('fuente_validacion')
    clase = forms.modelform_factory(modelo, form=FormularioGestion, fields=campos)
    formulario = clase(datos, archivos, instance=objeto, initial={'revision': _revision(objeto)})
    for nombre, campo in formulario.fields.items():
        if isinstance(campo, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
            acotar_relacion(campo, centro)
        if isinstance(campo, forms.DateTimeField):
            campo.widget = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
        elif isinstance(campo, forms.DateField):
            campo.widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
        elif isinstance(campo, forms.TimeField):
            campo.widget = forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
        elif isinstance(campo.widget, forms.Textarea):
            campo.widget.attrs['rows'] = 4
        campo.widget.attrs['class'] = 'cidg-control'
    if modelo.__name__ == 'SolicitudCentro':
        permitidos = (objeto.estado,) + objeto.SIGUIENTES[objeto.estado]
        formulario.fields['estado'].choices = [(v, t) for v, t in objeto.ESTADOS if v in permitidos]
        formulario.fields['motivo'] = forms.CharField(label='Detalle de la atención o motivo de la decisión',
            required=False, max_length=2000, widget=forms.Textarea(attrs={'rows': 3, 'class': 'cidg-control'}))
    # Mover un recurso/regla o una sesión existente entre expedientes rompe su trazabilidad.
    inmoviles = {'EquipoCentro': ('componente',), 'HabilitacionEquipo': ('equipo', 'usuario'),
        'HorarioRecurso': ('zona', 'equipo'), 'BloqueoRecurso': ('zona', 'equipo'),
        'SesionAcompanamiento': ('solicitud',), 'TareaSolicitud': ('solicitud',)}
    if objeto.pk:
        for nombre in inmoviles.get(modelo.__name__, ()):
            formulario.fields[nombre].disabled = True
    preparar_opciones(formulario, modelo, centro)
    return formulario


def _guardar(formulario, usuario):
    objeto = formulario.save(commit=False)
    if objeto.__class__.__name__ == 'HabilitacionEquipo':
        objeto.verificador = identidad_de(usuario)
    objeto.full_clean()
    if objeto.__class__.__name__ in ('SolicitudCentro', 'SesionAcompanamiento'):
        extras = {'motivo': formulario.cleaned_data.get('motivo', '')} if objeto.__class__.__name__ == 'SolicitudCentro' else {}
        objeto.save(actor=usuario, **extras)
    else:
        objeto.save()
    formulario.save_m2m()
    return objeto


def _fila(objeto, centro, panel, tipo):
    estado = next((str(getattr(objeto, 'get_' + c + '_display')()) for c in
                   ('estado', 'estado_acceso', 'estado_oferta', 'estado_documental', 'tipo')
                   if hasattr(objeto, 'get_' + c + '_display')), '')
    titulo = str(getattr(objeto, 'titulo', '') or getattr(objeto, 'nombre', '') or objeto)
    detalle = ''
    if tipo == 'solicitudes':
        detalle = f'{objeto.referencia} · {objeto.usuario} · {objeto.get_tipo_display()}'
    elif tipo == 'hitos':
        detalle = f'{objeto.proyecto} · {objeto.fecha_prevista:%d/%m/%Y}'
    elif tipo == 'horarios':
        detalle = f'{objeto.get_dia_display()} · {objeto.abre:%H:%M}–{objeto.cierra:%H:%M}'
    elif tipo in ('sesiones', 'bloqueos'):
        detalle = f'{timezone.localtime(objeto.inicio):%d/%m/%Y %H:%M}–{timezone.localtime(objeto.fin):%H:%M}'
    elif hasattr(objeto, 'componente') and objeto.componente_id:
        detalle = str(objeto.componente)
    return {'titulo': titulo, 'detalle': detalle, 'estado': estado,
            'url': url_gestion(centro, panel=panel, tipo=tipo, editar=objeto.pk)}


def _resumen(centro):
    from apps.centros_id.escenarios import filtro_contenido
    desde, hasta = timezone.now(), timezone.now() + timedelta(days=7)
    solicitudes = centro.solicitudes.all()
    activas = solicitudes.filter(estado__in=('recibida', 'evaluacion', 'aprobada', 'ejecucion'))
    sesiones = _consulta(_modelo('SesionAcompanamiento'), centro).filter(estado='programada', fin__gte=desde,
                                                                       inicio__lte=hasta).select_related('solicitud', 'responsable')
    reservas = solicitudes.filter(estado__in=('aprobada', 'ejecucion'), fin_reservado__gte=desde,
                                  inicio_reservado__lte=hasta).select_related('zona', 'equipo')
    agenda = [{'titulo': s.titulo, 'inicio': s.inicio_reservado, 'fin': s.fin_reservado,
               'detalle': str(s.zona or s.equipo or 'Atención del centro'),
               'url': url_gestion(centro, panel='solicitudes', tipo='solicitudes', editar=s.pk)} for s in reservas[:20]]
    agenda += [{'titulo': s.solicitud.titulo, 'inicio': s.inicio, 'fin': s.fin,
                'detalle': f'Acompañamiento · {s.responsable}',
                'url': url_gestion(centro, panel='agenda', tipo='sesiones', editar=s.pk)} for s in sesiones[:20]]
    tarjetas = [
        ('Por evaluar', solicitudes.filter(estado__in=('recibida', 'evaluacion')).count(), 'solicitudes', 'solicitudes'),
        ('Atenciones en curso', activas.filter(estado__in=('aprobada', 'ejecucion')).count(), 'solicitudes', 'solicitudes'),
        ('Entregas por cerrar', solicitudes.filter(estado='entregada').count(), 'solicitudes', 'solicitudes'),
        ('Proyectos en curso', centro.proyectos.filter(estado__in=('formulacion', 'ejecucion'),
                                                     **filtro_contenido(centro)).count(), 'investigacion', 'proyectos'),
    ]
    hitos = _consulta(_modelo('HitoProyecto'), centro).filter(estado='pendiente', fecha_prevista__lte=hasta.date(),
        proyecto__estado__in=('formulacion', 'ejecucion'), **{'proyecto__' + k: v for k, v in filtro_contenido(centro).items()})
    return {'tarjetas': [{'titulo': t, 'valor': v, 'url': url_gestion(centro, panel=p, tipo=k)} for t, v, p, k in tarjetas],
            'agenda': sorted(agenda, key=lambda a: a['inicio']),
            'hitos': [_fila(h, centro, 'investigacion', 'hitos') for h in hitos.select_related('proyecto').order_by('fecha_prevista')[:15]],
            'recibidas': [_fila(s, centro, 'solicitudes', 'solicitudes') for s in activas.select_related('usuario', 'centro').order_by('-creada')[:8]]}


@login_required
@never_cache
@csrf_protect
@require_http_methods(['GET', 'POST'])
def gestion_view(request, slug):
    centro = _centro(slug)
    if not centro.puede_gestionar(request.user):
        raise PermissionDenied
    panel = request.GET.get('panel', 'resumen')
    if panel not in {p[0] for p in PANELES}:
        raise Http404
    tipos = [(k, s[2]) for k, s in REGISTROS.items() if s[0] == panel]
    tipo = request.GET.get('tipo', tipos[0][0] if tipos else '')
    if tipo and tipo not in {t[0] for t in tipos}:
        raise Http404
    contexto = {'centro': centro, 'panel': panel, 'tipos': tipos, 'tipo': tipo,
        'panel_titulo': next(p[1] for p in PANELES if p[0] == panel),
        'paneles': [{'clave': k, 'titulo': t, 'icono': i, 'url': url_gestion(centro, panel=k)} for k, t, i in PANELES],
        'gestion_url': url_gestion(centro), 'volver_url': url_gestion(centro, panel=panel, tipo=tipo),
        'page_key': 'centros', 'page_title': 'Gestionar centro', 'ahora': timezone.now()}
    editar = request.GET.get('editar', '')
    if panel == 'configuracion' or editar:
        if panel == 'configuracion':
            modelo, campos = type(centro), CAMPOS_CENTRO
        elif tipo:
            modelo, campos = _modelo(REGISTROS[tipo][1]), REGISTROS[tipo][4].split()
        else:
            raise Http404
        if tipo == 'solicitudes' and editar == 'nuevo':
            raise Http404
        from .parametros import identificador
        editar_id = identificador(editar) if editar != 'nuevo' else None
        with transaction.atomic(using=router.db_for_write(type(centro))):
            if panel == 'configuracion':
                objeto = type(centro).objects.select_for_update().get(pk=centro.pk)
            elif editar == 'nuevo':
                objeto = modelo()
                if any(f.name == 'centro' for f in modelo._meta.fields):
                    objeto.centro = centro
                if hasattr(objeto, 'es_muestra'):
                    objeto.es_muestra = centro.en_escenario
                if tipo == 'habilitaciones':
                    objeto.verificador = identidad_de(request.user)
            else:
                objeto = get_object_or_404(_consulta(modelo, centro).select_for_update(), pk=editar_id)
            revision = _revision(objeto)
            formulario = _formulario(modelo, campos, centro, objeto,
                request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None)
            if editar == 'nuevo' and tipo == 'carpetas':
                formulario.initial.update({k: request.GET[k] for k in ('pestana', 'seccion') if k in request.GET})
            if request.method == 'POST':
                valido = formulario.is_valid()
                accion = request.POST.get('accion', 'guardar')
                if accion not in ('guardar', 'validar_identidad', 'validar_estado') or (accion != 'guardar' and panel != 'configuracion'):
                    formulario.add_error(None, 'Acción no reconocida.')
                    valido = False
                if objeto.pk and not constant_time_compare(request.POST.get('revision', ''), revision):
                    formulario.add_error(None, 'Este registro cambió mientras lo editabas. Vuelve a abrirlo antes de guardar.')
                    valido = False
                if valido:
                    try:
                        # Savepoint: una validación tardía no deja guardados parciales.
                        with transaction.atomic(using=router.db_for_write(type(centro))):
                            objeto = _guardar(formulario, request.user)
                            if accion != 'guardar':
                                getattr(objeto, accion)(request.user)
                    except IntegrityError:
                        formulario.add_error(None, 'No se pudo guardar porque otro registro cambió. Actualiza la lista y revisa los datos.')
                    except ValidationError as error:
                        formulario.add_error(None, ' '.join(error.messages))
                    else:
                        messages.success(request, 'Cambios guardados.')
                        parametros = {'panel': panel, 'tipo': tipo, 'editar': objeto.pk}
                        if request.GET.get('fragment') == '1':
                            parametros['fragment'] = 1
                        return redirect(url_gestion(centro, **parametros))
            contexto.update(formulario=formulario, objeto=objeto, revision=revision,
                editor_titulo='Configuración del centro' if panel == 'configuracion' else
                    ('Nuevo registro' if editar == 'nuevo' else str(objeto)),
                formulario_url=request.get_full_path(), es_solicitud=tipo == 'solicitudes')
            if tipo == 'solicitudes':
                contexto['historial'] = objeto.historial.select_related('autor').order_by('-fecha')[:40]
    elif request.method == 'POST':
        raise Http404
    elif panel in ('resumen', 'agenda'):
        contexto.update(_resumen(centro))
    if tipo and not editar and panel != 'configuracion':
        consulta = _consulta(_modelo(REGISTROS[tipo][1]), centro)
        # Los títulos/detalles usan relaciones de estas filas. Cargarlas con la
        # página evita una consulta por fila en los paneles administrativos.
        relaciones = {
            'solicitudes': ('usuario', 'centro'), 'hitos': ('proyecto',),
            'horarios': ('zona', 'equipo'), 'bloqueos': ('zona', 'equipo'),
            'sesiones': ('solicitud', 'responsable'),
        }.get(tipo, ())
        if relaciones:
            consulta = consulta.select_related(*relaciones)
        elif 'componente' in {f.name for f in consulta.model._meta.fields}:
            consulta = consulta.select_related('componente')
        busqueda = request.GET.get('q', '').strip()[:200]
        candidatos = {f.name for f in consulta.model._meta.fields}
        columnas = [n for n in ('titulo', 'nombre', 'codigo', 'descripcion') if n in candidatos]
        if busqueda and columnas:
            criterio = Q()
            for nombre in columnas:
                criterio |= Q(**{nombre + '__icontains': busqueda})
            consulta = consulta.filter(criterio)
        estado = request.GET.get('estado', '')
        if tipo == 'solicitudes':
            if estado in dict(consulta.model.ESTADOS):
                consulta = consulta.filter(estado=estado)
            contexto['estados'] = consulta.model.ESTADOS
        pagina = Paginator(consulta.order_by('-pk'), 25).get_page(request.GET.get('pagina'))
        contexto.update(filas=[_fila(o, centro, panel, tipo) for o in pagina], pagina=pagina, q=busqueda,
            estado_filtro=estado, lista_titulo=REGISTROS[tipo][2], puede_crear=tipo != 'solicitudes',
            nuevo_url=url_gestion(centro, panel=panel, tipo=tipo, editar='nuevo'))
        contexto['anterior_url'] = url_gestion(centro, panel=panel, tipo=tipo, q=busqueda, estado=estado,
                                               pagina=pagina.previous_page_number()) if pagina.has_previous() else ''
        contexto['siguiente_url'] = url_gestion(centro, panel=panel, tipo=tipo, q=busqueda, estado=estado,
                                                pagina=pagina.next_page_number()) if pagina.has_next() else ''
    plantilla = 'centros_id/gestion/panel.html' if request.GET.get('fragment') == '1' else 'centros_id/gestion/pagina.html'
    return render(request, plantilla, contexto)
