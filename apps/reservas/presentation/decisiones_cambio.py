"""Decisiones sobre solicitudes; no aplican propuestas al expediente vigente."""
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext

from apps.reservas.models.reservas import SolicitudCambioReserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cambios import CAMPOS_CAMBIO, _bloquear_solicitud_cambio
from apps.reservas.presentation.notificaciones import crear_notificacion


def notificar_personal_cambio(solicitud, *, titulo=None, mensaje=None, clave='personal'):
    """Aviso comun de solicitud/retirada, con destinatarios sin duplicados."""
    reserva = solicitud.reserva
    destinatarios = []
    if reserva.laboratorio.administrador_id:
        destinatarios.append(reserva.laboratorio.administrador)
    if reserva.responsable_asignado_id and reserva.responsable_asignado.usuario_id:
        destinatarios.append(reserva.responsable_asignado.usuario)
    vistos = set()
    for usuario in destinatarios:
        if not usuario or usuario.pk in vistos:
            continue
        vistos.add(usuario.pk)
        crear_notificacion(
            reserva=reserva, usuario=usuario, tipo='informacion',
            titulo=titulo or gettext('Cambio solicitado por el titular'),
            mensaje=mensaje or (
                f'{reserva.nombre_completo_solicitante} solicita modificar la reserva. '
                f'Motivo: {solicitud.motivo_solicitud}'),
            clave=f'reserva:{reserva.pk}:cambio:{solicitud.pk}:{clave}',
            url=(f"{reverse('gestion_unidad', args=[reserva.laboratorio.slug])}"
                 f'?view=reservas&modo_reservas=solicitudes&reserva={reserva.pk}'))


def _cargar_decision(solicitud, actor, operacion, unidad_esperada):
    """Caller atomic, default actual: bloqueos reserva -> solicitud y autoridad."""
    if solicitud._state.db not in {None, 'default'}:
        raise ValidationError(gettext('Las decisiones de cambio requieren la base de datos principal.'), code='no_disponible')
    alcance = solicitud.reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    solicitud, reserva = _bloquear_solicitud_cambio(solicitud)
    actor = exigir_autoridad_reserva(reserva, actor, operacion=operacion, unidad_esperada=alcance)
    return solicitud, reserva, actor


@operacion_reservas
@transaction.atomic
def autorizar_solicitud_cambio(solicitud, *, actor, campos=None, observacion='', request=None, unidad_esperada=None):
    """Abre una sola ventana de 48 horas sobre una solicitud pendiente vigente."""
    solicitud, reserva, actor = _cargar_decision(solicitud, actor, 'autorizar_cambio', unidad_esperada)
    if solicitud.estado != 'solicitada':
        raise ValidationError(gettext('La solicitud ya fue atendida.'), code='estado_cerrado')
    if reserva.estado not in {'pendiente', 'confirmada'}:
        raise ValidationError(gettext('La reserva ya inició o está cerrada; no admite este cambio.'), code='estado_cerrado')
    if solicitud.solicitada_por_id != reserva.usuario_id:
        raise ValidationError(gettext('La solicitud ya no pertenece al titular de la reserva.'), code='estado_cerrado')
    if campos is None:
        campos = list(CAMPOS_CAMBIO)
    if not isinstance(campos, (list, tuple)) or not campos or any(
        not isinstance(campo, str) or campo not in CAMPOS_CAMBIO for campo in campos
    ):
        raise ValidationError(gettext('La selección de campos para autorizar no es válida.'), code='campos_invalidos')
    campos = list(dict.fromkeys(campos))
    ahora = timezone.now()
    solicitud.estado = 'autorizada'
    solicitud.campos_autorizados = campos
    solicitud.autorizada_por = actor
    solicitud.autorizada_en = ahora
    solicitud.autorizacion_vence_en = ahora + timedelta(hours=48)
    solicitud.observacion_revision = observacion
    solicitud.save(update_fields=['estado', 'campos_autorizados', 'autorizada_por',
        'autorizada_en', 'autorizacion_vence_en', 'observacion_revision', 'actualizada_en'])
    registrar_auditoria(request, unidad=reserva.laboratorio, accion='aprobar', objeto=solicitud,
        descripcion='Se habilitó al titular una ventana de edición de 48 horas.',
        anteriores={'estado': 'solicitada'}, nuevos={'estado': solicitud.estado, 'campos': campos}, usuario=actor)
    crear_notificacion(reserva=reserva, usuario=solicitud.solicitada_por, tipo='informacion',
        titulo=gettext('Edición de reserva habilitada'),
        mensaje=gettext('Puedes preparar tu propuesta durante las próximas 48 horas. '
                        'La reserva original seguirá vigente hasta la aprobación final.'),
        clave=f'reserva:{reserva.pk}:cambio:{solicitud.pk}:autorizada',
        url=reverse('editar_solicitud_cambio_reserva', args=[solicitud.pk]))
    return solicitud


