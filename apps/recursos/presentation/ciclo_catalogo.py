"""Ciclo común a todas las tipologías: catálogo, solicitud, compra y recepción."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, es_receptor_de
from apps.recursos.models.adquisiciones import SolicitudAdquisicionRecurso
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo

TIPOS = {'equipo': (UnidadEquipo, 'laboratorio', 'activa', 'recursos', 'activos'),
         'software': (SoftwareDisponible, 'unidad', 'activo', 'recursos', 'software'),
         'consumible': (Consumible, 'unidad', 'activo', 'inventario', 'insumos')}


class SolicitudForm(forms.Form):
    anio = forms.IntegerField(label='Año de preparación del plan', min_value=2000, max_value=2200)
    cantidad = forms.DecimalField(min_value=Decimal('0.001'), max_digits=12, decimal_places=3)
    costo_unitario = forms.DecimalField(label='Valor unitario estimado (USD)', min_value=0,
        max_digits=14, decimal_places=4, required=False)
    mes_compra = forms.TypedChoiceField(label='Mes previsto de compra', coerce=str,
        choices=tuple((str(n), nombre) for n, nombre in enumerate(('Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo',
        'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'), 1)))
    justificacion = forms.CharField(label='Justificación de la necesidad', widget=forms.Textarea, max_length=3000)
    area_id = forms.ChoiceField(label='Área de destino')

    def __init__(self, *args, unidad=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gestion_unidades.models.espacios import EspacioReservable
        self.fields['area_id'].choices = [('unidad', 'Toda la unidad')] + list(
            EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre').values_list('pk', 'nombre'))


def _cantidad(valor, tipo):
    try:
        cantidad = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValidationError('Revisa la cantidad en el plan de compras.') from error
    if not cantidad.is_finite() or cantidad <= 0 or cantidad > Decimal('999999999') or cantidad.as_tuple().exponent < -3:
        raise ValidationError('La cantidad debe ser positiva y válida.')
    if tipo == 'equipo' and cantidad != 1:
        raise ValidationError('Esta solicitud corresponde a una unidad física. Solicita por separado las otras unidades del modelo.')
    if tipo == 'software' and cantidad != cantidad.to_integral_value():
        raise ValidationError('Las licencias se reciben en cantidades enteras.')
    return cantidad


def _fila(solicitud, redaccion):
    return next((fila for fila in (redaccion.contenido or {}).get('compras', [])
                 if isinstance(fila, dict) and fila.get('id_necesidad') == str(solicitud.necesidad)), None)


@transaction.atomic
def solicitar(unidad, tipo, recurso, datos, usuario):
    Unidad.objects.select_for_update().get(pk=unidad.pk)
    if getattr(recurso, TIPOS[tipo][2]):
        raise ValidationError('El recurso ya existe en el inventario; utiliza el plan para ampliación o reposición.')
    if tipo == 'equipo' and recurso.fecha_baja:
        raise ValidationError('Un activo dado de baja conserva su historia. Crea una referencia nueva para su sustituto.')
    anteriores = SolicitudAdquisicionRecurso.objects.filter(**{tipo: recurso})
    if (anteriores.exists() if tipo == 'equipo' else anteriores.exclude(estado='recibida').exists()):
        raise ValidationError('Este recurso ya tiene una solicitud; revisa su seguimiento.')
    cantidad = _cantidad(datos['cantidad'], tipo)
    documentos = DocumentoExpediente.objects.filter(unidad=unidad, anio=datos['anio'], exigido__fuente_reporte='compras')
    if not documentos.exists():
        from apps.documentos.presentation.expediente import construir_expediente
        construir_expediente(unidad, datos['anio'])
    documento = documentos.select_for_update().select_related('exigido').order_by('pk').first()
    if not documento or documento.estado not in ('pendiente', 'observado') or documento.recurso_id:
        raise ValidationError('El plan no está abierto para añadir necesidades. Abre un borrador editable en el Centro de reportes.')
    from apps.documentos.presentation.expediente_redaccion import obtener_redaccion
    redaccion = DocumentoElaborado.objects.select_for_update().filter(documento=documento).first() or obtener_redaccion(documento)
    solicitud = SolicitudAdquisicionRecurso(unidad=unidad, documento=documento, cantidad=cantidad,
        solicitada_por=usuario, **{tipo: recurso})
    from apps.documentos.presentation.pac_universitario import preparar_pac
    contenido = preparar_pac(deepcopy(redaccion.contenido or {}), unidad=unidad)
    clase = {'equipo': 'equipos', 'software': 'software'}.get(tipo,
        {'material': 'materiales', 'reactivo': 'reactivos'}.get(getattr(recurso, 'clasificacion', ''), 'insumos'))
    from apps.gestion_unidades.models.espacios import EspacioReservable
    area_id = str(datos.get('area_id') or 'unidad')
    area = None if area_id == 'unidad' else EspacioReservable.objects.filter(unidad=unidad, activo=True, pk=area_id).first()
    if area_id != 'unidad' and area is None:
        raise ValidationError('Selecciona un área activa de esta unidad.')
    nombre = recurso.equipo.nombre if tipo == 'equipo' else recurso.nombre
    from django.utils.html import strip_tags
    especificaciones = (recurso.equipo.caracteristicas_publicas if tipo == 'equipo'
        else recurso.descripcion if tipo == 'software' else recurso.especificacion_tecnica)
    fila = dict(id_necesidad=str(solicitud.necesidad), clase_bien=clase, item=nombre,
        especificaciones=strip_tags(especificaciones or '')[:3000],
        area_id=area_id, area_nombre=area.nombre if area else 'Toda la unidad', tipo_necesidad='dotacion',
        unidad_medida='unidad' if tipo != 'consumible' else recurso.unidad_medida,
        cantidad=str(cantidad), costo_unitario=str(datos['costo_unitario']) if datos.get('costo_unitario') is not None else '',
        mes_compra=datos['mes_compra'], justificacion=datos['justificacion'], equipos_referencia=[],
        observaciones=f'Solicitud de catálogo {tipo} #{recurso.pk}. Recurso aún no existente; pendiente de recepción.')
    contenido.setdefault('compras', []).append(fila)
    contenido['sin_compras_justificacion'] = ''
    redaccion.contenido, redaccion.actualizado_por = contenido, usuario
    redaccion.version += 1
    redaccion.save()
    solicitud.save()
    return solicitud


@transaction.atomic
def transicionar(solicitud, accion, referencia, usuario, tipo):
    Unidad.objects.select_for_update().get(pk=solicitud.unidad_id)
    solicitud = SolicitudAdquisicionRecurso.objects.select_for_update().get(pk=solicitud.pk)
    recurso = TIPOS[tipo][0].objects.select_for_update().get(pk=getattr(solicitud, tipo + '_id'))
    if accion == 'recibir' and solicitud.estado == 'recibida':
        return solicitud
    redaccion = DocumentoElaborado.objects.select_for_update().get(documento=solicitud.documento)
    fila = _fila(solicitud, redaccion)
    if not fila:
        raise ValidationError('La necesidad ya no está en el plan. Revisa el borrador antes de continuar.')
    esperada = {'equipo': 'equipos', 'software': 'software'}.get(tipo)
    clase_distinta = (esperada and fila.get('clase_bien') != esperada or tipo == 'consumible'
                     and fila.get('clase_bien') not in ('materiales', 'insumos', 'reactivos', 'repuestos'))
    if accion != 'revisar' and clase_distinta:
        raise ValidationError('La clase de compra ya no corresponde al recurso solicitado.')
    if accion == 'revisar':
        if not usuario.is_superuser:
            raise PermissionDenied('Solo Dirección devuelve una adquisición a revisión.')
        if solicitud.estado not in ('aprobada', 'comprada'):
            raise ValidationError('La solicitud no está pendiente de revisión de una aprobación.')
        solicitud.estado, solicitud.contenido_aprobado, solicitud.aprobada_por = 'solicitada', {}, None
    elif accion == 'aprobar':
        if not usuario.is_superuser:
            raise PermissionDenied('Solo Dirección aprueba esta adquisición.')
        if solicitud.estado != 'solicitada':
            raise ValidationError('La solicitud ya fue evaluada.')
        solicitud.cantidad = _cantidad(fila.get('cantidad'), tipo)
        from apps.documentos.presentation.pac_universitario import _numero
        costo = _numero(fila.get('costo_unitario'))
        if costo is None or costo < 0 or str(fila.get('mes_compra')) not in {str(n) for n in range(1, 13)} or not str(fila.get('justificacion', '')).strip():
            raise ValidationError('Completa el precio, mes y justificación en el plan antes de aprobar.')
        solicitud.contenido_aprobado, solicitud.aprobada_por = deepcopy(fila), usuario
        solicitud.estado = 'aprobada'
    else:
        if solicitud.contenido_aprobado != fila:
            raise ValidationError('La necesidad cambió después de aprobarse. Requiere una nueva revisión de Dirección.')
        if not referencia.strip() or len(referencia.strip()) > 200:
            raise ValidationError('Registra una referencia documental válida (hasta 200 caracteres).')
        if accion == 'comprar' and solicitud.estado == 'aprobada':
            if not (usuario.is_superuser or es_receptor_de(usuario, solicitud.unidad)
                    or puede_operar_modulo_unidad(usuario, solicitud.unidad, 'finanzas')):
                raise PermissionDenied('La compra la documenta la dependencia responsable o el responsable financiero.')
            solicitud.estado, solicitud.referencia_compra = 'comprada', referencia.strip()
        elif accion == 'recibir' and solicitud.estado == 'comprada':
            if not puede_operar_modulo_unidad(usuario, solicitud.unidad, TIPOS[tipo][3]):
                raise PermissionDenied('No tienes permiso para recibir este recurso en la unidad.')
            solicitud.estado, solicitud.referencia_recepcion, solicitud.recibida_por = 'recibida', referencia.strip(), usuario
            solicitud.save()  # El guardado y el ingreso se confirman en la misma transacción.
            if tipo == 'equipo':
                recurso.activa, recurso.estado_unidad = True, 'disponible'
                recurso.existencia_verificada = True
                recurso.existencia_verificada_en, recurso.existencia_verificada_por = timezone.now(), usuario
                recurso.documento_adquisicion = solicitud.referencia_compra
                area_id = fila.get('area_id')
                if area_id and area_id != 'unidad':
                    from apps.gestion_unidades.models.espacios import EspacioReservable
                    area = EspacioReservable.objects.filter(pk=area_id, unidad=solicitud.unidad, activo=True).first()
                    if not area:
                        raise ValidationError('El área de destino dejó de estar activa; revisa la adquisición antes de recibir.')
                    recurso.espacios_asociados.set([area])
            elif tipo == 'software':
                recurso.activo = True
                recurso.licencias_totales = recurso.licencias_disponibles = int(solicitud.cantidad)
            else:
                if recurso.stock_total != 0:
                    raise ValidationError('La referencia inactiva conserva saldo. Concilia las existencias antes de recibirla.')
                EntradaInventario.objects.create(consumible=recurso, unidad=solicitud.unidad,
                    tipo='ingreso', motivo='recepcion', cantidad=solicitud.cantidad, usuario=usuario,
                    referencia=referencia.strip()[:100], clave_idempotencia=f'adquisicion-recurso:{solicitud.pk}')
                recurso.refresh_from_db()
                recurso.activo, recurso.visible_en_reservas = True, True
            recurso.full_clean()
            recurso.save()
        else:
            raise ValidationError('Completa primero la aprobación, luego la compra y finalmente la recepción.')
    solicitud.save()
    return solicitud


def eliminar_referencia(recurso, confirmacion):
    """Elimina sólo referencias sin historia; no borra movimientos en cascada."""
    from django.db.models.deletion import Collector
    if getattr(recurso, 'activa', getattr(recurso, 'activo', False)):
        raise ValidationError('Desactiva la referencia antes de eliminarla.')
    codigo = getattr(recurso, 'codigo_unidad', getattr(recurso, 'codigo', '')) or str(recurso.pk)
    if confirmacion != codigo:
        raise ValidationError(f'Confirma escribiendo {codigo}.')
    if getattr(recurso, 'stock_total', 0):
        raise ValidationError('La referencia tiene existencias; concilia el inventario antes de eliminarla.')
    if isinstance(recurso, UnidadEquipo) and recurso.laboratorios.exclude(pk=recurso.laboratorio_id).exists():
        raise ValidationError('El equipo está compartido con otra unidad. Conserva el registro y revisa sus asignaciones.')
    # Relaciones de catálogo admitidas. Cualquier otro vínculo conserva la historia.
    permitidas = {'espacios_asociados', 'software_instalado', 'laboratorios', 'equipos_instalados',
                  'elementos_de_ficha', 'por_equipo'}
    for relacion in recurso._meta.related_objects:
        if relacion.get_accessor_name() in permitidas:
            continue
        manager = getattr(recurso, relacion.get_accessor_name(), None)
        if manager is not None and hasattr(manager, 'exists') and manager.exists():
            raise ValidationError('El registro tiene historial o movimientos vinculados. Conserva la referencia inactiva.')
    colector = Collector(using=recurso._state.db)
    try:
        colector.collect([recurso])
    except (ProtectedError, RestrictedError) as error:
        raise ValidationError('El registro está vinculado a otros datos y debe conservarse inactivo.') from error
    # Evitar el borrado de entidades de negocio no detectadas como relación inversa.
    for modelo, objetos in colector.data.items():
        if modelo is not type(recurso) and not modelo._meta.auto_created and objetos:
            raise ValidationError('El registro tiene información dependiente y debe conservarse inactivo.')
    recurso.delete()


@login_required
@require_http_methods(['GET', 'POST'])
@xframe_options_sameorigin
def ciclo_recurso_view(request, slug, tipo, pk):
    if tipo not in TIPOS:
        raise Http404
    unidad = get_object_or_404(Unidad, slug=slug)
    modelo, campo_unidad, campo_activo, permiso, modo = TIPOS[tipo]
    if not (puede_operar_modulo_unidad(request.user, unidad, permiso)
            or puede_operar_modulo_unidad(request.user, unidad, 'finanzas') or es_receptor_de(request.user, unidad)):
        raise PermissionDenied
    recurso = get_object_or_404(modelo, pk=pk, **{campo_unidad: unidad})
    vuelta = reverse('gestion_unidad', args=[slug]) + f'?view=recursos&modo_recursos={modo}&estado_recursos=todos'
    solicitud = SolicitudAdquisicionRecurso.objects.filter(unidad=unidad, **{tipo: recurso}).order_by('-pk').first()
    form = SolicitudForm(request.POST if request.method == 'POST' and request.POST.get('accion') == 'solicitar' else None,
        unidad=unidad, initial={'anio': timezone.localdate().year, 'cantidad': 1, 'mes_compra': '1', 'area_id': 'unidad'})
    error = ''
    if request.method == 'POST':
        try:
            with transaction.atomic():
                Unidad.objects.select_for_update().get(pk=unidad.pk)
                recurso = modelo.objects.select_for_update().get(pk=recurso.pk)
                accion = request.POST.get('accion')
                if accion == 'eliminar':
                    if not puede_operar_modulo_unidad(request.user, unidad, permiso):
                        raise PermissionDenied
                    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
                    registrar_auditoria(request, unidad=unidad, accion='eliminar', objeto=recurso,
                        descripcion='Referencia inactiva eliminada sin movimientos vinculados',
                        anteriores={'codigo': getattr(recurso, 'codigo_unidad', getattr(recurso, 'codigo', '')),
                            'nombre': recurso.equipo.nombre if tipo == 'equipo' else recurso.nombre})
                    eliminar_referencia(recurso, request.POST.get('confirmacion', ''))
                    messages.success(request, 'Referencia eliminada.')
                    return redirect(vuelta)
                if accion == 'solicitar':
                    if not puede_operar_modulo_unidad(request.user, unidad, permiso):
                        raise PermissionDenied
                    if form.is_valid():
                        solicitud = solicitar(unidad, tipo, recurso, form.cleaned_data, request.user)
                    else:
                        raise ValidationError('Revisa los datos de la solicitud.')
                elif solicitud:
                    solicitud = transicionar(solicitud, accion, request.POST.get('referencia', ''), request.user, tipo)
                else:
                    raise ValidationError('No existe una solicitud para este recurso.')
                from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
                registrar_auditoria(request, unidad=unidad, accion='actualizar', objeto=solicitud,
                    descripcion=f'Adquisición de recurso: {solicitud.get_estado_display()}')
            return redirect(request.path)
        except ValidationError as exc:
            error = ' '.join(exc.messages)
        except IntegrityError:
            error = 'El recurso cambió o recibió nuevos vínculos. Revisa sus datos antes de continuar.'
    return render(request, 'portal/pages/unidades/gestion/ciclo_recurso.html', dict(unidad=unidad,
        recurso=recurso, nombre=recurso.equipo.nombre if tipo == 'equipo' else recurso.nombre,
        tipo=tipo, activo=getattr(recurso, campo_activo), solicitud=solicitud, form=form, error=error,
        codigo=getattr(recurso, 'codigo_unidad', getattr(recurso, 'codigo', '')) or str(recurso.pk), vuelta=vuelta,
        puede_aprobar=request.user.is_superuser,
        puede_solicitar=(not getattr(recurso, campo_activo)
            and (solicitud is None or solicitud.estado == 'recibida' and tipo != 'equipo')),
        puede_comprar=(request.user.is_superuser or es_receptor_de(request.user, unidad)
            or puede_operar_modulo_unidad(request.user, unidad, 'finanzas')),
        puede_gestionar=puede_operar_modulo_unidad(request.user, unidad, permiso)))


@login_required
@xframe_options_sameorigin
def adquisiciones_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not (puede_operar_modulo_unidad(request.user, unidad, 'recursos')
            or puede_operar_modulo_unidad(request.user, unidad, 'inventario')
            or puede_operar_modulo_unidad(request.user, unidad, 'finanzas') or es_receptor_de(request.user, unidad)):
        raise PermissionDenied
    entradas = []
    for solicitud in SolicitudAdquisicionRecurso.objects.filter(unidad=unidad).select_related(
            'equipo__equipo', 'software', 'consumible', 'documento').order_by('-pk'):
        tipo = 'equipo' if solicitud.equipo_id else 'software' if solicitud.software_id else 'consumible'
        recurso = solicitud.recurso
        entradas.append(dict(solicitud=solicitud, nombre=recurso.equipo.nombre if tipo == 'equipo' else recurso.nombre,
            url=reverse('ciclo_recurso_unidad', args=[slug, tipo, recurso.pk])))
    return render(request, 'portal/pages/unidades/gestion/adquisiciones.html', dict(unidad=unidad, entradas=entradas))
