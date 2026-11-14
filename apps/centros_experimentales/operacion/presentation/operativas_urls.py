"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path(
        "centro-experimental/<slug:slug>/como-funciona/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.funcionamiento_view'),
        name="funcionamiento_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/ejes/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.ejes_view'),
        name="ejes_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/ejes/<slug:codigo>/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.eje_view'),
        name="eje_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/calendario-productivo/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.calendario_view'),
        name="calendario_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/destino-de-la-produccion/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.destino_view'),
        name="destino_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/temas-de-investigacion/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.temas_view'),
        name="temas_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/produccion/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.produccion_view'),
        name="produccion_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/produccion.csv",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.produccion_csv_view'),
        name="produccion_csv_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/simuladores/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_simuladores.simuladores_view'),
        name="simuladores_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/cursos/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.cursos_view'),
        name="cursos_centro",
    ),
    path(
        "centro-experimental/<slug:slug>/como-se-reserva/",
        vista_diferida('apps.centros_experimentales.operacion.presentation.centro_experimental.como_reservar_view'),
        name="como_reservar_centro",
    ),
]

for _ruta, _orden in zip(urlpatterns, (46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56), strict=True):
    _ruta.prioridad_proyecto = _orden
