"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'campo_experimental', '2.0.0', 'apps.centros_experimentales.operacion', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.centros_experimentales.operacion', migraciones=('apps.centros_experimentales.operacion.migrations',),
    administracion=('apps.centros_experimentales.operacion.admin',),
    rutas=('apps.centros_experimentales.operacion.presentation.operativas_urls',),
    comandos=('apps.centros_experimentales.operacion.management.commands',),
)
