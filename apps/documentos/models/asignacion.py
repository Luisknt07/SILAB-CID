"""Referencias y escenarios archivados; no ejecutan gasto público."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .necesidades import CapturasNecesidadesQuerySet, huella_contenido


class CapturaAsignacion(models.Model):
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    registrado_en = models.DateTimeField(auto_now_add=True)
    contenido = models.JSONField(editable=False)
    sha256 = models.CharField(max_length=64, editable=False)
    objects = CapturasNecesidadesQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ['-registrado_en', '-pk']

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('El antecedente archivado no se modifica. Registra una nueva revisión.')
        if self.sha256 != huella_contenido(self.contenido):
            raise ValidationError('La huella no corresponde al antecedente.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El antecedente archivado no se elimina.')


class MarcoPresupuestoNecesidades(CapturaAsignacion):
    dependencia = models.ForeignKey('directorio_unidades.DependenciaAcademica', on_delete=models.PROTECT)
    anio_ejecucion = models.PositiveSmallIntegerField()

    class Meta(CapturaAsignacion.Meta):
        verbose_name = 'Referencia presupuestaria para necesidades'
        verbose_name_plural = 'Referencias presupuestarias para necesidades'


class EscenarioAsignacionNecesidades(CapturaAsignacion):
    remision = models.ForeignKey('documentos.RemisionNecesidades', on_delete=models.PROTECT,
                                related_name='escenarios')
    presupuesto = models.ForeignKey(MarcoPresupuestoNecesidades, on_delete=models.PROTECT,
                                   related_name='escenarios')

    class Meta(CapturaAsignacion.Meta):
        verbose_name = 'Escenario de distribución de necesidades'
        verbose_name_plural = 'Escenarios de distribución de necesidades'
