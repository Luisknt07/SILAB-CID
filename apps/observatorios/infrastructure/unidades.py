"""Composición del catálogo y detalle mediante contratos del directorio.

Las operaciones específicas pertenecen a la aplicación de la vertical;
este adaptador conecta sus entradas públicas con las capacidades compartidas.
"""

from apps.directorio_unidades.contracts import TipoUnidad
from apps.integraciones.unidades import catalogo_unidades, detalle_unidad


def consultar_catalogo(request):
    return catalogo_unidades(request, TipoUnidad.OBSERVATORIO)


def consultar_detalle(request, slug):
    return detalle_unidad(request, slug)
