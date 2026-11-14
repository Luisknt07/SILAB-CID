from django.urls import path

from apps.observatorios.presentation import views

urlpatterns = [
    path("observatorios/", views.catalogo, name="observatorios"),
    path("observatorio/<slug:slug>/", views.detalle, name="observatorio_detalle"),
]
