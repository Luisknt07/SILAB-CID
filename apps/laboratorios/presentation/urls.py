from django.urls import path

from apps.laboratorios.presentation import views

urlpatterns = [
    path("laboratorios-unidades/", views.catalogo, name="laboratorios_unidades"),
    path("hublab/", views.catalogo, name="hublab"),
    path("laboratorio/<slug:slug>/", views.detalle, name="laboratorio_detalle"),
]
