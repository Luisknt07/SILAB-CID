"""Operaciones administrativas simples sobre una reserva vigente."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext

from apps.reservas.models.reservas import Reserva
from apps.reservas.workflows.reservas import validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.reservas.presentation.responsables import resolver_responsable_operativo
from apps.reservas.presentation.trazabilidad import agregar_observacion, instantanea_reserva_para_auditoria, registrar_accion_reserva


ETIQUETAS_ACCIONES_ADMINISTRATIVAS = {
    "asignar": "Responsable asignado",
    "anotar": "Nota operativa registrada",
    "solicitar_info": "Información adicional solicitada",
}


def _normalizar_observacion(accion, observacion):
    if not isinstance(observacion, str):
        raise ValidationError(
            gettext("La observación debe ser texto."), code="observacion_invalida"
        )
    observacion = observacion.strip()
    if accion in {"anotar", "solicitar_info"} and not observacion:
        raise ValidationError(
            gettext("Registra el motivo de esta decisión."), code="observacion_requerida"
        )
    if len(observacion) > 1200:
        raise ValidationError(
            gettext("La observación no puede superar 1200 caracteres."),
            code="observacion_invalida",
        )
    return observacion


@operacion_reservas
@transaction.atomic
def gestionar_reserva_administrativa(
    reserva,
    *,
    actor,
    accion,
    observacion="",
    responsable_id=None,
    request=None,
    unidad_esperada=None,
):
    """Asigna o documenta una reserva con autoridad y fila vigentes.

    La reserva se bloquea antes de leer su estado y antes de resolver al
    responsable. Auditoría, bitácora y notificación forman parte de la misma
    transacción.
    """
    if accion not in ETIQUETAS_ACCIONES_ADMINISTRATIVAS:
        raise ValidationError(
            gettext("Selecciona una acción administrativa válida."),
            code="accion_invalida",
        )
    if reserva._state.db not in {None, "default"}:
        raise ValidationError(
            gettext("La gestión de reservas requiere la base de datos principal."),
            code="no_disponible",
        )
    observacion = _normalizar_observacion(accion, observacion)
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
    operacion = {
        "asignar": "asignar_responsable",
        "anotar": "anotar_reserva",
        "solicitar_info": "solicitar_informacion",
    }[accion]
    actor = exigir_autoridad_reserva(
        reserva,
        actor,
        operacion=operacion,
        unidad_esperada=alcance,
    )
    validar_accion_reserva(reserva.estado, accion, motivo=observacion)

    etiqueta = ETIQUETAS_ACCIONES_ADMINISTRATIVAS[accion]
    estado_anterior = reserva.estado
    datos_anteriores = instantanea_reserva_para_auditoria(reserva)

    if accion == "asignar":
        responsable = resolver_responsable_operativo(reserva, responsable_id)
        reserva.responsable_asignado = responsable
        reserva.save(update_fields=["responsable_asignado", "fecha_actualizacion"])
        reserva.notificaciones.filter(
            leida=False, clave__contains=":sin_responsable"
        ).update(leida=True)
    else:
        agregar_observacion(reserva, etiqueta, observacion)
        reserva.save(update_fields=["observaciones_validacion", "fecha_actualizacion"])
        if accion == "solicitar_info":
            notificar_cambio_reserva(reserva, accion, observacion)

    registrar_accion_reserva(
        actor, reserva, etiqueta, estado_anterior, observacion
    )
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="observar" if accion in {"anotar", "solicitar_info"} else "actualizar",
        objeto=reserva,
        descripcion=f"{etiqueta}: {observacion}" if observacion else etiqueta,
        anteriores=datos_anteriores,
        nuevos=instantanea_reserva_para_auditoria(reserva),
        usuario=actor,
    )
    return reserva
