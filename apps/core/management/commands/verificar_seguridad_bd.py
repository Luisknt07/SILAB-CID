"""Puerta de despliegue: el usuario web no puede saltarse RLS ni administrar roles."""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections

TABLES = ('webcitt_simulacionguardada', 'webcitt_intentoejercicio', 'webcitt_progresoleccion',
          'webcitt_intentoevaluacion', 'webcitt_entregadeber', 'webcitt_pagoinscripcion')


class Command(BaseCommand):
    help = 'Comprueba roles restringidos; RLS central o esquema exclusivo de Centros según alias.'

    def add_arguments(self, parser):
        grupo = parser.add_mutually_exclusive_group()
        grupo.add_argument('--database', choices=('default', 'centros'), default='default')
        grupo.add_argument('--all', action='store_true', dest='todas', help='Comprueba ambas bases cuando Centros está activo.')

    def handle(self, *args, **options):
        aliases = ['default', 'centros'] if options['todas'] and settings.CENTROS_DB_ENABLED else [options['database']]
        for alias in aliases:
            if alias not in connections:
                raise CommandError('El alias de base solicitado no está configurado.')
            self.verificar(connections[alias], alias)

    def verificar(self, connection, alias):
        if connection.vendor != 'postgresql':
            raise CommandError('Producción requiere PostgreSQL.')
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user')
            if any(cursor.fetchone()):
                raise CommandError('DB_USER web debe ser NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB; use otro rol para migraciones y respaldos.')
            cursor.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE') OR "
                           "EXISTS(SELECT 1 FROM pg_roles r WHERE r.rolname <> current_user "
                           "AND pg_has_role(current_user, r.oid, 'MEMBER')) OR "
                           "EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                           "WHERE n.nspname='public' AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)) OR "
                           "EXISTS(SELECT 1 FROM pg_database WHERE datname=current_database() "
                           "AND datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user))")
            if cursor.fetchone()[0]:
                raise CommandError('El rol web no puede ser propietario, crear objetos en public ni pertenecer a otros roles.')
            if alias == 'default':
                if settings.CENTROS_DB_ENABLED:
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                                   "WHERE n.nspname='public' AND left(c.relname, 11)='centros_id_' "
                                   "AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S') AND CASE WHEN c.relkind='S' "
                                   "THEN has_sequence_privilege(current_user, c.oid, 'USAGE,SELECT,UPDATE') "
                                   "ELSE has_table_privilege(current_user, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') END)")
                    if cursor.fetchone()[0]:
                        raise CommandError('Tras el corte el rol web central no puede acceder a las tablas/secuencias Centros conservadas en origen; reaprovisione sus permisos.')
                cursor.execute('SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, '
                               'EXISTS(SELECT 1 FROM pg_policy p WHERE p.polrelid=c.oid AND p.polname=%s) '
                               'FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace '
                               "WHERE n.nspname='public' AND c.relname = ANY(%s)", ['slcid_personal', list(TABLES)])
                found = {row[0]: all(row[1:]) for row in cursor.fetchall()}
                if not all(found.get(table) for table in TABLES):
                    raise CommandError('Faltan políticas RLS personales; aplique las migraciones con el rol de mantenimiento.')
            else:
                cursor.execute("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                               "WHERE n.nspname='public' AND c.relkind IN ('r', 'p')")
                tablas = {row[0] for row in cursor.fetchall()}
                if (not {'centros_id_centroid', 'centros_id_cuentacentro'} <= tablas
                        or any(not tabla.startswith('centros_id_') and tabla != 'django_migrations' for tabla in tablas)):
                    raise CommandError('El destino debe contener solo el esquema Centros y su registro de migraciones, sin auth ni datos de otras apps.')
        detalle = 'seis tablas personales con RLS forzado' if alias == 'default' else 'esquema exclusivo Centros (autorización del módulo; no RLS central)'
        self.stdout.write(self.style.SUCCESS(f'{alias}: rol web restringido y {detalle}.'))
