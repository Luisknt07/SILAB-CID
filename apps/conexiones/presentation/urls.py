"""Rutas del módulo; solo se incluyen cuando la instalación lo activa."""
from django.urls import path

from apps.core.routing.diferidas import vista_diferida

# Los dispositivos no tienen sesión ni formulario: se autentican con su
# credencial y la vista cuenta sus envíos por dispositivo, no por dirección.
ingesta = vista_diferida('apps.conexiones.presentation.views.ingesta_view', csrf_exempt=True)
ingesta.limite_propio = True

urlpatterns = [
    path('conexiones/ingesta/', ingesta, name='conexiones_ingesta'),
    path('conexiones/canales/<int:pk>/lecturas/',
         vista_diferida('apps.conexiones.presentation.views.lecturas_canal_view'),
         name='conexiones_lecturas_canal'),
    path('conexiones/unidades/<slug:slug>/',
         vista_diferida('apps.conexiones.presentation.views.estado_unidad_view'),
         name='conexiones_estado_unidad'),
]
