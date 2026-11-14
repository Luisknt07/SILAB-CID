"""Las relaciones entre unidades leídas desde cada punta, y la red completa para dibujarla.

En la ficha de cada unidad se ve con quién se relaciona y cómo («Funciona en», «Recibe materia prima de»,
«Analiza sus muestras»…), con enlace a la otra unidad. La red pone los cuatro tipos en columnas, de donde nace la
materia prima (centros) a donde se transforma (plantas), se analiza (laboratorios) y se sigue con datos (observatorios).
"""
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.directorio_unidades.models.relaciones import RelacionUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.directorio_unidades.models.relaciones import TIPOS_RELACION

# El orden de lectura en la ficha: primero dónde está y de dónde le llega lo que usa; después a quién sirve.
ORDEN_ETIQUETAS = [etiqueta for clave in TIPOS_RELACION for etiqueta in (TIPOS_RELACION[clave][1], TIPOS_RELACION[clave][0])]
ICONOS = {'aloja': 'simple-icon-home', 'abastece': 'iconsminds-plant', 'analiza': 'iconsminds-microscope',
          'sigue': 'simple-icon-graph', 'apoya': 'simple-icon-support'}
COLORES = {'aloja': '#2f6f4f', 'abastece': '#c98a1d', 'analiza': '#2b6cb0', 'sigue': '#7b4bb3', 'apoya': '#6b7a72'}
# Las columnas de la red, en el orden en que viaja la materia prima.
# Cada tipo sale a su altura del nodo: «aloja» y «provee» entre las mismas dos unidades no se tapan.
DESVIO = {'aloja': -8, 'abastece': 8, 'analiza': 0, 'sigue': 0, 'apoya': 4}
COLUMNAS = (('centro_experimental', 'Centros experimentales', 'iconsminds-environmental'),
            ('plantas_piloto', 'Plantas piloto', 'iconsminds-factory'),
            ('laboratorios', 'Laboratorios', 'iconsminds-microscope'),
            ('observatorios', 'Observatorios', 'iconsminds-big-data'))


def _vigentes():
    return RelacionUnidad.objects.filter(activa=True, origen__activo=True, destino__activo=True)


def relaciones_de(unidad):
    """Las relaciones de la unidad agrupadas por cómo se leen desde ella, cada una con la otra unidad."""
    grupos = {}
    for relacion in _vigentes().filter(origen=unidad).select_related('destino'):
        grupos.setdefault(relacion.get_tipo_display(), (relacion.tipo, []))[1].append(
            {'unidad': relacion.destino, 'que_fluye': relacion.que_fluye, 'descripcion': relacion.descripcion})
    for relacion in _vigentes().filter(destino=unidad).select_related('origen'):
        grupos.setdefault(relacion.etiqueta_inversa, (relacion.tipo, []))[1].append(
            {'unidad': relacion.origen, 'que_fluye': relacion.que_fluye, 'descripcion': relacion.descripcion})
    return [{'etiqueta': etiqueta, 'tipo': tipo, 'icono': ICONOS[tipo], 'color': COLORES[tipo], 'unidades': unidades}
            for etiqueta, (tipo, unidades) in sorted(grupos.items(), key=lambda par: ORDEN_ETIQUETAS.index(par[0]))]


def red_de_unidades(foco=None):
    """Las unidades con alguna relación, en columnas por tipo, y cada relación como un trazo entre ellas.

    Con foco, se marcan la unidad y sus vecinas; el resto queda atenuado pero visible para dar contexto.
    """
    relaciones = list(_vigentes().select_related('origen', 'destino').order_by('orden', 'tipo'))
    presentes = {relacion.origen_id: relacion.origen for relacion in relaciones}
    presentes.update({relacion.destino_id: relacion.destino for relacion in relaciones})
    vecinas = set()
    if foco is not None:
        vecinas = {foco.pk} | {r.destino_id for r in relaciones if r.origen_id == foco.pk} \
            | {r.origen_id for r in relaciones if r.destino_id == foco.pk}
    ancho_columna, separacion, alto_fila, margen = 230, 50, 58, 30
    columnas, posiciones = [], {}
    for indice, (dependencia, titulo, icono) in enumerate(COLUMNAS):
        unidades = sorted((u for u in presentes.values() if u.dependencia == dependencia), key=lambda u: u.nombre)
        x = margen + indice * (ancho_columna + separacion)
        nodos = []
        for fila, unidad in enumerate(unidades):
            y = 70 + fila * alto_fila
            posiciones[unidad.pk] = (x, y)
            nodos.append({'unidad': unidad, 'x': x, 'y': y, 'foco': foco is not None and unidad.pk == foco.pk,
                          'atenuada': bool(vecinas) and unidad.pk not in vecinas})
        columnas.append({'titulo': titulo, 'icono': icono, 'x': x, 'nodos': nodos})
    trazos = []
    for relacion in relaciones:
        if relacion.origen_id not in posiciones or relacion.destino_id not in posiciones:
            continue
        (x1, y1), (x2, y2) = posiciones[relacion.origen_id], posiciones[relacion.destino_id]
        y1, y2 = y1 + DESVIO[relacion.tipo], y2 + DESVIO[relacion.tipo]
        # El trazo sale por el lado que mira a la otra unidad; dentro de la misma columna, por la derecha.
        if x1 == x2:
            inicio, fin, curva = (x1 + ancho_columna, y1 + 20), (x2 + ancho_columna, y2 + 20), 60
            camino = f'M{inicio[0]},{inicio[1]} C{inicio[0] + curva},{inicio[1]} {fin[0] + curva},{fin[1]} {fin[0]},{fin[1]}'
        else:
            derecha = x2 > x1
            inicio = (x1 + ancho_columna if derecha else x1, y1 + 20)
            fin = (x2 if derecha else x2 + ancho_columna, y2 + 20)
            medio = (inicio[0] + fin[0]) / 2
            camino = f'M{inicio[0]},{inicio[1]} C{medio},{inicio[1]} {medio},{fin[1]} {fin[0]},{fin[1]}'
        trazos.append({'camino': camino, 'color': COLORES[relacion.tipo], 'relacion': relacion,
                       'atenuado': foco is not None and foco.pk not in (relacion.origen_id, relacion.destino_id)})
    filas = max((len(columna['nodos']) for columna in columnas), default=0)
    return {
        'columnas': columnas, 'trazos': trazos, 'relaciones': relaciones,
        'ancho': margen * 2 + len(COLUMNAS) * ancho_columna + (len(COLUMNAS) - 1) * separacion,
        'alto': 70 + max(filas, 1) * alto_fila + 20,
        'ancho_nodo': ancho_columna,
        'leyenda': [{'tipo': clave, 'nombre': directa, 'color': COLORES[clave], 'icono': ICONOS[clave]}
                    for clave, (directa, _inversa, _origenes) in TIPOS_RELACION.items()
                    if any(relacion.tipo == clave for relacion in relaciones)],
    }


@xframe_options_sameorigin
def red_unidades_view(request):
    """La red de unidades: cómo se relacionan centros, plantas, laboratorios y observatorios, con enlace a cada una."""
    foco = None
    if request.GET.get('unidad'):
        foco = get_object_or_404(Unidad, slug=request.GET['unidad'], activo=True)
    return render(request, 'portal/pages/unidades/red_unidades.html', {
        'red': red_de_unidades(foco),
        'foco': foco,
        'relaciones_foco': relaciones_de(foco) if foco else [],
    })
