"""Lectura acotada de listas: sólo datos, sin fórmulas, vínculos o código ejecutable."""
import csv
import io
import re
import unicodedata
import zipfile
from pathlib import Path

from defusedxml.ElementTree import fromstring, iterparse
from django.core.exceptions import ValidationError

from apps.formacion.presentation.matriculas_datos import validar_datos_matricula

MAX_FILAS = 500
MAX_BYTES = 2 * 1024 * 1024
MAX_DESCOMPRIMIDO = 20 * 1024 * 1024


def _cabecera(valor):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', str(valor or '')) if not unicodedata.combining(c))
    texto = '_'.join(texto.strip().lower().split())
    return {'cedula': 'documento', 'nombres': 'nombres_completos',
            'nombres_y_apellidos': 'nombres_completos', 'nombres_y_apellidos_completos': 'nombres_completos',
            'apellidos_y_nombres': 'nombres_completos', 'nombre_completo': 'nombres_completos',
            'email': 'correo'}.get(texto, texto)


def _xlsx(contenido):
    from openpyxl import load_workbook
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
            archivos = paquete.infolist()
            if len(archivos) > 1000 or sum(a.file_size for a in archivos) > MAX_DESCOMPRIMIDO:
                raise ValidationError('El Excel descomprimido supera el límite permitido.')
            for archivo in archivos:
                nombre = archivo.filename.lower()
                if archivo.flag_bits & 1 or 'vbaproject' in nombre or 'externallinks/' in nombre or 'embeddings/' in nombre:
                    raise ValidationError('Use un Excel sin macros, objetos incrustados ni vínculos externos.')
                if archivo.file_size > 1024 * 1024 and archivo.file_size > max(archivo.compress_size, 1) * 200:
                    raise ValidationError('El archivo contiene una compresión no permitida.')
                if nombre.startswith('xl/worksheets/') and nombre.endswith('.xml'):
                    # La dimensión declarada puede mentir: limita también las celdas reales del XML.
                    for _, elemento in iterparse(io.BytesIO(paquete.read(archivo)), events=('start',)):
                        etiqueta = elemento.tag.rsplit('}', 1)[-1]
                        if etiqueta in ('f', 'hyperlink'):
                            raise ValidationError('Retire las fórmulas y los hipervínculos del Excel.')
                        if etiqueta == 'row' and int(elemento.attrib.get('r', 0)) > MAX_FILAS + 1:
                            raise ValidationError('La lista admite hasta 500 participantes.')
                        if etiqueta == 'c':
                            referencia = elemento.attrib.get('r', '')
                            if not re.fullmatch(r'[A-C][1-9][0-9]*', referencia) or int(referencia[1:]) > MAX_FILAS + 1:
                                raise ValidationError('Use la plantilla: hasta 500 filas y sólo las columnas requeridas.')
                if nombre.endswith('.rels'):
                    relaciones = fromstring(paquete.read(archivo))
                    if any(r.attrib.get('TargetMode', '').lower() == 'external' for r in relaciones):
                        raise ValidationError('Retire los vínculos externos y los hipervínculos del Excel.')
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=False, keep_links=False)
        try:
            if len(libro.worksheets) != 1:
                raise ValidationError('La lista debe tener una sola hoja de participantes.')
            hoja = libro.worksheets[0]
            if (hoja.max_row or 0) > MAX_FILAS + 1 or (hoja.max_column or 0) > 3:
                raise ValidationError('Use la plantilla: hasta 500 filas y sólo las columnas requeridas.')
            filas = []
            for celdas in hoja.iter_rows(max_row=MAX_FILAS + 2, max_col=3):
                valores = []
                for celda in celdas:
                    if celda.data_type == 'f':
                        raise ValidationError(f'Fila {celda.row}: retire las fórmulas y pegue únicamente valores.')
                    valores.append(celda.value)
                filas.append(valores)
            while filas and all(v in (None, '') for v in filas[-1]):
                filas.pop()
            return filas
        finally:
            libro.close()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError('No se pudo leer el Excel. Use un archivo XLSX válido de la plantilla.') from exc


