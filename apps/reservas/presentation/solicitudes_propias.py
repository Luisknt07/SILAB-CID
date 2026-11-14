"""Solicitudes y cancelacion propias, sin permisos de operacion administrativa."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext

from apps.reservas.models.reservas import Reserva, SolicitudCambioReserva
from apps.reservas.workflows.reservas import TransicionReservaNoPermitida, validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cambios import asegurar_revision_inicial, cerrar_solicitudes_activas, instantanea_reserva
from apps.reservas.presentation.decisiones_cambio import notificar_personal_cambio


class SolicitudCambioActiva(ValidationError):
    """Conflicto conocido; solo incluye expediente ya autorizado para el actor."""
    def __init__(self, solicitud=None):
        self.solicitud = solicitud
        super().__init__(gettext('La reserva ya tiene una solicitud de cambio activa.'), code='solicitud_activa')


def _cargar_reserva_propia(reserva, actor, operacion, unidad_esperada):
    """Caller atomic: alias principal, fila vigente bloqueada y autoridad propia."""
    if reserva._state.db not in {None, 'default'}:
        raise ValidationError(gettext('Las solicitudes propias requieren la base de datos principal.'), code='no_disponible')
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    reserva = Reserva.objects.select_for_update(of=('self',)).filter(pk=reserva.pk).first()
    if reserva is None:
        raise ValidationError(gettext('La reserva ya no está disponible.'), code='no_disponible')
    actor = exigir_autoridad_reserva(reserva, actor, operacion=operacion, unidad_esperada=alcance)
    return reserva, actor


@operacion_reservas
def crear_solicitud_cambio(reserva, *, actor, motivo, request=None, unidad_esperada=None):
    """Crea una solicitud y su revision base/aviso/auditoria en una transaccion."""
    try:
        with transaction.atomic():
            reserva, actor = _cargar_reserva_propia(reserva, actor, 'solicitar_cambio', unidad_esperada)
            if not isinstance(motivo, str) or len(motivo.strip()) < 10:
                raise ValidationError(gettext('Explica el cambio que necesitas en al menos 10 caracteres.'), code='motivo_invalido')
            motivo = motivo.strip()
            if len(motivo) > 1200:
                raise ValidationError(gettext('El motivo no puede superar 1200 caracteres.'), code='motivo_invalido')
            if reserva.estado not in {'pendiente', 'confirmada'}:
                raise ValidationError(gettext('Solo se pueden solicitar cambios antes de iniciar la atención.'), code='estado_cerrado')
            existente = (reserva.solicitudes_cambio.select_for_update(of=('self',))
                         .filter(estado__in=SolicitudCambioReserva.ESTADOS_ACTIVOS).first())
            vencida_id = None
            if existente:
                if existente.autorizacion_vencida:
                    vencida_id = existente.pk
                    # Mantener fechas y propuesta del historial anterior.
                    SolicitudCambioReserva.objects.filter(pk=existente.pk).update(estado='vencida')
                else:
                    existente.reserva = reserva
                    raise SolicitudCambioActiva(existente)
            asegurar_revision_inicial(reserva, actor=actor)
            solicitud = SolicitudCambioReserva.objects.create(
                reserva=reserva, solicitada_por=actor, motivo_solicitud=motivo,
                datos_base=instantanea_reserva(reserva))
            registrar_auditoria(request, unidad=reserva.laboratorio, accion='crear', objeto=solicitud,
                descripcion='El titular solicitó autorización para modificar la reserva.',
                anteriores={'solicitud_vencida': vencida_id} if vencida_id else None,
                nuevos={'estado': solicitud.estado, 'motivo': motivo}, usuario=actor)
            notificar_personal_cambio(solicitud)
            return solicitud
    except IntegrityError as error:
        # Traducir solo la restriccion conocida; no disfrazar otro fallo de datos.
        diagnostico = getattr(error.__cause__, 'diag', None)
        if getattr(diagnostico, 'constraint_name', None) == 'una_solicitud_cambio_activa_por_reserva':
            raise SolicitudCambioActiva() from error
        raise


@operacion_reservas
@transaction.atomic
def cancelar_reserva_propia(reserva, *, actor, motivo='', request=None, unidad_esperada=None):
    """Cancela una pendiente propia y cierra cambios activos sin borrar historial."""
    reserva, actor = _cargar_reserva_propia(reserva, actor, 'cancelar_propia', unidad_esperada)
    if reserva.estado != 'pendiente':
        raise ValidationError(gettext('Solo se pueden cancelar solicitudes que todavía están pendientes.'), code='estado_cerrado')
    if not isinstance(motivo, str):
        raise ValidationError(gettext('El motivo de cancelación debe ser texto.'), code='motivo_invalido')
    motivo_usuario = motivo.strip()[:500]
    descripcion = 'Cancelación solicitada por el titular de la reserva.' + (
        f' Motivo: {motivo_usuario}' if motivo_usuario else '')
    try:
        nuevo_estado = validar_accion_reserva(reserva.estado, 'cancelar', motivo=descripcion)
    except TransicionReservaNoPermitida as error:
        raise ValidationError(gettext('Solo se pueden cancelar solicitudes que todavía están pendientes.'), code='estado_cerrado') from error
    estado_anterior = reserva.estado
    reserva.registrar_cancelacion(actor=actor, origen='solicitante', motivo=motivo_usuario)
    reserva.save(update_fields=['estado', 'fecha_actualizacion', 'cancelada_en', 'cancelada_por',
        'origen_cancelacion', 'motivo_cancelacion', 'observaciones_validacion'])
    cerrar_solicitudes_activas(reserva, motivo=descripcion, actor=actor)
    registrar_auditoria(request, unidad=reserva.laboratorio, accion='actualizar', objeto=reserva,
        descripcion=descripcion, anteriores={'estado': estado_anterior},
        nuevos={'estado': nuevo_estado}, usuario=actor)
    return reserva
