"""Sonda HTTP local de Compose; no inicia Django ni imprime configuración."""
import ipaddress
import os
import re
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class SinRedirecciones(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def host_permitido(valor):
    for entrada in valor.split(','):
        host = entrada.strip().removeprefix('.')
        if host.startswith('[') and host.endswith(']'):
            try:
                ipaddress.IPv6Address(host[1:-1])
            except ValueError:
                continue
            return host
        if len(host) <= 253 and re.fullmatch(
                r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*'
                r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.?', host):
            return host
    raise ValueError('No hay un Host explícito válido.')


def comprobar():
    try:
        host = host_permitido(os.environ.get('ALLOWED_HOSTS', ''))
    except ValueError:
        return 2
    solicitud = Request('http://127.0.0.1:8000/salud/listo/', method='HEAD', headers={'Host': host})
    # Nunca usar HTTP_PROXY del entorno ni seguir un redirect hacia otro host.
    cliente = build_opener(ProxyHandler({}), SinRedirecciones())
    try:
        with cliente.open(solicitud, timeout=3) as respuesta:
            return 0 if respuesta.status == 204 else 1
    except (OSError, ValueError):
        return 1


if __name__ == '__main__':
    raise SystemExit(comprobar())
