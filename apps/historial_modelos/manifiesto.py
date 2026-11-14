"""Solo historial de instalaciones existentes; sin modelos ni operación actual."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'historial_modelos', '2.0.0', 'apps.historial_modelos', 'heredado',
    app_django='apps.historial_modelos', migraciones=('apps.historial_modelos.migrations',),
)
