#!/bin/sh
set -eu

# Restaura un respaldo en una base efimera. Debe ejecutarse con un usuario que
# tenga CREATEDB, idealmente en un servidor de verificacion aislado.
umask 077

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "Uso: verify_database_backup.sh /ruta/database_YYYYMMDDTHHMMSSZ.dump" >&2
    exit 2
fi
for name in DB_HOST DB_USER DB_PASSWORD; do
    eval "value=\${$name:-}"
    if [ -z "$value" ]; then
        echo "Falta la variable obligatoria $name." >&2
        exit 2
    fi
done

DB_PORT="${DB_PORT:-5432}"
RESTORE_DB_PREFIX="${RESTORE_DB_PREFIX:-citt_restore_check}"
# PostgreSQL trunca identificadores a 63 bytes. El prefijo se restringe para
# evitar colisiones por truncamiento o nombres fuera del espacio de prueba.
case "$RESTORE_DB_PREFIX" in
    ''|[0-9]*|*[!a-z0-9_]*)
        echo "RESTORE_DB_PREFIX solo admite letras minusculas, numeros y guion bajo; debe comenzar por letra o guion bajo." >&2
        exit 2
        ;;
esac
if [ "${#RESTORE_DB_PREFIX}" -gt 32 ]; then
    echo "RESTORE_DB_PREFIX no puede superar 32 caracteres." >&2
    exit 2
fi
RESTORE_DB_NAME="${RESTORE_DB_PREFIX}_$(date -u +%Y%m%d%H%M%S)_$$"
RESTORE_DB_CREATED=false
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
export PGPASSWORD="$DB_PASSWORD"

if [ ! -f "$CHECKSUM_FILE" ]; then
    echo "Falta el checksum: $CHECKSUM_FILE" >&2
    exit 2
fi
(
    cd "$(dirname "$BACKUP_FILE")"
    sha256sum --check "$(basename "$CHECKSUM_FILE")"
)
pg_restore --list "$BACKUP_FILE" >/dev/null

cleanup() {
    # Si createdb falla (por ejemplo, nombre ya ocupado), nunca borrar esa base.
    if [ "$RESTORE_DB_CREATED" = true ]; then
        dropdb --if-exists --host="$DB_HOST" --username="$DB_USER" --port="$DB_PORT" "$RESTORE_DB_NAME" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

createdb --host="$DB_HOST" --username="$DB_USER" --port="$DB_PORT" "$RESTORE_DB_NAME"
RESTORE_DB_CREATED=true
pg_restore \
    --exit-on-error \
    --no-owner \
    --no-privileges \
    --host="$DB_HOST" \
    --username="$DB_USER" \
    --port="$DB_PORT" \
    --dbname="$RESTORE_DB_NAME" \
    "$BACKUP_FILE"
psql \
    --host="$DB_HOST" \
    --username="$DB_USER" \
    --port="$DB_PORT" \
    --dbname="$RESTORE_DB_NAME" \
    --tuples-only \
    --command='SELECT 1;' | grep -q 1

echo "Restauracion comprobada en la base efimera ${RESTORE_DB_NAME}."
