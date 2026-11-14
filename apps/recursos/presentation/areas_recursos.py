"""Áreas de los activos: una misma asignación para inventario y seguimiento.

La asociación no cambia registros. Un activo compartido ocupa una sola fila
en su primera área vigente y conserva las demás áreas como referencia.
"""
from collections import OrderedDict

from django.db.models import Q

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.unidades import UnidadEquipo

SIN_AREA = 'Sin área asignada'


def equipos_activos_de(unidad):
    """Activos físicos vigentes, incluso los asociados por la relación múltiple."""
    return UnidadEquipo.objects.filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad),
        activa=True, fecha_baja__isnull=True,
    ).distinct()


def areas_ordenadas_de(unidad, espacios=None):
    """Catálogo canónico, compartido por agrupación y paginación del inventario."""
    espacios = list(espacios) if espacios is not None else list(
        EspacioReservable.objects.filter(unidad=unidad)
    )
    return sorted((e for e in espacios if e.unidad_id == unidad.pk),
                  key=lambda e: (not e.activo, e.orden, e.nombre.casefold(), e.pk))


def asignaciones_por_area(unidad, equipos, espacios=None):
    """Devuelve ``areas`` y ``por_equipo`` sin duplicar ningún activo.

    Se ordenan primero las áreas activas por orden, nombre e identificador.
    Las asociaciones que sólo conservan un área inactiva se muestran en esa
    área, identificada como tal; las áreas ajenas nunca se atribuyen a la unidad.
    ``espacios`` es un catálogo completo opcional, no un filtro de paginación.
    """
    espacios = areas_ordenadas_de(unidad, espacios)
    catalogo = {e.pk: e for e in espacios}
    orden = {e.pk: indice for indice, e in enumerate(espacios)}
    areas = OrderedDict((e.pk, {
        'id': e.pk, 'espacio': e, 'nombre': e.nombre, 'codigo': e.codigo,
        'activa': e.activo, 'equipos': [],
    }) for e in espacios)
    sin_area = {'id': None, 'espacio': None, 'nombre': SIN_AREA,
                'codigo': '', 'activa': True, 'equipos': []}
    por_equipo, vistos = {}, set()
    for equipo in equipos:
        if equipo.pk in vistos:
            continue
        vistos.add(equipo.pk)
        propias = sorted({e.pk for e in equipo.espacios_asociados.all() if e.pk in catalogo},
                         key=orden.__getitem__)
        area = areas[propias[0]] if propias else sin_area
        area['equipos'].append(equipo)
        por_equipo[equipo.pk] = {
            'area_id': area['id'], 'area_nombre': area['nombre'],
            'espacio': area['espacio'], 'area_activa': area['activa'],
            'areas_compartidas': [catalogo[pk] for pk in propias[1:]],
        }
    resultado = [area for area in areas.values() if area['equipos']]
    if sin_area['equipos']:
        resultado.append(sin_area)
    return {'areas': resultado, 'por_equipo': por_equipo}


def grupos_de_filas(unidad, filas, *, equipo_de=lambda fila: fila['equipo']):
    """Filas operativas agrupadas por área y familia/categoría, sin copias."""
    filas = list(filas)
    asignacion = asignaciones_por_area(unidad, [equipo_de(fila) for fila in filas])
    areas = OrderedDict((area['id'], {**area, 'categorias': OrderedDict(), 'total': 0})
                        for area in asignacion['areas'])
    for fila in filas:
        equipo = equipo_de(fila)
        area = areas[asignacion['por_equipo'][equipo.pk]['area_id']]
        familia = equipo.equipo.familia
        categorias = list(equipo.equipo.categorias.all()) if not familia else []
        categoria = familia or next(iter(categorias), None)
        nombre = categoria.nombre if categoria else 'Sin categoría registrada'
        clave = ('familia' if familia else 'categoria', categoria.pk if categoria else None)
        grupo = area['categorias'].setdefault(clave, {'nombre': nombre, 'filas': [], 'total': 0})
        grupo['filas'].append(fila)
        grupo['total'] += 1
        area['total'] += 1
    for area in areas.values():
        area['categorias'] = sorted(area['categorias'].values(), key=lambda c: c['nombre'].casefold())
        area.pop('equipos', None)
    return list(areas.values())
