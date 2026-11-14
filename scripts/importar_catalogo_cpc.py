"""Extrae referencias CPC de un XLS aportado sin ejecutar macros ni fórmulas.

Uso: python scripts/importar_catalogo_cpc.py origen.xls destino.json.gz
Requiere xlrd sólo para actualizar el catálogo; la aplicación no lo necesita.
"""
from argparse import ArgumentParser
from collections import Counter
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path


def extraer(origen, incorporado_el):
    import xlrd

    libro = xlrd.open_workbook(str(origen), on_demand=True)
    try:
        hoja = libro.sheet_by_name('CPC')
        cabecera = next((i for i in range(min(30, hoja.nrows))
                         if str(hoja.cell_value(i, 0)).strip().upper() == 'CPC N9'), None)
        if cabecera is None:
            raise ValueError('No se encontró la cabecera CPC N9 del archivo de referencia.')
        filas, codigos = [], set()
        for numero in range(cabecera + 1, hoja.nrows):
            celda = hoja.cell(numero, 0)
            if celda.ctype == xlrd.XL_CELL_NUMBER:
                if celda.value != int(celda.value) or abs(celda.value) > 2**53:
                    raise ValueError(f'Código numérico no exacto en la fila {numero + 1}.')
                codigo = str(int(celda.value))
            else:
                codigo = str(celda.value).strip()
            descripcion = str(hoja.cell_value(numero, 1)).strip()
            if not codigo and not descripcion:
                continue
            if not codigo.isascii() or not codigo.isdecimal() or not 8 <= len(codigo) <= 12:
                raise ValueError(f'Código no reconocido en la fila {numero + 1}.')
            if not descripcion or codigo in codigos:
                raise ValueError(f'Código duplicado o descripción vacía en la fila {numero + 1}.')
            codigos.add(codigo)
            filas.append([codigo, descripcion])
        filas.sort(key=lambda fila: fila[0])
        canonico = json.dumps(filas, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        return {
            'version': 1,
            'fuente': {
                'nombre': origen.name,
                'sha256': hashlib.sha256(origen.read_bytes()).hexdigest(),
                'incorporado_el': incorporado_el,
                'alcance': 'Copia de referencia aportada; no certifica vigencia ni habilitación para contratar.',
                'formato_origen': 'Formulario de solicitud de CPC para giro específico de negocio; sólo se extraen códigos y descripciones.',
                'consulta_oficial': 'https://www.compraspublicas.gob.ec/ProcesoContratacion/compras/EP/buscarComProducto.cpe',
                'registros': len(filas),
                'registros_seleccionables': sum(len(codigo) >= 9 for codigo, _ in filas),
                'longitudes': dict(sorted(Counter(len(codigo) for codigo, _ in filas).items())),
                'datos_sha256': hashlib.sha256(canonico).hexdigest(),
            },
            'productos': filas,
        }
    finally:
        libro.release_resources()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('origen', type=Path)
    parser.add_argument('destino', type=Path)
    parser.add_argument('--incorporado-el', default=date.today().isoformat())
    args = parser.parse_args()
    date.fromisoformat(args.incorporado_el)
    catalogo = extraer(args.origen, args.incorporado_el)
    args.destino.parent.mkdir(parents=True, exist_ok=True)
    salida = json.dumps(catalogo, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with args.destino.open('wb') as archivo:
        with gzip.GzipFile(fileobj=archivo, mode='wb', filename='', mtime=0) as comprimido:
            comprimido.write(salida)
    print(json.dumps(catalogo['fuente'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
