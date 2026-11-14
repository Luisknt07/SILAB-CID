"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'finanzas', '2.0.0', 'apps.finanzas', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.finanzas', migraciones=('apps.finanzas.migrations',),
    administracion=('apps.finanzas.admin',),
    rutas=('apps.finanzas.presentation.operativas_urls',),
)
