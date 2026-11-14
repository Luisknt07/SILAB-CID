from django.urls import path

from apps.directorio_unidades.presentation import views

urlpatterns = [
    path("unidades/<slug:tipologia>/", views.catalogo, name="catalogo_tipologia"),
]
