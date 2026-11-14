"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path(
        "gestion/unidades/<slug:slug>/expediente/",
        vista_diferida('apps.documentos.presentation.expediente.expediente_unidad_view'),
        name="gestion_expediente_unidad",
    ),
    path(
        "gestion/unidades/<slug:slug>/expediente/<int:documento_id>/redactar/",
        vista_diferida('apps.documentos.presentation.expediente_redaccion.redactar_documento_view'),
        name="redactar_documento_expediente",
    ),
    path(
        "gestion/unidades/<slug:slug>/expediente/<int:documento_id>/vista-previa/",
        vista_diferida('apps.documentos.presentation.expediente_redaccion.vista_previa_documento_view'),
        name="vista_previa_documento_expediente",
    ),
    path(
        "gestion/unidades/<slug:slug>/expediente/<int:documento_id>/borrador.pdf",
        vista_diferida('apps.documentos.presentation.expediente_redaccion.pdf_borrador_documento_view'),
        name="pdf_borrador_documento_expediente",
    ),
    path(
        "laboratorio/<slug:slug>/procesos/<int:receta_id>/documentacion/",
        vista_diferida('apps.documentos.presentation.documentacion.documentacion_proceso_view'),
        name="documentacion_proceso",
    ),
    path("gestion/unidades/<slug:slug>/metas/fuentes/",
         vista_diferida('apps.documentos.presentation.medicion_vistas.fuentes_metas_view'),
         name='fuentes_metas_unidad'),
    path("gestion/unidades/<slug:slug>/metas/fuentes/<int:evidencia_id>/respaldo/",
         vista_diferida('apps.documentos.presentation.medicion_vistas.respaldo_meta_view'),
         name='respaldo_meta_unidad'),
    path('gestion/unidades/<slug:slug>/expediente/escenario-ideal/',
         vista_diferida('apps.documentos.presentation.escenario_ideal_consulta.escenario_ideal_view'),
         name='escenario_ideal_laboratorio'),
    path('gestion/unidades/<slug:slug>/expediente/escenario-ideal/<slug:codigo>.pdf',
         vista_diferida('apps.documentos.presentation.escenario_ideal_consulta.escenario_ideal_pdf_view'),
         name='escenario_ideal_laboratorio_pdf'),
]

for _ruta, _orden in zip(urlpatterns, (150, 151, 152, 153, 224, 225.01, 226.01, 226.1, 226.2), strict=True):
    _ruta.prioridad_proyecto = _orden

for _ruta, _orden in (
    (path('documentos/verificar/<uuid:token>/', vista_diferida(
        'apps.documentos.presentation.verificacion_qr.verificar_documento_view'), name='verificar_documento_qr'), 153.1),
    (path('gestion/unidades/<slug:slug>/expediente/<int:documento_id>/enviar/', vista_diferida(
        'apps.documentos.presentation.verificacion_qr.enviar_documento_view'), name='enviar_documento_qr'), 153.2),
    (path('gestion/unidades/<slug:slug>/expediente/<int:documento_id>/pac.xlsx', vista_diferida(
        'apps.documentos.presentation.pac_exportacion.exportar_pac_view'), name='exportar_pac_unidad'), 153.3),
    (path('gestion/unidades/<slug:slug>/expediente/<int:documento_id>/cpc/', vista_diferida(
        'apps.documentos.presentation.catalogo_cpc_vistas.buscar_cpc_necesidad_view'), name='buscar_cpc_necesidad'), 153.4),
):
    _ruta.prioridad_proyecto = _orden
    urlpatterns.append(_ruta)
