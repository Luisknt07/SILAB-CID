#!/bin/sh
set -eu
unset DB_MIGRATION_PASSWORD DB_MIGRATION_USER DB_BACKUP_PASSWORD DB_BACKUP_USER
unset CENTROS_DB_MIGRATION_PASSWORD CENTROS_DB_MIGRATION_USER CENTROS_DB_BACKUP_PASSWORD CENTROS_DB_BACKUP_USER
python manage.py check --deploy
python manage.py verificar_seguridad_bd --all
# La imagen ya trae los estáticos recopilados (Dockerfile). Solo se recopilan
# aquí si falta su manifiesto, por ejemplo con un volumen vacío en var/static.
[ -f var/static/staticfiles.json ] || python manage.py collectstatic --noinput
exec python scripts/servir_produccion.py
