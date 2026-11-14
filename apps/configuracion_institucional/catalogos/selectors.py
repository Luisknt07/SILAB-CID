"""Lecturas academicas validadas; sin dependencias del dominio de usuarios."""
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction

from apps.core.catalogos import catalogo_academico
from apps.core.presentation.identidad import identidad_de_despliegue
from .models import PublicacionCatalogoAcademico, RevisionCatalogoAcademico

logger = logging.getLogger(__name__)


def catalogo_de_revision(revision):
    producto, institucion = identidad_de_despliegue()
    if (revision.producto_codigo != producto.codigo or revision.institucion_codigo != institucion.siglas):
        raise ValueError('La revision pertenece a otra identidad de despliegue.')
    revision.clean()
    return catalogo_academico(revision.contenido)


def catalogo_publicado(base, *, database='default', estricto=False):
    try:
        with transaction.atomic(using=database):
            puntero = PublicacionCatalogoAcademico.objects.using(database).select_related('revision').filter(pk=1).first()
        if puntero and puntero.revision:
            if puntero.revision.estado != RevisionCatalogoAcademico.Estado.PUBLICADA:
                raise ValueError
            return catalogo_de_revision(puntero.revision)
    except (DatabaseError, ValueError, ValidationError, TypeError):
        if estricto:
            raise
        logger.warning('Catalogo institucional no disponible; se usa el catalogo del despliegue.')
    return base
