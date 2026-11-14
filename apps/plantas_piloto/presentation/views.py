"""Adaptadores HTTP publicos de Plantas Piloto."""

from apps.plantas_piloto.infrastructure.unidades import (
    consultar_catalogo,
    consultar_detalle,
)


def catalogo(request):
    return consultar_catalogo(request)


def detalle(request, slug):
    return consultar_detalle(request, slug)
