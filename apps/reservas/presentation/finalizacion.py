"""Finalizacion integral y trazable de una reserva atendida."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext

from apps.reservas.models.reservas import Reserva
from apps.reservas.workflows.reservas import validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_corregir_reservas_cerradas_unidad
from apps.formacion.presentation.practicas_integracion import validar_compuerta_documental
from apps.reservas.presentation.seguridad import otorgar_habilitaciones_por_sesion
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cambios import cerrar_solicitudes_activas
from apps.reservas.presentation.ejecucion import registrar_cierre_operativo
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.reservas.presentation.participantes import actualizar_participantes_reserva
from apps.reservas.presentation.responsables import resolver_responsable_operativo
from apps.reservas.presentation.trazabilidad import agregar_observacion, instantanea_reserva_para_auditoria, registrar_accion_reserva


ETIQUETA_FINALIZACION = "Atención completada"


class CierreOperativoFueraDeHorario(ValueError):
    """La reserva confirmada todavia no habilita su cierre operativo."""


def _normalizar_observacion(observacion):
    if not isinstance(observacion, str):
        raise ValidationError(
            gettext("La observación debe ser texto."), code="observacion_invalida"
        )
    return observacion.strip()


@operacion_reservas
@transaction.atomic
def completar_reserva(
    reserva,
    *,
    actor,
    datos,
    observacion="",
    responsable_id=None,
    request=None,
    unidad_esperada=None,
):
    """Cierra la reserva y todos sus efectos dentro de una transaccion."""
    if reserva._state.db not in {None, "default"}:
        raise ValidationError(
            gettext("El cierre operativo requiere la base de datos principal."),
            code="no_disponible",
        )
    if datos is None or not hasattr(datos, "get"):
        raise ValidationError(
            gettext("Los datos del cierre no tienen un formato válido."),
            code="datos_invalidos",
        )
    observacion = _normalizar_observacion(observacion)
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
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
        operacion="cerrar_operacion",
        unidad_esperada=alcance,
    )
    validar_compuerta_documental(reserva, "completar")
    estado_anterior = reserva.estado
    datos_anteriores = instantanea_reserva_para_auditoria(reserva)
    validar_accion_reserva(
        estado_anterior,
        "completar",
        puede_corregir_cerradas=puede_corregir_reservas_cerradas_unidad(
            actor, reserva.laboratorio
        ),
        permite_regularizacion=reserva.requiere_regularizacion_operativa,
    )
    if estado_anterior == "confirmada" and not reserva.requiere_cierre_operativo:
        raise CierreOperativoFueraDeHorario(
            gettext(
                "La atención solo puede cerrarse cuando finalice su horario."
            )
        )

    responsable = reserva.responsable_asignado
    if responsable_id not in {None, ""}:
        responsable = resolver_responsable_operativo(reserva, responsable_id)
    participantes_cambiados = actualizar_participantes_reserva(reserva, datos)
    reserva.responsable_asignado = responsable
    campos_previos = ["responsable_asignado", "fecha_actualizacion"]
    if participantes_cambiados:
        campos_previos.append("numero_participantes")
    reserva.save(update_fields=campos_previos)

    detalle_ejecucion = registrar_cierre_operativo(
        reserva,
        actor,
        datos,
        unidad_esperada=alcance,
    )
    otorgar_habilitaciones_por_sesion(reserva, actor)
    reserva.detalle_cierre = detalle_ejecucion.get("observaciones") or observacion
    agregar_observacion(
        reserva,
        ETIQUETA_FINALIZACION,
        reserva.detalle_cierre,
    )
    reserva.save(
        update_fields=[
            "detalle_cierre",
            "observaciones_validacion",
            "fecha_actualizacion",
        ]
    )

    cerrar_solicitudes_activas(
        reserva,
        motivo=(
            f"La reserva pasó a {reserva.get_estado_display()}; "
            "la solicitud de cambio ya no aplica."
        ),
        actor=actor,
    )
    reserva.notificaciones.filter(tipo="cierre_pendiente", leida=False).update(
        leida=True
    )
    if reserva.responsable_asignado_id:
        reserva.notificaciones.filter(
            leida=False,
            clave__contains=":sin_responsable",
        ).update(leida=True)
    reserva.notificaciones.filter(
        leida=False,
        clave__contains=":riesgo_operativo:",
    ).update(leida=True)

    notificar_cambio_reserva(reserva, "completar", observacion)
    registrar_accion_reserva(
        actor,
        reserva,
        ETIQUETA_FINALIZACION,
        estado_anterior,
        observacion,
    )
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="actualizar",
        objeto=reserva,
        descripcion=(
            f"{ETIQUETA_FINALIZACION}: {observacion}"
            if observacion
            else ETIQUETA_FINALIZACION
        ),
        anteriores=datos_anteriores,
        nuevos=instantanea_reserva_para_auditoria(reserva),
        usuario=actor,
    )
    return reserva
