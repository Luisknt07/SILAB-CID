"""API interna para consultar inventario físico asociado a una Unidad."""

import re
import unicodedata
import json
from datetime import date, datetime

from django.db.models import Q
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.templatetags.static import static
from django.utils.translation import gettext

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.presentation.availability import ACTIVE_RESERVATION_STATUSES, administrative_block_hours, administrative_block_matches_selection, evaluate_administrative_block_conflicts, evaluate_selection_conflicts, selection_occupancy, event_matches_selection, reservation_hours as shared_reservation_hours, reservation_space_scope as shared_reservation_space_scope, reservation_space_ids as shared_reservation_space_ids, reservation_software_ids as shared_reservation_software_ids, reservation_unit_ids as shared_reservation_unit_ids


CALENDAR_ACTIVE_STATUSES = ACTIVE_RESERVATION_STATUSES
CALENDAR_MAX_RANGE_DAYS = 93


def _field_url(field):
    if not field:
        return ""
    try:
        return field.url
    except (AttributeError, ValueError):
        return ""


CATEGORIAS_PUBLICAS_EQUIPO = (
    ("Impresión 3D", ("impresora", "impresion 3d", "fdm", "sla", "resina", "filamento")),
    ("Corte y grabado", ("cortadora", "laser", "grabado", "grabadora", "plotter", "vinil")),
    ("Mecanizado", ("fresadora", "cnc", "torno", "router", "taladro", "mecanizado")),
    ("Digitalización y medición", ("escaner", "scanner", "digitaliz", "medicion", "microscopio", "camara", "fotogrametria")),
    ("Estaciones de trabajo", ("estacion", "workstation", "computador", "laptop", "ordenador", "pc")),
    ("Electrónica e instrumentación", ("osciloscopio", "multimetro", "fuente de", "generador", "soldadura", "arduino", "raspberry")),
)


def _texto_sin_acentos(valor):
    plano = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(caracter for caracter in plano if not unicodedata.combining(caracter)).lower()


def categoria_publica_equipo(equipment):
    """Categoría con la que el asistente agrupa los equipos.

    Si la unidad clasificó el equipo en su catálogo, manda esa categoría. Si
    no, se deduce del nombre, que es lo que hacía el FabLab desde el inicio.

    El catálogo no registra categorías; la palabra clave al inicio de una
    palabra del nombre o la descripción decide (impresora, cortadora, cnc...).
    """
    propia = next(
        (categoria.nombre for categoria in equipment.categorias.all() if categoria.activa),
        "",
    )
    if propia:
        return propia
    texto = _texto_sin_acentos(f"{equipment.nombre} {getattr(equipment, 'descripcion', '') or ''}")
    for categoria, palabras in CATEGORIAS_PUBLICAS_EQUIPO:
        if any(re.search(r"\b" + re.escape(palabra), texto) for palabra in palabras):
            return categoria
    return "Otros equipos"


def _public_equipment_payload(equipment):
    if equipment is None:
        return {
            "equipo_nombre": "Sin equipo",
            "equipo_codigo": "N/A",
            "equipo_id": None,
            "imagen_url": "",
            "caracteristicas_publicas": "",
            "uso_publico": "",
            "instrucciones_publicas": "",
            "marca": "",
            "modelo": "",
            "manual_url": "",
            "ficha_tecnica_url": "",
            "video_url": "",
            "categoria": "Otros equipos",
            "admite_software_adicional": False,
            "rol": "principal",
            "auxiliares": [],
            "accesorios": [],
        }
    image_url = _field_url(getattr(equipment, "imagen", None))
    if not image_url and getattr(equipment, "imagen_catalogo", ""):
        image_url = static(equipment.imagen_catalogo)
    return {
        "equipo_nombre": equipment.nombre,
        "equipo_codigo": equipment.codigo,
        "equipo_id": equipment.pk,
        "imagen_url": image_url,
        "caracteristicas_publicas": (
            getattr(equipment, "caracteristicas_publicas", "")
            or getattr(equipment, "descripcion", "")
            or ""
        ),
        "uso_publico": getattr(equipment, "uso_publico", "") or "",
        "instrucciones_publicas": (
            getattr(equipment, "instrucciones_publicas", "") or ""
        ),
        "marca": getattr(equipment, "marca", "") or "",
        "modelo": getattr(equipment, "modelo", "") or "",
        "manual_url": _field_url(getattr(equipment, "manual_operacion", None)),
        "ficha_tecnica_url": _field_url(getattr(equipment, "ficha_tecnica", None)),
        "video_url": _field_url(getattr(equipment, "video_montaje_cuidados", None)),
        "categoria": categoria_publica_equipo(equipment),
        "admite_software_adicional": bool(
            getattr(equipment, "admite_software_adicional", False)
        ),
        # Lo que acompaña al equipo: sus auxiliares, que no se reservan
        # aparte, y los accesorios que llegan con él.
        "rol": getattr(equipment, "rol", "principal"),
        "auxiliares": [
            auxiliar.nombre
            for auxiliar in equipment.auxiliares.filter(estado="disponible").order_by("nombre")
        ],
        "accesorios": equipment.get_accesorios_incluidos_list(),
    }


