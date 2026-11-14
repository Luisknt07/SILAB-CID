"""Enrutamiento principal del SLCID.

La configuración raíz solo integra infraestructura transversal. Las rutas
funcionales pertenecen a sus aplicaciones y se incluyen desde aquí.
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('salud/', include('apps.core.presentation.salud_urls')),
    path('', include('apps.configuracion_institucional.urls')),
    path('i18n/', include('apps.core.presentation.urls')),
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('config.rutas_aplicaciones')),
]
