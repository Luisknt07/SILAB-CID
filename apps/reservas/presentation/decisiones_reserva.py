"""Rechazo y cancelacion administrativa de reservas vigentes."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.reservas.models.reservas import Reserva
from apps.reservas.workflows.reservas import validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.plantas_piloto.operacion.presentation.gestion_produccion import cancelar_orden_de_practica
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cambios import cerrar_solicitudes_activas
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.reservas.presentation.trazabilidad import agregar_observacion, instantanea_reserva_para_auditoria, registrar_accion_reserva


ETIQUETAS_DECISIONES_RESERVA = {
    "rechazar": "Solicitud rechazada",
    "cancelar": "Reserva cancelada",
}


def _normalizar_motivo(motivo):
    if not isinstance(motivo, str):
        raise ValidationError(
            gettext("El motivo de la decisión debe ser texto."),
            code="motivo_invalido",
        )
    motivo = motivo.strip()
    if not motivo:
        raise ValidationError(
            gettext("Registra el motivo de esta decisión."),
            code="motivo_requerido",
        )
    if len(motivo) > 1200:
        raise ValidationError(
            gettext("El motivo de la decisión no puede superar 1200 caracteres."),
            code="motivo_invalido",
        )
    return motivo


@operacion_reservas
@transaction.atomic
def decidir_reserva(
    reserva,
    *,
    actor,
    accion,
    motivo,
    request=None,
    unidad_esperada=None,
):
    """Cierra una evaluacion con autoridad y estado persistidos vigentes.

    La reserva se bloquea antes de validar la transicion. El cambio de estado,
    sus efectos en produccion y solicitudes pendientes, la notificacion y la
    trazabilidad se confirman o revierten como una sola operacion.
    """
    if accion not in ETIQUETAS_DECISIONES_RESERVA:
        raise ValidationError(
            gettext("Selecciona una decisión de reserva válida."),
            code="accion_invalida",
        )
    if reserva._state.db not in {None, "default"}:
        raise ValidationError(
            gettext("Las decisiones de reserva requieren la base de datos principal."),
            code="no_disponible",
        )
    motivo = _normalizar_motivo(motivo)
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    reserva = (
        Reserva.objects.select_for_update(of=("self",))
        .filter(pk=reserva.pk)
        .first()
    )
    if reserva is None:
        raise ValidationError(
            gettext("La reserva ya no está disponible."), code="no_disponible"
        )
    actor = exigir_autoridad_reserva(
        reserva,
        actor,
        operacion=f"{accion}_reserva",
        unidad_esperada=alcance,
    )
    nuevo_estado = validar_accion_reserva(reserva.estado, accion, motivo=motivo)

    etiqueta = ETIQUETAS_DECISIONES_RESERVA[accion]
    estado_anterior = reserva.estado
    datos_anteriores = instantanea_reserva_para_auditoria(reserva)
    if accion == "rechazar":
        reserva.estado = nuevo_estado
        reserva.validada_por = actor
        reserva.fecha_validacion = timezone.now()
        agregar_observacion(reserva, etiqueta, motivo)
        campos = [
            "estado",
            "validada_por",
            "fecha_validacion",
            "observaciones_validacion",
            "fecha_actualizacion",
        ]
    else:
        reserva.registrar_cancelacion(
            actor=actor,
            origen="laboratorio",
            motivo=motivo,
        )
        campos = [
            "estado",
            "cancelada_en",
            "cancelada_por",
            "origen_cancelacion",
            "motivo_cancelacion",
            "observaciones_validacion",
            "fecha_actualizacion",
        ]
    reserva.save(update_fields=campos)

    if reserva.receta_id:
        cancelar_orden_de_practica(reserva, etiqueta)
    cerrar_solicitudes_activas(
        reserva,
        motivo=(
            f"La reserva pasó a {reserva.get_estado_display()}; "
            "la solicitud de cambio ya no aplica."
        ),
        actor=actor,
    )
    if accion == "cancelar":
        reserva.notificaciones.filter(
            tipo="cierre_pendiente", leida=False
        ).update(leida=True)
    if reserva.responsable_asignado_id:
        reserva.notificaciones.filter(
            leida=False, clave__contains=":sin_responsable"
        ).update(leida=True)
    reserva.notificaciones.filter(
        leida=False, clave__contains=":riesgo_operativo:"
    ).update(leida=True)

    notificar_cambio_reserva(reserva, accion, motivo)
    registrar_accion_reserva(actor, reserva, etiqueta, estado_anterior, motivo)
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="archivar",
        objeto=reserva,
        descripcion=f"{etiqueta}: {motivo}",
        anteriores=datos_anteriores,
        nuevos=instantanea_reserva_para_auditoria(reserva),
        usuario=actor,
    )
    return reserva
