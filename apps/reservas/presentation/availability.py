"""Reglas compartidas de ocupacion para el calendario y el registro de reservas.

La disponibilidad se calcula por el alcance real de la solicitud, no por el
hecho de que dos actividades pertenezcan a la misma unidad. Esto permite que
dos trabajos parciales convivan y, al mismo tiempo, que una reserva de toda la
unidad bloquee cualquier otro uso fisico.
"""

from collections import defaultdict
from datetime import timedelta

from apps.reservas.workflows.reservas import ESTADOS_OCUPAN_AGENDA

ACTIVE_RESERVATION_STATUSES = tuple(ESTADOS_OCUPAN_AGENDA)
DOCENCIA_PURPOSE = "docencia_practica"


def administrative_block_hours(block):
    """Convierte un bloqueo administrativo en los bloques horarios que afecta."""
    if block.dia_completo:
        return list(range(24))
    if not block.hora_inicio or not block.hora_fin:
        return []
    end = block.hora_fin.hour + (1 if block.hora_fin.minute else 0)
    return list(range(block.hora_inicio.hour, max(block.hora_inicio.hour + 1, end)))


def administrative_block_matches_selection(
    block,
    *,
    selected_unit_ids=(),
    selected_space_ids=(),
    includes_space=False,
    space_scope="",
    request_kind="recursos",
):
    """Indica si el cierre afecta la solicitud sin bloquear recursos ajenos."""
    if request_kind == "servicio":
        if not block.bloquea_servicios:
            return False
    elif not block.bloquea_recursos:
        return False

    if block.alcance == "unidad_completa":
        return True

    selected_units = {int(value) for value in selected_unit_ids}
    selected_spaces = {int(value) for value in selected_space_ids}
    selected_full_unit = bool(
        space_scope == "unidad_completa"
        or (includes_space and not selected_spaces and not space_scope)
    )
    if selected_full_unit:
        return True
    if block.alcance == "areas":
        return bool(selected_spaces & {item.pk for item in block.espacios.all()})
    if block.alcance == "equipos":
        return bool(selected_units & {item.pk for item in block.equipos.all()})
    return False


def evaluate_administrative_block_conflicts(
    blocks,
    *,
    selected_unit_ids=(),
    selected_space_ids=(),
    includes_space=False,
    space_scope="",
    request_kind="recursos",
):
    """Devuelve cierres aplicables indexados por fecha y hora."""
    conflicts = defaultdict(list)
    for block in blocks:
        if not administrative_block_matches_selection(
            block,
            selected_unit_ids=selected_unit_ids,
            selected_space_ids=selected_space_ids,
            includes_space=includes_space,
            space_scope=space_scope,
            request_kind=request_kind,
        ):
            continue
        current = block.fecha_inicio
        while current <= block.fecha_fin:
            for hour in administrative_block_hours(block):
                conflicts[(current.isoformat(), hour)].append(
                    f"{block.get_tipo_display()}: {block.titulo}."
                )
            current += timedelta(days=1)
    return {
        key: tuple(dict.fromkeys(reasons))
        for key, reasons in conflicts.items()
        if reasons
    }


def reservation_unit_ids(reservation):
    identifiers = set()
    for item in reservation.get_unidades_seleccionadas_list():
        candidate = item.get("id") if isinstance(item, dict) else item
        try:
            identifiers.add(int(candidate))
        except (TypeError, ValueError):
            continue
    return identifiers


def reservation_space_ids(reservation):
    relation = getattr(reservation, "espacios_solicitados", None)
    if relation is None:
        return set()
    try:
        return {space.pk for space in relation.all()}
    except (AttributeError, TypeError, ValueError):
        return set()


def reservation_software_ids(reservation):
    relation = getattr(reservation, "software_solicitado", None)
    if relation is None:
        return set()
    try:
        return {software.pk for software in relation.all()}
    except (AttributeError, TypeError, ValueError):
        return set()


def reservation_hours(reservation):
    hours = []
    for raw_hour in reservation.get_horas_seleccionadas_list():
        try:
            hour = int(raw_hour)
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23:
            hours.append(hour)
    if hours:
        return sorted(set(hours))

    start = reservation.hora_inicio.hour
    end = reservation.hora_fin.hour + (1 if reservation.hora_fin.minute else 0)
    return list(range(start, max(start + 1, end)))


def reservation_space_scope(reservation, *, space_ids=None):
    scope = getattr(reservation, "alcance_espacio", "")
    spaces = reservation_space_ids(reservation) if space_ids is None else space_ids
    includes_space = bool(getattr(reservation, "incluye_espacio", False))
    if scope in {"areas", "espacio_unico", "unidad_completa"}:
        return scope
    if spaces:
        return "areas"
    if includes_space:
        return "unidad_completa"
    return "sin_espacio"


def reservation_is_full_unit(reservation, *, space_ids=None):
    return reservation_space_scope(
        reservation,
        space_ids=space_ids,
    ) == "unidad_completa"


