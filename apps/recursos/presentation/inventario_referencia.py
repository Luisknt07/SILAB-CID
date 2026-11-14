"""Lo que se deduce de un insumo sin pedirlo: su unidad de medida, el contenido de su presentación y niveles básicos.

«Bobina de 1 kg» son 1000 g; «Frasco de 500 mL», 500 mL; «Paquete de 50», 50 unidades; «Rollo», 1 rollo. Así la ficha
se llena sola y la unidad solo corrige lo que no corresponda.
"""
import re
import unicodedata
from decimal import Decimal

NIVELES_EN_PRESENTACIONES = {'objetivo': Decimal('4'), 'seguridad': Decimal('1'), 'reorden': Decimal('2')}
PLAZO_DIAS = 15
CONVERSIONES = (
    (r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo)', 'g', Decimal('1000')),
    (r'(\d+(?:[.,]\d+)?)\s*(?:g|gr|gramos?)\b', 'g', Decimal('1')),
    (r'(\d+(?:[.,]\d+)?)\s*(?:l|lt|litros?)\b', 'mL', Decimal('1000')),
    (r'(\d+(?:[.,]\d+)?)\s*(?:ml|mililitros?)\b', 'mL', Decimal('1')),
    (r'(\d+(?:[.,]\d+)?)\s*(?:m|metros?)\b', 'm', Decimal('1')),
    (r'(?:paquete|caja|bolsa|pack|juego|kit|set)\s+(?:de\s+)?(\d+)', 'unidad', Decimal('1')),
    (r'(\d+)\s*(?:unidades|piezas|hojas|laminas|tiras|pares)', 'unidad', Decimal('1')),
)
UNIDADES_POR_PALABRA = (
    ('lamina', 'lámina'), ('rollo', 'rollo'), ('frasco', 'frasco'), ('cartucho', 'cartucho'), ('bobina', 'bobina'),
    ('sobre', 'sobre'), ('bloque', 'bloque'), ('barra', 'barra'), ('galon', 'galón'), ('caja', 'caja'), ('par', 'par'),
)


def _normal(texto):
    return unicodedata.normalize('NFKD', str(texto or '').lower()).encode('ascii', 'ignore').decode()


def inferir_unidad(presentacion, nombre=''):
    """(unidad de medida, contenido por presentación) a partir del texto de la presentación y del nombre."""
    texto = _normal(f'{presentacion} {nombre}')
    for patron, unidad, factor in CONVERSIONES:
        coincidencia = re.search(patron, texto)
        if coincidencia:
            return unidad, (Decimal(coincidencia.group(1).replace(',', '.')) * factor).normalize()
    for palabra, unidad in UNIDADES_POR_PALABRA:
        if re.search(rf'\b{palabra}', _normal(presentacion)):
            return unidad, Decimal('1')
    return 'unidad', Decimal('1')


def completar(consumible):
    """Rellena lo vacío del insumo con lo deducible. Devuelve la lista de campos cambiados (no guarda)."""
    cambiados = []
    if not (consumible.unidad_medida or '').strip():
        unidad, contenido = inferir_unidad(consumible.presentacion, consumible.nombre)
        consumible.unidad_medida = unidad
        cambiados.append('unidad_medida')
        if not consumible.cantidad_por_presentacion or consumible.cantidad_por_presentacion == 1:
            consumible.cantidad_por_presentacion = contenido
            cambiados.append('cantidad_por_presentacion')
    presentacion = Decimal(consumible.cantidad_por_presentacion or 1)
    for campo, presentaciones in (('stock_objetivo', 'objetivo'), ('stock_seguridad', 'seguridad'), ('minimo', 'reorden')):
        if not getattr(consumible, campo):
            setattr(consumible, campo, presentacion * NIVELES_EN_PRESENTACIONES[presentaciones])
            cambiados.append(campo)
    if not consumible.plazo_reposicion_dias:
        consumible.plazo_reposicion_dias = PLAZO_DIAS
        cambiados.append('plazo_reposicion_dias')
    return cambiados
