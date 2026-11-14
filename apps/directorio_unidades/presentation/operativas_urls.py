"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path(
        "laboratorio/<slug:slug>/ubicacion/",
        vista_diferida('apps.directorio_unidades.presentation.ubicacion.ubicacion_unidad_view'),
        name="ubicacion_unidad",
    ),
    path(
        "laboratorio/<slug:slug>/software/",
        vista_diferida('apps.directorio_unidades.presentation.catalogos_publicos.software_unidad_view'),
        name="software_unidad",
    ),
    path(
        "laboratorio/<slug:slug>/insumos/",
        vista_diferida('apps.directorio_unidades.presentation.catalogos_publicos.insumos_unidad_view'),
        name="insumos_unidad",
    ),
    path(
        "laboratorio/<slug:slug>/asignaturas/",
        vista_diferida('apps.directorio_unidades.presentation.catalogos_publicos.asignaturas_unidad_view'),
        name="asignaturas_unidad",
    ),
    path(
        "red-de-unidades/",
        vista_diferida('apps.directorio_unidades.presentation.relaciones.red_unidades_view'),
        name="red_unidades",
    ),
    path(
        "laboratorio/<slug:slug>/actividades/<slug:clave>/",
        vista_diferida('apps.directorio_unidades.presentation.catalogos_publicos.proyectos_unidad_view'),
        name="proyectos_unidad",
    ),
]

for _ruta, _orden in zip(urlpatterns, (25, 28, 43, 44, 45, 128), strict=True):
    _ruta.prioridad_proyecto = _orden
