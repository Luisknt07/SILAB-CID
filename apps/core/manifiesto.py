"""Metadatos del nucleo; los proveedores institucionales son opcionales."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'core', '2.0.0', 'apps.core', 'nucleo',
    app_django='apps.core', migraciones=('apps.core.migrations',),
    integraciones_opcionales=('configuracion_institucional',),
    rutas=('apps.core.presentation.operativas_urls', 'apps.core.presentation.urls', 'apps.core.presentation.salud_urls'),
    salud=('apps.core.presentation.salud',),
    contratos=('identidad_producto_v1', 'identidad_institucion_v1', 'supervision_interna_v1'),
    comandos=('apps.core.management.commands',),
    administracion=('apps.core.admin',),
)