def reservation_is_single_space(reservation):
    return reservation_space_scope(reservation) == "espacio_unico"


def reservation_uses_physical_resources(
    reservation,
    *,
    unit_ids=None,
    space_ids=None,
):
    units = reservation_unit_ids(reservation) if unit_ids is None else unit_ids
    spaces = reservation_space_ids(reservation) if space_ids is None else space_ids
    return bool(
        units
        or spaces
        or getattr(reservation, "incluye_espacio", False)
        or getattr(reservation, "alcance_espacio", "") in {
            "areas", "espacio_unico", "unidad_completa"
        }
    )


def _safe_participant_count(value):
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def _usage_by_slot(reservations):
    """Indexa las reservas activas por bloque y por recurso.

    Es la base comun de la evaluacion de conflictos y de la ocupacion que se
    muestra en el calendario, para que ambas lean exactamente lo mismo.
    """
    usage = {
        name: defaultdict(list)
        for name in ("physical", "full_unit", "single_space", "unit", "area", "software")
    }
    for reservation in reservations:
        date_key = reservation.fecha.isoformat()
        unit_ids = reservation_unit_ids(reservation)
        space_ids = reservation_space_ids(reservation)
        software_ids = reservation_software_ids(reservation)
        full_unit = reservation_is_full_unit(reservation, space_ids=space_ids)
        single_space = reservation_is_single_space(reservation)
        uses_physical = reservation_uses_physical_resources(
            reservation,
            unit_ids=unit_ids,
            space_ids=space_ids,
        )
        for hour in reservation_hours(reservation):
            key = (date_key, hour)
            if uses_physical:
                usage["physical"][key].append(reservation)
            if full_unit:
                usage["full_unit"][key].append(reservation)
            if single_space:
                usage["single_space"][key].append(reservation)
            for unit_id in unit_ids:
                usage["unit"][(date_key, hour, unit_id)].append(reservation)
            for space_id in space_ids:
                usage["area"][(date_key, hour, space_id)].append(reservation)
            for software_id in software_ids:
                usage["software"][(date_key, hour, software_id)].append(reservation)
    return usage


def evaluate_selection_conflicts(
    reservations,
    *,
    selected_unit_ids=(),
    selected_spaces=(),
    includes_space=False,
    space_scope="",
    selected_software=(),
    purpose="",
    participant_count=1,
    unit_capacity=0,
):
    """Devuelve motivos de bloqueo indexados por ``(fecha_iso, hora)``.

    ``selected_spaces`` y ``selected_software`` son objetos de modelo porque su
    capacidad forma parte de la decision. Las reservas deben venir con sus
    relaciones de espacios y software precargadas.
    """

    selected_unit_ids = {int(identifier) for identifier in selected_unit_ids}
    selected_space_map = {space.pk: space for space in selected_spaces}
    selected_software_map = {software.pk: software for software in selected_software}
    requested_people = _safe_participant_count(participant_count)
    selected_full_unit = bool(
        space_scope == "unidad_completa"
        or (includes_space and not selected_space_map and not space_scope)
    )
    selected_single_space = space_scope == "espacio_unico"
    selected_uses_physical = bool(
        selected_unit_ids
        or selected_space_map
        or selected_full_unit
        or selected_single_space
    )

    usage = _usage_by_slot(reservations)
    physical_usage = usage["physical"]
    full_unit_usage = usage["full_unit"]
    single_space_usage = usage["single_space"]
    unit_usage = usage["unit"]
    area_usage = usage["area"]
    software_usage = usage["software"]

    all_slots = {
        (date_key, hour)
        for date_key, hour, _resource_id in (
            list(unit_usage) + list(area_usage) + list(software_usage)
        )
    }
    all_slots.update(physical_usage)
    all_slots.update(full_unit_usage)
    all_slots.update(single_space_usage)
    conflicts = defaultdict(list)

    for date_key, hour in sorted(all_slots):
        key = (date_key, hour)
        if selected_full_unit and physical_usage.get(key):
            conflicts[key].append(
                "La unidad completa ya tiene recursos físicos ocupados en este horario."
            )
        elif selected_uses_physical and full_unit_usage.get(key):
            conflicts[key].append(
                "La unidad completa ya está reservada en este horario."
            )

        if selected_space_map and single_space_usage.get(key):
            conflicts[key].append(
                "El laboratorio ya tiene una reserva registrada sobre su espacio único "
                "en este horario."
            )

        if selected_single_space:
            concurrent = single_space_usage.get(key, [])
            if concurrent:
                is_exclusive = purpose == DOCENCIA_PURPOSE or any(
                    reservation.proposito_codigo == DOCENCIA_PURPOSE
                    or reservation.tipo_uso == "practica"
                    for reservation in concurrent
                )
                if is_exclusive:
                    conflicts[key].append(
                        "El espacio único del laboratorio ya está ocupado por una "
                        "actividad docente."
                    )
                else:
                    occupied_people = sum(
                        _safe_participant_count(reservation.numero_participantes)
                        for reservation in concurrent
                    )
                    capacity = max(1, int(unit_capacity or 1))
                    if occupied_people + requested_people > capacity:
                        conflicts[key].append(
                            "El espacio único del laboratorio supera su capacidad de "
                            f"{capacity} personas con esta solicitud."
                        )

        for unit_id in selected_unit_ids:
            if unit_usage.get((date_key, hour, unit_id)):
                conflicts[key].append(
                    "Uno de los equipos seleccionados ya está reservado en este horario."
                )

        for space_id, space in selected_space_map.items():
            concurrent = area_usage.get((date_key, hour, space_id), [])
            if not concurrent:
                continue
            is_exclusive = purpose == DOCENCIA_PURPOSE or any(
                reservation.proposito_codigo == DOCENCIA_PURPOSE
                or reservation.tipo_uso == "practica"
                for reservation in concurrent
            )
            if is_exclusive:
                conflicts[key].append(
                    f"El área {space.nombre} ya está ocupada por una actividad docente."
                )
                continue
            occupied_people = sum(
                _safe_participant_count(reservation.numero_participantes)
                for reservation in concurrent
            )
            if occupied_people + requested_people > max(1, int(space.capacidad or 1)):
                conflicts[key].append(
                    f"El área {space.nombre} supera su capacidad de {space.capacidad} "
                    "personas con esta solicitud."
                )

        for software_id, software in selected_software_map.items():
            concurrent = software_usage.get((date_key, hour, software_id), [])
            capacity = max(0, int(software.licencias_disponibles or 0))
            if capacity <= 0 or len(concurrent) >= capacity:
                conflicts[key].append(
                    f"No quedan accesos concurrentes de {software.nombre} en este horario."
                )

    return {
        key: tuple(dict.fromkeys(reasons))
        for key, reasons in conflicts.items()
        if reasons
    }


