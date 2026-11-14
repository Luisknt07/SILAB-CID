"""Validación y representación común del período de los reportes."""

from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlencode

from django.core.exceptions import BadRequest


def entero_pedido(valor, nombre, *, defecto=None, minimo=1, maximo=9223372036854775807):
    if valor in (None, ''):
        return defecto
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise BadRequest(f'{nombre}: introduce un número entero válido.') from None
    if not minimo <= numero <= maximo:
        raise BadRequest(f'{nombre}: valor fuera del rango permitido.')
    return numero


def anio_pedido(valor, defecto):
    return entero_pedido(valor, 'Año', defecto=defecto, minimo=1900, maximo=9998)


def fecha_pedida(valor, nombre):
    if not valor:
        return None
    try:
        fecha = date.fromisoformat(valor)
        if fecha.isoformat() != valor or not 1900 <= fecha.year <= 9998:
            raise ValueError
        return fecha
    except (TypeError, ValueError):
        raise BadRequest(f'{nombre}: introduce una fecha válida entre 1900 y 9998 (AAAA-MM-DD).') from None


@dataclass(frozen=True)
class PeriodoReporte:
    desde: date | None
    hasta: date | None

    @classmethod
    def pedido(cls, parametros, *, defecto=(None, None), maximo_dias=None,
               claves=('desde', 'hasta')):
        desde = fecha_pedida(parametros.get(claves[0]), 'Desde') or defecto[0]
        hasta = fecha_pedida(parametros.get(claves[1]), 'Hasta') or defecto[1]
        if desde and hasta:
            if desde > hasta:
                desde, hasta = hasta, desde
            if maximo_dias is not None and (hasta - desde).days > maximo_dias:
                desde = hasta - timedelta(days=maximo_dias)
        return cls(desde, hasta)

    def parametros(self):
        return {'desde': self.desde.isoformat() if self.desde else '',
                'hasta': self.hasta.isoformat() if self.hasta else ''}

    def query(self, **extra):
        return urlencode({**extra, **self.parametros()})
