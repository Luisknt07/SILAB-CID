"""Ventas: a quién despacha la planta.

El cliente es uno solo para la institución, como el proveedor: la misma
tienda no se registra dos veces porque le vendan dos plantas. Cada salida de
producto puede llevar su cliente, y con él la planta sabe a quién despachó cada
lote y a qué temperatura salió.
"""

from django.db import models

from apps.finanzas.models.compras import ContraparteComercial


class Cliente(ContraparteComercial):
    TIPOS = [
        ('persona', 'Persona'),
        ('comercio', 'Comercio o empresa'),
        ('institucion', 'Institución'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS, default='persona')

    class Meta(ContraparteComercial.Meta):
        db_table = 'webcitt_cliente'
        ordering = ('nombre',)
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
