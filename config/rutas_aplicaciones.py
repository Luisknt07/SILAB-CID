"""Composicion de rutas; cada contexto posee su entrada publica.

Las definiciones operativas pertenecen a cada aplicación. La composición
conserva nombres, precedencia y direcciones publicadas.
"""

from django.conf import settings
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

# Módulos opcionales: sus rutas solo existen en las instalaciones que los activan.
if getattr(settings, 'MODULO_CONEXIONES', False):
    urlpatterns.insert(0, path("", include("apps.conexiones.presentation.urls")))
