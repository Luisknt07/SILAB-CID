"""Version publicada de niveles por solicitud o tarea, sin SQL al importar."""
from contextlib import contextmanager
from contextvars import ContextVar
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.functional import SimpleLazyObject

_niveles = ContextVar('niveles_institucionales', default=None)


def niveles_en_contexto():
    return _niveles.get()


@contextmanager
def con_niveles_institucionales(*, database='default', estricto=False, diferido=False):
    from .niveles import niveles_de_despliegue
    actual = niveles_en_contexto()
    if actual is not None and not estricto:
        yield actual
        return
    def resolver():
        base = niveles_de_despliegue()
        proveedor = getattr(settings, 'ACADEMIC_LEVELS_PROVIDER', '')
        return import_string(proveedor)(base, database=database, estricto=estricto) if proveedor else base
    niveles = SimpleLazyObject(resolver) if diferido and not estricto else resolver()
    token = _niveles.set(niveles)
    try:
        yield niveles
    finally:
        _niveles.reset(token)
