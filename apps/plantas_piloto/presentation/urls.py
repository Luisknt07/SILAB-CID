from django.urls import path

from apps.plantas_piloto.presentation import views

urlpatterns = [
    path("plantas-piloto/", views.catalogo, name="plantas-piloto"),
    path("planta-piloto/<slug:slug>/", views.detalle, name="planta_piloto_detalle"),
]
