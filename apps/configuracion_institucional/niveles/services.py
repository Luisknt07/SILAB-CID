"""Comandos academicos: autoridad fresca, compatibilidad y cambio atomico."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext_lazy as _

from apps.core.niveles import niveles_academicos, datos_niveles, validar_transicion_niveles
from apps.core.presentation.auditoria_catalogos import auditar_catalogo
from apps.core.presentation.niveles import niveles_de_despliegue
from apps.core.presentation.catalogo_institucional import con_catalogo_institucional
from apps.core.presentation.identidad import identidad_de_despliegue
from ..versionado import actor_con_permiso, bloquear_publicacion
from .models import PublicacionNivelesAcademicos, RevisionNivelesAcademicos
from .selectors import niveles_de_revision


def puede_publicar_niveles(usuario):
    return bool(usuario.is_authenticated and usuario.is_active and usuario.is_staff
                and usuario.has_perm('configuracion_institucional.view_revisionnivelesacademicos')
                and usuario.has_perm('configuracion_institucional.publicar_niveles'))


def revisar_compatibilidad(revision, actual=None):
    propuesto = niveles_de_revision(revision)
    try:
        if actual and actual.estado != RevisionNivelesAcademicos.Estado.PUBLICADA:
            raise ValueError
        anterior = niveles_de_revision(actual) if actual else niveles_de_despliegue()
    except (ValueError, ValidationError, TypeError):
        raise ValidationError(_('La publicación de base es inválida; revisa su integridad antes de continuar.')) from None
    try:
        validar_transicion_niveles(anterior, propuesto)
    except ValueError as exc:
        raise ValidationError(_(str(exc))) from None
    try:
        with transaction.atomic(), con_catalogo_institucional(estricto=True):
            resultados = auditar_catalogo(niveles_propuestos=propuesto)
    except (DatabaseError, ValueError, ValidationError, TypeError):
        raise ValidationError(_('No se pudo comprobar la compatibilidad; no se publicaron cambios.')) from None
    if any(fila['codigos_desconocidos'] or fila['relaciones_incompatibles'] for fila in resultados):
        raise ValidationError(_('Los niveles propuestos no son compatibles con los registros existentes. Revisa sus referencias.'))
    return propuesto, None, resultados


@transaction.atomic
def guardar_borrador_niveles(datos, usuario, *, titulo):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.add_revisionnivelesacademicos')
    actual = bloquear_publicacion(PublicacionNivelesAcademicos)
    producto, institucion = identidad_de_despliegue()
    try:
        contenido = datos_niveles(niveles_academicos(datos))
    except (ValueError, TypeError):
        raise ValidationError({'contenido': _('Revisa los códigos, las etiquetas y las rutas de niveles.')}) from None
    revision = RevisionNivelesAcademicos(
        titulo=titulo, contenido=contenido,
        institucion_codigo=institucion.siglas, producto_codigo=producto.codigo,
        estado=RevisionNivelesAcademicos.Estado.BORRADOR, basada_en_id=actual.revision_id, autor=autor,
    )
    revision.full_clean()
    revision.save(_desde_editor=True)
    return revision


@transaction.atomic
def publicar_niveles(revision_id, usuario, *, base_esperada):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.publicar_niveles',
                             lectura='configuracion_institucional.view_revisionnivelesacademicos')
    actual = bloquear_publicacion(PublicacionNivelesAcademicos)
    if actual.revision_id != base_esperada:
        raise ValidationError(_('La publicación cambió. Recarga y revisa los datos antes de confirmar.'))
    origen = RevisionNivelesAcademicos.objects.get(pk=revision_id)
    if origen.estado == 'borrador' and origen.basada_en_id != base_esperada:
        raise ValidationError(_('Este borrador tiene una base anterior. Crea una revisión nueva con los datos actuales.'))
    propuesto, _relaciones, _resultados = revisar_compatibilidad(origen, actual.revision)
    revision = RevisionNivelesAcademicos(
        titulo=origen.titulo, contenido=datos_niveles(propuesto),
        institucion_codigo=origen.institucion_codigo, producto_codigo=origen.producto_codigo,
        estado=RevisionNivelesAcademicos.Estado.PUBLICADA, basada_en_id=base_esperada,
        fuente=origen, autor=autor,
    )
    revision.full_clean()
    revision.save(_desde_editor=True)
    actual.revision = revision
    actual.save(_desde_editor=True, update_fields=['revision'])
    return revision
