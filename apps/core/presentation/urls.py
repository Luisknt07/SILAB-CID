"""Idioma transversal, sin prefijos ni cambios de rutas de las apps."""

from django.urls import path

from apps.core.presentation.idiomas import cambiar_idioma, catalogo_javascript


urlpatterns = [
    path("idioma/", cambiar_idioma, name="set_language"),
    path("catalogo.js", catalogo_javascript, name="javascript_catalog"),
]
