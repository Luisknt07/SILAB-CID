"""Contratos de integración entre aplicaciones con propietarios explícitos."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'integraciones', '2.0.0', 'apps.integraciones', 'propio',
    dependencias=('core','directorio_unidades','gestion_unidades','recursos','reservas','formacion','documentos','finanzas'),
    app_django='apps.integraciones', rutas=('apps.integraciones.urls',),
    integraciones_opcionales=('centros_id',), migraciones=('apps.integraciones.migrations',), contratos=('senales_heredadas_v1',),
    comandos=('apps.integraciones.management.commands',),
)
