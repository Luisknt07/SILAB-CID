"""El proceso web local nunca recibe las claves de administración o respaldo."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.servidor_local_seguro import main


class ServidorLocalSeguroTests(SimpleTestCase):
    def test_conserva_acceso_web_y_excluye_mantenimiento_en_ambos_procesos(self):
        valores = {'DB_USER': 'web_qa', 'DB_PASSWORD': 'web-ficticia', 'CENTROS_DB_USER': 'centros_web_qa'}
        prefijos = ('DB_MIGRATION_', 'DB_BACKUP_', 'DB_RUNTIME_', 'CENTROS_DB_MIGRATION_',
                    'CENTROS_DB_BACKUP_', 'CENTROS_DB_RUNTIME_')
        valores.update({prefijo + 'PASSWORD': 'mantenimiento-ficticio' for prefijo in prefijos})
        with patch('scripts.servidor_local_seguro.dotenv_values', return_value=valores), patch.dict(
                'os.environ', {}, clear=True), patch('scripts.servidor_local_seguro.subprocess.run',
                return_value=SimpleNamespace(returncode=0)) as validar, patch(
                'scripts.servidor_local_seguro.subprocess.call', return_value=0) as servidor:
            self.assertEqual(main(), 0)
        for llamada in (validar.call_args, servidor.call_args):
            entorno = llamada.kwargs['env']
            self.assertEqual(entorno['DB_USER'], 'web_qa')
            self.assertEqual(entorno['DB_PASSWORD'], 'web-ficticia')
            self.assertEqual(entorno['PYTHON_DOTENV_DISABLED'], '1')
            self.assertFalse(any(clave.startswith(prefijos) for clave in entorno))
        self.assertIn('127.0.0.1:8000', servidor.call_args.args[0])

    def test_no_inicia_si_la_verificacion_de_privilegios_falla(self):
        with patch('scripts.servidor_local_seguro.dotenv_values', return_value={}), patch.dict(
                'os.environ', {}, clear=True), patch('scripts.servidor_local_seguro.subprocess.run',
                return_value=SimpleNamespace(returncode=1)), patch(
                'scripts.servidor_local_seguro.subprocess.call') as servidor:
            self.assertEqual(main(), 1)
        servidor.assert_not_called()
