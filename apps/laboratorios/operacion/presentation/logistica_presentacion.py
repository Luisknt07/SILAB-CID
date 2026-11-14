"""Portada docente de Logística: relaciones reales y lectura selectiva por unidad.

La página no abre el panel de gestión, el inventario detallado ni la base de
Centros I+D. Las asociaciones académicas proceden del texto explícito que ya
registra cada asignatura; no se deducen a partir de su nombre.
"""
import re
import unicodedata
from urllib.parse import urlencode

from apps.core.presentation.tipologias import tipologia_activa

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_safe

from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, SLUG
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.asignaturas import Asignatura
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

_COORDENADAS = ((92, 60), (340, 36), (588, 60), (92, 342), (340, 366), (588, 342))
_NOMBRES_DIAGRAMA = {
    'LOG-ALMACEN': ('Almacenamiento', 'e intralogística'),
    'LOG-AREA-SIM': ('Planificación', 'de la cadena'),
    'LOG-AREA-TMS': ('Transporte', 'y distribución'),
    'LOG-AREA-PRODUCCION': ('Producción', 'y operaciones'),
    'LOG-AREA-COMERCIO': ('Logística', 'internacional'),
    'LOG-AREA-ERP': ('Tecnologías', 'y simulación'),
}
_AREA_EN_DESCRIPCION = re.compile(r'área\s+«([^»]+)»', re.IGNORECASE)


def _normalizar(texto):
    return ' '.join(unicodedata.normalize('NFKC', str(texto or '')).split()).casefold()


def _texto_filtro(texto, limite=120):
    return ' '.join(''.join(c for c in str(texto or '') if not unicodedata.category(c).startswith('C')).split())[:limite]


def _aplicaciones_editoriales(ficha):
    resultados = {'competencias': [], 'indicadores': [], 'practicas': []}
    if ficha is None:
        return resultados
    claves = {'competencia': 'competencias', 'competencias': 'competencias',
              'indicador': 'indicadores', 'indicadores': 'indicadores',
              'práctica': 'practicas', 'prácticas': 'practicas'}
    for linea in ficha.lista_aplicaciones:
        prefijo, separador, contenido = linea.partition(':')
        clave = claves.get(_normalizar(prefijo))
        if separador and clave and contenido.strip():
            resultados[clave].append(contenido.strip())
    return resultados


def _nombres_area(area):
    anteriores = AREAS.get(area.codigo, {})
    return tuple(dict.fromkeys(nombre for nombre in (
        area.nombre, anteriores.get('nombre'), anteriores.get('anterior'),
    ) if nombre))


def _consulta_area(area):
    consulta = Q(pk__in=[])
    for nombre in _nombres_area(area):
        consulta |= Q(descripcion__icontains=f'área «{nombre}»')
    return consulta


def _area_de(asignatura, indice):
    coincidencia = _AREA_EN_DESCRIPCION.search(asignatura.descripcion or '')
    return indice.get(_normalizar(coincidencia.group(1))) if coincidencia else None


def _metadatos_editoriales():
    # El contenido se comparte con el comando que publica las fichas del área.
    # No depende de la carga del panel ni se consulta ninguna otra base.
    from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import FUENTES, MATRIZ_ASIGNATURAS
    return FUENTES, MATRIZ_ASIGNATURAS


def visibilidad_secciones_logistica(unidad):
    """Publicación explícita de cada bloque, compartida por enlaces y consultas."""
    modulos = set(unidad.modulos_contenido.filter(activo=True).values_list('clave', flat=True))
    ocultas = set(AjusteSeccionPlanta.objects.filter(unidad=unidad, oculta=True).values_list('numero', flat=True))
    def visible(modulo, numero):
        return modulo in modulos and numero not in ocultas
    return {
        'identidad': visible('informacion-general', '1.3'),
        'presentacion': visible('informacion-general', '1.1'),
        'repositorio': visible('informacion-general', '1.5'),
        'areas': visible('areas-equipos', '2.1'),
        'equipos': visible('areas-equipos', '2.2'),
        'software': visible('areas-equipos', '2.3'),
        'matriz': visible('docencia-capacitacion', '4.2'),
        'juego': visible('docencia-capacitacion', '4.4'),
    }


