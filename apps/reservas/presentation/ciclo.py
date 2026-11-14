"""Diagnóstico preventivo del ciclo operativo de las reservas.

Este módulo no cambia decisiones humanas. Detecta reservas activas que pueden
verse afectadas por cambios posteriores a su creación: equipos fuera de
servicio, espacios o software deshabilitados, bloqueos de agenda, cruces de
capacidad y falta proyectada de insumos.
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import ESTADOS_OCUPAN_AGENDA

from apps.reservas.presentation.elegibilidad import riesgos_elegibilidad_recursos

from apps.reservas.presentation.availability import evaluate_administrative_block_conflicts, evaluate_selection_conflicts, reservation_hours, reservation_space_ids, reservation_unit_ids


ACTIVE_OPERATIONAL_STATUSES = tuple(ESTADOS_OCUPAN_AGENDA)


def operational_alert_horizon_days():
    return max(
        1,
        int(getattr(settings, "RESERVATION_OPERATIONAL_ALERT_DAYS", 30)),
    )


def reservas_en_horizonte_operativo(*, unidad=None, ahora=None):
    """Obtiene las reservas que todavía requieren vigilancia operativa."""
    ahora = ahora or timezone.now()
    hoy = timezone.localdate(ahora)
    hasta = hoy + timedelta(days=operational_alert_horizon_days())
    queryset = (
        Reserva.objects.filter(
            estado__in=ACTIVE_OPERATIONAL_STATUSES,
            fecha__range=(hoy, hasta),
        )
        .select_related(
            "laboratorio",
            "laboratorio__administrador",
            "responsable_asignado__usuario",
        )
        .prefetch_related(
            "espacios_solicitados",
            "software_solicitado__equipos_instalados",
            "consumibles_solicitados__consumible",
        )
        .order_by("fecha", "hora_inicio", "pk")
    )
    if unidad is not None:
        queryset = queryset.filter(laboratorio=unidad)
    return queryset


def _decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _risk(code, detail, *, level="critico"):
    return {"codigo": code, "detalle": detail, "nivel": level}


def _deduplicate_risks(risks):
    unique = []
    seen = set()
    for risk in risks:
        key = (risk["codigo"], risk["detalle"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(risk)
    return unique


def _reservation_slot_keys(reservation):
    return {
        (reservation.fecha.isoformat(), hour) for hour in reservation_hours(reservation)
    }


def analizar_riesgos_operativos_reservas(*, unidad=None, ahora=None, reservas=None):
    """Retorna únicamente reservas afectadas, con motivos concretos y trazables.

    La proyección de materiales respeta el orden cronológico: el stock de
    seguridad no se compromete y cada reserva posterior ve descontado lo ya
    requerido por las anteriores.
    """
    ahora = ahora or timezone.now()
    if reservas is None:
        reservas = list(reservas_en_horizonte_operativo(unidad=unidad, ahora=ahora))
    else:
        reservas = sorted(
            list(reservas),
            key=lambda item: (item.fecha, item.hora_inicio, item.pk),
        )
    if not reservas:
        return []

    reservation_ids = {reservation.pk for reservation in reservas}
    unit_ids = {reservation.laboratorio_id for reservation in reservas}
    selected_equipment_ids = {
        equipment_id
        for reservation in reservas
        for equipment_id in reservation_unit_ids(reservation)
    }
    equipment_by_id = {
        equipment.pk: equipment
        for equipment in UnidadEquipo.objects.filter(pk__in=selected_equipment_ids)
        .select_related("equipo", "laboratorio")
        .prefetch_related("laboratorios")
    }

    first_date = min(reservation.fecha for reservation in reservas)
    last_date = max(reservation.fecha for reservation in reservas)
    blocks_by_unit = defaultdict(list)
    for block in (
        BloqueoAgendaUnidad.objects.filter(
            unidad_id__in=unit_ids,
            activo=True,
            fecha_inicio__lte=last_date,
            fecha_fin__gte=first_date,
        )
        .prefetch_related("espacios", "equipos")
        .order_by("fecha_inicio", "hora_inicio", "pk")
    ):
        blocks_by_unit[block.unidad_id].append(block)

    active_by_unit_and_date = defaultdict(list)
    all_active = (
        Reserva.objects.filter(
            laboratorio_id__in=unit_ids,
            estado__in=ACTIVE_OPERATIONAL_STATUSES,
            fecha__range=(first_date, last_date),
        )
        .select_related("laboratorio")
        .prefetch_related("espacios_solicitados", "software_solicitado")
    )
    for active in all_active:
        active_by_unit_and_date[(active.laboratorio_id, active.fecha)].append(active)

    remaining_stock = {}
    affected = []
    for reservation in reservas:
        risks = []
        equipment_ids = reservation_unit_ids(reservation)
        spaces = list(reservation.espacios_solicitados.all())
        software_items = list(reservation.software_solicitado.all())
        slot_keys = _reservation_slot_keys(reservation)

        risks.extend(
            riesgos_elegibilidad_recursos(
                reservation, equipment_by_id, spaces, software_items
            )
        )

        administrative_conflicts = evaluate_administrative_block_conflicts(
            blocks_by_unit[reservation.laboratorio_id],
            selected_unit_ids=equipment_ids,
            selected_space_ids=reservation_space_ids(reservation),
            includes_space=(
                reservation.incluye_espacio or reservation.solicito_espacio
            ),
            space_scope=reservation.alcance_espacio,
            request_kind=reservation.tipo_solicitud,
        )
        block_reasons = {
            reason
            for key, reasons in administrative_conflicts.items()
            if key in slot_keys
            for reason in reasons
        }
        for reason in sorted(block_reasons):
            risks.append(_risk("bloqueo_agenda", reason))

        concurrent = [
            item
            for item in active_by_unit_and_date[
                (reservation.laboratorio_id, reservation.fecha)
            ]
            if item.pk not in reservation_ids or item.pk != reservation.pk
        ]
        selection_conflicts = evaluate_selection_conflicts(
            concurrent,
            selected_unit_ids=equipment_ids,
            selected_spaces=spaces,
            includes_space=(
                reservation.incluye_espacio or reservation.solicito_espacio
            ),
            space_scope=reservation.alcance_espacio,
            selected_software=software_items,
            purpose=reservation.proposito_codigo,
            participant_count=reservation.numero_participantes,
            unit_capacity=getattr(reservation.laboratorio, "capacidad", 0) or 0,
        )
        overlap_reasons = {
            reason
            for key, reasons in selection_conflicts.items()
            if key in slot_keys
            for reason in reasons
        }
        for reason in sorted(overlap_reasons):
            risks.append(_risk("conflicto_capacidad", reason, level="advertencia"))

        if reservation.provision_consumibles == "unidad":
            for line in reservation.consumibles_solicitados.all():
                consumable = line.consumible
                amount = (
                    line.cantidad_aprobada
                    if line.cantidad_aprobada is not None
                    else line.cantidad_solicitada
                )
                if amount is None:
                    risks.append(
                        _risk(
                            "insumo_por_calcular",
                            f"Falta calcular la cantidad de {consumable.nombre}.",
                            level="advertencia",
                        )
                    )
                    continue
                amount = _decimal(amount)
                if consumable.pk not in remaining_stock:
                    remaining_stock[consumable.pk] = max(
                        Decimal("0"),
                        _decimal(consumable.stock_total)
                        - _decimal(consumable.stock_seguridad),
                    )
                available = remaining_stock[consumable.pk]
                unit_name = consumable.unidad_medida or "unidades"
                if not consumable.activo:
                    risks.append(
                        _risk(
                            "insumo_inactivo",
                            f"{consumable.nombre} está inactivo en inventario.",
                        )
                    )
                elif amount > available:
                    risks.append(
                        _risk(
                            "stock_proyectado_insuficiente",
                            (
                                f"{consumable.nombre} requiere {amount:g} {unit_name}; "
                                f"solo quedan {available:g} {unit_name} comprometibles "
                                "sin tocar el stock de seguridad."
                            ),
                        )
                    )
                remaining_stock[consumable.pk] = max(
                    Decimal("0"),
                    available - amount,
                )

        risks = _deduplicate_risks(risks)
        if risks:
            affected.append(
                {
                    "reserva": reservation,
                    "riesgos": risks,
                    "nivel": (
                        "critico"
                        if any(item["nivel"] == "critico" for item in risks)
                        else "advertencia"
                    ),
                }
            )
    return affected
