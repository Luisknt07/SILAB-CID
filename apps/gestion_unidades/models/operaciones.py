
from apps.core.presentation.catalogos import tipos_usuario
from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.directorio_unidades.models.core import Unidad
from apps.core.models.periodos import PeriodoAcademico
from apps.reservas.models.reservas import PROPOSITO_INSTITUCIONAL_CHOICES


def hora_de_apertura_por_omision():
    """Las ocho en punto, la primera hora que las unidades ofrecen."""
    return time(8, 0)


def hora_de_cierre_por_omision():
    """Las seis de la tarde, la ultima hora que las unidades ofrecen.

    Va en una funcion y no como valor fijo porque Django avisa cuando una hora
    fija por omision coincide con la hora actual: el aviso aparecia solo a las
    seis de la tarde y tumbaba la comprobacion del sistema a esa hora.
    """
    return time(18, 0)


class ConfiguracionOperativaUnidad(models.Model):
    """Activa capacidades operativas sin acoplarlas a un laboratorio concreto."""

    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name="configuracion_operativa",
    )
    solicitudes_servicio = models.BooleanField(default=True)
    reservas_espacios = models.BooleanField(default=True)
    reservas_equipos = models.BooleanField(default=True)
    inventario_equipos = models.BooleanField(default=True)
    mantenimiento_equipos = models.BooleanField(default=True)
    incidencias_equipos = models.BooleanField(default=True)
    ciclo_vida_equipos = models.BooleanField(default=True)
    consumibles = models.BooleanField(default=True)
    revision_tecnica = models.BooleanField(default=True)
    cotizacion_costos = models.BooleanField(default=True)
    tarifa_referencial_hora_espacio = models.DecimalField(
        "Valor referencial por hora de espacio",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Costo comparable del uso de un espacio; no implica que se cobre al usuario.",
    )
    tarifa_referencial_hora_equipo = models.DecimalField(
        "Valor referencial por hora de equipo",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Costo comparable por cada unidad física reservada y hora.",
    )
    tarifa_referencial_hora_software = models.DecimalField(
        "Valor referencial por hora de software",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Costo comparable por cada software o licencia reservada y hora.",
    )
    tarifa_referencial_hora_acompanamiento = models.DecimalField(
        "Valor referencial por hora de acompañamiento",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Valor de referencia del acompañamiento técnico durante la reserva.",
    )
    aporte_institucional_recursos_pct = models.DecimalField(
        "Aporte institucional en reservas de recursos (%)",
        editable=False,
        max_digits=5,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=(
            "Campo histórico. La política vigente cubre siempre el 100 % de recursos y personal."
        ),
    )
    # Compatibilidad histórica: estas banderas ya no habilitan cobros.
    # La política vigente solo traslada al usuario los materiales consumidos.
    cobrar_tarifa_base = models.BooleanField(
        "Cobrar la tarifa base del servicio",
        editable=False,
        default=False,
        help_text="Desactivado: la tarifa base se muestra como referencia y la asume la Universidad.",
    )
    cobrar_uso_equipo = models.BooleanField(
        "Cobrar el uso de equipo",
        editable=False,
        default=False,
        help_text="Horas de máquina estimadas por pieza multiplicadas por el costo hora del servicio.",
    )
    cobrar_uso_equipo_ejecucion = models.BooleanField(
        "Cobrar el uso de equipo cuando el laboratorio ejecuta",
        editable=False,
        default=False,
        help_text=(
            'Campo histórico sin efecto en cobros nuevos. El uso de equipo lo asume la UPEC.'
        ),
    )
    cobrar_mano_obra = models.BooleanField(
        "Cobrar la mano de obra",
        editable=False,
        default=False,
        help_text="Horas de trabajo técnico estimadas por pieza multiplicadas por su costo hora.",
    )
    cobrar_diseno = models.BooleanField(
        "Cobrar el diseño realizado por el laboratorio",
        editable=False,
        default=False,
        help_text=(
            "Campo histórico sin efecto en cobros nuevos. El diseño lo asume la UPEC."
        ),
    )
    # Impuesto: desactivado mientras la unidad no declare; se integra a
    # estimaciones, comprobantes y liquidaciones cuando se activa.
    aplicar_iva = models.BooleanField(
        "Aplicar IVA al valor del usuario",
        default=False,
        help_text=(
            "Agrega el IVA sobre el valor a cargo del usuario en estimaciones, "
            "comprobantes y liquidaciones. Desactivado mientras no se declare."
        ),
    )
    porcentaje_iva = models.DecimalField(
        "Porcentaje de IVA",
        max_digits=5,
        decimal_places=2,
        default=15,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje vigente del impuesto al valor agregado.",
    )
    ordenes_trabajo = models.BooleanField(default=True)
    seguimiento = models.BooleanField(default=True)
    dias_antelacion_guia = models.PositiveSmallIntegerField(
        default=2,
        help_text='Días hábiles de antelación con que una sesión programada debe tener su guía aprobada.',
    )
    acepta_visitas = models.BooleanField(
        'Acepta visitas',
        default=True,
        help_text='Permite solicitar visitas. Solo las áreas marcadas como visitables forman parte del recorrido publicado.',
    )
    personas_por_guia = models.PositiveSmallIntegerField(
        default=15,
        help_text='Personas que acompaña un guía; el grupo exige tantos guías como haga falta.',
    )
    visitas_texto = models.TextField(
        'Oferta de visitas',
        blank=True,
        help_text='Lo que la ficha publica sobre las visitas: qué se recorre, para quién y en qué condiciones.',
    )
    registra_produccion = models.BooleanField(
        'Registra producción',
        default=False,
        help_text=(
            'Activa productos, recetas, órdenes de producción, lotes y salidas. '
            'Propio de las plantas piloto y de los centros que producen para la '
            'venta o para otra unidad.'
        ),
    )
    tarifa_energia_kwh = models.DecimalField(
        'Tarifa de energía eléctrica (USD/kWh)',
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=(
            'Costo de las corridas de producción: la potencia de cada equipo por el '
            'tiempo que trabaja. Vacía, la energía queda sin dato.'
        ),
    )
    costo_hora_persona = models.DecimalField(
        'Costo de la hora-persona en producción (USD/h)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=(
            'Costo de las corridas de producción: las horas-persona de cada etapa. '
            'Vacío, la mano de obra queda sin dato.'
        ),
    )
    indicadores_reportes = models.BooleanField(default=True)
    tutorial_recursos_url = models.URLField(
        'Videotutorial para reservar recursos',
        blank=True,
        help_text='Video genérico que explica la ruta para reservar espacios, equipos o software.',
    )
    tutorial_servicios_url = models.URLField(
        'Videotutorial para encargar un servicio',
        blank=True,
        help_text='Video genérico que explica la ruta para solicitar un resultado al laboratorio.',
    )
    # Cómo llama esta unidad a lo que produce una sesión. Un taller fabrica
    # piezas; un laboratorio húmedo procesa muestras y uno de materiales corre
    # ensayos. La palabra se usa en el asistente, el panel y el comprobante.
    UNIDADES_DE_TRABAJO = [
        ('piezas', 'Piezas'),
        ('muestras', 'Muestras'),
        ('ensayos', 'Ensayos'),
        ('prototipos', 'Prototipos'),
        ('lotes', 'Lotes'),
        ('ciclos', 'Ciclos'),
    ]
    unidad_de_trabajo = models.CharField(
        "Cómo se llama lo que se produce",
        max_length=10,
        choices=UNIDADES_DE_TRABAJO,
        default='piezas',
        help_text=(
            "Palabra con la que la unidad cuenta el trabajo de una sesión. "
            "El asistente pide la cantidad de material por cada una."
        ),
    )
    # Horario que la unidad ofrece a quien reserva. La jornada operativa puede
    # ser más amplia (`HorarioOperacionUnidad`): esta es la franja que se
    # publica, y cada laboratorio la ajusta a su realidad.
    hora_apertura_atencion = models.TimeField(
        "Primera hora que se ofrece",
        default=hora_de_apertura_por_omision,
        help_text=(
            "Hora en punto desde la que los usuarios pueden reservar. Un "
            "laboratorio que atiende más temprano la adelanta a las 07:00."
        ),
    )
    hora_cierre_atencion = models.TimeField(
        "Hora en que termina la atención",
        default=hora_de_cierre_por_omision,
        help_text=(
            "Hora en punto hasta la que los usuarios pueden reservar. Un "
            "laboratorio que atiende más tarde la extiende hasta las 20:00."
        ),
    )

    class Meta:
        db_table = 'webcitt_configuracionoperativaunidad'
        verbose_name = "Configuración operativa de la unidad"
        verbose_name_plural = "Configuraciones operativas de las unidades"

    def __str__(self):
        return f"Operación de {self.unidad.nombre}"

    # Singular, plural y género: «prototipo» y «ensayo» son masculinos, y sin
    # esa marca el asistente escribía «una prototipo».
    PALABRAS_TRABAJO = {
        'piezas': ('pieza', 'piezas', 'f'),
        'muestras': ('muestra', 'muestras', 'f'),
        'ensayos': ('ensayo', 'ensayos', 'm'),
        'prototipos': ('prototipo', 'prototipos', 'm'),
        # Una planta piloto produce lotes; un centro experimental corre ciclos.
        'lotes': ('lote', 'lotes', 'm'),
        'ciclos': ('ciclo', 'ciclos', 'm'),
    }

    @property
    def palabras_trabajo(self):
        """Singular y plural de lo que la unidad produce en una sesión."""
        singular, plural, _ = self.PALABRAS_TRABAJO[self.unidad_de_trabajo]
        return singular, plural

    @property
    def formas_trabajo(self):
        """Las formas que tienen que concordar con la palabra de la unidad."""
        singular, plural, genero = self.PALABRAS_TRABAJO[self.unidad_de_trabajo]
        femenino = genero == 'f'
        return {
            'singular': singular,
            'plural': plural,
            'genero': genero,
            'un': 'una' if femenino else 'un',
            'los': 'las' if femenino else 'los',
            'cuantos': 'cuántas' if femenino else 'cuántos',
            'obtenidos': 'obtenidas' if femenino else 'obtenidos',
            'juntos': 'juntas' if femenino else 'juntos',
        }

    def clean(self):
        super().clean()
        errores = {}
        for campo in ("hora_apertura_atencion", "hora_cierre_atencion"):
            valor = getattr(self, campo, None)
            if valor and (valor.minute or valor.second):
                errores[campo] = (
                    "La agenda trabaja por horas completas: usa una hora en punto."
                )
        if (
            not errores
            and self.hora_apertura_atencion
            and self.hora_cierre_atencion
            and self.hora_cierre_atencion <= self.hora_apertura_atencion
        ):
            errores["hora_cierre_atencion"] = (
                "La atención debe terminar después de la hora en que empieza."
            )
        if errores:
            raise ValidationError(errores)

