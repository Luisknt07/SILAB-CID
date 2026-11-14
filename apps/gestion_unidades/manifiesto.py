"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'gestion_unidades', '2.0.0', 'apps.gestion_unidades', 'propio', dependencias=('core',),
    app_django='apps.gestion_unidades', migraciones=('apps.gestion_unidades.migrations',),
    administracion=('apps.gestion_unidades.admin',),
    rutas=('apps.gestion_unidades.presentation.operativas_urls',),
    comandos=('apps.gestion_unidades.management.commands',),
)