def selection_occupancy(
    reservations,
    *,
    selected_spaces=(),
    includes_space=False,
    space_scope="",
    unit_capacity=0,
):
    """Personas ya presentes por ``(fecha_iso, hora)`` en el espacio elegido y
    la capacidad con la que se comparte.

    Solo informa: la decision de bloquear la toma
    ``evaluate_selection_conflicts`` con la misma regla (docencia es exclusiva;
    el resto comparte el espacio hasta llenarlo). Devuelve ``({}, 0)`` cuando la
    seleccion no comparte capacidad: sin espacio o con la unidad completa, que
    bloquea todo el laboratorio.
    """
    selected_space_map = {space.pk: space for space in selected_spaces}
    full_unit = bool(
        space_scope == "unidad_completa"
        or (includes_space and not selected_space_map and not space_scope)
    )
    if full_unit:
        return {}, 0
    if space_scope == "espacio_unico":
        capacity = max(1, int(unit_capacity or 1))
    elif selected_space_map:
        capacity = sum(
            max(1, int(space.capacidad or 1)) for space in selected_space_map.values()
        )
    else:
        return {}, 0

    usage = _usage_by_slot(reservations)
    people = defaultdict(int)
    if space_scope == "espacio_unico":
        for key, concurrent in usage["single_space"].items():
            people[key] += sum(
                _safe_participant_count(item.numero_participantes) for item in concurrent
            )
    else:
        for (date_key, hour, space_id), concurrent in usage["area"].items():
            if space_id not in selected_space_map:
                continue
            people[(date_key, hour)] += sum(
                _safe_participant_count(item.numero_participantes) for item in concurrent
            )
    return dict(people), capacity


def event_matches_selection(
    reservation,
    *,
    selected_unit_ids=(),
    selected_space_ids=(),
    selected_software_ids=(),
    includes_space=False,
    space_scope="",
):
    selected_unit_ids = set(selected_unit_ids)
    selected_space_ids = set(selected_space_ids)
    selected_software_ids = set(selected_software_ids)
    reservation_units = reservation_unit_ids(reservation)
    reservation_spaces = reservation_space_ids(reservation)
    reservation_software = reservation_software_ids(reservation)
    selected_full_unit = bool(
        space_scope == "unidad_completa"
        or (includes_space and not selected_space_ids and not space_scope)
    )
    selected_single_space = space_scope == "espacio_unico"
    existing_full_unit = reservation_is_full_unit(
        reservation,
        space_ids=reservation_spaces,
    )
    existing_single_space = reservation_is_single_space(reservation)
    selected_physical = bool(
        selected_unit_ids
        or selected_space_ids
        or selected_full_unit
        or selected_single_space
    )
    existing_physical = reservation_uses_physical_resources(
        reservation,
        unit_ids=reservation_units,
        space_ids=reservation_spaces,
    )
    return bool(
        selected_unit_ids & reservation_units
        or selected_space_ids & reservation_spaces
        or selected_software_ids & reservation_software
        or (selected_full_unit and existing_physical)
        or (existing_full_unit and selected_physical)
        or (selected_single_space and existing_single_space)
        or (selected_space_ids and existing_single_space)
        or (selected_single_space and reservation_spaces)
    )
