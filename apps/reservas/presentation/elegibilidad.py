"""Compuerta fresca de recursos antes de aprobar o iniciar una reserva.

Comparte el diagnóstico de catálogo con el ciclo preventivo y las reglas de
agenda existentes. No certifica operatividad física ni modifica inventarios.
El llamador mantiene Unidad → Reserva bloqueadas dentro de la transacción.
"""

import json

from django.conf import settings

from apps.recursos.models.unidades import UnidadEquipo

from apps.reservas.presentation.availability import reservation_unit_ids
from apps.reservas.presentation.conflictos import validar_conflictos_recursos

UNAVAILABLE_EQUIPMENT_STATUSES = {
    "mantenimiento",
    "dañado",
    "prestado",
    "no_disponible",
}


def _risk(code, detail, *, level="critico"):
    return {"codigo": code, "detalle": detail, "nivel": level}


def _equipment_belongs_to_unit(equipment, unit_id):
    if equipment.laboratorio_id == unit_id:
        return True
    asociadas = getattr(equipment, "_prefetched_objects_cache", {}).get("laboratorios")
    if asociadas is not None:
        return any(unidad.pk == unit_id for unidad in asociadas)
    return equipment.laboratorios.filter(pk=unit_id).exists()


def riesgos_elegibilidad_recursos(reservation, equipment_by_id, spaces, software_items):
    """Reglas de catálogo usadas también por los avisos preventivos de ciclo."""
    risks = []
    equipment_ids = reservation_unit_ids(reservation)
    for equipment_id in sorted(equipment_ids):
        equipment = equipment_by_id.get(equipment_id)
        if equipment is None:
            risks.append(
                _risk(
                    "equipo_inexistente",
                    f"El equipo físico #{equipment_id} ya no existe en el catálogo.",
                )
            )
            continue
        name = f"{equipment.equipo.nombre} ({equipment.codigo_unidad})"
        if not _equipment_belongs_to_unit(equipment, reservation.laboratorio_id):
            risks.append(
                _risk(
                    "equipo_fuera_unidad",
                    f"{name} ya no está asociado a este laboratorio.",
                )
            )
        elif not equipment.activa:
            risks.append(_risk("equipo_inactivo", f"{name} fue retirado del servicio."))
        elif equipment.estado_unidad in UNAVAILABLE_EQUIPMENT_STATUSES:
            risks.append(
                _risk(
                    "equipo_no_disponible",
                    f"{name} está {equipment.get_estado_unidad_display().lower()}.",
                )
            )

    for space in spaces:
        if space.unidad_id != reservation.laboratorio_id:
            risks.append(
                _risk(
                    "espacio_fuera_unidad",
                    f"El espacio {space.nombre} ya no pertenece a este laboratorio.",
                )
            )
        elif not space.activo or not space.reservable:
            risks.append(
                _risk(
                    "espacio_no_disponible",
                    f"El espacio {space.nombre} no está habilitado para reservas.",
                )
            )

    for software in software_items:
        if software.unidad_id != reservation.laboratorio_id:
            risks.append(
                _risk(
                    "software_fuera_unidad",
                    f"{software.nombre} ya no pertenece a este laboratorio.",
                )
            )
            continue
        if not software.activo:
            risks.append(
                _risk(
                    "software_inactivo",
                    f"{software.nombre} está deshabilitado.",
                )
            )
        elif int(software.licencias_disponibles or 0) <= 0:
            risks.append(
                _risk(
                    "software_sin_licencias",
                    f"{software.nombre} no tiene licencias disponibles.",
                )
            )
        installed = list(software.equipos_instalados.all())
        if (
            software.tipo_acceso == "instalacion"
            and installed
            and not any(
                item.activa and item.estado_unidad == "disponible" for item in installed
            )
        ):
            risks.append(
                _risk(
                    "software_sin_equipo",
                    f"{software.nombre} no tiene un equipo instalado disponible.",
                )
            )

    return risks


def _seleccion_equipos_valida(reserva):
    """Normaliza identificadores heredados sin omitir selecciones corruptas."""
    raw = reserva.unidades_seleccionadas
    if raw in (None, ""):
        return []
    mensaje = (
        "La selección de equipos de la reserva no es válida. "
        "Revisa los recursos seleccionados antes de continuar."
    )
    try:
        seleccion = json.loads(raw)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(mensaje) from error
    if not isinstance(seleccion, list):
        raise ValueError(mensaje)
    normalizada = []
    for item in seleccion:
        valor = item.get("id") if isinstance(item, dict) else item
        if isinstance(valor, bool) or not isinstance(valor, (int, str)):
            raise ValueError(mensaje)
        try:
            identificador = int(valor)
        except (TypeError, ValueError) as error:
            raise ValueError(mensaje) from error
        if not 0 < identificador <= 2**63 - 1:
            raise ValueError(mensaje)
        normalizada.append(
            dict(item, id=identificador)
            if isinstance(item, dict)
            else {"id": identificador}
        )
    return normalizada


def validar_elegibilidad_reserva(reserva):
    """Relee recursos acotados y aplica las reglas actuales de elegibilidad.

    Los equipos seleccionados, licencias y espacios se bloquean en orden fijo
    por tipo y PK. No usa fotografías del navegador ni un diagnóstico viejo.
    Las decisiones retrospectivas de cierre no invocan esta compuerta.
    """
    seleccion = _seleccion_equipos_valida(reserva)
    ids = {item["id"] for item in seleccion}
    equipos = {
        equipo.pk: equipo
        for equipo in UnidadEquipo.objects.filter(pk__in=ids)
        .select_related("equipo")
        .prefetch_related("laboratorios")
        .order_by("pk")
        .select_for_update(of=("self",))
    }
    software = list(
        reserva.software_solicitado.all()
        .prefetch_related("equipos_instalados")
        .order_by("pk")
        .select_for_update(of=("self",))
    )
    espacios = list(
        reserva.espacios_solicitados.all()
        .order_by("pk")
        .select_for_update(of=("self",))
    )
    riesgos = riesgos_elegibilidad_recursos(reserva, equipos, espacios, software)
    if getattr(settings, "CITT_EXIGIR_EQUIPOS_VERIFICADOS", False):
        riesgos.extend(
            _risk(
                "equipo_sin_verificar",
                f"{equipo.equipo.nombre} ({equipo.codigo_unidad}) no tiene existencia verificada.",
            )
            for equipo in equipos.values()
            if not equipo.existencia_verificada
        )
    if riesgos:
        raise ValueError(
            " ".join(dict.fromkeys(riesgo["detalle"] for riesgo in riesgos))
        )
    validar_conflictos_recursos(
        reserva.laboratorio,
        reserva.fecha,
        reserva.hora_inicio,
        reserva.hora_fin,
        seleccion,
        software,
        espacios,
        incluye_espacio=(reserva.incluye_espacio or reserva.solicito_espacio),
        alcance_espacio=reserva.alcance_espacio,
        tipo_solicitud=reserva.tipo_solicitud,
        modalidad_servicio=reserva.modalidad_servicio,
        proposito_codigo=reserva.proposito_codigo,
        numero_participantes=reserva.numero_participantes,
        bloquear_existentes=True,
        excluir_reserva_id=reserva.pk,
    )
