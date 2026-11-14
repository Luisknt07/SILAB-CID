"""Adaptador unico de tipologias para catalogo, detalle, modelos y admin.

Sin proveedor institucional se usan las cuatro tipologias implementadas. El
proveedor solo puede ser el registrado; un fallo de lectura cae a las bases
y queda en el registro, nunca oculta una tipologia implementada.
"""

import logging

from django.conf import settings
from django.utils import translation
from django.utils.module_loading import import_string

from apps.core.tipologias import TIPOLOGIAS_BASE, catalogo_tipologias

logger = logging.getLogger(__name__)
PROVEEDOR_REGISTRADO = 'apps.configuracion_institucional.tipologias.selectors.tipologias_publicadas'


def tipologias_de_despliegue():
    return catalogo_tipologias(TIPOLOGIAS_BASE)


def proveedor_tipologias():
    ruta = getattr(settings, 'UNIT_TYPOLOGY_PROVIDER', '')
    if not ruta:
        return None
    if ruta != PROVEEDOR_REGISTRADO:
        raise ValueError('El proveedor de tipologias no esta registrado.')
    return import_string(ruta)


def tipologias_actuales():
    base = tipologias_de_despliegue()
    proveedor = proveedor_tipologias()
    return proveedor(base) if proveedor else base


def tipologias_publicas():
    return tuple(tipologia for tipologia in tipologias_actuales() if tipologia.activa)


def tipologia(codigo):
    if not codigo:
        return None
    return next((t for t in tipologias_actuales() if t.codigo == codigo), None)


def tipologia_activa(codigo):
    actual = tipologia(codigo)
    return bool(actual and actual.activa)


def idioma_actual():
    return translation.get_language() or 'es'


def nombre_tipologia(codigo, *, plural=False):
    actual = tipologia(codigo)
    if actual is None:
        return codigo or ''
    return actual.etiqueta(idioma_actual(), plural=plural)


def opciones_tipologias(*, incluir=None):
    """Choices para formularios: activas mas la que ya tenga el registro."""
    idioma = idioma_actual()
    return tuple(
        (t.codigo, t.etiqueta(idioma))
        for t in tipologias_actuales()
        if t.activa or t.codigo == incluir
    )


def codigos_por_base(base):
    """Codigos de tipologia que reutilizan una implementacion base.

    Una tipologia institucional nueva no trae reglas propias: declara la base
    cuyo comportamiento reutiliza. Por eso la seccion de una vertical reune
    todas las tipologias de su base, no solo la que trae el sistema.
    """
    return tuple(t.codigo for t in tipologias_actuales() if t.base == base)

