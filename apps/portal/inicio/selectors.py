"""Lectura acotada a la publicación vigente; los borradores nunca son públicos."""
import logging
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.utils.translation import get_language
from .contracts import validar_portada
from .defaults import portada_base
from .control import inicio_activo

logger = logging.getLogger(__name__)


def portada_de_revision(revision):
    from .services import contenido_revision
    contenido = contenido_revision(revision)
    idioma = 'en' if (get_language() or '').startswith('en') else 'es'
    return validar_portada(contenido[idioma])


def portada_publicada():
    if not inicio_activo():
        return portada_base()
    from .models import PublicacionInicio
    try:
        actual = PublicacionInicio.objects.select_related('revision').filter(pk=1).first()
        if actual and actual.revision and actual.revision.estado == 'publicada':
            return portada_de_revision(actual.revision)
        if actual and actual.revision:
            logger.warning('Publicación de Inicio inválida; se utiliza la portada base.')
    except (DatabaseError, ValidationError, ValueError):
        logger.warning('Contenido de Inicio no disponible; se utiliza la portada base.')
    return portada_base()
