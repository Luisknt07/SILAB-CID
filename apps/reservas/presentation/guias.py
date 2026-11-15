"""Edición, revisión y publicación de guías estructuradas de práctica."""

from apps.core.presentation.identidad import identidad_actual

from copy import deepcopy
from io import BytesIO
import json
from uuid import uuid4
from pathlib import Path
import re
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, OuterRef, Q, Subquery
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.dateparse import parse_datetime
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods, require_POST

from apps.gestion_unidades.presentation.auditoria import instantanea, registrar_auditoria
from apps.core.presentation.pdf_institucional import marco_institucional
from apps.gestion_unidades.presentation.permisos import puede_crear_guias_unidad, puede_operar_modulo_unidad, puede_cargar_guia_firmada
from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.formacion.models.practicas import PlanificacionPractica
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile

from apps.reservas.presentation.forms import GuiaPracticaForm
from apps.reservas.presentation.guia_automatizacion import politicas_guia_desde_reserva
from apps.reservas.presentation.guia_contenido import adjuntar_figuras_borrador, figuras_borrador, bloques_enriquecidos, figuras_de_guia, figuras_permitidas, guardar_figura, guardar_imagenes_guia, pasos_procedimiento, resolver_figura, tiene_adjuntos, validar_imagenes_guia
from apps.reservas.presentation.guia_firma_certificada import registrar_pdf_firmado
from apps.reservas.presentation.guia_contrato import GUIA_INTEGRADA_CAMPOS
from apps.reservas.presentation.guia_html import CAMPOS_RICOS, FORMATO_HTML, POLITICA_POR_CAMPO, DocumentoHtml, html_desde_legado, sanear
from apps.reservas.presentation.guia_firmas import ROLES_FIRMA, firmar_contenido_guia, firmas_desde_post, firmas_predeterminadas, normalizar_firmas, verificar_firma_elaborador
from apps.reservas.presentation.guia_referencias import normalizar_bibliografia, normalizar_materiales_complementarios
from apps.core.presentation.pdf_institucional import fuentes_documento, hoja_de_estilos


GUIA_FIELDS_AUDIT = (
    'actividad_id', 'titulo', 'descripcion', 'codigo_guia', 'numero_version',
    'es_estructurada', 'es_vigente', 'contenido', 'visibilidad',
    'estado_publicacion', 'permite_descarga', 'solicita_publicacion',
    'observaciones_revision', 'activo', 'orden', 'subido_por_id',
    'revisado_por_id', 'revisado_en', 'aprobado_por_id', 'aprobado_en',
    'firmado_por_id', 'firmado_en', 'firma_certificada_resumen',
)


def _puede_operar_guias(usuario, unidad):
    return puede_operar_modulo_unidad(usuario, unidad, 'practicas')


def _momento_firma_local(firma):
    momento = parse_datetime(str((firma or {}).get('momento') or ''))
    if momento is None:
        return None
    if timezone.is_naive(momento):
        momento = timezone.make_aware(momento, timezone.get_current_timezone())
    return timezone.localtime(momento)


def _puede_crear_guias(usuario, unidad):
    return puede_crear_guias_unidad(usuario, unidad)


def _puede_ver_guia(usuario, guia):
    actividad = guia.actividad
    if usuario.is_authenticated and usuario.is_active:
        if (
            actividad.creado_por_id == usuario.pk
            or actividad.participantes_autorizados.filter(pk=usuario.pk).exists()
            or _puede_operar_guias(usuario, actividad.unidad)
        ):
            return True
        return (
            guia.estado_publicacion == 'publicada'
            and guia.visibilidad in {'unidad', 'publica'}
        )
    return guia.estado_publicacion == 'publicada' and guia.visibilidad == 'publica'


def _puede_cargar_firmada(usuario, guia):
    """La persona autora o el personal de la unidad cargan la version firmada."""
    return puede_cargar_guia_firmada(usuario, guia)


def puede_editar_guia(usuario, guia):
    if not usuario.is_authenticated or not usuario.is_active or not guia.es_editable:
        return False
    return (
        guia.actividad.creado_por_id == usuario.pk
        or _puede_operar_guias(usuario, guia.actividad.unidad)
    )


def _reserva_fuente_visible(guia, usuario, *, operador=False):
    """Recupera la solicitud origen sin exponer reservas de terceros."""
    if not guia or not isinstance(guia.contenido, dict):
        return None
    reserva_id = guia.contenido.get("reserva_fuente_id")
    if not reserva_id:
        return None
    queryset = Reserva.objects.filter(
        pk=reserva_id,
        laboratorio=guia.actividad.unidad,
        actividad_catalogo=guia.actividad,
    )
    if not operador:
        queryset = queryset.filter(usuario=usuario)
    return queryset.first()


ESTADOS_GUIA_EN_TRABAJO = ('borrador', 'revision', 'rechazada')


def _version_en_trabajo(actividad, *, excluir_pk=None, sesion=None):
    """Borrador abierto de la actividad, si existe.

    Solo puede haber una version en trabajo a la vez: crear otra deja al
    revisor con dos borradores y sin saber cual es el vigente.
    """
    queryset = GuiaActividadReserva.objects.filter(
        actividad=actividad,
        es_estructurada=True,
        activo=True,
        sesion=sesion,
        estado_publicacion__in=ESTADOS_GUIA_EN_TRABAJO,
    )
    if excluir_pk:
        queryset = queryset.exclude(pk=excluir_pk)
    return queryset.order_by('-numero_version', '-pk').first()


def _contenido_para_vista(guia, figuras=None):
    """Contenido listo para la plantilla; ``figuras`` sustituye a las de la guía (borradores)."""
    contenido = deepcopy(guia.contenido or {})
    es_html = contenido.get('formato_contenido') == FORMATO_HTML
    campos_lista = (
        'objetivos',
        'equipos',
        'software',
        'materiales',
        'reactivos',
        'medidas_seguridad',
        'procedimiento',
        'resultados_esperados',
        'criterios_evaluacion',
        'manejo_residuos',
        'bibliografia',
    )
    for clave in campos_lista:
        if es_html and clave in CAMPOS_RICOS:
            # Los apartados del editor visual son HTML acotado, no listas.
            continue
        valor = contenido.get(clave)
        if isinstance(valor, str):
            contenido[clave] = [linea.strip() for linea in valor.splitlines() if linea.strip()]
        elif not valor:
            contenido[clave] = []
        elif not isinstance(valor, (list, tuple)):
            contenido[clave] = [str(valor)]
    # Compatibilidad con versiones anteriores: el software se guardaba dentro
    # de ``equipos`` con el prefijo "Software:". Se separa al presentar el
    # documento sin alterar el historial ni exigir migraciones destructivas.
    if not contenido.get('software'):
        software_heredado = []
        equipos = []
        for item in contenido.get('equipos', []):
            texto = str(item).strip()
            if texto.lower().startswith('software:'):
                nombre = texto.split(':', 1)[1].strip()
                if nombre:
                    software_heredado.append(nombre)
            else:
                equipos.append(item)
        contenido['equipos'] = equipos
        contenido['software'] = software_heredado
    # En versiones iniciales existía una celda separada de reactivos. El
    # formato vigente usa una sola fuente para materiales e insumos; se integra
    # aquí para conservar el historial sin volver a pedir el dato al usuario.
    for item in contenido.get('reactivos', []):
        if item not in contenido['materiales']:
            contenido['materiales'].append(item)
    contenido['reactivos'] = []
    if contenido.get('formato_procedimiento') not in {'numerado', 'vinetas', 'parrafos'}:
        contenido['formato_procedimiento'] = 'numerado'
    if not es_html:
        contenido['procedimiento'] = [
            re.sub(r'^\s*(?:\d+[.)]|[-*\u2022])\s*', '', str(item)).strip()
            for item in contenido.get('procedimiento', [])
            if re.sub(r'^\s*(?:\d+[.)]|[-*\u2022])\s*', '', str(item)).strip()
        ]
    contenido.setdefault('laboratorio', guia.actividad.unidad.nombre)
    materiales = contenido.get('materiales_complementarios')
    if isinstance(materiales, str):
        materiales = normalizar_materiales_complementarios(materiales)
    contenido['materiales_complementarios'] = [
        item for item in (materiales or [])
        if isinstance(item, dict) and (item.get('titulo') or item.get('url'))
    ]
    contenido['figuras'] = figuras if figuras is not None else figuras_de_guia(guia)
    contenido['es_html'] = es_html
    firmas = contenido.get('firmas')
    # Guias anteriores (sin configuracion de firmas) conservan las tres columnas.
    contenido['firmas'] = normalizar_firmas(firmas) if isinstance(firmas, dict) else firmas_predeterminadas(legado=True)
    contenido['firmas_lista'] = _firmas_lista(guia, contenido)
    if es_html:
        for clave in CAMPOS_RICOS:
            if not isinstance(contenido.get(clave), str):
                contenido[clave] = ''
        seguridad = contenido.get('seguridad_institucional')
        contenido['seguridad_institucional'] = (
            [str(item).strip() for item in seguridad if str(item).strip()]
            if isinstance(seguridad, (list, tuple)) else []
        )
        documento = DocumentoHtml(
            contenido, contenido['figuras'],
            formato_procedimiento=contenido['formato_procedimiento'],
        )
        contenido['documento'] = documento
        contenido['zonas'] = {clave: documento.html(clave) for clave in CAMPOS_RICOS}
    return contenido


