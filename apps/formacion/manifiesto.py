"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'formacion', '2.0.0', 'apps.formacion', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.formacion', migraciones=('apps.formacion.migrations',),
    administracion=('apps.formacion.admin',),
    rutas=('apps.formacion.presentation.operativas_urls',),
    comandos=('apps.formacion.management.commands',),
)
