"""Trazabilidad compartida de las mutaciones del expediente de reserva."""

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType

from apps.reservas.models.reservas import Reserva


def agregar_observacion(reserva, etiqueta, observacion):
    detalle = f"{etiqueta}: {observacion}" if observacion else etiqueta
    anterior = (reserva.observaciones_validacion or "").strip()
    reserva.observaciones_validacion = "\n".join(
        parte for parte in (anterior, detalle) if parte
    )


def registrar_accion_reserva(usuario, reserva, etiqueta, estado_anterior, observacion):
    responsable = (
        reserva.responsable_asignado.nombre_publico
        if reserva.responsable_asignado_id
        else "Sin asignar"
    )
    mensaje = (
        f"{etiqueta}. Estado: {estado_anterior} → {reserva.estado}. "
        f"Responsable: {responsable}."
    )
    if observacion:
        mensaje += f" Observación: {observacion}"
    LogEntry.objects.log_action(
        user_id=usuario.pk,
        content_type_id=ContentType.objects.get_for_model(Reserva).pk,
        object_id=str(reserva.pk),
        object_repr=str(reserva)[:200],
        action_flag=CHANGE,
        change_message=mensaje,
    )


def instantanea_reserva_para_auditoria(reserva):
    """Representación estable usada por el historial visible de la reserva."""
    registros = list(
        reserva.registros_participantes.order_by("rol", "nombre").values(
            "nombre", "rol", "asistencia"
        )
    )
    return {
        "estado": reserva.estado,
        "titulo": reserva.titulo_solicitud,
        "fecha": reserva.fecha.isoformat() if reserva.fecha else "",
        "hora_inicio": reserva.hora_inicio.strftime("%H:%M") if reserva.hora_inicio else "",
        "hora_fin": reserva.hora_fin.strftime("%H:%M") if reserva.hora_fin else "",
        "participantes": reserva.numero_participantes,
        "proposito": reserva.proposito_codigo,
        "motivo": reserva.motivo,
        "descripcion": reserva.descripcion_proyecto,
        "requisitos": reserva.requisitos_especiales,
        "responsable_id": reserva.responsable_asignado_id,
        "responsable": (
            reserva.responsable_asignado.nombre_publico
            if reserva.responsable_asignado_id
            else ""
        ),
        "equipos": [
            " · ".join(
                str(parte)
                for parte in (item.get("codigo", ""), item.get("nombre", ""))
                if parte
            )
            for item in reserva.get_unidades_seleccionadas_list()
            if isinstance(item, dict)
        ],
        "software": list(reserva.software_solicitado.values_list("nombre", flat=True)),
        "espacios": list(reserva.espacios_solicitados.values_list("nombre", flat=True)),
        "servicios": list(reserva.servicios_solicitados.values_list("nombre", flat=True)),
        "participantes_identificados": [item["nombre"] for item in registros],
        "asistencia": [
            f'{item["nombre"]}: {item["asistencia"]}' for item in registros
        ],
        "consumibles": [
            (
                f"{item.consumible.nombre}: solicitada "
                f"{item.cantidad_solicitada if item.cantidad_solicitada is not None else 'por revisar'}, "
                f"aprobada {item.cantidad_aprobada if item.cantidad_aprobada is not None else 'sin definir'}, "
                f"consumida {item.cantidad_consumida}, "
                f"desperdiciada {item.cantidad_desperdiciada}"
            )
            for item in reserva.consumibles_solicitados.select_related("consumible")
        ],
        "provision_consumibles": reserva.provision_consumibles,
        "modalidad_servicio": reserva.modalidad_servicio,
        "urgencia_servicio": reserva.urgencia_servicio,
        "fecha_entrega_prevista": (
            reserva.fecha_entrega_prevista.isoformat()
            if reserva.fecha_entrega_prevista else ""
        ),
        "costo_estimado": (
            str(reserva.costo_estimado) if reserva.costo_estimado is not None else ""
        ),
        "descuento_aplicado": str(reserva.descuento_aplicado),
        "metodo_pago": reserva.metodo_pago,
        "cotizacion_aceptada": reserva.cotizacion_aceptada,
        "beneficiario": reserva.alcance_beneficiario,
        "entidad_beneficiaria": reserva.entidad_beneficiaria,
        "archivos": list(
            reserva.archivos_tecnicos.values_list("nombre_original", flat=True)
        ),
        "ejecucion": reserva.detalle_ejecucion or {},
    }
