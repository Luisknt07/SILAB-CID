"""Códigos temporales de un solo uso (TOTP, RFC 6238) con la biblioteca estándar.

Es el algoritmo de las aplicaciones autenticadoras habituales: HMAC-SHA1,
seis dígitos y pasos de treinta segundos. No guarda ni decide nada: las reglas
de acceso están en ``segundo_factor``.
"""
import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote, urlencode

PASO_SEGUNDOS = 30
DIGITOS = 6
# Un paso antes y uno después: tolera relojes desfasados hasta medio minuto.
TOLERANCIA_PASOS = 1


def nuevo_secreto():
    """Veinte bytes aleatorios en base32, como los pide una aplicación autenticadora."""
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii')


def paso_de(instante):
    return int(instante) // PASO_SEGUNDOS


def codigo(secreto, paso):
    clave = base64.b32decode(secreto, casefold=True)
    resumen = hmac.new(clave, struct.pack('>Q', paso), hashlib.sha1).digest()
    desplazamiento = resumen[-1] & 0x0F
    valor = struct.unpack('>I', resumen[desplazamiento:desplazamiento + 4])[0] & 0x7FFFFFFF
    return str(valor % 10 ** DIGITOS).zfill(DIGITOS)


def paso_valido(secreto, propuesto, instante, ultimo_paso=None):
    """Devuelve el paso al que corresponde el código, o ``None``.

    Un paso ya usado no vuelve a aceptarse: quien observe un código no puede
    repetirlo dentro de su ventana.
    """
    propuesto = ''.join(caracter for caracter in str(propuesto or '') if not caracter.isspace())
    if len(propuesto) != DIGITOS or not propuesto.isascii() or not propuesto.isdigit():
        return None
    actual = paso_de(instante)
    encontrado = None
    for paso in range(actual - TOLERANCIA_PASOS, actual + TOLERANCIA_PASOS + 1):
        # Se comparan todos los candidatos: el tiempo de respuesta no revela cuál coincidió.
        coincide = hmac.compare_digest(codigo(secreto, paso), propuesto)
        if coincide and (ultimo_paso is None or paso > ultimo_paso):
            encontrado = paso
    return encontrado


def direccion_de_alta(secreto, cuenta, emisor):
    """Dirección ``otpauth://`` que una aplicación autenticadora lee desde un código QR."""
    etiqueta = quote(f'{emisor}:{cuenta}', safe='')
    return f'otpauth://totp/{etiqueta}?' + urlencode({
        'secret': secreto, 'issuer': emisor, 'algorithm': 'SHA1', 'digits': DIGITOS, 'period': PASO_SEGUNDOS})
