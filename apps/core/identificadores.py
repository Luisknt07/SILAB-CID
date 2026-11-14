"""Claves numéricas procedentes de URLs o formularios HTTP."""
from django.http import Http404


MAX_ID = 9223372036854775807


def id_solicitado(valor):
    """Normaliza una clave positiva antes del ORM; conserva el 404 de objeto ausente.

    Limitar longitud antes de int evita también conversiones costosas y claves
    fuera del bigint de PostgreSQL. La búsqueda mantiene su alcance en la vista.
    """
    texto = str(valor).strip() if valor is not None else ''
    if not texto or len(texto) > 19 or not texto.isascii() or not texto.isdecimal():
        raise Http404('Identificador inválido.')
    numero = int(texto)
    if not 0 < numero <= MAX_ID:
        raise Http404('Identificador inválido.')
    return numero
