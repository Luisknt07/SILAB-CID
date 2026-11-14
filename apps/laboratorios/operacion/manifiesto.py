"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'laboratorios_operacion', '2.0.0', 'apps.laboratorios.operacion', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.laboratorios.operacion', migraciones=('apps.laboratorios.operacion.migrations',),
    comandos=('apps.laboratorios.operacion.management.commands',),
    administracion=('apps.laboratorios.operacion.admin',),
    rutas=('apps.laboratorios.operacion.presentation.operativas_urls',),
)
