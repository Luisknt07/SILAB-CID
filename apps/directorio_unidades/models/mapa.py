"""Un punto en el mapa: lo comparten las unidades y las sedes de la institución."""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class PuntoEnMapa(models.Model):
    # Grados decimales (WGS84): seis decimales ubican el punto a unos 10 cm.
    latitud = models.DecimalField(
        'Latitud', max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text='Se fija marcando el punto en el mapa del editor.'
    )
    longitud = models.DecimalField(
        'Longitud', max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text='Se fija marcando el punto en el mapa del editor.'
    )

    class Meta:
        abstract = True

    @property
    def tiene_coordenadas(self):
        return self.latitud is not None and self.longitud is not None

    @property
    def punto(self):
        """[latitud, longitud] para el mapa, o None."""
        return [float(self.latitud), float(self.longitud)] if self.tiene_coordenadas else None

    def clean(self):
        super().clean()
        if (self.latitud is None) != (self.longitud is None):
            raise ValidationError({
                'latitud' if self.latitud is None else 'longitud':
                    'La ubicación exacta necesita latitud y longitud; márquela en el mapa.',
            })