def _firmas_lista(guia, contenido):
    """Bloques de firma: lo escrito por el autor o, en su defecto, lo que registra el sistema."""
    firmas = contenido.get('firmas') or {}
    firma_elaborador = contenido.get('firma_elaborador') or {}
    valida = verificar_firma_elaborador(guia)
    momento = _momento_firma_local(firma_elaborador)

    def fecha_local(valor):
        return timezone.localtime(valor).strftime('%d/%m/%Y %H:%M') if valor else ''

    respaldo = {
        'elaborado': (
            firma_elaborador.get('nombre') or contenido.get('docente_responsable')
            or _nombre_usuario_pdf(guia.subido_por) or 'Pendiente',
            'Docente responsable',
            (
                f"Firma electrónica interna · {str(firma_elaborador.get('huella_sha256', ''))[:12]}"
                if valida else 'Firma electrónica pendiente'
            ),
            momento.strftime('%d/%m/%Y %H:%M') if valida and momento else (fecha_local(guia.creado_en) or 'Pendiente'),
        ),
        'revisado': (
            _nombre_usuario_pdf(guia.revisado_por) or 'Pendiente',
            'Revisión de la unidad',
            'Revisión electrónica registrada' if guia.revisado_en else 'Pendiente de revisión',
            fecha_local(guia.revisado_en) or 'Pendiente',
        ),
        'aprobado': (
            _nombre_usuario_pdf(guia.aprobado_por) or 'Pendiente',
            'Aprobación de la unidad',
            'Aprobación electrónica registrada' if guia.aprobado_en else 'Pendiente de aprobación',
            fecha_local(guia.aprobado_en) or 'Pendiente',
        ),
    }
    lista = []
    for rol, etiqueta in ROLES_FIRMA:
        datos = firmas.get(rol) or {}
        nombre, cargo, estado, fecha = respaldo[rol]
        lista.append({
            'rol': rol,
            'etiqueta': etiqueta,
            'activo': bool(datos.get('activo', True)),
            'nombre': datos.get('nombre', ''),
            'cargo': datos.get('cargo', ''),
            'fecha': datos.get('fecha', ''),
            'nombre_vista': datos.get('nombre') or nombre,
            'cargo_vista': datos.get('cargo') or cargo,
            'estado_vista': estado,
            'fecha_vista': datos.get('fecha') or fecha,
            'verificacion': (
                str(firma_elaborador.get('huella_sha256', ''))[:12]
                if rol == 'elaborado' and valida else ''
            ),
        })
    return lista


def _zonas_para_editor(guia, contenido_vista):
    """HTML de cada apartado para las zonas editables (imágenes resueltas).

    Una guía en el formato de texto anterior se convierte al abrirla; el
    registro no cambia hasta que la persona guarda desde el editor.
    """
    if contenido_vista.get('es_html'):
        documento = contenido_vista['documento']
        return {clave: documento.html(clave, edicion=True) for clave in CAMPOS_RICOS}
    convertido = html_desde_legado(contenido_vista, contenido_vista.get('figuras'))
    documento = DocumentoHtml(convertido, contenido_vista.get('figuras'))
    return {clave: documento.html(clave, edicion=True) for clave in CAMPOS_RICOS}


def _figuras_json(figuras):
    return [
        {'id': figura['pk'], 'url': figura['url'], 'titulo': figura['titulo']}
        for figura in figuras or [] if figura.get('pk')
    ]


def _version_de(guia):
    return guia.actualizado_en.isoformat() if guia and guia.pk and guia.actualizado_en else ''


def _actividad_desde_formulario(form, usuario, unidad):
    actividad = form.cleaned_data.get('actividad_existente')
    if actividad:
        return actividad
    return CatalogoActividadReserva.objects.create(
        proposito_codigo=form.cleaned_data['proposito_codigo'],
        subtipo_actividad=form.cleaned_data['subtipo_actividad'],
        nombre=form.cleaned_data['nombre_actividad'],
        codigo=form.cleaned_data.get('codigo_actividad', ''),
        unidad=unidad,
        responsable=form.cleaned_data.get('docente_responsable', ''),
        descripcion=form.cleaned_data.get('descripcion_actividad', ''),
        creado_por=usuario,
        estado_publicacion='borrador',
        visibilidad='privada',
        activo=True,
    )


def _pestana_de_guias(unidad):
    """Clave y nombre de la pestaña pública donde la unidad muestra sus guías aprobadas."""
    mapa = mapa_de(unidad)
    modulos = unidad.modulos_contenido.filter(activo=True).order_by('orden')
    if mapa:
        modulo = modulos.filter(clave=mapa.modulo_de(mapa.numero('guias'))).first()
    else:
        modulo = modulos.first()
    return (modulo.clave, modulo.nombre) if modulo else ('', 'la ficha')


