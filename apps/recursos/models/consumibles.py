from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.templatetags.static import static
from django.utils import timezone
from django.conf import settings
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.medios import medios_publicos, validar_medios_referencia
from apps.directorio_unidades.models.core import Unidad


class Consumible(models.Model):
    """Existencia de una unidad: lo que se consume, se usa o se desecha.

    La clasificación dice qué papel juega cada artículo, y es la misma en un
    taller, un laboratorio húmedo y una planta piloto.
    """

    CLASIFICACIONES = [
        ('insumo', 'Insumo'),
        ('reactivo', 'Reactivo'),
        ('agroquimico', 'Agroquímico'),
        ('veterinario', 'Medicamento o insumo veterinario'),
        ('material', 'Material'),
        ('empaque', 'Empaque'),
        ('proteccion', 'Protección'),
        ('limpieza', 'Limpieza'),
        ('otro', 'Otro'),
    ]
    # Cómo se presenta cada clase en el catálogo público y en el panel.
    CLASIFICACION_DETALLE = {
        'insumo': (
            'Insumos',
            'Se transforman en el producto o en la pieza: filamento, resina, '
            'láminas, leche cruda, cultivos, azúcar.',
        ),
        'reactivo': (
            'Reactivos',
            'Sustancias químicas o biológicas que se consumen en un análisis o '
            'un proceso, con lote y vencimiento: agarosa, etanol, kits.',
        ),
        'agroquimico': (
            'Agroquímicos',
            'Fertilizantes, plaguicidas y reguladores de uso agrícola, con lote, '
            'vencimiento y ficha de seguridad.',
        ),
        'veterinario': (
            'Medicamentos e insumos veterinarios',
            'Vacunas, antibióticos, antiparasitarios y biológicos de uso animal, '
            'con lote y vencimiento.',
        ),
        'material': (
            'Materiales',
            'Se usan y se desgastan o se desechan sin formar parte del '
            'resultado: espátulas, camas de impresión, fresas, puntas, tubos.',
        ),
        'empaque': (
            'Empaque',
            'Envases, etiquetas y fundas que salen con el producto.',
        ),
        'proteccion': (
            'Protección',
            'Equipo de protección personal: guantes, mascarillas, cofias, batas.',
        ),
        'limpieza': (
            'Limpieza',
            'Detergentes, sanitizantes y desinfectantes que sostienen la '
            'inocuidad y el orden.',
        ),
        'otro': (
            'Otros',
            'Existencias que no encajan en las clases anteriores.',
        ),
    }

    ORIGEN_ABASTECIMIENTO_CHOICES = [
        ('compra_publica', 'Compra pública institucional'),
        ('recursos_autogestion', 'Recursos generados por servicios'),
        ('proyecto', 'Proyecto de investigación o vinculación'),
        ('donacion', 'Donación'),
        ('transferencia', 'Transferencia entre unidades'),
        ('otro', 'Otro origen documentado'),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='consumibles_inventario',
        help_text='Unidad responsable de esta existencia. Vacío conserva registros generales heredados.',
    )
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    familia = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            'Agrupación técnica dentro del tipo principal. Ejemplos: Filamentos, '
            'Resinas, Reactivos, Vidriería, Materiales planos o Accesorios.'
        ),
    )
    variante = models.CharField(
        max_length=120,
        blank=True,
        help_text='Tipo, diámetro, espesor o formulación que distingue esta existencia.',
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        help_text='Color de esta existencia cuando sea relevante para la selección.',
    )
    presentacion = models.CharField(
        max_length=120,
        blank=True,
        help_text='Presentación de almacenamiento o entrega, por ejemplo bobina de 1 kg.',
    )
    cantidad_por_presentacion = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('1'),
        help_text='Cantidad de la unidad base contenida en cada envase, rollo, bobina o paquete.',
    )
    marca = models.CharField(
        max_length=100,
        blank=True,
        help_text='Marca o fabricante admitido para esta existencia.',
    )
    especificacion_tecnica = models.TextField(
        blank=True,
        help_text='Calidad, composición, tolerancias y requisitos técnicos que debe cumplir.',
    )
    clasificacion = models.CharField(
        max_length=20,
        choices=CLASIFICACIONES,
        default='insumo',
        verbose_name='Tipo de inventario',
        help_text=(
            'Insumo: se transforma en el producto o la pieza. Reactivo: sustancia '
            'química o biológica con lote y vencimiento. Material: se usa y se '
            'desgasta o se desecha sin formar parte del resultado. Empaque, '
            'protección personal y limpieza tienen su propia clase.'
        ),
    )
    unidad_medida = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    instrucciones_solicitud = models.TextField(
        blank=True,
        help_text='Orientación para que el usuario determine la cantidad que debe solicitar.',
    )
    stock_total = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    minimo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0'),
        verbose_name='Stock mínimo',
        help_text='Umbral para mostrar una alerta de reposición. Use 0 para desactivarla.',
    )
    stock_seguridad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0'),
        help_text='Reserva que no debe comprometerse para cubrir retrasos o demanda inesperada.',
    )
    stock_objetivo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0'),
        help_text='Nivel deseado después de reponer. Permite calcular porcentaje y cantidad de compra.',
    )
    plazo_reposicion_dias = models.PositiveIntegerField(
        default=0,
        help_text='Días estimados entre solicitar y recibir una nueva provisión.',
    )
    precio_unitario = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Costo estimado en USD por unidad base; admite fracciones de centavo.',
    )
    origen_abastecimiento = models.CharField(
        max_length=30,
        choices=ORIGEN_ABASTECIMIENTO_CHOICES,
        default='compra_publica',
        help_text='Fuente de recursos con la que normalmente se repone esta existencia.',
    )
    proveedor_referencia = models.CharField(
        max_length=180,
        blank=True,
        help_text='Proveedor, convenio o dependencia de referencia; no constituye una adjudicación.',
    )
    ubicacion = models.CharField(max_length=200, blank=True)
    lote = models.CharField(max_length=100, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    imagen = models.ImageField(upload_to='consumibles/catalogo/', null=True, blank=True)
    imagen_catalogo = models.CharField(
        max_length=255,
        blank=True,
        help_text='Ruta de una imagen estática de referencia usada por datos demostrativos.',
    )
    credito_imagen = models.CharField(
        'Crédito de la imagen',
        max_length=300,
        blank=True,
        help_text='Autor y licencia de la imagen de catálogo cuando no es propia de la unidad.',
    )
    fuente_imagen = models.URLField(
        'Fuente de la imagen',
        max_length=500,
        blank=True,
        help_text='Página de origen de la imagen de catálogo.',
    )
    ficha_tecnica = models.FileField(upload_to='consumibles/fichas/', null=True, blank=True)
    medios_referencia = models.JSONField(
        default=dict, blank=True, validators=[validar_medios_referencia],
        help_text='Fuentes y medios de la variante identificada; no acredita stock, compatibilidad ni recepción.',
    )
    visible_en_reservas = models.BooleanField(
        default=True,
        help_text='Permite mostrar este registro en el catálogo del asistente de reservas.',
    )
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    equipos_compatibles = models.ManyToManyField(
        EquiposServicios,
        through='ConsumiblePorEquipo',
        related_name='insumos_compatibles',
        blank=True,
        help_text='Modelos de equipo en los que este insumo está técnicamente autorizado.',
    )

    class Meta:
        db_table = 'webcitt_consumible'
        ordering = ['unidad__nombre', 'clasificacion', 'familia', 'nombre']
        verbose_name = 'Insumo o material'
        verbose_name_plural = 'Insumos y materiales'

    def __str__(self):
        if self.unidad_medida:
            return f"{self.nombre} ({self.stock_total} {self.unidad_medida})"
        return f"{self.nombre} ({self.stock_total})"

    def clean(self):
        super().clean()
        from apps.recursos.models.adquisiciones import validar_habilitacion
        validar_habilitacion(self)
        errores = {}
        campos_no_negativos = {
            'stock_total': self.stock_total,
            'minimo': self.minimo,
            'stock_seguridad': self.stock_seguridad,
            'stock_objetivo': self.stock_objetivo,
            'precio_unitario': self.precio_unitario,
        }
        for campo, valor in campos_no_negativos.items():
            if valor is not None and valor < 0:
                errores[campo] = 'El valor no puede ser negativo.'
        if self.cantidad_por_presentacion is None or self.cantidad_por_presentacion <= 0:
            errores['cantidad_por_presentacion'] = (
                'La cantidad por presentación debe ser mayor que cero.'
            )
        if self.stock_seguridad and self.minimo and self.stock_seguridad > self.minimo:
            errores['stock_seguridad'] = (
                'El stock de seguridad no puede superar el punto de reposición.'
            )
        if self.stock_objetivo and self.stock_objetivo < max(
            self.minimo or Decimal('0'),
            self.stock_seguridad or Decimal('0'),
        ):
            errores['stock_objetivo'] = (
                'El stock objetivo debe cubrir el punto de reposición y el stock de seguridad.'
            )
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def bajo_minimo(self):
        umbral = max(self.minimo or 0, self.stock_seguridad or 0)
        return umbral > 0 and self.stock_total <= umbral

    @property
    def estado_stock(self):
        if self.stock_total <= 0:
            return 'agotado'
        if self.stock_seguridad > 0 and self.stock_total <= self.stock_seguridad:
            return 'critico'
        if self.bajo_minimo:
            return 'bajo'
        return 'normal'

    @property
    def imagen_publica_url(self):
        if self.imagen:
            try:
                return self.imagen.url
            except ValueError:
                pass
        if self.medios_publicos.get('medios_por_revisar'):
            return ''
        if self.imagen_catalogo:
            return static(self.imagen_catalogo)
        if self.medios_publicos.get('estado') == 'identidad_pendiente':
            return ''
        referencia = f'{self.familia} {self.nombre} {self.variante}'.lower()
        fallbacks = (
            (("filamento", "pla", "petg", "abs"), "img/catalogo/fablab/filamentos-pla-colores.png"),
            (("resina",), "img/catalogo/fablab/resina-fotopolimerica.png"),
            (("mdf",), "img/catalogo/fablab/laminas-mdf-3mm.png"),
            (("acril",), "img/catalogo/fablab/laminas-acrilico-3mm.png"),
            (("cinta",), "img/catalogo/fablab/cinta-enmascarar.png"),
        )
        for palabras, ruta in fallbacks:
            if any(palabra in referencia for palabra in palabras):
                return static(ruta)
        # Sin foto propia ni de catálogo, la página lo ilustra con el ícono de su clase.
        return ''

    @property
    def medios_publicos(self):
        return medios_publicos(self.medios_referencia)

    ICONOS_POR_CLASE = {
        'insumo': 'fas fa-box-open', 'reactivo': 'fas fa-flask', 'agroquimico': 'fas fa-seedling',
        'veterinario': 'fas fa-syringe', 'material': 'fas fa-layer-group',
        'empaque': 'fas fa-box', 'proteccion': 'fas fa-mitten', 'limpieza': 'fas fa-pump-soap', 'otro': 'fas fa-cube',
    }

    @property
    def icono(self):
        return self.ICONOS_POR_CLASE.get(self.clasificacion, 'fas fa-cube')

class ConsumiblePorEquipo(models.Model):

    consumible = models.ForeignKey(Consumible, on_delete=models.CASCADE, related_name='por_equipo')
    equipo = models.ForeignKey(EquiposServicios, on_delete=models.CASCADE, related_name='consumibles')
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    minimo_alerta = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ubicacion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'webcitt_consumibleporequipo'
        unique_together = ('consumible', 'equipo')
        verbose_name = 'Consumible por Equipo'
        verbose_name_plural = 'Consumibles por Equipo'

    def __str__(self):
        return f"{self.consumible.nombre} @ {self.equipo.nombre} ({self.cantidad})"


class LoteConsumible(models.Model):
    """Envase, rollo o lote físico localizable desde su recepción hasta su cierre."""

    ESTADO_CHOICES = (
        ('bodega', 'En bodega'),
        ('en_uso', 'En uso'),
        ('agotado', 'Agotado'),
        ('caducado', 'Caducado'),
        ('extraviado', 'Extraviado'),
        ('retirado', 'Retirado'),
    )

    consumible = models.ForeignKey(
        Consumible,
        on_delete=models.PROTECT,
        related_name='lotes_inventario',
    )
    codigo = models.CharField(max_length=100)
    cantidad_inicial = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='bodega', db_index=True)
    bodega = models.CharField(max_length=120, blank=True)
    estanteria = models.CharField(max_length=80, blank=True)
    posicion = models.CharField(max_length=80, blank=True)
    equipo_en_uso = models.ForeignKey(
        'recursos.UnidadEquipo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lotes_consumibles_en_uso',
    )
    fecha_ingreso = models.DateField(default=timezone.localdate)
    fecha_apertura = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    documento_recepcion = models.CharField(max_length=120, blank=True)
    material_cliente = models.BooleanField(
        default=False,
        help_text='Materia prima que trajo el cliente de un encargo; entra a costo cero y se consume en su corrida.',
    )
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_material_cliente',
        help_text='El encargo al que pertenece la materia prima del cliente.',
    )
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lotes_consumibles_creados',
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lotes_consumibles_actualizados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_loteconsumible'
        ordering = ('consumible__nombre', 'fecha_vencimiento', 'codigo')
        verbose_name = 'Lote físico de insumo'
        verbose_name_plural = 'Lotes físicos de insumos'
        constraints = (
            models.UniqueConstraint(
                fields=('consumible', 'codigo'),
                name='lote_consumible_codigo_unico',
            ),
        )

    def __str__(self):
        return f'{self.codigo} · {self.consumible.nombre}'

    def clean(self):
        super().clean()
        errores = {}
        if self.cantidad_inicial is None or self.cantidad_inicial <= 0:
            errores['cantidad_inicial'] = 'La cantidad recibida debe ser mayor que cero.'
        if self.cantidad_actual is None or self.cantidad_actual < 0:
            errores['cantidad_actual'] = 'La cantidad disponible no puede ser negativa.'
        if (
            self.cantidad_inicial is not None
            and self.cantidad_actual is not None
            and self.cantidad_actual > self.cantidad_inicial
        ):
            errores['cantidad_actual'] = 'La cantidad disponible no puede superar la recibida.'
        if self.estado == 'en_uso' and not self.equipo_en_uso_id:
            errores['equipo_en_uso'] = 'Selecciona el equipo donde se encuentra el lote abierto.'
        if self.estado == 'bodega' and not self.bodega.strip():
            errores['bodega'] = 'Registra la bodega o ambiente donde se encuentra el lote.'
        if self.estado != 'en_uso' and self.equipo_en_uso_id:
            errores['equipo_en_uso'] = 'Solo un lote en uso puede estar asignado a un equipo.'
        if self.estado in {'agotado', 'caducado', 'extraviado', 'retirado'} and self.cantidad_actual > 0:
            errores['estado'] = 'Un lote con saldo disponible no puede marcarse como cerrado.'
        if self.equipo_en_uso_id and self.consumible_id:
            pertenece_a_unidad = (
                self.equipo_en_uso.laboratorio_id == self.consumible.unidad_id
                or self.equipo_en_uso.laboratorios.filter(
                    pk=self.consumible.unidad_id
                ).exists()
            )
            if self.consumible.unidad_id and not pertenece_a_unidad:
                errores['equipo_en_uso'] = (
                    'El equipo no pertenece a la unidad responsable del insumo.'
                )
            compatibilidad_definida = self.consumible.equipos_compatibles.exists()
            if compatibilidad_definida and not self.consumible.equipos_compatibles.filter(
                pk=self.equipo_en_uso.equipo_id
            ).exists():
                errores['equipo_en_uso'] = 'El insumo no está autorizado para ese modelo de equipo.'
        if self.costo_unitario is not None and self.costo_unitario < 0:
            errores['costo_unitario'] = 'El costo unitario no puede ser negativo.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.pk and self.cantidad_actual == 0 and self.estado in {'bodega', 'en_uso'}:
            self.estado = 'agotado'
            self.equipo_en_uso = None
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def ubicacion_completa(self):
        if self.estado == 'en_uso' and self.equipo_en_uso_id:
            return f'En uso · {self.equipo_en_uso.codigo_unidad}'
        partes = [parte for parte in (self.bodega, self.estanteria, self.posicion) if parte]
        return ' · '.join(partes) or 'Ubicación pendiente'

    @property
    def porcentaje_disponible(self):
        if not self.cantidad_inicial:
            return 0
        return int(max(Decimal('0'), min(Decimal('100'), self.cantidad_actual / self.cantidad_inicial * 100)))

    @property
    def vencido(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())

    @property
    def proximo_a_vencer(self):
        if not self.fecha_vencimiento or self.vencido:
            return False
        return self.fecha_vencimiento <= timezone.localdate() + timedelta(days=30)


