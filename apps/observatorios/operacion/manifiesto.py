"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'observacion', '2.0.0', 'apps.observatorios.operacion', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.observatorios.operacion', migraciones=('apps.observatorios.operacion.migrations',),
    comandos=('apps.observatorios.operacion.management.commands',),
    administracion=('apps.observatorios.operacion.admin',),
    rutas=('apps.observatorios.operacion.presentation.operativas_urls',),
)
