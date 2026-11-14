"""Seccion propia de Plantas piloto: solo sus unidades."""

from django.contrib import admin

from apps.integraciones.unidades import administracion_de_funciones, administracion_por_tipologia

from . import models
from .models import PlantaPiloto


@admin.register(PlantaPiloto)
class PlantaPilotoAdmin(administracion_por_tipologia()):
    base_tipologia = 'plantas_piloto'


administracion_de_funciones(models, base_tipologia='plantas_piloto')
