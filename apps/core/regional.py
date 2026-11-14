"""Contrato regional y conversion civil explicita, sin dependencias Django."""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True, slots=True)
class ConfiguracionRegional:
    idioma: str
    zona_horaria: str


def configuracion_regional(idioma, zona_horaria):
    if not isinstance(idioma, str) or not re.fullmatch(
            r"[a-zA-Z]{2,3}(?:-[a-zA-Z]{4})?(?:-(?:[a-zA-Z]{2}|[0-9]{3}))?", idioma):
        raise ValueError("INSTITUTION_LANGUAGE_CODE debe ser un codigo de idioma valido.")
    if (not isinstance(zona_horaria, str) or len(zona_horaria) > 100
            or not re.fullmatch(r"[A-Za-z0-9_+/-]+", zona_horaria)):
        raise ValueError("INSTITUTION_TIME_ZONE debe ser una zona IANA valida.")
    try:
        ZoneInfo(zona_horaria)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("INSTITUTION_TIME_ZONE no existe en los datos horarios instalados.") from exc
    return ConfiguracionRegional(idioma.lower(), zona_horaria)


def instante_civil(valor, zona):
    """Rechaza horas inexistentes o duplicadas; el modelo civil no almacena fold."""
    if not isinstance(valor, datetime) or valor.tzinfo is not None:
        raise ValueError("Introduce fecha y hora locales, sin zona ni desplazamiento UTC.")
    candidatos = {}
    for fold in (0, 1):
        candidato = valor.replace(tzinfo=zona, fold=fold)
        utc = candidato.astimezone(timezone.utc)
        if utc.astimezone(zona).replace(tzinfo=None) == valor:
            candidatos[utc] = candidato
    if not candidatos:
        raise ValueError("Ese horario no existe por el cambio de hora de la institucion; selecciona otro.")
    if len(candidatos) != 1:
        raise ValueError("Ese horario se repite por el cambio de hora de la institucion; selecciona otro.")
    return next(iter(candidatos.values()))


def intervalo_civil(inicio, fin, zona):
    primero, ultimo = instante_civil(inicio, zona), instante_civil(fin, zona)
    if ultimo <= primero:
        raise ValueError("La hora de fin debe ser posterior a la hora de inicio.")
    if primero.utcoffset() != ultimo.utcoffset():
        raise ValueError("La reserva atraviesa un cambio de hora; selecciona un intervalo sin ese cambio.")
    return primero, ultimo
