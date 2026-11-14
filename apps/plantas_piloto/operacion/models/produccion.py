"""Lo que produce una unidad: productos, recetas, órdenes, lotes y salidas.

Un laboratorio termina su trabajo en el cierre de la reserva: piezas,
muestras o ensayos con su consumo. Una planta piloto sigue: lo que sale de
la corrida es un producto con lote, vencimiento y control de calidad, que
se vende, se transfiere a otra unidad o se da de baja. Este módulo modela
ese tramo sin duplicar el motor común de reservas e inventario.

Lo que fluye se distingue por tipo:

* **Producto terminado**: sale para la venta o para otra unidad.
* **Producto intermedio**: vuelve a entrar en otra corrida de la misma
  unidad, como la crema que se convierte en mantequilla.
* **Subproducto**: sale con valor propio, como el suero de quesería.
* **Residuo**: sale sin valor comercial y solo se registra.

La receta es la lista de materiales: por cada corrida base (cien litros de
leche) declara qué insumos entran y qué productos salen. La orden escala esa
receta, ocupa la línea en la agenda mientras dura y, al cerrarse, descuenta
los insumos del inventario por lote y crea los lotes de producto con su
rendimiento y su merma.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.directorio_unidades.models.core import Unidad
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad

TRES_DECIMALES = Decimal('0.001')
DOS_DECIMALES = Decimal('0.01')


def _decimal(valor):
    try:
        numero = Decimal(str(valor or 0))
        if not numero.is_finite():
            raise ValidationError('La cantidad debe ser un número finito.')
        return numero.quantize(TRES_DECIMALES, rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise ValidationError('La cantidad no es un número válido o excede la precisión admitida.') from error


class FamiliaProducto(models.Model):
    """Taxonomía común que ordena el contenido técnico de una planta piloto."""

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='familias_producto')
    codigo = models.CharField(max_length=20, unique=True)
    orden = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'webcitt_familiaproducto'
        ordering = ('unidad', 'orden', 'nombre')
        verbose_name = 'Familia de producto'
        verbose_name_plural = 'Familias de producto'
        constraints = [
            models.UniqueConstraint(fields=('unidad', 'orden'), name='familia_orden_unico_por_planta'),
            models.UniqueConstraint(fields=('unidad', 'nombre'), name='familia_nombre_unico_por_planta'),
        ]

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def clean(self):
        super().clean()
        if self.unidad_id and self.unidad.dependencia != 'plantas_piloto':
            raise ValidationError({'unidad': 'Las familias de producto pertenecen únicamente a plantas piloto.'})


class Producto(models.Model):
    """Algo que sale de una corrida y se cuenta en la unidad de medida propia."""

    TIPOS = [
        ('terminado', 'Producto terminado'),
        ('intermedio', 'Producto intermedio'),
        ('subproducto', 'Subproducto'),
        ('residuo', 'Residuo'),
    ]
    TIPO_DETALLE = {
        'terminado': (
            'Productos terminados',
            'Salen para la venta o para otra unidad, con lote, vencimiento y '
            'control de calidad.',
        ),
        'intermedio': (
            'Productos intermedios',
            'Vuelven a entrar en otra corrida de la misma unidad, como la crema '
            'que se convierte en mantequilla.',
        ),
        'subproducto': (
            'Subproductos',
            'Salen del proceso con valor propio, como el suero de quesería que '
            'se vende o se transfiere.',
        ),
        'residuo': (
            'Residuos',
            'Salen del proceso sin valor comercial y solo se registran para el '
            'control ambiental.',
        ),
    }
    TIPOS_PUBLICOS = ('terminado', 'intermedio', 'subproducto')

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='productos')
    familia = models.ForeignKey(
        FamiliaProducto,
        on_delete=models.PROTECT,
        related_name='productos',
        null=True,
        blank=True,
        help_text='Familia maestra que agrupa este producto y sus procesos.',
    )
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='terminado', db_index=True)
    unidad_medida = models.CharField(
        max_length=50,
        help_text='Unidad en la que se cuenta el producto: kg, litro, unidad.',
    )
    presentacion = models.CharField(
        max_length=120,
        blank=True,
        help_text='Cómo se entrega: bloque de 500 g, botella de 1 litro, bidón de 20 litros.',
    )
    precio_venta = models.DecimalField(
        'Precio de venta por unidad de medida',
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Cero cuando el producto no se vende.',
    )
    vida_util_dias = models.PositiveIntegerField(
        'Vida útil en días',
        default=0,
        help_text='Cero cuando el producto no vence.',
    )
    requiere_frio = models.BooleanField('Requiere cadena de frío', default=False)
    temperatura_maxima = models.DecimalField(
        'Temperatura máxima de conservación (°C)',
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Refrigerado, 4 °C; congelado, −18 °C. Con cadena de frío y vacía, se toman 4 °C.',
    )
    descripcion = models.TextField(blank=True)
    publico = models.BooleanField(
        'Visible en la ficha pública',
        default=True,
        help_text='Los residuos nunca se publican.',
    )
    activo = models.BooleanField(default=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_producto'
        ordering = ('unidad', 'tipo', 'nombre')
        verbose_name = 'Producto de la unidad'
        verbose_name_plural = 'Productos de las unidades'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def clean(self):
        super().clean()
        if self.familia_id and self.unidad_id and self.familia.unidad_id != self.unidad_id:
            raise ValidationError({'familia': 'La familia debe pertenecer a la misma planta.'})

    @property
    def se_vende(self):
        return self.precio_venta > 0

    LIMITE_REFRIGERADO = Decimal('4')

    @property
    def limite_frio(self):
        """La temperatura que el producto no debe superar; sin cadena de frío, ninguna."""
        if not self.requiere_frio:
            return None
        return self.temperatura_maxima if self.temperatura_maxima is not None else self.LIMITE_REFRIGERADO

    @property
    def conservacion(self):
        limite = self.limite_frio
        if limite is None:
            return 'Ambiente'
        estado = 'Congelado' if limite < 0 else 'Refrigerado'
        return f"{estado}, hasta {format(limite.normalize(), 'f')} °C"

    @property
    def es_publico(self):
        return self.publico and self.activo and self.tipo in self.TIPOS_PUBLICOS

    @property
    def existencia_disponible(self):
        total = self.lotes.filter(estado='disponible').aggregate(total=Sum('cantidad_disponible'))['total']
        return total or Decimal('0')


class Receta(models.Model):
    """Lista de materiales: lo que entra y lo que sale por cada corrida base."""

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='recetas')
    responsable = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad', on_delete=models.SET_NULL, null=True, blank=True, related_name='procesos_a_cargo',
        help_text='Quien mantiene el proceso al día: su receta, sus etapas y su ficha.',
    )
    familia = models.ForeignKey(
        FamiliaProducto,
        on_delete=models.PROTECT,
        related_name='recetas',
        null=True,
        blank=True,
        help_text='Familia del proceso; debe coincidir con la del producto principal.',
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='recetas')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    cantidad_base = models.DecimalField(
        'Cantidad base de la corrida',
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='La corrida de referencia: cien litros de leche, veinte kilos de carne.',
    )
    unidad_base = models.CharField(
        'Unidad de la corrida base',
        max_length=60,
        help_text='Con qué se mide la corrida: litros de leche, kilos de masa.',
    )
    rendimiento_esperado = models.DecimalField(
        'Producto esperado por corrida base',
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    duracion_horas = models.DecimalField(
        'Duración de la corrida base en horas',
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    instrucciones = models.TextField(blank=True)
    ORIGENES = [
        ('referencia', 'Proceso de referencia del sistema'),
        ('derivado', 'Derivado de un proceso de referencia, por validar'),
        ('validado', 'Validado por la planta'),
    ]
    origen = models.CharField(
        'Origen del proceso',
        max_length=12,
        choices=ORIGENES,
        default='referencia',
        db_index=True,
        help_text='Los derivados copian las etapas de otro proceso como punto de partida: '
                  'se ajustan y la planta los valida antes de producir.',
    )
    derivado_de = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derivados',
        verbose_name='Derivado del proceso',
    )
    software = models.ManyToManyField(
        'recursos.SoftwareDisponible', db_table='webcitt_receta_software',
        blank=True,
        related_name='recetas',
        help_text='Programas y simuladores propios del proceso; la reserva por proceso los marca y la guía los toma.',
    )
    activa = models.BooleanField(default=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_receta'
        ordering = ('unidad', 'nombre')
        verbose_name = 'Receta o lista de materiales'
        verbose_name_plural = 'Recetas o listas de materiales'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    @property
    def nombre_publico(self):
        """Nombre del producto sin la escala interna de la corrida base; el derivado lo avisa."""
        if self.origen == 'derivado':
            return f'{self.producto.nombre} · derivado, por validar'
        return self.producto.nombre

    def clean(self):
        super().clean()
        errores = {}
        if self.producto_id and self.unidad_id and self.producto.unidad_id != self.unidad_id:
            errores['producto'] = 'El producto debe pertenecer a la misma unidad.'
        if self.familia_id and self.unidad_id and self.familia.unidad_id != self.unidad_id:
            errores['familia'] = 'La familia debe pertenecer a la misma planta.'
        if self.familia_id and self.producto_id and self.producto.familia_id not in (None, self.familia_id):
            errores['familia'] = 'La familia del proceso debe coincidir con la del producto principal.'
        if errores:
            raise ValidationError(errores)

    def insumos_para(self, factor):
        factor = Decimal(str(factor))
        return [
            {
                'consumible': insumo.consumible,
                'cantidad': _decimal(insumo.cantidad * factor),
                'obligatorio': insumo.obligatorio,
                'forma_parte': insumo.forma_parte,
                'etapa': insumo.etapa.orden if insumo.etapa_id else None,
            }
            for insumo in self.insumos.select_related('consumible', 'etapa').order_by('pk')
        ]

    def salidas_para(self, factor):
        factor = Decimal(str(factor))
        salidas = [{
            'producto': self.producto,
            'cantidad': _decimal(self.rendimiento_esperado * factor),
            'principal': True,
            'etapa': None,
        }]
        salidas.extend(
            {
                'producto': salida.producto,
                'cantidad': _decimal(salida.cantidad * factor),
                'principal': False,
                'externa_al_flujo': salida.externa_al_flujo,
                'etapa': salida.etapa.orden if salida.etapa_id else None,
            }
            for salida in self.salidas.select_related('producto', 'etapa').order_by('pk')
        )
        return salidas

    @property
    def duracion_estandar_min(self):
        """Suma del trabajo y las esperas de las etapas; sin etapas, las horas declaradas."""
        etapas = list(self.etapas.all())
        if etapas:
            return sum(etapa.duracion_min + etapa.espera_min for etapa in etapas)
        return int(Decimal(self.duracion_horas or 0) * 60)


class EtapaReceta(models.Model):
    """Un paso del proceso: dónde ocurre, cuánto dura, qué entra, qué sale.

    Los tipos son los del cursograma analítico (operación, inspección,
    transporte, espera y almacenamiento), así el diagrama sinóptico y el
    analítico se dibujan solos. El rendimiento es el balance de masa: qué
    parte de lo que entra sigue a la etapa siguiente.
    """

    TIPOS = [
        ('operacion', 'Operación'),
        ('inspeccion', 'Inspección'),
        ('transporte', 'Transporte'),
        ('espera', 'Espera'),
        ('almacenamiento', 'Almacenamiento'),
    ]
    SIMBOLOS = {
        'operacion': '○',
        'inspeccion': '□',
        'transporte': '⇨',
        'espera': 'D',
        'almacenamiento': '▽',
    }

    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='etapas')
    familia = models.ForeignKey(
        FamiliaProducto,
        on_delete=models.PROTECT,
        related_name='puntos_y_etapas',
        null=True,
        blank=True,
        help_text='Familia del proceso, disponible para ordenar los puntos críticos de control.',
    )
    orden = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='operacion', db_index=True)
    equipo = models.ForeignKey(
        'recursos.EquiposServicios',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etapas_receta',
        help_text='El equipo principal donde ocurre; sus auxiliares van incluidos.',
    )
    espacio = models.ForeignKey(
        'gestion_unidades.EspacioReservable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etapas_receta',
    )
    duracion_min = models.PositiveIntegerField('Trabajo en minutos', default=0)
    espera_min = models.PositiveIntegerField(
        'Espera en minutos',
        default=0,
        help_text='Tiempo en que el equipo o el área siguen ocupados sin personas: coagulación, prensado, fermentación, maduración.',
    )
    personas = models.PositiveSmallIntegerField(default=1)
    rendimiento_pct = models.DecimalField(
        'Continúa a la etapa siguiente (%)',
        max_digits=6,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    distancia_m = models.DecimalField(
        'Distancia recorrida (m)',
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    # Codex CXC 1-1969: el PCC es de inocuidad; lo que controla calidad o proceso es un PC.
    punto_critico = models.BooleanField(
        'Punto crítico de control (PCC)', default=False,
        help_text='Solo si la etapa controla un peligro de inocuidad y ninguna etapa posterior lo elimina.',
    )
    punto_control = models.BooleanField(
        'Punto de control de calidad (PC)', default=False,
        help_text='Controla calidad o proceso, no inocuidad. Usa el mismo parámetro y límite.',
    )
    parametro = models.CharField(max_length=160, blank=True)
    limite = models.CharField(max_length=120, blank=True)
    instrucciones = models.TextField(blank=True)

    class Meta:
        db_table = 'webcitt_etapareceta'
        ordering = ('receta', 'orden')
        unique_together = (('receta', 'orden'),)
        verbose_name = 'Etapa de la receta'
        verbose_name_plural = 'Etapas de la receta'

    def __str__(self):
        return f'{self.orden}. {self.nombre}'

    @property
    def simbolo(self):
        return self.SIMBOLOS.get(self.tipo, '○')

    @property
    def tiempo_total_min(self):
        return self.duracion_min + self.espera_min

    def clean(self):
        super().clean()
        errores = {}
        if self.espacio_id and self.receta_id and self.espacio.unidad_id != self.receta.unidad_id:
            errores['espacio'] = 'El área debe pertenecer a la unidad de la receta.'
        if self.familia_id and self.receta_id and self.receta.familia_id not in (None, self.familia_id):
            errores['familia'] = 'La familia del punto de control debe coincidir con la del proceso.'
        if self.punto_critico and self.punto_control:
            errores['punto_control'] = 'Una etapa es PCC (inocuidad) o PC (calidad), no ambas.'
        if errores:
            raise ValidationError(errores)
        if self.equipo_id and self.receta_id:
            unidad_id = self.receta.unidad_id
            pertenece = self.equipo.unidades.filter(
                models.Q(laboratorio_id=unidad_id) | models.Q(laboratorios=unidad_id)
            ).exists()
            if not pertenece:
                raise ValidationError({'equipo': 'El equipo debe pertenecer a la unidad de la receta.'})
        if self.punto_critico and not self.parametro:
            raise ValidationError({'parametro': 'Un punto crítico declara qué se controla y con qué límite.'})


class InsumoReceta(models.Model):
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='insumos')
    consumible = models.ForeignKey(Consumible, on_delete=models.PROTECT, related_name='recetas')
    etapa = models.ForeignKey(
        EtapaReceta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='insumos',
        help_text='La etapa del proceso en la que entra.',
    )
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Cantidad por corrida base, en la unidad del insumo.',
    )
    obligatorio = models.BooleanField(default=True)
    FORMA_PARTE = [
        ('base', 'Materia prima de la corrida base'),
        ('si', 'Se incorpora al producto'),
        ('no', 'Auxiliar del proceso: no entra al producto'),
    ]
    forma_parte = models.CharField(
        'Relación con el producto',
        max_length=5,
        choices=FORMA_PARTE,
        default='si',
        help_text='El balance de masa suma lo que se incorpora; la materia prima base es lo que entra; el auxiliar no cuenta.',
    )

    class Meta:
        db_table = 'webcitt_insumoreceta'
        ordering = ('pk',)
        unique_together = (('receta', 'consumible'),)
        verbose_name = 'Insumo de la receta'
        verbose_name_plural = 'Insumos de la receta'

    def __str__(self):
        return f'{self.consumible.nombre}: {self.cantidad} {self.consumible.unidad_medida}'

    def clean(self):
        super().clean()
        if self.consumible_id and self.receta_id and self.consumible.unidad_id != self.receta.unidad_id:
            raise ValidationError({'consumible': 'El insumo debe pertenecer a la unidad de la receta.'})
        if self.etapa_id and self.receta_id and self.etapa.receta_id != self.receta_id:
            raise ValidationError({'etapa': 'La etapa debe ser de la misma receta.'})


class SalidaReceta(models.Model):
    """Lo demás que sale de la corrida: subproductos, intermedios y residuos."""

    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='salidas')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='salidas_receta')
    etapa = models.ForeignKey(
        EtapaReceta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salidas',
        help_text='La etapa del proceso en la que sale.',
    )
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Cantidad esperada por corrida base, en la unidad del producto.',
    )
    externa_al_flujo = models.BooleanField(
        'Salida externa al flujo', default=False,
        help_text='Agua de lavado u otro auxiliar que no procede de la masa del producto. '
        'Se registra como salida, pero no consume la merma ni integra el balance del producto.',
    )

    class Meta:
        db_table = 'webcitt_salidareceta'
        ordering = ('pk',)
        unique_together = (('receta', 'producto'),)
        verbose_name = 'Salida de la receta'
        verbose_name_plural = 'Salidas de la receta'

    def __str__(self):
        return f'{self.producto.nombre}: {self.cantidad} {self.producto.unidad_medida}'

    def clean(self):
        super().clean()
        if self.producto_id and self.receta_id:
            if self.producto.unidad_id != self.receta.unidad_id:
                raise ValidationError({'producto': 'La salida debe pertenecer a la unidad de la receta.'})
            if self.producto_id == self.receta.producto_id:
                raise ValidationError({'producto': 'El producto principal ya es el rendimiento de la receta.'})
        if self.etapa_id and self.receta_id and self.etapa.receta_id != self.receta_id:
            raise ValidationError({'etapa': 'La etapa debe ser de la misma receta.'})


class OrdenQuerySet(models.QuerySet):
    def reales(self):
        """Sin las corridas demostrativas: lo que cuenta en indicadores y reportes."""
        return self.filter(demostrativa=False)

    def en_sesion(self, sesion):
        """Las órdenes de esa sesión; sin sesión, las de la producción real."""
        return self.filter(sesion=sesion) if sesion is not None else self.reales()


class LoteQuerySet(models.QuerySet):
    def reales(self):
        return self.filter(demostrativo=False)

    def en_sesion(self, sesion):
        return self.filter(orden__sesion=sesion) if sesion is not None else self.reales()


class MovimientoQuerySet(models.QuerySet):
    def reales(self):
        return self.filter(lote__demostrativo=False)

    def en_sesion(self, sesion):
        return self.filter(lote__orden__sesion=sesion) if sesion is not None else self.reales()


class OrdenProduccion(models.Model):
    """Una corrida: la receta escalada, la línea ocupada y lo que salió."""

    ESTADOS = [
        ('planificada', 'Planificada'),
        ('en_proceso', 'En proceso'),
        ('terminada', 'Terminada'),
        ('cancelada', 'Cancelada'),
    ]
    ESTADOS_ABIERTOS = ('planificada', 'en_proceso')
    ORIGENES = [
        ('propia', 'Producción propia'),
        ('maquila', 'Encargo de maquila'),
        ('practica', 'Práctica docente'),
        ('investigacion', 'Desarrollo o ensayo'),
    ]
    # El ámbito separa lo que enseña, lo que investiga y lo que produce de verdad.
    AMBITOS = {
        'practica': 'Académico',
        'investigacion': 'Investigación',
        'propia': 'Producción real',
        'maquila': 'Producción real',
    }

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='ordenes_produccion')
    sesion = models.ForeignKey(
        'plantas_operacion.SesionERP', on_delete=models.PROTECT, null=True, blank=True, related_name='ordenes_produccion',
        help_text='La sesión de práctica donde se registró; sin sesión, es producción real.',
    )
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    receta = models.ForeignKey(Receta, on_delete=models.PROTECT, related_name='ordenes')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='ordenes', editable=False)
    origen = models.CharField(max_length=20, choices=ORIGENES, default='propia', db_index=True)
    demostrativa = models.BooleanField(
        'Corrida demostrativa',
        default=False,
        db_index=True,
        help_text='Valida el flujo con datos de ejemplo: no descuenta inventario, sus lotes no se venden '
                  'de verdad y no cuenta en los indicadores ni en los reportes.',
    )
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_produccion',
        help_text='El encargo de maquila o la práctica que originó la corrida.',
    )
    factor = models.DecimalField(
        'Corridas base',
        max_digits=8,
        decimal_places=3,
        default=1,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Cuántas veces la corrida base de la receta: 2 son doscientos litros si la base es cien.',
    )
    cantidad_planificada = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    fecha_inicio = models.DateField(db_index=True)
    fecha_fin = models.DateField(db_index=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    linea = models.ForeignKey(
        'gestion_unidades.EspacioReservable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_produccion',
        help_text='La línea o área que ocupa la corrida; queda bloqueada en la agenda.',
    )
    equipos = models.ManyToManyField('recursos.UnidadEquipo', db_table='webcitt_ordenproduccion_equipos', blank=True, related_name='ordenes_produccion')
    responsable = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_produccion',
    )
    bloqueo = models.OneToOneField(
        BloqueoAgendaUnidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orden_produccion',
        editable=False,
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='planificada', db_index=True)
    observaciones = models.TextField(blank=True)
    cantidad_obtenida = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, editable=False)
    merma = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, editable=False)
    rendimiento_real_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, editable=False)
    detalle_cierre = models.JSONField(default=dict, blank=True, editable=False)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_produccion_creadas',
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    cerrada_en = models.DateTimeField(null=True, blank=True, editable=False)

    objects = OrdenQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_ordenproduccion'
        ordering = ('-fecha_inicio', '-pk')
        verbose_name = 'Orden de producción'
        verbose_name_plural = 'Órdenes de producción'

    def __str__(self):
        return f'{self.codigo or "Orden"} · {self.producto.nombre}'

    @property
    def abierta(self):
        return self.estado in self.ESTADOS_ABIERTOS

    @property
    def ambito(self):
        ambito = self.AMBITOS.get(self.origen, '')
        return f'{ambito} · demostrativa' if self.demostrativa else ambito

    @property
    def dias(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def clean(self):
        super().clean()
        if self.receta_id and self.unidad_id and self.receta.unidad_id != self.unidad_id:
            raise ValidationError({'receta': 'La receta debe pertenecer a esta unidad.'})
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La corrida no puede terminar antes de empezar.'})
        if bool(self.hora_inicio) != bool(self.hora_fin):
            raise ValidationError({'hora_fin': 'Indica la hora inicial y la final, o ninguna para la jornada completa.'})
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({'hora_fin': 'La hora final debe ser posterior a la inicial.'})
        if self.linea_id and self.unidad_id and self.linea.unidad_id != self.unidad_id:
            raise ValidationError({'linea': 'La línea debe pertenecer a esta unidad.'})
        if self.responsable_id and self.unidad_id and self.responsable.unidad_id != self.unidad_id:
            raise ValidationError({'responsable': 'La persona responsable debe pertenecer a esta unidad.'})
        if self.reserva_id and self.unidad_id and self.reserva.laboratorio_id != self.unidad_id:
            raise ValidationError({'reserva': 'La solicitud de origen debe pertenecer a esta unidad.'})

    def planificar_cantidades(self):
        """El producto y la cantidad planificada salen de la receta y el factor."""
        if self.receta_id:
            self.producto = self.receta.producto
            if self.factor is not None:
                self.cantidad_planificada = _decimal(
                    self.receta.rendimiento_esperado * Decimal(str(self.factor))
                )

    def save(self, *args, **kwargs):
        self.planificar_cantidades()
        # Lo de una sesión nunca es producción real: no toca inventario, finanzas ni indicadores.
        if self.sesion_id:
            self.demostrativa = True
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'OP{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])

    # ------------------------------------------------------------ planificación
    def insumos_planificados(self):
        return self.receta.insumos_para(self.factor)

    def salidas_planificadas(self):
        return self.receta.salidas_para(self.factor)

    def sincronizar_bloqueo(self, usuario=None):
        """La línea y los equipos de la corrida quedan fuera de la agenda.

        Una corrida demostrativa valida datos: no le quita la línea a una reserva real.
        """
        if not self.abierta or self.demostrativa:
            if self.bloqueo_id and self.bloqueo.activo:
                self.bloqueo.activo = False
                self.bloqueo.save(update_fields=['activo'])
            return None
        equipos = list(self.equipos.all())
        if self.linea_id:
            alcance = 'areas'
        elif equipos:
            alcance = 'equipos'
        else:
            alcance = 'unidad_completa'
        bloqueo = self.bloqueo or BloqueoAgendaUnidad(unidad=self.unidad, creado_por=usuario)
        bloqueo.tipo = 'produccion'
        bloqueo.titulo = f'{self.producto.nombre} · {self.codigo}'
        bloqueo.motivo = (
            f'Corrida de producción {self.codigo}: {self.cantidad_planificada} '
            f'{self.producto.unidad_medida} de {self.producto.nombre}.'
        )
        bloqueo.fecha_inicio = self.fecha_inicio
        bloqueo.fecha_fin = self.fecha_fin
        bloqueo.dia_completo = not self.hora_inicio
        bloqueo.hora_inicio = self.hora_inicio
        bloqueo.hora_fin = self.hora_fin
        bloqueo.alcance = alcance
        bloqueo.bloquea_recursos = True
        bloqueo.bloquea_servicios = False
        bloqueo.visible_en_agenda = True
        bloqueo.activo = True
        bloqueo.save()
        bloqueo.espacios.set([self.linea] if self.linea_id else [])
        bloqueo.equipos.set(equipos)
        if self.bloqueo_id != bloqueo.pk:
            self.bloqueo = bloqueo
            super().save(update_fields=['bloqueo'])
        return bloqueo

    # ------------------------------------------------------------------ ciclo
    def iniciar(self):
        if self.estado != 'planificada':
            raise ValidationError('Solo una orden planificada puede iniciarse.')
        self.estado = 'en_proceso'
        self.save(update_fields=['estado'])

    def cancelar(self, motivo=''):
        if not self.abierta:
            raise ValidationError('Solo una orden abierta puede cancelarse.')
        self.estado = 'cancelada'
        if motivo:
            self.observaciones = f'{self.observaciones}\n{motivo}'.strip()
        self.save(update_fields=['estado', 'observaciones'])
        self.sincronizar_bloqueo()

    def cerrar(self, *, usuario, consumos, salidas, observaciones='', ubicacion=''):
        """Descuenta lo consumido por lote y crea los lotes de lo obtenido.

        ``consumos``: lista de ``{'consumible_id', 'lote_id', 'cantidad'}``.
        ``salidas``: lista de ``{'producto_id', 'cantidad'}``. Una salida en cero
        no crea lote; el producto principal debe tener cantidad.
        """
        if not self.abierta:
            raise ValidationError('La orden ya está terminada o cancelada.')
        hoy = timezone.localdate()
        planificados = {item['consumible'].pk: item for item in self.insumos_planificados()}
        esperadas = {item['producto'].pk: item for item in self.salidas_planificadas()}
        registro_consumos, registro_salidas = [], []
        with transaction.atomic():
            if not self.demostrativa:
                # Compartir el orden de bloqueo con el kardex y los conteos;
                # el orden de los renglones enviados no cambia ese contrato.
                list(Consumible.objects.select_for_update().filter(
                    pk__in=planificados,
                ).order_by('pk'))
            for consumo in consumos:
                consumible_id = int(consumo['consumible_id'])
                cantidad = _decimal(consumo.get('cantidad'))
                if consumible_id not in planificados:
                    raise ValidationError('Solo se descuentan los insumos de la receta.')
                if cantidad <= 0:
                    continue
                consumible = planificados[consumible_id]['consumible']
                if self.sesion_id and self.sesion.tipo != 'demostrativa':
                    # En una sesión de práctica se descuenta lo que la sesión tiene, no el inventario real.
                    existencia = self.sesion.existencias.select_for_update().filter(consumible=consumible).first()
                    disponible = existencia.cantidad if existencia else Decimal('0')
                    if cantidad > disponible:
                        raise ValidationError(
                            f'En la sesión quedan {disponible} {consumible.unidad_medida} de {consumible.nombre}: '
                            'pídelo y recíbelo antes de cerrar la corrida.'
                        )
                    existencia.cantidad = disponible - cantidad
                    existencia.save(update_fields=['cantidad'])
                if self.demostrativa:
                    # Se registra como simulado: el inventario real no se toca.
                    registro_consumos.append({
                        'consumible_id': consumible_id,
                        'consumible': consumible.nombre,
                        'lote': '',
                        'planificado': str(planificados[consumible_id]['cantidad']),
                        'consumido': str(cantidad),
                        'unidad': consumible.unidad_medida,
                        'simulado': True,
                    })
                    continue
                lote = LoteConsumible.objects.select_for_update().filter(
                    pk=consumo.get('lote_id') or None,
                    consumible_id=consumible_id,
                    consumible__unidad=self.unidad,
                ).first()
                if lote is None:
                    raise ValidationError(f'Selecciona el lote abierto de {consumible.nombre}.')
                if lote.estado != 'en_uso':
                    raise ValidationError(
                        f'El lote {lote.codigo} de {consumible.nombre} no está en uso; ábrelo antes de descontar.'
                    )
                entrada, creada = EntradaInventario.objects.get_or_create(
                    clave_idempotencia=f'orden-produccion-{self.pk}-{consumible_id}-{lote.pk}',
                    defaults={
                        'consumible': consumible,
                        'unidad': self.unidad,
                        'tipo': 'salida',
                        'motivo': 'consumo_produccion',
                        'cantidad': cantidad,
                        'lote_inventario': lote,
                        'equipo': lote.equipo_en_uso,
                        'reserva': self.reserva,
                        'usuario': usuario,
                        'referencia': self.codigo,
                        'nota': f'Consumo de la orden {self.codigo}: {self.producto.nombre}.',
                        'responsable_costo': 'laboratorio',
                    },
                )
                registro_consumos.append({
                    'consumible_id': consumible_id,
                    'consumible': consumible.nombre,
                    'lote': lote.codigo,
                    'planificado': str(planificados[consumible_id]['cantidad']),
                    'consumido': str(cantidad),
                    'unidad': consumible.unidad_medida,
                    'entrada_id': entrada.pk,
                })
            obtenida = None
            for salida in salidas:
                producto_id = int(salida['producto_id'])
                cantidad = _decimal(salida.get('cantidad'))
                if producto_id not in esperadas:
                    raise ValidationError('Solo se registran las salidas previstas por la receta.')
                esperada = esperadas[producto_id]
                if esperada['principal']:
                    obtenida = cantidad
                if cantidad <= 0:
                    continue
                producto = esperada['producto']
                lote = LoteProducto.crear_desde_orden(
                    self, producto, cantidad, fecha=hoy, ubicacion=ubicacion
                )
                registro_salidas.append({
                    'producto_id': producto_id,
                    'producto': producto.nombre,
                    'tipo': producto.tipo,
                    'esperado': str(esperada['cantidad']),
                    'obtenido': str(cantidad),
                    'unidad': producto.unidad_medida,
                    'lote': lote.codigo,
                    'lote_id': lote.pk,
                })
            if obtenida is None or obtenida <= 0:
                raise ValidationError(f'Registra cuánto {self.producto.nombre} obtuviste en la corrida.')
            self.cantidad_obtenida = obtenida
            self.merma = max(Decimal('0'), _decimal(self.cantidad_planificada - obtenida))
            self.rendimiento_real_pct = (
                (obtenida / self.cantidad_planificada * 100).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                if self.cantidad_planificada
                else None
            )
            self.detalle_cierre = {
                'consumos': registro_consumos,
                'salidas': registro_salidas,
                'observaciones': observaciones,
                'cerrada_por': getattr(usuario, 'username', ''),
                'demostrativa': self.demostrativa,
            }
            self.estado = 'terminada'
            self.cerrada_en = timezone.now()
            if observaciones:
                self.observaciones = f'{self.observaciones}\n{observaciones}'.strip()
            self.save()
            if self.bloqueo_id and self.bloqueo.fecha_fin > hoy:
                # La línea vuelve a la agenda en cuanto termina la corrida.
                self.bloqueo.fecha_fin = max(hoy, self.bloqueo.fecha_inicio)
                self.bloqueo.save(update_fields=['fecha_fin'])
        return self


class LoteProducto(models.Model):
    """Una cantidad de producto con fecha, vencimiento y control de calidad."""

    ESTADOS = [
        ('cuarentena', 'En cuarentena'),
        ('disponible', 'Disponible'),
        ('agotado', 'Agotado'),
        ('retirado', 'Retirado'),
    ]
    CALIDAD = [
        ('pendiente', 'Pendiente de control'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('no_aplica', 'No aplica'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='lotes_producto')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lotes')
    orden = models.ForeignKey(
        OrdenProduccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes',
    )
    codigo = models.CharField(max_length=60, unique=True)
    cantidad_inicial = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    cantidad_disponible = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    fecha_produccion = models.DateField(default=timezone.localdate, db_index=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='cuarentena', db_index=True)
    control_calidad = models.CharField(max_length=20, choices=CALIDAD, default='pendiente', db_index=True)
    ubicacion = models.CharField(max_length=160, blank=True, help_text='Cámara, estantería o bodega donde está el lote.')
    observaciones = models.TextField(blank=True)
    demostrativo = models.BooleanField(
        default=False,
        db_index=True,
        editable=False,
        help_text='Viene de una corrida demostrativa: no es existencia real ni cuenta en los indicadores.',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = LoteQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_loteproducto'
        ordering = ('-fecha_produccion', '-pk')
        verbose_name = 'Lote de producto'
        verbose_name_plural = 'Lotes de producto'

    def __str__(self):
        return f'{self.codigo} · {self.producto.nombre}'

    @classmethod
    def crear_desde_orden(cls, orden, producto, cantidad, *, fecha, ubicacion=''):
        # La secuencia sale de los códigos ya usados: la fecha de un lote puede corregirse después.
        secuencia = cls.objects.filter(codigo__startswith=f'{producto.codigo}-{fecha:%y%m%d}-').count() + 1
        vence = fecha + timedelta(days=producto.vida_util_dias) if producto.vida_util_dias else None
        if producto.tipo == 'residuo':
            estado, calidad, disponible = 'retirado', 'no_aplica', Decimal('0')
        elif producto.tipo == 'terminado':
            estado, calidad, disponible = 'cuarentena', 'pendiente', cantidad
        else:
            estado, calidad, disponible = 'disponible', 'no_aplica', cantidad
        return cls.objects.create(
            unidad=orden.unidad,
            producto=producto,
            orden=orden,
            codigo=f'{producto.codigo}-{fecha:%y%m%d}-{secuencia:02d}{"-DEMO" if orden.demostrativa else ""}',
            cantidad_inicial=cantidad,
            cantidad_disponible=disponible,
            fecha_produccion=fecha,
            fecha_vencimiento=vence,
            estado=estado,
            control_calidad=calidad,
            ubicacion=ubicacion if producto.tipo != 'residuo' else '',
            observaciones=f'Lote de la orden {orden.codigo}.',
            demostrativo=orden.demostrativa,
        )

    @property
    def vencido(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.localdate()).days

    def clean(self):
        super().clean()
        if self.cantidad_disponible is not None and self.cantidad_disponible < 0:
            raise ValidationError({'cantidad_disponible': 'La cantidad disponible no puede ser negativa.'})
        if (
            self.cantidad_inicial is not None
            and self.cantidad_disponible is not None
            and self.cantidad_disponible > self.cantidad_inicial
        ):
            raise ValidationError({'cantidad_disponible': 'La cantidad disponible no puede superar la producida.'})
        if self.fecha_vencimiento and self.fecha_produccion and self.fecha_vencimiento < self.fecha_produccion:
            raise ValidationError({'fecha_vencimiento': 'El lote no puede vencer antes de producirse.'})
        if self.producto_id and self.unidad_id and self.producto.unidad_id != self.unidad_id:
            raise ValidationError({'producto': 'El producto debe pertenecer a esta unidad.'})

    def save(self, *args, **kwargs):
        if self.estado == 'disponible' and self.cantidad_disponible is not None and self.cantidad_disponible <= 0:
            self.estado = 'agotado'
        super().save(*args, **kwargs)

    def aprobar_calidad(self):
        if self.estado == 'retirado':
            raise ValidationError('Un lote retirado no vuelve a aprobarse.')
        self.control_calidad = 'aprobado'
        if self.estado == 'cuarentena':
            self.estado = 'disponible' if self.cantidad_disponible > 0 else 'agotado'
        self.save(update_fields=['control_calidad', 'estado', 'actualizado_en'])

    def rechazar_calidad(self, *, usuario, motivo=''):
        if self.estado == 'retirado':
            raise ValidationError('El lote ya está retirado.')
        self.control_calidad = 'rechazado'
        self.save(update_fields=['control_calidad', 'actualizado_en'])
        if self.cantidad_disponible > 0:
            MovimientoProducto.objects.create(
                unidad=self.unidad,
                lote=self,
                tipo='baja',
                cantidad=self.cantidad_disponible,
                motivo=motivo or 'Rechazado en el control de calidad.',
                registrado_por=usuario,
            )
        self.refresh_from_db()
        self.estado = 'retirado'
        self.save(update_fields=['estado', 'actualizado_en'])


class MovimientoProducto(models.Model):
    """Cómo sale un lote: venta, transferencia, muestra, consumo interno o baja."""

    TIPOS = [
        ('venta', 'Venta'),
        ('transferencia', 'Transferencia a otra unidad'),
        ('muestra', 'Muestra o degustación'),
        ('consumo_interno', 'Consumo interno o docencia'),
        ('baja', 'Baja o descarte'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='movimientos_producto')
    lote = models.ForeignKey(LoteProducto, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    destino = models.CharField(
        max_length=200,
        blank=True,
        help_text='Cliente, feria, asignatura o unidad que recibe el producto.',
    )
    unidad_destino = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos_recibidos',
    )
    consumible_destino = models.ForeignKey(
        Consumible,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencias_recibidas',
        help_text='El insumo de la unidad destino que recibe el producto como materia prima.',
    )
    entrada_destino = models.ForeignKey(
        EntradaInventario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        editable=False,
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    movimiento_financiero = models.ForeignKey(
        MovimientoFinancieroUnidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas_producto',
        editable=False,
    )
    referencia = models.CharField(max_length=120, blank=True, help_text='Factura, acta de entrega o comprobante.')
    cliente = models.ForeignKey(
        'finanzas.Cliente', on_delete=models.PROTECT, null=True, blank=True, related_name='compras',
    )
    temperatura_despacho = models.DecimalField(
        'Temperatura al despacho (°C)',
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='La del producto al salir; obligatoria si requiere cadena de frío.',
    )
    motivo = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_producto_registrados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    objects = MovimientoQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_movimientoproducto'
        ordering = ('-fecha', '-pk')
        verbose_name = 'Salida de producto'
        verbose_name_plural = 'Salidas de producto'

    def __str__(self):
        return f'{self.get_tipo_display()} de {self.cantidad} {self.lote.producto.unidad_medida} · {self.lote.codigo}'

    def clean(self):
        super().clean()
        if not self.lote_id:
            return
        lote = self.lote
        if self.unidad_id and lote.unidad_id != self.unidad_id:
            raise ValidationError({'lote': 'El lote debe pertenecer a esta unidad.'})
        if lote.estado in {'agotado', 'retirado'}:
            raise ValidationError({'lote': f'El lote {lote.codigo} ya está {lote.get_estado_display().lower()}.'})
        if lote.demostrativo and (self.unidad_destino_id or self.consumible_destino_id or self.tipo == 'transferencia'):
            raise ValidationError({'lote': 'Un lote demostrativo no entra al inventario de ninguna unidad.'})
        if self.tipo in {'venta', 'transferencia'} and lote.estado != 'disponible':
            raise ValidationError({'lote': 'Solo un lote disponible, con el control de calidad aprobado, sale por venta o transferencia.'})
        if self.cantidad is not None and self.cantidad > lote.cantidad_disponible:
            raise ValidationError({
                'cantidad': f'La salida supera lo disponible en el lote ({lote.cantidad_disponible} {lote.producto.unidad_medida}).'
            })
        if self.tipo == 'transferencia':
            if not self.unidad_destino_id:
                raise ValidationError({'unidad_destino': 'Indica la unidad que recibe el producto.'})
            if self.unidad_destino_id == self.unidad_id:
                raise ValidationError({'unidad_destino': 'La transferencia va a otra unidad.'})
            if self.consumible_destino_id and self.consumible_destino.unidad_id != self.unidad_destino_id:
                raise ValidationError({'consumible_destino': 'El insumo receptor debe pertenecer a la unidad destino.'})
        elif self.tipo == 'consumo_interno':
            # Un intermedio vuelve a entrar en la misma unidad como insumo: la crema en la mantequilla.
            if self.unidad_destino_id:
                raise ValidationError({'unidad_destino': 'El consumo interno queda en la misma unidad.'})
            if self.consumible_destino_id and self.consumible_destino.unidad_id != self.unidad_id:
                raise ValidationError({'consumible_destino': 'El insumo receptor debe pertenecer a esta unidad.'})
        elif self.unidad_destino_id or self.consumible_destino_id:
            raise ValidationError({'unidad_destino': 'Solo una transferencia o un consumo interno tienen destino.'})
        if self.tipo == 'venta' and self.registrado_por_id is None:
            raise ValidationError({'registrado_por': 'Una venta se registra con la cuenta de quien la realiza.'})

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        if not es_nuevo:
            super().save(*args, **kwargs)
            return
        with transaction.atomic():
            lote = LoteProducto.objects.select_for_update().get(pk=self.lote_id)
            self.lote = lote
            self.full_clean()
            if self.tipo == 'venta':
                if self.precio_unitario is None:
                    self.precio_unitario = lote.producto.precio_venta
                self.valor_total = (self.cantidad * self.precio_unitario).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            else:
                self.valor_total = Decimal('0')
            lote.cantidad_disponible = _decimal(lote.cantidad_disponible - self.cantidad)
            lote.save()
            super().save(*args, **kwargs)
            campos = []
            # La venta de un lote demostrativo valida el despacho, pero no es un ingreso.
            if self.tipo == 'venta' and self.valor_total > 0 and not lote.demostrativo:
                self.movimiento_financiero, _ = MovimientoFinancieroUnidad.objects.get_or_create(
                    clave_idempotencia=f'venta-producto-{self.pk}',
                    defaults={
                        'unidad': self.unidad,
                        'tipo': 'ingreso',
                        'categoria': 'producto',
                        'fuente_fondos': 'autogestion',
                        'estado': 'confirmado',
                        'fecha_movimiento': timezone.localdate(self.fecha),
                        'monto': self.valor_total,
                        'metodo': 'otro',
                        'referencia': self.referencia or lote.codigo,
                        'descripcion': (
                            f'Venta de {self.cantidad} {lote.producto.unidad_medida} de '
                            f'{lote.producto.nombre} (lote {lote.codigo})'
                        )[:240],
                        'creado_por': self.registrado_por,
                        'actualizado_por': self.registrado_por,
                    },
                )
                campos.append('movimiento_financiero')
            if self.tipo in {'transferencia', 'consumo_interno'} and self.consumible_destino_id:
                self.entrada_destino = self._recibir_en_destino(lote)
                campos.append('entrada_destino')
            if campos:
                super().save(update_fields=campos)

    def _recibir_en_destino(self, lote):
        """El producto entra como un lote nuevo del insumo receptor.

        En una transferencia lo recibe otra unidad; en un consumo interno, la
        misma unidad: el intermedio vuelve a entrar en la siguiente corrida.
        """
        consumible = self.consumible_destino
        destino = self.unidad_destino or self.unidad
        interno = destino.pk == self.unidad_id
        lote_destino = LoteConsumible.objects.create(
            consumible=consumible,
            codigo=f'{lote.codigo}-{"INT" if interno else format(destino.pk, "03d")}',
            cantidad_inicial=self.cantidad,
            cantidad_actual=Decimal('0'),
            estado='bodega',
            bodega=consumible.ubicacion or 'Recepción',
            fecha_ingreso=timezone.localdate(self.fecha),
            fecha_vencimiento=lote.fecha_vencimiento,
            costo_unitario=self.precio_unitario if self.precio_unitario is not None else lote.producto.precio_venta,
            documento_recepcion=self.referencia,
            creado_por=self.registrado_por,
            observaciones=(
                f'Intermedio de la propia planta: lote {lote.codigo}.' if interno
                else f'Transferido desde {self.unidad.nombre}: lote {lote.codigo}.'
            ),
        )
        return EntradaInventario.objects.create(
            consumible=consumible,
            unidad=destino,
            tipo='ingreso',
            motivo='recepcion',
            cantidad=self.cantidad,
            lote_inventario=lote_destino,
            usuario=self.registrado_por,
            referencia=lote.codigo,
            nota='Intermedio que vuelve a entrar como insumo.' if interno else f'Transferencia desde {self.unidad.nombre}.',
            responsable_costo='institucional',
            costo_unitario=lote_destino.costo_unitario,
        )
