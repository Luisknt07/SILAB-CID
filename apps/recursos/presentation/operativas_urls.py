"""Rutas propietarias; controladores diferidos y precedencia conservada."""
from django.urls import path, re_path  # noqa: F401
from apps.core.routing.diferidas import vista_diferida

urlpatterns = [
    path(
        "laboratorio/<slug:slug>/equipamiento-referencia/<int:elemento_id>/",
        vista_diferida('apps.recursos.presentation.equipo_referencia.ficha_equipo_referencia'),
        name="ficha_equipo_referencia",
    ),
    path(
        "gestion/equipamiento-institucional/",
        vista_diferida('apps.recursos.presentation.equipamiento_institucional.equipamiento_institucional_view'),
        name="equipamiento_institucional",
    ),
    path(
        "gestion/equipamiento-institucional/<slug:clave>/",
        vista_diferida('apps.recursos.presentation.equipamiento_institucional.familia_equipo_institucional_view'),
        name="familia_equipo_institucional",
    ),
    path(
        "escanear/",
        vista_diferida('apps.recursos.presentation.lector_equipos.lector_equipos_view'),
        name="lector_equipos",
    ),
    path(
        "escanear/buscar/",
        vista_diferida('apps.recursos.presentation.lector_equipos.buscar_equipo_api'),
        name="lector_buscar_equipo",
    ),
    path(
        "escanear/registrar/",
        vista_diferida('apps.recursos.presentation.lector_equipos.registrar_equipo_api'),
        name="lector_registrar_equipo",
    ),
    path(
        "escanear/sugerencias/",
        vista_diferida('apps.recursos.presentation.lector_equipos.sugerencias_api'),
        name="lector_sugerencias",
    ),
    path(
        "laboratorio/<slug:slug>/escaner/",
        vista_diferida('apps.recursos.presentation.escaner_equipos.escaner_unidad_view'),
        name="escaner_unidad",
    ),
    path(
        "laboratorio/<slug:slug>/escaner/buscar/",
        vista_diferida('apps.recursos.presentation.escaner_equipos.escaner_buscar_api'),
        name="escaner_buscar",
    ),
    path(
        "equipos/codigo/<str:codigo>/",
        vista_diferida('apps.recursos.presentation.etiquetas_equipo.equipo_por_codigo_view'),
        name="equipo_por_codigo",
    ),
    path(
        "laboratorio/<slug:slug>/equipos/<str:codigo>/identificador.svg",
        vista_diferida('apps.recursos.presentation.etiquetas_equipo.identificador_equipo_view'),
        name="identificador_equipo",
    ),
    path(
        "laboratorio/<slug:slug>/equipos/<str:codigo>/editar/",
        vista_diferida('apps.recursos.presentation.edicion_equipo.editar_equipo_view'),
        name="editar_equipo_ficha",
    ),
    path(
        "laboratorio/<slug:slug>/equipos/<str:codigo>/verificar/",
        vista_diferida('apps.recursos.presentation.verificacion_equipos.verificar_equipo_view'),
        name="verificar_equipo",
    ),
    path(
        "equipos/traspasos/<str:codigo>/acta/",
        vista_diferida('apps.recursos.presentation.traspasos.acta_traspaso_view'),
        name="acta_traspaso_equipos",
    ),
    path(
        "laboratorio/<slug:slug>/etiquetas-equipos.pdf",
        vista_diferida('apps.recursos.presentation.etiquetas_equipo.etiquetas_equipos_pdf_view'),
        name="etiquetas_equipos",
    ),
    path(
        "gestion/unidades/<slug:slug>/equipos/<int:equipo_id>/",
        vista_diferida('apps.recursos.presentation.ficha_equipo.ficha_equipo_view'),
        name="ficha_equipo_unidad",
    ),
    path(
        "gestion/unidades/<slug:slug>/equipos/<int:equipo_id>/ficha.pdf",
        vista_diferida('apps.recursos.presentation.ficha_equipo.ficha_equipo_pdf_view'),
        name="ficha_equipo_unidad_pdf",
    ),
    re_path(r"^media/(?P<path>.*)$", vista_diferida('apps.recursos.entrega.media.media_no_xframe')),
]

for _ruta, _orden in zip(urlpatterns, (28.5, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 154, 155, 170), strict=True):
    _ruta.prioridad_proyecto = _orden

_ciclo = path('gestion/unidades/<slug:slug>/catalogo/<str:tipo>/<int:pk>/ciclo/',
    vista_diferida('apps.recursos.presentation.ciclo_catalogo.ciclo_recurso_view'), name='ciclo_recurso_unidad')
_ciclo.prioridad_proyecto = 170.2
urlpatterns.append(_ciclo)
_adquisiciones = path('gestion/unidades/<slug:slug>/adquisiciones/',
    vista_diferida('apps.recursos.presentation.ciclo_catalogo.adquisiciones_unidad_view'), name='adquisiciones_unidad')
_adquisiciones.prioridad_proyecto = 170.3
urlpatterns.append(_adquisiciones)
# Desechos: la unidad registra la entrega al gestor y su manifiesto, que se abre solo con la vista protegida.
for _ruta, _orden in (
    (path('gestion/unidades/<slug:slug>/desechos/entregas/',
          vista_diferida('apps.recursos.presentation.desechos.entregas_desechos_view'),
          name='entregas_desechos_unidad'), 170.4),
    (path('gestion/unidades/<slug:slug>/desechos/<int:desecho_id>/manifiesto/',
          vista_diferida('apps.recursos.presentation.desechos.manifiesto_desecho_view'),
          name='manifiesto_desecho_unidad'), 170.5),
    # Traspasos que propone la unidad que entrega y acepta y recibe la que recibe (la Dirección aprueba en Administración).
    (path('gestion/unidades/<slug:slug>/equipos/<int:equipo_id>/traspaso/',
          vista_diferida('apps.recursos.presentation.traspasos.proponer_traspaso_view'),
          name='proponer_traspaso_equipo'), 170.6),
    (path('gestion/unidades/<slug:slug>/traspasos/<str:codigo>/',
          vista_diferida('apps.recursos.presentation.traspasos.traspaso_unidad_view'),
          name='traspaso_equipo_unidad'), 170.7),
):
    _ruta.prioridad_proyecto = _orden
    urlpatterns.append(_ruta)
