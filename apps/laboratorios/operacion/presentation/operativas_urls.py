"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path("laboratorio/<slug:slug>/logistica/operacion/",
         vista_diferida("apps.laboratorios.operacion.presentation.logistica_operacion.operacion_view"), name="logistica_operacion"),
    path('laboratorio/<slug:slug>/logistica/distribucion/',
         vista_diferida('apps.laboratorios.operacion.presentation.logistica_distribucion.distribucion_view'), name='logistica_distribucion'),
    path('laboratorio/<slug:slug>/logistica/por-dentro/',
         vista_diferida('apps.laboratorios.operacion.presentation.logistica_presentacion.logistica_identidad_view'), name='logistica_identidad'),
    path('laboratorio/<slug:slug>/logistica/juego-cerveza/',
         vista_diferida('apps.laboratorios.operacion.presentation.logistica_juego.juego_cerveza_logistica_view'), name='logistica_juego_cerveza'),
    path(
        "laboratorio/<slug:slug>/procesos/<int:proceso_id>/",
        vista_diferida('apps.laboratorios.operacion.presentation.procesos_laboratorio.proceso_laboratorio_view'),
        name="proceso_laboratorio",
    ),
    path(
        "laboratorio/<slug:slug>/procesos/metodos-y-parametros/",
        vista_diferida('apps.laboratorios.operacion.presentation.procesos_laboratorio.metodos_laboratorio_view'),
        name="metodos_laboratorio",
    ),
    path(
        "laboratorio/<slug:slug>/productos-y-servicios/",
        vista_diferida('apps.laboratorios.operacion.presentation.procesos_laboratorio.productos_laboratorio_view'),
        name="productos_laboratorio",
    ),
]

for _ruta, _orden in zip(urlpatterns, (0, 1, 6, 7, 211, 212, 213), strict=True):
    _ruta.prioridad_proyecto = _orden
