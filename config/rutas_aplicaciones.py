"""Composicion de rutas; cada contexto posee su entrada publica.

Las definiciones operativas pertenecen a cada aplicación. La composición
conserva nombres, precedencia y direcciones publicadas.
"""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.portal.presentation.urls")),
    path("", include("apps.centros_id.presentation.urls")),
    path("", include("apps.laboratorios.presentation.urls")),
    path("", include("apps.observatorios.presentation.urls")),
    path("", include("apps.centros_experimentales.presentation.urls")),
    path("", include("apps.plantas_piloto.presentation.urls")),
    path("", include("apps.directorio_unidades.presentation.urls")),
    path("", include("config.rutas_operativas")),
]
