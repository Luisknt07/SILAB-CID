from django.urls import path
from apps.integraciones import views_seguimiento as views

urlpatterns = [
    path(
        "seguimiento/consolidado/<int:pk>/centro/documento/<int:documento_id>/",
        views.archivo_centro,
        name="seguimiento_archivo_centro",
    ),
    path(
        "seguimiento/consolidado/<int:pk>/documento/<int:documento_id>/",
        views.archivo_documental,
        name="seguimiento_archivo_documental",
    ),
    path("seguimiento/", views.mesa, name="seguimiento_mesa"),
    path("seguimiento/exportar/", views.exportar, name="seguimiento_exportar"),
    path(
        "seguimiento/registrar/<str:tipo>/",
        views.registrar,
        name="seguimiento_registrar",
    ),
    path(
        "seguimiento/consolidado/<int:pk>/", views.detalle, name="seguimiento_detalle"
    ),
    path(
        "seguimiento/referencia/<int:pk>/verificar/",
        views.verificar_referencia,
        name="seguimiento_verificar_referencia",
    ),
]
