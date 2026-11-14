"""«Conoce la unidad»: qué es, qué hace, su historia y su rumbo, contados por la propia unidad."""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Íconos de Font Awesome que la ficha ya carga; el editor elige por su nombre.
ICONOS_LINEA = [
    ('fa-industry', 'Producción'),
    ('fa-graduation-cap', 'Docencia'),
    ('fa-microscope', 'Investigación'),
    ('fa-chart-line', 'Control de procesos'),
    ('fa-shield-alt', 'Inocuidad y seguridad'),
    ('fa-leaf', 'Sostenibilidad'),
    ('fa-handshake', 'Vinculación'),
    ('fa-lightbulb', 'Innovación'),
    ('fa-flask', 'Análisis de laboratorio'),
    ('fa-users', 'Comunidad'),
    ('fa-cogs', 'Tecnología'),
    ('fa-award', 'Calidad'),
]


class PresentacionUnidad(models.Model):
    unidad = models.OneToOneField('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='presentacion')
    lema = models.CharField('Lema', max_length=140, blank=True,
                            help_text='Frase breve que resume a la unidad; va sobre su foto.')
    que_es = models.TextField('Qué es la unidad', blank=True)
    que_hace = models.TextField('Qué se hace aquí', blank=True)
    capacidades = models.TextField('Capacidades y servicios', blank=True)
    areas_trabajo = models.TextField('Áreas o líneas de trabajo', blank=True)
    historia = models.TextField('Historia', blank=True,
                                help_text='El relato. Los hitos con año van en «Hitos de la historia».')
    mision = models.TextField('Misión', blank=True)
    vision = models.TextField('Visión', blank=True)
    objetivos = models.TextField('Objetivos', blank=True, help_text='Uno por línea.')
    beneficiarios = models.TextField('Usuarios o beneficiarios', blank=True, help_text='Uno por línea.')
    resultados = models.TextField('Resultados o aportes', blank=True, help_text='Uno por línea.')
    video_url = models.URLField('Video de presentación', max_length=500, blank=True,
                                help_text='Enlace de YouTube en el que el responsable presenta la unidad.')
    video_presenta = models.CharField('Quién presenta el video', max_length=160, blank=True,
                                      help_text='Por ejemplo «Ing. Patricia Chamorro, coordinadora de la unidad».')
    publicada = models.BooleanField('Publicada', default=False,
                                    help_text='Mientras no se publique, solo la ve el personal de la unidad.')

    class Meta:
        db_table = 'webcitt_presentacionunidad'
        verbose_name = 'Presentación de la unidad'
        verbose_name_plural = 'Presentaciones de las unidades'

    def __str__(self):
        return f'Presentación de {self.unidad}'

    @property
    def video_id(self):
        from apps.directorio_unidades.models.core import Unidad
        return Unidad._youtube_video_id(self.video_url)

    def lista(self, campo):
        """Un campo de «uno por línea» como lista, sin renglones vacíos."""
        return [linea.strip() for linea in getattr(self, campo).splitlines() if linea.strip()]

    def clean(self):
        super().clean()
        if self.video_url and not self.video_id:
            raise ValidationError({'video_url': 'Pegue un enlace de YouTube (youtube.com/watch, youtu.be o shorts).'})


class LineaAccionUnidad(models.Model):
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='lineas_accion')
    titulo = models.CharField('Línea', max_length=80)
    descripcion = models.CharField('Descripción', max_length=200, blank=True)
    icono = models.CharField('Ícono', max_length=30, choices=ICONOS_LINEA, default='fa-industry')
    orden = models.PositiveSmallIntegerField('Orden', default=0)

    class Meta:
        db_table = 'webcitt_lineaaccionunidad'
        ordering = ('orden', 'pk')
        verbose_name = 'Línea de acción'
        verbose_name_plural = 'Líneas de acción'

    def __str__(self):
        return self.titulo


# Qué clase de momento es cada hito: decide su ícono y su color en la línea de tiempo.
TIPOS_HITO = {
    'creacion': {'nombre': 'Creación y normativa', 'icono': 'fa-landmark', 'color': '#1e5a3d'},
    'hito': {'nombre': 'Momento clave', 'icono': 'fa-flag', 'color': '#0f3f2a'},
    'infraestructura': {'nombre': 'Infraestructura y espacios', 'icono': 'fa-building', 'color': '#6c5ce7'},
    'equipamiento': {'nombre': 'Equipamiento', 'icono': 'fa-cogs', 'color': '#e67e22'},
    'certificacion': {'nombre': 'Certificación y reconocimiento', 'icono': 'fa-certificate', 'color': '#c9a227'},
    'convenio': {'nombre': 'Convenio y vinculación', 'icono': 'fa-handshake', 'color': '#2980b9'},
    'formacion': {'nombre': 'Formación y eventos', 'icono': 'fa-graduation-cap', 'color': '#16a085'},
    'plataforma': {'nombre': 'Documentación y plataforma', 'icono': 'fa-laptop-code', 'color': '#7f8c8d'},
}


class HitoUnidad(models.Model):
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='hitos')
    anio = models.PositiveSmallIntegerField('Año', validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    mes = models.PositiveSmallIntegerField('Mes', null=True, blank=True,
                                           validators=[MinValueValidator(1), MaxValueValidator(12)],
                                           help_text='Si se conoce; ordena los hitos del mismo año.')
    tipo = models.CharField('Tipo', max_length=20, default='hito',
                            choices=[(clave, datos['nombre']) for clave, datos in TIPOS_HITO.items()])
    titulo = models.CharField('Hito', max_length=120)
    descripcion = models.CharField('Descripción', max_length=255, blank=True)
    enlace = models.URLField('Enlace', max_length=500, blank=True,
                             help_text='Documento, noticia o certificado que respalda el hito.')

    class Meta:
        db_table = 'webcitt_hitounidad'
        ordering = ('anio', 'mes', 'pk')
        verbose_name = 'Hito de la historia'
        verbose_name_plural = 'Hitos de la historia'

    def __str__(self):
        return f'{self.anio} · {self.titulo}'
