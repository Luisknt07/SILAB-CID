"""CORS explícito. CSRF, autenticación y permisos siguen siendo obligatorios."""
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.cache import patch_vary_headers


class OrigenesPermitidosMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('Origin')
        own = request.build_absolute_uri('/').rstrip('/')
        allowed = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', ()))
        # En desarrollo el proxy del IDE puede declarar HTTPS mientras el formulario sigue en localhost HTTP.
        trusted_local = origin in settings.CSRF_TRUSTED_ORIGINS and urlsplit(origin).netloc == urlsplit(own).netloc
        cross = bool(origin and origin != own and not trusted_local)
        if cross and origin not in allowed:
            return JsonResponse({'error': 'Origen no permitido.'}, status=403)
        preflight = request.method == 'OPTIONS' and request.headers.get('Access-Control-Request-Method')
        if preflight:
            method = request.headers['Access-Control-Request-Method'].upper()
            headers = {h.strip().lower() for h in request.headers.get('Access-Control-Request-Headers', '').split(',') if h.strip()}
            permitted = {'content-type', 'x-csrftoken', 'x-requested-with'}
            if not origin or method not in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'} or not headers <= permitted:
                return HttpResponse(status=403)
            response = HttpResponse(status=204)
            response['Access-Control-Allow-Methods'] = 'GET, HEAD, POST, PUT, PATCH, DELETE'
            response['Access-Control-Allow-Headers'] = ', '.join(sorted(permitted))
            response['Access-Control-Max-Age'] = '600'
        else:
            response = self.get_response(request)
        if origin:
            patch_vary_headers(response, ['Origin'])
        if cross:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
        return response


def origen_https_valido(value):
    try:
        parsed = urlsplit(value)
        parsed.port  # También valida puertos y direcciones IPv6.
    except ValueError:
        return False
    return bool(parsed.scheme == 'https' and parsed.hostname and not parsed.username
                and not parsed.password and not parsed.query and not parsed.fragment
                and parsed.path == '' and '*' not in value)
