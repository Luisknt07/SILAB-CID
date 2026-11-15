"""Rutas de acceso propias del núcleo."""
from django.urls import path

from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path('segundo-factor/', vista_diferida('apps.core.acceso.vistas.segundo_factor_view'), name='segundo_factor'),
]
