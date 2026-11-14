"""Inicio y cierres alternos de una reserva vigente."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.reservas.workflows.reservas import validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.plantas_piloto.operacion.presentation.gestion_produccion import cancelar_orden_de_practica
from apps.gestion_unidades.presentation.permisos import puede_corregir_reservas_cerradas_unidad
from apps.formacion.presentation.practicas_integracion import validar_compuerta_documental
from apps.reservas.presentation.seguridad import validar_inicio
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cambios import cerrar_solicitudes_activas
from apps.reservas.presentation.elegibilidad import validar_elegibilidad_reserva
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.reservas.presentation.responsables import resolver_responsable_operativo
from apps.reservas.presentation.trazabilidad import agregar_observacion, instantanea_reserva_para_auditoria, registrar_accion_reserva


ETIQUETAS_TRANSICIONES_OPERATIVAS = {
    "iniciar": "Atención iniciada",
    "no_presentado": "Inasistencia registrada",
    "no_atendida": "Reserva no atendida por la unidad",
}
ACCIONES_CIERRE_ALTERNATIVO = frozenset({"no_presentado", "no_atendida"})


def _normalizar_observacion(accion, observacion):
    if not isinstance(observacion, str):
        raise ValidationError(
            gettext("La observación debe ser texto."), code="observacion_invalida"
        )
    observacion = observacion.strip()
    if accion in ACCIONES_CIERRE_ALTERNATIVO and not observacion:
        raise ValidationError(
            gettext("Registra el motivo de esta decisión."),
            code="observacion_requerida",
        )
    if len(observacion) > 1200:
        raise ValidationError(
            gettext("La observación no puede superar 1200 caracteres."),
            code="observacion_invalida",
        )
    return observacion


@operacion_reservas
@transaction.atomic
def transicionar_reserva_operativa(
    reserva,
    *,
    actor,
    accion,
    observacion="",
    responsable_id=None,
    request=None,
    unidad_esperada=None,
):
    """Inicia o cierra sin atencion con autoridad y estado persistidos."""
    if accion not in ETIQUETAS_TRANSICIONES_OPERATIVAS:
        raise ValidationError(
            gettext("Selecciona una transición operativa válida."),
            code="accion_invalida",
        )
    if reserva._state.db not in {None, "default"}:
        raise ValidationError(
            gettext(
                "Las transiciones operativas requieren la base de datos principal."
            ),
            code="no_disponible",
        )
    observacion = _normalizar_observacion(accion, observacion)
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    if accion == "iniciar":
        # Mismo orden de aprobación: unidad → reserva → recursos.
        Unidad.objects.select_for_update(of=("self",)).filter(pk=alcance).first()
    reserva = (
        Reserva.objects.select_for_update(of=("self",))
        .select_related("laboratorio", "responsable_asignado")
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
        operacion="transicionar_reserva_operativa",
        unidad_esperada=alcance,
    )
    if accion == "iniciar":
        validar_compuerta_documental(reserva, accion)

    responsable = reserva.responsable_asignado
    if responsable_id not in {None, ""}:
        responsable = resolver_responsable_operativo(reserva, responsable_id)

    estado_nuevo = validar_accion_reserva(
        reserva.estado,
        accion,
        motivo=observacion,
        puede_corregir_cerradas=puede_corregir_reservas_cerradas_unidad(
            actor, reserva.laboratorio
        ),
        permite_regularizacion=reserva.requiere_regularizacion_operativa,
    )
    if accion == "iniciar":
        validar_elegibilidad_reserva(reserva)
        validar_inicio(reserva)
    elif not (
        reserva.requiere_cierre_operativo or reserva.requiere_regularizacion_operativa
    ):
        mensaje = (
            gettext("La inasistencia se registra después de finalizar el horario.")
            if accion == "no_presentado"
            else gettext("Este cierre se registra después de finalizar el horario.")
        )
        raise ValueError(mensaje)

    etiqueta = ETIQUETAS_TRANSICIONES_OPERATIVAS[accion]
    estado_anterior = reserva.estado
    datos_anteriores = instantanea_reserva_para_auditoria(reserva)
    reserva.responsable_asignado = responsable
    reserva.estado = estado_nuevo
    campos = ["responsable_asignado", "estado", "fecha_actualizacion"]
    if accion == "iniciar":
        reserva.fecha_inicio_atencion = timezone.now()
        campos.append("fecha_inicio_atencion")
    else:
        reserva.resultado_cierre = accion
        reserva.fecha_cierre = timezone.now()
        reserva.detalle_cierre = observacion
        campos.extend(["resultado_cierre", "fecha_cierre", "detalle_cierre"])
        if accion == "no_presentado":
            reserva.registros_participantes.update(asistencia="no_asistio")
    agregar_observacion(reserva, etiqueta, observacion)
    campos.append("observaciones_validacion")
    reserva.save(update_fields=campos)

    if accion in ACCIONES_CIERRE_ALTERNATIVO and reserva.receta_id:
        cancelar_orden_de_practica(reserva, etiqueta)
    cerrar_solicitudes_activas(
        reserva,
        motivo=(
            f"La reserva pasó a {reserva.get_estado_display()}; "
            "la solicitud de cambio ya no aplica."
        ),
        actor=actor,
    )
    if accion in ACCIONES_CIERRE_ALTERNATIVO:
        reserva.notificaciones.filter(tipo="cierre_pendiente", leida=False).update(
            leida=True
        )
        reserva.notificaciones.filter(
            leida=False, clave__contains=":riesgo_operativo:"
        ).update(leida=True)
    if reserva.responsable_asignado_id:
        reserva.notificaciones.filter(
            leida=False, clave__contains=":sin_responsable"
        ).update(leida=True)

    notificar_cambio_reserva(reserva, accion, observacion)
    registrar_accion_reserva(actor, reserva, etiqueta, estado_anterior, observacion)
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="archivar" if accion in ACCIONES_CIERRE_ALTERNATIVO else "actualizar",
        objeto=reserva,
        descripcion=f"{etiqueta}: {observacion}" if observacion else etiqueta,
        anteriores=datos_anteriores,
        nuevos=instantanea_reserva_para_auditoria(reserva),
        usuario=actor,
    )
    return reserva
