"""Recordatorios idempotentes y avisos del ciclo operativo de reservas."""

from datetime import timedelta
import hashlib
import json
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from apps.core.presentation.presentacion_institucional import con_presentacion_institucional
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.core.presentation.identidad import identidad_publica

from apps.reservas.models.reservas import NotificacionReserva, Reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria

from apps.reservas.presentation.ciclo import analizar_riesgos_operativos_reservas, reservas_en_horizonte_operativo
from apps.reservas.presentation.capacidad import CapacidadReservasSuspendida, bloquear_operacion_reservas
from apps.reservas.presentation.comprobantes import construir_comprobante_reserva


logger = logging.getLogger(__name__)


def correo_transaccional_configurado():
    """Indica si el backend activo puede entregar mensajes fuera del sistema."""
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if backend.endswith('.console.EmailBackend'):
        return False
    if backend.endswith('.smtp.EmailBackend'):
        return bool(
            getattr(settings, 'EMAIL_HOST', '')
            and getattr(settings, 'EMAIL_HOST_USER', '')
            and getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        )
    return True


def _url_reserva(reserva):
    # El id permite que Mis reservas abra directamente esta solicitud.
    return reserva.url_seguimiento


def _url_gestion_reserva(reserva, *, filtro="pendientes"):
    query = urlencode(
        {
            "view": "reservas",
            "modo_reservas": "solicitudes",
            "filtro_reservas": filtro,
            "reserva": reserva.pk,
        }
    )
    return f"{reverse('gestion_unidad', args=[reserva.laboratorio.slug])}?{query}"


def _limite_intentos_email():
    return max(1, int(getattr(settings, 'RESERVATION_EMAIL_MAX_ATTEMPTS', 5)))


def _intervalo_reintento_email():
    minutos = max(1, int(getattr(settings, 'RESERVATION_EMAIL_RETRY_MINUTES', 15)))
    return timedelta(minutes=minutos)


def _puede_reintentar_email(notificacion, *, ahora=None):
    if notificacion.enviada_email or not (notificacion.usuario.email or '').strip():
        return False
    if notificacion.intentos_email >= _limite_intentos_email():
        return False
    ahora = ahora or timezone.now()
    return (
        not notificacion.ultimo_intento_email
        or notificacion.ultimo_intento_email <= ahora - _intervalo_reintento_email()
    )


def _reclamar_intento_email(notificacion_id, *, ahora=None):
    """Reserva un intento SMTP para que dos ejecutores no envien el mismo aviso."""
    ahora = ahora or timezone.now()
    with transaction.atomic():
        notificacion = (
            NotificacionReserva.objects.select_for_update()
            .select_related('usuario', 'reserva__laboratorio')
            .get(pk=notificacion_id)
        )
        correo = (notificacion.usuario.email or '').strip()
        if not correo:
            notificacion.error_email = 'El usuario no tiene un correo registrado.'
            notificacion.save(update_fields=['error_email'])
            return None
        if not correo_transaccional_configurado():
            notificacion.error_email = (
                'Envío pendiente: configure las credenciales del correo '
                'transaccional institucional.'
            )
            notificacion.save(update_fields=['error_email'])
            return None
        if not _puede_reintentar_email(notificacion, ahora=ahora):
            return None
        notificacion.intentos_email += 1
        notificacion.ultimo_intento_email = ahora
        notificacion.save(update_fields=['intentos_email', 'ultimo_intento_email'])
        return notificacion


@con_presentacion_institucional()
def _enviar_correo(notificacion):
    """Entrega un correo y conserva cada intento sin afectar el aviso interno."""
    notificacion = _reclamar_intento_email(notificacion.pk)
    if notificacion is None:
        return False
    correo = (notificacion.usuario.email or '').strip()

    sitio = getattr(settings, 'SITE_URL', '').rstrip('/')
    enlace = f'{sitio}{notificacion.url}'
    contexto = {
        **identidad_publica(),
        'notificacion': notificacion,
        'reserva': notificacion.reserva,
        'unidad': notificacion.reserva.laboratorio,
        'comprobante': construir_comprobante_reserva(notificacion.reserva),
        'enlace': enlace,
        'modo_correo': True,
    }
    asunto = f"[{contexto['identidad_institucion'].siglas} Laboratorios] {notificacion.titulo}"
    texto = render_to_string('emails/reservas/notificacion.txt', contexto).strip()
    html = render_to_string('emails/reservas/notificacion.html', contexto)
    try:
        email = EmailMultiAlternatives(
            asunto,
            texto,
            settings.DEFAULT_FROM_EMAIL,
            [correo],
        )
        email.attach_alternative(html, 'text/html')
        email.send(fail_silently=False)
        NotificacionReserva.objects.filter(pk=notificacion.pk).update(
            enviada_email=True,
            fecha_email=timezone.now(),
            error_email='',
        )
        return True
    except Exception as error:  # La notificación interna no debe perderse por SMTP.
        logger.exception('No se pudo enviar la notificación de reserva %s', notificacion.pk)
        NotificacionReserva.objects.filter(pk=notificacion.pk).update(
            error_email=str(error)[:1000],
        )
        return False


