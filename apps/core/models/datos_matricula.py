"""Reglas puras de datos de matrícula compartidas por modelos y aplicación."""
import re
import unicodedata

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from apps.core.documentos_identidad import cedula_ecuatoriana_valida


def _texto_simple(valor, *, etiqueta, maximo):
    texto = unicodedata.normalize('NFKC', str(valor or '')).strip()
    if any(unicodedata.category(caracter) in ('Cc', 'Cf') for caracter in texto) or '<' in texto or '>' in texto:
        raise ValidationError(f'{etiqueta}: utiliza texto simple, sin etiquetas ni caracteres de control.')
    texto = ' '.join(texto.split())
    if not texto or len(texto) > maximo:
        raise ValidationError(f'{etiqueta}: completa el dato con un máximo de {maximo} caracteres.')
    return texto


def normalizar_correo(correo):
    correo = str(correo or '').strip().lower()
    validate_email(correo)
    if len(correo) > 254:
        raise ValidationError('El correo supera los 254 caracteres.')
    return correo


def validar_datos_matricula(*, nombres_completos, documento, correo=None):
    errores = {}
    try:
        nombre = _texto_simple(nombres_completos, etiqueta='Nombres completos', maximo=200)
        if nombre.startswith(('=', '+', '-', '@')):
            raise ValidationError('Escribe nombres completos, sin fórmulas de hoja de cálculo.')
        if not any(caracter.isalpha() for caracter in nombre):
            raise ValidationError('Escribe los nombres completos de la persona.')
    except ValidationError as error:
        errores['nombres_completos'] = error.messages
        nombre = ''
    try:
        documento = _texto_simple(documento, etiqueta='Documento de identidad', maximo=30).upper()
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9 .-]{3,29}', documento):
            raise ValidationError('Utiliza entre 4 y 30 letras, números, espacios, puntos o guiones para el documento.')
        if documento.isdigit() and len(documento) == 10:
            if not cedula_ecuatoriana_valida(documento):
                raise ValidationError('La cédula no es válida. Revisa los diez dígitos.')
    except ValidationError as error:
        errores['documento'] = error.messages
        documento = ''
    if correo is not None:
        try:
            correo = normalizar_correo(correo)
        except ValidationError as error:
            errores['correo'] = error.messages
    if errores:
        raise ValidationError(errores)
    datos = {'nombres_completos': nombre, 'documento': documento}
    if correo is not None:
        datos['correo'] = correo
    return datos

