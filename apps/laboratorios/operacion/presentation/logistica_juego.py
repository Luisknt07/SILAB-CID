"""Recurso nativo de dinámica de cadenas: lectura pública, cálculo local y sin escrituras."""
from apps.core.presentation.tipologias import tipologia_activa

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.directorio_unidades.models.core import Unidad

from apps.plantas_piloto.operacion.presentation.secciones_plantas import secciones_ocultas

SLUG_LOGISTICA = 'laboratorio-logistica-comercio-internacional'


@xframe_options_sameorigin
@require_GET
def juego_cerveza_logistica_view(request, slug):
    """No extiende el recurso a otras unidades ni muestra una sección desactivada."""
    if slug != SLUG_LOGISTICA:
        raise Http404('Recurso no disponible en esta unidad.')
    unidad = get_object_or_404(Unidad, slug=slug, activo=True, dependencia='laboratorios')
    if not tipologia_activa(unidad.dependencia):
        raise Http404('Tipología no disponible.')
    if not unidad.modulos_contenido.filter(clave='docencia-capacitacion', activo=True).exists():
        raise Http404('Módulo docente no disponible.')
    if '4.4' in secciones_ocultas(unidad):
        raise Http404('Sección de aprendizaje no disponible.')
    respuesta = render(request, 'portal/pages/unidades/logistica/juego_cerveza.html', {
        'unidad': unidad,
        'volver_url': f'{unidad.get_absolute_url()}#docencia-capacitacion',
    })
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta
