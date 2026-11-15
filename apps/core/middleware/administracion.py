"""Entrada al administrador: red autorizada y segundo factor.

Cubre todo lo que cuelga del administrador, también las búsquedas de su
interfaz. Fuera de las redes autorizadas responde como si no existiera; dentro,
una sesión con permiso de entrada debe haber presentado su segundo factor.
"""
from urllib.parse import urlencode

from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.acceso import segundo_factor

PREFIJOS = ('/admin/', '/grappelli/')


class AccesoAdministracionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path_info.startswith(PREFIJOS):
            return self.get_response(request)
        if not segundo_factor.red_autorizada(request):
            raise Http404
        usuario = getattr(request, 'user', None)
        if (segundo_factor.exigido() and usuario is not None and usuario.is_authenticated
                and not segundo_factor.sesion_verificada(request)):
            from django.contrib import admin

            # Quien no puede entrar recibe la respuesta habitual del administrador, sin pedirle un alta.
            if admin.site.has_permission(request):
                if request.method not in ('GET', 'HEAD'):
                    return HttpResponseForbidden('Confirma tu segundo factor antes de continuar.')
                return redirect(reverse('segundo_factor') + '?' + urlencode({'next': request.get_full_path()}))
        return self.get_response(request)
