"""Lectura opcional de marca; sin imports de unidades ni consultas al arrancar."""

import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError, transaction

from apps.core.identidad import identidades

from .imagenes import CAMPOS_IMAGENES
from .models import PublicacionInstitucional


logger = logging.getLogger(__name__)


def identidad_de_revision(revision, producto, institucion):
    if (revision.producto_codigo != producto.codigo
            or revision.institucion_codigo != institucion.siglas):
        raise ValueError('La presentacion pertenece a otra identidad de despliegue.')
    revision.clean()
    if revision.correo:
        validate_email(revision.correo)
    return identidades(
        {'nombre': revision.nombre_producto, 'nombre_corto': revision.nombre_corto_producto,
         'codigo': producto.codigo},
        {'nombre': revision.nombre_institucion, 'siglas': institucion.siglas,
         **{campo: getattr(revision, campo) for campo in
            ('telefono', 'correo', 'ubicacion', 'logo', 'logo_secundario', 'paleta')},
         'imagenes': tuple((campo, getattr(revision, campo).name) for campo in CAMPOS_IMAGENES if getattr(revision, campo))},
    )


def identidad_publicada(base):
    """Un fallo del proveedor de presentacion conserva la identidad de despliegue.

    El savepoint evita dejar rota una transaccion exterior por una tabla ausente.
    No oculta errores del resto de la base ni certifica aislamiento de procesos.
    """
    try:
        with transaction.atomic():
            publicacion = PublicacionInstitucional.objects.select_related('revision').filter(pk=1).first()
        if publicacion and publicacion.revision:
            if publicacion.revision.estado != 'publicada':
                raise ValueError('La presentacion activa no es una publicacion.')
            return identidad_de_revision(publicacion.revision, *base)
    except (DatabaseError, ValueError, ValidationError):
        logger.warning('Presentacion institucional no disponible; se usa la identidad del despliegue.')
    return base
