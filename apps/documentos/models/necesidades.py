"""Capturas inmutables de las necesidades remitidas a cada dependencia."""
import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def contenido_canonico(contenido):
    """Una representación estable para verificar la captura y evitar duplicados."""
    if not isinstance(contenido, dict):
        raise ValidationError('La remisión debe conservar un informe estructurado.')
    try:
        return json.dumps(contenido, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as error:
        raise ValidationError('El contenido de la remisión no es una captura válida.') from error


def huella_contenido(contenido):
    return hashlib.sha256(contenido_canonico(contenido)).hexdigest()


class CapturasNecesidadesQuerySet(models.QuerySet):
    """La remisión es un antecedente: cada envío produce otra captura."""

    def update(self, **kwargs):
        raise ValidationError('Una remisión archivada no se modifica.')

    def delete(self):
        raise ValidationError('Una remisión archivada no se elimina.')

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError('Una remisión archivada no se modifica.')

    def bulk_create(self, objs, **kwargs):
        raise ValidationError('Las remisiones se archivan individualmente desde el informe evaluado.')


class RemisionNecesidades(models.Model):
    dependencia = models.ForeignKey('directorio_unidades.DependenciaAcademica',
        on_delete=models.PROTECT, related_name='remisiones_necesidades')
    dependencia_nombre = models.CharField(max_length=220)
    anio_preparacion = models.PositiveSmallIntegerField()
    anio_ejecucion = models.PositiveSmallIntegerField()
    remitido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='remisiones_necesidades')
    remitido_en = models.DateTimeField(auto_now_add=True)
    destinatarios = models.JSONField(default=list, editable=False)
    contenido = models.JSONField(editable=False)
    sha256 = models.CharField(max_length=64, editable=False)

    objects = CapturasNecesidadesQuerySet.as_manager()

    class Meta:
        ordering = ['-remitido_en', '-pk']
        verbose_name = 'Remisión de necesidades'
        verbose_name_plural = 'Remisiones de necesidades'
        constraints = [models.UniqueConstraint(fields=['dependencia', 'anio_preparacion', 'sha256'],
            name='remision_necesidades_captura_unica')]

    def __str__(self):
        return f'{self.dependencia_nombre} · Necesidades {self.anio_ejecucion}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Una remisión archivada no se modifica; prepara otra remisión.')
        if (type(self.anio_preparacion) is not int or type(self.anio_ejecucion) is not int
                or self.anio_ejecucion != self.anio_preparacion + 1):
            raise ValidationError('El año de ejecución debe ser el siguiente al de preparación.')
        if self.sha256 != huella_contenido(self.contenido):
            raise ValidationError('La huella no corresponde al contenido de la remisión.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Una remisión archivada no se elimina.')
