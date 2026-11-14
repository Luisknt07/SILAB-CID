from django.urls import path

from apps.centros_id.presentation import archivos, atencion, gestion, gestion_opciones, informes, secciones, views

urlpatterns = [
    path("centros-id/reportes/", informes.informes_view, name="reportes_centros_id"),
    path("centros-id/<slug:slug>/archivos/<slug:tipo>/<int:pk>/", archivos.descarga_archivo_view,
         name="archivo_centro_id"),
    path("centros-id/<slug:slug>/gestion/", gestion.gestion_view, name="gestion_centro_id"),
    path("centros-id/<slug:slug>/gestion/opciones/", gestion_opciones.opciones_view,
         name="opciones_gestion_centro_id"),
    path("centros-id/<slug:slug>/simular/capacidad/", secciones.simulador_view, name="simulador_centro_id"),
    path("centros-id/<slug:slug>/solicitudes/<int:pk>/", atencion.solicitud_view, name="solicitud_detalle_centro_id"),
    path("centros-id/", views.CentrosIDView.as_view(), name="centros_id"),
    path("centros-id/<slug:slug>/", views.centro_view, name="centro_id"),
    path("centros-id/<slug:slug>/pestana/<slug:pestana>/", views.pestana_view, name="pestana_centro_id"),
    path("centros-id/<slug:slug>/s/<slug:clave>/", secciones.seccion_view, name="seccion_centro_id"),
    path("centros-id/<slug:slug>/area/<slug:codigo>/", secciones.area_view, name="componente_centro_id"),
    path("centros-id/<slug:slug>/carpeta/<int:pk>/", secciones.carpeta_view, name="carpeta_centro_id"),
    path("centros-id/<slug:slug>/ficha/<slug:tipo>/<int:pk>/", secciones.fragmento_view, name="fragmento_centro_id"),
    path("centros-id/<slug:slug>/servicios/", secciones.portafolio_view, name="servicios_centro_id"),
    path("centros-id/<slug:slug>/solicitar/", secciones.solicitar_view, name="solicitar_centro_id"),
    path("centros-id/<slug:slug>/resultados/exportar/", secciones.exportar_resultados_view, name="exportar_resultados_centro_id"),
    path("centros-id/<slug:slug>/reporte.pdf", views.reporte_view, name="reporte_centro_id"),
]
