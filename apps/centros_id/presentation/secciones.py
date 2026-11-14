"""Las páginas que se abren dentro del visualizador de un Centro I+D: cada sección del mapa, la página de cada área,
las carpetas propias del centro y los fragmentos que se abren en modales (un equipo, un proyecto, una persona…).

Son documentos propios, con la paleta institucional, que la ficha carga en su visualizador; por eso se sirven con
`xframe_options_sameorigin`. Los modelos se importan dentro de cada función: las rutas del contexto se cargan sin
configurar Django."""

import re
from collections import OrderedDict
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import prefetch_related_objects
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.centros_id.identidades import identidad_de

from apps.centros_id.mapa import MAPA, SUBPAGINAS
from apps.centros_id.gestion_catalogo import url_edicion
from apps.centros_id.escenarios import contenido_admitido, filtro_contenido
from apps.centros_id.presentation.views import _centro, _contenidos, _portada_de, portada_de_area

# Los pasos visibles corresponden a los estados que guarda SolicitudCentro.
RUTA_SERVICIO = (
    ('Recibida', 'Registras la necesidad y recibes una referencia para seguirla.'),
    ('Evaluación técnica', 'El centro revisa alcance, requisitos, recursos y condiciones económicas.'),
    ('Aprobada y planificada', 'Se acuerdan entregables y, cuando aplica, se confirma recurso y horario.'),
    ('En ejecución', 'El centro registra la atención y sus compromisos.'),
    ('Entregada', 'Recibes el resultado acordado.'),
    ('Cerrada', 'Se registra el cierre; una solicitud también puede no proceder o cancelarse con motivo.'),
)


def _agrupar(filas, clave):
    grupos = OrderedDict()
    for fila in filas:
        grupos.setdefault(clave(fila), []).append(fila)
    return grupos


def _abrir(request):
    """El elemento que la página abre sola en su modal (?abrir=pk), si lo piden."""
    from .parametros import identificador
    return identificador(request.GET.get('abrir', ''))


def _base(request, centro, c, seccion_clave):
    """El contexto común de toda página del visualizador."""
    seccion = MAPA.seccion(seccion_clave)
    ajuste = c.ajustes.get(seccion_clave)
    return {
        'centro': centro, 'c': c, 'gestor': c.gestor, 'generado_en': timezone.localtime(), 'abrir': _abrir(request),
        'seccion': {**seccion, 'titulo': ajuste.titulo if ajuste and ajuste.titulo else seccion['titulo']},
        'pestana': MAPA.pestanas[seccion['pestana']],
        'ficha_url': reverse('centro_id', args=[centro.slug]),
        'solicitar_url': reverse('seccion_centro_id', args=[centro.slug, 'solicitar']),
        'completar': c.completar(seccion_clave) if c.gestor else '',
    }


def _nombres_de(area):
    """Los nombres con los que un texto libre puede aludir a un área: completo, corto y cada parte del corto
    («Prototipado y FabLab» también es «FabLab»)."""
    nombres = [area.nombre, area.nombre_corto]
    nombres += [parte.strip() for parte in re.split(r',| y | e ', area.nombre_corto or '') if len(parte.strip()) >= 5]
    return [nombre.lower() for nombre in nombres if nombre]


def _area_de_texto(areas, texto):
    """El área que nombra un texto libre (la cadena integrada nombra áreas sin clave); gana el nombre más largo."""
    texto = (texto or '').lower()
    candidatos = sorted(((nombre, area) for area in areas for nombre in _nombres_de(area)), key=lambda par: -len(par[0]))
    return next((area for nombre, area in candidatos if nombre in texto), None)


# ----------------------------------------------------------------------------- las secciones
def _imagenes(centro):
    """Las imágenes del centro y de sus áreas: primero las generales, luego las de cada área, en su orden."""
    return sorted(centro.imagenes.select_related('componente'),
                  key=lambda i: (i.componente_id is not None, i.componente_id or 0, i.orden, i.pk))


def _galeria_del_centro(centro):
    """Las fotos que abre el visor de «Conoce el centro»: las generales y las de cada área, nunca planos. La portada
    entra solo si el centro no tiene fotos generales (de lo contrario es una de ellas y se vería repetida)."""
    fotos = [i for i in _imagenes(centro) if not i.es_plano]
    generales = any(i.componente_id is None for i in fotos)
    portada = [SimpleNamespace(imagen=centro.imagen, titulo=centro.sigla or centro.nombre, credito=centro.credito_imagen,
                               es_plano=False)] if centro.imagen and not generales else []
    return portada + fotos


# Lo que hace un centro de investigación y desarrollo según su definición institucional: sostener una agenda científica
# y tecnológica e integrar capacidades, talento y proyectos para producir conocimiento, innovación y transferencia. Cada
# función dice dónde la documenta el centro (la primera sección con contenido) y qué tiene registrado.
FUNCIONES = (
    ('Agenda de investigación', 'fas fa-compass', ('lineas',),
     'Define y sostiene líneas de investigación con retos prioritarios, alineadas con su plan de desarrollo y con las '
     'necesidades del territorio.',
     lambda c: ((len(c.lineas), 'línea', 'líneas'), (sum(len(linea.lista_retos) for linea in c.lineas), 'reto', 'retos'))),
    ('Investigación aplicada y desarrollo experimental', 'fas fa-flask', ('proyectos',),
     'Ejecuta proyectos que generan conocimiento y lo convierten en métodos, prototipos y soluciones validadas, con su '
     'equipo, sus hitos y su financiamiento.',
     lambda c: ((len(c.proyectos_activos), 'proyecto en curso', 'proyectos en curso'),
                (len(c.proyectos), 'proyecto en la cartera', 'proyectos en la cartera'))),
    ('Talento investigador', 'fas fa-user-graduate', ('investigadores', 'grupos', 'personal', 'direccion'),
     'Reúne investigadores, grupos de investigación y personal técnico, y forma a nuevos investigadores en sus '
     'proyectos.',
     lambda c: ((len(c.investigadores), 'investigador', 'investigadores'), (len(c.grupos), 'grupo', 'grupos'),
                (len(c.por_rol('tesista', 'estudiante')), 'persona en formación', 'personas en formación'))),
    ('Resultados y propiedad intelectual', 'fas fa-certificate', ('produccion', 'desarrollos'),
     'Produce resultados verificables —publicaciones, datos, software y prototipos— y protege los que pueden '
     'transferirse.',
     lambda c: ((len(c.produccion), 'producto científico', 'productos científicos'),
                (len(c.desarrollos), 'desarrollo', 'desarrollos'))),
    ('Innovación y transferencia', 'fas fa-exchange-alt', ('casos', 'alianzas'),
     'Lleva sus resultados a quien los usa —empresas, instituciones, comunidades y emprendimientos— con alianzas que '
     'lo sostienen.',
     lambda c: ((len(c.casos), 'caso de transferencia', 'casos de transferencia'), (len(c.aliados), 'aliado', 'aliados'))),
    ('Capacidades propias y vinculadas', 'fas fa-th-large', ('areas', 'vinculadas'),
     'Opera áreas con equipamiento y procesos propios y se articula, mediante instrumentos formales, con las unidades de '
     'la universidad que amplían su alcance.',
     lambda c: ((len(c.areas), 'área propia', 'áreas propias'),
                (len(c.unidades_vinculadas), 'capacidad vinculada', 'capacidades vinculadas'))),
    ('Servicios científico-tecnológicos', 'fas fa-concierge-bell', ('portafolio',),
     'Presta servicios especializados con un ciclo controlado: solicitud, evaluación técnica, costeo, autorización, '
     'ejecución, entrega y cierre.',
     lambda c: ((len(c.servicios), 'servicio', 'servicios'), (len({s.linea for s in c.servicios}), 'línea de servicio',
                                                              'líneas de servicio'))),
    ('Gobernanza y evaluación', 'fas fa-sitemap', ('gobierno',),
     'Se gobierna con una dirección, un comité técnico-científico y un plan, y rinde cuentas con indicadores de '
     'investigación, innovación e impacto.',
     lambda c: ((len(c.gobierno), 'instancia de gobierno', 'instancias de gobierno'),
                (len(c.indicadores_medidos), 'indicador medido', 'indicadores medidos'))),
)


