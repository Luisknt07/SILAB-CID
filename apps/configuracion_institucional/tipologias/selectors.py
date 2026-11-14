"""Lectura del catalogo institucional; falla cerrado a las tipologias base."""
import logging

from django.db import DatabaseError

from apps.core.tipologias import catalogo_tipologias
from .models import TipologiaUnidad

logger = logging.getLogger(__name__)


def tipologias_publicadas(base, *, database='default', estricto=False):
    """Las filas institucionales se superponen a las implementadas por codigo.

    Asi una base sin filas, o con filas solo de tipologias nuevas, conserva
    las cuatro implementadas; desactivar una de ellas exige su fila.
    """
    try:
        por_codigo = {tipologia.codigo: tipologia for tipologia in base}
        for fila in TipologiaUnidad.objects.using(database).all():
            por_codigo[fila.codigo] = fila.como_tipologia()
        return catalogo_tipologias(por_codigo.values())
    except (DatabaseError, ValueError):
        if estricto:
            raise
        logger.warning('Tipologias institucionales no disponibles; se usa el despliegue.')
        return base
