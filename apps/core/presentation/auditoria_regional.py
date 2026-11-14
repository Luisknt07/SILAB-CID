"""Cuenta agendas afectadas por otra zona; no revela personas ni modifica datos."""

from datetime import datetime, timezone as utc_timezone
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.core.regional import configuracion_regional, intervalo_civil


def auditar_zona_horaria(zona_horaria, database="default"):
    from apps.reservas.models.reservas import Reserva

    candidata = configuracion_regional(settings.LANGUAGE_CODE, zona_horaria)
    anterior, nueva = ZoneInfo(settings.TIME_ZONE), ZoneInfo(candidata.zona_horaria)
    resultado = {"reservas": 0, "sin_horario_completo": 0, "horarios_no_representables": 0,
                 "reservas_con_instante_distinto": 0}
    filas = Reserva.objects.using(database).values_list("fecha", "hora_inicio", "hora_fin").iterator()
    for fecha, hora_inicio, hora_fin in filas:
        resultado["reservas"] += 1
        if not fecha or hora_inicio is None or hora_fin is None:
            resultado["sin_horario_completo"] += 1
            continue
        inicio, fin = datetime.combine(fecha, hora_inicio), datetime.combine(fecha, hora_fin)
        try:
            despues = intervalo_civil(inicio, fin, nueva)
        except ValueError:
            resultado["horarios_no_representables"] += 1
            continue
        antes = (inicio.replace(tzinfo=anterior), fin.replace(tzinfo=anterior))
        if any(a.astimezone(utc_timezone.utc) != d.astimezone(utc_timezone.utc) for a, d in zip(antes, despues)):
            resultado["reservas_con_instante_distinto"] += 1
    return resultado
