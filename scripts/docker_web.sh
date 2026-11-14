#!/bin/sh
set -eu
unset DB_MIGRATION_PASSWORD DB_MIGRATION_USER DB_BACKUP_PASSWORD DB_BACKUP_USER
unset CENTROS_DB_MIGRATION_PASSWORD CENTROS_DB_MIGRATION_USER CENTROS_DB_BACKUP_PASSWORD CENTROS_DB_BACKUP_USER
python manage.py check --deploy
python manage.py verificar_seguridad_bd --all
python manage.py collectstatic --noinput
exec python scripts/servir_produccion.py
