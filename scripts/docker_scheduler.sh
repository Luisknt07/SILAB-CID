#!/bin/sh
set -eu
unset DB_MIGRATION_PASSWORD DB_MIGRATION_USER DB_BACKUP_PASSWORD DB_BACKUP_USER
unset CENTROS_DB_MIGRATION_PASSWORD CENTROS_DB_MIGRATION_USER CENTROS_DB_BACKUP_PASSWORD CENTROS_DB_BACKUP_USER
python manage.py verificar_seguridad_bd --all

interval="${RESERVATION_REMINDER_INTERVAL_MINUTES:-15}"

case "$interval" in
  ''|*[!0-9]*)
    echo "RESERVATION_REMINDER_INTERVAL_MINUTES debe ser un entero." >&2
    exit 2
    ;;
esac

if [ "$interval" -lt 5 ]; then
  echo "El intervalo mínimo del programador es 5 minutos." >&2
  exit 2
fi

while true; do
  python manage.py limpiar_contadores_peticiones
  python manage.py procesar_recordatorios_reservas
  # Silencio operativo: revisar el uso aun cuando no se registren nuevas actividades.
  # Sin política configurada sólo informa; nunca comunica ni ejecuta traspasos.
  python manage.py detectar_equipos_sin_uso || echo "No se completó la revisión de uso de equipos." >&2
  # Los laboratorios sin incidencias avanzan sin revisión individual de Dirección.
  python manage.py automatizar_documentos_laboratorios --aplicar --limite 25 || echo "No se completó un lote de controles documentales." >&2
  # Los indicadores de los observatorios con API pública: cada conexión solo consulta cuando le toca.
  python manage.py sincronizar_observatorios || echo "No se pudo sincronizar los observatorios." >&2
  sleep "$((interval * 60))"
done