def crear_notificacion(
    *,
    reserva,
    usuario,
    tipo,
    titulo,
    mensaje,
    clave,
    enviar_email=True,
    url=None,
):
    if not usuario or not usuario.pk:
        return None, False
    notificacion, creada = NotificacionReserva.objects.get_or_create(
        clave=clave,
        defaults={
            'reserva': reserva,
            'usuario': usuario,
            'tipo': tipo,
            'titulo': titulo,
            'mensaje': mensaje,
            'url': url or _url_reserva(reserva),
        },
    )
    if enviar_email and (
        creada
        or (notificacion.intentos_email > 0 and _puede_reintentar_email(notificacion))
    ):
        transaction.on_commit(lambda pk=notificacion.pk: _enviar_correo(NotificacionReserva.objects.get(pk=pk)))
    return notificacion, creada


def reenviar_notificaciones_pendientes(*, limite=100, ahora=None, unidad=None):
    """Reintenta entregas SMTP fallidas respetando intervalo y máximo de intentos."""
    ahora = ahora or timezone.now()
    corte = ahora - _intervalo_reintento_email()
    pendientes = (
        NotificacionReserva.objects.filter(
            enviada_email=False,
            intentos_email__lt=_limite_intentos_email(),
            usuario__email__isnull=False,
        )
        .exclude(usuario__email='')
        .filter(
            Q(
                intentos_email=0,
                error_email__startswith='Envío pendiente:',
            )
            | Q(intentos_email__gt=0) & (
                Q(ultimo_intento_email__isnull=True)
                | Q(ultimo_intento_email__lte=corte)
            )
        )
    )
    if unidad is not None:
        pendientes = pendientes.filter(reserva__laboratorio=unidad)
    pendientes = (
        pendientes.select_related('usuario', 'reserva__laboratorio')
        .order_by('creada_en', 'pk')[: max(1, int(limite))]
    )
    resultados = {'correos_reintentados': 0, 'correos_fallidos': 0}
    for notificacion in pendientes:
        if _enviar_correo(notificacion):
            resultados['correos_reintentados'] += 1
        else:
            resultados['correos_fallidos'] += 1
    return resultados


def notificar_cambio_reserva(reserva, accion, observacion=''):
    if not reserva.usuario_id:
        return None
    mensajes = {
        'aprobar': ('Reserva confirmada', 'Tu reserva fue aprobada y quedó confirmada.'),
        'rechazar': ('Solicitud rechazada', 'La solicitud no pudo ser aprobada.'),
        'cancelar': ('Reserva cancelada', 'La reserva fue cancelada.'),
        'iniciar': ('Atención iniciada', 'El laboratorio registró el inicio de la atención.'),
        'completar': ('Atención completada', 'La actividad fue registrada como atendida y completada.'),
        'no_presentado': ('Inasistencia registrada', 'La reserva fue cerrada porque no se registró asistencia.'),
        'no_atendida': ('Reserva no atendida', 'La unidad registró que la reserva no pudo ser atendida.'),
        'solicitar_info': ('Información requerida', 'El laboratorio necesita que completes o confirmes información de la solicitud.'),
        'actualizar': ('Reserva actualizada', 'El laboratorio actualizó los datos operativos de la reserva.'),
        'cambio_aprobado': (
            'Cambio de reserva aprobado',
            'Tu propuesta fue validada y ya forma parte de la reserva vigente.',
        ),
    }
    titulo, mensaje = mensajes.get(accion, ('Actualización de reserva', 'Tu reserva fue actualizada.'))
    if observacion:
        mensaje = f'{mensaje} Detalle: {observacion}'
    clave = f'reserva:{reserva.pk}:accion:{accion}:{timezone.now().strftime("%Y%m%d%H%M%S%f")}'
    return crear_notificacion(
        reserva=reserva,
        usuario=reserva.usuario,
        tipo='informacion' if accion == 'solicitar_info' else 'estado',
        titulo=titulo,
        mensaje=mensaje,
        clave=clave,
    )[0]


def _resultado_ciclo_vacio():
    return {
        'vencidas': 0,
        'recordatorios_24h': 0,
        'recordatorios_2h': 0,
        'cierres_pendientes': 0,
        'sin_responsable': 0,
        'riesgos_operativos': 0,
        'correos_reintentados': 0,
        'correos_fallidos': 0,
        'guias_sesion_pendientes': 0,
    }


