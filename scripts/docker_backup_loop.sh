#!/bin/sh
set -eu

interval="${BACKUP_INTERVAL_SECONDS:-86400}"
case "$interval" in
    ''|*[!0-9]*)
        echo "BACKUP_INTERVAL_SECONDS debe ser un entero." >&2
        exit 2
        ;;
esac
if [ "$interval" -lt 3600 ]; then
    echo "El intervalo minimo de respaldo es una hora." >&2
    exit 2
fi

verificar="${BACKUP_VERIFY_RESTORE:-true}"
case "$verificar" in
    true|false) ;;
    *) echo "BACKUP_VERIFY_RESTORE requiere true o false." >&2; exit 2 ;;
esac
incluir_media="${BACKUP_INCLUDE_MEDIA:-true}"
case "$incluir_media" in
    true|false) ;;
    *) echo "BACKUP_INCLUDE_MEDIA requiere true o false." >&2; exit 2 ;;
esac

while true; do
    sh /scripts/backup_database.sh
    # La copia se considera valida solo si se restaura en una base temporal y
    # responde a una consulta; BACKUP_VERIFY_RESTORE=false lo desactiva.
    if [ "$verificar" = "true" ]; then
        ultima="$(ls -1t "${BACKUP_DIR:-/backups}"/database_*.dump 2>/dev/null | head -n 1)"
        if [ -n "$ultima" ]; then
            sh /scripts/verify_database_backup.sh "$ultima"
        fi
    fi
    if [ "$incluir_media" = true ]; then
        sh /scripts/backup_media.sh
        MEDIA_ROOT=/brand BACKUP_DIR="${BACKUP_DIR:-/backups}/institutional-brand" sh /scripts/backup_media.sh
    fi
    sleep "$interval"
done
