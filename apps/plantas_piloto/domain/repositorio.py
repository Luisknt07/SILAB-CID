"""Reglas puras de vigencia para artefactos externos de Plantas Piloto."""

from datetime import date


def estado_vigencia(
    hoy: date,
    vigente_desde: date | None,
    vigente_hasta: date | None,
    *,
    desactualizado: bool = False,
) -> str:
    if desactualizado:
        return "requiere_revision"
    if vigente_desde is None:
        return "sin_declarar"
    if vigente_desde > hoy:
        return "programado"
    if vigente_hasta is not None and vigente_hasta < hoy:
        return "vencido"
    return "vigente"


def esta_vigente(
    hoy: date,
    vigente_desde: date | None,
    vigente_hasta: date | None,
    *,
    desactualizado: bool = False,
) -> bool:
    return estado_vigencia(
        hoy,
        vigente_desde,
        vigente_hasta,
        desactualizado=desactualizado,
    ) == "vigente"
