"""El runner rechaza la configuración operativa antes de crear bases de prueba."""
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.testing import validar_bases_pruebas


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