class EntradaInventario(models.Model):
    TIPO_CHOICES = [('ingreso', 'Ingreso'), ('salida', 'Salida')]
    MOTIVO_CHOICES = (
        ('recepcion', 'Recepción o compra'),
        ('devolucion', 'Devolución al inventario'),
        ('consumo_produccion', 'Consumo en fabricación o servicio'),
        ('consumo_practica', 'Consumo en práctica o docencia'),
        ('desperdicio_equipo', 'Desperdicio por falla del equipo'),
        ('desperdicio_calidad', 'Desperdicio por calidad o proceso'),
        ('caducidad', 'Baja por caducidad'),
        ('extravio', 'Baja por extravío'),
        ('ajuste_positivo', 'Ajuste positivo de conteo'),
        ('ajuste_negativo', 'Ajuste negativo de conteo'),
    )
    RESPONSABLE_COSTO_CHOICES = (
        ('laboratorio', 'Asumido por el laboratorio'),
        ('usuario', 'Facturable al usuario'),
        ('institucional', 'Asumido institucionalmente'),
        ('proyecto', 'Asumido por proyecto'),
        ('no_aplica', 'No aplica'),
    )

    consumible = models.ForeignKey(Consumible, on_delete=models.CASCADE, related_name='entradas')
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='movimientos_consumibles',
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES, default='', blank=True, db_index=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    lote_inventario = models.ForeignKey(
        LoteConsumible,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos',
    )
    equipo = models.ForeignKey(
        'recursos.UnidadEquipo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_consumibles',
    )
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
    )
    incidencia = models.ForeignKey(
        'recursos.IncidenciaEquipo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_desperdicio',
    )
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    responsable_costo = models.CharField(
        max_length=20,
        choices=RESPONSABLE_COSTO_CHOICES,
        default='laboratorio',
    )
    fecha = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    nota = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True)
    clave_idempotencia = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        unique=True,
        editable=False,
        help_text='Evita descontar dos veces el mismo consumo durante un cierre.',
    )
    saldo_resultante = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        db_table = 'webcitt_entradainventario'
        ordering = ['-fecha']
        verbose_name = 'Entrada de Inventario'
        verbose_name_plural = 'Entradas de Inventario'

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad} de {self.consumible.nombre} en {self.fecha.date()}"

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({'cantidad': 'La cantidad debe ser mayor que cero.'})
        if self.consumible_id and self.unidad_id and self.consumible.unidad_id not in (None, self.unidad_id):
            raise ValidationError({'unidad': 'El movimiento debe pertenecer a la unidad del consumible.'})
        if self.lote_inventario_id and self.lote_inventario.consumible_id != self.consumible_id:
            raise ValidationError({'lote_inventario': 'El lote no corresponde al insumo seleccionado.'})
        if (
            self.lote_inventario_id
            and self.unidad_id
            and self.lote_inventario.consumible.unidad_id != self.unidad_id
        ):
            raise ValidationError({'lote_inventario': 'El lote no pertenece a esta unidad.'})
        if self.equipo_id and self.consumible_id:
            pertenece_a_unidad = (
                not self.unidad_id
                or self.equipo.laboratorio_id == self.unidad_id
                or self.equipo.laboratorios.filter(pk=self.unidad_id).exists()
            )
            if not pertenece_a_unidad:
                raise ValidationError({'equipo': 'El equipo no pertenece a esta unidad.'})
            compatibilidad_definida = self.consumible.equipos_compatibles.exists()
            if compatibilidad_definida and not self.consumible.equipos_compatibles.filter(
                pk=self.equipo.equipo_id
            ).exists():
                raise ValidationError({'equipo': 'El insumo no está autorizado para ese equipo.'})
        if self.reserva_id and self.unidad_id and self.reserva.laboratorio_id != self.unidad_id:
            raise ValidationError({'reserva': 'La reserva no pertenece a esta unidad.'})
        if (
            self.incidencia_id
            and self.unidad_id
            and self.incidencia.unidad_id not in (None, self.unidad_id)
        ):
            raise ValidationError({'incidencia': 'La incidencia no pertenece a esta unidad.'})
        if self.incidencia_id and self.equipo_id and self.incidencia.equipo_id != self.equipo_id:
            raise ValidationError({'incidencia': 'La incidencia no corresponde al equipo seleccionado.'})
        motivos_ingreso = {'recepcion', 'devolucion', 'ajuste_positivo'}
        if self.tipo == 'ingreso' and self.motivo not in motivos_ingreso:
            raise ValidationError({'motivo': 'Selecciona una causa válida para el ingreso.'})
        if self.tipo == 'salida' and self.motivo in motivos_ingreso:
            raise ValidationError({'motivo': 'Selecciona una causa válida para la salida.'})
        if self.motivo == 'desperdicio_equipo' and not self.incidencia_id:
            raise ValidationError({'incidencia': 'Vincula la incidencia que ocasionó el desperdicio.'})
        if self.motivo in {'caducidad', 'extravio'} and not self.lote_inventario_id:
            raise ValidationError({'lote_inventario': 'Selecciona el lote físico que se dará de baja.'})
        if self.costo_unitario is not None and self.costo_unitario < 0:
            raise ValidationError({'costo_unitario': 'El costo unitario no puede ser negativo.'})

    def save(self, *args, **kwargs):
        if self.pk is not None:
            anterior = type(self).objects.get(pk=self.pk)
            campos_contables = (
                'consumible_id', 'unidad_id', 'tipo', 'motivo', 'cantidad',
                'lote_inventario_id', 'equipo_id', 'reserva_id', 'incidencia_id',
                'costo_unitario', 'responsable_costo', 'saldo_resultante',
            )
            if any(getattr(anterior, campo) != getattr(self, campo) for campo in campos_contables):
                raise ValidationError(
                    'Los datos contables de un movimiento registrado no se pueden modificar.'
                )
            return super().save(*args, **kwargs)

        if not self.motivo:
            self.motivo = 'recepcion' if self.tipo == 'ingreso' else 'consumo_produccion'
        if self.unidad_id is None and self.consumible_id:
            self.unidad_id = self.consumible.unidad_id
        if (
            self.equipo_id is None
            and self.lote_inventario_id
            and self.lote_inventario.equipo_en_uso_id
        ):
            self.equipo_id = self.lote_inventario.equipo_en_uso_id
        self.full_clean()
        with transaction.atomic():
            consumible = Consumible.objects.select_for_update().get(pk=self.consumible_id)
            factor = 1 if self.tipo == 'ingreso' else -1
            saldo = Decimal(consumible.stock_total or 0) + (Decimal(self.cantidad) * factor)
            if saldo < 0:
                raise ValidationError({'cantidad': 'La salida supera el stock disponible.'})
            lote = None
            if self.lote_inventario_id:
                lote = LoteConsumible.objects.select_for_update().get(pk=self.lote_inventario_id)
                if self.tipo == 'salida' and lote.estado in {
                    'agotado', 'caducado', 'extraviado', 'retirado'
                }:
                    raise ValidationError({'lote_inventario': 'El lote seleccionado ya está cerrado.'})
                if self.motivo in {'caducidad', 'extravio'} and Decimal(self.cantidad) != Decimal(lote.cantidad_actual):
                    raise ValidationError({
                        'cantidad': 'La baja por caducidad o extravío debe retirar todo el saldo del lote.'
                    })
                saldo_lote = Decimal(lote.cantidad_actual or 0) + (Decimal(self.cantidad) * factor)
                if saldo_lote < 0:
                    raise ValidationError({'cantidad': 'La salida supera la cantidad disponible en el lote.'})
                if saldo_lote > lote.cantidad_inicial:
                    raise ValidationError({'cantidad': 'El ingreso supera la cantidad originalmente recibida en el lote.'})
                lote.cantidad_actual = saldo_lote
                if self.motivo == 'caducidad':
                    lote.estado = 'caducado'
                    lote.equipo_en_uso = None
                elif self.motivo == 'extravio':
                    lote.estado = 'extraviado'
                    lote.equipo_en_uso = None
                elif saldo_lote == 0:
                    lote.estado = 'agotado'
                    lote.equipo_en_uso = None
                elif self.tipo == 'ingreso' and lote.estado == 'agotado':
                    lote.estado = 'bodega'
                lote.save()
            consumible.stock_total = saldo
            consumible.save(update_fields=['stock_total', 'fecha_actualizacion'])
            if self.costo_unitario is None:
                self.costo_unitario = lote.costo_unitario if lote and lote.costo_unitario is not None else consumible.precio_unitario
            self.saldo_resultante = saldo
            return super().save(*args, **kwargs)

    @property
    def costo_total(self):
        if self.costo_unitario is None:
            return None
        return self.cantidad * self.costo_unitario

    @property
    def es_desperdicio(self):
        return self.motivo in {'desperdicio_equipo', 'desperdicio_calidad', 'caducidad', 'extravio'}
