"""Compuerta de perfil: sin datos vigentes no se usan las funciones.

El portal se lee sin cuenta; reservar, gestionar una unidad o escribir una guía
son actos institucionales que quedan registrados a nombre de alguien. Mientras
ese alguien no tenga sus datos completos y confirmados para el período en
curso, la plataforma lo devuelve a su perfil en lugar de dejar constancia
incompleta.
"""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.usuarios.vigencia import estado_perfil


# Rutas donde la persona actúa como usuaria del laboratorio: solicitar,
# seguir y documentar. El resto del portal —inicio, catálogo, noticias, la
# ficha pública de cada unidad— se sigue leyendo con la cuenta incompleta.
#
# El panel de la unidad queda fuera a propósito: ahí se atiende el trabajo de
# otros bajo un rol que asigna la unidad, y dejar sin atender la agenda por un
# dato del perfil personal detendría al laboratorio entero.
RUTAS_CONTROLADAS = ("/reservas/",)
# El módulo de guías queda fuera por la misma razón que el panel: leer una guía
# publicada es lectura, y escribirla, firmarla o validarla es trabajo docente y
# de la unidad, que no puede detenerse por un dato del perfil personal de quien
# lo atiende.
RUTAS_LIBRES = ("/reservas/actividades/guias/",)

AVISO = (
    "Completa y confirma tus datos institucionales para usar los laboratorios: "
    "identifican quién solicita y sostienen los reportes de la Universidad."
)


def _es_ruta_controlada(ruta):
    if ruta.startswith(RUTAS_LIBRES):
        return False
    return ruta.startswith(RUTAS_CONTROLADAS)


class PerfilInstitucionalVigenteMiddleware:
    """Devuelve al perfil a quien todavía no tiene sus datos al día."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if (
            usuario
            and usuario.is_authenticated
            # Quien administra la plataforma no puede quedar fuera de ella.
            and not usuario.is_superuser
            and _es_ruta_controlada(request.path)
            and not estado_perfil(usuario)["vigente"]
        ):
            return self._respuesta(request)
        return self.get_response(request)

    def _respuesta(self, request):
        destino = reverse("profile")
        # Una navegación del navegador se devuelve al perfil; una llamada del
        # asistente recibe el mismo aviso en JSON, que es lo que sabe mostrar.
        navegacion = request.method == "GET" and "text/html" in request.headers.get(
            "accept", ""
        )
        if not navegacion:
            return JsonResponse(
                {"success": False, "error": AVISO, "perfil_url": destino},
                status=403,
            )
        messages.warning(request, AVISO)
        return redirect(f"{destino}?completar=1")
