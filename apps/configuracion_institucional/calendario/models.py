"""Historial de calendario y sus límites sin reescribir clasificaciones operativas."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.calendario import politica_calendario
from apps.core.identidad import validar_texto
from ..versionado import HistorialInstitucionalQuerySet


class RevisionPoliticaCalendario(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'borrador', _('Borrador')
        PUBLICADA = 'publicada', _('Publicada')

    titulo = models.CharField(_('Nombre de la revisión'), max_length=100)
    institucion_codigo = models.CharField(max_length=200, editable=False)
    producto_codigo = models.CharField(max_length=250, editable=False)
    contenido = models.JSONField(_('Política de calendario'))
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
        verbose_name = _('Revisión de política de calendario')
        verbose_name_plural = _('Revisiones de política de calendario')
        permissions = (('publicar_calendario', 'Publicar politica de calendario institucional'),)

    def __str__(self):
        return f'{self.titulo} #{self.pk or "—"}'

    def clean(self):
        errores = {}
        try:
            validar_texto(self.titulo, obligatorio=True)
        except ValueError:
            errores['titulo'] = _('Usa un nombre de revisión en texto simple.')
        try:
            politica_calendario(self.contenido)
        except (ValueError, TypeError):
            errores['contenido'] = _('Revisa los ciclos, los ámbitos y las semanas.')
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        autorizado = kwargs.pop('_desde_editor', False)
        if not autorizado or not self._state.adding or self.pk is not None:
            raise ValidationError(_('Usa el editor; las revisiones guardadas no se pueden modificar.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))


class PublicacionPoliticaCalendario(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    revision = models.ForeignKey(RevisionPoliticaCalendario, null=True, blank=True,
                                 on_delete=models.PROTECT, related_name='+')
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='calendario_publicacion_unica')]

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_editor', False):
            raise ValidationError(_('Usa el editor institucional.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))
