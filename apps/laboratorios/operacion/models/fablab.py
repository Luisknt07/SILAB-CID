from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.consumibles import Consumible


class FablabService(models.Model):
    TIPOS = [
        ('fabricacion', 'Fabricación y prototipado'),
        ('analisis', 'Análisis y ensayos'),
        ('practica', 'Práctica de docencia'),
        ('uso_equipo', 'Uso de equipos'),
        ('produccion', 'Producción'),
        ('desarrollo_producto', 'Desarrollo de producto'),
        ('maquila_academica', 'Maquila académica'),
        ('escalamiento', 'Escalamiento'),
        ('capacitacion', 'Capacitación'),
        ('visita', 'Visita técnica'),
        ('soporte', 'Soporte especializado'),
        ('otro', 'Otro'),
    ]
    TIPOS_CATALOGO_PLANTA = [
        ('practica', 'Prácticas docentes'),
        ('desarrollo_producto', 'Desarrollo de producto'),
        ('maquila_academica', 'Maquila académica'),
        ('analisis', 'Análisis de laboratorio'),
        ('escalamiento', 'Escalamiento'),
        ('capacitacion', 'Capacitación'),
        ('uso_equipo', 'Alquiler de equipos'),
    ]

    code = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    imagen_referencial = models.ImageField(
        upload_to='servicios/catalogo/',
        blank=True,
        null=True,
        help_text=(
            'Fotografía o imagen que identifica el servicio en el catálogo público. '
            'Se recomienda formato horizontal y relación 4:3.'
        ),
    )
    imagen_catalogo = models.CharField(
        'Ruta de imagen demostrativa',
        max_length=255,
        blank=True,
        help_text=(
            'Ruta relativa en archivos estáticos usada por datos demostrativos. '
            'La imagen subida tiene prioridad.'
        ),
    )
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios_operativos',
        help_text='Vacío mantiene el servicio disponible como opción general heredada.',
    )
    tipo_servicio = models.CharField(max_length=20, choices=TIPOS, default='fabricacion')
    familia = models.CharField(
        'Familia o categoría del servicio',
        max_length=80,
        blank=True,
        help_text=(
            'Agrupa los servicios afines en el catálogo (por ejemplo, Impresión 3D). '
            'Vacío usa el tipo de servicio.'
        ),
    )
    activo = models.BooleanField(default=True)
    publico = models.BooleanField(default=True)
    receta = models.ForeignKey(
        'plantas_operacion.Receta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios',
        help_text='Proceso que el servicio ejecuta por encargo; sus insumos por lote son los materiales del servicio.',
    )
    materia_prima_cliente = models.BooleanField(
        default=False,
        help_text='El cliente puede traer la materia prima de la corrida base (maquila).',
    )
    requiere_reserva = models.BooleanField(default=False)
    requiere_revision_tecnica = models.BooleanField(default=False)
    requiere_cotizacion = models.BooleanField(default=False)
    requiere_archivos = models.BooleanField(
        default=False,
        help_text='Exige al usuario adjuntar un modelo, plano o referencia técnica.',
    )
    resultado_entregado = models.TextField(
        blank=True,
        help_text=(
            'Explica el producto, archivo, pieza o resultado concreto que recibirá '
            'el solicitante.'
        ),
    )
    cuando_elegirlo = models.TextField(
        blank=True,
        help_text=(
            'Orienta al usuario sobre los casos en los que este servicio es la '
            'alternativa adecuada.'
        ),
    )
    tiempo_estimado_texto = models.CharField(
        max_length=120,
        blank=True,
        help_text='Referencia comprensible, por ejemplo: 1 a 3 días laborables.',
    )
    requisitos_usuario = models.TextField(
        blank=True,
        help_text='Información y condiciones que el usuario debe conocer antes de solicitar.',
    )
    unidad_cobro = models.CharField(
        'Unidad de facturación',
        max_length=80,
        default='Por solicitud',
        help_text='Ejemplos: por solicitud, por muestra, por hora o por corrida.',
    )
    responsable = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios_responsables',
        help_text='Responsable público del servicio; debe pertenecer a la misma unidad.',
    )
    formatos_archivo = models.CharField(
        max_length=255,
        blank=True,
        default='PDF, STL, OBJ, 3MF, STEP, DXF, DWG, SVG, imágenes o ZIP',
    )
    tutorial_youtube_url = models.URLField(
        blank=True,
        help_text='Enlace público al videotutorial de YouTube relacionado con el servicio.',
    )
    tutorial_titulo = models.CharField(
        max_length=180,
        blank=True,
        help_text='Título breve que se mostrará junto al videotutorial.',
    )
    permite_modelo_listo = models.BooleanField(
        default=True,
        help_text='Permite que el usuario entregue un modelo o archivo preparado.',
    )
    permite_diseno_asistido = models.BooleanField(
        default=True,
        help_text='Permite que el usuario diseñe en el laboratorio con asesoría.',
    )
    permite_diseno_completo = models.BooleanField(
        default=True,
        help_text='Permite encargar al laboratorio el diseño y la ejecución completos.',
    )
    tarifa_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    horas_equipo_estimadas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    costo_hora_equipo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    horas_mano_obra_estimadas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    costo_hora_mano_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_diseno_asistido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_diseno_completo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento_estudiante = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    descuento_personal = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    descuento_externo = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'webcitt_fablabservice'
        verbose_name = 'Servicio operativo de unidad'
        verbose_name_plural = 'Servicios operativos de unidades'
        ordering = ['unidad__nombre', 'code']

    def __str__(self):
        return f"{self.code} - {self.nombre}"

    @property
    def familia_catalogo(self):
        """Categoría con la que se agrupa en el catálogo de solicitud."""
        return self.familia.strip() or self.get_tipo_servicio_display()

    @property
    def costo_referencial(self):
        """Costo fijo de una solicitud antes de materiales y diseño."""
        return (
            Decimal(self.tarifa_base or 0)
            + Decimal(self.horas_equipo_estimadas or 0) * Decimal(self.costo_hora_equipo or 0)
            + Decimal(self.horas_mano_obra_estimadas or 0) * Decimal(self.costo_hora_mano_obra or 0)
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def tarifa_referencial(self, descuento):
        porcentaje = min(Decimal('100'), max(Decimal('0'), Decimal(descuento or 0)))
        return (
            self.costo_referencial * (Decimal('100') - porcentaje) / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def tarifa_interna_referencial(self):
        return self.tarifa_referencial(self.descuento_personal)

    @property
    def tarifa_externa_referencial(self):
        return self.tarifa_referencial(self.descuento_externo)

    def clean(self):
        super().clean()
        if self.responsable_id and self.unidad_id and self.responsable.unidad_id != self.unidad_id:
            raise ValidationError({
                'responsable': 'El responsable debe pertenecer a la unidad del servicio.',
            })


class SolicitudFabricacion(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    TIPO_TRABAJO = [
        ('investigacion', 'Proyecto de Investigación'),
        ('academico', 'Proyecto Académico/Clase'),
        ('servicio_institucional', 'Servicio Institucional'),
        ('uso_equipo', 'Uso de Equipos/Préstamo'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_revision', 'En revisión'),
        ('estimada', 'Estimada'),
        ('en_fabricacion', 'En fabricación'),
        ('completada', 'Completada'),
        ('rechazada', 'Rechazada'),
    ]
    REVISION_LABORATORISTA_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_operativas',
    )
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_operativas',
    )
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_fablab')
    departamento = models.CharField(max_length=200, blank=True, null=True)
    fecha_solicitud = models.DateField(default=timezone.now)
    tipo_trabajo = models.CharField(max_length=30, choices=TIPO_TRABAJO, default='investigacion')
    nombre_proyecto = models.CharField(max_length=255, blank=True, null=True)
    descripcion_general = models.TextField(blank=True, null=True)
    servicios = models.ManyToManyField(FablabService, db_table='webcitt_solicitudfabricacion_servicios', blank=True, related_name='solicitudes')
    materiales_principales = models.TextField(blank=True, null=True, help_text='Ej: MDF 12mm, Acrílico 5mm, Filamento PLA')

    # Consumibles solicitados (through)
    consumibles = models.ManyToManyField('recursos.Consumible', through='SolicitudConsumible', blank=True)

    # Máquinas / recursos específicos
    maquinas_requeridas = models.ManyToManyField('recursos.EquiposServicios', db_table='webcitt_solicitudfabricacion_maquinas_requeridas', blank=True, related_name='solicitudes_requeridas')
    tiempo_estimado_horas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    costo_materiales_estimado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    maquina_alto_costo = models.ForeignKey('recursos.EquiposServicios', on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_maquina_costo')

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
    )
    revision_laboratorista = models.CharField(
        max_length=20,
        choices=REVISION_LABORATORISTA_CHOICES,
        default='pendiente',
    )
    fecha_revision_laboratorista = models.DateTimeField(null=True, blank=True)
    observaciones_laboratorista = models.TextField(blank=True, null=True)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='normal')
    responsable_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_operativas_asignadas',
    )
    fecha_programada_inicio = models.DateTimeField(null=True, blank=True)
    fecha_programada_fin = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True, editable=False)
    notas_operativas = models.TextField(blank=True)
    aprobada_decanato = models.BooleanField(default=False)
    fecha_aprobacion_decanato = models.DateTimeField(null=True, blank=True)
    observaciones_decanato = models.TextField(blank=True, null=True)
    costo_amortizado_decanato = models.BooleanField(default=False)
    fecha_amortizacion_decanato = models.DateTimeField(null=True, blank=True)
    comprobante_pago = models.FileField(
        upload_to='comprobantes_pago/',
        blank=True,
        null=True,
    )

    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_solicitudfabricacion'
        verbose_name = 'Solicitud de servicio de unidad'
        verbose_name_plural = 'Solicitudes de servicios de unidades'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        titulo = self.nombre_proyecto or f"Solicitud {self.pk}"
        return f"{titulo} - {self.get_tipo_trabajo_display()}"

    def clean(self):
        super().clean()
        if self.reserva_id and self.unidad_id and self.reserva.laboratorio_id != self.unidad_id:
            raise ValidationError({'reserva': 'La reserva debe pertenecer a la misma unidad.'})
        if self.pk and self.unidad_id:
            incompatibles = self.servicios.exclude(unidad__isnull=True).exclude(unidad_id=self.unidad_id)
            if incompatibles.exists():
                raise ValidationError({'servicios': 'Todos los servicios deben pertenecer a la unidad seleccionada.'})
        if (
            self.fecha_programada_inicio
            and self.fecha_programada_fin
            and self.fecha_programada_fin <= self.fecha_programada_inicio
        ):
            raise ValidationError({'fecha_programada_fin': 'La fecha final debe ser posterior al inicio.'})

    def save(self, *args, **kwargs):
        anterior = None
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values(
                'revision_laboratorista',
                'aprobada_decanato',
                'costo_amortizado_decanato',
            ).first()

        cambio_revision = not anterior or (
            anterior['revision_laboratorista'] != self.revision_laboratorista
        )
        if cambio_revision:
            if self.revision_laboratorista == 'aprobada':
                self.fecha_revision_laboratorista = timezone.now()
                self.estado = 'estimada'
            elif self.revision_laboratorista == 'rechazada':
                self.fecha_revision_laboratorista = timezone.now()
                self.estado = 'rechazada'
            else:
                self.fecha_revision_laboratorista = None

        if self.aprobada_decanato:
            if not anterior or not anterior['aprobada_decanato']:
                self.fecha_aprobacion_decanato = timezone.now()
        else:
            self.fecha_aprobacion_decanato = None

        if self.costo_amortizado_decanato:
            if not anterior or not anterior['costo_amortizado_decanato']:
                self.fecha_amortizacion_decanato = timezone.now()
        else:
            self.fecha_amortizacion_decanato = None

        if self.estado == 'completada' and not self.fecha_cierre:
            self.fecha_cierre = timezone.now()
        elif self.estado != 'completada':
            self.fecha_cierre = None

        super().save(*args, **kwargs)

    @property
    def numero_orden(self):
        prefijo = self.unidad.codigo if self.unidad_id and self.unidad.codigo else 'UPEC'
        return f"OT-{prefijo}-{self.pk or 0:05d}"


