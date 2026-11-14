from django.urls import path

from apps.centros_experimentales.presentation import views

urlpatterns = [
    path("centros-experimentales/", views.catalogo, name="centros-experimentales"),
    path(
        "centro-experimental/<slug:slug>/",
        views.detalle,
        name="centro_experimental_detalle",
    ),
]