def _parse_iso_date(value, *, field_name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"El parámetro {field_name} debe usar el formato AAAA-MM-DD.")


def _parse_id_list(request, parameter):
    """Acepta ids repetidos, CSV o una lista JSON sin confiar en el cliente."""
    raw_values = request.GET.getlist(parameter)
    parsed = set()
    for raw_value in raw_values:
        if raw_value in (None, ""):
            continue
        candidates = []
        try:
            decoded = json.loads(raw_value)
            candidates = decoded if isinstance(decoded, list) else [decoded]
        except (TypeError, ValueError, json.JSONDecodeError):
            candidates = str(raw_value).split(",")
        for candidate in candidates:
            try:
                identifier = int(candidate)
            except (TypeError, ValueError):
                continue
            if identifier > 0:
                parsed.add(identifier)
    return parsed


def _reservation_unit_ids(reservation):
    identifiers = set()
    for item in reservation.get_unidades_seleccionadas_list():
        candidate = item.get("id") if isinstance(item, dict) else item
        try:
            identifiers.add(int(candidate))
        except (TypeError, ValueError):
            continue
    return identifiers


def _reservation_space_ids(reservation):
    """Lee la futura relación de áreas sin acoplar esta API a una migración."""
    relation = getattr(reservation, "espacios_solicitados", None)
    if relation is None:
        return set()
    try:
        return set(relation.values_list("pk", flat=True))
    except (AttributeError, TypeError, ValueError):
        return set()


def obtener_unidades_equipo(request, equipo_id):
    """Devuelve las unidades físicas disponibles de un equipo."""
    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    try:
        equipo = EquiposServicios.objects.get(id=equipo_id)
        unidades = UnidadEquipo.objects.filter(equipo=equipo).order_by("codigo_unidad")
        fecha = request.GET.get("fecha")
        horas_json = request.GET.get("horas")
        try:
            horas = json.loads(horas_json) if horas_json else []
        except (TypeError, ValueError, json.JSONDecodeError):
            horas = []
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else None
        except (TypeError, ValueError):
            fecha_obj = None

        resultado = []
        for unidad in unidades:
            estado = unidad.estado_unidad
            disponible = estado == "disponible"
            if fecha_obj and horas and disponible:
                reservas = Reserva.objects.filter(
                    fecha=fecha_obj,
                    estado__in=["confirmada", "en_proceso"],
                    unidades_seleccionadas__contains=unidad.codigo_unidad,
                )
                for reserva in reservas:
                    try:
                        horas_reserva = json.loads(reserva.horas_seleccionadas or "[]")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        horas_reserva = []
                    if set(horas_reserva) & set(horas):
                        estado = "reservado"
                        disponible = False
                        break

            resultado.append(
                {
                    "id": unidad.id,
                    "codigo": unidad.codigo_unidad,
                    "ubicacion": unidad.ubicacion_especifica or "No especificada",
                    "estado": estado,
                    "disponible": disponible,
                    "laboratorio": (
                        unidad.laboratorio.nombre if unidad.laboratorio else None
                    ),
                    **_public_equipment_payload(equipo),
                }
            )
        return JsonResponse(
            {
                "success": True,
                "unidades": resultado,
                "total": len(resultado),
                "equipo_nombre": equipo.nombre,
            }
        )
    except EquiposServicios.DoesNotExist:
        return JsonResponse({"success": False, "error": "Equipo no encontrado"})
    except Exception as error:
        return JsonResponse({"success": False, "error": str(error)})


