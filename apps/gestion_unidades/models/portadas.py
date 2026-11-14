"""Lo que cada unidad decide de la portada de una pestaña de su ficha: su frase, su texto, su imagen, el estilo animado
con que se presenta y, si quiere, una escena 3D publicada (Spline o Sketchfab) en lugar de la animación."""
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models

from apps.recursos.models.recursos import ModuloUnidad

# Dónde se publican las escenas 3D que la portada puede incrustar.
SITIOS_DE_ESCENAS_3D = ('my.spline.design', 'prod.spline.design', 'sketchfab.com')


def validar_escena_3d(valor):
    sitio = urlparse(valor or '').hostname or ''
    if valor and not any(sitio == permitido or sitio.endswith(f'.{permitido}') for permitido in SITIOS_DE_ESCENAS_3D):
        raise ValidationError('Use el enlace público de una escena de Spline (my.spline.design) o el de inserción de '
                              'un modelo de Sketchfab.')


class PortadaPestana(models.Model):
    TEMAS = [
        ('', 'Según la pestaña'),
        ('orbitas', 'Órbitas alrededor de un núcleo'),
        ('cubos', 'Cubos e isometría de equipos'),
        ('engranajes', 'Engranajes y flujo de procesos'),
        ('red', 'Red de nodos que aprende'),
        ('reloj', 'Anillos de agenda y tiempo'),
        ('molecula', 'Molécula e investigación'),
        ('ondas', 'Ondas y señales'),
    ]

    modulo = models.OneToOneField(ModuloUnidad, on_delete=models.CASCADE, related_name='portada', verbose_name='Pestaña')
    lema = models.CharField('Frase de portada', max_length=160, blank=True,
                            help_text='Una frase corta que invite a recorrer la pestaña.')
    descripcion = models.TextField('Qué ofrece la pestaña', blank=True,
                                   help_text='Vacío, se usa la explicación estándar de la pestaña.')
    tema = models.CharField('Estilo animado', max_length=12, choices=TEMAS, blank=True)
    imagen = models.ImageField('Imagen de fondo', upload_to='portadas_pestana/', blank=True,
                               help_text='Se funde con la animación, a la derecha.')
    escena_3d = models.URLField('Escena 3D (opcional)', blank=True, validators=[validar_escena_3d],
                                help_text='Enlace público de una escena de Spline o de inserción de Sketchfab; '
                                          'reemplaza la animación.')
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_portadapestana'
        verbose_name = 'Portada de pestaña'
        verbose_name_plural = 'Portadas de pestañas'

    def __str__(self):
        return f'Portada de {self.modulo}'
