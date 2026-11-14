"""Escala pública de 0 a 10, sin modificar las notas históricas de 0 a 100.

El almacenamiento conserva dos decimales sobre 100. Su representación exacta
sobre 10 puede necesitar tres: 69.99 se muestra como 6.999, nunca como 7 aprobado.
La aprobación siempre compara valores almacenados, no valores redondeados.
"""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError


DECIMALES_ALMACENADOS = Decimal('0.01')
DECIMALES_PUBLICOS = Decimal('0.001')


def _decimal(valor):
    texto = str(valor).strip().replace(',', '.')
    if len(texto) > 32:
        raise InvalidOperation
    numero = Decimal(texto)
    if not numero.is_finite():
        raise InvalidOperation
    return numero


def nota_sobre_diez(valor):
    """Decimal exacto 0–10 o None para una nota ausente/no válida; no altera el dato."""
    if valor is None:
        return None
    try:
        nota = _decimal(valor)
        return nota / Decimal(10) if 0 <= nota <= 100 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def nota_desde_diez(valor):
    """Valida una entrada 0–10 (máximo tres decimales) y devuelve el valor 0–100.

    Rechaza NaN, infinitos y precisión que el almacenamiento no puede conservar,
    en vez de redondear una nota por debajo del mínimo hasta convertirla en aprobada.
    """
    try:
        nota = _decimal(valor)
        if not 0 <= nota <= 10:
            raise InvalidOperation
        if nota != nota.quantize(DECIMALES_PUBLICOS):
            raise InvalidOperation
        return (nota * Decimal(10)).quantize(DECIMALES_ALMACENADOS)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError('Escriba una nota entre 0 y 10, con hasta tres decimales.') from None
