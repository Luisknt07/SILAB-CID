"""Seccion propia de Laboratorios: solo sus unidades."""

from django.contrib import admin

from apps.integraciones.unidades import administracion_de_funciones, administracion_por_tipologia

from . import models
from .models import Laboratorio


@admin.register(Laboratorio)
class LaboratorioAdmin(administracion_por_tipologia()):
    base_tipologia = 'laboratorios'


administracion_de_funciones(models, base_tipologia='laboratorios')
