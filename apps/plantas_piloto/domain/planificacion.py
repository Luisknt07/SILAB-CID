"""Reglas puras de demanda y planificación de una planta piloto.

Este módulo no conoce Django ni los modelos heredados. Recibe fechas y
cantidades y devuelve valores que la capa de aplicación puede persistir.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


TRES_DECIMALES = Decimal("0.001")


def decimal_tres(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(TRES_DECIMALES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class PeriodoDemanda:
    inicio: date
    fin: date

    def __post_init__(self):
        if self.fin < self.inicio:
            raise ValueError("El período termina antes de empezar.")


def periodos_demanda(desde: date, hasta: date, periodicidad: str) -> tuple[PeriodoDemanda, ...]:
    """Divide un horizonte en semanas consecutivas o meses calendario."""
    if hasta < desde:
        raise ValueError("El horizonte termina antes de empezar.")
    if periodicidad not in {"semanal", "mensual"}:
        raise ValueError("La periodicidad debe ser semanal o mensual.")
    periodos = []
    cursor = desde
    while cursor <= hasta:
        if periodicidad == "semanal":
            fin = min(cursor + timedelta(days=6), hasta)
        else:
            fin_mes = date(cursor.year, cursor.month, monthrange(cursor.year, cursor.month)[1])
            fin = min(fin_mes, hasta)
        periodos.append(PeriodoDemanda(cursor, fin))
        cursor = fin + timedelta(days=1)
    return tuple(periodos)


def ventanas_historicas(inicio: date, periodicidad: str, cantidad: int = 3) -> tuple[PeriodoDemanda, ...]:
    """Devuelve los períodos anteriores usados por el promedio móvil."""
    if cantidad < 1:
        raise ValueError("Se necesita al menos un período histórico.")
    ventanas = []
    cursor = inicio
    for _ in range(cantidad):
        if periodicidad == "semanal":
            fin = cursor - timedelta(days=1)
            comienzo = fin - timedelta(days=6)
        elif periodicidad == "mensual":
            fin = cursor.replace(day=1) - timedelta(days=1)
            comienzo = fin.replace(day=1)
        else:
            raise ValueError("La periodicidad debe ser semanal o mensual.")
        ventanas.append(PeriodoDemanda(comienzo, fin))
        cursor = comienzo
    return tuple(reversed(ventanas))


def promedio_movil(valores) -> Decimal:
    valores = tuple(decimal_tres(valor) for valor in valores)
    if not valores:
        return Decimal("0.000")
    return decimal_tres(sum(valores, Decimal("0")) / len(valores))


def cantidad_planificada(pronostico, compromisos, docencia, ajuste) -> Decimal:
    total = sum(
        (
            decimal_tres(pronostico),
            decimal_tres(compromisos),
            decimal_tres(docencia),
            decimal_tres(ajuste),
        ),
        Decimal("0"),
    )
    return max(Decimal("0.000"), decimal_tres(total))


def demanda_no_comprometida(pronostico, ajuste) -> Decimal:
    return max(Decimal("0.000"), decimal_tres(decimal_tres(pronostico) + decimal_tres(ajuste)))


def equivalente_base(cantidad_producto, rendimiento, cantidad_base) -> Decimal:
    rendimiento = decimal_tres(rendimiento)
    if rendimiento <= 0:
        raise ValueError("El rendimiento de la receta debe ser mayor que cero.")
    return decimal_tres(decimal_tres(cantidad_producto) / rendimiento * decimal_tres(cantidad_base))
