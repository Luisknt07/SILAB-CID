"""Calidad e inocuidad: qué se mide, con qué límites y en qué momento.

Un plan de calidad dice qué parámetros se controlan en la recepción de una
materia prima, durante el proceso o al liberar un producto, y con qué
límites. Un control es una medición de ese plan sobre un lote (de producto o
de materia prima) o sobre una corrida; si algo sale del límite nace una no
conformidad con su disposición (reproceso, rechazo, devolución, liberación
condicionada) y sus acciones correctivas. La liberación del lote de producto
depende del control: conforme se aprueba, no conforme espera la decisión.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.directorio_unidades.models.core import Unidad
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, LoteProducto, OrdenProduccion, Producto


class PlanCalidad(models.Model):
    MOMENTOS = [
        ('recepcion', 'Recepción de materia prima'),
        ('proceso', 'Durante el proceso'),
        ('liberacion', 'Liberación de producto'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='planes_calidad')
    familia = models.ForeignKey(
        FamiliaProducto,
        on_delete=models.PROTECT,
        related_name='planes_calidad',
        null=True,
        blank=True,
        help_text='Familia a la que pertenece esta especificación de calidad.',
    )
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=160)
    momento = models.CharField(max_length=20, choices=MOMENTOS, default='liberacion', db_index=True)
    producto = models.ForeignKey(
        Producto, on_delete=models.SET_NULL, null=True, blank=True, related_name='planes_calidad',
        help_text='El producto que libera o controla en proceso; vacío si el plan es de materia prima.',
    )
    consumible = models.ForeignKey(
        Consumible, on_delete=models.SET_NULL, null=True, blank=True, related_name='planes_calidad',
        help_text='La materia prima que recibe; vacío si el plan es de producto.',
    )
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_plancalidad'
        unique_together = ('unidad', 'codigo')
        ordering = ('momento', 'nombre', 'pk')
        verbose_name = 'Plan de calidad'
        verbose_name_plural = 'Planes de calidad'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def clean(self):
        super().clean()
        errores = {}
        if self.familia_id and self.unidad_id and self.familia.unidad_id != self.unidad_id:
            errores['familia'] = 'La familia debe pertenecer a la misma planta.'
        if self.producto_id and self.familia_id and self.producto.familia_id not in (None, self.familia_id):
            errores['familia'] = 'La familia del plan debe coincidir con la del producto.'
        if errores:
            from django.core.exceptions import ValidationError
            raise ValidationError(errores)

    @property
    def aplica_a(self):
        if self.producto_id:
            return self.producto.nombre
        if self.consumible_id:
            return self.consumible.nombre
        return 'El proceso'

    def parametros_ordenados(self):
        return list(
            self.parametros.filter(activo=True)
            .select_related('etapa', 'etapa__receta')
            .order_by('orden', 'pk')
        )


class ParametroCalidad(models.Model):
    TIPOS = [
        ('numerico', 'Numérico'),
        ('cualitativo', 'Cualitativo'),
    ]

    plan = models.ForeignKey(PlanCalidad, on_delete=models.CASCADE, related_name='parametros')
    orden = models.PositiveSmallIntegerField(default=1)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='numerico')
    unidad_medida = models.CharField(max_length=30, blank=True)
    minimo = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    maximo = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    valor_esperado = models.CharField(
        max_length=120, blank=True, help_text='Para un parámetro cualitativo: «negativa», «ausencia», «conforme».',
    )
    metodo = models.CharField(max_length=200, blank=True)
    etapa = models.ForeignKey(
        EtapaReceta, on_delete=models.SET_NULL, null=True, blank=True, related_name='parametros_calidad',
        help_text='La etapa del proceso (punto crítico) donde se mide, si aplica.',
    )
    critico = models.BooleanField(default=True, help_text='Fuera de límite, la no conformidad es crítica.')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'webcitt_parametrocalidad'
        ordering = ('plan', 'orden', 'pk')
        verbose_name = 'Parámetro de calidad'
        verbose_name_plural = 'Parámetros de calidad'

    def __str__(self):
        return f'{self.nombre} ({self.limite_texto})'

    @property
    def limite_texto(self):
        if self.tipo == 'cualitativo':
            return self.valor_esperado or 'conforme'
        unidad = f' {self.unidad_medida}' if self.unidad_medida else ''
        minimo = _texto(self.minimo) if self.minimo is not None else None
        maximo = _texto(self.maximo) if self.maximo is not None else None
        if minimo is not None and maximo is not None:
            return f'{minimo}–{maximo}{unidad}'
        if minimo is not None:
            return f'≥ {minimo}{unidad}'
        if maximo is not None:
            return f'≤ {maximo}{unidad}'
        return 'sin límite'

    def evaluar(self, valor_numerico=None, valor_texto=''):
        """Conforme cuando el valor cae dentro del límite o coincide con lo esperado."""
        if self.tipo == 'numerico':
            if valor_numerico is None:
                return False
            valor = Decimal(valor_numerico)
            if self.minimo is not None and valor < self.minimo:
                return False
            if self.maximo is not None and valor > self.maximo:
                return False
            return True
        esperado = (self.valor_esperado or '').strip().lower()
        return not esperado or (valor_texto or '').strip().lower() == esperado


def _texto(valor):
    return format(Decimal(valor).normalize(), 'f')


class ControlQuerySet(models.QuerySet):
    def reales(self):
        """Sin lo medido en corridas o lotes demostrativos."""
        return self.exclude(lote_producto__demostrativo=True).exclude(orden__demostrativa=True)

    def en_sesion(self, sesion):
        if sesion is None:
            return self.reales()
        return self.filter(models.Q(lote_producto__orden__sesion=sesion) | models.Q(orden__sesion=sesion))


class NoConformidadQuerySet(models.QuerySet):
    def reales(self):
        return (self.exclude(lote_producto__demostrativo=True)
                .exclude(control__lote_producto__demostrativo=True)
                .exclude(control__orden__demostrativa=True))

    def en_sesion(self, sesion):
        if sesion is None:
            return self.reales()
        return self.filter(models.Q(lote_producto__orden__sesion=sesion) | models.Q(control__orden__sesion=sesion))


class ControlCalidad(models.Model):
    RESULTADOS = [
        ('conforme', 'Conforme'),
        ('no_conforme', 'No conforme'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='controles_calidad')
    plan = models.ForeignKey(PlanCalidad, on_delete=models.PROTECT, related_name='controles')
    lote_producto = models.ForeignKey(
        LoteProducto, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles_calidad',
    )
    lote_consumible = models.ForeignKey(
        LoteConsumible, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles_calidad',
    )
    orden = models.ForeignKey(
        OrdenProduccion, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles_calidad',
    )
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles_calidad',
    )
    resultado = models.CharField(max_length=20, choices=RESULTADOS, default='conforme', db_index=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    objects = ControlQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_controlcalidad'
        ordering = ('-fecha', '-pk')
        verbose_name = 'Control de calidad'
        verbose_name_plural = 'Controles de calidad'

    def __str__(self):
        return f'{self.plan.nombre} · {self.get_resultado_display()} · {self.fecha:%d/%m/%Y}'

    @property
    def objeto(self):
        if self.lote_producto_id:
            return f'Lote {self.lote_producto.codigo}'
        if self.lote_consumible_id:
            return f'Lote {self.lote_consumible.codigo}'
        if self.orden_id:
            return f'Corrida {self.orden.codigo}'
        return 'Sin lote'


class MedicionCalidad(models.Model):
    control = models.ForeignKey(ControlCalidad, on_delete=models.CASCADE, related_name='mediciones')
    parametro = models.ForeignKey(ParametroCalidad, on_delete=models.PROTECT, related_name='mediciones')
    valor_numerico = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    valor_texto = models.CharField(max_length=120, blank=True)
    conforme = models.BooleanField(default=True)

    class Meta:
        db_table = 'webcitt_medicioncalidad'
        ordering = ('pk',)

    def __str__(self):
        return f'{self.parametro.nombre}: {self.valor}'

    @property
    def valor(self):
        if self.valor_numerico is not None:
            unidad = f' {self.parametro.unidad_medida}' if self.parametro.unidad_medida else ''
            return f'{_texto(self.valor_numerico)}{unidad}'
        return self.valor_texto


class NoConformidad(models.Model):
    GRAVEDADES = [
        ('menor', 'Menor'),
        ('mayor', 'Mayor'),
        ('critica', 'Crítica'),
    ]
    ESTADOS = [
        ('abierta', 'Abierta'),
        ('en_tratamiento', 'En tratamiento'),
        ('cerrada', 'Cerrada'),
    ]
    DISPOSICIONES = [
        ('pendiente', 'Por decidir'),
        ('reproceso', 'Reproceso'),
        ('liberacion_condicionada', 'Liberación condicionada'),
        ('rechazo', 'Rechazo del lote'),
        ('devolucion', 'Devolución al proveedor'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='no_conformidades')
    codigo = models.CharField(max_length=30, blank=True)
    control = models.ForeignKey(
        ControlCalidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='no_conformidades',
    )
    lote_producto = models.ForeignKey(
        LoteProducto, on_delete=models.SET_NULL, null=True, blank=True, related_name='no_conformidades',
    )
    lote_consumible = models.ForeignKey(
        LoteConsumible, on_delete=models.SET_NULL, null=True, blank=True, related_name='no_conformidades',
    )
    descripcion = models.TextField()
    gravedad = models.CharField(max_length=20, choices=GRAVEDADES, default='mayor', db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierta', db_index=True)
    disposicion = models.CharField(max_length=30, choices=DISPOSICIONES, default='pendiente')
    causa = models.TextField(blank=True)
    detectada_en = models.DateTimeField(default=timezone.now, db_index=True)
    detectada_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='no_conformidades_detectadas',
    )
    cerrada_en = models.DateTimeField(null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = NoConformidadQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_noconformidad'
        ordering = ('-detectada_en', '-pk')
        verbose_name = 'No conformidad'
        verbose_name_plural = 'No conformidades'

    def __str__(self):
        return f'{self.codigo or self.pk} · {self.get_gravedad_display()} · {self.get_estado_display()}'

    @property
    def objeto(self):
        if self.lote_producto_id:
            return f'Lote {self.lote_producto.codigo}'
        if self.lote_consumible_id:
            return f'Lote {self.lote_consumible.codigo}'
        return 'Proceso'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'NC-{self.pk:04d}'
            super().save(update_fields=['codigo'])


class AccionCorrectiva(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('cumplida', 'Cumplida'),
        ('verificada', 'Verificada'),
    ]

    no_conformidad = models.ForeignKey(NoConformidad, on_delete=models.CASCADE, related_name='acciones')
    descripcion = models.TextField()
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acciones_correctivas',
    )
    fecha_compromiso = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente', db_index=True)
    verificacion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_accioncorrectiva'
        ordering = ('fecha_compromiso', 'pk')
        verbose_name = 'Acción correctiva'
        verbose_name_plural = 'Acciones correctivas'

    def __str__(self):
        return f'{self.descripcion[:60]} · {self.get_estado_display()}'

    @property
    def vencida(self):
        return bool(
            self.estado == 'pendiente' and self.fecha_compromiso and self.fecha_compromiso < timezone.localdate()
        )
