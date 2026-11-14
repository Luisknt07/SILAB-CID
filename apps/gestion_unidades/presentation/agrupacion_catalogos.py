"""Catálogos privados por clase, áreas acreditadas y referencias documentadas.

Las áreas son referencias de uso, no ubicaciones de stock ni licencias extra.
Cada registro aparece una sola vez aunque se relacione con varios equipos.
"""

from collections import defaultdict

from django.core.exceptions import BadRequest
from django.db.models import Exists, OuterRef, Prefetch, Q

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.unidades import UnidadEquipo


def equipos_vigentes(unidad):
    return UnidadEquipo.objects.filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad),
        activa=True, fecha_baja__isnull=True,
    ).distinct()


def referencias_de_area(unidad, tipo):
    campo = 'software_registrado' if tipo == 'software' else 'insumo_registrado'
    return ElementoFichaArea.objects.filter(
        ficha__espacio__unidad=unidad,
        tipo='software' if tipo == 'software' else 'insumo',
        **{f'{campo}__unidad': unidad},
    ), campo


def filtrar_area_catalogo(consulta, unidad, tipo, valor):
    """Filtra por equipos o ficha de referencia antes de paginar."""
    areas = list(EspacioReservable.objects.filter(unidad=unidad).order_by('orden', 'nombre', 'pk'))
    valor = str(valor or '').strip()
    if valor and valor != 'sin_area' and valor not in {str(area.pk) for area in areas}:
        raise BadRequest('Selecciona un área de esta unidad.')
    if not valor:
        return consulta, valor, areas
    equipos = equipos_vigentes(unidad).filter(espacios_asociados__unidad=unidad)
    if valor != 'sin_area':
        equipos = equipos.filter(espacios_asociados__pk=int(valor))
    if tipo == 'software':
        vinculados = consulta.filter(equipos_instalados__in=equipos)
    else:
        vinculados = consulta.filter(por_equipo__equipo_id__in=equipos.values('equipo_id'))
    referencias, campo = referencias_de_area(unidad, tipo)
    if valor != 'sin_area':
        referencias = referencias.filter(ficha__espacio_id=int(valor))
    condicion = Q(pk__in=vinculados.values('pk')) | Q(pk__in=referencias.values(f'{campo}_id'))
    consulta = consulta.exclude(condicion) if valor == 'sin_area' else consulta.filter(condicion)
    return consulta.distinct(), valor, areas


def agrupar_catalogo(items, tipo, areas_por_registro, areas_referencia_por_registro=None):
    """Agrupación de presentación: no suma ni replica existencias/licencias."""
    grupos = {}
    vistos = set()
    for item in items:
        if item.pk in vistos:
            continue
        vistos.add(item.pk)
        areas = areas_por_registro.get(item.pk, {})
        item.areas_catalogo_resumen = ', '.join(sorted(areas.values(), key=str.casefold))
        referencias = (areas_referencia_por_registro or {}).get(item.pk, {})
        item.areas_catalogo_referencia_resumen = ', '.join(sorted(
            (nombre for pk, nombre in referencias.items() if pk not in areas), key=str.casefold,
        ))
        if tipo == 'software':
            clase = 'Licencias institucionales' if item.tipo_recurso == 'licencia' else 'Software'
            familia = item.get_tipo_acceso_display()
        else:
            clase = Consumible.CLASIFICACION_DETALLE.get(item.clasificacion, ('Otros', ''))[0]
            familia = (item.familia or '').strip() or 'Sin familia asignada'
        grupo = grupos.setdefault((clase, familia), {'clase': clase, 'familia': familia, 'items': []})
        grupo['items'].append(item)
    return sorted(grupos.values(), key=lambda grupo: (grupo['clase'].casefold(), grupo['familia'].casefold()))


def preparar_catalogos_por_area(unidad, software, consumibles):
    instalados = {item.pk: {equipo.pk for equipo in item.equipos_instalados.all()} for item in software}
    compatibles = {item.pk: {relacion.equipo_id for relacion in item.por_equipo.all()} for item in consumibles}
    pendientes = set()
    if consumibles:
        elementos, _ = referencias_de_area(unidad, 'insumos')
        elementos = elementos.filter(insumo_registrado_id=OuterRef('pk'))
        pendientes = set(Consumible.objects.filter(
            unidad=unidad, pk__in=compatibles, stock_total=0,
            lotes_inventario__isnull=True, entradas__isnull=True,
        ).annotate(
            propuesta=Exists(elementos.filter(solo_referencia=True)),
            acreditada=Exists(elementos.filter(solo_referencia=False)),
        ).filter(propuesta=True, acreditada=False).values_list('pk', flat=True))
    for item in consumibles:
        item.referencia_catalogo_pendiente = item.pk in pendientes
    ids = set().union(*instalados.values()) if instalados else set()
    modelos = set().union(*compatibles.values()) if compatibles else set()
    areas_por_equipo = defaultdict(dict)
    areas_por_modelo = defaultdict(dict)
    if ids or modelos:
        equipos = equipos_vigentes(unidad).filter(Q(pk__in=ids) | Q(equipo_id__in=modelos)).prefetch_related(Prefetch(
            'espacios_asociados', queryset=EspacioReservable.objects.filter(unidad=unidad),
        ))
        for equipo in equipos:
            for area in equipo.espacios_asociados.all():
                areas_por_equipo[equipo.pk][area.pk] = area.nombre
                areas_por_modelo[equipo.equipo_id][area.pk] = area.nombre

    def referencias(vinculos, fuente):
        return {pk: {area_id: nombre for referencia in ids_relacionados
                     for area_id, nombre in fuente[referencia].items()}
                for pk, ids_relacionados in vinculos.items()}

    def areas_documentadas(tipo, registros):
        if not registros:
            return {}
        consulta, campo = referencias_de_area(unidad, tipo)
        resultado = defaultdict(dict)
        for pk, area_id, nombre in consulta.filter(**{f'{campo}_id__in': registros}).values_list(
            f'{campo}_id', 'ficha__espacio_id', 'ficha__espacio__nombre',
        ):
            resultado[pk][area_id] = nombre
        return resultado

    return {
        'software_grupos': agrupar_catalogo(software, 'software', referencias(instalados, areas_por_equipo),
            areas_documentadas('software', instalados)),
        'insumos_grupos': agrupar_catalogo(consumibles, 'insumos', referencias(compatibles, areas_por_modelo),
            areas_documentadas('insumos', compatibles)),
    }