def obtener_unidades_laboratorio(request, laboratorio_id):
    """Devuelve las unidades físicas de todos los equipos de una Unidad."""
    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    try:
        laboratorio = Unidad.objects.get(id=laboratorio_id)
        # Los auxiliares acompañan a un principal: no son una tarjeta más.
        unidades = _unidades_activas(laboratorio).exclude(equipo__rol="auxiliar")

        # Compatibilidad con la utilidad histórica de datos de demostración.
        resultado = [
            {
                "id": unidad.id,
                "codigo": unidad.codigo_unidad,
                "ubicacion": unidad.ubicacion_especifica or "No especificada",
                "estado": unidad.estado_unidad,
                "disponible": unidad.estado_unidad == "disponible",
                "laboratorio": (
                    unidad.laboratorio.nombre if unidad.laboratorio else "Sin asignar"
                ),
                **_public_equipment_payload(unidad.equipo),
            }
            for unidad in unidades
        ]
        return JsonResponse(
            {
                "success": True,
                "unidades": resultado,
                "total": len(resultado),
                "laboratorio_nombre": laboratorio.nombre,
                "datos_prueba_creados": False,
            }
        )
    except Unidad.DoesNotExist:
        return JsonResponse({"success": False, "error": "Laboratorio no encontrado"})
    except Exception as error:
        return JsonResponse({"success": False, "error": str(error)})