def _funciones(c):
    """Las funciones que el centro cumple con registros: al público, solo las que tienen evidencia; quien gestiona ve
    todas, para saber qué le falta registrar."""
    filas = []
    for titulo, icono, claves, texto, contar in FUNCIONES:
        evidencias = [f'{total} {uno if total == 1 else varios}' for total, uno, varios in contar(c) if total]
        if not evidencias and not c.gestor:
            continue
        seccion = next((clave for clave in claves if c.tiene(clave)), claves[0])
        filas.append({'titulo': titulo, 'icono': icono, 'texto': texto, 'evidencias': evidencias,
                      'seccion': MAPA.seccion(seccion)['titulo'],
                      'url': reverse('seccion_centro_id', args=[c.centro.slug, seccion])})
    return filas


def _presentacion(request, centro, c):
    """«Conoce el centro», con la pieza de «Conoce la unidad» de Laboratorios: la portada con su foto y sus cifras, un
    tema a la vez con sus fotos, sus objetivos, sus funciones como centro de investigación y desarrollo, sus áreas y
    sus videos; de aquí cuelgan la identidad y la ubicación."""
    slug = centro.slug
    destacado = next((p for p in c.proyectos if p.destacado), None) or (c.proyectos_activos[0] if c.proyectos_activos else None)
    temas = [{'titulo': 'Qué es', 'icono': 'fas fa-landmark', 'texto': centro.presentacion or centro.proposito}]
    if centro.presentacion and centro.proposito:
        temas.append({'titulo': 'Para qué existe', 'icono': 'fas fa-bullseye', 'texto': centro.proposito})
    ofrece = [(len(c.areas), 'áreas propias', reverse('seccion_centro_id', args=[slug, 'areas'])),
              (len(c.servicios), 'servicios en el portafolio', reverse('seccion_centro_id', args=[slug, 'portafolio'])),
              (len(c.unidades_vinculadas), 'capacidades vinculadas', reverse('seccion_centro_id', args=[slug, 'vinculadas'])),
              (len(c.lineas), 'líneas de investigación', reverse('seccion_centro_id', args=[slug, 'lineas']))]
    enlaces = [{'valor': valor, 'titulo': titulo, 'url': url} for valor, titulo, url in ofrece if valor]
    if enlaces:
        temas.append({'titulo': 'Qué ofrece', 'icono': 'fas fa-hand-holding', 'enlaces': enlaces,
                      'texto': 'Lo que el centro pone a disposición de quien investiga, produce o estudia: sus áreas con '
                               'sus equipos y sus procesos, su portafolio de servicios, las capacidades con las que se '
                               'articula y sus líneas de investigación.'})
    galeria = _galeria_del_centro(centro)
    fotos = []
    for imagen in galeria:
        if imagen.imagen.url not in fotos:
            fotos.append(imagen.imagen.url)
    return {'videos': centro.lista_videos, 'cifras': c.cifras(5), 'destacado': destacado, 'portada': _portada_de(centro),
            'grupos_areas': _grupos_de_areas(c), 'temas': temas, 'fotos': fotos[:3], 'galeria': galeria,
            'objetivos': centro.lista_objetivos, 'funciones': _funciones(c), 'datos': centro.lista_cifras,
            'fase': c.fase_actual, 'identidad_url': reverse('seccion_centro_id', args=[slug, 'identidad']),
            'ubicacion_url': reverse('seccion_centro_id', args=[slug, 'ubicacion'])}


def _identidad(request, centro, c):
    """Identidad y contacto: la ficha del centro, quién lo dirige y cuántas personas atienden (nunca quiénes)."""
    atienden = set(centro.gestores.values_list('pk', flat=True))
    if centro.responsable_id:
        atienden.add(centro.responsable_id)
    return {'director': next((p for p in c.por_rol('director')), None), 'comite': len(c.por_rol('comite')),
            'atienden': len(atienden), 'fase': c.fase_actual,
            'documentos_creacion': c.documentos_de('creacion'),
            'editar_identidad': c._admin('centroid') if c.gestor else '',
            'hay_equipo': bool(c.por_rol('director', 'comite')),
            'enlace_publico': request.build_absolute_uri(reverse('centro_id', args=[centro.slug])),
            'ubicacion_url': reverse('seccion_centro_id', args=[centro.slug, 'ubicacion'])}


def como_llegar(centro):
    """La ruta en Google Maps hasta el punto exacto o, sin él, la búsqueda por dirección o referencia."""
    if centro.tiene_coordenadas:
        return 'https://www.google.com/maps/dir/?' + urlencode({'api': 1, 'destination': f'{centro.latitud},{centro.longitud}'})
    referencia = centro.direccion or centro.ubicacion
    if referencia:
        return 'https://www.google.com/maps/search/?' + urlencode({'api': 1, 'query': f'{centro.nombre}, {referencia}'})
    return ''


def _ubicacion(request, centro, c):
    """Ubicación y cómo llegar: el centro sobre el mapa de las sedes, con el mismo mapa que usan las unidades."""
    from apps.centros_id.vinculos import sedes_en_el_mapa

    return {'mapa': {'nombre': centro.nombre, 'espacio': centro.ubicacion, 'direccion': centro.direccion,
                     'imagen': _portada_de(centro), 'punto': centro.punto, 'enElMismoPunto': [],
                     'sedes': sedes_en_el_mapa(), 'comoLlegar': como_llegar(centro)}}


def _ahora(request, centro, c):
    return {'proyectos': c.proyectos_activos[:6], 'en_ejecucion': c.en_ejecucion,
            'resultados': c.resultados[:6], 'novedades': [n for n in c.novedades if not n.proximo][:6],
            'eventos': c.eventos_proximos[:4], 'convocatorias': c.convocatorias[:4], 'fase': c.fase_actual,
            'fases': c.fases if not centro.en_operacion else [],
            'presupuesto': list(centro.presupuesto.all()) if not centro.en_operacion else []}


def _como_trabaja(request, centro, c):
    cadena = [{'etapa': etapa, 'texto': texto, 'resultado': resultado, 'area': _area_de_texto(c.areas, texto)}
              for etapa, texto, resultado in centro.etapas_cadena]
    return {'ruta': c.ruta, 'cadena': cadena, 'modalidades': c.modalidades}


def _gobierno(request, centro, c):
    from apps.centros_id.models import DocumentoCentro

    documentos = c.documentos_de(*DocumentoCentro.GOBIERNO)
    return {'gobierno': c.gobierno, 'director': next((p for p in c.por_rol('director')), None),
            'comite': c.por_rol('comite'),
            'plan': next((d for d in documentos if d.tipo == 'plan_desarrollo'), None),
            'informes': [d for d in documentos if d.tipo in ('informe_anual', 'evaluacion')],
            'actas': [d for d in documentos if d.tipo == 'acta_comite'],
            'indicadores': _agrupar(c.indicadores if c.gestor else c.indicadores_medidos, lambda i: i.categoria),
            'medidos': len(c.indicadores_medidos), 'por_medir': len(c.indicadores) - len(c.indicadores_medidos),
            'riesgos': _agrupar(c.riesgos, lambda r: r.categoria), 'fase': c.fase_actual}


