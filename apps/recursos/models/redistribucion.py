"""Redistribución de equipos entre unidades: la alerta de un equipo sin uso y el traspaso que lo reasigna.

La política configurada por Dirección determina los umbrales de revisión.
La unidad documenta su compromiso; si otra unidad lo necesita, se solicita el traspaso, la Dirección lo aprueba y, al
ejecutarlo, el equipo pasa a la unidad que lo recibe con un nuevo código de laboratorio. El código del bien
(bodega) no cambia. El acta de traspaso deja constancia de quién entrega, quién recibe y de bodega.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class PoliticaUsoEquipo(models.Model):
    """Umbrales explícitos de Dirección; ningún valor se presume aprobado."""
    dias_sin_uso = models.PositiveIntegerField('Días sin uso acreditado', null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(36500)],
        help_text='Plazo para revisar un activo sin uso acreditado. Vacío: regla no configurada.')
    horas_minimas_anuales = models.DecimalField('Mínimo de horas acreditadas en 12 meses', max_digits=10,
        decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)],
        help_text='Umbral de atención para revisar poco uso; no acredita por sí solo incumplimiento. Vacío: regla no configurada.')
    dias_atencion = models.PositiveIntegerField('Días para atender la alerta después de comunicarla', null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(36500)],
        help_text='Se propone al registrar una comunicación real; Dirección puede acordar otra fecha por alerta.')
    fundamento = models.TextField('Fundamento de la política', blank=True)
    actualizada = models.DateTimeField(auto_now=True)
    actualizada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', editable=False)

    class Meta:
        db_table = 'webcitt_politicausoequipo'
        verbose_name = 'Política de seguimiento del uso de equipos'
        verbose_name_plural = 'Política de seguimiento del uso de equipos'
        constraints = [models.CheckConstraint(condition=Q(pk=1), name='politica_uso_equipo_unica')]

    def __str__(self):
        return 'Política institucional de uso de equipos'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class AlertaUsoEquipo(models.Model):
    MOTIVOS = [
        ('sin_uso', 'Sin uso acreditado en el plazo definido'),
        ('sin_registros', 'Sin uso acreditado; revisar registros'),
        ('pendiente', 'Cierres de uso por completar'),
        ('poco_uso', 'Uso acreditado inferior al umbral configurado'),
    ]
    ESTADOS = [
        ('abierta', 'Abierta'),
        ('en_estudio', 'En estudio por la Dirección'),
        ('justificada', 'Uso justificado por la unidad'),
        ('reasignacion', 'En reasignación'),
        ('cerrada', 'Cerrada'),
    ]
    VIGENTES = ('abierta', 'en_estudio', 'reasignacion')

    equipo = models.ForeignKey('recursos.UnidadEquipo', on_delete=models.CASCADE, related_name='alertas_uso')
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.SET_NULL, null=True, related_name='alertas_uso_equipos',
                               help_text='La unidad que tenía el equipo cuando se detectó.')
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    detectada = models.DateField(default=timezone.localdate)
    horas_anuales = models.DecimalField('Horas de uso en 12 meses', max_digits=8, decimal_places=1, default=0)
    ultimo_uso = models.DateField('Último uso', null=True, blank=True)
    estado = models.CharField(max_length=14, choices=ESTADOS, default='abierta', db_index=True)
    justificacion = models.TextField(
        'Justificación o resolución', blank=True,
        help_text='Por qué la unidad conserva el equipo (uso estacional, proyecto, respaldo…) o qué se resolvió.')
    plan_uso = models.TextField('Compromiso para aprovechar el equipo', blank=True,
        help_text='Actividades previstas, responsable y evidencia que permitirá comprobar su ejecución.')
    notificada_en = models.DateField('Fecha de comunicación a la unidad', null=True, blank=True,
        help_text='Registra una comunicación realizada. Completar este campo no envía mensajes.')
    revisar_desde = models.DateField('Revisar posible redistribución desde', null=True, blank=True,
        help_text='La Dirección fija el plazo de corrección; no se aplica un plazo automático.')
    evidencia = models.JSONField('Última lectura acreditada', default=dict, blank=True, editable=False)
    ultima_revision = models.DateField('Última revisión de uso', null=True, blank=True, editable=False)
    atendida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='alertas_uso_atendidas')
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_alertausoequipo'
        ordering = ['-detectada', 'equipo__codigo_unidad']
        verbose_name = 'Alerta de uso de equipo'
        verbose_name_plural = 'Alertas de uso de equipos'
        constraints = [
            models.UniqueConstraint(fields=['equipo'], condition=Q(estado__in=('abierta', 'en_estudio', 'reasignacion')),
                                    name='alerta_uso_vigente_unica'),
        ]

    def __str__(self):
        return f'{self.equipo.codigo_unidad} · {self.get_motivo_display()}'

    def clean(self):
        if self.notificada_en and self.notificada_en > timezone.localdate():
            raise ValidationError({'notificada_en': 'Registra la fecha de una comunicación ya realizada.'})
        if self.revisar_desde and (not self.notificada_en or self.revisar_desde <= self.notificada_en):
            raise ValidationError({'revisar_desde': 'Fija una fecha posterior a la comunicación a la unidad.'})
        if self.revisar_desde and not self.plan_uso.strip():
            raise ValidationError({'plan_uso': 'Documenta las actividades y el responsable antes de fijar el plazo de revisión.'})

    @property
    def vigente(self):
        return self.estado in self.VIGENTES


class TraspasoEquipo(models.Model):
    MOTIVOS = [
        ('subutilizado', 'Equipo sin uso suficiente en su unidad'),
        ('necesidad', 'Necesidad de la unidad que lo recibe'),
        ('reorganizacion', 'Reorganización institucional'),
        ('otro', 'Otro motivo documentado'),
    ]
    ESTADOS = [
        ('solicitado', 'Solicitado'),
        ('aprobado', 'Aprobado por la Dirección'),
        ('ejecutado', 'Ejecutado'),
        ('rechazado', 'Rechazado'),
        ('anulado', 'Anulado'),
    ]
    EN_CURSO = ('solicitado', 'aprobado')

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    unidad_origen = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.PROTECT, related_name='traspasos_entregados',
                                      verbose_name='Unidad que entrega')
    unidad_destino = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.PROTECT, related_name='traspasos_recibidos',
                                       verbose_name='Unidad que recibe')
    area_destino = models.ForeignKey(
        'gestion_unidades.EspacioReservable', on_delete=models.SET_NULL, null=True, blank=True, related_name='traspasos_recibidos',
        verbose_name='Área que lo recibe', help_text='Define el nuevo código de laboratorio (UNIDAD-ÁREA-MODELO-N.º).')
    motivo = models.CharField(max_length=16, choices=MOTIVOS, default='necesidad')
    justificacion = models.TextField(help_text='Para qué lo necesita la unidad que recibe y por qué no conviene comprar otro.')
    alerta = models.ForeignKey(AlertaUsoEquipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='traspasos',
                               verbose_name='Alerta de uso que lo originó')
    estado = models.CharField(max_length=12, choices=ESTADOS, default='solicitado', db_index=True)
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                       related_name='traspasos_solicitados')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='traspasos_aprobados', verbose_name='Aprobado (o rechazado) por')
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    observacion_direccion = models.TextField('Observación de la Dirección', blank=True)
    entrega_nombre = models.CharField('Quien entrega', max_length=160, blank=True)
    recibe_nombre = models.CharField('Quien recibe', max_length=160, blank=True)
    custodio_nuevo = models.CharField('Nuevo custodio', max_length=160, blank=True,
                                      help_text='Si queda vacío, el equipo conserva su custodio.')
    bodega_nombre = models.CharField('Por bodega / activos fijos', max_length=160, blank=True)
    ejecutado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='traspasos_ejecutados')
    fecha_ejecucion = models.DateTimeField(null=True, blank=True)
    acta_firmada = models.FileField('Acta firmada (escaneada)', upload_to='traspasos/%Y/', blank=True)

    class Meta:
        db_table = 'webcitt_traspasoequipo'
        ordering = ['-fecha_solicitud']
        verbose_name = 'Traspaso de equipos'
        verbose_name_plural = 'Traspasos de equipos'
        permissions = [('aprobar_traspasoequipo', 'Puede aprobar y ejecutar traspasos de equipos (Dirección)')]

    def __str__(self):
        return f'{self.codigo} · {self.unidad_origen} → {self.unidad_destino}'

    def clean(self):
        if self.unidad_origen_id and self.unidad_origen_id == self.unidad_destino_id:
            raise ValidationError({'unidad_destino': 'La unidad que recibe debe ser distinta de la que entrega.'})
        if self.area_destino_id and self.unidad_destino_id and self.area_destino.unidad_id != self.unidad_destino_id:
            raise ValidationError({'area_destino': 'El área debe ser de la unidad que recibe.'})

    def save(self, *args, **kwargs):
        if not self.codigo:
            anio = timezone.localdate().year
            ultimo = (TraspasoEquipo.objects.filter(codigo__startswith=f'TRP-{anio}-')
                      .order_by('-codigo').values_list('codigo', flat=True).first())
            numero = int(ultimo.rsplit('-', 1)[1]) + 1 if ultimo else 1
            self.codigo = f'TRP-{anio}-{numero:04d}'
        super().save(*args, **kwargs)

    @property
    def en_curso(self):
        return self.estado in self.EN_CURSO


class EquipoEnTraspaso(models.Model):
    """Cada equipo del traspaso, con la constancia de sus códigos antes y después."""

    traspaso = models.ForeignKey(TraspasoEquipo, on_delete=models.CASCADE, related_name='equipos')
    equipo = models.ForeignKey('recursos.UnidadEquipo', on_delete=models.PROTECT, related_name='traspasos')
    codigo_anterior = models.CharField('Código de laboratorio anterior', max_length=60, blank=True)
    codigo_nuevo = models.CharField('Código de laboratorio nuevo', max_length=60, blank=True)
    codigo_bien = models.CharField('Código del bien (se conserva)', max_length=60, blank=True)
    custodio_anterior = models.CharField(max_length=160, blank=True)

    class Meta:
        db_table = 'webcitt_equipoentraspaso'
        ordering = ['codigo_anterior']
        verbose_name = 'Equipo del traspaso'
        verbose_name_plural = 'Equipos del traspaso'
        constraints = [models.UniqueConstraint(fields=['traspaso', 'equipo'], name='equipo_una_vez_por_traspaso')]

    def __str__(self):
        return f'{self.codigo_anterior or self.equipo.codigo_unidad} → {self.codigo_nuevo or "por asignar"}'

    def clean(self):
        if not self.equipo_id or not self.traspaso_id:
            return
        traspaso = self.traspaso
        if traspaso.en_curso and self.equipo.laboratorio_id != traspaso.unidad_origen_id:
            raise ValidationError({'equipo': 'El equipo debe estar en la unidad que entrega.'})
        otro = (EquipoEnTraspaso.objects.filter(equipo=self.equipo, traspaso__estado__in=TraspasoEquipo.EN_CURSO)
                .exclude(traspaso=traspaso).values_list('traspaso__codigo', flat=True).first())
        if otro:
            raise ValidationError({'equipo': f'El equipo ya está en el traspaso {otro}, todavía en curso.'})
