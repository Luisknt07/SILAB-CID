"""Decisiones institucionales conservadas aparte de los datos declarados."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class HistorialVerificacionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError(_('El historial de verificación no se puede modificar.'))

    def delete(self):
        raise ValidationError(_('El historial de verificación no se puede modificar.'))

    def bulk_create(self, objs, **kwargs):
        raise ValidationError(_('Registra cada decisión desde la revisión institucional.'))


class VerificacionInstitucional(models.Model):
    class Decision(models.TextChoices):
        APROBADA = 'aprobada', _('Aprobada')
        RECHAZADA = 'rechazada', _('Rechazada')
        REVOCADA = 'revocada', _('Revocada')

    perfil = models.ForeignKey(
        'core.UserProfile', on_delete=models.PROTECT,
        related_name='verificaciones_institucionales', verbose_name=_('Perfil'),
    )
    revisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='verificaciones_realizadas', verbose_name=_('Revisor'),
    )
    decision = models.CharField(max_length=10, choices=Decision.choices, verbose_name=_('Decisión'))
    identidad_revisada = models.JSONField(verbose_name=_('Identidad revisada'))
    fundamento = models.TextField(max_length=2000, verbose_name=_('Fundamento de la revisión'))
    referencia = models.CharField(max_length=250, verbose_name=_('Referencia de la evidencia'))
    vigente_hasta = models.DateField(null=True, blank=True, verbose_name=_('Vigente hasta'))
    fecha = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha'))

    objects = HistorialVerificacionQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_verificacioninstitucional'
        ordering = ('-fecha', '-pk')
        verbose_name = _('Verificación institucional')
        verbose_name_plural = _('Verificaciones institucionales')
        permissions = (
            ('revisar_pertenencia_institucional', 'Revisar pertenencia institucional'),
        )

    def __str__(self):
        return f'{self.perfil_id}: {self.get_decision_display()}'

    def save(self, *args, **kwargs):
        desde_revision = kwargs.pop('_desde_revision', False)
        if not self._state.adding or self.pk is not None:
            raise ValidationError(_('El historial de verificación no se puede modificar.'))
        if not desde_revision:
            raise ValidationError(_('Registra cada decisión desde la revisión institucional.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial de verificación no se puede modificar.'))
