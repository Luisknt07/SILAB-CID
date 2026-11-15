"""Dispositivos conectados de una unidad, sus canales y las lecturas que envían."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.conexiones import credenciales


class DispositivoConectado(models.Model):
    """Un sensor, una pasarela o un equipo que envía mediciones por su cuenta."""

    TIPOS = [
        ('sensor', 'Sensor'),
        ('pasarela', 'Pasarela que reúne varios sensores'),
        ('equipo', 'Equipo con conectividad propia'),
        ('estacion_xr', 'Estación de realidad virtual o aumentada'),
        ('otro', 'Otro'),
    ]

    unidad = models.ForeignKey(
        'directorio_unidades.Unidad', on_delete=models.PROTECT, related_name='dispositivos_conectados')
    equipo = models.ForeignKey(
        'recursos.UnidadEquipo', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispositivos_conectados',
        help_text='Equipo físico inventariado al que pertenece o que vigila, si corresponde.')
    codigo = models.SlugField(max_length=60, unique=True,
                              help_text='Identificador estable, por ejemplo fablab-clima-01.')
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='sensor')
    ubicacion = models.CharField(max_length=200, blank=True, help_text='Dónde está instalado dentro de la unidad.')
    activo = models.BooleanField(default=True, help_text='Un dispositivo inactivo no puede enviar lecturas.')
    clave_hash = models.CharField(max_length=64, blank=True, editable=False)
    clave_generada_en = models.DateTimeField(null=True, blank=True, editable=False)
    ultima_senal = models.DateTimeField(null=True, blank=True, editable=False)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False,
        related_name='+')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dispositivo conectado'
        verbose_name_plural = 'Dispositivos conectados'
        ordering = ('unidad', 'codigo')

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def clean(self):
        super().clean()
        equipo = self.equipo
        if (equipo is not None and self.unidad_id and equipo.laboratorio_id != self.unidad_id
                and not equipo.laboratorios.filter(pk=self.unidad_id).exists()):
            raise ValidationError({'equipo': 'El equipo no pertenece a la unidad del dispositivo.'})

    def generar_clave(self):
        """Reemplaza la clave y devuelve la credencial completa; es la única vez que puede leerse."""
        if self.pk is None:
            raise ValueError('Guarda el dispositivo antes de generar su clave.')
        secreto = credenciales.nuevo_secreto()
        self.clave_hash = credenciales.huella(secreto)
        self.clave_generada_en = timezone.now()
        self.save(update_fields=['clave_hash', 'clave_generada_en', 'fecha_actualizacion'])
        return credenciales.componer(self.pk, secreto)

    @classmethod
    def autenticar(cls, credencial):
        """Devuelve el dispositivo activo, de una unidad activa, dueño de la credencial; si no, ``None``."""
        partes = credenciales.separar(credencial)
        if partes is None:
            return None
        identificador, secreto = partes
        dispositivo = cls.objects.select_related('unidad').filter(pk=identificador).first()
        # Se compara aunque no exista, para no revelar qué identificadores están en uso.
        valida = credenciales.coincide(secreto, dispositivo.clave_hash if dispositivo else credenciales.huella(''))
        if dispositivo is None or not valida or not dispositivo.activo or not dispositivo.unidad.activo:
            return None
        return dispositivo


class CanalMedicion(models.Model):
    """Una magnitud que mide un dispositivo: temperatura, consumo, horas de uso."""

    dispositivo = models.ForeignKey(DispositivoConectado, on_delete=models.CASCADE, related_name='canales')
    clave = models.SlugField(max_length=60,
                             help_text='Nombre con el que el dispositivo identifica el canal al enviar.')
    nombre = models.CharField(max_length=120)
    magnitud = models.CharField(max_length=80, blank=True, help_text='Qué se mide, por ejemplo temperatura ambiente.')
    unidad_medida = models.CharField(max_length=20, blank=True, help_text='Por ejemplo °C, kWh, h.')
    minimo_esperado = models.FloatField(null=True, blank=True)
    maximo_esperado = models.FloatField(null=True, blank=True)
    retencion_dias = models.PositiveIntegerField(
        default=365, validators=[MinValueValidator(1), MaxValueValidator(3650)],
        help_text='Días que se conservan las lecturas antes de depurarlas.')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Canal de medición'
        verbose_name_plural = 'Canales de medición'
        ordering = ('dispositivo', 'clave')
        constraints = [models.UniqueConstraint(fields=('dispositivo', 'clave'), name='conexiones_canal_unico')]

    def __str__(self):
        return f'{self.dispositivo.codigo}/{self.clave}'

    def clean(self):
        super().clean()
        if (self.minimo_esperado is not None and self.maximo_esperado is not None
                and self.minimo_esperado > self.maximo_esperado):
            raise ValidationError({'maximo_esperado': 'El máximo esperado no puede ser menor que el mínimo.'})

    def fuera_de_rango(self, valor):
        return ((self.minimo_esperado is not None and valor < self.minimo_esperado)
                or (self.maximo_esperado is not None and valor > self.maximo_esperado))


class LecturaCanal(models.Model):
    """Un valor medido en un instante. Repetir el envío de la misma lectura no la duplica."""

    canal = models.ForeignKey(CanalMedicion, on_delete=models.CASCADE, related_name='lecturas')
    instante = models.DateTimeField(help_text='Momento de la medición según el dispositivo.')
    valor = models.FloatField()
    recibida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lectura'
        verbose_name_plural = 'Lecturas'
        ordering = ('canal', '-instante')
        constraints = [models.UniqueConstraint(fields=('canal', 'instante'), name='conexiones_lectura_unica')]

    def __str__(self):
        return f'{self.canal} @ {self.instante:%Y-%m-%d %H:%M:%S}: {self.valor}'
