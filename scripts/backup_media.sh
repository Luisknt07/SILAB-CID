#!/bin/sh
set -eu

# Los adjuntos forman parte de los datos de negocio y se respaldan aparte de
# PostgreSQL para poder restaurarlos y validarlos de manera independiente.
umask 077

MEDIA_ROOT="${MEDIA_ROOT:-/media}"
BACKUP_DIR="${BACKUP_DIR:-/backups/media}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
FINAL_FILE="${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz"
TEMP_FILE="${FINAL_FILE}.tmp"
CHECKSUM_FILE="${FINAL_FILE}.sha256"
CHECKSUM_TEMP="${CHECKSUM_FILE}.tmp"

if [ ! -d "$MEDIA_ROOT" ]; then
    echo "MEDIA_ROOT no existe: $MEDIA_ROOT" >&2
    exit 2
fi
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

tar -C "$MEDIA_ROOT" -czf "$TEMP_FILE" .
tar -tzf "$TEMP_FILE" >/dev/null
mv "$TEMP_FILE" "$FINAL_FILE"
(
    cd "$BACKUP_DIR"
    sha256sum "$(basename "$FINAL_FILE")" >"$(basename "$CHECKSUM_TEMP")"
)
mv "$CHECKSUM_TEMP" "$CHECKSUM_FILE"

find "$BACKUP_DIR" -type f -name 'media_*.tar.gz' -mtime "+$BACKUP_RETENTION_DAYS" -delete
find "$BACKUP_DIR" -type f -name 'media_*.tar.gz.sha256' -mtime "+$BACKUP_RETENTION_DAYS" -delete

echo "Respaldo de adjuntos verificado: ${FINAL_FILE}"
