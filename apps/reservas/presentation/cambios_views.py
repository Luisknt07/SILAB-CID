"""Vistas del circuito de cambios de una reserva ya registrada."""

from django.utils.translation import gettext

import json

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.reservas.models.reservas import Reserva, SolicitudCambioReserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.permisos import puede_operar_reservas_unidad
from apps.reservas.presentation.cambios import CAMPOS_CAMBIO, aplicar_solicitud_cambio, enviar_propuesta_cambio
from apps.reservas.presentation.cambios import cantidad_insumo_normalizada, describir_diferencias
from apps.reservas.presentation.decisiones_cambio import autorizar_solicitud_cambio, rechazar_solicitud_cambio, retirar_solicitud_cambio

from apps.reservas.presentation.solicitudes_propias import SolicitudCambioActiva, crear_solicitud_cambio


def _mensaje_error(error):
    if hasattr(error, 'messages'):
        return ' '.join(error.messages)
    return str(error)


def serializar_solicitud_cambio(solicitud):
    if not solicitud:
        return None
    vencida = solicitud.autorizacion_vencida
    return {
        'id': solicitud.pk,
        'estado': 'vencida' if vencida else solicitud.estado,
        'estado_display': (
            'Autorización vencida' if vencida else solicitud.get_estado_display()
        ),
        'motivo': solicitud.motivo_solicitud,
        'campos_autorizados': solicitud.campos_autorizados or [],
        'campos_autorizados_display': [
            CAMPOS_CAMBIO.get(campo, campo)
            for campo in (solicitud.campos_autorizados or [])
        ],
        'puede_editar': solicitud.puede_editar,
        'puede_retirar': (
            not vencida and solicitud.estado in SolicitudCambioReserva.ESTADOS_ACTIVOS
        ),
        'retirar_url': reverse('retirar_solicitud_cambio_reserva', args=[solicitud.pk]),
        'editar_url': reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk]),
        'accion_url': reverse(
            'gestion_solicitud_cambio_reserva_accion',
            args=[solicitud.reserva.laboratorio.slug, solicitud.pk],
        ),
        'vence_en': (
            solicitud.autorizacion_vence_en.isoformat()
            if solicitud.autorizacion_vence_en else None
        ),
        'creada_en': solicitud.creada_en.isoformat(),
        'enviada_en': solicitud.enviada_en.isoformat() if solicitud.enviada_en else None,
        'observacion_revision': solicitud.observacion_revision,
        'diferencias': describir_diferencias(
            solicitud.reserva, solicitud.datos_base, solicitud.propuesta,
        ),
        'revision': (
            solicitud.revision_aplicada.numero
            if solicitud.revision_aplicada_id else None
        ),
    }


@login_required
@require_POST
def solicitar_cambio_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id, usuario=request.user)
    try:
        solicitud = crear_solicitud_cambio(
            reserva, actor=request.user, motivo=request.POST.get('motivo', ''),
            request=request, unidad_esperada=reserva.laboratorio_id)
    except SolicitudCambioActiva as error:
        datos = {'success': False, 'error': _mensaje_error(error)}
        if error.solicitud is not None:
            datos['solicitud_cambio'] = serializar_solicitud_cambio(error.solicitud)
        return JsonResponse(datos, status=409)
    except PermissionDenied as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=403)
    except ValidationError as error:
        codigo = getattr(error, 'code', None)
        estado_http = 400 if codigo == 'motivo_invalido' else 404 if codigo == 'no_disponible' else 409
        return JsonResponse({'success': False, 'error': _mensaje_error(error)}, status=estado_http)
    return JsonResponse({
        'success': True,
        'message': gettext('Solicitud enviada. La reserva vigente no cambiará hasta que el '
                           'laboratorio autorice la edición y apruebe tu propuesta.'),
        'solicitud_cambio': serializar_solicitud_cambio(solicitud)}, status=201)


def _catalogos_editor(reserva):
    unidad = reserva.laboratorio
    return {
        'usuarios': get_user_model().objects.filter(is_active=True)
        .exclude(pk=reserva.usuario_id)
        .order_by('first_name', 'last_name', 'username')[:200],
        'equipos': UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True
        ).select_related('equipo').distinct().order_by('equipo__nombre', 'codigo_unidad'),
        'software': SoftwareDisponible.objects.filter(
            unidad=unidad, activo=True
        ).order_by('nombre'),
        'espacios': EspacioReservable.objects.filter(
            unidad=unidad, activo=True, reservable=True
        ).order_by('orden', 'nombre'),
        'servicios': FablabService.objects.filter(
            Q(unidad=unidad) | Q(unidad__isnull=True), activo=True
        ).distinct().order_by('nombre'),
        'consumibles': Consumible.objects.filter(
            unidad=unidad, activo=True, visible_en_reservas=True
        ).order_by('clasificacion', 'familia', 'nombre'),
    }


