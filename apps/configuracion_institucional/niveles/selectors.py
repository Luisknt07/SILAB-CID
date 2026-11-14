"""Lecturas academicas validadas; sin dependencias del dominio de usuarios."""
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction

from apps.core.niveles import niveles_academicos
from apps.core.presentation.identidad import identidad_de_despliegue
from .models import PublicacionNivelesAcademicos, RevisionNivelesAcademicos

logger = logging.getLogger(__name__)


def niveles_de_revision(revision):
    producto, institucion = identidad_de_despliegue()
    if (revision.producto_codigo != producto.codigo or revision.institucion_codigo != institucion.siglas):
        raise ValueError('La revision pertenece a otra identidad de despliegue.')
    revision.clean()
    return niveles_academicos(revision.contenido)


def niveles_publicados(base, *, database='default', estricto=False):
    try:
        with transaction.atomic(using=database):
            puntero = PublicacionNivelesAcademicos.objects.using(database).select_related('revision').filter(pk=1).first()
        if puntero and puntero.revision:
            if puntero.revision.estado != RevisionNivelesAcademicos.Estado.PUBLICADA:
                raise ValueError
            return niveles_de_revision(puntero.revision)
    except (DatabaseError, ValueError, ValidationError, TypeError):
        if estricto:
            raise
        logger.warning('Niveles institucionales no disponibles; se usa el despliegue.')
    return base
