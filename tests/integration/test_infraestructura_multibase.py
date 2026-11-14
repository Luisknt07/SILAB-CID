"""Contratos de configuración/routing sin abrir bases reales."""
from io import StringIO
from types import SimpleNamespace
import os
from unittest.mock import MagicMock, patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from django.test import RequestFactory, SimpleTestCase, override_settings

from config.bases_datos import configurar_centros
from config.router_centros import RouterCentros
from apps.core.presentation.salud import listo


class ConfiguracionMultibaseTests(SimpleTestCase):
    def entorno(self, **cambios):
        return {'CENTROS_DB_NAME': 'centros_destino', 'CENTROS_DB_HOST': 'centros.interno',
                'CENTROS_DB_USER': 'centros_web', 'CENTROS_DB_PASSWORD': 'clave-centros-ficticia', **cambios}

    def test_preparar_destino_no_activa_routing_ni_hereda_secretos(self):
        bases = {'default': {'NAME': 'principal', 'PASSWORD': 'otra-clave'}}
        self.assertFalse(configurar_centros(bases, self.entorno(CENTROS_DB_PASSWORD='')))
        self.assertEqual(set(bases), {'default', 'centros'})
        self.assertEqual(bases['centros']['PASSWORD'], '')
        self.assertEqual(bases['centros']['PORT'], '5432')
        self.assertTrue(configurar_centros(bases, self.entorno(CENTROS_DB_ENABLED='true')))

    def test_flag_invalido_destino_ausente_mismo_nombre_y_host_ausente_se_rechazan(self):
        for entorno in ({'CENTROS_DB_ENABLED': 'quizas'}, {'CENTROS_DB_ENABLED': 'true'},
                        self.entorno(CENTROS_DB_NAME='principal'), self.entorno(CENTROS_DB_HOST=''),
                        self.entorno(CENTROS_DB_USER='')):
            with self.subTest(entorno=entorno), self.assertRaises(ImproperlyConfigured):
                configurar_centros({'default': {'NAME': 'principal'}}, entorno)
        bases = {'default': {'NAME': 'principal'}}
        self.assertFalse(configurar_centros(bases, {}))
        self.assertEqual(set(bases), {'default'})

    def objeto(self, app, alias=None):
        return SimpleNamespace(_meta=SimpleNamespace(app_label=app), _state=SimpleNamespace(db=alias))

    def test_router_upgrade_previo_conserva_lecturas_y_escrituras_y_prepara_solo_centros(self):
        router = RouterCentros()
        with override_settings(CENTROS_DB_ENABLED=False):
            for app in ('centros_id', 'auth', 'contenttypes', 'guardian', 'webcitt'):
                modelo = self.objeto(app)
                self.assertEqual(router.db_for_read(modelo), 'default')
                self.assertEqual(router.db_for_write(modelo), 'default')
                self.assertTrue(router.allow_migrate('default', app))
                self.assertEqual(router.allow_migrate('centros', app), app == 'centros_id')

    def test_router_activado_separa_identidades_y_relaciones_sql(self):
        router = RouterCentros()
        with override_settings(CENTROS_DB_ENABLED=True):
            for app in ('centros_id', 'auth', 'contenttypes', 'admin', 'sessions', 'guardian', 'webcitt'):
                self.assertEqual(router.db_for_read(self.objeto(app)), 'centros' if app == 'centros_id' else 'default')
                self.assertEqual(router.db_for_write(self.objeto(app)), router.db_for_read(self.objeto(app)))
                self.assertEqual(router.allow_migrate('default', app), app != 'centros_id')
                self.assertEqual(router.allow_migrate('centros', app), app == 'centros_id')
            self.assertFalse(router.allow_migrate('desconocida', 'centros_id'))
            self.assertTrue(router.allow_relation(self.objeto('centros_id'), self.objeto('centros_id')))
            self.assertFalse(router.allow_relation(self.objeto('auth'), self.objeto('centros_id')))
            self.assertFalse(router.allow_relation(self.objeto('centros_id', 'default'), self.objeto('centros_id', 'centros')))

    def test_readiness_destino_preparado_no_abre_centros_y_activado_exige_ambas(self):
        with patch('apps.core.presentation.salud.connection') as principal, patch('apps.core.presentation.salud.connections') as conexiones:
            principal.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            secundaria = conexiones.__getitem__.return_value
            secundaria.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            with override_settings(CENTROS_DB_ENABLED=False):
                self.assertEqual(listo(RequestFactory().head('/salud/listo/')).status_code, 204)
                conexiones.__getitem__.assert_not_called()
            with override_settings(CENTROS_DB_ENABLED=True):
                self.assertEqual(listo(RequestFactory().head('/salud/listo/')).status_code, 204)
                secundaria.cursor.return_value.__enter__.return_value.execute.assert_called_once_with('SELECT 1')
                secundaria.cursor.side_effect = OperationalError('dato-privado')
                respuesta = listo(RequestFactory().get('/salud/listo/'))
                self.assertEqual(respuesta.status_code, 503)
                self.assertEqual(respuesta.content, b'')
                self.assertIn('no-store', respuesta['Cache-Control'])