def _lista_enteros(request, nombre):
    try:
        return sorted({int(valor) for valor in request.POST.getlist(nombre) if valor})
    except (TypeError, ValueError) as error:
        raise ValidationError('La selección contiene un identificador no válido.') from error


def _propuesta_desde_post(request, solicitud):
    permitidos = set(solicitud.campos_autorizados or [])
    propuesta = {}
    if 'fecha_horario' in permitidos:
        propuesta.update(
            fecha=(request.POST.get('fecha') or '').strip(),
            hora_inicio=(request.POST.get('hora_inicio') or '').strip(),
            hora_fin=(request.POST.get('hora_fin') or '').strip(),
        )
    if 'actividad' in permitidos:
        propuesta.update(
            titulo_solicitud=(request.POST.get('titulo_solicitud') or '').strip(),
            motivo=(request.POST.get('motivo') or '').strip(),
            descripcion_proyecto=(request.POST.get('descripcion_proyecto') or '').strip(),
            requisitos_especiales=(request.POST.get('requisitos_especiales') or '').strip(),
        )
    if 'participantes' in permitidos:
        participantes = _lista_enteros(request, 'participantes_ids')
        propuesta.update(
            participantes_ids=participantes,
            numero_participantes=1 + len(participantes),
        )
    for grupo, nombre in (
        ('equipos', 'unidades_ids'),
        ('software', 'software_ids'),
        ('espacios', 'espacios_ids'),
        ('servicios', 'servicios_ids'),
    ):
        if grupo in permitidos:
            propuesta[nombre] = _lista_enteros(request, nombre)
    if 'insumos' in permitidos:
        filas = []
        for consumible_id in _lista_enteros(request, 'consumibles_ids'):
            metodo = (
                request.POST.get(f'consumible_{consumible_id}_metodo') or 'estimacion'
            ).strip()
            # Se valida al enviar, no al aprobar: antes una cantidad vacia se
            # aceptaba y fallaba dias despues, con el error visible solo para
            # el personal y el titular sin saber por que no avanzaba.
            cantidad = cantidad_insumo_normalizada(
                (request.POST.get(f'consumible_{consumible_id}_cantidad') or '').strip()
                or None,
                metodo,
            )
            filas.append(
                {
                    'id': consumible_id,
                    'cantidad_solicitada': str(cantidad) if cantidad is not None else None,
                    'metodo_estimacion': metodo,
                }
            )
        propuesta['consumibles'] = filas
    return propuesta


@login_required
@require_http_methods(['GET', 'POST'])
def editar_solicitud_cambio_reserva(request, solicitud_id):
    solicitud = get_object_or_404(
        SolicitudCambioReserva.objects.select_related(
            'reserva__laboratorio', 'solicitada_por'
        ),
        pk=solicitud_id,
        solicitada_por=request.user,
    )
    if request.method == 'POST':
        estado_http = 200
        try:
            propuesta = _propuesta_desde_post(request, solicitud)
            solicitud = enviar_propuesta_cambio(
                solicitud, propuesta, actor=request.user, request=request,
                unidad_esperada=solicitud.reserva.laboratorio_id)
            messages.success(
                request,
                gettext('Tu propuesta de cambio fue enviada. La reserva original sigue vigente '
                'hasta que el laboratorio la revise.'),
            )
            return redirect(
                f"{reverse('laboratorio_detalle', args=[solicitud.reserva.laboratorio.slug])}"
                f'?reserva={solicitud.reserva_id}#mis-reservas'
            )
        except ValidationError as error:
            mensaje = _mensaje_error(error)
            if getattr(error, 'code', None) in {'ventana_cerrada', 'campos_cambiados', 'no_disponible'}:
                estado_http = 409
            solicitud = get_object_or_404(
                SolicitudCambioReserva.objects.select_related('reserva__laboratorio'),
                pk=solicitud_id, solicitada_por=request.user)
    else:
        mensaje = ''
        estado_http = 200

    # Presentacion del vencimiento; GET no cambia el expediente almacenado.
    if solicitud.autorizacion_vencida:
        solicitud.estado = 'vencida'

    datos = dict(solicitud.datos_base or {})
    datos.update(solicitud.propuesta or {})
    seleccion = {
        'participantes': {int(valor) for valor in datos.get('participantes_ids', [])},
        'equipos': {int(valor) for valor in datos.get('unidades_ids', [])},
        'software': {int(valor) for valor in datos.get('software_ids', [])},
        'espacios': {int(valor) for valor in datos.get('espacios_ids', [])},
        'servicios': {int(valor) for valor in datos.get('servicios_ids', [])},
        'consumibles': {
            int(fila['id']): fila for fila in datos.get('consumibles', [])
        },
    }
    return render(
        request,
        'portal/pages/unidades/reservas/editar_cambio.html',
        {
            'solicitud': solicitud,
            'reserva': solicitud.reserva,
            'datos': datos,
            'seleccion': seleccion,
            'error': mensaje,
            'diferencias': describir_diferencias(
                solicitud.reserva, solicitud.datos_base, solicitud.propuesta,
            ),
            'puede_retirar': solicitud.estado in SolicitudCambioReserva.ESTADOS_ACTIVOS,
            'retirar_url': reverse(
                'retirar_solicitud_cambio_reserva', args=[solicitud.pk]
            ),
            **_catalogos_editor(solicitud.reserva),
        },
        status=estado_http,
    )


