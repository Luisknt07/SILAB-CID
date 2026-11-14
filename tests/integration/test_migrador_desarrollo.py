"""Migrador local: dobles exclusivamente, sin SQL ni archivos de entorno."""
from contextlib import redirect_stderr
import copy
import importlib.util
from io import StringIO
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]


class MigradorDesarrolloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('migrador_desarrollo_qa', ROOT / 'scripts/migrar_desarrollo.py')
        cls.modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.modulo)

    def configuracion(self, activo=False):
        bases = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'qa_principal',
                             'USER': 'runtime_principal', 'PASSWORD': 'clave-runtime-principal'}}
        if activo:
            bases['centros'] = {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'qa_centros',
                                'USER': 'runtime_centros', 'PASSWORD': 'clave-runtime-centros'}
        return SimpleNamespace(SETTINGS_MODULE='config.settings', DEBUG=True,
                               CENTROS_DB_ENABLED=activo, DATABASES=bases)

    def propietarios(self):
        return {'DB_MIGRATION_USER': 'owner_principal', 'DB_MIGRATION_PASSWORD': 'clave-owner-principal',
                'CENTROS_DB_MIGRATION_USER': 'owner_centros', 'CENTROS_DB_MIGRATION_PASSWORD': 'clave-owner-centros'}

    def test_legacy_sin_propietario_explicito_conserva_credenciales_y_solo_actualiza_default(self):
        configuracion = self.configuracion()
        preparar, comando = Mock(), Mock()
        self.modulo.ejecutar_migraciones(configuracion, {}, preparar, comando)
        preparar.assert_called_once_with()
        comando.assert_called_once_with('migrate', database='default', interactive=False)
        self.assertEqual(configuracion.DATABASES['default']['USER'], 'runtime_principal')

    def test_dual_selecciona_ambos_propietarios_antes_de_setup_y_respeta_orden(self):
        configuracion = self.configuracion(activo=True)
        eventos = []

        def preparar():
            self.assertEqual(configuracion.DATABASES['default']['USER'], 'owner_principal')
            self.assertEqual(configuracion.DATABASES['centros']['USER'], 'owner_centros')
            eventos.append('setup')

        def comando(nombre, **opciones):
            self.assertEqual(nombre, 'migrate')
            self.assertFalse(opciones['interactive'])
            eventos.append(opciones['database'])

        entorno = self.propietarios()
        original = dict(entorno)
        self.modulo.ejecutar_migraciones(configuracion, entorno, preparar, comando)
        self.assertEqual(eventos, ['setup', 'default', 'centros'])
        self.assertEqual(entorno, original)

    def test_flag_apagado_ignora_destino_preparado_y_no_exige_su_owner(self):
        configuracion = self.configuracion(activo=True)
        configuracion.CENTROS_DB_ENABLED = False
        comando = Mock()
        self.modulo.ejecutar_migraciones(configuracion, {}, Mock(), comando)
        comando.assert_called_once_with('migrate', database='default', interactive=False)
        self.assertEqual(configuracion.DATABASES['centros']['USER'], 'runtime_centros')

    def test_configuracion_invalida_falla_antes_de_setup_migracion_o_mutacion_de_credenciales(self):
        for caso in ('prod', 'debug', 'par_default_incompleto', 'par_centros_ausente',
                     'par_centros_incompleto', 'alias_ausente', 'mismo_nombre', 'engine'):
            configuracion = self.configuracion(activo=True)
            entorno = self.propietarios()
            if caso == 'prod':
                configuracion.SETTINGS_MODULE = 'config.settings_production'
            elif caso == 'debug':
                configuracion.DEBUG = False
            elif caso == 'par_default_incompleto':
                entorno.pop('DB_MIGRATION_PASSWORD')
            elif caso == 'par_centros_ausente':
                entorno.pop('CENTROS_DB_MIGRATION_USER')
                entorno.pop('CENTROS_DB_MIGRATION_PASSWORD')
            elif caso == 'par_centros_incompleto':
                entorno.pop('CENTROS_DB_MIGRATION_PASSWORD')
            elif caso == 'alias_ausente':
                configuracion.DATABASES.pop('centros')
            elif caso == 'mismo_nombre':
                configuracion.DATABASES['centros']['NAME'] = 'qa_principal'
            else:
                configuracion.DATABASES['centros']['ENGINE'] = 'django.db.backends.sqlite3'
            anteriores = copy.deepcopy(configuracion.DATABASES)
            preparar, comando = Mock(), Mock()
            with self.subTest(caso=caso), self.assertRaises(self.modulo.ConfiguracionMigracionError):
                self.modulo.ejecutar_migraciones(configuracion, entorno, preparar, comando)
            preparar.assert_not_called()
            comando.assert_not_called()
            self.assertEqual(configuracion.DATABASES, anteriores)

    def test_error_default_detiene_centros_sin_afirmar_rollback_conjunto(self):
        comando = Mock(side_effect=RuntimeError('clave-ficticia-no-publicar'))
        with self.assertRaises(RuntimeError):
            self.modulo.ejecutar_migraciones(self.configuracion(activo=True), self.propietarios(), Mock(), comando)
        comando.assert_called_once_with('migrate', database='default', interactive=False)

    def test_main_rechaza_produccion_antes_de_cargar_settings_o_migrar(self):
        salida = StringIO()
        with patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'config.settings_production'}), patch.object(
                self.modulo, 'ejecutar_migraciones') as ejecutar, redirect_stderr(salida):
            self.assertEqual(self.modulo.main(), 2)
        ejecutar.assert_not_called()
        self.assertIn('procedimiento separado', salida.getvalue())

    def test_main_no_imprime_excepciones_con_secretos(self):
        salida = StringIO()
        with patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'config.settings'}), patch.object(
                self.modulo, 'ejecutar_migraciones', side_effect=RuntimeError('contraseña-no-publicable')), redirect_stderr(salida):
            self.assertEqual(self.modulo.main(), 1)
        self.assertNotIn('contraseña-no-publicable', salida.getvalue())
        self.assertIn('pueden haberse aplicado', salida.getvalue())

    def test_arranque_windows_invoca_helper_y_no_migra_solo_default(self):
        contenido = (ROOT / 'scripts/iniciar_desarrollo.ps1').read_text(encoding='utf8')
        self.assertIn('& $pythonPath scripts/migrar_desarrollo.py', contenido)
        self.assertNotIn('& $pythonPath manage.py migrate --noinput', contenido)
