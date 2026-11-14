"""Entradas y reglas propias; la persistencia operativa sigue en el legado."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'plantas_piloto', '1.4.0', 'apps.plantas_piloto', 'presentacion',
    dependencias=('core', 'integraciones', 'plantas_operacion'), rutas=('apps.plantas_piloto.presentation.urls',),
    app_django='apps.plantas_piloto',
    capacidades=(
        'catalogo_publico', 'detalle_unidad', 'planificacion_demanda',
        'gobierno_completitud', 'repositorio_trazable',
    ),
    contratos=('identidad_unidad_v1',),
)
