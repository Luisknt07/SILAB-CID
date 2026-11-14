"""El inventario de equipos de la gestión, ordenado como el visualizador: por área y, en cada área, por modelo.

Cada unidad física lleva lo que hace falta para administrarla sin abrir otra pantalla: su estado, si ya se verificó
que existe, si tiene una alerta de uso abierta y si está en un traspaso. Los contadores de cada área y de cada
modelo alimentan los filtros del panel (en servicio, fuera de servicio, por verificar, con alerta).
"""
from collections import OrderedDict
from urllib.parse import urlencode

from django.db.models import prefetch_related_objects
from django.urls import reverse

from apps.recursos.models.redistribucion import AlertaUsoEquipo, EquipoEnTraspaso, TraspasoEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.uso_equipos import situaciones
from apps.recursos.presentation.areas_recursos import SIN_AREA, asignaciones_por_area, equipos_activos_de


def preparar_recursos_de_equipos(equipos):
    """Carga relaciones existentes por lote; no crea asignaciones ni existencias."""
    prefetch_related_objects(equipos, 'equipo__familia', 'equipo__categorias',
                             'software_instalado', 'equipo__consumibles__consumible')


def categoria_del_modelo(tipo):
    categoria = tipo.familia or next(iter(tipo.categorias.all()), None)
    return dict(clave=('familia' if tipo.familia_id else 'categoria', categoria.pk if categoria else None),
                nombre=categoria.nombre if categoria else 'Sin categoría registrada')


def vinculos_del_modelo(unidad, equipos):
    """Software instalado en estos activos y compatibilidad del modelo, sin sumar stock."""
    software, consumibles = OrderedDict(), OrderedDict()
    base = reverse('gestion_unidad', args=[unidad.slug])
    for equipo in equipos:
        for recurso in equipo.software_instalado.all():
            if recurso.unidad_id != unidad.pk:
                continue
            entrada = software.setdefault(recurso.pk, dict(recurso=recurso, codigos=[],
                url=base + '?' + urlencode(dict(view='recursos', modo_recursos='software', estado_recursos='todos', busqueda_recursos=recurso.nombre))))
            if equipo.codigo_unidad not in entrada['codigos']:
                entrada['codigos'].append(equipo.codigo_unidad)
        for vinculo in equipo.equipo.consumibles.all():
            recurso = vinculo.consumible
            if recurso.unidad_id != unidad.pk:
                continue
            consumibles.setdefault(recurso.pk, dict(recurso=recurso,
                url=base + '?' + urlencode(dict(view='recursos', modo_recursos='insumos', estado_recursos='todos', busqueda_recursos=recurso.nombre))))
    return dict(software=sorted(software.values(), key=lambda r: (r['recurso'].nombre.casefold(), r['recurso'].pk)),
                consumibles=sorted(consumibles.values(), key=lambda r: (r['recurso'].get_clasificacion_display(),
                    r['recurso'].nombre.casefold(), r['recurso'].pk)))


def _filtros_de(equipo):
    """Las etiquetas por las que el panel filtra cada unidad física."""
    if not equipo.en_inventario_real:
        return ['inactivo']
    etiquetas = ['servicio' if equipo.es_publico else 'fuera']
    if not equipo.existencia_verificada:
        etiquetas.append('verificar')
    if equipo.alerta_uso or equipo.alerta_inmediata:
        etiquetas.append('alerta')
    return etiquetas


def _contar(grupo, equipo):
    grupo['total'] += 1
    if not equipo.en_inventario_real:
        grupo['inactivos'] += 1
        return
    grupo['existentes'] += 1
    grupo['en_servicio'] += equipo.es_publico
    grupo['fuera'] += not equipo.es_publico
    grupo['por_verificar'] += not equipo.existencia_verificada
    grupo['con_alerta'] += bool(equipo.alerta_uso or equipo.alerta_inmediata)


def _contadores():
    return {'total': 0, 'existentes': 0, 'inactivos': 0, 'en_servicio': 0, 'fuera': 0, 'por_verificar': 0, 'con_alerta': 0}


