from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.persistence.publicacion import HistorialInstitucionalQuerySet
from .contracts import validar_contenido
from apps.core.presentation.capacidades import con_capacidad_bloqueada


class RevisionInicio(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'borrador', _('Borrador')
        PUBLICADA = 'publicada', _('Publicada')

    titulo = models.CharField(_('Nombre de la revisión'), max_length=200)
    contenido = models.JSONField(_('Contenido bilingüe'))
    institucion_codigo = models.CharField(max_length=200, editable=False)
    producto_codigo = models.CharField(max_length=250, editable=False)
    estado = models.CharField(_('Estado'), max_length=10, choices=Estado.choices, editable=False)
    basada_en = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='+', editable=False)
    fuente = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                              related_name='+', editable=False)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name='+', editable=False)
    fecha = models.DateTimeField(_('Fecha'), auto_now_add=True)
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        ordering = ('-pk',)
        default_permissions = ('add', 'view')
        verbose_name = _('Portada de Inicio')
        verbose_name_plural = _('Portadas de Inicio')
        permissions = (('publicar_inicio', 'Publicar portada de Inicio'),)

    def __str__(self):
        return f'{self.titulo} · {self.get_estado_display()} #{self.pk or "—"}'

    def clean(self):
        try:
            self.contenido = validar_contenido(self.contenido)
        except ValueError as exc:
            raise ValidationError({'contenido': _(str(exc))}) from exc
        if (not isinstance(self.titulo, str) or not self.titulo.strip()
                or any(ord(c) < 32 or ord(c) == 127 or c in '<>' for c in self.titulo)):
            raise ValidationError({'titulo': _('Usa texto simple para el nombre de la revisión.')})

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_editor', False) or not self._state.adding or self.pk is not None:
            raise ValidationError(_('Usa el editor; las revisiones guardadas no se pueden modificar.'))
        with con_capacidad_bloqueada('portal', 'portada_inicio'):
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))


class PublicacionInicio(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    revision = models.ForeignKey(RevisionInicio, null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='+')
    objects = HistorialInstitucionalQuerySet.as_manager()

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='portal_inicio_publicacion_unica')]

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_editor', False):
            raise ValidationError(_('Usa el editor institucional.'))
        with con_capacidad_bloqueada('portal', 'portada_inicio'):
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))
