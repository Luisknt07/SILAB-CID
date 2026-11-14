"""Version publicada de calendario por solicitud o tarea, sin SQL al importar."""
from contextlib import contextmanager
from contextvars import ContextVar
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.functional import SimpleLazyObject

_calendario = ContextVar('calendario_institucional', default=None)


def calendario_en_contexto():
    return _calendario.get()


@contextmanager
def con_calendario_institucional(*, database='default', estricto=False, diferido=False):
    from .calendario import calendario_de_despliegue
    actual = calendario_en_contexto()
    if actual is not None and not estricto:
        yield actual
        return
    def resolver():
        base = calendario_de_despliegue()
        proveedor = getattr(settings, 'ACADEMIC_CALENDAR_PROVIDER', '')
        return import_string(proveedor)(base, database=database, estricto=estricto) if proveedor else base
    calendario = SimpleLazyObject(resolver) if diferido and not estricto else resolver()
    token = _calendario.set(calendario)
    try:
        yield calendario
    finally:
        _calendario.reset(token)
