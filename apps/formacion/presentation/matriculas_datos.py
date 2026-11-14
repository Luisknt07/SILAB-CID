"""Validación de datos de matrícula y listas CSV antes de modificar registros."""
import csv
import io

from django.core.exceptions import ValidationError
from apps.core.models.datos_matricula import normalizar_correo as normalizar_correo, validar_datos_matricula

MAX_FILAS_MATRICULA = 100
MAX_BYTES_MATRICULA = 1_048_576
CABECERA_MATRICULA = ('correo', 'documento', 'nombres_completos')


def leer_lista_matricula(contenido):
    """Devuelve filas normalizadas; un error rechaza toda la lista, sin escrituras."""
    if isinstance(contenido, str):
        contenido = contenido.encode('utf-8')
    if len(contenido) > MAX_BYTES_MATRICULA:
        raise ValidationError('La lista supera 1 MB.')
    try:
        texto = contenido.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValidationError('Guarda la lista como CSV UTF-8.') from error
    primera = texto.splitlines()[0] if texto.splitlines() else ''
    separador = ';' if primera.count(';') == 2 and primera.count(',') == 0 else ','
    lector = csv.reader(io.StringIO(texto, newline=''), delimiter=separador, strict=True)
    try:
        cabecera = next(lector, [])
        if tuple(cabecera) not in (CABECERA_MATRICULA, ('correo', 'cedula', 'nombres_completos')):
            raise ValidationError('Cabecera requerida: correo,documento,nombres_completos. También se admite cedula en lugar de documento.')
        filas, errores, correos, documentos = [], [], set(), set()
        for numero, fila in enumerate(lector, start=2):
            if not fila or all(not celda.strip() for celda in fila):
                continue
            if len(filas) + len(errores) >= MAX_FILAS_MATRICULA:
                raise ValidationError('La lista admite hasta 100 personas.')
            if len(fila) != 3:
                errores.append(f'Fila {numero}: se requieren tres columnas.')
                continue
            try:
                datos = validar_datos_matricula(correo=fila[0], documento=fila[1], nombres_completos=fila[2])
                if datos['correo'] in correos:
                    raise ValidationError('El correo está repetido en la lista.')
                if datos['documento'] in documentos:
                    raise ValidationError('El documento está repetido en la lista.')
                correos.add(datos['correo'])
                documentos.add(datos['documento'])
                filas.append(datos)
            except ValidationError as error:
                errores.append(f'Fila {numero}: ' + ' '.join(error.messages))
    except csv.Error as error:
        raise ValidationError('No se pudo leer el CSV. Revisa las comillas y las tres columnas.') from error
    if errores:
        raise ValidationError(errores[:20])
    if not filas:
        raise ValidationError('Añade al menos una persona a la lista.')
    return filas
