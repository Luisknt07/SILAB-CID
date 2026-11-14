"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'recursos', '2.0.0', 'apps.recursos', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.recursos', migraciones=('apps.recursos.migrations',),
    comandos=('apps.recursos.management.commands',),
    administracion=('apps.recursos.admin',),
    rutas=('apps.recursos.presentation.operativas_urls',),
)