@operacion_reservas
@transaction.atomic
def rechazar_solicitud_cambio(solicitud, *, actor, observacion='', request=None, unidad_esperada=None):
    """Cierra una solicitud activa; conserva propuesta, ventana y reserva."""
    solicitud, reserva, actor = _cargar_decision(solicitud, actor, 'rechazar_cambio', unidad_esperada)
    if solicitud.estado not in SolicitudCambioReserva.ESTADOS_ACTIVOS:
        raise ValidationError(gettext('La solicitud ya está cerrada.'), code='estado_cerrado')
    if not isinstance(observacion, str) or len(observacion.strip()) < 5:
        raise ValidationError(gettext('Registra el motivo del rechazo.'), code='motivo_invalido')
    observacion = observacion.strip()
    anterior = solicitud.estado
    solicitud.estado = 'rechazada'
    solicitud.revisada_por = actor
    solicitud.revisada_en = timezone.now()
    solicitud.observacion_revision = observacion
    solicitud.save(update_fields=['estado', 'revisada_por', 'revisada_en',
        'observacion_revision', 'actualizada_en'])
    registrar_auditoria(request, unidad=reserva.laboratorio, accion='observar', objeto=solicitud,
        descripcion='La solicitud de cambio fue rechazada.', anteriores={'estado': anterior},
        nuevos={'estado': solicitud.estado, 'motivo': observacion}, usuario=actor)
    crear_notificacion(reserva=reserva, usuario=solicitud.solicitada_por, tipo='informacion',
        titulo=gettext('Solicitud de cambio revisada'),
        mensaje=gettext('La propuesta no fue autorizada o aprobada. Detalle: %(observacion)s') % {'observacion': observacion},
        clave=f'reserva:{reserva.pk}:cambio:{solicitud.pk}:rechazada')
    return solicitud


@operacion_reservas
@transaction.atomic
def retirar_solicitud_cambio(solicitud, *, actor, request=None, unidad_esperada=None):
    """Retirada propia de una solicitud activa, incluso como limpieza de historial."""
    solicitud, reserva, actor = _cargar_decision(solicitud, actor, 'retirar_cambio', unidad_esperada)
    if solicitud.solicitada_por_id != actor.pk:
        raise PermissionDenied(gettext('No tienes autorización para modificar esta reserva.'))
    if solicitud.estado not in SolicitudCambioReserva.ESTADOS_ACTIVOS:
        raise ValidationError(gettext('Esta solicitud ya fue resuelta y no puede retirarse.'), code='estado_cerrado')
    anterior = solicitud.estado
    solicitud.estado = 'cancelada'
    solicitud.observacion_revision = 'Retirada por el titular antes de la decisión del laboratorio.'
    solicitud.revisada_por = actor
    solicitud.revisada_en = timezone.now()
    solicitud.save(update_fields=['estado', 'observacion_revision', 'revisada_por', 'revisada_en', 'actualizada_en'])
    registrar_auditoria(request, unidad=reserva.laboratorio, accion='cancelar', objeto=solicitud,
        descripcion='El titular retiró su solicitud de cambio.', anteriores={'estado': anterior},
        nuevos={'estado': solicitud.estado}, usuario=actor)
    notificar_personal_cambio(solicitud, titulo=gettext('Solicitud de cambio retirada'),
        mensaje=(f'{reserva.nombre_completo_solicitante} retiró su solicitud de '
                 'cambio. La reserva vigente no se modifica.'), clave='retirada')
    return solicitud
