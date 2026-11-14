"""Agenda semanal y calendario mensual del panel de una unidad.

Reparte las reservas en franjas continuas y carriles para que dos solicitudes a
la misma hora se vean lado a lado, y acota la rejilla al horario de atención que
la unidad declaró.
"""

import calendar
from datetime import date, time, timedelta

from django.db.models import Count

from apps.gestion_unidades.models.operaciones import ventana_atencion


def _horarios_aplicables_en_fecha(horarios, fecha):
    """Aplica la jornada del período vigente o, en su defecto, la general."""
    generales = [horario for horario in horarios if horario.periodo_id is None]
    especificos = []
    for horario in horarios:
        if not horario.periodo_id:
            continue
        version = horario.periodo.version_vigente
        if version and version.fecha_inicio_clases <= fecha <= version.fecha_fin_periodo:
            especificos.append(horario)
    return especificos or generales


def _agenda_semanal(
    reservas,
    horarios,
    bloqueos,
    inicio_semana,
    hoy,
    fecha_seleccionada,
):
    fin_semana = inicio_semana + timedelta(days=6)
    reservas_semana = list(
        reservas.filter(fecha__range=(inicio_semana, fin_semana)).order_by(
            "fecha", "hora_inicio", "pk"
        )
    )
    dias_visibles = list(range(5))
    sabado = inicio_semana + timedelta(days=5)
    domingo = inicio_semana + timedelta(days=6)
    if any(
        horario.dia_semana == 5
        for horario in _horarios_aplicables_en_fecha(horarios, sabado)
    ) or any(
        reserva.fecha.weekday() == 5 for reserva in reservas_semana
    ) or any(
        bloqueo.fecha_inicio <= sabado <= bloqueo.fecha_fin
        for bloqueo in bloqueos
    ):
        dias_visibles.append(5)
    if any(
        horario.dia_semana == 6
        for horario in _horarios_aplicables_en_fecha(horarios, domingo)
    ) or any(
        reserva.fecha.weekday() == 6 for reserva in reservas_semana
    ) or any(
        bloqueo.fecha_inicio <= domingo <= bloqueo.fecha_fin
        for bloqueo in bloqueos
    ):
        dias_visibles.append(6)
    fechas = [inicio_semana + timedelta(days=dia) for dia in dias_visibles]
    por_fecha = {fecha: [] for fecha in fechas}
    for reserva in reservas_semana:
        por_fecha.setdefault(reserva.fecha, []).append(reserva)
    return [
        {
            "fecha": fecha,
            "dia_semana": fecha.weekday(),
            "reservas": por_fecha.get(fecha, []),
            "es_hoy": fecha == hoy,
            "es_seleccionado": fecha == fecha_seleccionada,
        }
        for fecha in fechas
    ]


def _rango_horario_agenda(agenda_semana, horarios, configuracion=None):
    """Primera y última hora que debe mostrar la agenda semanal.

    La jornada operativa se recorta al horario que la unidad ofrece. Las
    reservas que atraviesan sus límites se representan dentro de esa franja.
    """
    apertura, cierre = ventana_atencion(configuracion)
    inicios = [max(apertura, horario.hora_inicio.hour) for horario in horarios]
    fines = [
        min(cierre, horario.hora_fin.hour + bool(horario.hora_fin.minute))
        for horario in horarios
    ]
    # Una excepción o reserva de todo el día se recorta dentro de la franja
    # publicada: sigue visible, pero no fuerza a empezar la agenda a las 00:00.
    primera = max(apertura, min(inicios, default=apertura))
    ultima = min(cierre, max(fines, default=cierre))
    if ultima <= primera:
        ultima = min(24, primera + 1)
    return primera, ultima


def _repartir_carriles(franjas):
    """Reparte en carriles las franjas que se solapan dentro de un mismo día."""
    ordenadas = sorted(franjas, key=lambda franja: (franja["inicio"], franja["filas"]))
    grupo = []
    activos = []

    def cerrar_grupo():
        total = max((franja["carril"] + 1 for franja in grupo), default=1)
        for franja in grupo:
            franja["carriles"] = total
        grupo.clear()

    for franja in ordenadas:
        activos = [
            activo
            for activo in activos
            if activo["inicio"] + activo["filas"] > franja["inicio"]
        ]
        if not activos and grupo:
            cerrar_grupo()
        usados = {activo["carril"] for activo in activos}
        while franja["carril"] in usados:
            franja["carril"] += 1
        activos.append(franja)
        grupo.append(franja)
    if grupo:
        cerrar_grupo()
    return ordenadas


