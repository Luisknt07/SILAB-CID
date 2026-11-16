"""Navegación del catálogo completo por categorías registradas, antes de paginar.

Una categoría no crea relaciones de área, instalaciones ni existencias. Los
contadores describen el queryset recibido (búsqueda, estado y área ya aplicados),
sin quedar limitados a las tarjetas de la página ni a la categoría seleccionada.
"""

from hashlib import sha256
import json

from django.core.exceptions import BadRequest
from django.db.models import Count, Q
from django.urls import reverse

from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.software import SoftwareDisponible

# Cómo se nombra cada tipo de recurso en el catálogo de software; un simulador es software con su propia etiqueta.
CLASES_DE_SOFTWARE = {'software': 'Software', 'licencia': 'Licencias institucionales', 'simulador': 'Simuladores'}


def _configuracion(tipo):
    if tipo == 'software':
        return SoftwareDisponible, ('tipo_recurso', 'tipo_acceso')
    if tipo == 'insumos':
        return Consumible, ('clasificacion', 'familia')
    raise BadRequest('El catálogo no admite esta categoría.')


def _clave(fila, campos):
    return tuple(str(fila.get(campo) or '').strip() for campo in campos)


def _codigo(tipo, clave):
    # La familia es texto libre: no viaja como SQL, ruta, índice ni etiqueta HTML.
    # El código incluye la clase para no mezclar familias homónimas de otra clase.
    serializado = json.dumps([tipo, *clave], ensure_ascii=False, separators=(',', ':'))
    return ('s-' if tipo == 'software' else 'm-') + sha256(serializado.encode('utf-8')).hexdigest()[:24]


def _nombre(tipo, clave):
    clase, familia = clave
    if tipo == 'software':
        clases = CLASES_DE_SOFTWARE
        accesos = {'instalacion': 'Instalado en equipos', 'licencia': 'Individual temporal',
                   'red': 'Concurrente o de red', 'remoto': 'Acceso remoto'}
        return f"{clases.get(clase, clase or 'Tipo sin definir')} · {accesos.get(familia, familia or 'Acceso sin definir')}"
    clase = Consumible.CLASIFICACION_DETALLE.get(clase, (clase or 'Otros', ''))[0]
    return f"{clase} · {familia or 'Sin familia asignada'}"


def _preparar_contexto(universo, conteos, request, unidad, tipo, campos):
    """Construcción pura de códigos y enlaces sobre valores agregados por SQL."""
    categorias = {}
    for fila in universo:
        clave = _clave(fila, campos)
        codigo = _codigo(tipo, clave)
        entrada = categorias.setdefault(codigo, dict(
            codigo=codigo, nombre=_nombre(tipo, clave), cantidad=0, valores=[],
        ))
        # Se conserva el valor guardado para filtrar también familias con espacios
        # periféricos, que ya se presentan juntas en agrupar_catalogo().
        valores = tuple(fila.get(campo) for campo in campos)
        if valores not in entrada['valores']:
            entrada['valores'].append(valores)
    for fila in conteos:
        codigo = _codigo(tipo, _clave(fila, campos))
        if codigo in categorias:
            categorias[codigo]['cantidad'] += fila['cantidad']
    seleccion = str(request.GET.get('categoria_recursos', '') or '').strip()
    if seleccion and (len(seleccion) > 30 or seleccion not in categorias):
        raise BadRequest('Selecciona una categoría de este catálogo de la unidad.')

    parametros = request.GET.copy()
    parametros['view'] = 'recursos'
    parametros['modo_recursos'] = tipo
    parametros.pop('pagina_recursos', None)
    parametros.pop('editar_equipo', None)
    base = reverse('gestion_unidad', args=[unidad.slug])

    def enlace(codigo):
        valores = parametros.copy()
        if codigo:
            valores['categoria_recursos'] = codigo
        else:
            valores.pop('categoria_recursos', None)
        return base + '?' + valores.urlencode()

    filas = [dict(codigo='', nombre='Todos', cantidad=sum(c['cantidad'] for c in categorias.values()))]
    filas.extend({k: c[k] for k in ('codigo', 'nombre', 'cantidad')}
                 for c in sorted(categorias.values(), key=lambda c: (c['nombre'].casefold(), c['codigo'])))
    for fila in filas:
        fila.update(url=enlace(fila['codigo']), seleccionada=fila['codigo'] == seleccion)
    return seleccion, categorias, dict(recursos_categoria=seleccion, recursos_categorias=filas)


def filtrar_categoria_catalogo(consulta, request, unidad, tipo):
    """Devuelve ``(queryset, contexto)`` sin evaluar registros individuales.

    Integrar después de buscar/filtrar estado y área, antes de Paginator. Valida
    la selección contra todas las categorías de la unidad; una categoría válida
    que quede vacía por otro filtro conserva la navegación y muestra cero.
    """
    modelo, campos = _configuracion(tipo)
    consulta = consulta.filter(unidad=unidad).distinct()
    universo = modelo.objects.filter(unidad=unidad).order_by().values(*campos).distinct()
    conteos = consulta.order_by().values(*campos).annotate(cantidad=Count('pk', distinct=True))
    seleccion, categorias, contexto = _preparar_contexto(
        universo, conteos, request, unidad, tipo, campos,
    )
    if seleccion:
        condicion = Q()
        for valores in categorias[seleccion]['valores']:
            condicion |= Q(**dict(zip(campos, valores)))
        consulta = consulta.filter(condicion).distinct()
    return consulta, contexto
