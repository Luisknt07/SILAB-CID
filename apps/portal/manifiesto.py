"""Inicio posee datos propios; las demas secciones siguen en presentacion."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'portal', '1.1.0', 'apps.portal', 'propio', dependencias=('core',),
    integraciones_opcionales=('centros_id', 'laboratorios', 'configuracion_institucional'),
    app_django='apps.portal', rutas=('apps.portal.presentation.urls',),
    administracion=('apps.portal.admin',), migraciones=('apps.portal.migrations',),
    comandos=('apps.portal.management.commands.auditar_capacidades',),
    capacidades=('portada_inicio',), contratos=('portada_inicio_v1',),
)
