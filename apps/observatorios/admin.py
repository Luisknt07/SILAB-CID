"""Seccion propia de Observatorios: solo sus unidades."""

from django.contrib import admin

from apps.integraciones.unidades import administracion_de_funciones, administracion_por_tipologia

from . import models
from .models import Observatorio


@admin.register(Observatorio)
class ObservatorioAdmin(administracion_por_tipologia()):
    base_tipologia = 'observatorios'


administracion_de_funciones(models, base_tipologia='observatorios')
