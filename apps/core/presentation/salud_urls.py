"""Rutas de supervisión interna, ajenas a las capacidades funcionales."""
from django.urls import path

from .salud import SONDAS

app_name = 'salud_interna'
urlpatterns = [path(ruta, vista, name=ruta.rstrip('/')) for ruta, vista in SONDAS.items()]
