"""Comandos academicos: autoridad fresca, compatibilidad y cambio atomico."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext_lazy as _

from apps.core.catalogos import catalogo_academico, datos_catalogo, relaciones_para_publicar
from apps.core.presentation.auditoria_catalogos import auditar_catalogo
from apps.core.presentation.catalogos import catalogo_de_despliegue
from apps.core.presentation.identidad import identidad_de_despliegue
from ..versionado import actor_con_permiso, bloquear_publicacion
from .models import PublicacionCatalogoAcademico, RevisionCatalogoAcademico
from .selectors import catalogo_de_revision


def puede_publicar_catalogo(usuario):
    return bool(usuario.is_authenticated and usuario.is_active and usuario.is_staff
                and usuario.has_perm('configuracion_institucional.view_revisioncatalogoacademico')
                and usuario.has_perm('configuracion_institucional.publicar_catalogo'))


def revisar_compatibilidad(revision, actual=None):
    propuesto = catalogo_de_revision(revision)
    try:
        if actual and actual.estado != RevisionCatalogoAcademico.Estado.PUBLICADA:
            raise ValueError
        anterior = catalogo_de_revision(actual) if actual else catalogo_de_despliegue()
    except (ValueError, ValidationError, TypeError):
        raise ValidationError(_('La publicación de base es inválida; revisa su integridad antes de continuar.')) from None
    try:
        relaciones = relaciones_para_publicar(anterior, propuesto, actual.relaciones_reservadas if actual else {})
    except ValueError as exc:
        raise ValidationError(_(str(exc))) from None
    try:
        with transaction.atomic():
            resultados = auditar_catalogo(catalogo=propuesto)
    except DatabaseError:
        raise ValidationError(_('No se pudo comprobar la compatibilidad; no se publicaron cambios.')) from None
    if any(fila['codigos_desconocidos'] or fila['relaciones_incompatibles'] for fila in resultados):
        raise ValidationError(_('El catálogo propuesto no es compatible con los registros existentes. Revisa sus referencias.'))
    return propuesto, relaciones, resultados


@transaction.atomic
def guardar_borrador_catalogo(datos, usuario, *, titulo):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.add_revisioncatalogoacademico')
    actual = bloquear_publicacion(PublicacionCatalogoAcademico)
    producto, institucion = identidad_de_despliegue()
    try:
        contenido = datos_catalogo(catalogo_academico(datos))
    except (ValueError, TypeError):
        raise ValidationError({'contenido': _('Revisa los códigos, los nombres y las relaciones del catálogo.')}) from None
    revision = RevisionCatalogoAcademico(
        titulo=titulo, contenido=contenido,
        institucion_codigo=institucion.siglas, producto_codigo=producto.codigo,
        estado=RevisionCatalogoAcademico.Estado.BORRADOR, basada_en_id=actual.revision_id, autor=autor,
    )
    revision.full_clean()
    revision.save(_desde_editor=True)
    return revision


@transaction.atomic
def publicar_catalogo(revision_id, usuario, *, base_esperada):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.publicar_catalogo',
                             lectura='configuracion_institucional.view_revisioncatalogoacademico')
    actual = bloquear_publicacion(PublicacionCatalogoAcademico)
    if actual.revision_id != base_esperada:
        raise ValidationError(_('La publicación cambió. Recarga y revisa los datos antes de confirmar.'))
    origen = RevisionCatalogoAcademico.objects.get(pk=revision_id)
    if origen.estado == 'borrador' and origen.basada_en_id != base_esperada:
        raise ValidationError(_('Este borrador tiene una base anterior. Crea una revisión nueva con los datos actuales.'))
    propuesto, relaciones, _resultados = revisar_compatibilidad(origen, actual.revision)
    revision = RevisionCatalogoAcademico(
        titulo=origen.titulo, contenido=datos_catalogo(propuesto), relaciones_reservadas=relaciones,
        institucion_codigo=origen.institucion_codigo, producto_codigo=origen.producto_codigo,
        estado=RevisionCatalogoAcademico.Estado.PUBLICADA, basada_en_id=base_esperada,
        fuente=origen, autor=autor,
    )
    revision.full_clean()
    revision.save(_desde_editor=True)
    actual.revision = revision
    actual.save(_desde_editor=True, update_fields=['revision'])
    return revision
