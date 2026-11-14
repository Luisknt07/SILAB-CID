"""Frontera publica propia; la operacion continua en el adaptador heredado."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'observatorios', '1.1.0', 'apps.observatorios', 'presentacion',
    dependencias=('core', 'integraciones', 'observacion'), rutas=('apps.observatorios.presentation.urls',),
    app_django='apps.observatorios',
    capacidades=('catalogo_publico', 'detalle_unidad'),
    contratos=('identidad_unidad_v1',),
)
