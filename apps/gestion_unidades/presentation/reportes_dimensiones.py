"""Catálogo único de dimensiones y métricas de uso de reservas.

Existían dos reportes que medían lo mismo de forma distinta: el de la unidad
calculaba horas y participantes desde la ejecución real, mientras que el
institucional sumaba la duración planificada. El mismo laboratorio obtenía
cifras diferentes según la pantalla que abriera.

Este módulo define una sola vez qué es una hora efectiva, cuántos participantes
tuvo una atención y cómo se etiqueta cada dimensión. Ambos reportes lo consumen.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable

from django.utils.dateparse import parse_time

from apps.reservas.models.reservas import Reserva


SIN_CLASIFICAR = "Sin clasificar"


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #

def horas_efectivas(reserva):
    """Horas de la atención, priorizando el horario real sobre el planificado.

    Una reserva cerrada con ejecución registrada aporta las horas que realmente
    ocupó el recurso. Mientras no exista ese registro se usa el horario
    solicitado, que es la mejor estimación disponible.
    """
    ejecucion = reserva.detalle_ejecucion if isinstance(reserva.detalle_ejecucion, dict) else {}
    horario_real = ejecucion.get("horario_real")
    horario_real = horario_real if isinstance(horario_real, dict) else {}

    def hora(campo, prevista):
        try:
            return parse_time(str(horario_real.get(campo) or "")) or prevista
        except ValueError:
            return prevista

    inicio = hora("inicio", reserva.hora_inicio)
    fin = hora("fin", reserva.hora_fin)
    if not inicio or not fin:
        return 0.0
    minutos_inicio = (inicio.hour * 60) + inicio.minute
    minutos_fin = (fin.hour * 60) + fin.minute
    return max(0, minutos_fin - minutos_inicio) / 60


def participantes(reserva):
    """Asistencia conciliada cuando la atención se cerró; si no, la prevista."""
    ejecucion = reserva.detalle_ejecucion if isinstance(reserva.detalle_ejecucion, dict) else {}
    if reserva.es_efectiva:
        if 'asistentes_total' not in ejecucion:
            registrados = getattr(reserva, 'reporte_asistentes_visita', None)
            if registrados is not None:
                return registrados
            if getattr(reserva, 'visita', None):
                return reserva.visita.presentes
        try:
            return max(0, int(ejecucion.get("asistentes_total") or 0))
        except (TypeError, ValueError, OverflowError):
            pass
    return max(1, reserva.numero_participantes or 1)


# --------------------------------------------------------------------------- #
# Dimensiones
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Dimension:
    """Una forma de agrupar reservas.

    ``resolver`` devuelve una etiqueta o, cuando ``multiple`` es verdadero, una
    lista de etiquetas. En ese caso una misma reserva aparece en varias filas y
    los totales dejan de sumar el número de solicitudes; el reporte debe
    advertirlo.
    """

    clave: str
    etiqueta: str
    resolver: Callable[[Reserva], object]
    multiple: bool = False
    ambitos: frozenset = field(
        default_factory=lambda: frozenset({"unidad", "institucional"})
    )


def _mapa_opciones(nombre_campo):
    return dict(Reserva._meta.get_field(nombre_campo).flatchoices)


def _por_opciones(nombre_campo):
    """Etiqueta legible de un campo con ``choices``."""

    def resolver(reserva, _campo=nombre_campo):
        valor = getattr(reserva, _campo, "") or ""
        return _mapa_opciones(_campo).get(valor, SIN_CLASIFICAR)

    return resolver


def _por_responsable(reserva):
    if reserva.responsable_asignado_id:
        return reserva.responsable_asignado.nombre_publico
    return "Sin responsable asignado"


def _por_unidad(reserva):
    return reserva.laboratorio.nombre if reserva.laboratorio_id else SIN_CLASIFICAR


def _por_fecha(reserva):
    return reserva.fecha.strftime("%d/%m/%Y") if reserva.fecha else "Sin fecha"


def _nombre_periodo(reserva):
    if reserva.periodo_id:
        return reserva.periodo.codigo
    return reserva.periodo_academico or "Sin período"


def _por_semana_academica(reserva):
    periodo = _nombre_periodo(reserva)
    numero = reserva.semana_academica_numero
    if numero:
        return f"{periodo} · Semana {numero}"
    return f"{periodo} · Sin semana"


def _por_semana_calendario(reserva):
    if not reserva.fecha:
        return "Sin fecha"
    anio, semana, _dia = reserva.fecha.isocalendar()
    return f"{anio} · Semana {semana:02d}"


def _por_mes(reserva):
    return reserva.fecha.strftime("%Y-%m") if reserva.fecha else "Sin fecha"


def _por_trimestre(reserva):
    if not reserva.fecha:
        return "Sin fecha"
    trimestre = ((reserva.fecha.month - 1) // 3) + 1
    return f"{reserva.fecha.year} · T{trimestre}"


def _por_anio(reserva):
    return str(reserva.fecha.year) if reserva.fecha else "Sin fecha"


def _por_jornada(reserva):
    if not reserva.fecha:
        return "Sin fecha"
    return "Fin de semana" if reserva.fecha.weekday() >= 5 else "Día laborable"


CODIGOS_EQUIPO_NO_FISICO = {
    "", "ESPACIO", "ESPACIOS", "SOFTWARE", "SERVICIO", "MULTI", "VISITA",
}


def _por_recurso(reserva):
    """Todos los recursos comprometidos: equipos, espacios, software y servicios.

    Una solicitud combinada aparece en varias filas a propósito: la pregunta
    que responde esta dimensión es cuánto se usa cada recurso, no cuántas
    solicitudes hubo.
    """
    recursos = []
    for item in reserva.get_unidades_seleccionadas_list():
        if not isinstance(item, dict):
            continue
        nombre = (item.get("nombre") or "").strip()
        codigo = (item.get("codigo") or "").strip()
        etiqueta = " · ".join(parte for parte in (codigo, nombre) if parte)
        if etiqueta and etiqueta not in recursos:
            recursos.append(etiqueta)
    if not recursos and not getattr(reserva, 'visita', None) and (reserva.equipo_codigo or "") not in CODIGOS_EQUIPO_NO_FISICO:
        etiqueta = " · ".join(
            parte for parte in (reserva.equipo_codigo, reserva.equipo_nombre) if parte
        )
        if etiqueta:
            recursos.append(etiqueta)
    for atributo, relacion in (
        ("_reporte_espacios", "espacios_solicitados"),
        ("_reporte_software", "software_solicitado"),
        ("_reporte_servicios", "servicios_solicitados"),
    ):
        coleccion = getattr(reserva, atributo, None)
        if coleccion is None:
            coleccion = getattr(reserva, relacion).all()
        for recurso in coleccion:
            nombre = getattr(recurso, "nombre", "") or str(recurso)
            if nombre and nombre not in recursos:
                recursos.append(nombre)
    return recursos or ["Sin recurso registrado"]


DIMENSIONES = OrderedDict(
    (dimension.clave, dimension)
    for dimension in (
        Dimension("fecha", "Fecha", _por_fecha),
        Dimension("estado", "Estado de la solicitud", _por_opciones("estado")),
        Dimension(
            "proposito", "Propósito institucional", _por_opciones("proposito_codigo")
        ),
        Dimension("subtipo", "Tipo de actividad", _por_opciones("subtipo_actividad")),
        Dimension(
            "tipo_usuario", "Tipo de usuario", _por_opciones("tipo_usuario_solicitante")
        ),
        Dimension(
            "tipo_solicitud", "Tipo de solicitud", lambda reserva: 'Visita' if getattr(reserva, 'visita', None) else _por_opciones('tipo_solicitud')(reserva)
        ),
        Dimension(
            "vinculacion",
            "Vinculación de la actividad",
            _por_opciones("vinculacion_actividad"),
        ),
        Dimension(
            "facultad", "Facultad beneficiaria", _por_opciones("facultad_beneficiaria")
        ),
        Dimension(
            "carrera", "Carrera beneficiaria", _por_opciones("carrera_beneficiaria")
        ),
        Dimension(
            "alcance",
            "Alcance del beneficiario",
            _por_opciones("alcance_beneficiario"),
        ),
        Dimension(
            "responsable",
            "Responsable asignado",
            _por_responsable,
            ambitos=frozenset({"unidad"}),
        ),
        Dimension("recurso", "Recurso utilizado", _por_recurso, multiple=True),
        Dimension("periodo", "Período académico", _nombre_periodo),
        Dimension("semana_academica", "Semana académica", _por_semana_academica),
        Dimension("semana_calendario", "Semana calendario", _por_semana_calendario),
        Dimension("mes", "Mes calendario", _por_mes),
        Dimension("trimestre", "Trimestre calendario", _por_trimestre),
        Dimension("anio", "Año", _por_anio),
        Dimension("jornada", "Tipo de jornada", _por_jornada),
        Dimension(
            "unidad", "Unidad", _por_unidad, ambitos=frozenset({"institucional"})
        ),
    )
)


def dimensiones_de(ambito):
    """Pares ``(clave, etiqueta)`` disponibles para un reporte."""
    return tuple(
        (clave, dimension.etiqueta)
        for clave, dimension in DIMENSIONES.items()
        if ambito in dimension.ambitos
    )


def es_multiple(clave):
    """Indica si una dimensión puede contar una reserva en más de una fila."""
    dimension = DIMENSIONES.get(clave)
    return bool(dimension and dimension.multiple)


def resumir_reservas(
    reservas, clave=None, *, efectividad="", limite_detalle=0, incluir_alcance=False
):
    """Recorre una vez un iterable, conservando solo el detalle solicitado.

    Las cifras incluyen todos los registros que cumplen el filtro. Los grupos
    conservan únicamente etiquetas y acumuladores, nunca reservas o sus PK.
    El tiempo sigue dependiendo del número de reservas; la memoria del resumen
    depende del número de etiquetas distintas y del límite de detalle.
    """
    dimension = DIMENSIONES.get(clave) if clave is not None else None
    if clave is not None and dimension is None:
        raise KeyError(f"Dimensión desconocida: {clave}")

    acumulado = OrderedDict()
    total = confirmadas = asistentes_total = 0
    horas_total = 0.0
    detalle = []
    primera_fecha = ultima_fecha = None
    unidades = set()
    for reserva in reservas:
        efectiva = reserva.es_efectiva
        if efectividad == "efectivas" and not efectiva:
            continue
        if efectividad == "no_efectivas" and efectiva:
            continue
        total += 1
        confirmadas += int(efectiva)
        horas = horas_efectivas(reserva) if efectiva else 0.0
        asistentes = participantes(reserva) if efectiva else 0
        horas_total += horas
        asistentes_total += asistentes
        if len(detalle) < limite_detalle:
            detalle.append(reserva)
        if incluir_alcance:
            fecha = reserva.fecha
            if fecha:
                primera_fecha = min(primera_fecha, fecha) if primera_fecha else fecha
                ultima_fecha = max(ultima_fecha, fecha) if ultima_fecha else fecha
            if reserva.laboratorio_id:
                unidades.add(reserva.laboratorio.nombre)
        if dimension is None:
            continue
        etiquetas = dimension.resolver(reserva)
        if not isinstance(etiquetas, (list, tuple, set)):
            etiquetas = [etiquetas]
        for etiqueta in etiquetas:
            fila = acumulado.setdefault(
                etiqueta,
                {
                    "label": etiqueta,
                    "total": 0,
                    "effective": 0,
                    "hours": 0.0,
                    "participants": 0,
                },
            )
            fila["total"] += 1
            fila["effective"] += 1 if efectiva else 0
            fila["hours"] += horas
            fila["participants"] += asistentes

    filas = []
    for fila in acumulado.values():
        fila["hours"] = round(fila["hours"], 1)
        fila["percentage"] = round((fila["total"] / total) * 100, 1) if total else 0
        filas.append(fila)
    filas.sort(key=lambda item: (-item["total"], item["label"]))
    return {
        "metrics": {
            "total": total,
            "confirmed": confirmadas,
            "hours": round(horas_total, 1),
            "participants": asistentes_total,
        },
        "rows": filas,
        "reservations": detalle,
        "first_date": primera_fecha,
        "last_date": ultima_fecha,
        "units": sorted(unidades),
    }


def agrupar(reservas, clave):
    """Agrupa todas las reservas sin retener los modelos que recibe."""
    return resumir_reservas(reservas, clave)["rows"]
