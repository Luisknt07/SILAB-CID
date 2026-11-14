"""Avisos del expediente, aislados de las notificaciones de reservas."""
from django.conf import settings
from django.db import models


class AvisoDocumental(models.Model):
    TIPOS = [('recordatorio', 'Recordatorio de entrega'), ('apertura', 'Preparación del cierre'),
             ('ultimatum', 'Ultimátum de entrega'), ('evaluacion', 'Evaluación por no entrega')]
    tipo = models.CharField(max_length=20, choices=TIPOS, default='recordatorio')
    documento = models.ForeignKey('documentos.DocumentoExpediente', on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plazo = models.DateTimeField()
    horas = models.PositiveSmallIntegerField()
    titulo = models.CharField(max_length=180)
    mensaje = models.TextField()
    url = models.CharField(max_length=500)
    leida = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    email_enviado = models.BooleanField(default=False)
    sms_enviado = models.BooleanField(default=False)
    intentos = models.PositiveSmallIntegerField(default=0)
    ultimo_intento = models.DateTimeField(null=True, blank=True)
    error_email = models.TextField(blank=True)
    error_sms = models.TextField(blank=True)

    class Meta:
        db_table = 'webcitt_avisodocumental'
        constraints = [models.UniqueConstraint(fields=['documento', 'usuario', 'plazo', 'horas'],
                                               name='aviso_documental_unico')]
        ordering = ['-creada_en', '-pk']


class UltimatumDocumental(models.Model):
    exigido = models.ForeignKey('documentos.DocumentoExigido', on_delete=models.PROTECT)
    anio = models.PositiveSmallIntegerField()
    corte = models.CharField(max_length=1, blank=True)
    mes = models.PositiveSmallIntegerField(default=0)
    hasta = models.DateTimeField()
    motivo = models.TextField()
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_ultimatumdocumental'
        constraints = [models.UniqueConstraint(fields=['exigido', 'anio', 'corte', 'mes'],
                                               name='ultimatum_documental_unico')]
