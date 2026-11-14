"""Contadores compartidos de abuso; no almacenan direcciones IP ni credenciales."""
from django.db import models


class ContadorPeticion(models.Model):
    clave = models.CharField(max_length=64, primary_key=True)
    total = models.PositiveIntegerField(default=1)
    vence = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'webcitt_contadorpeticion'
        verbose_name = 'Contador temporal de peticiones'
