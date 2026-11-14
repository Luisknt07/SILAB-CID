"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path(
        "gestion/unidades/<slug:slug>/compras/<int:orden_id>/",
        vista_diferida('apps.finanzas.presentation.compras.orden_compra_view'),
        name="orden_compra",
    ),
]

for _ruta, _orden in zip(urlpatterns, (232,), strict=True):
    _ruta.prioridad_proyecto = _orden
