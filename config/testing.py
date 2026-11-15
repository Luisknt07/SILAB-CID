"""Pruebas con base y archivos aislados, también en procesos paralelos."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.test.runner import DiscoverRunner, ParallelTestSuite


def validar_bases_pruebas(aliases):
    """Impide crear test_* en un servidor operativo por cargar su .env."""
    if aliases is None:
        aliases = settings.DATABASES
    if not aliases:
        return
    if os.environ.get('PYTHON_DOTENV_DISABLED') != '1':
        raise ImproperlyConfigured('Las pruebas con SQL requieren PYTHON_DOTENV_DISABLED=1 y bases QA explícitas.')
    for alias in aliases:
        base = settings.DATABASES.get(alias)
        if not base:
            raise ImproperlyConfigured(f'El alias de pruebas {alias} no está configurado.')
        nombre = str(base.get('NAME') or '')
        if not (nombre.startswith('citt_qa_') or nombre == 'citt_ci'):
            raise ImproperlyConfigured(f'El alias {alias} requiere una base citt_qa_* (o citt_ci en CI).')
        if base.get('HOST') not in {'127.0.0.1', 'localhost', '::1'}:
            raise ImproperlyConfigured(f'El alias {alias} debe apuntar al servidor QA en loopback.')


def almacenes_de_pruebas():
    # Un manifiesto de estáticos recopilado en este equipo (var/static) no debe
    # cambiar las direcciones que comprueban las pruebas: se usan sin huella.
    return {**settings.STORAGES,
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}


def aislar_worker(media_root, password_hashers):
    # spawn no hereda override_settings del proceso principal. Cada worker
    # escribe en su carpeta y el contexto del padre las elimina al terminar.
    carpeta = Path(media_root) / str(os.getpid())
    carpeta.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(carpeta)
    settings.PASSWORD_HASHERS = password_hashers
    settings.STORAGES = almacenes_de_pruebas()


class SuiteParalelaAislada(ParallelTestSuite):
    process_setup = aislar_worker


class PruebasAisladas(DiscoverRunner):
    parallel_test_suite = SuiteParalelaAislada

    def setup_databases(self, **kwargs):
        validar_bases_pruebas(kwargs.get('aliases', settings.DATABASES))
        return super().setup_databases(**kwargs)

    def run_tests(self, test_labels, **kwargs):
        with TemporaryDirectory(prefix='slcid-tests-') as media:
            anteriores = self.parallel_test_suite.process_setup_args
            self.parallel_test_suite.process_setup_args = (media, settings.PASSWORD_HASHERS)
            try:
                with override_settings(MEDIA_ROOT=media, STORAGES=almacenes_de_pruebas()):
                    return super().run_tests(test_labels, **kwargs)
            finally:
                self.parallel_test_suite.process_setup_args = anteriores