def obtener_ocupacion_laboratorio(request, laboratorio_id):
    """Publica ocupación agregada y reserva la identidad al entorno autenticado.

    La agenda siempre muestra todas las reservas activas de la unidad. Cuando
    el cliente envía recursos, la misma respuesta identifica además cuáles
    bloques colisionan con esa selección para impedir cruces sin ocultar el
    resto de la actividad del laboratorio.
    """
    if request.method != "GET":
        return JsonResponse(
            {"success": False, "error": "Método no permitido"}, status=405
        )

    try:
        laboratorio = Unidad.objects.get(pk=laboratorio_id)
    except Unidad.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Laboratorio no encontrado"}, status=404
        )

    try:
        start_date = _parse_iso_date(
            request.GET.get("desde"), field_name="desde"
        )
        end_date = _parse_iso_date(
            request.GET.get("hasta"), field_name="hasta"
        )
    except ValueError as error:
        return JsonResponse({"success": False, "error": str(error)}, status=400)

    if end_date < start_date:
        return JsonResponse(
            {
                "success": False,
                "error": "El parámetro hasta no puede ser anterior a desde.",
            },
            status=400,
        )
    if (end_date - start_date).days + 1 > CALENDAR_MAX_RANGE_DAYS:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    f"El rango máximo de consulta es de "
                    f"{CALENDAR_MAX_RANGE_DAYS} días."
                ),
            },
            status=400,
        )

    selected_units = _parse_id_list(request, "unidades")
    selected_software = _parse_id_list(request, "software")
    selected_spaces = _parse_id_list(request, "espacios")
    includes_space = request.GET.get("incluye_espacio", "").lower() in {
        "1",
        "true",
        "si",
        "sí",
    }
    space_scope = request.GET.get("alcance_espacio", "").strip()
    if space_scope not in {
        "", "sin_espacio", "areas", "espacio_unico", "unidad_completa"
    }:
        return JsonResponse(
            {"success": False, "error": "El alcance del espacio no es válido."},
            status=400,
        )
    selection_applied = any(
        (
            selected_units,
            selected_software,
            selected_spaces,
            includes_space,
            space_scope not in {"", "sin_espacio"},
        )
    )
    purpose = request.GET.get("proposito_codigo", "").strip()
    request_kind = request.GET.get("tipo_solicitud", "recursos").strip()
    try:
        participant_count = max(
            1,
            min(10000, int(request.GET.get("participantes", "1"))),
        )
    except (TypeError, ValueError):
        participant_count = 1

    reservations = (
        Reserva.objects.filter(
            laboratorio=laboratorio,
            fecha__range=(start_date, end_date),
            estado__in=CALENDAR_ACTIVE_STATUSES,
        )
        .select_related("actividad_catalogo", "periodo")
        .prefetch_related("software_solicitado", "servicios_solicitados")
        .order_by("fecha", "hora_inicio", "pk")
    )
    # La relación se agrega mediante una migración separada; prefetch solo si
    # ya existe para que un despliegue escalonado siga respondiendo.
    if any(field.name == "espacios_solicitados" for field in Reserva._meta.get_fields()):
        reservations = reservations.prefetch_related("espacios_solicitados")

    reservations = list(reservations)
    selected_space_objects = list(
        EspacioReservable.objects.filter(
            unidad=laboratorio,
            pk__in=selected_spaces,
            activo=True,
            reservable=True,
        )
    )
    selected_software_objects = list(
        SoftwareDisponible.objects.filter(
            unidad=laboratorio,
            pk__in=selected_software,
            activo=True,
            requiere_reserva=True,
        )
    )
    if request_kind == 'visita':
        from apps.reservas.presentation.visitas import (
            aforo_del_recorrido, guias_necesarios, oferta_de_visitas, seleccionar_recorrido_visita,
        )
        try:
            oferta = oferta_de_visitas(laboratorio)
            if not laboratorio.activo or not oferta['acepta']:
                raise ValidationError('Esta unidad no recibe visitas por ahora.')
            visitantes = int(request.GET.get('visita_personas', '1'))
            if not 1 <= visitantes <= 200:
                raise ValidationError('Indica un grupo de entre 1 y 200 visitantes.')
            # Antes de elegir áreas se muestra la ocupación de toda la unidad;
            # el alta sí exige un recorrido cuando hay áreas publicadas.
            selected_space_objects = seleccionar_recorrido_visita(oferta, selected_spaces) if selected_spaces else []
            aforo = aforo_del_recorrido(selected_space_objects) if selected_space_objects else (laboratorio.capacidad_personas or 0)
            if aforo and visitantes > aforo:
                raise ValidationError(f'El recorrido admite hasta {aforo} visitantes por grupo.')
            participant_count = visitantes + guias_necesarios(visitantes, oferta['personas_por_guia'])
        except (ValidationError, ValueError, TypeError) as error:
            mensaje = ' '.join(error.messages) if isinstance(error, ValidationError) else 'Indica un número válido de visitantes.'
            return JsonResponse({'success': False, 'error': mensaje}, status=400)
        selected_units, selected_software_objects = set(), []
        includes_space, selection_applied = True, True
        space_scope = 'areas' if selected_space_objects else 'unidad_completa'
        purpose, request_kind = 'vinculacion', 'recursos'
    selected_spaces = {space.pk for space in selected_space_objects}
    selected_software = {software.pk for software in selected_software_objects}
    conflicts_by_slot = evaluate_selection_conflicts(
        reservations,
        selected_unit_ids=selected_units,
        selected_spaces=selected_space_objects,
        includes_space=includes_space,
        space_scope=space_scope,
        selected_software=selected_software_objects,
        purpose=purpose,
        participant_count=participant_count,
        unit_capacity=laboratorio.capacidad_personas,
    ) if selection_applied else {}
    occupancy_by_slot, shared_capacity = selection_occupancy(
        reservations,
        selected_spaces=selected_space_objects,
        includes_space=includes_space,
        space_scope=space_scope,
        unit_capacity=laboratorio.capacidad_personas,
    ) if selection_applied else ({}, 0)
    administrative_blocks = list(
        BloqueoAgendaUnidad.objects.filter(
            unidad=laboratorio,
            activo=True,
            fecha_inicio__lte=end_date,
            fecha_fin__gte=start_date,
        ).prefetch_related("espacios", "equipos")
    )
    administrative_conflicts = evaluate_administrative_block_conflicts(
        administrative_blocks,
        selected_unit_ids=selected_units,
        selected_space_ids=selected_spaces,
        includes_space=includes_space,
        space_scope=space_scope,
        request_kind="servicio" if request_kind == "servicio" else "recursos",
    )
    for slot, reasons in administrative_conflicts.items():
        conflicts_by_slot[slot] = tuple(dict.fromkeys(
            (*conflicts_by_slot.get(slot, ()), *reasons)
        ))

    events = []
    days = {}
    for reservation in reservations:
        matches_selection = event_matches_selection(
            reservation,
            selected_unit_ids=selected_units,
            selected_software_ids=selected_software,
            selected_space_ids=selected_spaces,
            includes_space=includes_space,
            space_scope=space_scope,
        )

        hours = shared_reservation_hours(reservation)
        date_key = reservation.fecha.isoformat()
        reservation_unit_ids = shared_reservation_unit_ids(reservation)
        reservation_software_ids = shared_reservation_software_ids(reservation)
        reservation_space_ids = shared_reservation_space_ids(reservation)
        reservation_includes_space = bool(
            getattr(reservation, "incluye_espacio", False)
        )
        reservation_space_scope = shared_reservation_space_scope(
            reservation,
            space_ids=reservation_space_ids,
        )
        reservation_space_scope_display = dict(
            Reserva.ALCANCE_ESPACIO_CHOICES
        ).get(reservation_space_scope, "Según recursos seleccionados")
        blocked_hours = {
            hour
            for hour in hours
            if matches_selection and (date_key, hour) in conflicts_by_slot
        }
        blocking_reasons = sorted({
            reason
            for hour in blocked_hours
            for reason in conflicts_by_slot.get((date_key, hour), ())
        })

        resource_types = []
        if reservation_unit_ids:
            resource_types.append("equipo")
        if reservation_software_ids:
            resource_types.append("software")
        if reservation_includes_space or reservation_space_ids:
            resource_types.append("espacio")
        if reservation.tipo_solicitud == "servicio":
            resource_types.append("servicio")
        resource_types = sorted(set(resource_types)) or ["actividad"]

        public_resource_names = []
        public_resource_names.extend(
            service.nombre for service in reservation.servicios_solicitados.all()
        )
        public_resource_names.extend(
            software.nombre for software in reservation.software_solicitado.all()
        )
        if hasattr(reservation, "espacios_solicitados"):
            public_resource_names.extend(
                space.nombre for space in reservation.espacios_solicitados.all()
            )
        if not public_resource_names and reservation.equipo_nombre:
            public_resource_names.append(reservation.equipo_nombre)
        if not public_resource_names and reservation_includes_space:
            public_resource_names.append(laboratorio.nombre)

        request_kind = reservation.get_tipo_solicitud_display()
        activity_summary = request_kind
        if public_resource_names:
            visible_names = public_resource_names[:2]
            activity_summary += ": " + ", ".join(visible_names)
            if len(public_resource_names) > len(visible_names):
                activity_summary += f" y {len(public_resource_names) - len(visible_names)} más"
        if request.user.is_authenticated and reservation.titulo_solicitud:
            # Nombre corto: en la agenda por franjas el espacio es limitado.
            activity_summary = reservation.resumen_solicitud

        requester_type = dict(Reserva._meta.get_field("tipo_usuario_solicitante").choices).get(
            reservation.tipo_usuario_solicitante,
            "Usuario registrado",
        )
        requester_label = requester_type
        if request.user.is_authenticated:
            requester_label = reservation.nombre_solicitante or requester_type

        purpose_label = (
            reservation.get_proposito_codigo_display()
            if reservation.proposito_codigo
            else "Uso del laboratorio"
        )
        activity_label = ""
        if request.user.is_authenticated:
            activity_label = reservation.referencia_actividad or (
                reservation.actividad_catalogo.nombre
                if reservation.actividad_catalogo_id
                else ""
            )

        events.append(
            {
                "evento_id": f"reserva-{reservation.pk}",
                "tipo_evento": "reserva",
                "fecha": date_key,
                "hora_inicio": reservation.hora_inicio.strftime("%H:%M"),
                "hora_fin": reservation.hora_fin.strftime("%H:%M"),
                "horas": hours,
                "estado": reservation.estado,
                "estado_display": reservation.get_estado_display(),
                "tipos_recurso": resource_types,
                "tipo_solicitud_display": request_kind,
                "recursos": public_resource_names,
                "resumen": activity_summary,
                "reservado_por": requester_label,
                "proposito_display": purpose_label,
                "proposito_codigo": reservation.proposito_codigo or "otro",
                "actividad": activity_label,
                "periodo_academico": reservation.periodo_academico or (
                    reservation.periodo.codigo if reservation.periodo_id else ""
                ),
                "coincide_seleccion": bool(selection_applied and matches_selection),
                "bloquea_seleccion": bool(blocked_hours),
                "motivos_bloqueo": blocking_reasons,
                "participantes": max(1, reservation.numero_participantes or 1),
                "alcance_espacio": reservation_space_scope,
                "alcance_espacio_display": reservation_space_scope_display,
                "etiqueta": (
                    "Horario ocupado"
                    if blocked_hours
                    else "Actividad registrada"
                ),
            }
        )
        summary = days.setdefault(
            date_key,
            {
                "solicitudes": 0,
                "horas_ocupadas": set(),
                "horas_bloqueadas": set(),
                "estados": set(),
            },
        )
        summary["solicitudes"] += 1
        summary["horas_ocupadas"].update(hours)
        summary["horas_bloqueadas"].update(blocked_hours)
        summary["estados"].add(reservation.estado)

    for block in administrative_blocks:
        if not block.visible_en_agenda:
            continue
        applies_to_selection = administrative_block_matches_selection(
            block,
            selected_unit_ids=selected_units,
            selected_space_ids=selected_spaces,
            includes_space=includes_space,
            space_scope=space_scope,
            request_kind="servicio" if request_kind == "servicio" else "recursos",
        )
        hours = administrative_block_hours(block)
        current = max(start_date, block.fecha_inicio)
        final = min(end_date, block.fecha_fin)
        resources = []
        if block.alcance == "unidad_completa":
            resources.append(laboratorio.nombre)
        elif block.alcance == "areas":
            resources.extend(item.nombre for item in block.espacios.all())
        else:
            resources.extend(
                item.equipo.nombre if item.equipo_id else item.codigo_unidad
                for item in block.equipos.all()
            )
        while current <= final:
            date_key = current.isoformat()
            events.append({
                "evento_id": f"bloqueo-{block.pk}-{date_key}",
                "tipo_evento": "bloqueo",
                "fecha": date_key,
                "hora_inicio": "00:00" if block.dia_completo else block.hora_inicio.strftime("%H:%M"),
                "hora_fin": "23:59" if block.dia_completo else block.hora_fin.strftime("%H:%M"),
                "horas": hours,
                "estado": "bloqueado",
                "estado_display": "No habilitado",
                "tipos_recurso": ["cierre administrativo"],
                "tipo_solicitud_display": block.get_tipo_display(),
                "recursos": resources,
                "resumen": block.titulo,
                "reservado_por": "Administración de la unidad",
                "proposito_display": block.get_tipo_display(),
                "proposito_codigo": "bloqueo",
                "actividad": block.motivo,
                "periodo_academico": "",
                "coincide_seleccion": applies_to_selection,
                "bloquea_seleccion": applies_to_selection,
                "motivos_bloqueo": [f"{block.get_tipo_display()}: {block.titulo}."],
                "participantes": 0,
                "alcance_espacio": block.alcance,
                "alcance_espacio_display": block.get_alcance_display(),
                "etiqueta": "Horario no habilitado",
            })
            summary = days.setdefault(date_key, {
                "solicitudes": 0,
                "horas_ocupadas": set(),
                "horas_bloqueadas": set(),
                "estados": set(),
            })
            summary["solicitudes"] += 1
            summary["horas_ocupadas"].update(hours)
            if applies_to_selection:
                summary["horas_bloqueadas"].update(hours)
            summary["estados"].add("bloqueado")
            current += date.resolution

    events.sort(key=lambda item: (item["fecha"], item["hora_inicio"], item["evento_id"]))
    for evento in events:
        # Traducir etiquetas de presentación; códigos, recursos y solicitantes quedan intactos.
        for campo in ('estado_display', 'tipo_solicitud_display', 'alcance_espacio_display',
                      'proposito_display', 'etiqueta'):
            if evento.get(campo):
                evento[campo] = gettext(evento[campo])

    occupancy_by_day = {}
    for (date_key, hour), people in occupancy_by_slot.items():
        occupancy_by_day.setdefault(date_key, {})[str(hour)] = people
    serialized_days = {
        key: {
            "solicitudes": value["solicitudes"],
            "horas_ocupadas": sorted(value["horas_ocupadas"]),
            "horas_bloqueadas": sorted(value["horas_bloqueadas"]),
            "estados": sorted(value["estados"]),
            "bloquea_seleccion": bool(value["horas_bloqueadas"]),
            "ocupacion": occupancy_by_day.get(key, {}),
        }
        for key, value in days.items()
    }
    return JsonResponse(
        {
            "success": True,
            "laboratorio": {"id": laboratorio.pk, "nombre": laboratorio.nombre},
            "rango": {"desde": start_date.isoformat(), "hasta": end_date.isoformat()},
            "seleccion_recursos_aplicada": selection_applied,
            "capacidad_seleccion": shared_capacity,
            "dias": serialized_days,
            "eventos": events,
            "leyenda": {
                "disponible": gettext("Sin ocupación registrada"),
                "ocupado": (
                    gettext("Conflicto con la selección actual")
                    if selection_applied
                    else gettext("Existen solicitudes registradas")
                ),
            },
        }
    )


def _unidades_activas(laboratorio):
    return (
        UnidadEquipo.objects.filter(
            Q(laboratorios=laboratorio) | Q(laboratorio=laboratorio),
            activa=True,
        )
        .select_related("equipo", "laboratorio")
        .distinct()
    )
