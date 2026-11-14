"""Proyeccion academica por solicitud/tarea y ambito explicito de auditoria."""
from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.functional import SimpleLazyObject

_catalogo_presentado = ContextVar('catalogo_presentado', default=None)


def catalogo_en_contexto():
    return _catalogo_presentado.get()


@contextmanager
def con_catalogo_institucional(*, catalogo=None, database='default', estricto=False, diferido=False):
    from .catalogos import catalogo_de_despliegue

    actual = catalogo_en_contexto()
    if catalogo is None and actual is not None and not estricto:
        yield actual
        return
    if catalogo is None:
        def resolver():
            base = catalogo_de_despliegue()
            proveedor = getattr(settings, 'ACADEMIC_CATALOG_PROVIDER', '')
            return import_string(proveedor)(base, database=database, estricto=estricto) if proveedor else base
        catalogo = SimpleLazyObject(resolver) if diferido and not estricto else resolver()
    token = _catalogo_presentado.set(catalogo)
    try:
        yield catalogo
    finally:
        _catalogo_presentado.reset(token)
