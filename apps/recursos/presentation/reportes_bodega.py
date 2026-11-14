"""Los reportes de bienes de bodega: cómo se leen y qué dicen de un código.

Bodega entrega su «Reporte de bienes» en CSV (separado por punto y coma o coma) con el código del bien,
BLD/BCA, la descripción, modelo, marca, color, material, dimensiones, ubicación, custodio, fecha de ingreso
y valor contable. Los reportes ya conciliados se guardan en apps/recursos/management/bienes_bodega/<slug de la
unidad>/<código del área>.csv: el importador los carga y el lector los consulta, para que un código que
aún no está en el sistema llegue con su descripción, marca, modelo, unidad y área.
"""
import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from apps.recursos.presentation.catalogo_inventario import normalizar
from apps.recursos.presentation.codigos_equipo import limpiar_codigo_bien

CARPETA = Path(__file__).resolve().parents[1] / 'management' / 'bienes_bodega'
COLUMNAS = {
    'codigo_bien': ('codigo del bien', 'codigo bien', 'codigo'),
    'tipo_bien': ('bld o bca', 'bld bca', 'tipo de bien', 'tipo bien', 'bld', 'tipo'),
    'descripcion': ('serie identificacion', 'descripcion', 'identificacion'),
    'modelo': ('modelo caracteristicas', 'modelo'),
    'marca': ('marca otros', 'marca'),
    'color': ('color',),
    'material': ('material',),
    'dimensiones': ('dimensiones',),
    'ubicacion_bodega': ('ubicacion de bodega', 'ubicacion bodega', 'ubicacion'),
    'custodio': ('custodio actual', 'custodio'),
    'fecha_ingreso': ('fecha de ingreso', 'fecha ingreso', 'fecha'),
    'valor_contable': ('valor contable', 'valor'),
    'observaciones': ('observaciones',),
    # Columnas opcionales para conciliar a mano: a qué equipo del sistema pertenece y cómo se llama lo nuevo.
    'codigo_sistema': ('codigo del sistema', 'codigo sistema', 'codigo_sistema'),
    'nombre': ('nombre del equipo', 'nombre_equipo'),
}


def leer(ruta):
    """Las filas del reporte, cada una con los campos de COLUMNAS que el archivo trae."""
    contenido = Path(ruta).read_bytes().decode('utf-8-sig', errors='replace')
    separador = ';' if contenido.count(';') >= contenido.count(',') else ','
    filas = list(csv.reader(contenido.splitlines(), delimiter=separador))
    if not filas:
        raise ValueError('El archivo está vacío.')
    encabezado = [normalizar(columna) for columna in filas[0]]
    indices = {}
    for campo, nombres in COLUMNAS.items():
        indice = next((i for nombre in map(normalizar, nombres) for i, columna in enumerate(encabezado)
                       if columna == nombre or columna.startswith(nombre)), None)
        if indice is not None:
            indices[campo] = indice
    if 'codigo_bien' not in indices or 'descripcion' not in indices:
        raise ValueError('Faltan las columnas «Código del bien» y «Serie/Identificación».')
    for fila in filas[1:]:
        if any(celda.strip() for celda in fila):
            yield {campo: (fila[indice].strip() if indice < len(fila) else '') for campo, indice in indices.items()}


def serie_de(bien):
    """El número de serie, que bodega anota en «Dimensiones» o en la descripción como «SN: …»."""
    coincidencia = re.search(r'\bS/?N\s*:?\s*([A-Za-z0-9-]{4,})', f"{bien.get('dimensiones', '')} {bien.get('observaciones', '')}")
    return coincidencia.group(1) if coincidencia else ''


def fecha_de(texto):
    for formato in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            continue
    return None


def valor_de(texto):
    try:
        return Decimal(texto.replace(' ', '').replace(',', '.')) if texto.strip() else None
    except InvalidOperation:
        return None


def _huella():
    """Cambia cuando se agrega, quita o modifica un reporte guardado."""
    return tuple((str(ruta), ruta.stat().st_mtime_ns) for ruta in sorted(CARPETA.glob('*/*.csv')))


@lru_cache(maxsize=2)
def _indice(huella):
    indice = {}
    for ruta, _momento in huella:
        archivo = Path(ruta)
        for bien in leer(archivo):
            codigo = limpiar_codigo_bien(bien.get('codigo_bien'))
            if codigo:
                indice[codigo] = {**bien, 'unidad': archivo.parent.name, 'area': archivo.stem}
    return indice


def bien_de_bodega(codigo):
    """Lo que los reportes guardados dicen de un código de bien (con la unidad y el área), o None."""
    return _indice(_huella()).get(limpiar_codigo_bien(codigo))