def procesar_recordatorios_reservas(
    *, ahora=None, enviar_email=True, unidad=None, simular=False
):
    """Omite el ciclo suspendido; la siguiente ejecución puede recuperarlo."""
    try:
        with bloquear_operacion_reservas():
            if simular:
                with transaction.atomic():
                    resultado = _procesar_recordatorios_reservas(
                        ahora=ahora,
                        enviar_email=False,
                        unidad=unidad,
                    )
                    transaction.set_rollback(True)
                    return resultado
            return _procesar_recordatorios_reservas(
                ahora=ahora, enviar_email=enviar_email, unidad=unidad
            )
    except CapacidadReservasSuspendida:
        logger.info('ciclo_reservas_omitido_capacidad_suspendida')
        return _resultado_ciclo_vacio()


def _procesar_recordatorios_reservas(*, ahora=None, enviar_email=True, unidad=None):
    """Procesa el ciclo completo sin decidir cierres por el laboratorista."""
    ahora = ahora or timezone.now()
    resultados = _resultado_ciclo_vacio()

    activas = Reserva.objects.filter(
        estado__in=['pendiente', 'confirmada', 'en_proceso'],
        fecha__lte=timezone.localdate(ahora) + timedelta(days=2),
    ).select_related(
        'usuario',
        'laboratorio',
        'responsable_asignado__usuario',
        'laboratorio__administrador',
    )
    if unidad is not None:
        activas = activas.filter(laboratorio=unidad)

    for reserva in activas:
        inicio = reserva.fecha_hora_inicio
        fin = reserva.fecha_hora_fin
        if not inicio or not fin:
            continue
        if reserva.estado == 'pendiente' and fin < ahora:
            with transaction.atomic():
                bloqueada = (
                    Reserva.objects.select_for_update()
                    .get(pk=reserva.pk)
                )
                if (
                    bloqueada.estado != 'pendiente'
                    or not bloqueada.fecha_hora_fin
                    or bloqueada.fecha_hora_fin >= ahora
                ):
                    continue
                anteriores = {
                    'estado': bloqueada.estado,
                    'resultado_cierre': bloqueada.resultado_cierre,
                    'fecha_cierre': (
                        bloqueada.fecha_cierre.isoformat()
                        if bloqueada.fecha_cierre
                        else None
                    ),
                    'detalle_cierre': bloqueada.detalle_cierre,
                }
                bloqueada.estado = 'vencida'
                bloqueada.resultado_cierre = 'vencida'
                bloqueada.fecha_cierre = ahora
                bloqueada.detalle_cierre = (
                    'La solicitud llegó al final de su horario sin aprobación.'
                )
                bloqueada.save(
                    update_fields=[
                        'estado',
                        'resultado_cierre',
                        'fecha_cierre',
                        'detalle_cierre',
                        'fecha_actualizacion',
                    ]
                )
                registrar_auditoria(
                    unidad=bloqueada.laboratorio,
                    accion='actualizar',
                    objeto=bloqueada,
                    descripcion='Vencimiento automático de solicitud sin aprobación.',
                    anteriores=anteriores,
                    nuevos={
                        'estado': bloqueada.estado,
                        'resultado_cierre': bloqueada.resultado_cierre,
                        'fecha_cierre': bloqueada.fecha_cierre.isoformat(),
                        'detalle_cierre': bloqueada.detalle_cierre,
                    },
                )
                resultados['vencidas'] += 1
                bloqueada.notificaciones.filter(
                    leida=False,
                    clave__contains=':riesgo_operativo:',
                ).update(leida=True)
                bloqueada.notificaciones.filter(
                    leida=False,
                    clave__contains=':sin_responsable',
                ).update(leida=True)
                if bloqueada.usuario_id:
                    crear_notificacion(
                        reserva=bloqueada,
                        usuario=bloqueada.usuario,
                        tipo='vencimiento',
                        titulo='Solicitud vencida sin aprobación',
                        mensaje=(
                            'La fecha de la solicitud pasó sin que la unidad la '
                            'aprobara. No se contabiliza como atención efectiva.'
                        ),
                        clave=f'reserva:{bloqueada.pk}:vencida',
                        enviar_email=enviar_email,
                    )
            continue

        if reserva.estado == 'confirmada' and inicio > ahora:
            faltante = inicio - ahora
            tipo = None
            if timedelta(hours=2) < faltante <= timedelta(hours=24):
                tipo = 'recordatorio_24h'
            elif timedelta(0) < faltante <= timedelta(hours=2):
                tipo = 'recordatorio_2h'
            if tipo and reserva.usuario_id:
                horas = '24 horas' if tipo == 'recordatorio_24h' else '2 horas'
                _, creada = crear_notificacion(
                    reserva=reserva,
                    usuario=reserva.usuario,
                    tipo=tipo,
                    titulo=f'Recordatorio de reserva ({horas})',
                    mensaje=(
                        f'Tienes una reserva en {reserva.laboratorio.nombre} el '
                        f'{reserva.fecha:%d/%m/%Y} de '
                        f'{reserva.hora_inicio:%H:%M} a {reserva.hora_fin:%H:%M}.'
                    ),
                    clave=f'reserva:{reserva.pk}:{tipo}',
                    enviar_email=enviar_email,
                )
                result_key = (
                    'recordatorios_24h'
                    if tipo == 'recordatorio_24h'
                    else 'recordatorios_2h'
                )
                resultados[result_key] += int(creada)

        if reserva.estado in {'confirmada', 'en_proceso'} and fin < ahora:
            encargado = (
                reserva.responsable_asignado.usuario
                if reserva.responsable_asignado_id
                and reserva.responsable_asignado.usuario_id
                else reserva.laboratorio.administrador
            )
            if encargado:
                _, creada = crear_notificacion(
                    reserva=reserva,
                    usuario=encargado,
                    tipo='cierre_pendiente',
                    titulo='Reserva pendiente de cierre operativo',
                    mensaje=(
                        'El horario ya terminó. Registra si fue atendida, si el '
                        'usuario no se presentó, si la unidad no pudo atenderla '
                        'o reprograma la fecha.'
                    ),
                    clave=f'reserva:{reserva.pk}:cierre_pendiente',
                    enviar_email=enviar_email,
                    url=_url_gestion_reserva(reserva, filtro='cierre'),
                )
                resultados['cierres_pendientes'] += int(creada)

    reservas_horizonte = list(
        reservas_en_horizonte_operativo(unidad=unidad, ahora=ahora)
    )
    ids_horizonte = [reserva.pk for reserva in reservas_horizonte]
    for reserva in reservas_horizonte:
        if reserva.responsable_asignado_id:
            reserva.notificaciones.filter(
                leida=False,
                clave__contains=':sin_responsable',
            ).update(leida=True)
            continue
        administrador = reserva.laboratorio.administrador
        if administrador:
            _, creada = crear_notificacion(
                reserva=reserva,
                usuario=administrador,
                tipo='informacion',
                titulo='Reserva activa sin responsable',
                mensaje=(
                    'Asigna personal antes de la atención para asegurar el '
                    'seguimiento y el cierre operativo.'
                ),
                clave=f'reserva:{reserva.pk}:sin_responsable',
                enviar_email=enviar_email,
                url=_url_gestion_reserva(reserva, filtro='sin_asignar'),
            )
            resultados['sin_responsable'] += int(creada)

    riesgos = analizar_riesgos_operativos_reservas(
        ahora=ahora,
        reservas=reservas_horizonte,
    )
    ids_con_riesgo = {item['reserva'].pk for item in riesgos}
    if ids_horizonte:
        (
            NotificacionReserva.objects.filter(
                reserva_id__in=ids_horizonte,
                leida=False,
                clave__contains=':riesgo_operativo:',
            )
            .exclude(reserva_id__in=ids_con_riesgo)
            .update(leida=True)
        )
    for analysis in riesgos:
        reserva = analysis['reserva']
        encargado = (
            reserva.responsable_asignado.usuario
            if reserva.responsable_asignado_id
            and reserva.responsable_asignado.usuario_id
            else reserva.laboratorio.administrador
        )
        if not encargado:
            continue
        details = [item['detalle'] for item in analysis['riesgos']]
        signature = hashlib.sha256(
            json.dumps(details, ensure_ascii=False, sort_keys=True).encode('utf-8')
        ).hexdigest()[:16]
        key = f'reserva:{reserva.pk}:riesgo_operativo:{signature}'
        reserva.notificaciones.filter(
            leida=False,
            clave__contains=':riesgo_operativo:',
        ).exclude(clave=key).update(leida=True)
        _, created = crear_notificacion(
            reserva=reserva,
            usuario=encargado,
            tipo='informacion',
            titulo='Reserva con riesgo operativo',
            mensaje='Revisa la reserva antes de atenderla: ' + ' '.join(details[:4]),
            clave=key,
            enviar_email=enviar_email,
            url=_url_gestion_reserva(reserva, filtro='riesgo'),
        )
        resultados['riesgos_operativos'] += int(created)

    if enviar_email:
        resultados.update(
            reenviar_notificaciones_pendientes(ahora=ahora, unidad=unidad)
        )
    # La guía de cada sesión programada se pide con antelación: el aviso llega una sola vez.
    from apps.formacion.presentation.asignaturas import avisar_guias_de_sesion

    resultados['guias_sesion_pendientes'] = avisar_guias_de_sesion(
        ahora,
        enviar_email=enviar_email,
        unidad=unidad,
    )
    return resultados
