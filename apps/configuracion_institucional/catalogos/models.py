"""Snapshots academicos; no duplican facultades/carreras en tablas operativas."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.catalogos import catalogo_academico
from apps.core.identidad import validar_texto
from ..versionado import HistorialInstitucionalQuerySet


class RevisionCatalogoAcademico(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'borrador', _('Borrador')
        PUBLICADA = 'publicada', _('Publicada')

    titulo = models.CharField(_('Nombre de la revisión'), max_length=100)
    institucion_codigo = models.CharField(max_length=200, editable=False)
    producto_codigo = models.CharField(max_length=250, editable=False)
    contenido = models.JSONField(_('Catálogo académico'))
    relaciones_reservadas = models.JSONField(default=dict, editable=False, blank=True)
    estado = models.CharField(_('Estado'), max_length=10, choices=Estado.choices, editable=False)
    basada_en = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='+', editable=False, verbose_name=_('Publicación de base'))
    fuente = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                              related_name='+', editable=False, verbose_name=_('Revisión de origen'))
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name='+', editable=False, verbose_name=_('Responsable'))
    fecha = models.DateTimeField(_('Fecha'), auto_now_add=True)
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        ordering = ('-pk',)
        verbose_name = _('Revisión de catálogo académico')
        verbose_name_plural = _('Revisiones de catálogo académico')
        permissions = (('publicar_catalogo', 'Publicar catalogo academico institucional'),)

    def __str__(self):
        return f'{self.titulo} #{self.pk or "—"}'

    def clean(self):
        errores = {}
        try:
            validar_texto(self.titulo, obligatorio=True)
        except ValueError:
            errores['titulo'] = _('Usa un nombre de revisión en texto simple.')
        try:
            catalogo = catalogo_academico(self.contenido)
            relaciones = self.relaciones_reservadas
            if (not isinstance(relaciones, dict) or len(relaciones) > 4000
                    or any(not isinstance(k, str) or not isinstance(v, str) for k, v in relaciones.items())):
                raise ValueError
            if self.estado == self.Estado.PUBLICADA:
                carreras = {c for c, _, _ in catalogo.carreras} | set(dict(catalogo.carreras_historicas))
                dependencias = set(dict(catalogo.facultades)) - {'externo'}
                if any(c not in carreras or f not in dependencias for c, f in relaciones.items()):
                    raise ValueError
                if any(relaciones.get(c) != f for c, _, f in catalogo.carreras):
                    raise ValueError
        except (ValueError, TypeError):
            errores['contenido'] = _('Revisa los códigos, los nombres y las relaciones del catálogo.')
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        autorizado = kwargs.pop('_desde_editor', False)
        if not autorizado or not self._state.adding or self.pk is not None:
            raise ValidationError(_('Usa el editor; las revisiones guardadas no se pueden modificar.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))


class PublicacionCatalogoAcademico(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    revision = models.ForeignKey(RevisionCatalogoAcademico, null=True, blank=True,
                                 on_delete=models.PROTECT, related_name='+')
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='catalogo_publicacion_unica')]

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_editor', False):
            raise ValidationError(_('Usa el editor institucional.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))
