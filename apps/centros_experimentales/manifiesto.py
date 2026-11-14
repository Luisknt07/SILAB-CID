"""Frontera publica propia; la operacion continua en el adaptador heredado."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'centros_experimentales', '1.2.0', 'apps.centros_experimentales', 'presentacion',
    dependencias=('core', 'integraciones', 'campo_experimental'), rutas=('apps.centros_experimentales.presentation.urls',),
    app_django='apps.centros_experimentales',
    capacidades=('catalogo_publico', 'detalle_unidad'),
    contratos=('identidad_unidad_v1',),
)
