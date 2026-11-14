"""Provisiona roles separados. Ejecutar exclusivamente con el rol de migraciones."""
import os
import re

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections, transaction


class Command(BaseCommand):
    help = 'Crea/actualiza el rol web y el de respaldo y concede privilegios sobre el esquema migrado.'

    def add_arguments(self, parser):
        parser.add_argument('--database', choices=('default', 'centros'), default='default')
        parser.add_argument('--solo-permisos', action='store_true',
                            help='Concede permisos a roles ya aprovisionados por un administrador; no crea roles ni cambia claves.')

    def handle(self, *args, **options):
        alias = options['database']
        if alias not in connections:
            raise CommandError('El alias de base solicitado no está configurado.')
        connection = connections[alias]
        if connection.vendor != 'postgresql':
            raise CommandError('El aprovisionamiento requiere PostgreSQL.')
        prefijo = 'CENTROS_DB_' if alias == 'centros' else 'DB_'
        runtime = os.environ.get(prefijo + 'RUNTIME_USER', '')
        password = os.environ.get(prefijo + 'RUNTIME_PASSWORD', '')
        backup = os.environ.get(prefijo + 'BACKUP_USER', '')
        backup_password = os.environ.get(prefijo + 'BACKUP_PASSWORD', '')
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_user, current_database()')
            owner, database = cursor.fetchone()
        if (not all(re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', name) for name in (runtime, backup))
                or len({runtime, backup, owner}) != 3 or min(len(password), len(backup_password)) < 20
                or password == backup_password
                or connection.settings_dict.get('PASSWORD') in {password, backup_password}):
            raise CommandError('Configure nombres y contraseñas distintos entre roles, con al menos 20 caracteres por contraseña.')
        quote = connection.ops.quote_name
        with transaction.atomic(using=alias), connection.cursor() as cursor:
            # Contraseñas como valores, nunca interpoladas ni impresas. format genera
            # el DDL porque PostgreSQL no admite parámetros en CREATE/ALTER ROLE.
            definiciones = (
                (runtime, password, 'NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOINHERIT'),
                (backup, backup_password, 'NOSUPERUSER BYPASSRLS NOCREATEROLE CREATEDB NOINHERIT'),
            )
            if options['solo_permisos']:
                cursor.execute('SELECT rolname,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolinherit,rolcanlogin '
                               'FROM pg_roles WHERE rolname=ANY(%s)', [[runtime, backup]])
                roles = {row[0]: row[1:] for row in cursor.fetchall()}
                if (roles.get(runtime) != (False, False, False, False, False, True)
                        or roles.get(backup) != (False, True, False, True, False, True)):
                    raise CommandError('Un administrador debe aprovisionar primero los roles web y respaldo con sus privilegios previstos.')
            else:
                for name, secret, privileges in definiciones:
                    cursor.execute('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)', [name])
                    verb = 'ALTER' if cursor.fetchone()[0] else 'CREATE'
                    cursor.execute('SELECT format(%s, %s, %s)',
                                   [verb + ' ROLE %I LOGIN ' + privileges + ' PASSWORD %L', name, secret])
                    cursor.execute(cursor.fetchone()[0])
            cursor.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            cursor.execute(f'REVOKE ALL ON SCHEMA public FROM {quote(runtime)}')
            cursor.execute(f'GRANT USAGE ON SCHEMA public TO {quote(runtime)}, {quote(backup)}')
            cursor.execute(f'GRANT CONNECT ON DATABASE {quote(database)} TO {quote(runtime)}, {quote(backup)}')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quote(runtime)}')
            cursor.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {quote(runtime)}')
            cursor.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO {quote(backup)}')
            cursor.execute(f'GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO {quote(backup)}')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quote(runtime)}')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {quote(runtime)}')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {quote(backup)}')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO {quote(backup)}')
            if alias == 'default' and settings.CENTROS_DB_ENABLED:
                # El origen queda conservado para auditoría/recuperación, pero
                # deja de ser accesible al rol web tras el corte. Los roles de
                # mantenimiento/respaldo mantienen sus permisos.
                cursor.execute("SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                               "WHERE n.nspname='public' AND left(c.relname, 11)='centros_id_' "
                               "AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')")
                for tabla, tipo in cursor.fetchall():
                    objeto = 'SEQUENCE' if tipo == 'S' else 'TABLE'
                    cursor.execute(f'REVOKE ALL ON {objeto} public.{quote(tabla)} FROM {quote(runtime)}')
        mensaje = ('Permisos web y respaldo actualizados; roles y claves conservados.' if options['solo_permisos']
                   else 'Roles web y respaldo configurados; credenciales omitidas de la salida.')
        self.stdout.write(self.style.SUCCESS(mensaje))
