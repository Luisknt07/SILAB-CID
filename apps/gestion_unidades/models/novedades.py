"""Novedades de la unidad: lo que pasa en ella, contado por la propia unidad.

Se publican en la sección «Novedades» de su ficha y, juntas, en la página «Noticias»
del portal. Un evento lleva su fecha y una convocatoria su cierre: así la agenda y las
convocatorias del portal se arman solas y dejan de mostrarse cuando pasan.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone


class NovedadUnidad(models.Model):
    CATEGORIAS = [
        ('noticia', 'Noticia'),
        ('logro', 'Logro o resultado'),
        ('evento', 'Evento'),
        ('convocatoria', 'Convocatoria'),
    ]
    ICONOS = {
        'noticia': 'fas fa-newspaper',
        'logro': 'fas fa-award',
        'evento': 'fas fa-calendar-day',
        'convocatoria': 'fas fa-bullhorn',
    }

    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='novedades')
    titulo = models.CharField('Título', max_length=160)
    categoria = models.CharField('Tipo', max_length=20, choices=CATEGORIAS, default='noticia')
    resumen = models.CharField('Resumen', max_length=300,
                               help_text='Una o dos frases: es lo que se lee en la tarjeta.')
    cuerpo = models.TextField('Texto completo', blank=True,
                              help_text='La nota completa. Cada párrafo, separado por una línea en blanco.')
    imagen = models.ImageField('Foto', upload_to='unidades/novedades/', blank=True)
    enlace = models.URLField('Enlace para saber más', max_length=500, blank=True,
                             help_text='Inscripción, bases de la convocatoria o la nota original.')
    fecha_publicacion = models.DateField('Fecha de publicación', default=timezone.localdate)
    fecha_evento = models.DateTimeField('Fecha y hora del evento', null=True, blank=True,
                                        help_text='Solo para eventos: con ella entra a la agenda del portal.')
    lugar = models.CharField('Lugar', max_length=160, blank=True, help_text='Solo para eventos.')
    cierre = models.DateField('Cierre de la convocatoria', null=True, blank=True,
                              help_text='Solo para convocatorias: se deja de mostrar como abierta después de esta fecha.')
    publicada = models.BooleanField('Publicada', default=False,
                                    help_text='Sin marcar, la novedad es un borrador que solo ve la unidad.')
    destacada = models.BooleanField('Destacada', default=False,
                                    help_text='Va primero en la ficha y en la portada de «Noticias».')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_novedadunidad'
        ordering = ('-destacada', '-fecha_publicacion', '-id')
        verbose_name = 'Novedad de la unidad'
        verbose_name_plural = 'Novedades de la unidad'
        indexes = [models.Index(fields=['publicada', 'fecha_publicacion'], name='novedad_publicada_fecha')]

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        if self.categoria == 'evento' and not self.fecha_evento:
            raise ValidationError({'fecha_evento': 'Un evento necesita su fecha y hora.'})
        if self.categoria == 'convocatoria' and not self.cierre:
            raise ValidationError({'cierre': 'Una convocatoria necesita su fecha de cierre.'})

    @property
    def icono(self):
        return self.ICONOS[self.categoria]

    @property
    def parrafos(self):
        return [parrafo.strip() for parrafo in self.cuerpo.split('\n\n') if parrafo.strip()]

    @property
    def abierta(self):
        """Una convocatoria sigue abierta hasta su cierre; un evento, hasta que ocurre."""
        if self.categoria == 'convocatoria':
            return bool(self.cierre and self.cierre >= timezone.localdate())
        if self.categoria == 'evento':
            return bool(self.fecha_evento and self.fecha_evento >= timezone.now())
        return False

    def get_absolute_url(self):
        return reverse('novedad_detalle', args=[self.pk])
