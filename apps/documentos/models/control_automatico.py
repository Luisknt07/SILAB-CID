"""Último control automático; el historial detallado permanece en auditoría."""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class ControlAutomaticoDocumento(models.Model):
    ESTADOS = [('automatico', 'Comprobado automáticamente'), ('revision', 'Requiere revisión'),
               ('bloqueado', 'Bloqueado por inconsistencias'), ('sin_archivo', 'Sin archivo')]
    documento = models.OneToOneField('documentos.DocumentoExpediente', on_delete=models.CASCADE,
                                    related_name='control_automatico')
    metodo = models.CharField(max_length=80)
    version_documento = models.PositiveSmallIntegerField(default=0)
    recurso = models.ForeignKey('recursos.Recurso', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='controles_automaticos_documentales')
    sha256 = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='sin_archivo', db_index=True)
    hallazgos = models.JSONField(default=list, blank=True)
    resumen = models.JSONField(default=dict, blank=True)
    fuentes_sha256 = models.CharField(max_length=64, blank=True)
    comprobado_en = models.DateTimeField(default=timezone.now)
    aplicado = models.BooleanField(default=False)
    nota = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    politica = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Control automático del documento'
        verbose_name_plural = 'Controles automáticos de documentos'
        constraints = [models.CheckConstraint(condition=models.Q(nota__isnull=True) |
            (models.Q(nota__gte=0) & models.Q(nota__lte=100)), name='control_automatico_nota_porcentaje')]

    def clean(self):
        super().clean()
        errores = {}
        for campo, tipo in (('hallazgos', list), ('resumen', dict), ('politica', dict)):
            if not isinstance(getattr(self, campo), tipo):
                errores[campo] = 'El control debe conservar su estructura de datos original.'
        if self.recurso_id and self.documento_id and self.recurso.unidad_id != self.documento.unidad_id:
            errores['recurso'] = 'El recurso y el documento deben pertenecer a la misma unidad.'
        if errores:
            raise ValidationError(errores)
