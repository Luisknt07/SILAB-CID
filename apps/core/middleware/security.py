"""Cabeceras de seguridad adicionales configurables por entorno."""

import secrets

from django.conf import settings


def politica_de_permisos():
    # El servicio de clases en vivo conectado (Daily o BigBlueButton) define a qué origen se dejan cámara y micrófono.
    from django.db import DatabaseError

    from apps.formacion.presentation.servidor_clases_config import origen_del_servidor

    try:
        origen = origen_del_servidor()
    except DatabaseError:
        origen = ''  # Sin base de datos disponible, la cabecera sale sin permisos extra en lugar de romper la respuesta.
    if not origen:
        return "camera=(self), microphone=(), geolocation=(self), fullscreen=(self)"
    # El propio sitio también los conserva: si el aula se abre dentro del visor de la ficha, solo cede a la sala lo
    # que tiene.
    return (f'camera=(self "{origen}"), microphone=(self "{origen}"), display-capture=(self "{origen}"), '
            'geolocation=(self), fullscreen=(self)')


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(32)
        response = self.get_response(request)
        policy = getattr(settings, "CONTENT_SECURITY_POLICY", "").strip()
        if not policy:
            return response
        if policy:
            response.headers.setdefault("Content-Security-Policy", policy.replace("{nonce}", request.csp_nonce))
            if response.get("Content-Type", "").startswith("text/html") and not response.streaming:
                response["Cache-Control"] = "private, no-store"
        # La cámara para el propio sitio (lector de etiquetas de equipos) y, si hay servidor de clases en vivo,
        # cámara, micrófono y pantalla compartida para la sala de BigBlueButton que se abre dentro del aula.
        if response.get("Content-Type", "").startswith("text/html"):
            response.headers.setdefault("Permissions-Policy", politica_de_permisos())
        return response

