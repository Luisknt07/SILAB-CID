"""Segundo factor de una cuenta que entra al administrador."""
from django.conf import settings
from django.db import models


class SegundoFactor(models.Model):
    """Secreto de la aplicación autenticadora de una persona y el estado de su uso.

    El secreto se guarda cifrado y los códigos de respaldo, solo como huella.
    Mientras ``confirmado_en`` está vacío el alta sigue pendiente: aún no se
    demostró que la aplicación genera códigos válidos.
    """

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='segundo_factor')
    secreto_cifrado = models.TextField(editable=False)
    confirmado_en = models.DateTimeField(null=True, blank=True, editable=False)
    # Paso de tiempo del último código aceptado: un código no se usa dos veces.
    ultimo_paso = models.BigIntegerField(null=True, blank=True, editable=False)
    fallos = models.PositiveSmallIntegerField(default=0, editable=False)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, editable=False)
    codigos_respaldo = models.JSONField(default=list, blank=True, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Segundo factor'
        verbose_name_plural = 'Segundos factores'

    def __str__(self):
        estado = 'activo' if self.confirmado_en else 'pendiente'
        return f'Segundo factor de {self.usuario} ({estado})'
