"""Aplicación propietaria con persistencia y administración propias."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'reservas', '2.0.0', 'apps.reservas', 'propio', dependencias=('core', 'directorio_unidades'),
    app_django='apps.reservas', migraciones=('apps.reservas.migrations',), capacidades=('reservas_operativas',),
    comandos=('apps.reservas.management.commands',),
    administracion=('apps.reservas.admin',),
    rutas=('apps.reservas.presentation.operativas_urls',),
)
