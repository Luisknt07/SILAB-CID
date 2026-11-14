"""Sedes de la institución: dónde están sus campus, centros experimentales y plantas.

El mapa de ubicación de cada unidad las muestra resaltadas para orientar a
quien llega. Cada sede guarda su punto, el contorno del predio y sus
edificios, que se dibujan a mano en el editor de sedes.
"""

from django.core.exceptions import ValidationError
from django.db import models

from apps.directorio_unidades.models.mapa import PuntoEnMapa


def es_poligono(vertices):
    """Tres o más vértices [latitud, longitud] dentro de rango."""
    return isinstance(vertices, list) and len(vertices) >= 3 and all(
        isinstance(vertice, list) and len(vertice) == 2
        and all(isinstance(valor, (int, float)) and not isinstance(valor, bool) for valor in vertice)
        and -90 <= vertice[0] <= 90 and -180 <= vertice[1] <= 180
        for vertice in vertices
    )


class SedeQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(activa=True)


class SedeInstitucional(PuntoEnMapa):
    nombre = models.CharField('Nombre', max_length=120, unique=True)
    localidad = models.CharField(
        'Localidad', max_length=120, blank=True,
        help_text='Ciudad, parroquia o cantón, por ejemplo «Huaca» o «La Concepción, Mira».'
    )
    direccion = models.CharField(
        'Dirección', max_length=255, blank=True,
        help_text='Calle e intersección o referencia de acceso, tal como se lee en el mapa.'
    )
    # Vértices [latitud, longitud]; se dibujan en el mapa del editor de sedes.
    contorno = models.JSONField('Contorno del predio', default=list, blank=True)
    edificios = models.JSONField('Edificios', default=list, blank=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    activa = models.BooleanField('Activa', default=True)

    objects = SedeQuerySet.as_manager()

    class Meta:
        db_table = 'webcitt_sedeinstitucional'
        ordering = ('orden', 'nombre')
        verbose_name = 'Sede institucional'
        verbose_name_plural = 'Sedes institucionales'

    def __str__(self):
        return f'{self.nombre} · {self.localidad}' if self.localidad else self.nombre

    def clean(self):
        super().clean()
        if self.contorno and not es_poligono(self.contorno):
            raise ValidationError('El contorno del predio necesita al menos tres vértices dentro del mapa.')
        if not isinstance(self.edificios, list) or not all(
            isinstance(edificio, dict) and str(edificio.get('nombre', '')).strip() and es_poligono(edificio.get('contorno'))
            for edificio in self.edificios
        ):
            raise ValidationError('Cada edificio necesita un nombre y al menos tres vértices dentro del mapa.')
