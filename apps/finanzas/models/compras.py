"""Compras: quién abastece a las plantas y las órdenes de compra que se le emiten.

El proveedor, como el cliente, es uno solo para toda la institución —la misma lechera no se
registra dos veces porque la pidan dos plantas— y su desempeño se mide por
planta, con sus pedidos, sus entregas y los controles de recepción. La orden de
compra agrupa los pedidos de un proveedor en un documento con número: los
pedidos siguen siendo las líneas, con sus entregas y su recepción por lote.
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad


class ContraparteComercial(models.Model):
    """Lo común a proveedores y clientes: uno por nombre para toda la institución."""

    nombre = models.CharField(max_length=160)
    ruc = models.CharField('RUC o cédula', max_length=13, blank=True)
    contacto = models.CharField('Persona de contacto', max_length=160, blank=True)
    telefono = models.CharField('Teléfono', max_length=40, blank=True)
    email = models.EmailField('Correo', blank=True)
    direccion = models.CharField('Dirección', max_length=240, blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(Lower('nombre'), name='%(class)s_nombre_unico'),
        ]

    def __str__(self):
        return self.nombre

    @classmethod
    def por_nombre(cls, nombre):
        """El registro con ese nombre, sin distinguir mayúsculas ni espacios; si no existe, se crea."""
        nombre = ' '.join((nombre or '').split())[:160]
        if not nombre:
            return None
        existente = cls.objects.filter(nombre__iexact=nombre).first()
        return existente or cls.objects.create(nombre=nombre)


class Proveedor(ContraparteComercial):
    rubro = models.CharField('Qué provee', max_length=240, blank=True)

    class Meta(ContraparteComercial.Meta):
        db_table = 'webcitt_proveedor'
        ordering = ('nombre',)
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'


class OrdenCompra(models.Model):
    ESTADOS = [
        ('emitida', 'Emitida'),
        ('confirmada', 'Confirmada por el proveedor'),
        ('recibida', 'Recibida'),
        ('anulada', 'Anulada'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='ordenes_compra')
    sesion = models.ForeignKey(
        'plantas_operacion.SesionERP', on_delete=models.PROTECT, null=True, blank=True, related_name='ordenes_compra',
        help_text='La sesión de práctica donde se registró; sin sesión, es producción real.',
    )
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_compra')
    fecha_emision = models.DateField(default=timezone.localdate, db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='emitida', db_index=True)
    condiciones = models.TextField(
        'Condiciones de entrega y pago', blank=True,
        help_text='Lo que el proveedor debe cumplir: cadena de frío, documentos de la entrega, forma de pago.',
    )
    emitida_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_compra_emitidas',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_ordencompra'
        ordering = ('-fecha_emision', '-pk')
        verbose_name = 'Orden de compra'
        verbose_name_plural = 'Órdenes de compra'

    def __str__(self):
        return f'{self.codigo or self.pk} · {self.proveedor}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'OC{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])

    @property
    def total(self):
        # Un pedido anulado después de emitir deja de contar en la orden.
        return sum((pedido.costo_total for pedido in self.pedidos.all() if pedido.estado != 'cancelado'), 0)

    def actualizar_estado_por_pedidos(self):
        """Recibidos todos sus pedidos, la orden está recibida."""
        if self.estado in ('anulada', 'recibida'):
            return
        pedidos = list(self.pedidos.exclude(estado='cancelado'))
        if pedidos and all(pedido.estado == 'recibido' for pedido in pedidos):
            self.estado = 'recibida'
            self.save(update_fields=['estado', 'actualizado_en'])
