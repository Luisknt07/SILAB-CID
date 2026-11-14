"""Los datos de matrícula se validan sin cargar formularios ni servicios de aplicación."""
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.core.documentos_identidad import cedula_ecuatoriana_valida
from apps.core.models.datos_matricula import normalizar_correo, validar_datos_matricula

ROOT = Path(__file__).resolve().parents[2]


class ValidacionMatriculaPuraTests(SimpleTestCase):
    def test_reglas_inferiores_cargan_con_orm_formularios_y_dominios_bloqueados(self):
        codigo = r"""
import importlib.abc
import importlib.util
import sys
from pathlib import Path
class Bloqueo(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('apps.gestion_unidades', 'django.forms', 'django.db')):
            raise ImportError('Dependencia de capa superior: ' + fullname)
sys.meta_path.insert(0, Bloqueo())
ruta = Path('apps/core/models/datos_matricula.py')
spec = importlib.util.spec_from_file_location('datos_matricula_puros', ruta)
modulo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modulo)
assert modulo.validar_datos_matricula(nombres_completos='María  Pérez', documento='p-1234', correo=' Persona@EXAMPLE.ORG ') == {'nombres_completos':'María Pérez', 'documento':'P-1234', 'correo':'persona@example.org'}
assert not any(n.startswith(('django.db', 'django.forms', 'apps.gestion_unidades')) for n in sys.modules)
"""
        resultado = subprocess.run([sys.executable, '-c', codigo], cwd=ROOT,
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_normalizacion_y_rechazo_de_datos_inseguros_preservan_contrato(self):
        self.assertEqual(normalizar_correo(' Participante@EXAMPLE.ORG '), 'participante@example.org')
        self.assertEqual(validar_datos_matricula(nombres_completos='María  Pérez', documento='p-1234'),
                         {'nombres_completos': 'María Pérez', 'documento': 'P-1234'})
        for nombre in ('=SUM(A1)', '<b>Participante</b>', 'María\u200bPérez', '12345'):
            with self.subTest(nombre=nombre), self.assertRaises(ValidationError) as error:
                validar_datos_matricula(nombres_completos=nombre, documento='P-1234')
            self.assertIn('nombres_completos', error.exception.message_dict)
        with self.assertRaises(ValidationError) as error:
            validar_datos_matricula(nombres_completos='María Pérez', documento='0000000000', correo='invalido')
        self.assertEqual(set(error.exception.message_dict), {'documento', 'correo'})
        self.assertFalse(cedula_ecuatoriana_valida('0000000000'))
