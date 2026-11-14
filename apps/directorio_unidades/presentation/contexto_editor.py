

import re

from django.db.models import Q


from apps.recursos.models.unidades import UnidadEquipo





def unidad_en_edicion(request):
    """Identificador de la unidad cuyo formulario se edita, o None en un alta.

    Los bloques internos solo viven en formularios de unidad (la seccion
    general y las de cada tipo), asi que el objeto de la URL es la unidad sea
    cual sea la ruta de la seccion. Buscar `/unidad/<id>/` dejaba vacios los
    selectores en las secciones por tipo.
    """
    coincidencia = getattr(request, 'resolver_match', None)
    if coincidencia and coincidencia.kwargs.get('object_id'):
        return coincidencia.kwargs['object_id']
    encontrado = re.search(r'/(\d+)/change/', request.path)
    return encontrado.group(1) if encontrado else None


def equipos_de_la_unidad(request):
    """Equipos activos asignados a la unidad en edicion (propios o compartidos)."""
    unidad_id = unidad_en_edicion(request)
    if not unidad_id:
        return UnidadEquipo.objects.none()
    return UnidadEquipo.objects.filter(
        Q(laboratorio_id=unidad_id) | Q(laboratorios__id=unidad_id), activa=True,
    ).select_related('equipo').distinct()
