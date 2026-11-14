"""Secciones nuevas de la ficha de una unidad, creadas desde una plantilla estándar.

Cuando a una pestaña le falta una sección, la unidad la crea eligiendo una plantilla (tarjetas, tabla, pasos o
texto) y la llena en la propia página, con el mismo aspecto que las secciones comunes. Es distinto de las carpetas
propias, que reúnen archivos: aquí cada elemento es contenido que la página dibuja.
"""
from django.db import models

from apps.recursos.models.recursos import ModuloUnidad


class SeccionPropia(models.Model):
    PLANTILLAS = [
        ('tarjetas', 'Tarjetas, como «Productos y servicios»'),
        ('tabla', 'Tabla, como «Insumos y materiales»'),
        ('pasos', 'Pasos numerados, como un proceso'),
        ('texto', 'Bloques de texto con imagen, como «Conoce la unidad»'),
    ]
    ICONOS = [
        ('fas fa-layer-group', 'Capas'), ('fas fa-cubes', 'Cubos'), ('fas fa-lightbulb', 'Idea'),
        ('fas fa-flask', 'Laboratorio'), ('fas fa-tools', 'Herramientas'), ('fas fa-book-open', 'Libro'),
        ('fas fa-users', 'Personas'), ('fas fa-handshake', 'Vinculación'), ('fas fa-chart-line', 'Indicadores'),
        ('fas fa-globe-americas', 'Mundo'), ('fas fa-vr-cardboard', 'Realidad virtual'), ('fas fa-leaf', 'Ambiente'),
    ]

    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='secciones_propias')
    modulo = models.ForeignKey(ModuloUnidad, on_delete=models.CASCADE, related_name='secciones_propias',
                               verbose_name='Pestaña')
    titulo = models.CharField('Título', max_length=120)
    resumen = models.CharField('Resumen', max_length=200, blank=True,
                               help_text='Una frase bajo el título: qué encuentra aquí el visitante.')
    descripcion = models.TextField('Introducción', blank=True)
    plantilla = models.CharField(max_length=12, choices=PLANTILLAS, default='tarjetas')
    icono = models.CharField(max_length=40, choices=ICONOS, default='fas fa-layer-group')
    imagen = models.ImageField('Imagen de portada', upload_to='secciones_propias/', blank=True)
    orden = models.PositiveSmallIntegerField(default=1)
    activa = models.BooleanField('Visible', default=True,
                                 help_text='Oculta, no se muestra en la ficha; nada se borra.')
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_seccionpropia'
        ordering = ('modulo__orden', 'orden', 'pk')
        verbose_name = 'Sección propia de la ficha'
        verbose_name_plural = 'Secciones propias de la ficha'

    def __str__(self):
        return f'{self.unidad} · {self.titulo}'

    def elementos_publicos(self):
        return self.elementos.filter(activo=True, es_ejemplo=False)


class ElementoSeccionPropia(models.Model):
    seccion = models.ForeignKey(SeccionPropia, on_delete=models.CASCADE, related_name='elementos')
    titulo = models.CharField('Título', max_length=160)
    etiqueta = models.CharField('Etiqueta', max_length=60, blank=True,
                                help_text='Una o dos palabras arriba del título, por ejemplo «Servicio» o «Etapa».')
    descripcion = models.TextField('Descripción', blank=True)
    detalle = models.CharField('Dato destacado', max_length=200, blank=True,
                               help_text='Una línea final: cómo se entrega, duración, responsable…')
    imagen = models.ImageField('Imagen', upload_to='secciones_propias/elementos/', blank=True)
    enlace = models.URLField('Enlace', blank=True)
    orden = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField('Visible', default=True)
    # Los elementos de muestra con que nace la plantilla: solo los ve quien gestiona, hasta que los edita.
    es_ejemplo = models.BooleanField(default=False, editable=False)

    class Meta:
        db_table = 'webcitt_elementoseccionpropia'
        ordering = ('orden', 'pk')
        verbose_name = 'Elemento de una sección propia'
        verbose_name_plural = 'Elementos de las secciones propias'

    def __str__(self):
        return self.titulo
