"""Composición de URL: las definiciones pertenecen a cada aplicación."""

from importlib import import_module

PROVEEDORES = (
    "apps.laboratorios.operacion.presentation.operativas_urls",
    "apps.formacion.presentation.operativas_urls",
    "apps.gestion_unidades.presentation.operativas_urls",
    "apps.directorio_unidades.presentation.operativas_urls",
    "apps.recursos.presentation.operativas_urls",
    "apps.centros_experimentales.operacion.presentation.operativas_urls",
    "apps.observatorios.operacion.presentation.operativas_urls",
    "apps.reservas.presentation.operativas_urls",
    "apps.plantas_piloto.operacion.presentation.operativas_urls",
    "apps.documentos.presentation.operativas_urls",
    "apps.core.presentation.operativas_urls",
    "apps.finanzas.presentation.operativas_urls",
)

urlpatterns = sorted(
    (
        ruta
        for proveedor in PROVEEDORES
        for ruta in import_module(proveedor).urlpatterns
    ),
    key=lambda ruta: ruta.prioridad_proyecto,
)