class ReporteOperativoUnidad(ConfiguracionOperativaUnidad):
    """Proyección administrativa de indicadores; no crea una tabla adicional."""

    class Meta:
        db_table = 'webcitt_configuracionoperativaunidad'
        proxy = True
        verbose_name = "Reporte operativo"
        verbose_name_plural = "Reportes operativos"


# Hora de almuerzo: las reservas de recursos no la ocupan (lo comprueba
# _validar_horario_operativo) y el asistente la muestra bloqueada. Solo el
# panel de gestión la registra; los servicios se planifican por la cola.
HORA_ALMUERZO = 13

# Horario de atención con el que arranca una unidad: de 08:00 a 18:00. Cada
# laboratorio lo ajusta en su configuración operativa, porque uno abre a las
# 07:00 y otro cierra a las 20:00.
HORA_APERTURA = 8
HORA_CIERRE_ATENCION = 18


def ventana_atencion(configuracion=None, es_administrador=False):
    """Primera hora y hora de cierre (exclusiva) que se pueden reservar.

    La administración de la unidad no queda limitada por la franja publicada:
    registra dentro de la jornada operativa completa, que es la que declara
    `HorarioOperacionUnidad`.
    """
    if es_administrador:
        return 0, 24
    apertura = getattr(configuracion, "hora_apertura_atencion", None)
    cierre = getattr(configuracion, "hora_cierre_atencion", None)
    return (
        apertura.hour if apertura else HORA_APERTURA,
        cierre.hour if cierre else HORA_CIERRE_ATENCION,
    )


