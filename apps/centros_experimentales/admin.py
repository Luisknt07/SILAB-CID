"""Seccion propia de Centros experimentales: solo sus unidades."""

from django.contrib import admin

from apps.integraciones.unidades import administracion_de_funciones, administracion_por_tipologia

from . import models
from .models import CentroExperimental


@admin.register(CentroExperimental)
class CentroExperimentalAdmin(administracion_por_tipologia()):
    base_tipologia = 'centro_experimental'


administracion_de_funciones(models, base_tipologia='centro_experimental')
