#!/bin/sh
# Solo el servicio de migraciones recibe estas credenciales.
set -eu
export DJANGO_SETTINGS_MODULE=config.settings_production
: "${DB_MIGRATION_USER:?Configure DB_MIGRATION_USER fuera del repositorio}"
: "${DB_MIGRATION_PASSWORD:?Configure DB_MIGRATION_PASSWORD fuera del repositorio}"
export DB_RUNTIME_USER="$DB_USER" DB_RUNTIME_PASSWORD="$DB_PASSWORD"
export DB_USER="$DB_MIGRATION_USER" DB_PASSWORD="$DB_MIGRATION_PASSWORD"
# Preparar el destino no activa el corte. Migra Centros automáticamente solo
# tras la copia verificada y la activación explícita del router.
centros_flag="$(printf '%s' "${CENTROS_DB_ENABLED:-false}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
case "$centros_flag" in
    1|true|yes|on)
        : "${CENTROS_DB_MIGRATION_USER:?Configure el rol de migración Centros}"
        : "${CENTROS_DB_MIGRATION_PASSWORD:?Configure la clave de migración Centros}"
        export CENTROS_DB_RUNTIME_USER="$CENTROS_DB_USER" CENTROS_DB_RUNTIME_PASSWORD="$CENTROS_DB_PASSWORD"
        export CENTROS_DB_USER="$CENTROS_DB_MIGRATION_USER" CENTROS_DB_PASSWORD="$CENTROS_DB_MIGRATION_PASSWORD"
        centros_activo=true
        ;;
    *) centros_activo=false ;;
esac
python manage.py check --deploy
python manage.py migrate --database default --noinput
python manage.py preparar_roles_bd --database default
if [ "$centros_activo" = true ]; then
    python manage.py migrate --database centros --noinput
    # El propietario de Centros migra su esquema, sin administrar roles.
    # El DBA aprovisiona antes las cuentas web y de respaldo por separado.
    python manage.py preparar_roles_bd --database centros --solo-permisos
fi
