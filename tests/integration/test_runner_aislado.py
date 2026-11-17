"""El runner rechaza la configuración operativa y aísla los archivos de cada proceso de pruebas."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.test import SimpleTestCase, override_settings

from config.testing import SuiteParalelaAislada, aislar_worker, iniciar_worker, validar_bases_pruebas


class ProcesosDePruebasAisladosTests(SimpleTestCase):
    """Cada proceso paralelo escribe sus archivos en su propia carpeta, en Windows y en Linux.

    Django solo ejecuta el aislamiento cuando crea los procesos con spawn. Con fork (Linux y la
    integración continua) los procesos compartían la carpeta y una prueba veía los archivos de otra.
    """

    def test_la_suite_paralela_usa_el_iniciador_que_tambien_aisla_con_fork(self):
        self.assertIs(SuiteParalelaAislada.init_worker, iniciar_worker)
        self.assertIs(SuiteParalelaAislada.process_setup, aislar_worker)

    def test_con_fork_el_proceso_recibe_su_carpeta_y_el_almacen_la_usa(self):
        with TemporaryDirectory(prefix='runner-aislado-') as comun:
            with override_settings(MEDIA_ROOT=comun, STORAGES=settings.STORAGES,
                                   PASSWORD_HASHERS=settings.PASSWORD_HASHERS):
                # El almacén ya resolvió la carpeta común, como en un proceso que la hereda del padre.
                self.assertEqual(Path(default_storage.location), Path(comun).resolve())
                with patch('config.testing._init_worker') as de_django, patch(
                        'config.testing.multiprocessing.get_start_method', return_value='fork'):
                    iniciar_worker(None, process_setup=aislar_worker,
                                   process_setup_args=(comun, settings.PASSWORD_HASHERS))
                de_django.assert_called_once()
                propia = Path(comun) / str(os.getpid())
                self.assertEqual(Path(settings.MEDIA_ROOT), propia)
                self.assertTrue(propia.is_dir())
                self.assertEqual(Path(default_storage.location), propia.resolve())

    def test_con_spawn_no_repite_el_aislamiento_que_ya_hace_django(self):
        aislamiento = Mock()
        with patch('config.testing._init_worker') as de_django, patch(
                'config.testing.multiprocessing.get_start_method', return_value='spawn'):
            iniciar_worker(None, process_setup=aislamiento, process_setup_args=('carpeta', ()))
        de_django.assert_called_once()
        aislamiento.assert_not_called()


class BasesPruebasAisladasTests(SimpleTestCase):
    def validar(self, bases, *, dotenv='1', aliases=('default',)):
        with patch('config.testing.settings', SimpleNamespace(DATABASES=bases)), patch.dict(
            'os.environ', {'PYTHON_DOTENV_DISABLED': dotenv},
        ):
            validar_bases_pruebas(aliases)

    def test_impide_cargar_dotenv_operativo_aunque_la_base_se_llame_qa(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validar({'default': {'NAME': 'citt_qa_pruebas', 'HOST': '127.0.0.1'}}, dotenv='0')

    def test_impide_crear_test_en_bases_ajenas_a_qa(self):
        for nombre in ('institucional', 'postgres', 'test_institucional', ''):
            with self.subTest(nombre=nombre), self.assertRaises(ImproperlyConfigured):
                self.validar({'default': {'NAME': nombre, 'HOST': '127.0.0.1'}})

    def test_impide_usar_un_servidor_remoto_o_un_alias_ausente(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validar({'default': {'NAME': 'citt_qa_pruebas', 'HOST': 'db.institucion.example'}})
        with self.assertRaises(ImproperlyConfigured):
            self.validar({}, aliases=('centros',))

    def test_admite_qa_y_ci_en_loopback_y_revisa_todos_los_alias(self):
        self.validar({'default': {'NAME': 'citt_ci', 'HOST': '127.0.0.1'},
                      'centros': {'NAME': 'citt_qa_centros', 'HOST': 'localhost'}},
                     aliases=('default', 'centros'))
        with self.assertRaises(ImproperlyConfigured):
            self.validar({'default': {'NAME': 'citt_qa_pruebas', 'HOST': '127.0.0.1'},
                          'centros': {'NAME': 'institucional', 'HOST': '127.0.0.1'}},
                         aliases=('default', 'centros'))

    def test_las_pruebas_sin_sql_no_necesitan_configuracion_de_base(self):
        self.validar({}, dotenv='0', aliases=())

    def test_aliases_none_revisa_las_bases_implicitas(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validar({'default': {'NAME': 'institucional', 'HOST': '127.0.0.1'}}, aliases=None)
