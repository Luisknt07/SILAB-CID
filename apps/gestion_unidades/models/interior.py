"""Fotos y videos de «La planta por dentro», ordenados por las áreas de la unidad."""

from django.core.exceptions import ValidationError
from django.db import models


class MedioInterior(models.Model):
    TIPOS = [('foto', 'Foto'), ('video', 'Video de YouTube')]

    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='medios_interiores')
    espacio = models.ForeignKey(
        'gestion_unidades.EspacioReservable', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='medios_interiores', verbose_name='Área',
        help_text='Área de la planta que muestra. Sin área, va en «Vista general».',
    )
    tipo = models.CharField('Tipo', max_length=10, choices=TIPOS, default='foto')
    titulo = models.CharField('Título', max_length=160)
    descripcion = models.CharField('Descripción', max_length=255, blank=True)
    imagen = models.ImageField('Foto', upload_to='unidades/interior/', blank=True)
    youtube_url = models.URLField('Enlace de YouTube', max_length=500, blank=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    publicado = models.BooleanField('Publicado', default=True)

    class Meta:
        db_table = 'webcitt_mediointerior'
        ordering = ('orden', 'pk')
        verbose_name = 'Foto o video del interior'
        verbose_name_plural = 'Fotos y videos del interior'

    def __str__(self):
        return self.titulo

    @property
    def youtube_id(self):
        from apps.directorio_unidades.models.core import Unidad
        return Unidad._youtube_video_id(self.youtube_url)

    def clean(self):
        super().clean()
        if self.tipo == 'foto' and not self.imagen:
            raise ValidationError({'imagen': 'Cargue la foto.'})
        if self.tipo == 'video' and not self.youtube_id:
            raise ValidationError({'youtube_url': 'Pegue un enlace de YouTube (youtube.com/watch, youtu.be o shorts).'})
        if self.espacio_id and self.unidad_id and self.espacio.unidad_id != self.unidad_id:
            raise ValidationError({'espacio': 'El área tiene que ser de esta misma unidad.'})
