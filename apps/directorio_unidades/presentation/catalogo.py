"""Catálogo público de Laboratorios y Unidades Experimentales."""

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from apps.core.presentation.tipologias import idioma_actual, tipologias_publicas
from apps.core.presentation.tipologias import tipologia as tipologia_por_codigo
from apps.directorio_unidades.contracts import TipoUnidad
from apps.directorio_unidades.models.core import Categoria, TipoLaboratorio, Unidad
from apps.recursos.models.equipos import EquiposServicios
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.plantas_piloto.operacion.models.produccion import FamiliaProducto, Producto, Receta
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.core.presentation.text import normalizar_texto


ORDENAMIENTOS = {
    'visitadas': ('-visitas', 'nombre'),
    'recientes': ('-id',),
    'nombre': ('nombre',),
}
ORDEN_EXPLICADO = {
    'visitadas': 'ordenadas por visitas: las más consultadas van primero (una visita por persona y sesión; '
                 'no cuentan las de quien gestiona la unidad)',
    'recientes': 'ordenadas por fecha de registro: las más nuevas van primero',
    'nombre': 'ordenadas alfabéticamente por nombre',
}


def _paginacion_visible(paginator, pagina_actual):
    paginas = {1, paginator.num_pages, pagina_actual}
    paginas.update(
        numero
        for numero in range(pagina_actual - 2, pagina_actual + 3)
        if 1 <= numero <= paginator.num_pages
    )
    elementos = []
    anterior = None
    for numero in sorted(paginas):
        if anterior is not None and numero - anterior > 1:
            elementos.append(anterior + 1 if numero - anterior == 2 else None)
        elementos.append(numero)
        anterior = numero
    return elementos


def _texto_busqueda(unidad):
    valores = [unidad.nombre, unidad.descripcion, unidad.descripcion_corta]
    if unidad.dependencia == 'plantas_piloto':
        valores.extend(item.nombre for item in unidad.productos_busqueda)
        valores.extend(item.nombre for item in unidad.procesos_busqueda)
        valores.extend(item.equipo.nombre for item in unidad.equipos_busqueda)
    return normalizar_texto(' '.join(valor or '' for valor in valores))


def _preparar_tarjeta_planta(unidad):
    nombre = unidad.nombre
    for prefijo in ('Planta Piloto de ', 'Planta Piloto del ', 'Planta Piloto '):
        if nombre.startswith(prefijo):
            nombre = nombre.removeprefix(prefijo)
            break
    unidad.catalogo_etiqueta = nombre

    responsables = unidad.responsables_catalogo
    coordinacion = next(
        (item for item in responsables if item.rol == 'coordinacion'),
        responsables[0] if responsables else None,
    )
    unidad.catalogo_responsable = (
        coordinacion.nombre_publico if coordinacion else 'Coordinación de la planta'
    )

    familias = sorted(
        unidad.familias_catalogo,
        key=lambda item: (-(item.total_productos + item.total_procesos), item.orden),
    )
    unidad.catalogo_familias_principales = familias[:3]
    unidad.catalogo_en_construccion = not any((
        unidad.total_productos_catalogo,
        unidad.total_procesos_catalogo,
        unidad.total_equipos_catalogo,
    ))


def _clasificaciones_ofrecidas(modelo, dependencia):
    """Solo clasificaciones activas, ofrecidas a la tipologia y en uso en ella."""
    return modelo.objects.filter(
        Q(tipologias=[]) | Q(tipologias__contains=[dependencia]),
        activa=True,
        unidades__dependencia=dependencia,
    ).distinct()


def _codigo_seleccionado(modelo, valor):
    """Normaliza un filtro recibido por nombre historico a su codigo estable."""
    if not valor:
        return valor
    codigo = modelo.objects.filter(Q(codigo=valor) | Q(nombre=valor)).values_list('codigo', flat=True).first()
    return codigo or valor


def _url_catalogo(tipologia):
    """Las implementadas conservan su ruta historica; el resto usa la generica."""
    codigos_base = {tipo.value for tipo in TipoUnidad}
    if tipologia.codigo in codigos_base:
        return reverse(TipoUnidad(tipologia.codigo).ruta_catalogo)
    return reverse('catalogo_tipologia', kwargs={'tipologia': tipologia.codigo})


