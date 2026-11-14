"""Adaptadores HTTP publicos de Observatorios."""

from apps.observatorios.infrastructure.unidades import (
    consultar_catalogo,
    consultar_detalle,
)


def catalogo(request):
    return consultar_catalogo(request)


def detalle(request, slug):
    return consultar_detalle(request, slug)
