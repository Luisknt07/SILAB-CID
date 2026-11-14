"""Versiones emitidas para aprobación en la plataforma y verificación por QR."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ConstanciaDocumento(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    documento = models.ForeignKey('documentos.DocumentoExpediente', on_delete=models.PROTECT, related_name='constancias')
    recurso = models.OneToOneField('recursos.Recurso', on_delete=models.PROTECT, related_name='constancia_documental')
    version = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    titulo = models.CharField(max_length=300)
    unidad_nombre = models.CharField(max_length=250)
    periodo = models.CharField(max_length=120)
    emitido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    emisor_nombre = models.CharField(max_length=250)
    emisor_cedula = models.CharField(max_length=20, blank=True, editable=False)
    emitido_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    aprobado_en = models.DateTimeField(null=True, blank=True)
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    aprobador_nombre = models.CharField(max_length=250, blank=True)
    aprobador_cedula = models.CharField(max_length=20, blank=True, editable=False)
    observado_en = models.DateTimeField(null=True, blank=True)
    archivo_aprobado = models.FileField(upload_to='documentos/aprobaciones/', blank=True, editable=False)
    sha256_aprobado = models.CharField(max_length=64, blank=True, editable=False)
    contenido_emitido = models.JSONField(default=dict, blank=True, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['documento', 'version'], name='constancia_documento_version_unica')]

    def save(self, *args, **kwargs):
        if self.pk:
            anterior = type(self).objects.get(pk=self.pk)
            campos = ('token', 'documento_id', 'recurso_id', 'version', 'sha256', 'titulo', 'unidad_nombre',
                      'periodo', 'emitido_por_id', 'emisor_nombre', 'emisor_cedula', 'emitido_en', 'contenido_emitido')
            if any(getattr(self, c) != getattr(anterior, c) for c in campos):
                raise ValidationError('La identidad de una versión emitida no se modifica.')
            if anterior.archivo_aprobado and (self.archivo_aprobado.name != anterior.archivo_aprobado.name
                    or self.sha256_aprobado != anterior.sha256_aprobado
                    or self.aprobado_por_id != anterior.aprobado_por_id
                    or self.aprobador_nombre != anterior.aprobador_nombre
                    or self.aprobador_cedula != anterior.aprobador_cedula
                    or self.aprobado_en != anterior.aprobado_en):
                raise ValidationError('La copia aprobada se conserva sin modificaciones.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('La constancia conserva la trazabilidad de la versión.')


class PresentacionDocumento(models.Model):
    """Copias de presentación; conserva las descargas anteriores y su verificación."""
    constancia = models.ForeignKey(ConstanciaDocumento, on_delete=models.PROTECT, related_name='presentaciones')
    formato = models.PositiveSmallIntegerField()
    aprobada = models.BooleanField(default=True, editable=False)
    archivo = models.FileField(upload_to='documentos/presentaciones/', editable=False)
    sha256 = models.CharField(max_length=64, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['constancia', 'formato', 'aprobada'], name='presentacion_constancia_formato_estado_unica')]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('La copia de presentación se conserva sin modificaciones.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('La copia de presentación conserva la verificación del archivo.')