class HorarioOperacionUnidad(models.Model):
    """Jornada reservable de una unidad, general o específica de un período.

    Cuando existe al menos una jornada vinculada a un período, ese conjunto
    reemplaza por completo el horario general durante las fechas del período.
    Esto permite que un interperíodo atienda únicamente investigación o
    servicios, incluso los fines de semana, sin alterar el horario ordinario.
    """

    DIA_CHOICES = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name="horarios_operacion",
    )
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="horarios_unidades",
        help_text=(
            "Déjalo vacío para el horario general. Si se selecciona un período, "
            "sus jornadas reemplazan el horario general durante ese calendario."
        ),
    )
    nombre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ejemplo: Jornada ordinaria o Atención intersemestral de investigación.",
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    permite_recursos = models.BooleanField(
        default=True,
        help_text="Permite reservar espacios, equipos, software o licencias.",
    )
    permite_servicios = models.BooleanField(
        default=True,
        help_text="Permite solicitar atención o entrega de servicios de la unidad.",
    )
    tipos_usuario_habilitados = models.JSONField(
        default=list,
        blank=True,
        help_text="Vacío significa que aplica a todos los tipos de usuario.",
    )
    propositos_habilitados = models.JSONField(
        default=list,
        blank=True,
        help_text="Vacío significa que aplica a todos los propósitos institucionales.",
    )
    activo = models.BooleanField(default=True, db_index=True)
    observaciones = models.CharField(
        max_length=240,
        blank=True,
        help_text="Condiciones internas o excepciones que debe conocer la coordinación.",
    )

    class Meta:
        db_table = 'webcitt_horariooperacionunidad'
        ordering = ["unidad__nombre", "periodo__codigo", "dia_semana", "hora_inicio"]
        verbose_name = "Horario operativo de la unidad"
        verbose_name_plural = "Horarios operativos de las unidades"
        constraints = [
            models.CheckConstraint(
                check=Q(dia_semana__gte=0) & Q(dia_semana__lte=6),
                name="horario_unidad_dia_valido",
            ),
            models.UniqueConstraint(
                fields=[
                    "unidad", "periodo", "dia_semana", "hora_inicio", "hora_fin",
                ],
                condition=Q(periodo__isnull=False),
                name="horario_unidad_intervalo_unico",
            ),
            models.UniqueConstraint(
                fields=["unidad", "dia_semana", "hora_inicio", "hora_fin"],
                condition=Q(periodo__isnull=True),
                name="horario_general_unidad_intervalo_unico",
            ),
        ]

    def __str__(self):
        contexto = self.periodo.codigo if self.periodo_id else "Horario general"
        return (
            f"{self.unidad.nombre} · {contexto} · {self.get_dia_semana_display()} "
            f"{self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M}"
        )

    def clean(self):
        errors = {}
        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                errors["hora_fin"] = "La hora final debe ser posterior a la hora inicial."
            if any((
                self.hora_inicio.minute,
                self.hora_inicio.second,
                self.hora_fin.minute,
                self.hora_fin.second,
            )):
                errors["hora_inicio"] = (
                    "Los horarios de reserva se configuran en bloques completos de una hora."
                )

        tipos_validos = {codigo for codigo, _ in tipos_usuario()}
        propositos_validos = {codigo for codigo, _ in PROPOSITO_INSTITUCIONAL_CHOICES}
        tipos = self.tipos_usuario_habilitados or []
        propositos = self.propositos_habilitados or []
        if not isinstance(tipos, list) or any(tipo not in tipos_validos for tipo in tipos):
            errors["tipos_usuario_habilitados"] = "Selecciona tipos de usuario válidos."
        if not isinstance(propositos, list) or any(
            proposito not in propositos_validos for proposito in propositos
        ):
            errors["propositos_habilitados"] = "Selecciona propósitos institucionales válidos."
        if not self.permite_recursos and not self.permite_servicios:
            errors["permite_recursos"] = "Habilita al menos reservas de recursos o servicios."
        if errors:
            raise ValidationError(errors)

    def admite(self, *, tipo_solicitud, tipo_usuario="", proposito_codigo=""):
        es_servicio = tipo_solicitud == "servicio"
        if es_servicio and not self.permite_servicios:
            return False
        if not es_servicio and not self.permite_recursos:
            return False
        if (
            self.tipos_usuario_habilitados
            and tipo_usuario not in self.tipos_usuario_habilitados
        ):
            return False
        if self.propositos_habilitados and proposito_codigo not in self.propositos_habilitados:
            return False
        return True


