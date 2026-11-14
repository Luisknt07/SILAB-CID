"""Ambito explicito para resolver una presentacion una vez por solicitud/tarea."""

from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.functional import SimpleLazyObject


_identidad_presentada = ContextVar('identidad_presentada', default=None)


def identidad_en_contexto():
    return _identidad_presentada.get()


@contextmanager
def con_presentacion_institucional(*, diferido=False):
    """Tambien para tareas/correos: no consulta la base durante import o checks."""
    from .identidad import identidad_de_despliegue

    existente = identidad_en_contexto()
    if existente is not None:
        yield existente
        return
    def resolver():
        base = identidad_de_despliegue()
        proveedor = getattr(settings, 'PUBLIC_IDENTITY_PROVIDER', '')
        return import_string(proveedor)(base) if proveedor else base
    identidad = SimpleLazyObject(resolver) if diferido else resolver()
    token = _identidad_presentada.set(identidad)
    try:
        yield identidad
    finally:
        _identidad_presentada.reset(token)


class PresentacionInstitucionalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .catalogo_institucional import con_catalogo_institucional
        from .niveles_institucionales import con_niveles_institucionales
        from .calendario_institucional import con_calendario_institucional

        with con_presentacion_institucional(diferido=True), con_catalogo_institucional(diferido=True), con_niveles_institucionales(diferido=True), con_calendario_institucional(diferido=True):
            return self.get_response(request)
