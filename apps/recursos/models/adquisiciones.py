"""Solicitudes de un recurso de referencia, separadas del inventario existente."""
import uuid
from django.conf import settings
from django.db import models


class SolicitudAdquisicionRecurso(models.Model):
    ESTADOS = [('solicitada', 'Solicitada'), ('aprobada', 'Aprobada'),
               ('comprada', 'Compra documentada'), ('recibida', 'Recibida y habilitada')]
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.PROTECT)
    equipo = models.ForeignKey('recursos.UnidadEquipo', null=True, blank=True, on_delete=models.PROTECT)
    software = models.ForeignKey('recursos.SoftwareDisponible', null=True, blank=True, on_delete=models.PROTECT)
    consumible = models.ForeignKey('recursos.Consumible', null=True, blank=True, on_delete=models.PROTECT)
    documento = models.ForeignKey('documentos.DocumentoExpediente', on_delete=models.PROTECT)
    necesidad = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='solicitada')
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    contenido_aprobado = models.JSONField(default=dict, blank=True)
    referencia_compra = models.CharField(max_length=200, blank=True)
    referencia_recepcion = models.CharField(max_length=200, blank=True)
    solicitada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    aprobada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    recibida_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(
            models.Q(equipo__isnull=False, software__isnull=True, consumible__isnull=True)
            | models.Q(equipo__isnull=True, software__isnull=False, consumible__isnull=True)
            | models.Q(equipo__isnull=True, software__isnull=True, consumible__isnull=False)), name='adquisicion_un_recurso'),
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='adquisicion_cantidad_positiva')]

    @property
    def recurso(self):
        return self.equipo or self.software or self.consumible


def validar_habilitacion(recurso):
    """Una solicitud pendiente no se salta con el interruptor ni con otro editor."""
    from django.core.exceptions import ValidationError
    campo = {'unidadequipo': 'equipo', 'softwaredisponible': 'software', 'consumible': 'consumible'}.get(recurso._meta.model_name)
    activo = getattr(recurso, 'activa', getattr(recurso, 'activo', False))
    if campo and recurso.pk and activo and SolicitudAdquisicionRecurso.objects.filter(
            **{campo: recurso}, estado__in=['solicitada', 'aprobada', 'comprada']).exists():
        raise ValidationError('Este recurso está en adquisición: documenta la compra y su recepción para habilitarlo.')
