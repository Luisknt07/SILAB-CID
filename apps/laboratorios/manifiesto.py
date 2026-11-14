"""Frontera publica propia; la operacion continua en el adaptador heredado."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'laboratorios', '1.1.0', 'apps.laboratorios', 'presentacion',
    dependencias=('core', 'integraciones', 'laboratorios_operacion'), rutas=('apps.laboratorios.presentation.urls',),
    app_django='apps.laboratorios',
    capacidades=('catalogo_publico', 'detalle_unidad'),
    contratos=('identidad_unidad_v1',),
)
