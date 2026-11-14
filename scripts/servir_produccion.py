"""Waitress detrás de un único proxy que sobrescribe sus cabeceras."""
import ipaddress
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')
if os.environ['DJANGO_SETTINGS_MODULE'] != 'config.settings_production':
    raise SystemExit('El servidor de producción requiere config.settings_production.')


def _entero_acotado(nombre, predeterminado, minimo, maximo):
    """Fallar al arrancar ante límites inválidos, sin aceptar capacidad ilimitada."""
    try:
        valor = int(os.environ.get(nombre, str(predeterminado)))
    except ValueError:
        raise SystemExit(f'{nombre} debe ser un entero entre {minimo} y {maximo}.') from None
    if not minimo <= valor <= maximo:
        raise SystemExit(f'{nombre} debe estar entre {minimo} y {maximo}.')
    return valor


def argumentos():
    proxy = os.environ.get('TRUSTED_PROXY_IP', '').strip()
    try:
        ipaddress.ip_address(proxy)
    except ValueError:
        raise SystemExit('TRUSTED_PROXY_IP debe ser la IP exacta del proxy; no admite comodines.') from None
    threads = _entero_acotado('WEB_THREADS', 8, 1, 64)
    connection_limit = _entero_acotado('WEB_CONNECTION_LIMIT', 100, 16, 1024)
    if connection_limit < threads:
        raise SystemExit('WEB_CONNECTION_LIMIT no puede ser menor que WEB_THREADS.')
    return dict(listen=os.environ.get('WEB_LISTEN', '127.0.0.1:8000'), threads=threads,
                trusted_proxy=proxy, trusted_proxy_count=1,
                trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto'},
                clear_untrusted_proxy_headers=True, max_request_body_size=64 * 1024 * 1024,
                connection_limit=connection_limit,
                channel_timeout=_entero_acotado('WEB_CHANNEL_TIMEOUT', 60, 15, 300),
                max_request_header_size=32 * 1024,
                expose_tracebacks=False)


if __name__ == '__main__':
    from waitress import serve
    from config.wsgi import application
    serve(application, **argumentos())
