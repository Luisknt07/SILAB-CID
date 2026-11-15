"""Credencial de un dispositivo: ``<identificador>.<secreto>``.

El secreto son 256 bits aleatorios y solo se guarda su huella SHA-256. Con esa
entropía no hace falta un derivador lento, que además costaría cientos de
milisegundos en cada envío de lecturas.
"""
import hashlib
import hmac
import secrets


def nuevo_secreto():
    return secrets.token_urlsafe(32)


def huella(secreto):
    return hashlib.sha256(secreto.encode('utf-8')).hexdigest()


def componer(identificador, secreto):
    return f'{identificador}.{secreto}'


def separar(credencial):
    """Devuelve (identificador, secreto) o ``None`` si la credencial no tiene la forma esperada."""
    identificador, punto, secreto = (credencial or '').partition('.')
    if not punto or not identificador.isascii() or not identificador.isdigit() or len(identificador) > 18:
        return None
    if not 20 <= len(secreto) <= 200:
        return None
    return int(identificador), secreto


def coincide(secreto, huella_guardada):
    return bool(huella_guardada) and hmac.compare_digest(huella(secreto), huella_guardada)
