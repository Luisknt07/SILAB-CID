"""Aprovisionamiento real en la base aislada de pruebas, sin tocar roles existentes."""
import os
import uuid
from io import StringIO
from unittest import SkipTest
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TransactionTestCase


class RolesProduccionTests(TransactionTestCase):
    def test_roles_separados_privilegios_minimos_y_contrasenas_parametrizadas(self):
        if connection.vendor != 'postgresql':
            raise SkipTest('Requiere PostgreSQL.')
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
            if not cursor.fetchone()[0]:
                raise SkipTest('Crear el rol de respaldo BYPASSRLS requiere un administrador de prueba.')
        suffix = uuid.uuid4().hex[:12]
        runtime, backup = 'slcid_web_' + suffix, 'slcid_backup_' + suffix
        secret = "clave'" + uuid.uuid4().hex
        env = {'DB_RUNTIME_USER': runtime, 'DB_RUNTIME_PASSWORD': secret,
               'DB_BACKUP_USER': backup, 'DB_BACKUP_PASSWORD': "respaldo'" + uuid.uuid4().hex}
        output = StringIO()
        try:
            with patch.dict(os.environ, env):
                call_command('preparar_roles_bd', stdout=output)
                # La segunda ejecución actualiza los roles sin duplicarlos.
                call_command('preparar_roles_bd', stdout=output)
            self.assertNotIn(secret, output.getvalue())
            with connection.cursor() as cursor:
                cursor.execute('SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb, rolinherit FROM pg_roles WHERE rolname=ANY(%s)', [[runtime, backup]])
                roles = {row[0]: row[1:] for row in cursor.fetchall()}
                self.assertEqual(roles[runtime], (False, False, False, False, False))
                self.assertEqual(roles[backup], (False, True, False, True, False))
                cursor.execute('SELECT has_table_privilege(%s, %s, %s), has_schema_privilege(%s, %s, %s)',
                               [runtime, 'webcitt_unidad', 'INSERT', runtime, 'public', 'CREATE'])
                self.assertEqual(cursor.fetchone(), (True, False))
                cursor.execute('SELECT has_table_privilege(%s, %s, %s)', [backup, 'webcitt_unidad', 'INSERT'])
                self.assertFalse(cursor.fetchone()[0])
        finally:
            with connection.cursor() as cursor:
                for role in (runtime, backup):
                    quoted = connection.ops.quote_name(role)
                    cursor.execute('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)', [role])
                    if cursor.fetchone()[0]:
                        cursor.execute(f'DROP OWNED BY {quoted}')
                        cursor.execute(f'DROP ROLE {quoted}')

    def test_rechaza_nombres_sql_y_claves_debiles_antes_de_crear_roles(self):
        for name, password in (("web; DROP ROLE otro", 'x' * 32), ('web_seguro', 'corta'), ('web_seguro', 'x' * 32)):
            with self.subTest(name=name), patch.dict(os.environ, {
                'DB_RUNTIME_USER': name, 'DB_RUNTIME_PASSWORD': password,
                'DB_BACKUP_USER': 'backup_seguro', 'DB_BACKUP_PASSWORD': 'x' * 32,
            }), self.assertRaises(CommandError):
                call_command('preparar_roles_bd', stdout=StringIO())