class SolicitudConsumible(models.Model):
    solicitud = models.ForeignKey(SolicitudFabricacion, on_delete=models.CASCADE, related_name='solicitud_consumibles')
    consumible = models.ForeignKey(Consumible, on_delete=models.CASCADE, related_name='solicitud_entries')
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    uso_propio = models.BooleanField(default=False, help_text='El solicitante ya dispone del insumo')
    solicitar_compra = models.BooleanField(default=False, help_text='Solicitar compra si no dispone')
    notas = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'webcitt_solicitudconsumible'
        verbose_name = 'Consumible en Solicitud'
        verbose_name_plural = 'Consumibles en Solicitud'
        unique_together = ('solicitud', 'consumible')

    def __str__(self):
        return f"{self.consumible.nombre} x {self.cantidad} ({self.solicitud})"

    def clean(self):
        super().clean()
        errores = {}
        if self.solicitud_id and self.consumible_id and self.solicitud.unidad_id and (
            self.consumible.unidad_id != self.solicitud.unidad_id
        ):
            errores['consumible'] = 'El insumo debe pertenecer a la unidad de la solicitud.'
        if self.cantidad is not None and self.cantidad < 0:
            errores['cantidad'] = 'La cantidad no puede ser negativa.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class FablabServiceConsumible(models.Model):
    service = models.ForeignKey(FablabService, on_delete=models.CASCADE, related_name='service_consumibles')
    consumible = models.ForeignKey(Consumible, on_delete=models.CASCADE, related_name='service_usages')
    cantidad_sugerida = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    obligatorio = models.BooleanField(default=False, help_text='Marcar si este consumible es requerido por el servicio')
    notas = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'webcitt_fablabserviceconsumible'
        verbose_name = 'Consumible por Servicio'
        verbose_name_plural = 'Consumibles por Servicio'
        unique_together = ('service', 'consumible')

    def __str__(self):
        return f"{self.service.code} - {self.consumible.nombre} ({self.cantidad_sugerida})"

    def clean(self):
        super().clean()
        errores = {}
        if self.service_id and self.consumible_id and self.service.unidad_id and (
            self.consumible.unidad_id != self.service.unidad_id
        ):
            errores['consumible'] = 'El insumo debe pertenecer a la unidad del servicio.'
        if self.cantidad_sugerida is not None and self.cantidad_sugerida < 0:
            errores['cantidad_sugerida'] = 'La cantidad no puede ser negativa.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
