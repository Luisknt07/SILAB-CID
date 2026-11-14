"""Controladores síncronos heredados: se importan al atender su primera petición.

Las rutas conservan nombre, módulo y argumentos. Los metadatos que Django
lee antes de invocar la vista (CSRF) se declaran explícitamente y se verifican
en las pruebas de contrato; nunca se deducen desde datos de un usuario.
"""
from functools import lru_cache

from django.utils.module_loading import import_string


@lru_cache(maxsize=None)
def vista_diferida(ruta, *, csrf_exempt=False):
    modulo, nombre = ruta.rsplit('.', 1)

    @lru_cache(maxsize=1)
    def controlador():
        return import_string(ruta)

    def vista(request, *args, **kwargs):
        return controlador()(request, *args, **kwargs)

    vista.__module__ = modulo
    vista.__name__ = vista.__qualname__ = nombre
    vista.csrf_exempt = csrf_exempt
    vista.ruta_diferida = ruta
    vista.controlador = controlador
    return vista
