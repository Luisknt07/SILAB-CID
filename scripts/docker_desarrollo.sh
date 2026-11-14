#!/bin/sh
set -eu
# Los propietarios y respaldos no se entregan al proceso web.
for clave in DB_MIGRATION_USER DB_MIGRATION_PASSWORD DB_BACKUP_USER DB_BACKUP_PASSWORD DB_RUNTIME_USER DB_RUNTIME_PASSWORD CENTROS_DB_MIGRATION_USER CENTROS_DB_MIGRATION_PASSWORD CENTROS_DB_BACKUP_USER CENTROS_DB_BACKUP_PASSWORD CENTROS_DB_RUNTIME_USER CENTROS_DB_RUNTIME_PASSWORD; do
    unset "$clave"
done
export PYTHON_DOTENV_DISABLED=1
python manage.py check
python manage.py verificar_seguridad_bd --all
exec python manage.py runserver 0.0.0.0:8000
