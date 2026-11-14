"""El almacén: contar lo que hay y cuadrarlo con lo que el sistema dice.

Un conteo cíclico congela lo que el sistema cree tener de cada lote, el
bodeguero anota lo que encuentra en el estante, y al cerrarlo cada diferencia
entra al kardex como un ajuste con su nombre y su responsable. Lo que no se
cuenta no se ajusta: una línea sin contar queda como estaba.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.directorio_unidades.models.core import Unidad


class ConteoInventario(models.Model):
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('cerrado', 'Cerrado'),
        ('anulado', 'Anulado'),
    ]
    ALCANCES = [
        ('todo', 'Todo el almacén'),
        ('bodega', 'Una bodega'),
        ('clasificacion', 'Una clasificación'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='conteos_inventario')
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    nombre = models.CharField(max_length=160)
    alcance = models.CharField(max_length=20, choices=ALCANCES, default='todo')
    referencia = models.CharField(
        max_length=120, blank=True, help_text='La bodega o la clasificación que se cuenta, si el alcance lo acota.',
    )
    fecha = models.DateField(default=timezone.localdate, db_index=True)
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conteos_inventario',
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierto', db_index=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    cerrado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webcitt_conteoinventario'
        ordering = ('-fecha', '-pk')
        verbose_name = 'Conteo cíclico del almacén'
        verbose_name_plural = 'Conteos cíclicos del almacén'

    def __str__(self):
        return f'{self.codigo or self.pk} · {self.nombre}'

    @property
    def abierto(self):
        return self.estado == 'abierto'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'CI{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])


class LineaConteo(models.Model):
    conteo = models.ForeignKey(ConteoInventario, on_delete=models.CASCADE, related_name='lineas')
    lote = models.ForeignKey(LoteConsumible, on_delete=models.PROTECT, related_name='lineas_conteo')
    consumible = models.ForeignKey(Consumible, on_delete=models.PROTECT, related_name='lineas_conteo')
    cantidad_sistema = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_contada = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    ajuste = models.ForeignKey(
        EntradaInventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='lineas_conteo',
    )
    observaciones = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = 'webcitt_lineaconteo'
        unique_together = ('conteo', 'lote')
        ordering = ('consumible__nombre', 'lote__codigo', 'pk')
        verbose_name = 'Línea de un conteo'
        verbose_name_plural = 'Líneas de los conteos'

    def __str__(self):
        return f'{self.lote.codigo} · {self.cantidad_sistema}'

    @property
    def contada(self):
        return self.cantidad_contada is not None

    @property
    def diferencia(self):
        if self.cantidad_contada is None:
            return None
        return Decimal(self.cantidad_contada) - Decimal(self.cantidad_sistema)

    @property
    def cuadra(self):
        return self.diferencia == 0 if self.contada else None

    def clean(self):
        super().clean()
        errores = {}
        if self.cantidad_contada is not None and self.cantidad_contada < 0:
            errores['cantidad_contada'] = 'Lo contado no puede ser negativo.'
        if self.conteo_id and self.consumible_id and self.consumible.unidad_id != self.conteo.unidad_id:
            errores['consumible'] = 'El insumo debe pertenecer a la unidad del conteo.'
        if self.lote_id and self.consumible_id and self.lote.consumible_id != self.consumible_id:
            errores['lote'] = 'El lote debe corresponder al insumo contado.'
        if self.ajuste_id and (
            self.ajuste.consumible_id != self.consumible_id or self.ajuste.lote_inventario_id != self.lote_id
            or (self.conteo_id and self.ajuste.unidad_id != self.conteo.unidad_id)
        ):
            errores['ajuste'] = 'El ajuste debe corresponder a la unidad, el insumo y el lote contados.'
        if errores:
            raise ValidationError(errores)
