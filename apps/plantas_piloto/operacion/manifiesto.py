"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'plantas_operacion', '2.0.0', 'apps.plantas_piloto.operacion', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.plantas_piloto.operacion', migraciones=('apps.plantas_piloto.operacion.migrations',),
    comandos=('apps.plantas_piloto.operacion.management.commands',),
    administracion=('apps.plantas_piloto.operacion.admin',),
    rutas=('apps.plantas_piloto.operacion.presentation.operativas_urls',),
)
