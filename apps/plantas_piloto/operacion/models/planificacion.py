"""Planificación: qué producir, qué pedir y cuándo.

El plan maestro dice qué corridas hará la unidad cada día del período. De él
sale la explosión de materiales: lo que las recetas piden, menos lo que ya
está en bodega y lo que ya viene en camino, deja lo que falta pedir y la fecha
en que hay que pedirlo. Un pedido de abastecimiento lleva sus entregas, porque
la leche cruda no llega toda de una vez: llega cada día de proceso, y cada
entrega recibida entra al inventario como su lote.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.plantas_piloto.domain.planificacion import (
    cantidad_planificada,
    demanda_no_comprometida,
    equivalente_base,
)

from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.directorio_unidades.models.core import Unidad
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, Producto, Receta
from apps.reservas.models.reservas import Reserva


def _decimal(valor):
    return Decimal(valor).quantize(Decimal('0.001'))


class PlanMaestro(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('firme', 'Firme'),
        ('cerrado', 'Cerrado'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='planes_maestros')
    responsable = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad', on_delete=models.SET_NULL, null=True, blank=True, related_name='planes_a_cargo',
        help_text='Quien responde por el plan del período y sus corridas.',
    )
    sesion = models.ForeignKey(
        'plantas_operacion.SesionERP', on_delete=models.PROTECT, null=True, blank=True, related_name='planes_maestros',
        help_text='La sesión de práctica donde se registró; sin sesión, es producción real.',
    )
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    nombre = models.CharField(max_length=160)
    desde = models.DateField(db_index=True)
    hasta = models.DateField(db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador', db_index=True)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='planes_maestros',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_planmaestro'
        ordering = ('-desde', '-pk')
        verbose_name = 'Plan maestro de producción'
        verbose_name_plural = 'Planes maestros de producción'

    def __str__(self):
        return f'{self.codigo or self.nombre} · {self.desde:%d/%m/%Y} a {self.hasta:%d/%m/%Y}'

    @property
    def abierto(self):
        return self.estado != 'cerrado'

    @property
    def dias(self):
        return (self.hasta - self.desde).days + 1

    def fechas(self):
        return [self.desde + timedelta(days=paso) for paso in range(self.dias)]

    def clean(self):
        super().clean()
        errores = {}
        if self.desde and self.hasta:
            if self.hasta < self.desde:
                errores['hasta'] = 'El plan termina el mismo día que empieza o después.'
            elif (self.hasta - self.desde).days > 180:
                errores['hasta'] = 'Un plan maestro cubre a lo sumo seis meses.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'PM{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])


class PlanVentas(models.Model):
    """Demanda aprobada del período antes de convertirla en corridas."""

    PERIODICIDADES = [
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    ]
    METODOS = [
        ('promedio_movil_3', 'Promedio móvil de tres períodos'),
        ('manual', 'Estimación manual'),
    ]
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('aprobado', 'Aprobado'),
        ('cerrado', 'Cerrado'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='planes_ventas')
    sesion = models.ForeignKey(
        'plantas_operacion.SesionERP', on_delete=models.PROTECT, null=True, blank=True, related_name='planes_ventas',
        help_text='La sesión de práctica donde se registró; sin sesión, es producción real.',
    )
    plan_maestro = models.OneToOneField(
        PlanMaestro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plan_ventas',
        help_text='Plan maestro que recibe la demanda aprobada sin duplicar recetas ni órdenes.',
    )
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    nombre = models.CharField(max_length=160)
    desde = models.DateField(db_index=True)
    hasta = models.DateField(db_index=True)
    periodicidad = models.CharField(max_length=20, choices=PERIODICIDADES, default='semanal')
    metodo = models.CharField(max_length=30, choices=METODOS, default='promedio_movil_3')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador', db_index=True)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='planes_ventas_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_planventas'
        ordering = ('-desde', '-pk')
        verbose_name = 'Plan de ventas y demanda'
        verbose_name_plural = 'Planes de ventas y demanda'

    def __str__(self):
        return f'{self.codigo or self.nombre} · {self.desde:%d/%m/%Y} a {self.hasta:%d/%m/%Y}'

    @property
    def abierto(self):
        return self.estado != 'cerrado'

    def clean(self):
        super().clean()
        errores = {}
        if self.unidad_id and self.unidad.dependencia != 'plantas_piloto':
            errores['unidad'] = 'El plan de ventas pertenece únicamente a una planta piloto.'
        if self.desde and self.hasta:
            if self.hasta < self.desde:
                errores['hasta'] = 'El plan termina el mismo día que empieza o después.'
            elif (self.hasta - self.desde).days > 180:
                errores['hasta'] = 'Un plan de ventas cubre a lo sumo seis meses.'
        if self.plan_maestro_id:
            if self.unidad_id and self.plan_maestro.unidad_id != self.unidad_id:
                errores['plan_maestro'] = 'El plan maestro debe pertenecer a la misma planta.'
            elif self.desde and self.hasta and not (
                self.plan_maestro.desde <= self.desde <= self.hasta <= self.plan_maestro.hasta
            ):
                errores['plan_maestro'] = 'El plan maestro debe cubrir todo el horizonte de ventas.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'PV{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])


class LineaPlanVentas(models.Model):
    """Demanda de un producto en una semana o mes, con sus fuentes visibles."""

    plan = models.ForeignKey(PlanVentas, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name='lineas_plan_ventas', editable=False,
    )
    receta = models.ForeignKey(Receta, on_delete=models.PROTECT, related_name='lineas_plan_ventas')
    periodo_inicio = models.DateField(db_index=True)
    periodo_fin = models.DateField(db_index=True)
    historico_promedio = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0'))
    pronostico = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    compromisos = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    docencia = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    ajuste_manual = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0'))
    cantidad_planificada = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0'), editable=False,
    )
    observaciones = models.CharField(max_length=240, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_lineaplanventas'
        ordering = ('periodo_inicio', 'producto__nombre', 'pk')
        verbose_name = 'Línea del plan de ventas'
        verbose_name_plural = 'Líneas del plan de ventas'
        constraints = [
            models.UniqueConstraint(
                fields=('plan', 'producto', 'periodo_inicio'),
                name='plan_ventas_producto_periodo_unico',
            ),
            models.CheckConstraint(
                check=models.Q(periodo_fin__gte=models.F('periodo_inicio')),
                name='linea_plan_ventas_periodo_valido',
            ),
        ]

    def __str__(self):
        return f'{self.plan.codigo} · {self.producto.nombre} · {self.periodo_inicio:%d/%m/%Y}'

    @property
    def demanda_no_comprometida(self):
        return demanda_no_comprometida(self.pronostico, self.ajuste_manual)

    @property
    def equivalente_base(self):
        return equivalente_base(
            self.cantidad_planificada,
            self.receta.rendimiento_esperado,
            self.receta.cantidad_base,
        )

    @property
    def valor_estimado(self):
        return (Decimal(self.cantidad_planificada) * Decimal(self.producto.precio_venta or 0)).quantize(
            Decimal('0.01')
        )

    def clean(self):
        super().clean()
        errores = {}
        if self.plan_id and self.periodo_inicio and self.periodo_fin and not (
            self.plan.desde <= self.periodo_inicio <= self.periodo_fin <= self.plan.hasta
        ):
            errores['periodo_inicio'] = 'El período de demanda debe estar dentro del plan de ventas.'
        if self.plan_id and self.receta_id and self.receta.unidad_id != self.plan.unidad_id:
            errores['receta'] = 'El proceso debe pertenecer a la misma planta.'
        if self.receta_id and not self.receta.activa:
            errores['receta'] = 'El proceso elegido no está activo.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.receta_id:
            self.producto = self.receta.producto
        self.cantidad_planificada = cantidad_planificada(
            self.pronostico,
            self.compromisos,
            self.docencia,
            self.ajuste_manual,
        )
        super().save(*args, **kwargs)


class LineaPlanMaestro(models.Model):
    ORIGENES = [
        ('demanda', 'Demanda estimada'),
        ('maquila', 'Encargo de un cliente'),
        ('docencia', 'Práctica programada'),
        ('stock', 'Reposición de existencias'),
    ]

    plan = models.ForeignKey(PlanMaestro, on_delete=models.CASCADE, related_name='lineas')
    receta = models.ForeignKey(Receta, on_delete=models.PROTECT, related_name='lineas_plan')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lineas_plan', editable=False)
    fecha = models.DateField(db_index=True)
    factor = models.DecimalField(
        max_digits=8, decimal_places=3, default=Decimal('1'), validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Cuántas corridas base de la receta se harán ese día.',
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, editable=False, default=Decimal('0'))
    origen = models.CharField(max_length=20, choices=ORIGENES, default='demanda', db_index=True)
    reserva = models.ForeignKey(
        Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='lineas_plan',
        help_text='El encargo o la práctica que esta corrida atiende, si la hay.',
    )
    linea_ventas = models.OneToOneField(
        LineaPlanVentas,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linea_maestra',
        help_text='Demanda abierta del plan de ventas que originó esta corrida, si aplica.',
    )
    orden = models.OneToOneField(
        OrdenProduccion, on_delete=models.SET_NULL, null=True, blank=True, related_name='linea_plan',
    )
    observaciones = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = 'webcitt_lineaplanmaestro'
        ordering = ('fecha', 'pk')
        verbose_name = 'Línea del plan maestro'
        verbose_name_plural = 'Líneas del plan maestro'

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y} · {self.receta.nombre} × {self.factor}'

    @property
    def horas(self):
        return _decimal(Decimal(self.receta.duracion_horas) * Decimal(self.factor))

    def clean(self):
        super().clean()
        errores = {}
        if self.plan_id and self.fecha and not (self.plan.desde <= self.fecha <= self.plan.hasta):
            errores['fecha'] = 'La corrida cae fuera del período del plan.'
        if self.plan_id and self.receta_id and self.receta.unidad_id != self.plan.unidad_id:
            errores['receta'] = 'El proceso es de otra unidad.'
        if self.linea_ventas_id:
            if self.linea_ventas.plan.plan_maestro_id != self.plan_id:
                errores['linea_ventas'] = 'La demanda debe estar vinculada con este plan maestro.'
            elif self.receta_id and self.linea_ventas.receta_id != self.receta_id:
                errores['receta'] = 'La corrida debe usar el proceso aprobado en el plan de ventas.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.receta_id:
            self.producto = self.receta.producto
            self.cantidad = _decimal(Decimal(self.receta.rendimiento_esperado) * Decimal(self.factor))
        super().save(*args, **kwargs)


class PedidoAbastecimiento(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('enviado', 'Enviado al proveedor'),
        ('confirmado', 'Confirmado'),
        ('recibido', 'Recibido'),
        ('cancelado', 'Cancelado'),
    ]
    # Lo que ya se comprometió con el proveedor cuenta como existencia en camino.
    ESTADOS_EN_CAMINO = ('enviado', 'confirmado')

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='pedidos_abastecimiento')
    sesion = models.ForeignKey(
        'plantas_operacion.SesionERP', on_delete=models.PROTECT, null=True, blank=True, related_name='pedidos',
        help_text='La sesión de práctica donde se registró; sin sesión, es producción real.',
    )
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    consumible = models.ForeignKey(Consumible, on_delete=models.PROTECT, related_name='pedidos')
    plan = models.ForeignKey(
        PlanMaestro, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos',
        help_text='El plan maestro que lo motivó, si salió de una explosión de materiales.',
    )
    proveedor = models.ForeignKey(
        'finanzas.Proveedor', on_delete=models.PROTECT, null=True, blank=True, related_name='pedidos',
    )
    orden_compra = models.ForeignKey(
        'finanzas.OrdenCompra', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos',
        help_text='La orden de compra con la que se envió al proveedor.',
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))],
    )
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    fecha_pedido = models.DateField(default=timezone.localdate, db_index=True)
    fecha_entrega_prevista = models.DateField(db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador', db_index=True)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_abastecimiento',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_pedidoabastecimiento'
        ordering = ('fecha_entrega_prevista', '-pk')
        verbose_name = 'Pedido de abastecimiento'
        verbose_name_plural = 'Pedidos de abastecimiento'

    def __str__(self):
        return f'{self.codigo or self.pk} · {self.consumible.nombre} · {self.cantidad}'

    @property
    def cantidad_recibida(self):
        return _decimal(sum((entrega.cantidad for entrega in self.entregas.all() if entrega.recibida), Decimal('0')))

    @property
    def pendiente(self):
        return max(Decimal('0'), _decimal(Decimal(self.cantidad) - self.cantidad_recibida))

    @property
    def costo_total(self):
        return _decimal(Decimal(self.cantidad) * Decimal(self.costo_unitario or 0)).quantize(Decimal('0.01'))

    @property
    def en_camino(self):
        return self.estado in self.ESTADOS_EN_CAMINO

    def clean(self):
        super().clean()
        errores = {}
        if self.fecha_pedido and self.fecha_entrega_prevista and self.fecha_entrega_prevista < self.fecha_pedido:
            errores['fecha_entrega_prevista'] = 'La entrega no puede ser anterior al pedido.'
        if self.unidad_id and self.consumible_id and self.consumible.unidad_id != self.unidad_id:
            errores['consumible'] = 'El insumo pertenece a otra unidad.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'PA{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])

    def actualizar_estado_por_entregas(self):
        """Cuando ya no queda nada por entregar, el pedido está recibido."""
        if self.estado in ('cancelado', 'borrador'):
            return
        entregas = list(self.entregas.all())
        if entregas and all(entrega.recibida for entrega in entregas) and self.estado != 'recibido':
            self.estado = 'recibido'
            self.save(update_fields=['estado', 'actualizado_en'])
            if self.orden_compra_id:
                self.orden_compra.actualizar_estado_por_pedidos()


class EntregaPedido(models.Model):
    pedido = models.ForeignKey(PedidoAbastecimiento, on_delete=models.CASCADE, related_name='entregas')
    fecha = models.DateField(db_index=True)
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))],
    )
    recibida = models.BooleanField(default=False, db_index=True)
    recibida_en = models.DateTimeField(null=True, blank=True)
    lote_codigo = models.CharField(max_length=100, blank=True)
    entrada = models.ForeignKey(
        EntradaInventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregas_pedido',
    )
    observaciones = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = 'webcitt_entregapedido'
        ordering = ('fecha', 'pk')
        verbose_name = 'Entrega de un pedido'
        verbose_name_plural = 'Entregas de los pedidos'

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y} · {self.cantidad}'

    @property
    def atrasada(self):
        return bool(not self.recibida and self.fecha < timezone.localdate())
