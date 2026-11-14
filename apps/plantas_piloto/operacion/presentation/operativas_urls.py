"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path(
        "planta-piloto/<slug:slug>/cafe/cadena/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.cafe.cadena_cafe'),
        name="cadena_cafe",
    ),
    path(
        "planta-piloto/<slug:slug>/cafe/calculadora/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.cafe.calculadora_cafe'),
        name="calculadora_cafe",
    ),
    path(
        "erp/<slug:slug>/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.erp.erp_planta_view'),
        name="erp_planta",
    ),
    path(
        "erp/<slug:slug>/sesiones/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.erp.erp_sesion_accion_view'),
        name="erp_sesion_accion",
    ),
    path(
        "gestion/unidades/<slug:slug>/procesos/<int:receta_id>/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.gestion_produccion.ficha_proceso_view'),
        name="ficha_proceso",
    ),
    path(
        "gestion/unidades/<slug:slug>/procesos/<int:receta_id>/guia.json",
        vista_diferida('apps.plantas_piloto.operacion.presentation.gestion_produccion.guia_desde_proceso_view'),
        name="guia_desde_proceso",
    ),
    path(
        "laboratorio/<slug:slug>/plan-haccp/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.calidad.plan_haccp_view'),
        name="plan_haccp",
    ),
    path(
        "gestion/unidades/<slug:slug>/trazabilidad/<int:lote_id>/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.trazabilidad.trazabilidad_lote_view'),
        name="trazabilidad_lote",
    ),
    path(
        "gestion/reporte-institucional/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.trazabilidad.reporte_institucional_view'),
        name="reporte_institucional",
    ),
    path(
        "gestion/unidades/<slug:slug>/planificacion/<int:plan_id>/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.planificacion.plan_maestro_view'),
        name="plan_maestro",
    ),
    path(
        "gestion/unidades/<slug:slug>/despachos/<int:movimiento_id>/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.despacho.guia_despacho_view'),
        name="guia_despacho",
    ),
    path(
        "gestion/unidades/<slug:slug>/calidad/control/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.calidad.control_calidad_view'),
        name="control_calidad",
    ),
    path(
        "gestion/unidades/<slug:slug>/maquila/<int:reserva_id>/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.maquila.maquila_view'),
        name="maquila_expediente",
    ),
    path(
        "gestion/unidades/<slug:slug>/maquila/<int:reserva_id>/acta/",
        vista_diferida('apps.plantas_piloto.operacion.presentation.maquila.acta_entrega_view'),
        name="acta_entrega_maquila",
    ),
]

for _ruta, _orden in zip(urlpatterns, (137.4, 137.5, 138, 139, 160, 161, 228, 229, 230, 231, 233, 234, 235, 236), strict=True):
    _ruta.prioridad_proyecto = _orden