class SeguridadAliasesTests(SimpleTestCase):
    def conexion(self, tablas=()):
        conexion = MagicMock(vendor='postgresql')
        cursor = conexion.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(False,) * 4, (False,)]
        cursor.fetchall.return_value = [(tabla,) for tabla in tablas]
        return conexion

    def test_centros_verifica_esquema_y_no_exige_rls_legacy_ni_imprime_secretos(self):
        conexion = self.conexion(('django_migrations', 'centros_id_centroid', 'centros_id_cuentacentro'))
        salida = StringIO()
        with patch('apps.core.management.commands.verificar_seguridad_bd.connections', {'centros': conexion}):
            call_command('verificar_seguridad_bd', database='centros', stdout=salida)
        self.assertIn('no RLS central', salida.getvalue())
        sql = ' '.join(llamada.args[0] for llamada in conexion.cursor.return_value.__enter__.return_value.execute.call_args_list)
        self.assertNotIn('slcid_personal', sql)

    def test_centros_rechaza_esquema_ajeno_o_ausente_y_superusuario(self):
        for tablas in ((), ('centros_id_centroid',), ('centros_id_centroid', 'centros_id_cuentacentro', 'auth_user')):
            with self.subTest(tablas=tablas), patch('apps.core.management.commands.verificar_seguridad_bd.connections',
                                                  {'centros': self.conexion(tablas)}), self.assertRaises(CommandError):
                call_command('verificar_seguridad_bd', database='centros', stdout=StringIO())
        conexion = self.conexion()
        conexion.cursor.return_value.__enter__.return_value.fetchone.side_effect = [(True, False, False, False)]
        with patch('apps.core.management.commands.verificar_seguridad_bd.connections', {'centros': conexion}), self.assertRaises(CommandError):
            call_command('verificar_seguridad_bd', database='centros', stdout=StringIO())

    def test_all_ignora_destino_preparado_y_verifica_ambos_activados(self):
        from apps.core.management.commands.verificar_seguridad_bd import Command

        comando = Command()
        with patch('apps.core.management.commands.verificar_seguridad_bd.connections', {'default': 'principal', 'centros': 'secundaria'}), patch.object(comando, 'verificar') as verificar:
            with override_settings(CENTROS_DB_ENABLED=False):
                comando.handle(todas=True, database='default')
                verificar.assert_called_once_with('principal', 'default')
            verificar.reset_mock()
            with override_settings(CENTROS_DB_ENABLED=True):
                comando.handle(todas=True, database='default')
                self.assertEqual([c.args for c in verificar.call_args_list], [('principal', 'default'), ('secundaria', 'centros')])

    def test_provisionado_centros_usa_credenciales_y_transaccion_del_alias(self):
        conexion = MagicMock(vendor='postgresql')
        conexion.settings_dict = {'PASSWORD': 'clave-propietario-ficticia-distinta'}
        conexion.ops.quote_name.side_effect = lambda nombre: '"' + nombre + '"'
        cursor = conexion.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [('propietario_centros', 'destino_centros'),
                                      (False,), ('DDL runtime simulado',), (False,), ('DDL backup simulado',)]
        entorno = {'CENTROS_DB_RUNTIME_USER': 'centros_web', 'CENTROS_DB_RUNTIME_PASSWORD': 'clave-ficticia-web-centros-123',
                   'CENTROS_DB_BACKUP_USER': 'centros_backup', 'CENTROS_DB_BACKUP_PASSWORD': 'clave-ficticia-backup-centros-456'}
        salida = StringIO()
        with patch.dict(os.environ, entorno, clear=True), patch('apps.core.management.commands.preparar_roles_bd.connections',
                                                               {'centros': conexion}), patch(
                'apps.core.management.commands.preparar_roles_bd.transaction.atomic') as atomic:
            call_command('preparar_roles_bd', database='centros', stdout=salida)
        atomic.assert_called_once_with(using='centros')
        self.assertNotIn(entorno['CENTROS_DB_RUNTIME_PASSWORD'], salida.getvalue())
        self.assertNotIn(entorno['CENTROS_DB_BACKUP_PASSWORD'], salida.getvalue())
        self.assertTrue(any('"destino_centros"' in llamada.args[0] for llamada in cursor.execute.call_args_list))

    def test_deploy_exige_credenciales_y_transporte_centros_independientes(self):
        from apps.core.checks_despliegue import hardened_production_configuration

        principal = {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'principal', 'USER': 'web_principal',
                     'PASSWORD': 'clave-principal-ficticia-12345', 'HOST': 'privado', 'OPTIONS': {}}
        centros = {**principal, 'NAME': 'centros', 'USER': 'web_centros', 'PASSWORD': 'clave-centros-ficticia-67890'}
        with override_settings(REQUIRE_STRONG_DEPLOYMENT=True, DB_NETWORK_ISOLATED=True,
                               CENTROS_DB_NETWORK_ISOLATED=True):
            with patch('apps.core.checks_despliegue.settings.DATABASES', {'default': principal, 'centros': centros}):
                self.assertNotIn('webcitt.E011', [error.id for error in hardened_production_configuration(None)])
            for cambio in ({'USER': principal['USER']}, {'PASSWORD': principal['PASSWORD']},
                           {'PASSWORD': 'corta'}, {'HOST': ''}, {'ENGINE': 'django.db.backends.sqlite3'}):
                with self.subTest(cambio=cambio), patch('apps.core.checks_despliegue.settings.DATABASES',
                                                       {'default': principal, 'centros': {**centros, **cambio}}):
                    self.assertIn('webcitt.E011', [error.id for error in hardened_production_configuration(None)])
            with override_settings(CENTROS_DB_NETWORK_ISOLATED=False), patch('apps.core.checks_despliegue.settings.DATABASES',
                                                                             {'default': principal, 'centros': centros}):
                self.assertIn('webcitt.E011', [error.id for error in hardened_production_configuration(None)])

    def test_solo_permisos_no_administra_roles_ni_modifica_claves(self):
        conexion = MagicMock(vendor='postgresql')
        conexion.settings_dict = {'PASSWORD': 'propietario-ficticio-distinto'}
        conexion.ops.quote_name.side_effect = lambda nombre: '"' + nombre + '"'
        cursor = conexion.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ('propietario_centros', 'destino_centros')
        cursor.fetchall.return_value = [('web_centros', False, False, False, False, False, True),
                                       ('backup_centros', False, True, False, True, False, True)]
        entorno = {'CENTROS_DB_RUNTIME_USER': 'web_centros', 'CENTROS_DB_RUNTIME_PASSWORD': 'web-ficticio-123456789012345',
                   'CENTROS_DB_BACKUP_USER': 'backup_centros', 'CENTROS_DB_BACKUP_PASSWORD': 'backup-ficticio-123456789012345'}
        with patch.dict(os.environ, entorno, clear=True), patch(
                'apps.core.management.commands.preparar_roles_bd.connections', {'centros': conexion}), patch(
                'apps.core.management.commands.preparar_roles_bd.transaction.atomic'):
            call_command('preparar_roles_bd', database='centros', solo_permisos=True, stdout=StringIO())
        sql = ' '.join(llamada.args[0] for llamada in cursor.execute.call_args_list)
        self.assertIn('GRANT', sql)
        for prohibido in ('CREATE ROLE', 'ALTER ROLE', 'PASSWORD', 'format('):
            self.assertNotIn(prohibido, sql)

    def test_solo_permisos_rechaza_roles_ausentes_o_con_privilegios_inseguros(self):
        entorno = {'CENTROS_DB_RUNTIME_USER': 'web_centros', 'CENTROS_DB_RUNTIME_PASSWORD': 'web-ficticio-123456789012345',
                   'CENTROS_DB_BACKUP_USER': 'backup_centros', 'CENTROS_DB_BACKUP_PASSWORD': 'backup-ficticio-123456789012345'}
        for roles in ([], [('web_centros', True, False, False, False, False, True)],
                      [('web_centros', False, True, False, False, False, True)]):
            conexion = MagicMock(vendor='postgresql')
            conexion.settings_dict = {'PASSWORD': 'propietario-ficticio-distinto'}
            cursor = conexion.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = ('propietario_centros', 'destino_centros')
            cursor.fetchall.return_value = roles
            with self.subTest(roles=roles), patch.dict(os.environ, entorno, clear=True), patch(
                    'apps.core.management.commands.preparar_roles_bd.connections', {'centros': conexion}), patch(
                    'apps.core.management.commands.preparar_roles_bd.transaction.atomic'), self.assertRaises(CommandError):
                call_command('preparar_roles_bd', database='centros', solo_permisos=True, stdout=StringIO())
            self.assertFalse(any(llamada.args[0].startswith('GRANT') for llamada in cursor.execute.call_args_list))

    def test_corte_revoca_tablas_y_secuencias_origen_solo_al_rol_web(self):
        conexion = MagicMock(vendor='postgresql')
        conexion.settings_dict = {'PASSWORD': 'clave-propietario-ficticia-distinta'}
        conexion.ops.quote_name.side_effect = lambda nombre: '"' + nombre + '"'
        cursor = conexion.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [('propietario', 'principal'), (False,), ('DDL web',), (False,), ('DDL backup',)]
        cursor.fetchall.return_value = [('centros_id_centroid', 'r'), ('centros_id_centroid_id_seq', 'S')]
        entorno = {'DB_RUNTIME_USER': 'web_principal', 'DB_RUNTIME_PASSWORD': 'clave-ficticia-web-principal-123',
                   'DB_BACKUP_USER': 'backup_principal', 'DB_BACKUP_PASSWORD': 'clave-ficticia-backup-principal-456'}
        with override_settings(CENTROS_DB_ENABLED=True), patch.dict(os.environ, entorno, clear=True), patch(
                'apps.core.management.commands.preparar_roles_bd.connections', {'default': conexion}), patch(
                'apps.core.management.commands.preparar_roles_bd.transaction.atomic'):
            call_command('preparar_roles_bd', stdout=StringIO())
        sentencias = [llamada.args[0] for llamada in cursor.execute.call_args_list]
        self.assertIn('REVOKE ALL ON TABLE public."centros_id_centroid" FROM "web_principal"', sentencias)
        self.assertIn('REVOKE ALL ON SEQUENCE public."centros_id_centroid_id_seq" FROM "web_principal"', sentencias)
        self.assertFalse(any(sentencia.startswith('REVOKE') and 'backup_principal' in sentencia for sentencia in sentencias))

    def test_verificador_rechaza_acceso_residual_al_origen_y_acepta_privilegios_revocados(self):
        from apps.core.management.commands.verificar_seguridad_bd import TABLES

        for residual in (True, False):
            conexion = self.conexion()
            cursor = conexion.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [(False,) * 4, (False,), (residual,)]
            cursor.fetchall.return_value = [(tabla, True, True, True) for tabla in TABLES]
            with self.subTest(residual=residual), override_settings(CENTROS_DB_ENABLED=True), patch(
                    'apps.core.management.commands.verificar_seguridad_bd.connections', {'default': conexion}):
                if residual:
                    with self.assertRaisesMessage(CommandError, 'Tras el corte'):
                        call_command('verificar_seguridad_bd', stdout=StringIO())
                else:
                    call_command('verificar_seguridad_bd', stdout=StringIO())
