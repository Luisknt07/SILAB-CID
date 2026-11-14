"""Lecturas academicas validadas; sin dependencias del dominio de usuarios."""
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction

from apps.core.calendario import politica_calendario
from apps.core.presentation.identidad import identidad_de_despliegue
from .models import PublicacionPoliticaCalendario, RevisionPoliticaCalendario

logger = logging.getLogger(__name__)


def calendario_de_revision(revision):
    producto, institucion = identidad_de_despliegue()
    if (revision.producto_codigo != producto.codigo or revision.institucion_codigo != institucion.siglas):
        raise ValueError('La revision pertenece a otra identidad de despliegue.')
    revision.clean()
    return politica_calendario(revision.contenido)


def calendario_publicado(base, *, database='default', estricto=False):
    try:
        with transaction.atomic(using=database):
            puntero = PublicacionPoliticaCalendario.objects.using(database).select_related('revision').filter(pk=1).first()
        if puntero and puntero.revision:
            if puntero.revision.estado != RevisionPoliticaCalendario.Estado.PUBLICADA:
                raise ValueError
            return calendario_de_revision(puntero.revision)
    except (DatabaseError, ValueError, ValidationError, TypeError):
        if estricto:
            raise
        logger.warning('Calendario institucional no disponible; se usa el despliegue.')
    return base
