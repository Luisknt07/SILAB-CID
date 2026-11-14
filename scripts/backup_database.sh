#!/bin/sh
set -eu

# Respaldo logico atomico de PostgreSQL. Falla antes de crear un archivo si
# falta cualquier credencial y nunca imprime secretos en el registro.
umask 077

require_env() {
    name="$1"
    value="$2"
    if [ -z "$value" ]; then
        echo "Falta la variable obligatoria $name." >&2
        exit 2
    fi
}

require_env DB_NAME "${DB_NAME:-}"
require_env DB_USER "${DB_USER:-}"
require_env DB_PASSWORD "${DB_PASSWORD:-}"
require_env DB_HOST "${DB_HOST:-}"

BACKUP_DIR="${BACKUP_DIR:-/backups/database}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
FINAL_FILE="${BACKUP_DIR}/database_${TIMESTAMP}.dump"
TEMP_FILE="${FINAL_FILE}.tmp"
CHECKSUM_FILE="${FINAL_FILE}.sha256"
CHECKSUM_TEMP="${CHECKSUM_FILE}.tmp"

case "$BACKUP_RETENTION_DAYS" in
    ''|*[!0-9]*)
        echo "BACKUP_RETENTION_DAYS debe ser un entero positivo." >&2
        exit 2
        ;;
esac
if [ "$BACKUP_RETENTION_DAYS" -lt 1 ]; then
    echo "BACKUP_RETENTION_DAYS debe ser al menos 1." >&2
    exit 2
fi

mkdir -p "$BACKUP_DIR"
cleanup() {
    rm -f "$TEMP_FILE" "$CHECKSUM_TEMP"
}
trap cleanup EXIT HUP INT TERM

export PGPASSWORD="$DB_PASSWORD"
echo "Creando respaldo de ${DB_NAME} en ${FINAL_FILE}."
pg_dump \
    --host="$DB_HOST" \
    --username="$DB_USER" \
    --port="$DB_PORT" \
    --dbname="$DB_NAME" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --file="$TEMP_FILE"

# Un archivo no se publica como respaldo hasta que PostgreSQL puede leer su
# catalogo. La restauracion integral se prueba con verify_database_backup.sh.
pg_restore --list "$TEMP_FILE" >/dev/null
mv "$TEMP_FILE" "$FINAL_FILE"
(
    cd "$BACKUP_DIR"
    sha256sum "$(basename "$FINAL_FILE")" >"$(basename "$CHECKSUM_TEMP")"
)
mv "$CHECKSUM_TEMP" "$CHECKSUM_FILE"

find "$BACKUP_DIR" -type f -name 'database_*.dump' -mtime "+$BACKUP_RETENTION_DAYS" -delete
find "$BACKUP_DIR" -type f -name 'database_*.dump.sha256' -mtime "+$BACKUP_RETENTION_DAYS" -delete

echo "Respaldo verificado: ${FINAL_FILE}"
