"""Estado institucional y cambios inmutables; nunca administra derechos de uso."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.persistence.publicacion import HistorialInstitucionalQuerySet


class EstadoCapacidad(models.Model):
    producto_codigo = models.CharField(max_length=250, editable=False)
    institucion_codigo = models.CharField(max_length=200, editable=False)
    modulo = models.CharField(_('Módulo'), max_length=100, editable=False)
    capacidad = models.CharField(_('Capacidad'), max_length=100, editable=False)
    habilitada = models.BooleanField(_('Habilitada'), default=True)
    version = models.PositiveBigIntegerField(_('Versión'), default=0, editable=False)
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        default_permissions = ('view',)
        permissions = (('administrar_capacidades', 'Administrar habilitacion institucional de capacidades'),)
        verbose_name = _('Habilitación institucional')
        verbose_name_plural = _('Habilitaciones institucionales')
        constraints = [models.UniqueConstraint(
            fields=('producto_codigo', 'institucion_codigo', 'modulo', 'capacidad'),
            name='habilitacion_capacidad_instalacion_unica')]

    def __str__(self):
        return f'{self.modulo}.{self.capacidad} · {self.version}'

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_control', False):
            raise ValidationError(_('Usa la administración de capacidades.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))


class CambioCapacidad(models.Model):
    estado = models.ForeignKey(EstadoCapacidad, on_delete=models.PROTECT, related_name='cambios')
    habilitada_anterior = models.BooleanField(_('Estado anterior'))
    habilitada_nueva = models.BooleanField(_('Nuevo estado'))
    version = models.PositiveBigIntegerField(_('Versión'))
    motivo = models.CharField(_('Motivo del cambio'), max_length=500)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    fecha = models.DateTimeField(_('Fecha'), auto_now_add=True)
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        ordering = ('-pk',)
        default_permissions = ('view',)
        verbose_name = _('Cambio de habilitación')
        verbose_name_plural = _('Cambios de habilitación')
        constraints = [models.UniqueConstraint(fields=('estado', 'version'), name='cambio_capacidad_version_unica')]

    def __str__(self):
        return f'{self.estado_id} · {self.version}'

    def clean(self):
        if (not isinstance(self.motivo, str) or not self.motivo.strip()
                or any(ord(c) < 32 or ord(c) == 127 or c in '<>' for c in self.motivo)):
            raise ValidationError({'motivo': _('Usa texto simple para el motivo del cambio.')})

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_control', False) or not self._state.adding or self.pk is not None:
            raise ValidationError(_('El historial institucional no se puede modificar.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))