def _documentos(request, centro, c):
    """Los documentos y las normas del centro en una sola página, por tipo, con la seguridad de cada área y las
    carpetas propias que el centro publica aquí."""
    documentos = c.documentos_de(*c._documentales())
    seguridad = [(a, a.control) for a in c.areas if a.control[0]]
    return {'documentos': _agrupar(documentos, lambda d: d.get_tipo_display()), 'seguridad': seguridad,
            'carpetas': c._carpetas('el-centro', 'documentos')}


def _superficie(c):
    """Los metros cuadrados cubiertos del edificio, sin los espacios exteriores."""
    return sum((z.area_m2 for z in c.zonas if not z.nivel.lower().startswith('exterior')), Decimal(0))


def _tarjeta(c, area):
    """Un área para su tarjeta: su foto y lo que tiene (equipos, servicios y proyectos en los que participa)."""
    cuentas = ((len(area.equipos.all()), 'fas fa-toolbox', 'equipo', 'equipos'),
               (len([s for s in area.servicios.all() if s.activo]), 'fas fa-concierge-bell', 'servicio', 'servicios'),
               (sum(1 for p in c.proyectos if area in p.componentes.all()), 'fas fa-rocket', 'proyecto', 'proyectos'))
    return {'area': area, 'imagen': portada_de_area(area), 'modulos': c.modulos_de(area),
            'cuentas': [(icono, f'{total} {uno if total == 1 else varios}') for total, icono, uno, varios in cuentas if total]}


def _grupos_de_areas(c):
    """Las áreas del centro agrupadas por su tipo y en su orden, cada una con su tarjeta. El primer grupo es el que la
    ficha destaca (en el CIDT, sus divisiones)."""
    return [(tipo, [_tarjeta(c, area) for area in areas]) for tipo, areas in c.areas_por_tipo()]


def _areas(request, centro, c):
    """Áreas del centro: sus áreas por tipo y el edificio que las aloja (dónde está cada una en el plano, los espacios
    por nivel, el recorrido y las imágenes del edificio). Las fotos de cada área viven en su página."""
    por_nivel = _agrupar(c.zonas, lambda z: z.nivel)
    return {'grupos_areas': _grupos_de_areas(c),
            'planos': [{'plano': plano, 'zonas': [z for z in c.zonas if z.nivel == plano.nivel and z.en_plano]}
                       for plano in c.planos],
            'zonas_por_nivel': por_nivel, 'total_m2': _superficie(c),
            'superficie': {nivel: sum(z.area_m2 for z in filas) for nivel, filas in por_nivel.items()},
            'galeria': [i for i in _imagenes(centro) if i.componente_id is None], 'recorrido': centro.recorrido_360_url}


def _relaciones(request, centro, c):
    grupos = OrderedDict()
    for area in c.areas:
        grupos.setdefault(area.get_tipo_display(), []).append(area)
    por_area = {a.pk: {'area': a, 'entrega': [], 'recibe': []} for a in c.areas}
    for relacion in c.relaciones:
        if relacion.origen_id in por_area:
            por_area[relacion.origen_id]['entrega'].append(relacion)
        if relacion.destino_id in por_area:
            por_area[relacion.destino_id]['recibe'].append(relacion)
    return {'grupos': grupos, 'relaciones': c.relaciones,
            'por_area': [fila for fila in por_area.values() if fila['entrega'] or fila['recibe']]}


def _vinculadas(request, centro, c):
    from apps.centros_id.vinculos import unidades_de

    unidades = {u['slug']: u for u in unidades_de(c.unidades_vinculadas)}
    filas = []
    for slug in c.unidades_vinculadas:
        articulacion = next((a for a in c.articulaciones if a.unidad_slug == slug), None)
        areas = [a for a in c.areas if slug in a.lista_unidades]
        unidad = unidades.get(slug) or {'nombre': articulacion.actor if articulacion else slug, 'tipo': '', 'url': ''}
        filas.append({'unidad': unidad, 'articulacion': articulacion, 'areas': areas})
    return {'grupos': _agrupar(filas, lambda f: f['unidad']['tipo'] or 'Unidad de la universidad')}


def _personas(roles, titulo_vacio):
    """Las personas de unos roles. Tesistas y estudiantes se cuentan en público y se nombran solo al gestor."""
    def vista(request, centro, c):
        from apps.centros_id.models import Integrante

        personas = c.por_rol(*roles)
        nombradas = [p for p in personas if p.rol in Integrante.PUBLICOS or c.gestor]
        reservadas = _agrupar([p for p in personas if p not in nombradas], lambda p: p.get_rol_display())
        return {'grupos': _agrupar(nombradas, lambda p: p.get_rol_display()),
                'reservadas': [(rol, len(filas)) for rol, filas in reservadas.items()],
                'gobierno': c.gobierno if 'director' in roles else [], 'vacio': titulo_vacio,
                'areas_con_personas': _agrupar([p for p in nombradas if p.componente], lambda p: p.componente)}
    return vista


def _grupos(request, centro, c):
    return {'grupos': c.grupos, 'carreras': [a for a in c.articulaciones if a.tipo == 'carrera'],
            'futuras': [a for a in c.articulaciones if a.tipo == 'futura'],
            'integrantes_por_grupo': {g.pk: [p for p in c.integrantes if p.grupo_id == g.pk] for g in c.grupos}}


def _lineas(request, centro, c):
    texto, area = request.GET.get('q', '').strip(), request.GET.get('area', '')
    lineas = [linea for linea in c.lineas if (not area or (linea.componente and linea.componente.codigo == area))
              and (not texto or texto.casefold() in f'{linea.nombre} {linea.problema} {linea.resultados}'.casefold())]
    return {'filas': [{'linea': linea, 'proyectos': [p for p in c.proyectos if p.linea_id == linea.pk],
                      'resultados': sum(1 for r in c.resultados if r.proyecto and r.proyecto.linea_id == linea.pk)}
                     for linea in lineas], 'filtro': {'q': texto, 'area': area}}


def _proyectos(request, centro, c):
    from django.utils.translation import gettext
    from apps.centros_id import selectors_cientificos as consultas
    from apps.centros_id.contenidos import ocultar_referencias_muestra
    from apps.centros_id.models import Proyecto
    from .paginacion import paginar
    filtro = consultas.filtros(request.GET, ('estado', 'linea', 'area', 'anio', 'sector', 'q'))
    universo = c.consulta_proyectos
    consulta = consultas.filtrar_proyectos(universo, filtro)
    paginacion = paginar(consultas.proyectos_para_pagina(consulta, centro)
                        .order_by('-destacado', '-inicio', 'titulo', 'pk'), request)
    proyectos = [ocultar_referencias_muestra(p) for p in paginacion['pagina']]
    for proyecto in proyectos:
        proyecto.estado_catalogo = (gettext('Transferencia pendiente de documentar')
            if proyecto.estado == 'transferido' and not proyecto.transferencia_catalogo else proyecto.get_estado_display())
    return {'proyectos': proyectos,
            'paginacion': paginacion, 'total': c.resumen_proyectos['total'],
            'coincidencias': paginacion['pagina'].paginator.count, 'filtro': filtro, 'estados': Proyecto.ESTADOS,
            'lineas_filtro': centro.lineas.values('pk', 'nombre'),
            'areas_filtro': centro.componentes.filter(publicado=True).values('codigo', 'nombre', 'nombre_corto'),
            'anios': consultas.anios_proyectos(universo), 'sectores': consultas.distintos(universo, 'sector'),
            'financiado': consultas.financiado_publico(consulta)}