def inventario_por_area(unidad, equipos, espacios):
    """Las áreas de la unidad (en su orden) con sus modelos y, en cada modelo, sus unidades físicas.

    Un equipo asociado a varias áreas va en la primera de la unidad; el que no tiene área va al final.
    """
    from apps.formacion.presentation.aula import ICONOS_DE_ESPACIO

    equipos = list(equipos)
    preparar_recursos_de_equipos(equipos)
    lecturas = situaciones(equipos)
    alertas = {alerta.equipo_id: alerta for alerta in
               AlertaUsoEquipo.objects.filter(equipo__in=equipos, estado__in=AlertaUsoEquipo.VIGENTES)}
    traspasos = {item.equipo_id: item.traspaso for item in
                 EquipoEnTraspaso.objects.filter(equipo__in=equipos, traspaso__estado__in=TraspasoEquipo.EN_CURSO)
                 .select_related('traspaso__unidad_destino')}
    asignacion = asignaciones_por_area(unidad, equipos)
    areas = OrderedDict((espacio.pk, {
        'espacio': espacio, 'nombre': espacio.nombre, 'codigo': espacio.codigo,
        'icono': ICONOS_DE_ESPACIO.get(espacio.tipo, 'fas fa-vector-square'), 'modelos': OrderedDict(), **_contadores(),
        'activa': espacio.activo,
    }) for espacio in (area['espacio'] for area in asignacion['areas'] if area['espacio']))
    sin_area = {'espacio': None, 'nombre': SIN_AREA, 'codigo': '', 'icono': 'fas fa-question-circle',
                'modelos': OrderedDict(), **_contadores()}
    for equipo in equipos:
        equipo.en_inventario_real = equipo.activa and not equipo.fecha_baja
        equipo.alerta_uso = alertas.get(equipo.pk)
        equipo.situacion_uso = lecturas[equipo.pk]
        equipo.alerta_inmediata = equipo.situacion_uso['alerta']
        equipo.traspaso_en_curso = traspasos.get(equipo.pk)
        equipo.filtros = ' '.join(_filtros_de(equipo))
        lectura_area = asignacion['por_equipo'][equipo.pk]
        area = areas[lectura_area['area_id']] if lectura_area['area_id'] else sin_area
        equipo.areas_compartidas = lectura_area['areas_compartidas']
        # El lugar dentro del área, sin repetir su nombre.
        lugar = (equipo.ubicacion_especifica or '').strip()
        if area['espacio'] and lugar.lower().startswith(area['nombre'].lower()):
            lugar = lugar[len(area['nombre']):].lstrip(' ·-—,:')
        equipo.lugar = lugar
        tipo = equipo.equipo
        modelo = area['modelos'].setdefault(tipo.pk, {'tipo': tipo, 'unidades': [], **_contadores()})
        modelo['unidades'].append(equipo)
        _contar(modelo, equipo)
        _contar(area, equipo)
    resultado = [area for area in areas.values() if area['total']]
    if sin_area['total']:
        resultado.append(sin_area)
    for area in resultado:
        area['modelos'] = sorted(area['modelos'].values(), key=lambda modelo: modelo['tipo'].nombre.lower())
        categorias = OrderedDict()
        for modelo in area['modelos']:
            modelo['filtros'] = ' '.join(sorted({etiqueta for equipo in modelo['unidades'] for etiqueta in equipo.filtros.split()}))
            categoria = categoria_del_modelo(modelo['tipo'])
            grupo = categorias.setdefault(categoria['clave'], dict(nombre=categoria['nombre'], modelos=[], **_contadores()))
            grupo['modelos'].append(modelo)
            for equipo in modelo['unidades']:
                _contar(grupo, equipo)
            modelo['vinculos'] = vinculos_del_modelo(unidad, modelo['unidades'])
        area['categorias'] = sorted(categorias.values(), key=lambda c: c['nombre'].casefold())
    return resultado


def resumen_del_inventario(areas):
    total = _contadores()
    for area in areas:
        for clave in total:
            total[clave] += area[clave]
    total['modelos'] = len({modelo['tipo'].pk for area in areas for modelo in area['modelos']})
    return total


def retirados_de(unidad):
    """Lo retirado del inventario: se consulta y se puede reactivar desde su edición."""
    from django.db.models import Q
    return list(UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
                .filter(Q(activa=False) | Q(fecha_baja__isnull=False)).distinct().select_related('equipo')
                .order_by('equipo__nombre', 'codigo_unidad'))


def resumen_global_del_inventario(unidad):
    """Totales de toda la unidad, independientes de filtros y página visible."""
    from django.conf import settings
    from django.db.models import Count, Q
    activos = equipos_activos_de(unidad)
    publico = Q(estado_unidad__in=UnidadEquipo.ESTADOS_PUBLICOS)
    if getattr(settings, 'CITT_EXIGIR_EQUIPOS_VERIFICADOS', False):
        publico &= Q(existencia_verificada=True)
    return activos.aggregate(
        total=Count('pk', distinct=True), modelos=Count('equipo_id', distinct=True),
        en_servicio=Count('pk', filter=publico, distinct=True),
        fuera=Count('pk', filter=~publico, distinct=True),
        por_verificar=Count('pk', filter=Q(existencia_verificada=False), distinct=True),
    )