def leer_participantes(archivo, modo):
    """Devuelve todos los errores por fila; una lista con errores no se confirma."""
    if modo not in ('evento', 'matricula'):
        raise ValidationError('Seleccione una operación válida.')
    if getattr(archivo, 'size', 0) > MAX_BYTES:
        raise ValidationError('El archivo debe pesar como máximo 2 MB.')
    contenido = archivo.read(MAX_BYTES + 1)
    if not contenido or len(contenido) > MAX_BYTES:
        raise ValidationError('Adjunte una lista de hasta 2 MB.')
    extension = Path(archivo.name).suffix.lower()
    if extension == '.xlsx':
        filas = _xlsx(contenido)
    elif extension == '.csv':
        try:
            texto = contenido.decode('utf-8-sig')
            separador = ';' if texto.partition('\n')[0].count(';') > texto.partition('\n')[0].count(',') else ','
            filas = []
            for fila in csv.reader(io.StringIO(texto), delimiter=separador, strict=True):
                if len(filas) > MAX_FILAS:
                    raise ValidationError('La lista admite hasta 500 participantes.')
                filas.append(fila)
        except (UnicodeError, csv.Error) as exc:
            raise ValidationError('Use un CSV UTF-8 válido, separado por coma o punto y coma.') from exc
    else:
        raise ValidationError('Se admiten archivos XLSX y CSV UTF-8.')
    if not filas:
        raise ValidationError('La lista está vacía.')
    cabecera = [_cabecera(v) for v in filas.pop(0)]
    while cabecera and not cabecera[-1]:
        cabecera.pop()
    requeridos = {'documento', 'nombres_completos'} | ({'correo'} if modo == 'matricula' else set())
    if len(cabecera) != len(requeridos) or set(cabecera) != requeridos:
        raise ValidationError('Cabecera requerida: cedula,nombres_completos' + (',correo' if modo == 'matricula' else '') + '.')
    if len(filas) > MAX_FILAS:
        raise ValidationError('La lista admite hasta 500 participantes.')
    resultado, vistos = [], {'documento': {}, 'correo': {}}
    for numero, valores in enumerate(filas, start=2):
        if not any(v not in (None, '') for v in valores):
            continue
        fila = {'numero': numero, 'datos': {}, 'errores': [], 'estado': 'Por revisar'}
        resultado.append(fila)
        if any(v not in (None, '') for v in valores[len(cabecera):]):
            fila['errores'].append('Hay columnas adicionales. Use la plantilla.')
        datos = dict(zip(cabecera, list(valores[:len(cabecera)]) + [''] * max(0, len(cabecera) - len(valores))))
        fila['datos'] = {k: str(v or '').strip()[:254] for k, v in datos.items()}
        if isinstance(datos.get('documento'), (int, float)):
            fila['errores'].append('La cédula debe ser texto para conservar los ceros iniciales. Revise el documento original y vuelva a escribirlo como texto.')
        if any(str(v or '').lstrip().startswith(('=', '+', '-', '@')) for v in datos.values()):
            fila['errores'].append('Pegue únicamente datos; no se admiten fórmulas.')
        try:
            normalizados = validar_datos_matricula(documento=datos.get('documento'),
                nombres_completos=datos.get('nombres_completos'), **({'correo': datos.get('correo')} if modo == 'matricula' and datos.get('correo') else {}))
            fila['datos'] = normalizados
            if modo == 'matricula':
                fila['datos'].setdefault('correo', '')
        except ValidationError as exc:
            fila['errores'].extend(exc.messages)
        for clave in requeridos & {'documento', 'correo'}:
            valor = fila['datos'].get(clave, '').casefold()
            if valor and valor in vistos[clave]:
                anterior = vistos[clave][valor]
                fila['errores'].append(f'{clave.title()} repetido en la fila {anterior["numero"]}.')
                anterior['errores'].append(f'{clave.title()} repetido en la fila {numero}.')
            elif valor:
                vistos[clave][valor] = fila
    if not resultado:
        raise ValidationError('La lista no contiene participantes.')
    return resultado