class BloqueoAgendaUnidad(models.Model):
    """Excepción administrativa que cierra una jornada o recursos concretos."""

    TIPO_CHOICES = [
        ("mantenimiento", "Mantenimiento programado"),
        ("prestamo", "Equipo prestado fuera de la unidad"),
        ("feriado", "Feriado o suspensión institucional"),
        ("evento", "Evento institucional"),
        ("produccion", "Corrida de producción"),
        ("seguridad", "Cierre por seguridad"),
        ("limpieza", "Limpieza o preparación técnica"),
        ("otro", "Otra indisponibilidad"),
    ]
    ALCANCE_CHOICES = [
        ("unidad_completa", "Toda la unidad"),
        ("areas", "Áreas o espacios seleccionados"),
        ("equipos", "Equipos seleccionados"),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name="bloqueos_agenda",
    )
    mantenimiento = models.OneToOneField(
        'recursos.MantenimientoEquipo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bloqueo_agenda",
        help_text="Cuando el cierre lo genera una orden de mantenimiento, se mantiene solo.",
    )
    prestamo = models.OneToOneField(
        'recursos.PrestamoEquipo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bloqueo_agenda",
        help_text="Cuando el cierre lo genera un préstamo, se mantiene solo.",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="mantenimiento")
    titulo = models.CharField(max_length=160)
    motivo = models.TextField(blank=True)
    fecha_inicio = models.DateField(db_index=True)
    fecha_fin = models.DateField(db_index=True)
    dia_completo = models.BooleanField(
        default=False,
        help_text="Bloquea toda la jornada operativa durante las fechas indicadas.",
    )
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    alcance = models.CharField(
        max_length=20,
        choices=ALCANCE_CHOICES,
        default="unidad_completa",
    )
    espacios = models.ManyToManyField(
        'gestion_unidades.EspacioReservable', db_table='webcitt_bloqueoagendaunidad_espacios',
        blank=True,
        related_name="bloqueos_agenda",
    )
    equipos = models.ManyToManyField(
        'recursos.UnidadEquipo', db_table='webcitt_bloqueoagendaunidad_equipos',
        blank=True,
        related_name="bloqueos_agenda",
    )
    bloquea_recursos = models.BooleanField(default=True)
    bloquea_servicios = models.BooleanField(default=True)
    visible_en_agenda = models.BooleanField(
        default=True,
        help_text="Muestra el título y motivo operativo a los usuarios del calendario.",
    )
    activo = models.BooleanField(default=True, db_index=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bloqueos_agenda_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_bloqueoagendaunidad'
        ordering = ["-fecha_inicio", "hora_inicio", "unidad__nombre"]
        verbose_name = "Bloqueo de agenda"
        verbose_name_plural = "Bloqueos de agenda"
        indexes = [
            models.Index(fields=["unidad", "fecha_inicio", "fecha_fin"]),
            models.Index(fields=["activo", "tipo"]),
        ]

    def __str__(self):
        return f"{self.unidad.nombre} · {self.titulo} · {self.fecha_inicio}"

    def clean(self):
        errors = {}
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            errors["fecha_fin"] = "La fecha final no puede preceder a la inicial."
        if not self.dia_completo:
            if not self.hora_inicio:
                errors["hora_inicio"] = "Indica la hora inicial o marca día completo."
            if not self.hora_fin:
                errors["hora_fin"] = "Indica la hora final o marca día completo."
            if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
                errors["hora_fin"] = "La hora final debe ser posterior a la inicial."
        if not self.bloquea_recursos and not self.bloquea_servicios:
            errors["bloquea_recursos"] = "El bloqueo debe afectar recursos, servicios o ambos."
        if errors:
            raise ValidationError(errors)


class CapacidadOperativaUnidad(models.Model):
    """Fotografía histórica de la capacidad simultánea realmente utilizable."""

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name="capacidades_operativas",
    )
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="capacidades_unidades",
    )
    vigente_desde = models.DateField(db_index=True)
    vigente_hasta = models.DateField(null=True, blank=True, db_index=True)
    aforo_seguridad = models.PositiveIntegerField(
        help_text="Máximo permitido por infraestructura, evacuación y seguridad.",
    )
    puestos_mobiliario = models.PositiveIntegerField(
        help_text="Puestos con mesa, silla y condiciones mínimas de trabajo.",
    )
    puestos_equipados = models.PositiveIntegerField(
        help_text="Puestos que cuentan con el equipo o estación necesaria para operar.",
    )
    capacidad_personal = models.PositiveIntegerField(
        help_text="Personas que el personal disponible puede atender simultáneamente.",
    )
    fuente = models.CharField(
        max_length=180,
        blank=True,
        help_text="Acta, inspección, inventario o criterio técnico que respalda los valores.",
    )
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capacidades_operativas_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_capacidadoperativaunidad'
        ordering = ["unidad__nombre", "-vigente_desde"]
        verbose_name = "Capacidad operativa de la unidad"
        verbose_name_plural = "Capacidades operativas de las unidades"
        constraints = [
            models.UniqueConstraint(
                fields=["unidad", "vigente_desde"],
                name="capacidad_unidad_inicio_unico",
            ),
        ]

    def __str__(self):
        return f"{self.unidad.nombre} · {self.vigente_desde} · {self.capacidad_efectiva} puestos"

    @property
    def capacidad_efectiva(self):
        """Aplica el cuello de botella sin sobredimensionar la capacidad."""
        valores = (
            self.aforo_seguridad,
            self.puestos_mobiliario,
            self.puestos_equipados,
            self.capacidad_personal,
        )
        return min(int(valor or 0) for valor in valores)

    @property
    def factor_limitante(self):
        factores = {
            "Aforo y seguridad": self.aforo_seguridad,
            "Mobiliario": self.puestos_mobiliario,
            "Equipos operativos": self.puestos_equipados,
            "Personal disponible": self.capacidad_personal,
        }
        minimo = self.capacidad_efectiva
        return ", ".join(nombre for nombre, valor in factores.items() if valor == minimo)

    def clean(self):
        errors = {}
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            errors["vigente_hasta"] = "La vigencia final no puede preceder a la inicial."
        if errors:
            raise ValidationError(errors)
