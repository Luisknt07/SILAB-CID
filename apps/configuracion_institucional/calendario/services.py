"""Publicacion atomica de politica, sin cambios en fechas o reservas."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext_lazy as _

from apps.core.calendario import datos_calendario, politica_calendario, validar_transicion_calendario
from apps.core.presentation.auditoria_calendario import auditar_calendario
from apps.core.presentation.calendario import calendario_de_despliegue
from apps.core.presentation.identidad import identidad_de_despliegue
from ..versionado import actor_con_permiso, bloquear_publicacion
from .models import PublicacionPoliticaCalendario, RevisionPoliticaCalendario
from .selectors import calendario_de_revision


def puede_publicar_calendario(usuario):
    return bool(usuario.is_authenticated and usuario.is_active and usuario.is_staff
                and usuario.has_perm('configuracion_institucional.view_revisionpoliticacalendario')
                and usuario.has_perm('configuracion_institucional.publicar_calendario'))


def revisar_compatibilidad(revision, actual=None):
    propuesto = calendario_de_revision(revision)
    try:
        if actual and actual.estado != RevisionPoliticaCalendario.Estado.PUBLICADA:
            raise ValueError
        anterior = calendario_de_revision(actual) if actual else calendario_de_despliegue()
    except (ValueError, ValidationError, TypeError):
        raise ValidationError(_('La publicación de base es inválida; revisa su integridad antes de continuar.')) from None
    try:
        validar_transicion_calendario(anterior, propuesto)
    except ValueError:
        raise ValidationError(_('Conserva los códigos anteriores y el tipo de cada ciclo; retira como histórico.')) from None
    try:
        with transaction.atomic():
            resultado = auditar_calendario(politica_propuesta=propuesto)
    except (DatabaseError, ValueError, ValidationError, TypeError):
        raise ValidationError(_('No se pudo comprobar la compatibilidad; no se publicaron cambios.')) from None
    if any(v for k, v in resultado.items() if k not in {'periodos', 'semanas'}):
        raise ValidationError(_('La política propuesta no es compatible con los períodos y semanas existentes.'))
    return propuesto, None, [resultado]


@transaction.atomic
def guardar_borrador_calendario(datos, usuario, *, titulo):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.add_revisionpoliticacalendario')
    actual = bloquear_publicacion(PublicacionPoliticaCalendario)
    producto, institucion = identidad_de_despliegue()
    try:
        contenido = datos_calendario(politica_calendario(datos))
    except (ValueError, TypeError):
        raise ValidationError({'contenido': _('Revisa los ciclos, los ámbitos y las semanas.')}) from None
    revision = RevisionPoliticaCalendario(
        titulo=titulo, contenido=contenido, institucion_codigo=institucion.siglas,
        producto_codigo=producto.codigo, estado=RevisionPoliticaCalendario.Estado.BORRADOR,
        basada_en_id=actual.revision_id, autor=autor,
    )
    revision.full_clean()
    revision.save(_desde_editor=True)
    return revision


@transaction.atomic
def publicar_calendario(revision_id, usuario, *, base_esperada):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.publicar_calendario',
                             lectura='configuracion_institucional.view_revisionpoliticacalendario')
    actual = bloquear_publicacion(PublicacionPoliticaCalendario)
    if actual.revision_id != base_esperada:
        raise ValidationError(_('La publicación cambió. Recarga y revisa los datos antes de confirmar.'))
    origen = RevisionPoliticaCalendario.objects.get(pk=revision_id)
    if origen.estado == 'borrador' and origen.basada_en_id != base_esperada:
        raise ValidationError(_('Este borrador tiene una base anterior. Crea una revisión nueva con los datos actuales.'))
    propuesto, _relaciones, _resultados = revisar_compatibilidad(origen, actual.revision)
    revision = RevisionPoliticaCalendario(
        titulo=origen.titulo, contenido=datos_calendario(propuesto),
        institucion_codigo=origen.institucion_codigo, producto_codigo=origen.producto_codigo,
        estado=RevisionPoliticaCalendario.Estado.PUBLICADA, basada_en_id=base_esperada,
        fuente=origen, autor=autor,
    )
    revision.full_clean()
    revision.save(_desde_editor=True)
    actual.revision = revision
    actual.save(_desde_editor=True, update_fields=['revision'])
    return revision
