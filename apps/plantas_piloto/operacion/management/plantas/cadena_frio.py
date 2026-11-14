"""El límite de conservación de los productos con cadena de frío de las plantas cargadas.

Los congelados (helados, paletas, masas y pulpas congeladas) se conservan a
−18 °C o menos; el resto de lo refrigerado, a 4 °C o menos. El cargador solo lo
declara donde la planta no fijó el suyo, así que un valor corregido no se pisa.
"""
import re
from decimal import Decimal

CONGELADO = Decimal('-18')
REFRIGERADO = Decimal('4')
PATRON_CONGELADO = re.compile(r'congelad|helad|paleta', re.IGNORECASE)


def temperatura_de_conservacion(nombre, familia=''):
    return CONGELADO if PATRON_CONGELADO.search(f'{nombre} {familia}') else REFRIGERADO