def _consulta_resultados(request, c, universo, catalogo):
    from apps.centros_id import selectors_cientificos as consultas
    from apps.centros_id.contenidos import ocultar_referencias_muestra
    from apps.centros_id.models import Resultado
    from .paginacion import paginar
    filtro = consultas.filtros(request.GET, ('tipo', 'anio', 'linea', 'proyecto', 'sector', 'tecnologia', 'trl', 'q'))
    consulta = consultas.filtrar_resultados(universo, filtro, c.centro)
    paginacion = paginar(consulta.select_related('proyecto__linea', 'componente').prefetch_related('autores')
                        .order_by('-anio', 'titulo', 'pk'), request)
    filas = [ocultar_referencias_muestra(r) for r in paginacion['pagina']]
    opciones = consultas.opciones_proyectos(c.consulta_proyectos, request.GET.get('proyecto_q', ''), filtro['proyecto'])
    parametros = urlencode({k: v for k, v in filtro.items() if v} | {'catalogo': catalogo})
    tipos = consultas.distintos(universo, 'tipo')
    return {'filtrados': filas, 'total': paginacion['pagina'].paginator.count, 'paginacion': paginacion,
            'hay_resultados': universo.exists(), 'filtro': filtro, 'catalogo': catalogo,
            'tipos': [(tipo, nombre) for tipo, nombre in Resultado.TIPOS if tipo in tipos],
            'anios': list(reversed(consultas.distintos(universo, 'anio', vacios=True))),
            'sectores': consultas.distintos(universo, 'sector'),
            'tecnologias': consultas.distintos(universo, 'tecnologia'),
            'lineas_filtro': c.centro.lineas.values('pk', 'nombre'),
            'proyectos_filtro': opciones['opciones'], 'proyecto_q': opciones['q'], 'mas_proyectos_filtro': opciones['hay_mas'],
            'exportar_url': reverse('exportar_resultados_centro_id', args=[c.centro.slug]) + '?' + parametros}


def _produccion(request, centro, c):
    contexto = _consulta_resultados(request, c, c.consulta_resultados('produccion'), 'produccion')
    contexto['resultados'] = _agrupar(contexto['filtrados'], lambda r: r.anio)
    return contexto


def _desarrollos(request, centro, c):
    contexto = _consulta_resultados(request, c, c.consulta_resultados('desarrollos'), 'desarrollos')
    contexto.update(prototipos=[r for r in contexto['filtrados'] if r.tipo == 'prototipo'],
                    propiedad=[r for r in contexto['filtrados'] if r.tipo == 'propiedad_intelectual'],
                    niveles_trl=range(1, 10))
    return contexto


def _casos(request, centro, c):
    sector, area = request.GET.get('sector', ''), request.GET.get('area', '')
    casos = [k for k in c.casos if (not sector or k.sector == sector) and (not area or (k.componente and k.componente.codigo == area))]
    return {'casos': casos, 'sectores': sorted({k.sector for k in c.casos if k.sector}),
            'filtro': {'sector': sector, 'area': area},
            'transferidos': [p for p in c.proyectos if p.estado == 'transferido' and p.transferencia_documentada]}


def _alianzas(request, centro, c):
    financiadores = OrderedDict()
    for p in c.proyectos:
        if p.financiador:
            fila = financiadores.setdefault(p.financiador, {'nombre': p.financiador, 'proyectos': 0, 'monto': Decimal(0)})
            fila['proyectos'] += 1
            if p.monto_publico:
                fila['monto'] += p.monto or 0
    return {'aliados': _agrupar([a for a in c.aliados if a.tipo != 'emprendimiento'], lambda a: a.get_tipo_display()),
            'emprendimientos': [a for a in c.aliados if a.tipo == 'emprendimiento'],
            'externos': [a for a in c.articulaciones if a.tipo == 'externo'], 'financiadores': list(financiadores.values())}


def _portafolio(request, centro, c):
    linea, area, texto = request.GET.get('linea', ''), request.GET.get('area', ''), request.GET.get('q', '').strip()
    servicios = c.servicios
    if linea:
        servicios = [s for s in servicios if s.linea == linea]
    if area:
        servicios = [s for s in servicios if s.componente and s.componente.codigo == area]
    if texto:
        t = texto.lower()
        servicios = [s for s in servicios if t in f'{s.nombre} {s.descripcion} {s.entregable}'.lower()]
    lineas = []
    for s in c.servicios:
        if s.linea not in lineas:
            lineas.append(s.linea)
    return {'servicios_por_linea': _agrupar(servicios, lambda s: s.linea), 'total': len(servicios), 'todos': len(c.servicios),
            'lineas': lineas, 'filtro': {'linea': linea, 'area': area, 'q': texto}, 'ruta': RUTA_SERVICIO,
            'recibe_solicitudes': any(s.solicitable for s in c.servicios)}


def _recursos(request, centro, c):
    from apps.centros_id.formularios import DisponibilidadForm
    from apps.centros_id.models import EquipoCentro
    from apps.centros_id.operaciones import disponibilidad

    equipos = list(EquipoCentro.objects.filter(componente__centro=centro, componente__publicado=True, **filtro_contenido(centro))
                   .select_related('componente').prefetch_related('horarios'))
    zonas = [z for z in c.zonas if z.reservable and (not z.componente_id or z.componente.publicado)]
    seleccionado = None
    for clave, filas in (('equipo', equipos), ('zona', zonas)):
        if request.GET.get(clave):
            seleccionado = next((r for r in filas if str(r.pk) == request.GET[clave]), None)
            if seleccionado is None:
                raise Http404
            break
    formulario = DisponibilidadForm(request.GET if request.GET.get('fecha') else None,
                                    initial={'fecha': c.hoy})
    ventanas = None
    if seleccionado and formulario.is_valid():
        ventanas = disponibilidad(seleccionado, formulario.cleaned_data['fecha'])
    q = request.GET.get('q', '').strip()
    if q:
        equipos = [r for r in equipos if q.casefold() in f'{r.nombre} {r.codigo} {r.funcion}'.casefold()]
        zonas = [r for r in zonas if q.casefold() in f'{r.nombre} {r.codigo}'.casefold()]
    herramientas = list(c.herramientas)
    if c.escenario and centro.slug == 'cidt-upec':
        herramientas.append(SimpleNamespace(nombre='Capacidad de una línea de ensamble', version='1.0',
            get_tipo_display='Calculadora educativa', objetivo='Comparar tiempos de ciclo, puestos paralelos y demanda de dos etapas en serie.',
            entradas='Turno de 1 a 1.440 minutos; tiempo productivo de 1 a 100%; ciclos de 0,1 a 10.000 minutos/unidad y de 1 a 100 puestos por etapa.',
            metodo='Capacidad de cada etapa = parte entera de minutos productivos × puestos / tiempo de ciclo. La capacidad de la línea es el mínimo de ambas etapas.',
            salidas='Unidades por turno, etapa limitante y demanda pendiente.',
            supuestos='Flujo estable, puestos idénticos por etapa y buffer entre etapas; sin tiempos de arranque, fallos, retrabajo ni cambios de producto.',
            limites='Modelo educativo de capacidad nominal; no reproduce colas ni incertidumbre. Requiere contrastarse con mediciones para una decisión de ingeniería.',
            enlace=reverse('simulador_centro_id', args=[centro.slug])))
    return {'equipos': equipos, 'zonas': zonas, 'herramientas': herramientas,
            'unidades_operativas': c.oferta_vinculada['unidades'], 'recurso_seleccionado': seleccionado,
            'es_equipo': bool(seleccionado and hasattr(seleccionado, 'es_activo_individual')),
            'disponibilidad_form': formulario, 'ventanas': ventanas, 'busqueda': q,
            'zona_horaria': timezone.get_current_timezone_name()}


