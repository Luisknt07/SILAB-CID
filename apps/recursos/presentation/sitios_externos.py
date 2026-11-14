"""Sitios web enlazados como recursos: si su política permite mostrarlos dentro del portal."""
import hashlib
import ipaddress
import socket
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.core.cache import cache

VIGENCIA = 6 * 60 * 60


def _direccion_publica(anfitrion):
    """No consulta la red interna del servidor a partir de un enlace."""
    try:
        direcciones = {info[4][0] for info in socket.getaddrinfo(anfitrion, None)}
    except (socket.gaierror, UnicodeError):
        return False
    return bool(direcciones) and all(ipaddress.ip_address(d.split('%')[0]).is_global for d in direcciones)


def _admite_origen(fuente, origen):
    """Compara una fuente de frame-ancestors con el origen del portal."""
    if fuente == '*':
        return True
    esquema, _, resto = fuente.rpartition('://')
    anfitrion_fuente = resto.split('/')[0].lower()
    partes = urlsplit(origen)
    if esquema and esquema != partes.scheme:
        return False
    anfitrion = partes.netloc.lower()
    if anfitrion_fuente.startswith('*.'):
        return anfitrion.endswith(anfitrion_fuente[1:])
    return anfitrion_fuente in (anfitrion, partes.hostname)


def politica_permite(cabeceras, origen):
    """Aplica X-Frame-Options y frame-ancestors, como lo hará el navegador."""
    for politica in cabeceras.get_all('Content-Security-Policy') or []:
        for directiva in politica.split(';'):
            nombre, *fuentes = directiva.split()
            if nombre.lower() == 'frame-ancestors':
                # frame-ancestors prevalece sobre X-Frame-Options.
                return any(_admite_origen(f.strip("'").lower(), origen) for f in fuentes)
    return not (cabeceras.get('X-Frame-Options') or '').strip()


def permite_incrustar(url, origen):
    """True si el sitio puede verse dentro del visor servido desde ``origen``."""
    partes = urlsplit(url)
    if partes.scheme not in ('http', 'https') or not partes.hostname:
        return False
    if origen.startswith('https://') and partes.scheme == 'http':
        return False  # El navegador bloquea contenido http dentro de una página https.
    clave = 'sitio-externo:' + hashlib.sha256(f'{url}|{origen}'.encode()).hexdigest()
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado
    resultado = False
    if _direccion_publica(partes.hostname):
        try:
            peticion = Request(url, headers={'User-Agent': 'CITT-visor/1.0'})
            with urlopen(peticion, timeout=5) as respuesta:
                resultado = (_direccion_publica(urlsplit(respuesta.url).hostname or '')
                             and politica_permite(respuesta.headers, origen))
        except (URLError, OSError, ValueError):
            resultado = False
    cache.set(clave, resultado, VIGENCIA)
    return resultado
