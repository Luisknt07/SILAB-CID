"""Novedades de cada unidad: su sección en la ficha, la nota completa y lo que lleva «Noticias».

Solo sale lo publicado, de unidades activas y con fecha de publicación cumplida. Quien
gestiona la unidad ve también sus borradores en la ficha, marcados como tales. La página
«Noticias» del portal recibe estas novedades por `novedades_del_portal`, que el portal
importa solo si la configuración lo declara: el portal no depende de las unidades.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.novedades import NovedadUnidad
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

# Cuántas novedades lleva la portada de «Noticias».
EN_PORTADA = 6


def publicadas():
    """Las novedades que el público puede leer."""
    return (NovedadUnidad.objects.filter(publicada=True, unidad__activo=True,
                                         fecha_publicacion__lte=timezone.localdate())
            .select_related('unidad'))


def novedades_de(unidad, usuario=None):
    """Las novedades de una unidad; con sus borradores si quien mira la gestiona."""
    if usuario is not None and puede_gestionar_unidad(usuario, unidad):
        return list(unidad.novedades.all())
    return list(publicadas().filter(unidad=unidad))


def novedades_del_portal():
    """Lo que la página «Noticias» publica: portada, agenda y convocatorias abiertas."""
    ahora = timezone.now()
    return {
        'destacadas': list(publicadas()[:EN_PORTADA]),
        'agenda': list(publicadas().filter(categoria='evento', fecha_evento__gte=ahora).order_by('fecha_evento')),
        'convocatorias': list(publicadas().filter(categoria='convocatoria', cierre__gte=timezone.localdate())
                              .order_by('cierre')),
    }


@xframe_options_sameorigin
def novedades_unidad_view(request, slug):
    """La sección «Novedades» de la ficha: las notas de la unidad en tarjetas."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    gestor = puede_gestionar_unidad(request.user, unidad)
    return render(request, 'portal/pages/unidades/detalle/novedades_unidad.html', {
        'unidad': unidad,
        'novedades': novedades_de(unidad, request.user),
        'gestor': gestor,
        'ediciones': ediciones_de(request.user, unidad),
    })


def novedad_detalle_view(request, pk):
    """La nota completa, dentro del portal; un borrador solo lo abre quien gestiona su unidad."""
    novedad = get_object_or_404(NovedadUnidad.objects.select_related('unidad'), pk=pk)
    visible = publicadas().filter(pk=pk).exists()
    if not visible and not puede_gestionar_unidad(request.user, novedad.unidad):
        raise Http404('La novedad no está publicada')
    relacionadas = publicadas().filter(unidad=novedad.unidad).exclude(pk=novedad.pk)[:3]
    return render(request, 'portal/pages/noticias/novedad.html', {
        'novedad': novedad,
        'borrador': not visible,
        'relacionadas': relacionadas,
        'active_page': 'noticias',
    })