def _visitas(request, centro, c):
    areas = [a for a in c.areas if a.estado == 'operativa'] or c.areas
    return {'texto': centro.visitas_texto, 'tarjetas': [_tarjeta(c, area) for area in areas],
            'recorrido': centro.recorrido_360_url}


def _oportunidades(request, centro, c):
    from datetime import timedelta
    from apps.centros_id.contenido.cidt_operativo import CURSOS

    cursos, convocatorias = [], list(c.convocatorias)
    if c.escenario and centro.slug == 'cidt-upec':
        for programa in CURSOS:
            convocatoria = next((v for v in convocatorias if v.es_muestra and v.titulo == 'Curso: ' + programa['nombre']), None)
            if convocatoria:
                cursos.append({**programa, 'convocatoria': convocatoria,
                    'inicio': convocatoria.cierre + timedelta(days=3),
                    'fin': convocatoria.cierre + timedelta(days=10)})
                convocatorias.remove(convocatoria)
    return {'cursos_centro': cursos, 'cursos_vinculados': c.oferta_vinculada['cursos'], 'convocatorias': _agrupar(convocatorias, lambda v: v.get_tipo_display()),
            'modalidades': [m for m in c.modalidades if 'forma' in m.nombre.lower() or 'docencia' in m.nombre.lower()
                            or 'capacit' in m.nombre.lower()]}


# Las cifras que cada sección pone sobre el borde de su cabecera, como las páginas de Laboratorios: solo las que valen.
CIFRAS = {
    'ahora': lambda c: [(len(c.proyectos_activos), 'Proyectos en curso', 'fas fa-rocket'),
                        (c.en_ejecucion, 'Servicios en ejecución', 'fas fa-cogs'),
                        (len(c.eventos_proximos), 'Eventos próximos', 'fas fa-calendar-alt'),
                        (len(c.convocatorias), 'Convocatorias abiertas', 'fas fa-door-open')],
    'como_trabaja': lambda c: [(len(c.ruta), 'Etapas de la ruta', 'fas fa-route'),
                               (len(c.centro.etapas_cadena), 'Pasos de la cadena integrada', 'fas fa-project-diagram'),
                               (len(c.modalidades), 'Modalidades de funcionamiento', 'fas fa-th')],
    'gobierno': lambda c: [(len(c.gobierno), 'Instancias de gobierno', 'fas fa-sitemap'),
                           (len(c.indicadores_medidos), 'Indicadores medidos', 'fas fa-chart-bar'),
                           (len(c.riesgos), 'Riesgos con su mitigación', 'fas fa-shield-alt')],
    'documentos': lambda c: [(len(c.documentos_de(*c._documentales())), 'Documentos publicados', 'fas fa-file-pdf'),
                             (len([a for a in c.areas if a.control[0]]), 'Áreas con su control de seguridad',
                              'fas fa-hard-hat')],
    'areas': lambda c: [(len(c.areas), 'Áreas propias', 'fas fa-th-large'),
                        (sum(len(a.equipos.all()) for a in c.areas), 'Equipos con ficha', 'fas fa-toolbox'),
                        (len(c.servicios), 'Servicios que prestan', 'fas fa-concierge-bell'),
                        (_superficie(c), 'm² de instalaciones', 'fas fa-ruler-combined')],
    'relaciones': lambda c: [(len(c.relaciones), 'Flujos entre áreas', 'fas fa-exchange-alt'),
                             (len({r.origen_id for r in c.relaciones} | {r.destino_id for r in c.relaciones}),
                              'Áreas conectadas', 'fas fa-th-large')],
    'vinculadas': lambda c: [(len(c.unidades_vinculadas), 'Capacidades vinculadas', 'fas fa-link'),
                             (len([a for a in c.areas if a.lista_unidades]), 'Áreas que se articulan', 'fas fa-th-large'),
                             (len([a for a in c.articulaciones if a.unidad_slug and a.instrumento]),
                              'Con instrumento que las formaliza', 'fas fa-file-signature')],
    'direccion': lambda c: [(len(c.por_rol('director')), 'Dirección', 'fas fa-user-tie'),
                            (len(c.por_rol('comite')), 'Integrantes del comité', 'fas fa-users-cog'),
                            (len(c.gobierno), 'Instancias de gobierno', 'fas fa-sitemap')],
    'investigadores': lambda c: [(len(c.por_rol('investigador')), 'Investigadores', 'fas fa-user-graduate'),
                                 (len(c.por_rol('asociado')), 'Investigadores asociados', 'fas fa-user-friends'),
                                 (len(c.lineas), 'Líneas de investigación', 'fas fa-compass')],
    'personal': lambda c: [(len(c.por_rol('tecnico')), 'Personal técnico', 'fas fa-id-badge'),
                           (len(c.por_rol('visitante')), 'Investigadores visitantes', 'fas fa-plane-arrival'),
                           (len(c.por_rol('tesista', 'estudiante')), 'En formación', 'fas fa-user-graduate')],
    'grupos': lambda c: [(len(c.grupos), 'Grupos de investigación', 'fas fa-users'),
                         (len([a for a in c.articulaciones if a.tipo == 'carrera']), 'Carreras que participan',
                          'fas fa-graduation-cap'),
                         (len({g.facultad for g in c.grupos if g.facultad}), 'Facultades', 'fas fa-university')],
    'lineas': lambda c: [(len(c.lineas), 'Líneas de investigación', 'fas fa-compass'),
                         (sum(len(linea.lista_retos) for linea in c.lineas), 'Retos prioritarios', 'fas fa-bullseye'),
                         (len([p for p in c.proyectos if p.linea_id]), 'Proyectos en las líneas', 'fas fa-rocket')],
    'proyectos': lambda c: [(len(c.proyectos), 'Proyectos en la cartera', 'fas fa-folder-open'),
                            (len(c.proyectos_activos), 'En curso', 'fas fa-rocket'),
                            (sum(1 for p in c.proyectos if p.estado == 'finalizado'
                                 or (p.estado == 'transferido' and p.transferencia_documentada)),
                             'Concluidos o transferidos', 'fas fa-flag-checkered'),
                            (sum(1 for p in c.proyectos if p.financiador), 'Con financiamiento', 'fas fa-coins')],
    'produccion': lambda c: [(len(c.produccion), 'Productos científicos', 'fas fa-book-open'),
                             (len({r.tipo for r in c.produccion}), 'Tipos de producto', 'fas fa-layer-group'),
                             (len({r.anio for r in c.produccion}), 'Años con producción', 'fas fa-calendar')],
    'desarrollos': lambda c: [(sum(1 for r in c.desarrollos if r.tipo == 'prototipo'), 'Prototipos y desarrollos',
                               'fas fa-cogs'),
                              (sum(1 for r in c.desarrollos if r.tipo == 'propiedad_intelectual' and r.pi_documentada),
                               'Registros de propiedad intelectual', 'fas fa-certificate'),
                              (max((r.trl for r in c.desarrollos if r.trl_documentado), default=None), 'Nivel de madurez más alto (TRL)',
                               'fas fa-signal')],
    'casos': lambda c: [(len(c.casos), 'Casos documentados', 'fas fa-award'),
                        (len({k.sector for k in c.casos if k.sector}), 'Sectores beneficiados', 'fas fa-industry'),
                        (sum(1 for p in c.proyectos if p.estado == 'transferido' and p.transferencia_documentada), 'Proyectos transferidos',
                         'fas fa-exchange-alt')],
    'alianzas': lambda c: [(sum(1 for a in c.aliados_vigentes if a.tipo != 'emprendimiento'), 'Alianzas con vigencia documentada', 'fas fa-handshake'),
                           (len({p.financiador for p in c.proyectos if p.financiador}), 'Financiadores', 'fas fa-coins'),
                           (sum(1 for a in c.aliados if a.tipo == 'emprendimiento'), 'Emprendimientos', 'fas fa-seedling')],
    'portafolio': lambda c: [(len(c.servicios), 'Servicios', 'fas fa-concierge-bell'),
                             (len({s.linea for s in c.servicios}), 'Líneas de servicio', 'fas fa-stream'),
                             (len({s.componente_id for s in c.servicios if s.componente_id}), 'Áreas que los prestan',
                              'fas fa-th-large')],
    'oportunidades': lambda c: [(len(c.convocatorias), 'Convocatorias abiertas', 'fas fa-door-open'),
                                (len({v.tipo for v in c.convocatorias}), 'Tipos de oportunidad', 'fas fa-layer-group')],
}