def _agenda_grid(agenda_semana, horarios, bloqueos, configuracion=None):
    """Agenda semanal donde cada reserva es una franja continua.

    Una solicitud de dos horas ocupa un solo bloque que va de su hora inicial
    a la final, de modo que se ve su duración real. Las solicitudes que
    coinciden se reparten en carriles dentro del día, sin repetir la tarjeta
    en cada hora.
    """
    primera, ultima = _rango_horario_agenda(agenda_semana, horarios, configuracion)
    horas = list(range(primera, ultima))
    hay_horarios = bool(horarios)
    dias = []
    for dia in agenda_semana:
        aplicables = [
            horario
            for horario in _horarios_aplicables_en_fecha(horarios, dia["fecha"])
            if horario.dia_semana == dia["dia_semana"]
        ]
        bloqueos_dia = [
            bloqueo
            for bloqueo in bloqueos
            if bloqueo.fecha_inicio <= dia["fecha"] <= bloqueo.fecha_fin
        ]
        celdas = []
        for indice, hora in enumerate(horas):
            inicio = time(hora, 0)
            fin = time(hora + 1, 0) if hora < 23 else time(23, 59, 59)
            habilitada = any(
                horario.hora_inicio < fin and horario.hora_fin > inicio
                for horario in aplicables
            )
            if not hay_horarios:
                habilitada = dia["dia_semana"] < 5 and 8 <= hora < 17
            bloqueada = any(
                bloqueo.dia_completo
                or (
                    bloqueo.hora_inicio
                    and bloqueo.hora_fin
                    and bloqueo.hora_inicio < fin
                    and bloqueo.hora_fin > inicio
                )
                for bloqueo in bloqueos_dia
            )
            ocupada = any(
                reserva.hora_inicio < fin and reserva.hora_fin > inicio
                for reserva in dia["reservas"]
            )
            celdas.append(
                {
                    "hora": f"{hora:02d}:00",
                    "indice": indice,
                    "habilitada": habilitada,
                    "bloqueada": bloqueada,
                    "libre": habilitada and not bloqueada and not ocupada,
                }
            )
        franjas = []
        for reserva in dia["reservas"]:
            comienzo = max(primera, reserva.hora_inicio.hour)
            termino = min(
                ultima,
                reserva.hora_fin.hour + bool(reserva.hora_fin.minute),
            )
            if termino <= comienzo:
                termino = min(ultima, comienzo + 1)
            franjas.append(
                {
                    "reserva": reserva,
                    "inicio": comienzo - primera,
                    "filas": max(1, termino - comienzo),
                    "carril": 0,
                    "carriles": 1,
                }
            )
        bandas = []
        for bloqueo in bloqueos_dia:
            if bloqueo.dia_completo or not (bloqueo.hora_inicio and bloqueo.hora_fin):
                comienzo, termino = primera, ultima
            else:
                comienzo = max(primera, bloqueo.hora_inicio.hour)
                termino = min(
                    ultima,
                    bloqueo.hora_fin.hour + bool(bloqueo.hora_fin.minute),
                )
            if termino <= comienzo:
                continue
            bandas.append(
                {
                    "bloqueo": bloqueo,
                    "inicio": comienzo - primera,
                    "filas": termino - comienzo,
                }
            )
        dias.append(
            {
                **dia,
                "celdas": celdas,
                "eventos": _repartir_carriles(franjas),
                "bandas": bandas,
            }
        )
    return {"horas": [f"{hora:02d}:00" for hora in horas], "dias": dias}


def _desplazar_mes(fecha, cantidad):
    indice = fecha.year * 12 + fecha.month - 1 + cantidad
    return date(indice // 12, indice % 12 + 1, 1)


def _calendario_mensual(
    reservas,
    fecha_referencia,
    inicio_semana,
    fin_semana,
    hoy,
):
    """Crea el selector mensual que controla la semana de la agenda."""
    inicio_mes = fecha_referencia.replace(day=1)
    semanas_mes = calendar.Calendar(firstweekday=0).monthdatescalendar(
        inicio_mes.year,
        inicio_mes.month,
    )
    primera_fecha = semanas_mes[0][0]
    ultima_fecha = semanas_mes[-1][-1]
    reservas_por_fecha = {
        item["fecha"]: item["total"]
        for item in reservas.filter(
            fecha__range=(primera_fecha, ultima_fecha)
        )
        .values("fecha")
        .annotate(total=Count("pk"))
    }
    semanas = []
    for semana in semanas_mes:
        semanas.append(
            [
                {
                    "fecha": fecha,
                    "es_mes_actual": fecha.month == inicio_mes.month,
                    "es_hoy": fecha == hoy,
                    "es_seleccionada": fecha == fecha_referencia,
                    "esta_en_semana": inicio_semana <= fecha <= fin_semana,
                    "es_fin_semana": fecha.weekday() >= 5,
                    "reservas": reservas_por_fecha.get(fecha, 0),
                }
                for fecha in semana
            ]
        )
    return {
        "mes": inicio_mes,
        "mes_anterior": _desplazar_mes(inicio_mes, -1).isoformat(),
        "mes_siguiente": _desplazar_mes(inicio_mes, 1).isoformat(),
        "dias_semana": ("L", "M", "X", "J", "V", "S", "D"),
        "semanas": semanas,
    }
