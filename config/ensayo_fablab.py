"""Límites del perfil local de ensayo, sin conexiones ni cambios de entorno."""
from copy import deepcopy

from django.core.exceptions import ImproperlyConfigured


BASES_ENSAYO_FABLAB = {'default': 'test_citt_ideal_fablab_operativa_20261017',
                      'centros': 'test_citt_ideal_fablab_operativa_20261017_centros'}
HOSTS_LOCALES_ENSAYO = frozenset({'127.0.0.1', 'localhost', '::1'})


def bases_de_ensayo_fablab(bases, debug):
    if not debug:
        raise ImproperlyConfigured('El ensayo de FabLab requiere DEBUG y un servidor local.')
    configuracion = deepcopy(bases['default'])
    if configuracion.get('HOST') not in HOSTS_LOCALES_ENSAYO:
        raise ImproperlyConfigured('El ensayo de FabLab sólo admite PostgreSQL local.')
    configuracion['NAME'] = BASES_ENSAYO_FABLAB['default']
    configuracion['CONN_MAX_AGE'] = 0
    configuracion.pop('TEST', None)
    centros = deepcopy(configuracion)
    centros['NAME'] = BASES_ENSAYO_FABLAB['centros']
    return {'default': configuracion, 'centros': centros}