SECCIONES = {
    'presentacion': _presentacion, 'ahora': _ahora, 'como_trabaja': _como_trabaja, 'gobierno': _gobierno,
    'documentos': _documentos, 'areas': _areas,
    'relaciones': _relaciones, 'vinculadas': _vinculadas,
    'direccion': _personas(('director', 'comite'), 'La dirección y el comité se publican cuando el centro los registra.'),
    'investigadores': _personas(('investigador', 'asociado'), 'Los investigadores se publican cuando el centro los registra.'),
    'grupos': _grupos,
    'personal': _personas(('tecnico', 'visitante', 'tesista', 'estudiante'), 'Se publican cuando el centro los registra.'),
    'lineas': _lineas, 'proyectos': _proyectos, 'produccion': _produccion, 'desarrollos': _desarrollos,
    'casos': _casos, 'alianzas': _alianzas, 'portafolio': _portafolio, 'visitas': _visitas,
    'oportunidades': _oportunidades, 'recursos': _recursos,
}
SUBPAGINAS_VISTAS = {'identidad': _identidad, 'ubicacion': _ubicacion}
PLANTILLAS = {'presentacion': 'conoce', 'direccion': 'personas', 'investigadores': 'personas', 'personal': 'personas'}


@xframe_options_sameorigin
def seccion_view(request, slug, clave):
    """Una sección del mapa o una página que cuelga de ella (identidad y ubicación), con la visibilidad y el ajuste de
    su sección y, si la sección las tiene, sus cifras sobre la cabecera."""
    if clave == 'solicitar':
        return solicitar_view(request, slug)
    padre = MAPA.padre(clave)
    if padre not in SECCIONES:
        raise Http404
    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    ajuste = c.ajustes.get(padre)
    if (ajuste and ajuste.oculta) or (not c.tiene(padre) and not c.gestor):
        raise Http404
    contexto = _base(request, centro, c, padre)
    if clave in SUBPAGINAS:
        contexto['subpagina'] = {'clave': clave, **SUBPAGINAS[clave]}
        contexto.update(SUBPAGINAS_VISTAS[clave](request, centro, c))
    else:
        contexto.update(SECCIONES[clave](request, centro, c))
        if clave in CIFRAS:
            contexto['cifras'] = [{'valor': int(valor), 'titulo': titulo, 'icono': icono}
                                  for valor, titulo, icono in (c.cifras_cientificas(clave)
                                  if clave in ('proyectos', 'produccion', 'desarrollos') else CIFRAS[clave](c)) if valor]
    return render(request, f'centros_id/visor/{PLANTILLAS.get(clave, clave)}.html', contexto)


def portafolio_view(request, slug):
    return seccion_view(request, slug, 'portafolio')


# ----------------------------------------------------------------------------- proponer o solicitar
@xframe_options_sameorigin
def solicitar_view(request, slug):
    """La puerta de entrada del centro: un reto, un servicio, el uso de un área, una capacitación o una visita.

    Quien no inició sesión ve la ruta y el enlace para entrar; quien la envía ve después el estado de cada solicitud.
    Quien gestiona el centro las atiende en su panel dinámico, donde avanzan por la ruta y se les confirma el horario.
    """
    from apps.centros_id.formularios import SolicitudForm

    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    contexto = _base(request, centro, c, 'solicitar')
    contexto.update({'ruta': RUTA_SERVICIO, 'etapas': c.ruta, 'mostrar_recursos': c.tiene('recursos')})
    from apps.centros_id.models import SolicitudCentro
    servicios = [s for s in c.servicios if s.solicitable]
    uso_habilitado = any(z.apto_reserva for z in c.zonas) or any(
        e.apto_reserva for area in c.areas for e in area.equipos.all())
    tipos = [(clave, titulo) for clave, titulo in SolicitudCentro.TIPOS
             if (clave != 'servicio' or servicios) and (clave != 'uso' or uso_habilitado)]
    inicial = {'tipo': request.GET.get('tipo', 'servicio' if servicios else 'reto'), 'titulo': request.GET.get('titulo', '')[:160],
               'finalidad': request.GET.get('finalidad', '')}
    if request.method == 'GET' and inicial['tipo'] not in dict(SolicitudCentro.TIPOS):
        raise Http404
    referencias = []
    if request.GET.get('servicio'):
        servicio = next((s for s in servicios if str(s.pk) == request.GET['servicio']), None)
        if servicio is None:
            raise Http404
        inicial['servicio'] = servicio.pk
        referencias.append(servicio.nombre)
    for campo in ('proyecto', 'desarrollo'):
        pedido = request.GET.get(campo, '')
        if pedido:
            if not pedido.isascii() or not pedido.isdigit() or len(pedido) > 18:
                raise Http404
            consulta = (c.consulta_proyectos if campo == 'proyecto' else
                        centro.resultados.filter(publicado=True, confidencial=False, **filtro_contenido(centro)))
            objeto = get_object_or_404(consulta, pk=int(pedido))
            inicial[campo] = objeto.pk
            referencias.append(objeto.titulo)
    from .parametros import identificador
    equipo_id = identificador(request.GET.get('equipo', ''))
    zona_id = identificador(request.GET.get('zona', ''))
    if equipo_id is not None:
        from apps.centros_id.models import EquipoCentro
        equipo = get_object_or_404(EquipoCentro, pk=equipo_id, componente__centro=centro,
                                   componente__publicado=True, reservable=True, es_activo_individual=True)
        if not equipo.apto_reserva:
            raise Http404
        inicial['equipo'] = equipo.pk
        referencias.append(equipo.nombre)
    if zona_id is not None:
        zona = get_object_or_404(centro.zonas, pk=zona_id, reservable=True)
        if not zona.apto_reserva:
            raise Http404
        inicial['zona'] = zona.pk
        referencias.append(zona.nombre)
    contexto['referencias'] = referencias
    contexto['tipos_solicitud'] = tipos
    contexto['tipo_seleccionado'] = request.POST.get('tipo', inicial['tipo'])
    contexto['sin_oferta'] = contexto['tipo_seleccionado'] in ('servicio', 'uso') and contexto['tipo_seleccionado'] not in dict(tipos)
    destino = reverse('solicitar_centro_id', args=[slug])
    parametros = {k: v for k, v in request.GET.items() if k in
                  ('tipo', 'titulo', 'finalidad', 'proyecto', 'desarrollo', 'servicio', 'componente', 'area', 'equipo', 'zona')}
    destino += '?' + urlencode(parametros) if parametros else ''
    entrar = reverse('login') + '?' + urlencode({'next': destino})
    if not request.user.is_authenticated:
        if request.method == 'POST':
            return redirect(entrar)
        contexto['entrar_url'] = entrar
        return render(request, 'centros_id/visor/solicitar.html', contexto)
    if request.GET.get('componente') or request.GET.get('area'):
        componente = centro.componentes.filter(codigo=request.GET.get('componente') or request.GET.get('area')).first()
        if componente:
            inicial['componente'] = componente.pk
    formulario = None if contexto['sin_oferta'] else SolicitudForm(request.POST or None, centro=centro, initial=inicial)
    if request.method == 'POST' and formulario is not None and formulario.is_valid():
        solicitud = formulario.save(commit=False)
        solicitud.centro = centro
        solicitud.usuario = identidad_de(request.user)
        solicitud.save(actor=request.user)
        messages.success(request, f'Recibimos la solicitud {solicitud.referencia}. El centro la evaluará y te responderá por aquí.')
        return HttpResponseRedirect(f"{reverse('solicitar_centro_id', args=[slug])}#mis-solicitudes")
    from .paginacion import paginar
    paginacion_solicitudes = paginar(centro.solicitudes.filter(usuario_id=request.user.pk)
        .select_related('centro', 'servicio', 'componente', 'zona', 'equipo', 'proyecto', 'desarrollo')
        .order_by('-creada', '-pk'), request, parametro='pagina_solicitudes', fragmento='#mis-solicitudes')
    contexto.update({
        'formulario': formulario,
        'mis_solicitudes': paginacion_solicitudes['pagina'], 'paginacion_solicitudes': paginacion_solicitudes,
    })
    return render(request, 'centros_id/visor/solicitar.html', contexto)


