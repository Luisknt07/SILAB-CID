"""«La planta por dentro»: fotos y videos por área, y el recorrido 360°.

Las fotos y los videos de YouTube se cargan en el editor de la unidad, cada
uno con su área. El recorrido 360° es el ZIP que exporta su programa (Pano2VR,
krpano, 3DVista…), cargado como recurso de tipo «Recorrido 360°»: el visor lo
abre por su index.html y lo reproduce completo. Se publica con las mismas
reglas que cualquier recurso: visibilidad y verificación de seguridad.
"""
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.interior import MedioInterior
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad

from apps.recursos.presentation.miniaturas import recorte_cuadrado
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.formacion.presentation.recursos_publicos import _acceso_recurso
from apps.recursos.presentation.tipos_adjunto import entrada_360, nombres_del_zip

VISTA_GENERAL = 'Vista general'


def _medio(medio):
    if medio.tipo == 'video':
        return {
            'tipo': 'video', 'titulo': medio.titulo, 'descripcion': medio.descripcion,
            'video': f'https://www.youtube-nocookie.com/embed/{medio.youtube_id}?rel=0&modestbranding=1',
            'miniatura': f'https://i.ytimg.com/vi/{medio.youtube_id}/hqdefault.jpg',
        }
    return {
        'tipo': 'foto', 'titulo': medio.titulo, 'descripcion': medio.descripcion,
        'imagen': medio.imagen.url,
        'miniatura': recorte_cuadrado(medio.imagen, 'interior', lado=160) or medio.imagen.url,
    }


def galeria_por_area(unidad):
    """Fotos y videos publicados por área: primero la vista general, luego las áreas en su orden."""
    grupos = {}
    medios = (MedioInterior.objects.filter(unidad=unidad, publicado=True).select_related('espacio')
              .order_by('espacio__orden', 'espacio__nombre', 'orden', 'pk'))
    for medio in medios:
        clave = f'area-{medio.espacio_id}' if medio.espacio_id else 'general'
        grupo = grupos.setdefault(clave, {
            'clave': clave, 'nombre': medio.espacio.nombre if medio.espacio_id else VISTA_GENERAL, 'medios': [],
        })
        grupo['medios'].append(_medio(medio))
    general = grupos.pop('general', None)
    return ([general] if general else []) + list(grupos.values())


def recorrido_360(unidad, usuario, gestor):
    """El recorrido que puede abrir esta persona: el ZIP cargado por la unidad o, si no, la ruta publicada.

    Al personal le dice además si hay un ZIP cargado que todavía no se publica.
    """
    cargados = [recurso for recurso in Recurso.objects.filter(
        unidad=unidad, tipo_adjunto='recorrido_360', activo=True, estado='vigente',
    ).select_related('carpeta').order_by('-pk') if recurso.es_zip]
    for recurso in cargados:
        # Sin carpeta se sirve; dentro de una, solo si está activa.
        if (not recurso.carpeta_id or recurso.carpeta.activa) and _acceso_recurso(recurso, usuario) == 'permitido':
            with recurso.archivo.open('rb') as archivo:
                entrada = entrada_360(nombres_del_zip(archivo))
            return {'url': reverse('recurso_unidad_archivo', args=[recurso.pk, entrada]), 'nombre': recurso.nombre, 'zip': True}
    if unidad.recorrido_360_public_url:
        return {'url': unidad.recorrido_360_public_url, 'nombre': 'Recorrido 360°', 'zip': False}
    if gestor and cargados:
        return {'pendiente': cargados[0].nombre}
    return None


def interior_de_la_planta(unidad, usuario, gestor):
    """Qué muestra la sección en la ficha y cuántas entradas cuenta."""
    datos = {
        'plano_y_video': bool(unidad.plano_espacios or unidad.recorrido_espacios_youtube_embed_url),
        'medios': MedioInterior.objects.filter(unidad=unidad, publicado=True).count(),
        'recorrido': recorrido_360(unidad, usuario, gestor),
    }
    datos['total'] = datos['plano_y_video'] + bool(datos['medios']) + bool(datos['recorrido'] and datos['recorrido'].get('url'))
    return datos


@xframe_options_sameorigin
def galeria_interior_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    return render(request, 'portal/pages/unidades/detalle/galeria_interior.html', {
        'unidad': unidad,
        'galeria': galeria_por_area(unidad),
        'editar_url': reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk]) if gestor else '',
    })
