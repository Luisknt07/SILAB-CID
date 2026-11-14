"""Publicar crea una revisión; restaurar nunca borra una publicación anterior."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.persistence.publicacion import actor_con_permiso, bloquear_publicacion
from apps.core.presentation.identidad import identidad_de_despliegue
from apps.core.presentation.capacidades import con_capacidad_bloqueada
from .contracts import validar_contenido
from .models import PublicacionInicio, RevisionInicio


def contenido_revision(revision):
    producto, institucion = identidad_de_despliegue()
    if (revision.institucion_codigo != institucion.siglas or revision.producto_codigo != producto.codigo
            or revision.estado not in RevisionInicio.Estado.values):
        raise ValidationError(_('Esta revisión no pertenece a la instalación actual.'))
    try:
        return validar_contenido(revision.contenido)
    except ValueError as exc:
        raise ValidationError(_(str(exc))) from exc


def validar_revision(revision):
    contenido = contenido_revision(revision)
    revision.full_clean()
    return contenido


@transaction.atomic
def guardar_borrador(contenido, usuario, *, titulo, base_esperada):
    autor = actor_con_permiso(usuario, 'portal.add_revisioninicio')
    with con_capacidad_bloqueada('portal', 'portada_inicio'):
        actual = bloquear_publicacion(PublicacionInicio)
        if actual.revision_id != base_esperada:
            raise ValidationError(_('La publicación cambió. Recarga y revisa los datos antes de confirmar.'))
        producto, institucion = identidad_de_despliegue()
        revision = RevisionInicio(titulo=titulo, contenido=contenido,
                                  institucion_codigo=institucion.siglas, producto_codigo=producto.codigo,
                                  estado='borrador', basada_en_id=actual.revision_id, autor=autor)
        validar_revision(revision)
        revision.save(_desde_editor=True)
        return revision


@transaction.atomic
def publicar_revision(revision_id, usuario, *, base_esperada):
    autor = actor_con_permiso(usuario, 'portal.publicar_inicio', lectura='portal.view_revisioninicio')
    with con_capacidad_bloqueada('portal', 'portada_inicio'):
        actual = bloquear_publicacion(PublicacionInicio)
        if actual.revision_id != base_esperada:
            raise ValidationError(_('La publicación cambió. Recarga y revisa los datos antes de confirmar.'))
        origen = RevisionInicio.objects.get(pk=revision_id)
        validar_revision(origen)
        if origen.estado == 'borrador' and origen.basada_en_id != base_esperada:
            raise ValidationError(_('Este borrador tiene una base anterior. Crea una revisión nueva con los datos actuales.'))
        revision = RevisionInicio(titulo=origen.titulo, contenido=origen.contenido,
                                  institucion_codigo=origen.institucion_codigo, producto_codigo=origen.producto_codigo,
                                  estado='publicada', basada_en_id=actual.revision_id, fuente=origen, autor=autor)
        validar_revision(revision)
        revision.save(_desde_editor=True)
        actual.revision = revision
        actual.save(_desde_editor=True, update_fields=['revision'])
        return revision


@transaction.atomic
def exportar_revision(revision_id, usuario):
    actor_con_permiso(usuario, 'portal.view_revisioninicio')
    revision = RevisionInicio.objects.get(pk=revision_id)
    contenido = validar_revision(revision)
    return {'version_esquema': 1, 'revision_id': revision.pk, 'titulo': revision.titulo,
            'estado': revision.estado, 'fecha': revision.fecha.isoformat(),
            'producto_codigo': revision.producto_codigo, 'institucion_codigo': revision.institucion_codigo,
            'contenido': contenido}