# ----------------------------------------------------------------------------- la página de un área
def _partes(texto):
    """«Corte láser, CNC, resinas y polvo» se lee como Corte láser · CNC · Resinas · Polvo."""
    partes = [parte.strip() for parte in re.split(r',|;| y | e ', texto or '') if parte.strip()]
    return [parte[:1].upper() + parte[1:] for parte in partes]


def _seguridad(area):
    """Los riesgos que atiende un área y los controles que exige, en partes para leerlos y revisarlos uno a uno."""
    riesgos, controles = area.control
    return {'riesgos': _partes(riesgos), 'controles': _partes(controles)} if riesgos or controles else None


@xframe_options_sameorigin
def area_view(request, slug, codigo):
    """La página de un área, con la pieza de Laboratorios: qué hace, cómo trabaja, sus fotos y videos, sus equipos con
    ficha técnica, qué investiga, qué presta, con quién se relaciona, quiénes trabajan en ella, dónde está y su
    seguridad."""
    from apps.centros_id.models import Componente
    from apps.centros_id.vinculos import unidad_publica, unidades_de

    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    area = get_object_or_404(Componente, centro=centro, codigo=codigo, publicado=True)
    imagenes = list(area.imagenes.all())
    fotos = [i for i in imagenes if not i.es_plano]
    procesos = list(area.procesos.filter(publicado=True).prefetch_related('pasos__equipos'))
    equipos = list(area.equipos.filter(**filtro_contenido(centro)).prefetch_related('pasos__proceso'))
    zonas = [z for z in c.zonas if z.componente_id == area.pk]
    proyectos_area = [p for p in c.proyectos if area in p.componentes.all()]
    ids_proyectos = {p.pk for p in proyectos_area}
    ids_lineas = {p.linea_id for p in proyectos_area if p.linea_id}
    contexto = _base(request, centro, c, 'areas')
    contexto.update({
        'area': area, 'portada': fotos[0] if fotos else None, 'franja': fotos[1] if len(fotos) > 1 else None,
        'integrado_en': next((a for a in c.areas if a.pk == area.integrado_en_id), None),
        'modulos_integrados': c.modulos_de(area),
        'galeria': fotos + [i for i in imagenes if i.es_plano],
        'procesos': procesos, 'flujo': area.pasos if not procesos else [],
        'equipos': equipos, 'total_equipos': len(equipos), 'software': area.lista_software,
        'lineas': [linea for linea in c.lineas if linea.componente_id == area.pk or linea.pk in ids_lineas],
        'proyectos': proyectos_area,
        'resultados': [r for r in c.resultados if r.componente_id == area.pk or r.proyecto_id in ids_proyectos],
        'servicios': [s for s in area.servicios.all() if s.activo],
        'entrega': [r for r in c.relaciones if r.origen_id == area.pk],
        'recibe': [r for r in c.relaciones if r.destino_id == area.pk],
        'unidades': unidades_de(area.lista_unidades),
        'personas': [p for p in c.integrantes if p.componente_id == area.pk and (p.rol in c._publicos() or c.gestor)],
        'zonas': zonas, 'plano': next((p for p in c.planos for z in zonas if z.nivel == p.nivel and z.en_plano), None),
        'videos': area.lista_videos, 'otras': [a for a in c.areas if a.pk != area.pk],
        'seguridad': _seguridad(area), 'protocolo': next(iter(c.documentos_de('seguridad')), None),
        'seccion': {**contexto['seccion'], 'titulo': area.nombre_corto or area.nombre},
        'completar': url_edicion(centro, 'componente', area.pk) if c.gestor else '',
        'unidad_propia': unidad_publica(area.unidad_slug) if area.unidad_slug else None,
    })
    return render(request, 'centros_id/visor/area.html', contexto)


# ----------------------------------------------------------------------------- carpetas propias y fragmentos
@xframe_options_sameorigin
def carpeta_view(request, slug, pk):
    from apps.centros_id.models import CarpetaCentro

    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    carpeta = get_object_or_404(CarpetaCentro, centro=centro, pk=pk, activa=True)
    if carpeta.visibilidad != 'publica' and not c.gestor:
        raise Http404
    recursos = [r for r in carpeta.recursos.all() if r.activo]
    from .parametros import identificador
    recurso = identificador(request.GET.get('recurso', ''))
    contexto = {'centro': centro, 'c': c, 'gestor': c.gestor, 'generado_en': timezone.localtime(), 'carpeta': carpeta,
                'videos': [{'id': r.video_id, 'titulo': r.titulo, 'canal': '', 'descripcion': r.descripcion}
                           for r in recursos if r.tipo == 'video' and r.video_id],
                'textos': [r for r in recursos if r.tipo == 'texto'],
                'archivos': [r for r in recursos if r.tipo in ('archivo', 'enlace')],
                'abrir': recurso,
                'pestana': MAPA.pestanas.get(carpeta.pestana, MAPA.pestanas['el-centro']),
                'seccion': {'titulo': carpeta.nombre, 'clave': f'carpeta-{carpeta.pk}'},
                'ficha_url': reverse('centro_id', args=[centro.slug]),
                'completar': url_edicion(centro, 'carpetacentro', carpeta.pk) if c.gestor else ''}
    return render(request, 'centros_id/visor/carpeta.html', contexto)