@login_required
@require_POST
def gestion_solicitud_cambio_reserva_accion(request, slug, solicitud_id):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_reservas_unidad(request.user, unidad):
        raise PermissionDenied('No tienes autorización para revisar este cambio.')
    accion = (request.POST.get('accion') or '').strip()
    observacion = (request.POST.get('observacion') or '').strip()
    if accion not in {'autorizar', 'rechazar', 'aprobar'}:
        return JsonResponse(
            {'success': False, 'error': 'Selecciona una acción válida.'}, status=400)
    solicitud = get_object_or_404(
        SolicitudCambioReserva.objects.select_related('reserva__laboratorio'),
        pk=solicitud_id, reserva__laboratorio=unidad)
    try:
        if accion == 'autorizar':
            # Ausencia conserva todos los grupos; entrada explicita se valida.
            campos = request.POST.getlist('campos') if 'campos' in request.POST else None
            if campos and len(campos) == 1 and campos[0].lstrip().startswith('['):
                try:
                    campos = json.loads(campos[0])
                except (json.JSONDecodeError, RecursionError):
                    campos = []
            solicitud = autorizar_solicitud_cambio(
                solicitud, actor=request.user, campos=campos, observacion=observacion,
                request=request, unidad_esperada=unidad.pk)
            mensaje = gettext('Se habilitó la edición durante 48 horas.')
        elif accion == 'rechazar':
            solicitud = rechazar_solicitud_cambio(
                solicitud, actor=request.user, observacion=observacion,
                request=request, unidad_esperada=unidad.pk)
            mensaje = gettext('La solicitud de cambio fue rechazada con trazabilidad.')
        else:
            revision = aplicar_solicitud_cambio(
                solicitud, actor=request.user, request=request,
                observacion=observacion, unidad_esperada=unidad.pk)
            solicitud.refresh_from_db()
            mensaje = f'Cambios aplicados como revisión {revision.numero}.'
    except ValidationError as error:
        estado_http = 400 if getattr(error, 'code', None) in {'campos_invalidos', 'motivo_invalido'} else 409
        return JsonResponse({'success': False, 'error': _mensaje_error(error)}, status=estado_http)
    return JsonResponse({
        'success': True, 'message': mensaje,
        'solicitud_cambio': serializar_solicitud_cambio(solicitud)})


@login_required
@require_POST
def retirar_solicitud_cambio_reserva(request, solicitud_id):
    """Adapter HTTP de la retirada propia, con respuesta AJAX o aviso/redirect."""
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    solicitud = get_object_or_404(
        SolicitudCambioReserva.objects.select_related('reserva__laboratorio'),
        pk=solicitud_id, solicitada_por=request.user)
    volver = (
        f"{reverse('laboratorio_detalle', args=[solicitud.reserva.laboratorio.slug])}"
        f'?reserva={solicitud.reserva_id}#mis-reservas')
    try:
        solicitud = retirar_solicitud_cambio(
            solicitud, actor=request.user, request=request,
            unidad_esperada=solicitud.reserva.laboratorio_id)
    except ValidationError as error:
        mensaje = _mensaje_error(error)
        if es_ajax:
            return JsonResponse({'success': False, 'error': mensaje}, status=409)
        messages.error(request, mensaje)
        return redirect(volver)
    mensaje = gettext('Tu solicitud de cambio fue retirada. La reserva vigente no cambia.')
    if es_ajax:
        return JsonResponse({
            'success': True, 'message': mensaje,
            'solicitud_cambio': serializar_solicitud_cambio(solicitud)})
    messages.success(request, mensaje)
    return redirect(volver)
