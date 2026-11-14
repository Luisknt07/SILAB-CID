"""Pruebas optativas de la separación real: dos bases PostgreSQL efímeras.

Usar solo con variables de un servidor de QA; Django crea test_<NAME> para
ambos alias. No MIRROR, no SQLite, ni reutilización de la base operativa.
"""
import os

from django.core.exceptions import ImproperlyConfigured

if os.environ.get('PYTHON_DOTENV_DISABLED') != '1':
    raise ImproperlyConfigured('Las pruebas multibase requieren PYTHON_DOTENV_DISABLED=1.')

from .settings import *  # noqa: F403

if not CENTROS_DB_ENABLED or 'centros' not in DATABASES:  # noqa: F405
    raise ImproperlyConfigured('Las pruebas multibase requieren CENTROS_DB_ENABLED=true y el destino configurado.')
for _alias in ('default', 'centros'):
    _base = DATABASES[_alias]  # noqa: F405
    if not str(_base['NAME']).startswith('citt_qa_'):
        raise ImproperlyConfigured('Las pruebas multibase requieren nombres con prefijo citt_qa_.')
    _base['TEST'] = {'NAME': 'test_' + _base['NAME']}
    _base['CONN_MAX_AGE'] = 0
    _base['OPTIONS'] = {'connect_timeout': 5, 'options': '-c statement_timeout=30000 -c lock_timeout=5000'}
# Este perfil no cambia los hashers del producto.
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
ALLOW_DEMO_DATA_COMMANDS = False

# Compatibilidad de la regresión histórica de Centros: sus TestCase declaraban
# implícitamente una sola base. Solo este perfil de QA concede a esas clases
# ambas bases temporales; SimpleTestCase sigue prohibiendo SQL. La configuración
# común/producción y el runner histórico no alteran este contrato de pruebas.
from django.test import TestCase, TransactionTestCase  # noqa: E402

TestCase.databases = TransactionTestCase.databases = frozenset({'default', 'centros'})