FRAGMENTOS = {
    'linea': ('LineaInvestigacion', {'centro': None}),
    'equipo': ('EquipoCentro', {'componente__centro': None, 'componente__publicado': True}),
    'proyecto': ('Proyecto', {'centro': None, 'publicado': True}),
    'persona': ('Integrante', {'centro': None, 'vigente': True}),
    'grupo': ('Grupo', {'centro': None, 'activo': True}),
    'caso': ('CasoExito', {'centro': None, 'publicado': True}),
    'resultado': ('Resultado', {'centro': None, 'publicado': True, 'confidencial': False}),
    'aliado': ('Aliado', {'centro': None, 'activo': True}),
    'proceso': ('ProcesoArea', {'componente__centro': None, 'publicado': True}),
    'servicio': ('Servicio', {'centro': None, 'activo': True}),
}


@xframe_options_sameorigin
def fragmento_view(request, slug, tipo, pk):
    """La ficha de un elemento, sin página alrededor: la abre un modal dentro del visualizador. Tesistas y estudiantes
    se nombran solo a quien gestiona el centro; al público se le cuentan."""
    from apps.centros_id import models

    if tipo not in FRAGMENTOS:
        raise Http404
    centro = _centro(slug)
    nombre, filtros = FRAGMENTOS[tipo]
    filtros = {campo: (centro if valor is None else valor) for campo, valor in filtros.items()}
    modelo = getattr(models, nombre)
    if issubclass(modelo, models.ContenidoCentro):
        filtros.update(filtro_contenido(centro))
    objeto = get_object_or_404(modelo, pk=pk, **filtros)
    from apps.centros_id.contenidos import ocultar_referencias_muestra
    ocultar_referencias_muestra(objeto)
    gestor = centro.puede_gestionar(request.user)
    if tipo == 'caso' and not objeto.transferencia_documentada:
        raise Http404

    def nombrables(personas):
        return [p for p in personas if p.centro_id == centro.pk and p.vigente and contenido_admitido(p)
                and (p.rol in models.Integrante.PUBLICOS or gestor)]

    if tipo == 'persona' and not nombrables([objeto]):
        raise Http404
    contexto = {'centro': centro, 'objeto': objeto, tipo: objeto, 'niveles_trl': range(1, 10),
                'ficha_url': reverse('centro_id', args=[centro.slug]),
                'solicitar_url': reverse('seccion_centro_id', args=[centro.slug, 'solicitar'])}
    if tipo == 'linea':
        c = _contenidos(centro, request.user)
        contexto.update(proyectos=[p for p in c.proyectos if p.linea_id == objeto.pk],
                        resultados=[r for r in c.resultados if r.proyecto and r.proyecto.linea_id == objeto.pk],
                        produccion=[r for r in c.produccion if r.proyecto and r.proyecto.linea_id == objeto.pk],
                        desarrollos=[r for r in c.desarrollos if r.proyecto and r.proyecto.linea_id == objeto.pk],
                        grupos=[g for g in c.grupos if objeto in g.lineas.all()],
                        integrantes=nombrables([p for p in c.integrantes if objeto in p.lineas.all()]))
    if tipo == 'servicio':
        contexto['ruta'] = RUTA_SERVICIO
    if tipo == 'proyecto':
        equipo = list(objeto.equipo.filter(**filtro_contenido(centro)))
        contexto['aliados'] = objeto.aliados.filter(activo=True, **filtro_contenido(centro))
        contexto['equipo'] = nombrables(equipo)
        contexto['en_formacion'] = len(equipo) - len(contexto['equipo'])
        contexto['resultados'] = [r for r in objeto.resultados.filter(publicado=True, confidencial=False, **filtro_contenido(centro))]
        contexto['hitos'] = objeto.hitos_registrados.filter(publico=True)
        contexto['etapas'] = [(clave, nombre_etapa, clave in objeto.etapas_recorridas) for clave, nombre_etapa in objeto.ETAPAS]
    if tipo == 'persona':
        contexto['proyectos'] = list(objeto.proyectos.filter(publicado=True, **filtro_contenido(centro))) + list(objeto.proyectos_dirigidos.filter(publicado=True, **filtro_contenido(centro)))
        contexto['resultados'] = list(objeto.resultados.filter(publicado=True, confidencial=False, **filtro_contenido(centro)))
    if tipo == 'grupo':
        contexto['integrantes'] = nombrables(objeto.integrantes.filter(vigente=True))
    if tipo == 'aliado':
        contexto['proyectos'] = objeto.proyectos.filter(publicado=True, **filtro_contenido(centro))
        contexto['casos'] = [caso for caso in objeto.casos.filter(publicado=True, **filtro_contenido(centro)) if caso.transferencia_documentada]
    if tipo == 'resultado':
        contexto['autores'] = nombrables(objeto.autores.all())
    if tipo == 'equipo':
        prefetch_related_objects([objeto], 'pasos__proceso')
    return render(request, f'centros_id/visor/fragmentos/{tipo}.html', contexto)


def exportar_resultados_view(request, slug):
    from django.http import HttpResponse, JsonResponse
    from apps.centros_id.investigacion import metadatos, referencias_ris
    from apps.centros_id import selectors_cientificos as consultas
    from apps.centros_id.contenidos import ocultar_referencias_muestra

    centro = _centro(slug)
    c = _contenidos(centro, None)
    catalogo = request.GET.get('catalogo', 'produccion')
    if catalogo not in ('produccion', 'desarrollos') or not c.tiene(catalogo):
        raise Http404
    ajuste = c.ajustes.get(catalogo)
    if ajuste and ajuste.oculta:
        raise Http404
    universo = c.consulta_resultados(catalogo)
    filtro = consultas.filtros(request.GET, ('tipo', 'anio', 'linea', 'proyecto', 'sector', 'tecnologia', 'trl', 'q'))
    consulta = consultas.filtrar_resultados(universo, filtro, centro).select_related('proyecto__linea', 'componente')\
        .prefetch_related('autores').order_by('-anio', 'titulo', 'pk')
    filas = [ocultar_referencias_muestra(r) for r in consulta]
    formato = request.GET.get('formato', 'json')
    if formato == 'ris':
        respuesta = HttpResponse(referencias_ris(filas), content_type='application/x-research-info-systems; charset=utf-8')
    elif formato == 'json':
        respuesta = JsonResponse({'centro': centro.slug, 'fecha_consulta': c.hoy.isoformat(),
                                  'total': len(filas), 'resultados': [metadatos(r) for r in filas]},
                                 json_dumps_params={'ensure_ascii': False})
    else:
        raise Http404
    respuesta['Content-Disposition'] = f'attachment; filename="{centro.slug}-{catalogo}.{formato}"'
    return respuesta


@xframe_options_sameorigin
def simulador_view(request, slug):
    from apps.centros_id.simulacion import CapacidadForm, calcular_capacidad

    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    ajuste = c.ajustes.get('recursos')
    if not c.escenario or centro.slug != 'cidt-upec' or (ajuste and ajuste.oculta):
        raise Http404
    contexto = _base(request, centro, c, 'recursos')
    inicial = {nombre: campo.initial for nombre, campo in CapacidadForm.base_fields.items()}
    formulario = CapacidadForm(request.GET if request.GET else inicial)
    resultado = calcular_capacidad(formulario.cleaned_data) if formulario.is_valid() else None
    contexto.update(formulario=formulario, resultado=resultado,
        recursos_url=reverse('seccion_centro_id', args=[centro.slug, 'recursos']))
    return render(request, 'centros_id/visor/simulador.html', contexto)
