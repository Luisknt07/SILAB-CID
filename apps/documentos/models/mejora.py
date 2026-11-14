"""Remisión y seguimiento de una versión concreta del informe de mejora."""

from django.conf import settings
from django.db import models


class InformeMejora(models.Model):
    DECISIONES = [('continuidad', 'Continuidad con plan de mejora'),
                  ('rediseno', 'Rediseño'), ('cierre', 'Cierre')]
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.PROTECT, related_name='informes_mejora')
    recurso = models.OneToOneField('recursos.Recurso', on_delete=models.PROTECT, related_name='informe_mejora')
    anio = models.PositiveSmallIntegerField()
    corte = models.CharField(max_length=1, blank=True, choices=[('', 'Anual'), ('A', 'A'), ('B', 'B')])
    dependencia = models.ForeignKey('directorio_unidades.DependenciaAcademica', on_delete=models.PROTECT, null=True)
    destinatarios = models.JSONField(default=list, blank=True)
    remitido_en = models.DateTimeField(null=True, blank=True)
    remitido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    null=True, related_name='+')
    recibido_en = models.DateTimeField(null=True, blank=True)
    recibido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    null=True, related_name='+')
    decision = models.CharField(max_length=12, choices=DECISIONES, blank=True)
    motivo = models.TextField(blank=True)
    decidido_en = models.DateTimeField(null=True, blank=True)
    decidido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    null=True, related_name='+')

    class Meta:
        db_table = 'webcitt_informemejora'
        ordering = ['-anio', 'corte', '-pk']
        verbose_name = 'Informe de mejora'
        verbose_name_plural = 'Remisión y seguimiento de mejora'
        constraints = [models.UniqueConstraint(fields=['unidad', 'anio', 'corte'],
                       condition=models.Q(remitido_en__isnull=False), name='mejora_remision_periodo_unico')]

    def __str__(self):
        return f'{self.unidad} · {self.anio}{self.corte} · {self.estado}'

    @property
    def estado(self):
        if self.decidido_en:
            return 'Resuelto'
        if self.recibido_en:
            return 'Recibido'
        if self.remitido_en:
            return 'Remitido'
        return 'Archivado, pendiente de remisión'


class AccionMejora(models.Model):
    informe = models.ForeignKey(InformeMejora, on_delete=models.PROTECT, related_name='acciones')
    descripcion = models.TextField()
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    vence_el = models.DateField()
    creada_en = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    cerrada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webcitt_accionmejora'
        ordering = ['vence_el', 'pk']
        verbose_name = 'Acción de mejora'
        verbose_name_plural = 'Acciones de mejora'


class SeguimientoMejora(models.Model):
    accion = models.ForeignKey(AccionMejora, on_delete=models.PROTECT, related_name='seguimientos')
    detalle = models.TextField()
    cierre = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta:
        db_table = 'webcitt_seguimientomejora'
        ordering = ['creado_en', 'pk']
        verbose_name = 'Seguimiento de mejora'
        verbose_name_plural = 'Seguimientos de mejora'
