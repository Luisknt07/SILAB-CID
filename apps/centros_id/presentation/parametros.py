"""Identificadores públicos acotados antes de convertirlos o consultar el ORM."""
from django.http import Http404


def identificador(valor):
    if not valor:
        return None
    if not valor.isascii() or not valor.isdigit() or len(valor) > 18:
        raise Http404
    return int(valor)
