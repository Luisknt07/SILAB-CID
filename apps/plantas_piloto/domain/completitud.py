"""Reglas puras para clasificar la completitud editorial de una planta.

Los códigos se conservan fuera de Django para que el tablero, el administrador
y futuras API compartan la misma interpretación sin depender de una vista.
"""

ESTADO_APROBADO = "aprobado"
ESTADO_PARCIAL = "parcial"
ESTADO_PENDIENTE = "pendiente"
ESTADO_BLOQUEADO = "bloqueado"


def porcentaje_cobertura(actual: int, esperado: int) -> int:
    """Calcula un porcentaje acotado entre cero y cien."""
    if esperado <= 0:
        return 100
    return round(min(max(actual, 0), esperado) * 100 / esperado)


def estado_cobertura(actual: int, esperado: int, *, bloqueado: bool = False) -> str:
    """Clasifica una sección o familia a partir de su cobertura real."""
    if bloqueado:
        return ESTADO_BLOQUEADO
    if actual <= 0:
        return ESTADO_PENDIENTE
    if esperado <= 0 or actual >= esperado:
        return ESTADO_APROBADO
    return ESTADO_PARCIAL


def estado_ficha(
    completitud: int,
    estado_editorial: str,
    estado_validacion: str,
    *,
    bloqueado: bool = False,
) -> str:
    """Clasifica una ficha sin confundir publicación con validación UPEC."""
    if bloqueado or estado_validacion == "bloqueada":
        return ESTADO_BLOQUEADO
    if (
        completitud >= 100
        and estado_editorial == "publicada"
        and estado_validacion == "validada"
    ):
        return ESTADO_APROBADO
    if completitud <= 0 or estado_editorial in {"borrador", "archivada"}:
        return ESTADO_PENDIENTE
    return ESTADO_PARCIAL
