"""Comandos de borrador/publicacion con autoridad fresca y control de versiones."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.presentation.identidad import identidad_de_despliegue

from .imagenes import CAMPOS_IMAGENES, preparar_imagen
from .models import CAMPOS_PRESENTACION, PublicacionInstitucional, RevisionPresentacion
from .selectors import identidad_de_revision
from .versionado import actor_con_permiso, bloquear_publicacion


def puede_publicar(usuario):
    return bool(usuario.is_authenticated and usuario.is_active and usuario.is_staff
                and usuario.has_perm('configuracion_institucional.view_revisionpresentacion')
                and usuario.has_perm('configuracion_institucional.publicar_presentacion'))


def _autor_actual(usuario, *, publicar=False):
    return actor_con_permiso(
        usuario, 'configuracion_institucional.publicar_presentacion' if publicar
        else 'configuracion_institucional.add_revisionpresentacion',
        lectura='configuracion_institucional.view_revisionpresentacion' if publicar else None,
    )


def _publicacion_bloqueada():
    return bloquear_publicacion(PublicacionInstitucional)


def _validar_revision(revision):
    identidad_de_revision(revision, *identidad_de_despliegue())
    revision.full_clean()


@transaction.atomic
def guardar_borrador(revision, usuario):
    autor = _autor_actual(usuario)
    actual = _publicacion_bloqueada()
    producto, institucion = identidad_de_despliegue()
    revision.institucion_codigo = institucion.siglas
    revision.producto_codigo = producto.codigo
    revision.estado = RevisionPresentacion.Estado.BORRADOR
    revision.basada_en_id = actual.revision_id
    revision.fuente_id = None
    revision.autor = autor
    for campo in CAMPOS_IMAGENES:
        archivo = getattr(revision, campo)
        if archivo and not archivo._committed:
            setattr(revision, campo, preparar_imagen(archivo))
        elif archivo and not RevisionPresentacion.objects.filter(
                **{campo: archivo.name}, institucion_codigo=institucion.siglas,
                producto_codigo=producto.codigo).exists():
            raise ValidationError({campo: _('La imagen debe subirse desde el editor o proceder de una revisión de esta institución.')})
    _validar_revision(revision)
    revision.save(_desde_editor=True)
    return revision


@transaction.atomic
def publicar_revision(revision_id, usuario, *, base_esperada):
    autor = _autor_actual(usuario, publicar=True)
    actual = _publicacion_bloqueada()
    if actual.revision_id != base_esperada:
        raise ValidationError(_('La publicación cambió. Recarga y revisa los datos antes de confirmar.'))
    origen = RevisionPresentacion.objects.get(pk=revision_id)
    # Los borradores tienen una base fija: no sobrescribir cambios posteriores.
    if origen.estado == 'borrador' and origen.basada_en_id != base_esperada:
        raise ValidationError(_('Este borrador tiene una base anterior. Crea una revisión nueva con los datos actuales.'))
    revision = RevisionPresentacion(
        **{campo: getattr(origen, campo) for campo in CAMPOS_PRESENTACION},
        institucion_codigo=origen.institucion_codigo, producto_codigo=origen.producto_codigo,
        estado=RevisionPresentacion.Estado.PUBLICADA, basada_en_id=base_esperada,
        fuente=origen, autor=autor,
    )
    _validar_revision(revision)
    revision.save(_desde_editor=True)
    actual.revision = revision
    actual.save(_desde_editor=True, update_fields=['revision'])
    return revision