def _pestanas_catalogo(dependencia, conteos):
    idioma = idioma_actual()
    return [
        {
            'codigo': tipologia.codigo,
            'nombre': tipologia.etiqueta(idioma, plural=True),
            'icono': tipologia.icono,
            'url': _url_catalogo(tipologia),
            'conteo': conteos.get(tipologia.codigo, 0),
            'activa': tipologia.codigo == dependencia,
        }
        for tipologia in tipologias_publicas()
    ]


def catalogo_unidades(request, dependencia, seccion_activa, catalogo_titulo):
    """Construye el catálogo filtrado de un tipo de unidad."""
    tipologia = tipologia_por_codigo(dependencia)
    if tipologia is None or not tipologia.activa:
        # La desactivacion institucional se aplica en el servidor, no solo en
        # el menu: la ruta historica deja de responder mientras dure.
        raise Http404
    es_catalogo_plantas = tipologia.base == 'plantas_piloto'
    area_conocimiento = request.GET.get('area_conocimiento') or request.GET.get('tipo_proyecto')
    categoria = request.GET.get('categoria')
    tipo_laboratorio = request.GET.get('tipo_laboratorio')
    modo_operacion = request.GET.get('modo_operacion')
    familia_producto = request.GET.get('familia_producto')
    tecnologia = request.GET.get('tecnologia')
    servicio = request.GET.get('servicio')
    disponibilidad = request.GET.get('disponibilidad')
    busqueda = request.GET.get('busqueda', '').strip()

    # Una unidad desactivada sale del portal: el catálogo solo muestra las activas.
    unidades = Unidad.objects.filter(dependencia=dependencia, activo=True)
    if area_conocimiento:
        unidades = unidades.filter(area_conocimiento=area_conocimiento)
    # Los filtros publicos usan el codigo estable; el nombre sigue aceptandose
    # para no romper enlaces publicados antes del catalogo administrable.
    if categoria:
        unidades = unidades.filter(
            Q(categorias__codigo=categoria) | Q(categorias__nombre=categoria)
        )
    if tipo_laboratorio:
        unidades = unidades.filter(
            Q(tipos_laboratorio__codigo=tipo_laboratorio) | Q(tipos_laboratorio__nombre=tipo_laboratorio)
        )
    if es_catalogo_plantas:
        if modo_operacion:
            unidades = unidades.filter(modo_operacion=modo_operacion)
        if familia_producto:
            unidades = unidades.filter(
                familias_producto__codigo=familia_producto,
                familias_producto__activa=True,
            )
        if tecnologia:
            unidades = unidades.filter(
                unidades_equipo_principal__activa=True,
                unidades_equipo_principal__equipo__familia_tecnologica=tecnologia,
            )
        if servicio:
            unidades = unidades.filter(
                servicios_operativos__activo=True,
                servicios_operativos__publico=True,
                servicios_operativos__tipo_servicio=servicio,
            )
        if disponibilidad:
            unidades = unidades.filter(estado_catalogo=disponibilidad)

    no_results = False
    if busqueda:
        termino = normalizar_texto(busqueda)
        ids = [
            unidad.id
            for unidad in unidades.prefetch_related(
                Prefetch(
                    'productos',
                    queryset=Producto.objects.filter(activo=True, publico=True).only('nombre'),
                    to_attr='productos_busqueda',
                ),
                Prefetch(
                    'recetas',
                    queryset=Receta.objects.filter(activa=True).only('nombre'),
                    to_attr='procesos_busqueda',
                ),
                Prefetch(
                    'unidades_equipo_principal',
                    queryset=UnidadEquipo.objects.filter(activa=True).select_related('equipo'),
                    to_attr='equipos_busqueda',
                ),
            )
            if termino in _texto_busqueda(unidad)
        ]
        unidades = unidades.filter(id__in=ids)
        no_results = not ids

    orden = request.GET.get('orden', 'visitadas')
    if orden not in ORDENAMIENTOS:
        orden = 'visitadas'

    unidades = unidades.select_related('administrador').prefetch_related(
        'categorias', 'tipos_laboratorio'
    )
    if es_catalogo_plantas:
        unidades = unidades.annotate(
            total_productos_catalogo=Count(
                'productos',
                filter=Q(productos__activo=True, productos__publico=True),
                distinct=True,
            ),
            total_procesos_catalogo=Count(
                'recetas', filter=Q(recetas__activa=True), distinct=True,
            ),
            total_equipos_catalogo=Count(
                'unidades_equipo_principal',
                filter=Q(unidades_equipo_principal__activa=True),
                distinct=True,
            ),
        ).prefetch_related(
            Prefetch(
                'responsables_unidad',
                queryset=ResponsableUnidad.objects.filter(activo=True, publico=True),
                to_attr='responsables_catalogo',
            ),
            Prefetch(
                'familias_producto',
                queryset=FamiliaProducto.objects.filter(activa=True).annotate(
                    total_productos=Count(
                        'productos',
                        filter=Q(productos__activo=True, productos__publico=True),
                        distinct=True,
                    ),
                    total_procesos=Count(
                        'recetas', filter=Q(recetas__activa=True), distinct=True,
                    ),
                ),
                to_attr='familias_catalogo',
            ),
        )
    unidades = unidades.order_by(*ORDENAMIENTOS[orden]).distinct()

    opciones_tamano = (8, 12, 20)
    try:
        tamano = int(request.GET.get('page_size', 8))
    except (TypeError, ValueError):
        tamano = 8
    tamano = min(max(tamano, 1), 100)

    paginator = Paginator(unidades, tamano)
    pagina = paginator.get_page(request.GET.get('page', 1))
    for unidad in pagina.object_list:
        # Todas comparten la tipologia consultada; evita una lectura por tarjeta.
        unidad._tipologia_cache = (dependencia, tipologia)
        if es_catalogo_plantas:
            _preparar_tarjeta_planta(unidad)

    conteos = {
        item['dependencia']: item['total']
        for item in Unidad.objects.values('dependencia').annotate(total=Count('id'))
    }
    parametros = request.GET.copy()
    parametros.pop('page', None)

    contexto = {
        'unidades': pagina.object_list,
        'page_obj': pagina,
        'paginator': paginator,
        'page_size': tamano,
        'page_size_options': opciones_tamano,
        'pagination_items': _paginacion_visible(paginator, pagina.number),
        'areas_conocimiento': Unidad.AREA_CONOCIMIENTO_CHOICES,
        'categorias': _clasificaciones_ofrecidas(Categoria, dependencia),
        'tipos_laboratorio': _clasificaciones_ofrecidas(TipoLaboratorio, dependencia),
        'area_conocimiento_seleccionada': area_conocimiento,
        'categoria_seleccionada': _codigo_seleccionado(Categoria, categoria),
        'tipo_laboratorio_seleccionado': _codigo_seleccionado(TipoLaboratorio, tipo_laboratorio),
        'modo_operacion_seleccionado': modo_operacion,
        'familia_producto_seleccionada': familia_producto,
        'tecnologia_seleccionada': tecnologia,
        'servicio_seleccionado': servicio,
        'disponibilidad_seleccionada': disponibilidad,
        'familias_producto': FamiliaProducto.objects.filter(
            unidad__dependencia=dependencia, activa=True,
        ).select_related('unidad').order_by('unidad__nombre', 'orden'),
        'tecnologias': EquiposServicios.FAMILIA_TECNOLOGICA_CHOICES,
        'servicios_planta': FablabService.TIPOS_CATALOGO_PLANTA,
        'disponibilidades': Unidad.ESTADO_CATALOGO_CHOICES,
        'modos_operacion': Unidad.MODO_OPERACION_CHOICES,
        'es_catalogo_plantas': es_catalogo_plantas,
        'busqueda': busqueda,
        'no_results': no_results,
        'seccion_activa': seccion_activa,
        'catalogo_titulo': catalogo_titulo,
        'dependencia_activa': dependencia,
        'orden': orden,
        'orden_descripcion': ORDEN_EXPLICADO[orden],
        'pestanas_catalogo': _pestanas_catalogo(dependencia, conteos),
        'pagination_query': parametros.urlencode(),
        'page_key': 'laboratorios',
        'page_title': 'Laboratorios y Unidades Experimentales',
    }
    response = render(request, 'portal/pages/unidades/catalogo_unidades.html', contexto)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