@login_required
def lista_guias_practica(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    operador = _puede_operar_guias(request.user, unidad)
    mostrar_historial = request.GET.get('historial', '').strip() == '1'
    guias = GuiaActividadReserva.objects.filter(
        actividad__unidad=unidad, es_estructurada=True,
    ).select_related(
        'actividad', 'actividad__creado_por', 'revisado_por', 'aprobado_por'
    ).prefetch_related('actividad__reservas')
    if not operador:
        guias = guias.filter(actividad__creado_por=request.user)
    if not mostrar_historial:
        ultima_version = (
            GuiaActividadReserva.objects.filter(
                actividad_id=OuterRef('actividad_id'),
                es_estructurada=True,
                activo=True,
            )
            .order_by('-numero_version', '-pk')
            .values('pk')[:1]
        )
        guias = guias.filter(activo=True).filter(
            Q(es_vigente=True) | Q(pk=Subquery(ultima_version))
        )
    estado = request.GET.get('estado', '').strip()
    if estado in dict(GuiaActividadReserva.ESTADO_CHOICES):
        guias = guias.filter(estado_publicacion=estado)
    # Cada guía indica de qué solicitud viene: la lista es el índice y el
    # expediente de la reserva es donde se lee, se firma y se corrige.
    fichas = []
    clave_guias, nombre_guias = _pestana_de_guias(unidad)
    for guia in guias:
        reserva = next(
            (
                item
                for item in sorted(
                    guia.actividad.reservas.all(),
                    key=lambda item: item.pk,
                    reverse=True,
                )
                if item.usuario_id == request.user.pk or operador
            ),
            None,
        )
        reserva_url = (
            reserva.url_seguimiento
            if reserva and reserva.usuario_id == request.user.pk
            else ''
        )
        # La guia aprobada ya vive en el modulo publico de la unidad y la
        # pendiente se termina en la reserva: la lista lleva a ese sitio en vez
        # de abrir otra vez el visor.
        if guia.estado_publicacion == 'publicada' and (
            guia.visibilidad in {'unidad', 'publica'}
            or guia.actividad.creado_por_id == request.user.pk
            or operador
        ):
            destino = {
                'url': f"{unidad.get_absolute_url()}?guia={guia.pk}#{clave_guias}",
                'texto': f'Ver en {nombre_guias}',
                'icono': 'fa-book-open',
            }
        elif reserva_url:
            destino = {
                'url': reserva_url,
                'texto': (
                    'Firmar o corregir en mis reservas'
                    if guia.es_editable or guia.estado_publicacion == 'revision'
                    else 'Abrir en mis reservas'
                ),
                'icono': 'fa-calendar-check',
            }
        else:
            destino = {
                'url': reverse('ver_guia_actividad', args=[guia.pk]),
                'texto': 'Abrir el documento',
                'icono': 'fa-file-alt',
            }
        fichas.append({
            'guia': guia,
            'reserva': reserva,
            'reserva_url': reserva_url,
            'destino': destino,
            # Que la guía admita cambios no significa que esta persona pueda
            # hacerlos: el botón usa la misma regla que el editor.
            'puede_editar': puede_editar_guia(request.user, guia),
        })
    return render(request, 'portal/pages/unidades/guias/lista.html', {
        'unidad': unidad,
        'fichas': fichas,
        'estado': estado,
        'estados': GuiaActividadReserva.ESTADO_CHOICES,
        'mostrar_historial': mostrar_historial,
        'es_operador': operador,
        'puede_crear': _puede_crear_guias(request.user, unidad),
        'page_title': 'Mis guías de práctica',
        'page_key': 'guias-practica',
    })




def _procesos_para_guia(unidad):
    """Las recetas con etapas de una unidad que produce, para prellenar la guía."""
    from django.core.exceptions import ObjectDoesNotExist

    from apps.plantas_piloto.operacion.models.produccion import Receta

    try:
        if not unidad.configuracion_operativa.registra_produccion:
            return []
    except ObjectDoesNotExist:
        return []
    return [
        {
            'nombre': receta.nombre_publico,
            'producto': receta.producto.nombre,
            'etapas': receta.etapas.count(),
            'url': reverse('guia_desde_proceso', args=[unidad.slug, receta.pk]),
        }
        for receta in Receta.objects.filter(unidad=unidad, activa=True).select_related('producto').order_by('nombre')
        if receta.etapas.exists()
    ]


@login_required
@require_http_methods(['GET', 'POST'])
def editar_guia_practica(request, slug, guia_id=None):
    unidad = get_object_or_404(Unidad, slug=slug)
    operador = _puede_operar_guias(request.user, unidad)
    if guia_id is None and not _puede_crear_guias(request.user, unidad):
        return HttpResponseForbidden(
            _('Para crear guías nuevas necesitas verificación docente vigente '
              'o autorización de prácticas en esta unidad.')
        )
    guia = None
    if guia_id is not None:
        guia = get_object_or_404(
            GuiaActividadReserva.objects.select_related('actividad'),
            pk=guia_id, actividad__unidad=unidad, es_estructurada=True, activo=True,
        )
        if not puede_editar_guia(request.user, guia):
            raise Http404('Guía no disponible para edición')

    inicial = {}
    procedencia_plantilla = None
    if guia is None and request.GET.get('plantilla') == 'logistica-cd' and not request.GET.get('reserva'):
        # Precarga explícita y diferida: nunca se consulta el simulador al abrir
        # una guía ordinaria ni se interpreta metadata enviada por el cliente.
        from apps.formacion.presentation.logistica_partidas import unidad_disponible
        from apps.laboratorios.operacion.presentation.logistica_distribucion import _semilla
        from apps.laboratorios.operacion.presentation.logistica_distribucion_motor import CASOS
        from apps.laboratorios.operacion.presentation.logistica_operacion_contenido import inicial_guia, procedencia_guia

        unidad_disponible(slug)
        caso_plantilla = request.GET.get('caso', 'cd-normal')
        if caso_plantilla not in CASOS:
            raise Http404('Plantilla no disponible.')
        semilla_plantilla = _semilla(request)
        procedencia_plantilla = procedencia_guia(caso_plantilla, semilla_plantilla)
        if request.method == 'GET':
            inicial = inicial_guia(caso_plantilla, semilla_plantilla)
    if request.method == 'GET' and guia is None:
        if request.GET.get('reserva', '').isdigit():
            inicial['reserva_referencia'] = request.GET['reserva']
        if request.GET.get('actividad', '').isdigit():
            inicial['actividad_existente'] = request.GET['actividad']
    token_borrador = request.POST.get('guia_imagenes_token', request.GET.get('borrador', ''))[:40]
    form = GuiaPracticaForm(
        request.POST or None,
        unidad=unidad,
        usuario=request.user,
        guia=guia,
        operador=operador,
        initial=inicial,
        figuras_permitidas=figuras_permitidas(guia, token_borrador, request.user),
    )
    error_flujo = ''
    if request.method == 'POST' and form.is_valid():
        try:
            validar_imagenes_guia(
                request.FILES.getlist('guia_imagenes'),
                existentes=guia.imagenes.count() if guia else 0,
            )
        except ValueError as error:
            error_flujo = str(error)
        version_base = request.POST.get('version_base', '')
        if guia and version_base and version_base != _version_de(guia):
            # Otra pestaña o persona guardó después de abrir este formulario:
            # no se sobrescribe en silencio.
            error_flujo = (
                'Esta guía cambió después de que abriste el editor. Abre la versión '
                'actual y vuelve a aplicar tus cambios.'
            )
    if request.method == 'POST' and form.is_valid() and not error_flujo:
        accion = request.POST.get('accion', 'guardar')
        with transaction.atomic():
            es_nueva = guia is None
            if es_nueva:
                Unidad.objects.select_for_update().get(pk=unidad.pk)
                usuario_actual = get_user_model().objects.select_for_update().get(pk=request.user.pk)
                UserProfile.objects.select_for_update().get(user_id=usuario_actual.pk)
                if not _puede_crear_guias(usuario_actual, unidad):
                    return HttpResponseForbidden(_(
                        'Para crear guías nuevas necesitas verificación docente vigente '
                        'o autorización de prácticas en esta unidad.'
                    ))
            anteriores = instantanea(guia, GUIA_FIELDS_AUDIT) if guia else {}
            actividad = guia.actividad if guia else _actividad_desde_formulario(
                form, request.user, unidad
            )
            if guia is None:
                ultima_version = GuiaActividadReserva.objects.filter(
                    actividad=actividad, es_estructurada=True
                ).order_by('-numero_version').values_list('numero_version', flat=True).first()
                guia = GuiaActividadReserva(
                    actividad=actividad,
                    numero_version=(ultima_version or 0) + 1,
                    es_estructurada=True,
                    subido_por=request.user,
                    estado_publicacion='borrador',
                    visibilidad='participantes',
                )
            firmas_previas = (guia.contenido or {}).get('firmas') if guia.pk else None
            guia.titulo = form.cleaned_data['titulo']
            guia.codigo_guia = form.cleaned_data.get('codigo_guia', '')
            guia.descripcion = form.cleaned_data.get('descripcion_actividad', '')
            procedencia_anterior = (guia.contenido or {}).get('procedencia_simulacion')
            guia.contenido = form.contenido_normalizado()
            if isinstance(procedencia_anterior, dict):
                guia.contenido['procedencia_simulacion'] = deepcopy(procedencia_anterior)
            elif es_nueva and procedencia_plantilla:
                guia.contenido['procedencia_simulacion'] = deepcopy(procedencia_plantilla)
            firmas = firmas_desde_post(request.POST) or firmas_previas
            if firmas:
                guia.contenido['firmas'] = normalizar_firmas(firmas)
            guia.permite_descarga = form.cleaned_data.get('permite_descarga', False)
            guia.solicita_publicacion = form.cleaned_data.get('solicita_publicacion', False)
            if accion != 'enviar_revision' and guia.pk and guia.estado_publicacion == 'revision':
                # Corregir una guia ya enviada rehace la huella de elaboracion:
                # el revisor lee el documento vigente y su firma corresponde.
                guia.contenido = firmar_contenido_guia(
                    guia.contenido,
                    guia=guia,
                    usuario=request.user,
                    reserva=form.cleaned_data.get('reserva_referencia'),
                )
            if accion == 'enviar_revision':
                faltantes = guia.secciones_faltantes()
                if faltantes:
                    error_flujo = 'Completa antes de enviar: ' + ', '.join(faltantes) + '.'
                    guia.estado_publicacion = 'borrador'
                else:
                    if guia.pk is None:
                        # La huella incorpora el identificador definitivo del
                        # documento; por eso se reserva antes de firmar.
                        guia.full_clean()
                        guia.save()
                    guia.contenido = firmar_contenido_guia(
                        guia.contenido,
                        guia=guia,
                        usuario=request.user,
                        reserva=form.cleaned_data.get('reserva_referencia'),
                    )
                    guia.estado_publicacion = 'revision'
                    guia.observaciones_revision = ''
                    actividad.estado_publicacion = 'revision'
                    actividad.save(update_fields=['estado_publicacion', 'actualizado_en'])
            guia.full_clean()
            guia.save()
            adjuntar_figuras_borrador(guia, token_borrador, request.user)
            titulos_figuras = request.POST.getlist('guia_imagenes_titulos') or [
                linea.strip()
                for linea in request.POST.get('guia_imagenes_titulos_texto', '').splitlines()
            ]
            guardar_imagenes_guia(
                guia,
                request.FILES.getlist('guia_imagenes'),
                titulos_figuras,
                eliminar=request.POST.getlist('eliminar_imagenes'),
            )
            registrar_auditoria(
                request,
                unidad=unidad,
                accion=(
                    'enviar'
                    if accion == 'enviar_revision' and not error_flujo
                    else ('crear' if es_nueva else 'actualizar')
                ),
                objeto=guia,
                descripcion=(
                    f'Guía v{guia.numero_version} enviada a revisión.'
                    if accion == 'enviar_revision' and not error_flujo
                    else f'Guía v{guia.numero_version} guardada como borrador.'
                ),
                anteriores=anteriores,
                nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
            )
        if not error_flujo:
            destino = reverse('ver_guia_actividad', args=[guia.pk])
            return redirect(f'{destino}?guardado=1')

    reserva_fuente = _reserva_fuente_visible(
        guia,
        request.user,
        operador=operador,
    )
    contenido_vista = _contenido_para_vista(guia) if guia else {}
    if guia is None and inicial.get('formato_contenido') == FORMATO_HTML:
        # El mismo documento visual y saneado que se usa tras guardar; el
        # objeto en memoria no crea actividad, guía, reserva ni auditoría.
        contenido_inicial = deepcopy(inicial)
        contenido_inicial['bibliografia'] = normalizar_bibliografia(inicial.get('bibliografia', ''))
        contenido_inicial['materiales_complementarios'] = normalizar_materiales_complementarios(inicial.get('materiales_complementarios', ''))
        contenido_vista = _contenido_para_vista(GuiaActividadReserva(
            actividad=CatalogoActividadReserva(unidad=unidad),
            contenido=contenido_inicial, subido_por=request.user,
        ), figuras=[])
    if request.method == 'POST' and not form.is_valid() or error_flujo:
        # Se conserva lo escrito: las zonas se rellenan con lo enviado.
        zonas = {
            clave: sanear(
                request.POST.get(clave, ''), POLITICA_POR_CAMPO.get(clave, 'rico'),
                form.figuras_permitidas,
            )[0]
            for clave in CAMPOS_RICOS
        }
        zonas = {
            clave: DocumentoHtml(zonas, figuras_de_guia(guia) if guia else []).html(clave, edicion=True)
            for clave in CAMPOS_RICOS
        }
    elif guia or contenido_vista:
        zonas = _zonas_para_editor(guia, contenido_vista)
    else:
        zonas = {clave: '' for clave in CAMPOS_RICOS}
    if not token_borrador:
        token_borrador = uuid4().hex
    return render(request, 'portal/pages/unidades/guias/editor.html', {
        'unidad': unidad,
        'guia': guia,
        'form': form,
        'datos_autocompletado': form.autocompletado,
        'error_flujo': error_flujo,
        'reserva_fuente': reserva_fuente,
        'contenido_automatico': (
            contenido_vista if reserva_fuente else {}
        ),
        'contenido': contenido_vista,
        'zonas': zonas,
        'figuras_json': _figuras_json(figuras_de_guia(guia) if guia else []),
        'token_borrador': token_borrador,
        'version_base': _version_de(guia),
        'referencias': contenido_vista.get('bibliografia', []),
        'materiales_complementarios': contenido_vista.get('materiales_complementarios', []),
        'procedencia_simulacion': procedencia_plantilla or contenido_vista.get('procedencia_simulacion'),
        'procesos_unidad': _procesos_para_guia(unidad),
        'url_subida_figura': reverse('subir_figura_guia'),
        'url_guardado_contenido': reverse('guardar_contenido_guia', args=[guia.pk]) if guia else '',
        # La politica institucional se muestra aparte de las precauciones que
        # escribe el autor; el apartado almacenado ya contiene ambas.
        'politicas_unidad': (
            politicas_guia_desde_reserva(reserva_fuente) if reserva_fuente else {}
        ),
        'imagenes_guia': list(guia.imagenes.all()) if guia and guia.pk else [],
        'reserva_recien_creada': bool(
            reserva_fuente and request.GET.get('reserva_creada') == '1'
        ),
        'comprobante_url': (
            reverse('comprobante_reserva', args=[reserva_fuente.pk])
            if reserva_fuente else ''
        ),
        'page_title': 'Editar guía de práctica' if guia else 'Nueva guía de práctica',
        'page_key': 'editor-guia-practica',
    })


# El expediente de la reserva incrusta la guía (PDF y documento) en su propio
# lector, así que la vista debe admitir el encuadre desde el mismo dominio.
@xframe_options_sameorigin
@require_http_methods(['GET'])
def ver_guia_actividad(request, guia_id):
    guia = get_object_or_404(
        GuiaActividadReserva.objects.select_related(
            'actividad', 'actividad__creado_por', 'actividad__unidad',
            'revisado_por', 'aprobado_por',
        ).prefetch_related('actividad__participantes_autorizados'),
        pk=guia_id, activo=True,
    )
    if not _puede_ver_guia(request.user, guia):
        raise Http404('Guía no disponible')

    solicita_descarga = request.GET.get('download') == '1'
    solicita_vista_pdf = request.GET.get('preview') == 'pdf'
    descarga_interna = request.user.is_authenticated and request.user.is_active and (
        guia.actividad.creado_por_id == request.user.pk
        or _puede_operar_guias(request.user, guia.actividad.unidad)
    )
    # El autor y el personal de la unidad descargan cualquier version (el PDF
    # indica si aun no esta aprobada); el resto, solo el PDF aprobado.
    descarga_publica = guia.permite_descarga and guia.estado_publicacion == 'publicada'
    if solicita_descarga and not descarga_publica and not descarga_interna:
        return HttpResponseForbidden(
            'La descarga estará disponible cuando la guía sea aprobada y la unidad '
            'la habilite; mientras tanto puedes consultarla en la vista HTML.'
        )

    if not guia.es_estructurada:
        try:
            archivo = guia.archivo.open('rb')
        except (FileNotFoundError, OSError, ValueError) as error:
            raise Http404('El archivo de la guía no está disponible') from error
        registrar_auditoria(
            request,
            unidad=guia.actividad.unidad,
            accion='descargar' if solicita_descarga else 'consultar',
            objeto=guia,
            descripcion=(
                'PDF de guía descargado.' if solicita_descarga else 'PDF de guía visualizado.'
            ),
            nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
        )
        return FileResponse(
            archivo,
            content_type='application/pdf',
            as_attachment=solicita_descarga,
            filename=guia.nombre_original or f'guia-{guia.pk}.pdf',
        )

    if (solicita_descarga or solicita_vista_pdf) and guia.archivo_firmado:
        # La versión firmada con certificado electrónico es la oficial: se
        # descarga y también se lee en el visor, en lugar de la regenerada.
        try:
            archivo = guia.archivo_firmado.open('rb')
        except (FileNotFoundError, OSError, ValueError) as error:
            raise Http404('La versión firmada no está disponible') from error
        registrar_auditoria(
            request,
            unidad=guia.actividad.unidad,
            accion='descargar' if solicita_descarga else 'consultar',
            objeto=guia,
            descripcion=(
                f'Guía v{guia.numero_version} descargada en su versión firmada.'
                if solicita_descarga
                else f'Guía v{guia.numero_version} consultada en su versión firmada.'
            ),
            nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
        )
        return FileResponse(
            archivo,
            content_type='application/pdf',
            as_attachment=solicita_descarga,
            filename=f'guia-practica-{guia.pk}-v{guia.numero_version}-firmada.pdf',
        )

    if solicita_descarga or solicita_vista_pdf:
        contenido = construir_pdf_guia(guia)
        registrar_auditoria(
            request,
            unidad=guia.actividad.unidad,
            accion='descargar' if solicita_descarga else 'consultar',
            objeto=guia,
            descripcion=(
                f'Guía estructurada v{guia.numero_version} descargada en PDF.'
                if solicita_descarga
                else f'Guía estructurada v{guia.numero_version} visualizada en PDF.'
            ),
            nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
        )
        respuesta = HttpResponse(contenido, content_type='application/pdf')
        nombre = f'guia-practica-{guia.pk}-v{guia.numero_version}.pdf'
        disposicion = 'attachment' if solicita_descarga else 'inline'
        respuesta['Content-Disposition'] = f'{disposicion}; filename="{nombre}"'
        return respuesta

    unidad = guia.actividad.unidad
    es_operador = _puede_operar_guias(request.user, unidad)
    reserva_fuente = _reserva_fuente_visible(
        guia,
        request.user,
        operador=es_operador,
    )
    # Quien es titular de la reserva firma desde su expediente; aquí no se
    # repite el formulario.
    reserva_propia = (
        reserva_fuente
        if reserva_fuente and reserva_fuente.usuario_id == request.user.pk
        else None
    )
    contenido_vista = _contenido_para_vista(guia)
    firma_elaborador = contenido_vista.get('firma_elaborador') or {}
    # `fragmento=1` entrega solo el documento para leerlo dentro del expediente.
    plantilla = (
        'portal/pages/unidades/guias/fragmento.html'
        if request.GET.get('fragmento') == '1'
        else 'portal/pages/unidades/guias/vista.html'
    )
    return render(request, plantilla, {
        'guia': guia,
        'unidad': unidad,
        'contenido': contenido_vista,
        'zonas': contenido_vista.get('zonas', {}),
        'firma_elaborador': firma_elaborador,
        'firma_elaborador_fecha': _momento_firma_local(firma_elaborador),
        'firma_elaborador_valida': verificar_firma_elaborador(guia),
        'puede_editar': puede_editar_guia(request.user, guia),
        'puede_descargar': descarga_publica or descarga_interna,
        'puede_cargar_firmada': (
            guia.estado_publicacion in {'revision', 'publicada'}
            and _puede_cargar_firmada(request.user, guia)
            and reserva_propia is None
        ),
        'reserva_para_firmar': reserva_propia,
        'es_operador': es_operador,
        'puede_versionar': (
            es_operador
            and guia.estado_publicacion == 'publicada'
            and _version_en_trabajo(guia.actividad, sesion=guia.sesion) is None
        ),
        'version_en_trabajo': _version_en_trabajo(guia.actividad, sesion=guia.sesion),
        'puede_archivar': es_operador,
        'guardado': request.GET.get('guardado') == '1',
        'reserva_fuente': reserva_fuente,
        'comprobante_url': (
            reverse('comprobante_reserva', args=[reserva_fuente.pk])
            if reserva_fuente else ''
        ),
        'page_title': guia.titulo,
        'page_key': 'vista-guia-practica',
    })


@login_required
@require_POST
def cambiar_estado_guia_practica(request, guia_id):
    guia = get_object_or_404(
        GuiaActividadReserva.objects.select_related('actividad', 'actividad__unidad'),
        pk=guia_id, es_estructurada=True, activo=True,
    )
    if not _puede_operar_guias(request.user, guia.actividad.unidad):
        raise Http404('Guía no disponible')
    accion = request.POST.get('accion')
    observacion = request.POST.get('observacion', '').strip()
    if accion not in {'aprobar', 'rechazar', 'nueva_version', 'archivar'}:
        return redirect('ver_guia_actividad', guia_id=guia.pk)
    if accion == 'rechazar' and not observacion:
        return redirect('ver_guia_actividad', guia_id=guia.pk)

    with transaction.atomic():
        guia = GuiaActividadReserva.objects.select_for_update().get(pk=guia.pk)
        anteriores = instantanea(guia, GUIA_FIELDS_AUDIT)
        respaldos_aprobados = []
        planes_aprobados = []
        if accion == 'nueva_version' and guia.estado_publicacion == 'publicada':
            abierta = _version_en_trabajo(guia.actividad, sesion=guia.sesion)
            if abierta is not None:
                messages.info(
                    request,
                    f'La version {abierta.numero_version} ya esta en trabajo; '
                    'completa o archiva esa antes de crear otra.',
                )
                return redirect(
                    'editar_guia_practica',
                    slug=guia.actividad.unidad.slug,
                    guia_id=abierta.pk,
                )
            ultima_version = (
                GuiaActividadReserva.objects.filter(
                    actividad=guia.actividad,
                    es_estructurada=True,
                ).aggregate(maxima=Max('numero_version'))['maxima']
                or 0
            )
            nueva = GuiaActividadReserva(
                actividad=guia.actividad,
                titulo=guia.titulo,
                descripcion=guia.descripcion,
                codigo_guia=guia.codigo_guia,
                numero_version=ultima_version + 1,
                es_estructurada=True,
                es_vigente=False,
                contenido=deepcopy(guia.contenido or {}),
                visibilidad='participantes',
                estado_publicacion='borrador',
                permite_descarga=guia.permite_descarga,
                solicita_publicacion=guia.solicita_publicacion,
                activo=True,
                orden=guia.orden,
                alcance=guia.alcance,
                guia_general=guia.guia_general,
                sesion=guia.sesion,
                subido_por=request.user,
            )
            nueva.contenido.pop('firma_elaborador', None)
            nueva.full_clean()
            nueva.save()
            registrar_auditoria(
                request,
                unidad=guia.actividad.unidad,
                accion='crear',
                objeto=nueva,
                descripcion=(
                    f'Creada versión {nueva.numero_version} desde la versión '
                    f'{guia.numero_version}; la versión publicada continúa vigente.'
                ),
                anteriores=anteriores,
                nuevos=instantanea(nueva, GUIA_FIELDS_AUDIT),
            )
            return redirect(
                'editar_guia_practica',
                slug=guia.actividad.unidad.slug,
                guia_id=nueva.pk,
            )

        if accion == 'archivar':
            guia.estado_publicacion = 'archivada'
            guia.es_vigente = False
            guia.activo = False
            guia.revisado_por = request.user
            guia.revisado_en = timezone.now()
            guia.observaciones_revision = observacion or 'Versión archivada por el responsable de la unidad.'
            guia.save()
            if not GuiaActividadReserva.objects.filter(
                actividad=guia.actividad,
                es_estructurada=True,
                es_vigente=True,
                activo=True,
            ).exists():
                guia.actividad.estado_publicacion = 'borrador'
                guia.actividad.visibilidad = 'privada'
                guia.actividad.save(
                    update_fields=['estado_publicacion', 'visibilidad', 'actualizado_en']
                )
            registrar_auditoria(
                request,
                unidad=guia.actividad.unidad,
                accion='archivar',
                objeto=guia,
                descripcion=f'Guía v{guia.numero_version} archivada lógicamente.',
                anteriores=anteriores,
                nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
            )
            return redirect('lista_guias_practica', slug=guia.actividad.unidad.slug)

        if guia.estado_publicacion != 'revision':
            return redirect('ver_guia_actividad', guia_id=guia.pk)

        guia.revisado_por = request.user
        guia.revisado_en = timezone.now()
        accion_auditoria = 'observar'
        descripcion_auditoria = f'Revisión registrada para la guía v{guia.numero_version}.'
        if accion == 'aprobar':
            faltantes = guia.secciones_faltantes()
            if faltantes:
                guia.observaciones_revision = 'No se aprobó. Faltan: ' + ', '.join(faltantes)
            else:
                GuiaActividadReserva.objects.filter(
                    actividad=guia.actividad, es_estructurada=True, es_vigente=True,
                    sesion=guia.sesion,
                ).exclude(pk=guia.pk).update(es_vigente=False)
                guia.estado_publicacion = 'publicada'
                guia.es_vigente = True
                guia.aprobado_por = request.user
                guia.aprobado_en = timezone.now()
                guia.observaciones_revision = observacion
                guia.visibilidad = 'unidad' if guia.solicita_publicacion else 'participantes'
                guia.actividad.estado_publicacion = 'publicado'
                guia.actividad.visibilidad = (
                    'unidad' if guia.solicita_publicacion else 'participantes'
                )
                guia.actividad.save(
                    update_fields=['estado_publicacion', 'visibilidad', 'actualizado_en']
                )
                # Los PDF de respaldo de la misma actividad no tienen revision
                # propia: la aprobacion de la version estructurada los resuelve
                # con la visibilidad que solicitaron.
                pdfs_pendientes = GuiaActividadReserva.objects.filter(
                    actividad=guia.actividad,
                    es_estructurada=False,
                    activo=True,
                    estado_publicacion='revision',
                )
                for respaldo in pdfs_pendientes:
                    respaldo.estado_publicacion = 'publicada'
                    respaldo.visibilidad = (
                        'unidad' if respaldo.solicita_publicacion else 'participantes'
                    )
                    respaldo.revisado_por = request.user
                    respaldo.revisado_en = timezone.now()
                    respaldo.aprobado_por = request.user
                    respaldo.aprobado_en = timezone.now()
                    respaldo.save(update_fields=[
                        'estado_publicacion', 'visibilidad', 'revisado_por',
                        'revisado_en', 'aprobado_por', 'aprobado_en', 'actualizado_en',
                    ])
                    respaldos_aprobados.append(respaldo)
                accion_auditoria = 'aprobar'
                descripcion_auditoria = f'Guía v{guia.numero_version} aprobada y publicada.'
        elif accion == 'rechazar' and observacion:
            guia.estado_publicacion = 'rechazada'
            guia.es_vigente = False
            guia.observaciones_revision = observacion
            guia.actividad.estado_publicacion = 'borrador'
            guia.actividad.save(update_fields=['estado_publicacion', 'actualizado_en'])
            accion_auditoria = 'observar'
            descripcion_auditoria = f'Guía v{guia.numero_version} devuelta con observaciones.'
        guia.save()
        if accion == 'aprobar' and guia.estado_publicacion == 'publicada':
            # Una planificación puede nacer junto con la reserva mientras la
            # guía todavía es borrador. Al aprobarla se enlaza la versión exacta
            # y queda lista para revisión, sin reescribir la reserva fuente.
            planes_pendientes = PlanificacionPractica.objects.filter(
                actividad=guia.actividad,
                guia__isnull=True,
                requiere_guia=True,
                estado__in={'borrador', 'revision', 'observada'},
            )
            ids_planes = list(planes_pendientes.values_list('pk', flat=True))
            PlanificacionPractica.objects.filter(
                pk__in=ids_planes,
                estado='borrador',
            ).update(
                estado='revision',
                actualizado_en=timezone.now(),
            )
            PlanificacionPractica.objects.filter(
                pk__in=ids_planes,
                estado__in={'borrador', 'revision'},
                reserva__estado__in={'confirmada', 'en_proceso', 'completada'},
            ).update(
                estado='aprobada',
                actualizado_en=timezone.now(),
            )
            PlanificacionPractica.objects.filter(pk__in=ids_planes).update(
                guia=guia,
                actualizado_en=timezone.now(),
            )
            from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
            if es_laboratorio(guia.actividad.unidad):
                # Atribuir únicamente las aprobaciones que acaba de producir
                # esta acción; no completar planes o eventos históricos.
                aprobados = PlanificacionPractica.objects.filter(pk__in=ids_planes, estado='aprobada')
                aprobados.update(revisado_por=request.user, revisado_en=guia.aprobado_en)
                planes_aprobados = list(aprobados)
        evento_aprobacion = registrar_auditoria(
            request,
            unidad=guia.actividad.unidad,
            accion=accion_auditoria,
            objeto=guia,
            descripcion=descripcion_auditoria,
            anteriores=anteriores,
            nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
        )
        if accion_auditoria == 'aprobar':
            from apps.documentos.presentation.aprobacion_tecnica_laboratorios import registrar_aprobacion_tecnica
            registrar_aprobacion_tecnica(guia, request.user, evento=evento_aprobacion)
            from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
            if es_laboratorio(guia.actividad.unidad):
                for aprobado in respaldos_aprobados + planes_aprobados:
                    evento = registrar_auditoria(request, unidad=guia.actividad.unidad,
                        accion='aprobar', objeto=aprobado,
                        descripcion=f'Aprobación técnica vinculada a la guía v{guia.numero_version}.',
                        nuevos={'guia_origen': guia.pk})
                    registrar_aprobacion_tecnica(aprobado, request.user, evento=evento)
    return redirect('ver_guia_actividad', guia_id=guia.pk)


def _texto_pdf(value):
    lines = (
        [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, (list, tuple))
        else [line.strip() for line in str(value or '').splitlines()]
    )
    if not any(lines):
        return 'No aplica'
    formatted = []
    for line in lines:
        if not line:
            formatted.append('<br/>')
            continue
        heading = re.match(r'^#{2,3}\s+(.+)$', line)
        numbered = re.match(r'^(\d+)[.)]\s+(.+)$', line)
        bulleted = re.match(r'^[-*•]\s+(.+)$', line)
        if heading:
            formatted.append(f'<b>{escape(heading.group(1))}</b>')
        elif numbered:
            formatted.append(f'<b>{escape(numbered.group(1))}.</b> {escape(numbered.group(2))}')
        elif bulleted:
            formatted.append(f'&bull; {escape(bulleted.group(1))}')
        elif isinstance(value, (list, tuple)):
            formatted.append(f'&bull; {escape(line)}')
        else:
            formatted.append(escape(line))
    return '<br/>'.join(formatted)


def _texto_procedimiento_pdf(value, formato='numerado'):
    """Presenta el procedimiento sin duplicar números o viñetas escritos por el autor."""
    if isinstance(value, str):
        items = [linea.strip() for linea in value.splitlines() if linea.strip()]
    else:
        items = [str(item).strip() for item in (value or []) if str(item).strip()]
    if not items:
        return 'No registrado'
    items = [
        re.sub(r'^\s*(?:\d+[.)]|[-*\u2022])\s*', '', item).strip()
        for item in items
    ]
    if formato == 'parrafos':
        return '<br/><br/>'.join(escape(item) for item in items)
    if formato == 'vinetas':
        return '<br/>'.join(f'&bull; {escape(item)}' for item in items)
    return '<br/>'.join(
        f'<b>{indice}.</b> {escape(item)}' for indice, item in enumerate(items, 1)
    )


def _texto_bibliografia_pdf(contenido):
    """Referencias numeradas [n] en estilo IEEE."""
    referencias = contenido.get('bibliografia') or []
    if isinstance(referencias, str):
        referencias = [linea.strip() for linea in referencias.splitlines() if linea.strip()]
    lineas = [f'[{indice}] {escape(str(item))}' for indice, item in enumerate(referencias, 1)]
    return '<br/>'.join(lineas) if lineas else 'No registrada'


def _texto_cronograma_pdf(contenido):
    """El cronograma de la guía general: una línea por sesión."""
    lineas = []
    for fila in contenido.get('cronograma') or []:
        if not isinstance(fila, dict):
            continue
        partes = [f"Sesión {fila.get('sesion', '')}", str(fila.get('fecha_texto') or fila.get('fecha') or '')]
        if fila.get('semana'):
            partes.append(f"semana {fila['semana']}")
        partes.append(str(fila.get('tema') or 'Tema por definir'))
        if fila.get('proceso'):
            partes.append(f"proceso: {fila['proceso']}")
        extras = [str(fila.get('ejercicios') or '').strip(), ', '.join(fila.get('software') or [])]
        partes.extend(parte for parte in extras if parte)
        lineas.append('&bull; ' + escape(' · '.join(partes)))
    return '<br/>'.join(lineas) if lineas else 'Sin cronograma'


def _texto_materiales_pdf(contenido):
    """Materiales complementarios con enlace, uno por línea."""
    materiales = [
        item for item in (contenido.get('materiales_complementarios') or [])
        if isinstance(item, dict)
    ]
    lineas = []
    for item in materiales:
        titulo = escape(str(item.get('titulo') or item.get('url') or ''))
        url = str(item.get('url') or '')
        if url:
            lineas.append(f'&bull; <a href="{escape(url)}" color="#1a5b3f">{titulo}</a> ({escape(url)})')
        else:
            lineas.append(f'&bull; {titulo}')
    return '<br/>'.join(lineas) if lineas else 'No registrados'


def _nombre_usuario_pdf(usuario):
    if not usuario:
        return ''
    return usuario.get_full_name() or usuario.get_username()


def construir_pdf_guia(guia, *, figuras=None):
    """Genera el FT04 desde los mismos datos normalizados de la vista HTML."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
        TableStyle,
    )

    encabezado_pagina, NumberedCanvas, medidas = marco_institucional(
        formato='Guía de práctica',
        metadatos=(
            'Código: UPEC-P10-S01-FT04',
            'Revisión: 01',
            f'Versión de guía: {guia.numero_version}',
        ),
        pie='Guías de práctica',
    )
    tinta = medidas['colores']
    green, dark = tinta['primario'], tinta['oscuro']
    pale, line, gray = tinta['suave'], tinta['linea'], tinta['tenue']
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=medidas['pagesize'],
        rightMargin=medidas['margen'],
        leftMargin=medidas['margen'],
        topMargin=medidas['margen_superior'],
        bottomMargin=medidas['margen_inferior'],
        title=guia.titulo,
        author=identidad_actual()[1].nombre,
        subject='UPEC-P10-S01-FT04 · Formato guía de práctica',
    )
    styles = hoja_de_estilos()
    body = ParagraphStyle(
        'GuideBody', parent=styles['BodyText'], fontName=fuentes_documento()[0],
        fontSize=8.2, leading=11.2, textColor=dark, spaceAfter=3,
        alignment=TA_JUSTIFY,
    )
    small = ParagraphStyle('GuideSmall', parent=body, fontSize=7.1, leading=9.2)
    label = ParagraphStyle(
        'GuideLabel', parent=small, fontName=fuentes_documento()[1],
        fontSize=6.7, leading=8.2, textColor=green,
    )
    label_firma = ParagraphStyle(
        'FirmaEtiqueta',
        parent=label,
        alignment=TA_CENTER,
        textColor=green,
    )
    firma_nombre = ParagraphStyle(
        'FirmaNombre',
        parent=body,
        alignment=TA_CENTER,
        fontSize=8.5,
        leading=11,
    )
    firma_dato = ParagraphStyle(
        'FirmaDato',
        parent=body,
        alignment=TA_CENTER,
        fontSize=7,
        leading=9,
        textColor=gray,
    )
    title = ParagraphStyle(
        'GuideTitle', parent=body, fontName=fuentes_documento()[1], fontSize=12.5,
        leading=15, textColor=green, alignment=TA_CENTER, spaceAfter=4,
    )
    caption = ParagraphStyle(
        'GuideCaption', parent=small, alignment=TA_CENTER, textColor=gray, spaceBefore=2,
    )
    section_text = ParagraphStyle(
        'GuideSection', parent=body, fontName=fuentes_documento()[1], fontSize=8.4,
        leading=10.5, textColor=colors.white, alignment=TA_LEFT,
    )
    c = _contenido_para_vista(guia, figuras)

    def seccion(numero, texto):
        tabla = Table(
            [[Paragraph(f'{numero}. {escape(texto)}', section_text)]],
            splitInRow=1, colWidths=[182 * mm],
        )
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), green),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        # El titulo nunca queda solo al pie de una pagina; el contenido fluye
        # sin dejar hojas en blanco.
        return _pegado(tabla)

    def _pegado(flowable):
        flowable.keepWithNext = 1
        return flowable

    def bloque(numero, texto, valor, renderer=_texto_pdf):
        contenido = Table(
            [[Paragraph(renderer(valor), body)]],
            splitInRow=1, colWidths=[182 * mm],
            style=TableStyle([
                ('BOX', (0, 0), (-1, -1), .45, line),
                ('LEFTPADDING', (0, 0), (-1, -1), 7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]),
        )
        return [seccion(numero, texto), contenido, Spacer(1, 2.2 * mm)]

    def flowables_enriquecidos(bloques):
        """Parrafos, listas, tablas y figuras de una seccion, en flujo libre."""
        elementos = []
        for item in bloques:
            tipo = item.get('tipo')
            if tipo == 'parrafo':
                elementos.append(Paragraph(escape(item['texto']), body))
            elif tipo == 'subtitulo':
                elementos.append(Paragraph(f'<b>{escape(item["texto"])}</b>', body))
            elif tipo == 'lista':
                lineas = [
                    f'<b>{indice}.</b> {escape(texto)}' if item['ordenada'] else f'&bull; {escape(texto)}'
                    for indice, texto in enumerate(item['items'], 1)
                ]
                elementos.append(Paragraph('<br/>'.join(lineas), body))
            elif tipo == 'tabla':
                filas = item['filas']
                ancho = max(len(fila) for fila in filas)
                datos = [
                    [Paragraph(escape(celda), small) for celda in (list(fila) + [''] * (ancho - len(fila)))]
                    for fila in filas
                ]
                tabla = Table(datos, splitInRow=1, colWidths=[176 * mm / ancho] * ancho, repeatRows=1)
                tabla.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), .4, line),
                    ('BACKGROUND', (0, 0), (-1, 0), pale),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                elementos.extend([Spacer(1, 1.5 * mm), tabla, Spacer(1, 1.5 * mm)])
            elif tipo == 'imagen':
                figura = resolver_figura(item['fuente'], c.get('figuras'))
                texto = item.get('texto') or (figura or {}).get('titulo') or ''
                ruta = (figura or {}).get('ruta')
                dibujada = None
                if ruta and Path(ruta).exists():
                    try:
                        ancho_px, alto_px = ImageReader(ruta).getSize()
                        escala = min(120 * mm / ancho_px, 85 * mm / alto_px)
                        dibujada = Image(ruta, width=ancho_px * escala, height=alto_px * escala)
                        dibujada.hAlign = 'CENTER'
                    except Exception:  # noqa: BLE001 - un archivo dañado no debe tumbar el PDF
                        dibujada = None
                if dibujada is None:
                    elementos.append(Paragraph(
                        f'<i>[{escape(texto or item["fuente"])}: imagen no disponible]</i>', small,
                    ))
                else:
                    elementos.append(KeepTogether([
                        Spacer(1, 1.5 * mm), dibujada, Paragraph(escape(texto), caption),
                    ]))
        return elementos

    def seccion_enriquecida(numero, texto, valor):
        """Con tablas o figuras la seccion fluye sin caja para poder saltar de pagina."""
        bloques = bloques_enriquecidos(valor)
        if not tiene_adjuntos(bloques):
            return bloque(numero, texto, valor)
        return [seccion(numero, texto), _pegado(Spacer(1, 1.5 * mm)), *flowables_enriquecidos(bloques), Spacer(1, 2.2 * mm)]

    # ---- Formato HTML acotado (editor visual): mismos bloques que la vista.
    documento = c.get('documento') if c.get('es_html') else None
    limites_figura = {'pequena': (60, 55), 'mediana': (120, 85), 'ancha': (176, 120)}

    def lineas_lista_html(item_lista, nivel=0):
        sangria = '&nbsp;' * 4 * nivel
        lineas = []
        for indice, item in enumerate(item_lista['items'], 1):
            prefijo = f'<b>{indice}.</b> ' if item_lista['ordenada'] else '&bull; '
            lineas.append(f'{sangria}{prefijo}{item["html"]}')
            for sub in item.get('sub', []):
                lineas.extend(lineas_lista_html(sub, nivel + 1))
        return lineas

    def markup_html(bloques):
        """Bloques sin tablas ni figuras → una sola cadena para Paragraph."""
        lineas = []
        for item in bloques:
            tipo = item['tipo']
            if tipo == 'parrafo':
                lineas.append(item['html'] or '&nbsp;')
            elif tipo == 'subtitulo':
                lineas.append(f'<b>{item["html"]}</b>')
            elif tipo == 'subapartado':
                lineas.append(f'<b><i>{item["html"]}</i></b>')
            elif tipo == 'lista':
                lineas.extend(lineas_lista_html(item))
            elif tipo == 'tabla':
                lineas.append(f'<b>{escape(item["titulo"])}</b>')
                lineas.extend(' | '.join(fila) for fila in item['filas'])
            elif tipo == 'imagen':
                lineas.append(f'<i>[{escape(item["titulo"])}]</i>')
        return '<br/>'.join(lineas) or 'No aplica'

    def flowables_html(bloques):
        elementos = []
        for item in bloques:
            tipo = item['tipo']
            if tipo == 'parrafo':
                elementos.append(Paragraph(item['html'] or '&nbsp;', body))
            elif tipo == 'subtitulo':
                elementos.append(Paragraph(f'<b>{item["html"]}</b>', body))
            elif tipo == 'subapartado':
                elementos.append(Paragraph(f'<b><i>{item["html"]}</i></b>', body))
            elif tipo == 'lista':
                elementos.append(Paragraph('<br/>'.join(lineas_lista_html(item)), body))
            elif tipo == 'tabla':
                filas = item['filas'] or [['']]
                ancho = max(len(fila) for fila in filas)
                datos = [
                    [Paragraph(celda, small) for celda in (list(fila) + [''] * (ancho - len(fila)))]
                    for fila in filas
                ]
                tabla = Table(datos, splitInRow=1, colWidths=[176 * mm / ancho] * ancho, repeatRows=1 if item['cabecera'] else 0)
                estilo = [
                    ('GRID', (0, 0), (-1, -1), .4, line),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]
                if item['cabecera']:
                    estilo.append(('BACKGROUND', (0, 0), (-1, 0), pale))
                tabla.setStyle(TableStyle(estilo))
                # El titulo acompaña a la primera fila; la tabla puede continuar en otra pagina.
                elementos.extend([
                    Spacer(1, 1.5 * mm),
                    KeepTogether([Paragraph(escape(item['titulo']), caption), Spacer(1, 1 * mm)]),
                    tabla, Spacer(1, 1.5 * mm),
                ])
            elif tipo == 'imagen':
                ruta_imagen = item.get('ruta')
                dibujada = None
                if ruta_imagen and Path(ruta_imagen).exists():
                    try:
                        ancho_px, alto_px = ImageReader(ruta_imagen).getSize()
                        max_ancho, max_alto = limites_figura.get(item['tamano'], limites_figura['mediana'])
                        escala = min(max_ancho * mm / ancho_px, max_alto * mm / alto_px)
                        dibujada = Image(ruta_imagen, width=ancho_px * escala, height=alto_px * escala)
                        dibujada.hAlign = 'CENTER'
                    except Exception:  # noqa: BLE001 - un archivo dañado no debe tumbar el PDF
                        dibujada = None
                if dibujada is None:
                    elementos.append(Paragraph(f'<i>[{escape(item["titulo"])}: imagen no disponible]</i>', small))
                else:
                    elementos.append(KeepTogether([
                        Spacer(1, 1.5 * mm), dibujada, Paragraph(escape(item['titulo']), caption),
                    ]))
            elif tipo == 'paso':
                elementos.extend(flowables_html(item['bloques']))
        return elementos

    def seccion_html(numero, texto, clave, *, prefijo=''):
        """Apartado del editor visual: en caja si no tiene tablas ni figuras."""
        bloques = documento.bloques(clave)
        if not bloques and not prefijo:
            return bloque(numero, texto, None, renderer=lambda _valor: 'No aplica')
        if not documento.tiene_adjuntos(clave):
            cuerpo = markup_html(bloques) if bloques else ''
            return bloque(numero, texto, None, renderer=lambda _valor: '<br/>'.join(
                parte for parte in (prefijo, cuerpo) if parte
            ) or 'No aplica')
        elementos = [seccion(numero, texto), _pegado(Spacer(1, 1.5 * mm))]
        if prefijo:
            elementos.append(Paragraph(prefijo, body))
        elementos.extend(flowables_html(bloques))
        elementos.append(Spacer(1, 2.2 * mm))
        return elementos

    def seccion_procedimiento_html():
        formato = c.get('formato_procedimiento', 'numerado')
        bloques = documento.bloques('procedimiento')
        if formato == 'parrafos' or not any(item['tipo'] == 'paso' for item in bloques):
            return seccion_html('7', 'Procedimiento', 'procedimiento')
        pasos = [item for item in bloques if item['tipo'] == 'paso']
        if not documento.tiene_adjuntos('procedimiento'):
            lineas = []
            for numero, paso in enumerate(pasos, 1):
                prefijo = '&bull; ' if formato == 'vinetas' else f'<b>{numero}.</b> '
                lineas.append(prefijo + markup_html(paso['bloques']).replace('<br/>', '<br/>&nbsp;&nbsp;&nbsp;&nbsp;'))
            return bloque('7', 'Procedimiento', None, renderer=lambda _valor: '<br/>'.join(lineas) or 'No registrado')
        elementos = [seccion('7', 'Procedimiento'), _pegado(Spacer(1, 1.5 * mm))]
        for numero, paso in enumerate(pasos, 1):
            prefijo = '&bull; ' if formato == 'vinetas' else f'<b>{numero}.</b> '
            cuerpo = list(paso['bloques'])
            if cuerpo and cuerpo[0]['tipo'] == 'parrafo':
                elementos.append(Paragraph(prefijo + (cuerpo[0]['html'] or ''), body))
                cuerpo = cuerpo[1:]
            else:
                elementos.append(Paragraph(prefijo.strip(), body))
            elementos.extend(flowables_html(cuerpo))
        elementos.append(Spacer(1, 2.2 * mm))
        return elementos

    def seccion_procedimiento():
        formato = c.get('formato_procedimiento', 'numerado')
        pasos = pasos_procedimiento(c.get('procedimiento'), formato)
        if not tiene_adjuntos(pasos):
            return bloque(
                '7',
                'Procedimiento',
                c.get('procedimiento'),
                renderer=lambda valor: _texto_procedimiento_pdf(valor, formato),
            )
        elementos = []
        if formato == 'parrafos':
            elementos = flowables_enriquecidos(pasos)
        else:
            numero = 0
            for paso in pasos:
                if paso['texto']:
                    numero += 1
                    prefijo = '&bull; ' if formato == 'vinetas' else f'<b>{numero}.</b> '
                    elementos.append(Paragraph(f'{prefijo}{escape(paso["texto"])}', body))
                elementos.extend(flowables_enriquecidos(paso['adjuntos']))
        return [seccion('7', 'Procedimiento'), _pegado(Spacer(1, 1.5 * mm)), *elementos, Spacer(1, 2.2 * mm)]

    story = [Paragraph(_texto_pdf(guia.titulo), title)]
    if guia.estado_publicacion != 'publicada':
        story.append(Paragraph(
            f'ESTADO DOCUMENTAL: {escape(guia.get_estado_publicacion_display().upper())}',
            ParagraphStyle(
                'GuideDraft', parent=small, fontName=fuentes_documento()[1],
                textColor=colors.HexColor('#896A14'), alignment=TA_CENTER, spaceAfter=4,
            ),
        ))

    story.append(seccion('1', 'Datos generales'))
    generales = [
        ('CÓD. GUÍA', guia.codigo_guia or guia.actividad.codigo or 'Sin código'),
        ('ASIGNATURA', c.get('asignatura')),
        ('CARRERA / SEMESTRE', c.get('carrera_semestre')),
        ('DOCENTE RESPONSABLE', c.get('docente_responsable')),
        ('LABORATORIO', c.get('laboratorio') or guia.actividad.unidad.nombre),
        ('CATEGORÍA DE USO', c.get('categoria_uso')),
        ('DURACIÓN ESTIMADA', c.get('duracion')),
        ('N.º ESTUDIANTES (MÁX. RECOMENDADO)', c.get('maximo_estudiantes')),
    ]
    if c.get('sesion_programada'):
        generales.extend([
            ('SESIÓN PROGRAMADA', c.get('sesion_programada')),
            ('GUÍA GENERAL DEL PERÍODO', c.get('guia_general_codigo') or '—'),
        ])
    celdas = []
    for indice in range(0, len(generales), 2):
        fila = []
        for etiqueta, valor in generales[indice:indice + 2]:
            fila.append([
                Paragraph(escape(etiqueta), label),
                Paragraph(_texto_pdf(valor), small),
            ])
        celdas.append(fila)
    tabla_generales = Table(celdas, splitInRow=1, colWidths=[91 * mm, 91 * mm])
    tabla_generales.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), .55, line),
        ('INNERGRID', (0, 0), (-1, -1), .35, line),
        ('BACKGROUND', (0, 0), (-1, -1), pale),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    if documento is not None:
        story.extend([
            tabla_generales,
            Spacer(1, 2.2 * mm),
            *seccion_html('2', 'Resultado(s) de aprendizaje vinculado(s)', 'resultado_aprendizaje'),
            *seccion_html('3', 'Objetivo(s) de la práctica', 'objetivos'),
            *seccion_html('4', 'Fundamento teórico', 'fundamento_teorico'),
            seccion('5', 'Equipos, software, materiales e insumos requeridos'),
        ])
    else:
        story.extend([
            tabla_generales,
            Spacer(1, 2.2 * mm),
            *bloque('2', 'Resultado(s) de aprendizaje vinculado(s)', c.get('resultado_aprendizaje')),
            *bloque('3', 'Objetivo(s) de la práctica', c.get('objetivos')),
            *seccion_enriquecida('4', 'Fundamento teórico', c.get('fundamento_teorico')),
            seccion('5', 'Equipos, software, materiales e insumos requeridos'),
        ])

    recursos = Table([
        [Paragraph('<b>EQUIPOS</b>', label), Paragraph('<b>SOFTWARE Y LICENCIAS</b>', label), Paragraph('<b>MATERIALES, INSUMOS O REACTIVOS</b>', label)],
        [
            Paragraph(_texto_pdf(c.get('equipos')), small),
            Paragraph(_texto_pdf(c.get('software')), small),
            Paragraph(_texto_pdf(c.get('materiales')), small),
        ],
    ], splitInRow=1, colWidths=[60.66 * mm] * 3, repeatRows=1)
    recursos.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), .55, line),
        ('INNERGRID', (0, 0), (-1, -1), .35, line),
        ('BACKGROUND', (0, 0), (-1, 0), pale),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    if documento is not None:
        politica = '<br/>'.join(
            f'&bull; {escape(item)}' for item in c.get('seguridad_institucional', [])
        )
        story.extend([
            recursos,
            Spacer(1, 2.2 * mm),
            *seccion_html(
                '6', 'Seguridad institucional y precauciones específicas', 'medidas_seguridad',
                prefijo=politica,
            ),
            *seccion_procedimiento_html(),
        ])
        texto_resultados = markup_html(documento.bloques('resultados_esperados'))
        texto_criterios = markup_html(documento.bloques('criterios_evaluacion'))
    else:
        story.extend([
            recursos,
            Spacer(1, 2.2 * mm),
            *bloque('6', 'Seguridad institucional y precauciones específicas', c.get('medidas_seguridad')),
            *seccion_procedimiento(),
        ])
        texto_resultados = _texto_pdf(c.get('resultados_esperados'))
        texto_criterios = _texto_pdf(c.get('criterios_evaluacion'))

    resultados = Table([
        [Paragraph('<b>RESULTADOS ESPERADOS</b>', label), Paragraph('<b>CRITERIO DE EVALUACIÓN</b>', label)],
        [Paragraph(texto_resultados, body), Paragraph(texto_criterios, body)],
    ], splitInRow=1, colWidths=[91 * mm, 91 * mm])
    resultados.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), .55, line),
        ('INNERGRID', (0, 0), (-1, -1), .35, line),
        ('BACKGROUND', (0, 0), (-1, 0), pale),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.extend([
        seccion('8', 'Resultados esperados y criterio de evaluación'),
        resultados,
        Spacer(1, 2.2 * mm),
        *bloque('9', 'Manejo de residuos generados', c.get('manejo_residuos')),
        *bloque('10', 'Materiales complementarios', c, renderer=_texto_materiales_pdf),
        *bloque('11', 'Bibliografía / referencias', c, renderer=_texto_bibliografia_pdf),
        *(bloque('12', 'Cronograma de sesiones del período', c, renderer=_texto_cronograma_pdf) if c.get('cronograma') else []),
    ])

    # Cajetín de firmas: un recuadro por firma, con el espacio reservado para
    # la firma electrónica en QR y centrado en la hoja, sean una o tres.
    activas = [firma for firma in c.get('firmas_lista', []) if firma['activo']] or c.get('firmas_lista', [])[:1]
    ancho_cajetin = 56 * mm
    espacio_firma = Paragraph(
        'Espacio para la firma electrónica (FirmaEC)',
        ParagraphStyle(
            'FirmaEspacio',
            parent=small,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#93A49B'),
            fontSize=6,
            leading=8,
        ),
    )
    cajetines = []
    for firma in activas:
        cajetin = Table(
            [
                [Paragraph(f"<b>{escape(firma['etiqueta'].upper())}</b>", label_firma)],
                [espacio_firma],
                [Paragraph(_texto_pdf(firma['nombre_vista']), firma_nombre)],
                [Paragraph(_texto_pdf(firma['cargo_vista']), firma_dato)],
                [Paragraph(_texto_pdf(firma['estado_vista']), firma_dato)],
                [Paragraph(f"Fecha: {escape(str(firma['fecha_vista']))}", firma_dato)],
            ],
            splitInRow=1, colWidths=[ancho_cajetin],
            rowHeights=[7 * mm, 24 * mm, 8 * mm, 6 * mm, 8 * mm, 6 * mm],
        )
        cajetin.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), .6, green),
            ('LINEBELOW', (0, 0), (0, 0), .35, line),
            ('BACKGROUND', (0, 0), (0, 0), pale),
            ('BOX', (0, 1), (0, 1), .4, line),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        cajetines.append(cajetin)
    firmas = Table(
        [cajetines],
        splitInRow=1, colWidths=[ancho_cajetin + 5 * mm] * len(cajetines),
        hAlign='CENTER',
    )
    firmas.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.extend([Spacer(1, 5 * mm), firmas])

    doc.build(
        story,
        onFirstPage=encabezado_pagina,
        onLaterPages=encabezado_pagina,
        canvasmaker=NumberedCanvas,
    )
    return buffer.getvalue()


@login_required
@require_POST
def subir_figura_guia(request):
    """Imagen cargada desde el editor visual: con guía existente o en borrador.

    Devuelve el identificador estable con el que el contenido la cita. En
    borrador (``borrador``) la imagen queda ligada a esta persona y al token
    hasta que se guarda la guía; las huérfanas se limpian con
    ``limpiar_figuras_guia_huerfanas``.
    """
    archivo = request.FILES.get('imagen')
    if archivo is None:
        return JsonResponse({'success': False, 'error': 'Selecciona una imagen.'}, status=400)
    guia = None
    guia_id = request.POST.get('guia_id', '').strip()
    token = request.POST.get('borrador', '').strip()[:40]
    if guia_id.isdigit():
        guia = get_object_or_404(GuiaActividadReserva, pk=int(guia_id), es_estructurada=True, activo=True)
        if not puede_editar_guia(request.user, guia):
            return JsonResponse({'success': False, 'error': 'No puedes editar esta guía.'}, status=403)
    elif not re.fullmatch(r'[A-Za-z0-9-]{8,40}', token):
        return JsonResponse({'success': False, 'error': 'Falta el borrador al que pertenece la imagen.'}, status=400)
    try:
        figura = guardar_figura(
            archivo, request.POST.get('titulo', ''), usuario=request.user, guia=guia, token=token,
        )
    except ValueError as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)
    return JsonResponse({
        'success': True,
        'figura': {'id': figura.pk, 'url': figura.imagen.url, 'titulo': figura.titulo},
    })


@login_required
@require_POST
def guardar_contenido_guia(request, guia_id):
    """Guardado por apartado desde el editor visual (solo campos autorizados).

    Los datos protegidos (generales, recursos, políticas, firmas) no se
    aceptan aunque vengan en la solicitud. Un guardado sobre una versión más
    reciente se rechaza (409) en lugar de sobrescribirla. Cualquier cambio
    invalida la aceptación electrónica anterior.
    """
    guia = get_object_or_404(
        GuiaActividadReserva.objects.select_related('actividad', 'actividad__unidad'),
        pk=guia_id, es_estructurada=True, activo=True,
    )
    if not puede_editar_guia(request.user, guia):
        return JsonResponse({'success': False, 'error': 'No puedes editar esta guía.'}, status=403)
    try:
        datos = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Solicitud no válida.'}, status=400)
    if not isinstance(datos, dict):
        return JsonResponse({'success': False, 'error': 'Solicitud no válida.'}, status=400)
    campos = datos.get('campos') if isinstance(datos.get('campos'), dict) else {}
    token = str(datos.get('borrador') or '')[:40]
    with transaction.atomic():
        guia = GuiaActividadReserva.objects.select_for_update().get(pk=guia.pk)
        version_base = str(datos.get('version_base') or '')
        if version_base and version_base != _version_de(guia):
            return JsonResponse({
                'success': False,
                'conflicto': True,
                'error': 'Otra persona guardó una versión más reciente de esta guía. Recarga para continuar.',
                'version': _version_de(guia),
            }, status=409)
        anteriores = instantanea(guia, GUIA_FIELDS_AUDIT)
        adjuntar_figuras_borrador(guia, token, request.user)
        permitidas = figuras_permitidas(guia, '', request.user)
        contenido = deepcopy(guia.contenido or {})
        if contenido.get('formato_contenido') != FORMATO_HTML:
            # Primer guardado desde el editor: el resto de apartados de texto
            # se convierten con la misma regla que al abrirlos.
            convertidos = html_desde_legado(_contenido_para_vista(guia), figuras_de_guia(guia))
            for clave, valor in convertidos.items():
                contenido[clave] = valor
            reserva_id = contenido.get('reserva_fuente_id')
            reserva = Reserva.objects.filter(pk=reserva_id).first() if reserva_id else None
            contenido['seguridad_institucional'] = (
                politicas_guia_desde_reserva(reserva)['seguridad'] if reserva else []
            )
            contenido['formato_contenido'] = FORMATO_HTML
        avisos = []
        origen = contenido.get('origen_campos') if isinstance(contenido.get('origen_campos'), dict) else {}
        for clave in CAMPOS_RICOS:
            if clave not in campos:
                continue
            valor = campos[clave] if isinstance(campos[clave], str) else ''
            politica = POLITICA_POR_CAMPO.get(clave, 'rico')
            if clave == 'procedimiento' and datos.get('formato_procedimiento') == 'parrafos':
                politica = 'rico'
            limpio, avisos_campo = sanear(valor, politica, permitidas)
            contenido[clave] = limpio
            origen[clave] = 'manual'
            avisos.extend(f'{clave}: {aviso}' for aviso in avisos_campo)
        contenido['origen_campos'] = origen
        if datos.get('formato_procedimiento') in {'numerado', 'vinetas', 'parrafos'}:
            contenido['formato_procedimiento'] = datos['formato_procedimiento']
        if isinstance(datos.get('firmas'), dict):
            contenido['firmas'] = normalizar_firmas(datos['firmas'])
        contenido.pop('firma_elaborador', None)
        guia.contenido = contenido
        guia.full_clean()
        guia.save()
        registrar_auditoria(
            request,
            unidad=guia.actividad.unidad,
            accion='actualizar',
            objeto=guia,
            descripcion=f'Contenido de la guía v{guia.numero_version} guardado desde el editor visual.',
            anteriores=anteriores,
            nuevos=instantanea(guia, GUIA_FIELDS_AUDIT),
        )
    vista = _contenido_para_vista(guia)
    return JsonResponse({
        'success': True,
        'version': _version_de(guia),
        'guardado_en': timezone.localtime(guia.actualizado_en).strftime('%H:%M'),
        'faltantes': guia.secciones_faltantes(),
        'avisos': avisos,
        'zonas': {clave: vista['documento'].html(clave, edicion=True) for clave in CAMPOS_RICOS},
    })


@login_required
@require_POST
def formatear_bibliografia_guia(request):
    """Convierte BibTeX y referencias sueltas al estilo IEEE para la vista previa.

    Es el mismo formateador que usa el guardado, de modo que lo que el
    asistente muestra coincide con el HTML y el PDF finales.
    """
    try:
        datos = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Cuerpo JSON no válido.'}, status=400)
    if not isinstance(datos, dict):
        return JsonResponse({'success': False, 'error': 'Cuerpo JSON no válido.'}, status=400)
    texto = str(datos.get('texto') or '')[:20000]
    materiales = str(datos.get('materiales') or '')[:5000]
    return JsonResponse({
        'success': True,
        'referencias': normalizar_bibliografia(texto),
        'materiales': normalizar_materiales_complementarios(materiales),
    })


@login_required
@require_POST
def subir_guia_firmada(request, guia_id):
    """Carga el PDF de la guía aprobada firmado con certificado electrónico."""
    guia = get_object_or_404(
        GuiaActividadReserva.objects.select_related('actividad', 'actividad__unidad'),
        pk=guia_id, es_estructurada=True, activo=True,
    )
    if not _puede_cargar_firmada(request.user, guia):
        raise Http404('Guía no disponible')
    # El expediente de «Mis reservas» la carga sin salir de su ventana.
    desde_expediente = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _fallo(mensaje):
        if desde_expediente:
            return JsonResponse({'success': False, 'error': mensaje}, status=400)
        messages.error(request, mensaje)
        return redirect('ver_guia_actividad', guia_id=guia.pk)

    if guia.estado_publicacion not in {'revision', 'publicada'}:
        return _fallo(
            'La versión firmada se carga cuando la guía está en revisión o ya fue aprobada.'
        )
    archivo = request.FILES.get('archivo_firmado')
    if archivo is None:
        return _fallo('Selecciona el PDF firmado con FirmaEC.')
    try:
        registrar_pdf_firmado(guia, archivo, request.user, request=request)
    except ValueError as error:
        return _fallo(str(error))
    mensaje = 'Versión firmada registrada. La descarga entrega ahora el PDF firmado.'
    if desde_expediente:
        return JsonResponse({
            'success': True,
            'message': mensaje,
            'resumen': guia.firma_certificada_resumen,
        })
    messages.success(request, mensaje)
    return redirect('ver_guia_actividad', guia_id=guia.pk)


@login_required
@require_POST
def vista_previa_pdf_guia(request):
    """PDF de la guía tal como se redacta en el asistente, antes de que exista.

    Recibe los mismos campos ``guia_*`` que la solicitud y los datos
    automáticos que el asistente ya muestra; construye una guía transitoria
    (sin guardar) y devuelve el mismo PDF que se generará al aprobarla.
    """
    from apps.reservas.models.reservas import CatalogoActividadReserva, Reserva
    from apps.directorio_unidades.models.core import Unidad
    try:
        unidad = Unidad.objects.get(pk=int(request.POST.get('unidad_id', '')))
    except (Unidad.DoesNotExist, TypeError, ValueError):
        raise Http404('Unidad no disponible')
    if not _puede_crear_guias(request.user, unidad):
        raise Http404('Guía no disponible')
    try:
        automaticos = json.loads(request.POST.get('automaticos') or '{}')
    except ValueError:
        automaticos = {}
    if not isinstance(automaticos, dict):
        automaticos = {}

    def lineas(valor):
        if isinstance(valor, (list, tuple)):
            return [str(item).strip() for item in valor if str(item).strip()]
        return [parte.strip() for parte in re.split(r'\n| · ', str(valor or '')) if parte.strip()]

    token = str(request.POST.get('guia_imagenes_token', ''))[:40]
    figuras = []
    for posicion, imagen in enumerate(figuras_borrador(token, request.user), 1):
        try:
            figuras.append({
                'n': posicion, 'titulo': imagen.titulo, 'url': imagen.imagen.url,
                'ruta': imagen.imagen.path, 'pk': imagen.pk,
            })
        except (ValueError, NotImplementedError):
            continue
    participantes = re.search(r'\d+', str(automaticos.get('participants') or ''))
    datos = {campo: str(request.POST.get(f'guia_{campo}', '')).strip() for campo in GUIA_INTEGRADA_CAMPOS}
    datos.update({
        'proposito_codigo': 'docencia_practica',
        'subtipo_actividad': Reserva.SUBTIPO_PREDETERMINADO['docencia_practica'],
        'nombre_actividad': str(automaticos.get('activity') or 'Guía en preparación')[:220],
        'titulo': str(automaticos.get('title') or automaticos.get('activity') or 'Guía de práctica')[:220],
        'asignatura': datos.get('asignatura') or str(automaticos.get('subject') or ''),
        'carrera_semestre': str(automaticos.get('career') or ''),
        'docente_responsable': str(automaticos.get('responsible') or request.user.get_full_name() or request.user.username),
        'categoria_uso': str(automaticos.get('purpose') or ''),
        'duracion': str(automaticos.get('duration') or ''),
        'maximo_estudiantes': participantes.group(0) if participantes else '',
        'equipos': '\n'.join(lineas(automaticos.get('equipment'))),
        'software': '\n'.join(lineas(automaticos.get('software'))),
        'materiales': '\n'.join(lineas(automaticos.get('consumables'))),
        'manejo_residuos': '\n'.join(lineas(automaticos.get('waste'))),
        'formato_contenido': str(request.POST.get('guia_formato_contenido', '')).strip(),
        'permite_descarga': 'on',
    })
    datos['formato_procedimiento'] = datos.get('formato_procedimiento') or 'numerado'
    form = GuiaPracticaForm(
        datos, unidad=unidad, usuario=request.user,
        figuras_permitidas={figura['pk'] for figura in figuras},
    )
    if not form.is_valid():
        errores = '; '.join(
            f"{form.fields[campo].label if campo in form.fields else campo}: {' '.join(lista)}"
            for campo, lista in form.errors.items()
        )
        return HttpResponse(
            f'No fue posible generar la vista previa: {errores}',
            status=400, content_type='text/plain; charset=utf-8',
        )
    contenido = form.contenido_normalizado()
    try:
        contenido['firmas'] = normalizar_firmas(request.POST.get('guia_firmas', ''))
    except ValueError as error:
        return HttpResponse(str(error), status=400, content_type='text/plain; charset=utf-8')
    if contenido.get('formato_contenido') == FORMATO_HTML:
        contenido['seguridad_institucional'] = lineas(automaticos.get('safety'))
    contenido['reserva_fuente_codigo'] = str(automaticos.get('schedule') or '')
    actividad = CatalogoActividadReserva(
        unidad=unidad, nombre=datos['nombre_actividad'], codigo='',
        proposito_codigo='docencia_practica', creado_por=request.user,
    )
    guia = GuiaActividadReserva(
        actividad=actividad, titulo=form.cleaned_data['titulo'], contenido=contenido,
        numero_version=1, estado_publicacion='borrador', es_estructurada=True,
        subido_por=request.user,
    )
    respuesta = HttpResponse(construir_pdf_guia(guia, figuras=figuras), content_type='application/pdf')
    respuesta['Content-Disposition'] = 'inline; filename="guia-practica-vista-previa.pdf"'
    return respuesta
