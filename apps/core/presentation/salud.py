"""Sondas de infraestructura sin sesiones, plantillas ni datos de negocio."""
from django.conf import settings
from django.db import DatabaseError, connection, connections
from django.core.exceptions import DisallowedHost
from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


def _respuesta(estado):
    # text/plain evita proveedores de permisos/CSP específicos de HTML.
    respuesta = HttpResponse(status=estado, content_type='text/plain; charset=utf-8')
    add_never_cache_headers(respuesta)
    return respuesta


@never_cache
@require_safe
def vivo(request):
    return _respuesta(204)


@never_cache
@require_safe
def listo(request):
    try:
        # Un destino preparado con el flag apagado no es dependencia del web.
        bases = [connection]
        if getattr(settings, 'CENTROS_DB_ENABLED', False):
            bases.append(connections['centros'])
        disponible = True
        for base in bases:
            with base.cursor() as cursor:
                cursor.execute('SELECT 1')
                disponible = disponible and cursor.fetchone() == (1,)
    except DatabaseError:
        disponible = False
    return _respuesta(204 if disponible else 503)


SONDAS = {'vivo/': vivo, 'listo/': listo}


class SaludInternaMiddleware:
    """Solo estas sondas evitan sesión, RLS y controles de módulos funcionales.

    SecurityMiddleware y SecurityHeadersMiddleware se ejecutan antes. El Host
    se valida incluso si SSL ya fue establecido por el proxy de confianza.
    Nginx bloquea /salud/ desde la entrada pública.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        vista = SONDAS.get(request.path_info.removeprefix('/salud/')) if request.path_info.startswith('/salud/') else None
        if vista is None:
            return self.get_response(request)
        try:
            request.get_host()
        except DisallowedHost:
            return _respuesta(400)
        respuesta = vista(request)
        # HttpResponseNotAllowed también debe evitar proveedores para HTML.
        respuesta['Content-Type'] = 'text/plain; charset=utf-8'
        return respuesta
