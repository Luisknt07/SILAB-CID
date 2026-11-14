"""Ubicación exacta de la unidad sobre el mapa de las sedes de la institución.

El punto lo marca el responsable en el editor de la unidad; la ficha pública
lo muestra con su dirección y con las sedes resaltadas, cada una con el
contorno y los edificios que se dibujaron en el editor de sedes. Las unidades
que comparten edificio quedan en un solo marcador con su lista por piso, y
cada una se reconoce por la miniatura de su imagen.
"""
import math
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.directorio_unidades.models.sedes import SedeInstitucional
from apps.directorio_unidades.models.core import Unidad

from apps.recursos.presentation.miniaturas import recorte_cuadrado
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

# A menos de esta distancia dos unidades están en el mismo edificio o entrada.
MISMO_PUNTO_METROS = 20


def ruta_hasta(lugar):
    """Ruta en Google Maps hasta el punto marcado de una unidad o una sede."""
    destino = f'{lugar.latitud},{lugar.longitud}'
    return 'https://www.google.com/maps/dir/?' + urlencode({'api': 1, 'destination': destino})


def enlace_como_llegar(unidad):
    """La ruta hasta el punto exacto o, sin él, la búsqueda por dirección."""
    if unidad.tiene_coordenadas:
        return ruta_hasta(unidad)
    if unidad.direccion_completa:
        consulta = f'{unidad.nombre}, {unidad.direccion_completa}'
        return 'https://www.google.com/maps/search/?' + urlencode({'api': 1, 'query': consulta})
    return ''


def miniatura(unidad):
    """Foto de la unidad para su marcador de 40 px: la portada pesa megas."""
    return recorte_cuadrado(unidad.imagen, 'unidades')


def distancia_metros(a, b):
    """Distancia entre dos puntos [latitud, longitud]; a escala de campus basta la aproximación plana."""
    latitud_media = math.radians((a[0] + b[0]) / 2)
    este = math.radians(b[1] - a[1]) * math.cos(latitud_media)
    norte = math.radians(b[0] - a[0])
    return 6371000 * math.hypot(este, norte)


def ficha_en_el_mapa(unidad):
    return {
        'nombre': unidad.nombre,
        'edificio': unidad.ubicacion,
        'piso': unidad.piso_texto,
        'direccion': unidad.direccion,
        'imagen': miniatura(unidad),
        'url': unidad.get_absolute_url(),
        'punto': unidad.punto,
    }


def ubicadas():
    return Unidad.objects.filter(activo=True, latitud__isnull=False, longitud__isnull=False)


def unidades_ubicadas(excluir=None):
    """Las demás unidades con punto, para que el editor pueda copiar el de su mismo edificio."""
    return [ficha_en_el_mapa(unidad) for unidad in ubicadas().exclude(pk=excluir).order_by('nombre')]


def en_el_mismo_punto(unidad):
    """La unidad y las que comparten su punto, de la planta baja hacia arriba."""
    if not unidad.tiene_coordenadas:
        return []
    juntas = [otra for otra in ubicadas() if distancia_metros(unidad.punto, otra.punto) <= MISMO_PUNTO_METROS]
    juntas.sort(key=lambda otra: (otra.piso is None, otra.piso or 0, otra.nombre))
    return [{**ficha_en_el_mapa(otra), 'actual': otra.pk == unidad.pk} for otra in juntas]


def sedes_en_el_mapa(excluir=None):
    """Todas las sedes activas, por separado; la que se está editando no se repite."""
    return [{
        'nombre': sede.nombre,
        'localidad': sede.localidad,
        'direccion': sede.direccion,
        'punto': sede.punto,
        'contorno': sede.contorno,
        'edificios': sede.edificios,
        'comoLlegar': ruta_hasta(sede) if sede.tiene_coordenadas else '',
    } for sede in SedeInstitucional.objects.activas().exclude(pk=excluir)]


def datos_mapa(unidad):
    """Lo que el script del mapa necesita, listo para `json_script`."""
    return {
        'nombre': unidad.nombre,
        'espacio': unidad.espacio_completo,
        'direccion': unidad.direccion,
        'imagen': miniatura(unidad),
        'punto': unidad.punto,
        'enElMismoPunto': en_el_mismo_punto(unidad),
        'sedes': sedes_en_el_mapa(),
        'comoLlegar': enlace_como_llegar(unidad),
    }


@xframe_options_sameorigin
def ubicacion_unidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    return render(request, 'portal/pages/unidades/detalle/ubicacion.html', {
        'unidad': unidad,
        'mapa': datos_mapa(unidad),
        'editar_url': reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk]) if gestor else '',
    })
