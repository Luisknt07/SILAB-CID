"""Seguridad industrial y acceso a la unidad.

Una planta de alimentos no deja entrar a cualquiera de cualquier forma: la
unidad declara lo que exige por categoría de persona (`RequisitoAcceso`),
cada persona acumula sus habilitaciones vigentes (`HabilitacionAcceso`) y
cada sesión registra quién entró, con qué protección y por qué alguien no
entró (`RegistroIngreso`). Un laboratorio sin requisitos no cambia en nada.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad

CATEGORIAS_PERSONA = [
    ('estudiante', 'Estudiantes'),
    ('docente', 'Docentes e investigadores'),
    ('personal', 'Personal de la unidad'),
    ('externo', 'Personas externas'),
    ('visitante', 'Visitantes'),
]
CLAVES_CATEGORIA = {clave for clave, _ in CATEGORIAS_PERSONA}


class RequisitoAcceso(models.Model):
    """Algo que la unidad exige para entrar: a quién y cuándo se comprueba."""

    TIPOS = [
        ('induccion', 'Inducción de seguridad e inocuidad'),
        ('sanitario', 'Habilitación sanitaria'),
        ('documento', 'Documento o autorización'),
        ('proteccion', 'Protección personal'),
        ('restriccion', 'Restricción de ingreso'),
    ]
    # Lo que se habilita por persona con vigencia; la protección y las
    # restricciones se verifican en la puerta en cada sesión.
    TIPOS_HABILITABLES = ('induccion', 'sanitario', 'documento')
    MOMENTOS = [
        ('reservar', 'Al reservar y al ingresar'),
        ('ingresar', 'Solo al ingresar'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='requisitos_acceso')
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=12, choices=TIPOS)
    aplica_a = models.JSONField(
        default=list,
        blank=True,
        help_text='Categorías de persona a las que aplica; vacío es todas.',
    )
    obligatorio = models.BooleanField(default=True)
    momento = models.CharField(max_length=12, choices=MOMENTOS, default='reservar')
    vigencia_dias = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Días que dura la habilitación; vacío es sin vencimiento.',
    )
    consumible = models.ForeignKey(
        'recursos.Consumible',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitos_acceso',
        help_text='La protección que la unidad entrega por persona y descuenta del inventario.',
    )
    cantidad_por_persona = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal('1'),
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'webcitt_requisitoacceso'
        ordering = ('unidad', 'orden', 'nombre')
        constraints = [
            models.UniqueConstraint(fields=('unidad', 'codigo'), name='requisito_acceso_unico_por_unidad'),
        ]
        verbose_name = 'Requisito de acceso'
        verbose_name_plural = 'Requisitos de acceso'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    @property
    def habilitable(self):
        return self.tipo in self.TIPOS_HABILITABLES

    def aplica(self, categoria):
        return not self.aplica_a or categoria in self.aplica_a

    @property
    def categorias_display(self):
        nombres = dict(CATEGORIAS_PERSONA)
        return ', '.join(nombres[clave] for clave in self.aplica_a if clave in nombres) or 'Todas las personas'

    def clean(self):
        super().clean()
        if not isinstance(self.aplica_a, list) or any(clave not in CLAVES_CATEGORIA for clave in self.aplica_a):
            raise ValidationError({'aplica_a': 'Indica categorías de persona válidas.'})
        if self.consumible_id and self.tipo != 'proteccion':
            raise ValidationError({'consumible': 'Solo la protección personal se entrega desde el inventario.'})
        if self.consumible_id and self.consumible.unidad_id != self.unidad_id:
            raise ValidationError({'consumible': 'La protección debe ser un insumo de esta unidad.'})
        if not self.habilitable:
            self.vigencia_dias = None


class HabilitacionAcceso(models.Model):
    """Una persona cumple un requisito habilitable durante un tiempo."""

    ORIGENES = [
        ('sesion', 'Sesión de inducción en la unidad'),
        ('documento', 'Documento presentado'),
        ('manual', 'Registro de la unidad'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habilitaciones_acceso')
    requisito = models.ForeignKey(RequisitoAcceso, on_delete=models.CASCADE, related_name='habilitaciones')
    fecha = models.DateField(default=timezone.localdate)
    vence = models.DateField(null=True, blank=True)
    origen = models.CharField(max_length=12, choices=ORIGENES, default='manual')
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='habilitaciones_otorgadas',
        help_text='La sesión de inducción que la otorgó.',
    )
    documento = models.CharField(
        max_length=120,
        blank=True,
        help_text='Número o referencia del certificado, carné o autorización.',
    )
    otorgada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='habilitaciones_concedidas',
    )
    observaciones = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_habilitacionacceso'
        ordering = ('-fecha', '-pk')
        verbose_name = 'Habilitación de acceso'
        verbose_name_plural = 'Habilitaciones de acceso'

    def __str__(self):
        return f'{self.requisito.nombre} · {self.usuario.get_username()}'

    def vigente_en(self, fecha=None):
        fecha = fecha or timezone.localdate()
        return self.activa and self.fecha <= fecha and (self.vence is None or self.vence >= fecha)

    def clean(self):
        super().clean()
        if self.requisito_id and not self.requisito.habilitable:
            raise ValidationError({
                'requisito': 'La protección y las restricciones se verifican al ingresar; no se habilitan por persona.',
            })
        if self.vence and self.fecha and self.vence < self.fecha:
            raise ValidationError({'vence': 'La vigencia no puede terminar antes de la fecha en que se otorga.'})

    def save(self, *args, **kwargs):
        if self.vence is None and self.requisito_id and self.requisito.vigencia_dias:
            self.vence = self.fecha + timedelta(days=self.requisito.vigencia_dias)
        super().save(*args, **kwargs)


class RegistroIngreso(models.Model):
    """Quién entró a la sesión, con qué protección, o por qué no entró."""

    reserva = models.ForeignKey('reservas.Reserva', on_delete=models.CASCADE, related_name='ingresos')
    participante = models.ForeignKey(
        'reservas.RegistroParticipanteReserva',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_a_unidades',
    )
    nombre = models.CharField(max_length=180)
    categoria = models.CharField(max_length=12, choices=CATEGORIAS_PERSONA, default='externo')
    ingresa = models.BooleanField(default=True)
    motivo = models.CharField(
        max_length=200,
        blank=True,
        help_text='Por qué no ingresa, o una observación del ingreso.',
    )
    hora_ingreso = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    proteccion_verificada = models.BooleanField(default=False)
    restricciones_verificadas = models.BooleanField(default=False)
    habilitaciones_vigentes = models.BooleanField(default=False)
    pendientes = models.JSONField(
        default=list,
        blank=True,
        help_text='Lo que faltaba en el momento del ingreso.',
    )
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_registrados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_registroingreso'
        ordering = ('reserva', 'nombre')
        constraints = [
            models.UniqueConstraint(
                fields=('reserva', 'participante'),
                condition=Q(participante__isnull=False),
                name='ingreso_unico_por_participante',
            ),
        ]
        verbose_name = 'Registro de ingreso'
        verbose_name_plural = 'Registros de ingreso'

    def __str__(self):
        estado = 'ingresa' if self.ingresa else 'no ingresa'
        return f'{self.nombre} · {estado}'
