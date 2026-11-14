from django.urls import path
from . import views

urlpatterns = [
    path("", views.tablero, name="tablero"),
    path("productos/nuevo/", views.producto_nuevo, name="producto_nuevo"),
    path("movimientos/", views.historial, name="historial"),
    path("movimientos/nuevo/", views.movimiento_nuevo, name="movimiento_nuevo"),
    path("importar/", views.importar, name="importar"),
    path("exportar/", views.exportar, name="exportar"),
]