def contexto_logistica(request, unidad, visibilidad=None):
    """Solo consulta los bloques publicados; no abre tablas de secciones ocultas."""
    visible = visibilidad if visibilidad is not None else visibilidad_secciones_logistica(unidad)
    fuentes, orientaciones = _metadatos_editoriales()
    areas = []
    if visible['areas']:
        areas = list(EspacioReservable.objects.filter(
            unidad=unidad, activo=True, integrada_en__isnull=True,
        ).select_related('ficha').order_by('orden', 'nombre', 'pk'))
        orden = {codigo: posicion for posicion, codigo in enumerate(AREAS)}
        areas.sort(key=lambda area: (orden.get(area.codigo, len(orden)), area.orden, area.nombre))
    indice = {_normalizar(nombre): area for area in areas for nombre in _nombres_area(area)}
    conteos = {'total': None}
    carreras, matriz = [], []
    pagina = None
    filtros = {'q': '', 'area': '', 'carrera': ''}
    if visible['matriz']:
        asignaturas = Asignatura.objects.filter(unidad=unidad, activa=True)
        conteos = asignaturas.aggregate(
            total=Count('pk'),
            **{f'area_{numero}': Count('pk', filter=_consulta_area(area)) for numero, area in enumerate(areas)},
        )
        carreras = list(asignaturas.exclude(carrera='').order_by('carrera').values_list('carrera', flat=True).distinct())
        filtros = {
            'q': _texto_filtro(request.GET.get('q')),
            'area': _texto_filtro(request.GET.get('area'), 60),
            'carrera': _texto_filtro(request.GET.get('carrera'), 180),
        }
        areas_por_codigo = {area.codigo: area for area in areas}
        if filtros['area'] not in areas_por_codigo:
            filtros['area'] = ''
        if filtros['carrera'] not in carreras:
            filtros['carrera'] = ''
        consulta = asignaturas
        if filtros['q']:
            consulta = consulta.filter(Q(nombre__icontains=filtros['q']) | Q(codigo__icontains=filtros['q']))
        if filtros['carrera']:
            consulta = consulta.filter(carrera=filtros['carrera'])
        if filtros['area']:
            consulta = consulta.filter(_consulta_area(areas_por_codigo[filtros['area']]))
        numero_pagina = request.GET.get('pagina', '1')
        if not re.fullmatch(r'[0-9]{1,6}', numero_pagina):
            numero_pagina = '1'
        campos = ['codigo', 'nombre', 'carrera', 'semestre']
        if visible['areas']:
            campos.append('descripcion')
        pagina = Paginator(consulta.only(*campos).order_by('carrera', 'nombre', 'pk'), 12).get_page(numero_pagina)
        for asignatura in pagina.object_list:
            area = _area_de(asignatura, indice) if visible['areas'] else None
            matriz.append({
                'asignatura': asignatura, 'area': area,
                'orientacion': orientaciones.get(asignatura.codigo, {}),
                'area_url': reverse('area_unidad', args=[unidad.slug, area.codigo]) if area else '',
            })
    fichas = []
    for numero, area in enumerate(areas):
        try:
            ficha = area.ficha
        except ObjectDoesNotExist:
            ficha = None
        ficha = ficha if ficha and ficha.publicada else None
        aplicaciones = _aplicaciones_editoriales(ficha)
        fichas.append({
            'espacio': area, 'numero': numero + 1,
            'url': reverse('area_unidad', args=[unidad.slug, area.codigo]),
            'ancla': f'area-{area.codigo}',
            'asignaturas': conteos.get(f'area_{numero}'),
            'descripcion': ficha.que_es if ficha and ficha.que_es else area.descripcion_publica,
            'competencias': aplicaciones['competencias'],
            'indicadores': aplicaciones['indicadores'],
            'practicas': aplicaciones['practicas'],
            'ficha_publicada': bool(ficha),
            'diagrama_x': _COORDENADAS[numero][0] if numero < len(_COORDENADAS) else 0,
            'diagrama_y': _COORDENADAS[numero][1] if numero < len(_COORDENADAS) else 0,
            'diagrama_nombre': _NOMBRES_DIAGRAMA.get(area.codigo, (area.nombre, '')),
        })
    equipos = None
    if visible['equipos']:
        registros = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True)
        equipos = registros.aggregate(
            registrados=Count('pk', distinct=True),
            verificados=Count('pk', filter=Q(existencia_verificada=True), distinct=True),
            operativos_verificados=Count('pk', filter=Q(
                existencia_verificada=True, estado_unidad__in=UnidadEquipo.ESTADOS_PUBLICOS,
            ), distinct=True),
        )
    software = None
    if visible['software']:
        software = SoftwareDisponible.objects.filter(unidad=unidad, activo=True).aggregate(
            registrados=Count('pk', distinct=True),
            instalacion_asociada=Count('pk', filter=Q(equipos_instalados__isnull=False), distinct=True),
        )
    presentacion = None
    if visible['presentacion']:
        try:
            presentacion = unidad.presentacion
        except ObjectDoesNotExist:
            pass
        if not presentacion or not presentacion.publicada:
            presentacion = None
    return {
        'unidad': unidad, 'areas_logistica': fichas, 'diagrama_areas': fichas[:6],
        'total_asignaturas': conteos['total'], 'carreras_logistica': carreras,
        'matriz_logistica': matriz, 'pagina_matriz': pagina, 'filtros_logistica': filtros,
        'consulta_matriz': urlencode({clave: valor for clave, valor in filtros.items() if valor}),
        'hay_filtros': any(filtros.values()), 'equipos_logistica': equipos, 'software_logistica': software,
        'presentacion_logistica': presentacion, 'visibilidad_logistica': visible,
        'fuentes_logistica': list(fuentes.values()),
        'juego_cerveza_url': reverse('logistica_juego_cerveza', args=[unidad.slug]) if visible['juego'] else '',
        'identidad_url': reverse('logistica_identidad', args=[unidad.slug]),
    }


def logistica_identidad_visible_para(unidad, usuario, visibilidad=None):
    """La sección institucional controla también esta URL directa."""
    if unidad.slug != SLUG or not unidad.activo or not tipologia_activa(unidad.dependencia):
        return False
    visible = visibilidad if visibilidad is not None else visibilidad_secciones_logistica(unidad)
    return visible['identidad'] or puede_gestionar_unidad(usuario, unidad)


@require_safe
@xframe_options_sameorigin
def logistica_identidad_view(request, slug):
    if slug != SLUG:
        raise Http404
    unidad = get_object_or_404(Unidad, slug=slug, activo=True, dependencia='laboratorios')
    visibilidad = visibilidad_secciones_logistica(unidad)
    if not logistica_identidad_visible_para(unidad, request.user, visibilidad):
        raise Http404
    return render(request, 'portal/pages/unidades/logistica/identidad.html', contexto_logistica(request, unidad, visibilidad))
