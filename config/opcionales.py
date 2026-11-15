"""Decisiones de una instalación que se toman en su entorno.

No importa Django: lo leen por igual la configuración y el registro de
módulos, que debe poder cargarse sin iniciar el sistema.
"""
import ipaddress
import os

AFIRMATIVOS = {'1', 'true', 'yes', 'on', 'si', 'sí'}
NEGATIVOS = {'0', 'false', 'no', 'off'}


def decision(variable, entorno=None, heredada=None):
    """Lo que declaró la instalación: ``True``, ``False`` o ``None`` si no dijo nada.

    ``heredada`` es el nombre anterior de la variable; se sigue leyendo para no
    obligar a cambiar un entorno que ya la define.
    """
    entorno = os.environ if entorno is None else entorno
    for nombre in (variable, heredada):
        valor = (entorno.get(nombre) or '').strip().lower() if nombre else ''
        if not valor:
            continue
        if valor in AFIRMATIVOS:
            return True
        if valor in NEGATIVOS:
            return False
        raise ValueError(f'{nombre} requiere un booleano explícito (true o false).')
    return None


def redes_permitidas(texto):
    """Lista de redes en notación CIDR; una red mal escrita impide arrancar."""
    return tuple(ipaddress.ip_network(parte.strip(), strict=False)
                 for parte in (texto or '').replace(';', ',').split(',') if parte.strip())


def modulo_activo(variable, entorno=None):
    return bool(decision(variable, entorno))


def conexiones_activo(entorno=None):
    """Dispositivos conectados y series de medición: apps/conexiones/README.md."""
    return modulo_activo('SLCID_MODULO_CONEXIONES', entorno)
