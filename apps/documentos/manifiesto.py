"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'documentos', '2.0.0', 'apps.documentos', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.documentos', migraciones=('apps.documentos.migrations',),
    administracion=('apps.documentos.admin',),
    rutas=('apps.documentos.presentation.operativas_urls',),
    comandos=('apps.documentos.management.commands',),
)
