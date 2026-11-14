"""Consulta local de la copia CPC aportada para preparar necesidades nuevas.

Los productos son referencias de clasificación, no activos de inventario.
Encontrar un código no confirma su aplicabilidad ni su vigencia en el SOCE.
"""
from copy import deepcopy
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata


RUTA_CATALOGO = Path(__file__).resolve().parent.parent / 'data' / 'cpc_referencia.json.gz'
_CODIGO = re.compile(r'[0-9]{9,12}\Z', flags=re.ASCII)


def _normalizado(valor):
    texto = unicodedata.normalize('NFKD', str(valor or '').casefold())
    return ' '.join(''.join(c for c in texto if not unicodedata.combining(c)).split())


@lru_cache(maxsize=1)
def _catalogo():
    with gzip.open(RUTA_CATALOGO, 'rt', encoding='utf-8') as archivo:
        datos = json.load(archivo)
    productos = datos['productos']
    canonico = json.dumps(productos, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if (datos.get('version') != 1 or len(productos) != datos['fuente']['registros']
            or hashlib.sha256(canonico).hexdigest() != datos['fuente']['datos_sha256']):
        raise ValueError('La copia local del catálogo CPC no coincide con su referencia.')
    indice = {codigo: descripcion for codigo, descripcion in productos}
    if len(indice) != len(productos):
        raise ValueError('La copia local del catálogo CPC contiene códigos duplicados.')
    buscables = tuple((codigo, descripcion, _normalizado(descripcion))
                     for codigo, descripcion in productos if _CODIGO.fullmatch(codigo))
    return datos['fuente'], indice, buscables


def fuente_catalogo_cpc():
    """Procedencia de los datos, sin atribuirles una fecha de vigencia ausente."""
    return deepcopy(_catalogo()[0])


def validar_codigo_cpc(codigo):
    """El informe interno permite dejar el CPC pendiente de clasificación.

    No se exige coincidencia con una copia que puede quedar desactualizada.
    Se conservan códigos extendidos existentes en el catálogo oficial, sin
    truncarlos ni completar ceros; Compras verifica la categoría aplicable.
    """
    if not isinstance(codigo, str):
        return 'Escribe el CPC como texto para conservar todos sus dígitos.'
    if codigo.strip() and not _CODIGO.fullmatch(codigo.strip()):
        return 'Escribe el código CPC de 9 a 12 dígitos, sin puntos ni espacios, o déjalo por confirmar.'
    return ''


def referencia_cpc(codigo):
    """Una coincidencia exacta no sustituye la revisión de Compras."""
    if not isinstance(codigo, str):
        return None
    codigo = codigo.strip()
    fuente, indice, _buscables = _catalogo()
    descripcion = indice.get(codigo)
    if descripcion is None:
        return None
    return {'codigo': codigo, 'descripcion': descripcion, 'estado': 'por_validar',
            'seleccionable': bool(_CODIGO.fullmatch(codigo)),
            'fuente': {'nombre': fuente['nombre'], 'sha256': fuente['sha256'],
                       'incorporado_el': fuente['incorporado_el']}}


def buscar_cpc(consulta, limite=20):
    """Busca todos los términos por nombre o prefijo exacto del código."""
    consulta = _normalizado(consulta)[:120]
    if len(consulta) < 2:
        return []
    try:
        limite = max(1, min(int(limite), 30))
    except (TypeError, ValueError, OverflowError):
        limite = 20
    terminos = consulta.split()
    candidatos = []
    for codigo, descripcion, normalizada in _catalogo()[2]:
        if codigo == consulta:
            orden = 0
        elif codigo.startswith(consulta):
            orden = 1
        elif normalizada == consulta:
            orden = 2
        elif normalizada.startswith(consulta):
            orden = 3
        elif all(termino in normalizada for termino in terminos):
            orden = 4
        else:
            continue
        candidatos.append((orden, codigo, descripcion))
    candidatos.sort(key=lambda fila: (fila[0], fila[1]))
    return [{'codigo': codigo, 'descripcion': descripcion, 'estado': 'por_validar'}
            for _orden, codigo, descripcion in candidatos[:limite]]


def fijar_referencia_cpc(fila):
    """Deriva la descripción y procedencia del servidor al guardar un borrador.

    Nunca confía en una etiqueta o estado de validación enviado por el cliente.
    Sólo el flujo administrativo competente puede confirmar la clasificación.
    Las copias emitidas no deben pasar por este normalizador.
    """
    copia = deepcopy(fila)
    for clave in ('cpc_descripcion', 'cpc_fuente', 'cpc_estado'):
        copia.pop(clave, None)
    codigo = str(fila.get('cpc') or '').strip()
    if not codigo:
        return copia
    referencia = referencia_cpc(codigo)
    copia['cpc_estado'] = 'por_validar'
    if referencia and referencia['seleccionable']:
        copia['cpc_descripcion'] = referencia['descripcion']
        copia['cpc_fuente'] = referencia['fuente']
    return copia
