"""Límites por minuto atómicos compartidos por todos los procesos PostgreSQL."""
import hashlib
import hmac
import math
from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.utils import timezone
from django.utils.cache import patch_vary_headers


def contar_peticion(categoria, identidad, ahora=None):
    """Suma una petición al minuto en curso y devuelve cuántas van.

    La identidad no se guarda: solo su huella con la clave del sistema. Propaga
    ``DatabaseError`` para que quien llama cierre el acceso si el control falla.
    """
    ahora = ahora or timezone.now()
    tramo = math.floor(ahora.timestamp() / 60)
    clave = hmac.new(settings.SECRET_KEY.encode(), f'{categoria}:{identidad}:{tramo}'.encode(), hashlib.sha256).hexdigest()
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO webcitt_contadorpeticion (clave, total, vence) VALUES (%s, 1, %s) '
            'ON CONFLICT (clave) DO UPDATE SET total = webcitt_contadorpeticion.total + 1 RETURNING total',
            [clave, ahora + timedelta(minutes=2)],
        )
        return cursor.fetchone()[0]


def segundos_hasta_el_minuto(ahora):
    return 60 - int(ahora.timestamp()) % 60


class LimitePeticionesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
            return self.get_response(request)
        name = getattr(getattr(request, 'resolver_match', None), 'url_name', '')
        # El middleware corre antes de resolver la vista: resolver es lectura del URLconf.
        from django.urls import Resolver404, resolve
        propio = False
        try:
            encontrado = resolve(request.path_info)
            name = encontrado.url_name or ''
            # Una entrada para máquinas cuenta por credencial dentro de su vista:
            # el límite por dirección castigaría a todos los equipos de una misma red.
            propio = getattr(encontrado.func, 'limite_propio', False)
        except Resolver404:
            pass
        auth = name in {'login', 'register', 'account_login', 'account_signup', 'account_reset_password',
                        'segundo_factor'} or request.path_info.rstrip('/').endswith('/admin/login')
        write = request.method not in {'GET', 'HEAD', 'OPTIONS'}
        if propio or (not write and not auth):
            return self.get_response(request)
        user = getattr(request, 'user', None)
        user_id = user.pk if user and user.is_authenticated else None
        # REMOTE_ADDR lo fija el proxy local de confianza; nunca se cree X-Forwarded-For.
        identity = request.META.get('REMOTE_ADDR', '') if auth or not user_id else f'user:{user_id}'
        category = 'auth' if auth else 'write'
        limit = settings.RATE_LIMIT_AUTH_PER_MINUTE if auth else settings.RATE_LIMIT_WRITE_PER_MINUTE
        now = timezone.now()
        try:
            total = contar_peticion(category, identity, now)
        except DatabaseError:
            # No se abre el acceso silenciosamente si falla el control compartido.
            response = JsonResponse({'error': 'Servicio temporalmente no disponible.'}, status=503)
            response['Retry-After'] = '60'
            return response
        if total > limit:
            response = JsonResponse({'error': 'Demasiadas peticiones. Inténtalo en un minuto.'}, status=429)
            response['Retry-After'] = str(segundos_hasta_el_minuto(now))
            response['Cache-Control'] = 'no-store'
            patch_vary_headers(response, ['Cookie'])
            return response
        return self.get_response(request)
