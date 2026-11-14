"""Las páginas de los Centros I+D: la portada de todos los centros, la ficha de cada uno (pestañas, visualizador y panel
de contenidos), la portada de cada pestaña dentro del visualizador y el reporte en PDF.

Las secciones que se abren en el visualizador viven en `secciones.py`. Los modelos se importan dentro de cada vista:
las rutas del contexto se cargan sin configurar Django."""

from urllib.parse import urlencode

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView

from apps.centros_id.gestion_catalogo import url_edicion
from apps.centros_id.mapa import MAPA, PORTADAS, SUBPAGINAS


def _centros_activos():
    from apps.centros_id.models import CentroID

    return CentroID.objects.filter(activo=True)


def _centro(slug):
    from apps.centros_id.models import CentroID

    return get_object_or_404(CentroID, slug=slug, activo=True)


def _contenidos(centro, usuario):
    from apps.centros_id.contenidos import Contenidos

    return Contenidos(centro, usuario)


def _portada_de(centro):
    """La foto de portada del centro: la suya o la primera imagen general que no sea un plano."""
    if centro.imagen:
        return centro.imagen.url
    if 'imagenes' in getattr(centro, '_prefetched_objects_cache', {}):
        imagen = next((i for i in centro.imagenes.all() if i.componente_id is None and not i.es_plano), None)
    else:
        imagen = centro.imagenes.filter(componente__isnull=True, es_plano=False).first()
    return imagen.imagen.url if imagen else ''


def portada_de_area(area):
    imagen = next((i for i in area.imagenes.all() if not i.es_plano), None)
    return imagen.imagen.url if imagen else ''


class CentrosIDView(TemplateView):
    """Catálogo de centros con información comparable y acceso a sus fichas."""
    template_name = "centros_id/portada.html"
    page_key = "centros"
    page_title = "Centros I+D"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Prefetch
        from apps.centros_id.models import Componente, Servicio

        # La portada necesita resúmenes, no proyectos, equipos ni resultados de
        # cada centro. Siete consultas de conjuntos, independientemente del
        # número de tarjetas, sin cargar hijos de las áreas.
        consulta = _centros_activos().select_related('responsable').prefetch_related(
            'lineas', 'imagenes', 'articulaciones', 'fases',
            Prefetch('componentes', queryset=Componente.objects.filter(publicado=True), to_attr='areas_catalogo'),
            Prefetch('servicios', queryset=Servicio.objects.filter(activo=True), to_attr='servicios_catalogo'))
        todos = list(consulta)
        centros = todos
        contenidos = {centro.pk: _contenidos(centro, None) for centro in todos}
        for centro in todos:
            c = contenidos[centro.pk]
            c.areas = centro.areas_catalogo
            c.servicios = centro.servicios_catalogo
            c.lineas = list(centro.lineas.all())
            c.articulaciones = list(centro.articulaciones.all())
            c.fases = list(centro.fases.all())
            centro.contenidos = c
            centro.cifras_tarjeta = c.cifras_capacidades()
            centro.lineas_tarjeta = [linea.nombre for linea in c.lineas][:4]
            centro.areas_tarjeta = c.areas
            centro.portada = _portada_de(centro)
            centro.carreras_tarjeta = [a.actor for a in c.articulaciones if a.tipo == 'carrera']
            centro.otras_carreras = max(0, len(centro.carreras_tarjeta) - 3)
            centro.fase_actual = c.fase_actual
        context.update(
            page_key=self.page_key, page_title=self.page_title,
            centros=centros, todos=todos,
            cifras=self._cifras(contenidos.values()),
            diapositivas=self._diapositivas(todos),
        )
        return context

    @staticmethod
    def _cifras(contenidos):
        """El mismo alcance de las tarjetas; las unidades compartidas se cuentan una vez."""
        contenidos = list(contenidos)
        if not contenidos:
            return []
        suma = {}
        for c in contenidos:
            for cifra in c.cifras_capacidades():
                actual = suma.setdefault(cifra['clave'], {**cifra, 'valor': 0})
                actual['valor'] += cifra['valor']
        suma['vinculadas']['valor'] = len({slug for c in contenidos for slug in c.unidades_vinculadas})
        suma['areas']['titulo'] = 'Áreas de los centros'
        total = len(contenidos)
        return [{'clave': 'centros', 'valor': total, 'titulo': 'Centro I+D' if total == 1 else 'Centros I+D',
                 'icono': 'fas fa-landmark'}, *suma.values()]

    @staticmethod
    def _diapositivas(centros, por_centro=3, maximo=10):
        """Las fotos que pasan por la franja de la portada: la portada de cada centro y hasta dos imágenes generales más
        (sin planos), en ronda para que con muchos centros se vean todos; cada una lleva su centro y su texto."""
        por_cada = []
        for centro in centros:
            fotos = [(centro.imagen.url, centro.lema)] if centro.imagen else []
            for imagen in centro.imagenes.all():
                if imagen.componente_id is None and not imagen.es_plano and imagen.imagen.url not in [f[0] for f in fotos]:
                    fotos.append((imagen.imagen.url, imagen.titulo))
            por_cada.append([{'centro': centro, 'url': url, 'texto': texto} for url, texto in fotos[:por_centro]])
        ronda = [fotos[i] for i in range(por_centro) for fotos in por_cada if len(fotos) > i]
        return ronda[:maximo]



def _inicial(request, centro, carpetas):
    """Lo que el visualizador abre al entrar: una sección, un área o una pestaña pedidas en la dirección; si no, la
    presentación del centro."""
    pedido = request.GET
    slug = centro.slug
    seccion = pedido.get('seccion', '')

    def con_extras(url, *nombres):
        # Los filtros y lo que se abre viajan con la página (?seccion=portafolio&linea=IA&abrir=12).
        extra = {k: v for k, v in pedido.items() if k in nombres}
        return f'{url}?{urlencode(extra)}' if extra else url

    for clave_pestana, lista in carpetas.items():
        carpeta = next((c for c in lista if c['clave'] == seccion), None)
        if carpeta is None:
            continue
        url = con_extras(carpeta['url'], 'abrir', 'linea', 'tipo', 'estado', 'q', 'area', 'sector', 'categoria', 'recurso')
        return {'pestana': clave_pestana, 'url': url, 'titulo': carpeta['titulo']}
    if seccion in SUBPAGINAS:
        # Las páginas que cuelgan de una sección (identidad y ubicación) se abren en la pestaña de su sección.
        return {'pestana': MAPA.pestana_de(SUBPAGINAS[seccion]['padre']),
                'url': reverse('seccion_centro_id', args=[slug, seccion]), 'titulo': SUBPAGINAS[seccion]['titulo']}
    if pedido.get('area'):
        area = centro.componentes.filter(codigo=pedido['area'], publicado=True).first()
        if area:
            return {'pestana': MAPA.pestana_de('areas'), 'titulo': area.nombre_corto or area.nombre,
                    'url': reverse('componente_centro_id', args=[slug, area.codigo])}
    pestana = pedido.get('pestana', '')
    if pestana in MAPA.pestanas:
        return {'pestana': pestana, 'url': reverse('pestana_centro_id', args=[slug, pestana]),
                'titulo': MAPA.pestanas[pestana]['titulo']}
    return {'pestana': 'el-centro', 'url': reverse('seccion_centro_id', args=[slug, 'presentacion']),
            'titulo': MAPA.seccion('presentacion')['titulo']}


def centro_view(request, slug):
    """La ficha del centro: cabecera compacta, seis pestañas, visualizador y panel de contenidos."""
    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    carpetas = c.carpetas()
    pestanas = []
    for clave, pestana in MAPA.pestanas.items():
        secciones = [carpeta for carpeta in carpetas[clave] if not carpeta['pendiente']]
        if secciones or c.gestor:
            pestanas.append({**pestana, 'total': len(secciones), 'carpetas': carpetas[clave],
                             'pendientes': sum(1 for carpeta in carpetas[clave] if carpeta['pendiente'])})
    return render(request, 'centros_id/ficha.html', {
        'page_key': 'centros', 'page_title': str(centro),
        'centro': centro, 'c': c, 'pestanas': pestanas,
        'portada': _portada_de(centro),
        'inicial': _inicial(request, centro, carpetas),
        'puede_gestionar': c.gestor,
        'fase_actual': c.fase_actual,
        'solicitudes_pendientes': centro.solicitudes.filter(estado__in=('recibida', 'evaluacion')).count() if c.gestor else 0,
    })


@xframe_options_sameorigin
def pestana_view(request, slug, pestana):
    """La portada de una pestaña dentro del visualizador, con el aire de las de Laboratorios: un escenario con las
    fotos de lo que contiene, su frase y su texto, sus cifras, «Qué vas a encontrar» con cada sección, de dónde salen
    los datos y cómo leerlos."""
    if pestana not in MAPA.pestanas:
        raise Http404
    centro = _centro(slug)
    c = _contenidos(centro, request.user)
    carpetas = c.carpetas(solo_pestana=pestana)[pestana]
    if not carpetas and not c.gestor:
        raise Http404
    modulos = [{'titulo': carpeta['titulo'], 'icono': carpeta['icono'], 'url': carpeta['url'], 'imagen': '',
                'detalle': carpeta['botones'][0]['detalle'] if carpeta['botones'] else carpeta['descripcion']}
               for carpeta in carpetas if not carpeta['pendiente']]
    if pestana == MAPA.pestana_de('areas'):
        # Las áreas son lo que la pestaña presenta primero: cada una con su foto y lo que tiene.
        modulos = [{'titulo': a.nombre_corto or a.nombre, 'icono': a.icono, 'imagen': portada_de_area(a),
                    'url': reverse('componente_centro_id', args=[centro.slug, a.codigo]),
                    'detalle': _lo_que_tiene(c, a) + (f' · Incluye: {", ".join(str(m) for m in integrados)}' if integrados else '')}
                   for a, integrados in c.estructura_areas] + modulos[1:]
    return render(request, 'centros_id/visor/pestana.html', {
        'centro': centro, 'c': c, 'pestana': MAPA.pestanas[pestana], 'portada': PORTADAS[pestana],
        'modulos': modulos, 'cifras': _cifras_de_pestana(c, pestana),
        'imagenes': _imagenes_de_pestana(centro, c, pestana),
        'seccion': {'titulo': MAPA.pestanas[pestana]['titulo'], 'clave': ''},
        'gestor': c.gestor, 'ficha_url': reverse('centro_id', args=[centro.slug]),
        'editar': url_edicion(centro) if c.gestor else '',
    })


def _lo_que_tiene(c, area):
    """«12 equipos · 7 servicios · 3 proyectos»: lo que tiene un área, solo lo que vale algo."""
    cuentas = ((len(area.equipos.all()), 'equipo', 'equipos'),
               (len([s for s in area.servicios.all() if s.activo]), 'servicio', 'servicios'),
               (sum(1 for p in c.proyectos if area in p.componentes.all()), 'proyecto', 'proyectos'))
    return ' · '.join(f'{total} {uno if total == 1 else varios}' for total, uno, varios in cuentas if total)


def _cifras_de_pestana(c, pestana):
    """Las cifras de la portada de cada pestaña, solo las que valen algo."""
    filas = {
        'el-centro': lambda: [(len(c.areas), 'Áreas del centro'), (len(c.ruta), 'Etapas de la ruta de atención'),
                      (len(c.gobierno), 'Instancias de gobierno'), (len(c.documentos), 'Documentos publicados')],
        'areas': lambda: [(len(c.areas), 'Áreas propias'), (sum(len(a.equipos.all()) for a in c.areas), 'Equipos con ficha'),
                  (len(c.servicios), 'Servicios que prestan'), (len(c.unidades_vinculadas), 'Capacidades vinculadas')],
        'investigacion': lambda: [(len(c.lineas), 'Líneas de investigación'), (len(c.proyectos_activos), 'Proyectos en curso'),
                          (len(c.proyectos), 'Proyectos en la cartera'), (len(c.produccion), 'Productos científicos')],
        'innovacion': lambda: [(len(c.desarrollos), 'Desarrollos'), (len(c.casos), 'Casos de transferencia'),
                       (len(c.aliados), 'Aliados')],
        'equipo': lambda: [(len([p for p in c.integrantes if p.rol in c._publicos()]), 'Integrantes'),
                   (len(c.investigadores), 'Investigadores'),
                   (len([a for a in c.articulaciones if a.tipo == 'carrera']), 'Carreras que participan'),
                   (len(c.por_rol('tesista', 'estudiante')), 'En formación')],
        'servicios': lambda: [(len(c.servicios), 'Servicios en el portafolio'),
                      (len({s.linea for s in c.servicios}), 'Líneas de servicio'),
                      (len(c.ruta), 'Etapas de atención'), (len(c.convocatorias), 'Oportunidades abiertas')],
    }
    filas = filas[pestana]() if pestana in filas else []
    return [{'total': total, 'nombre': nombre} for total, nombre in filas if total]


def _imagenes_de_pestana(centro, c, pestana, cuantas=6):
    """Las fotos del escenario: las de las áreas en su pestaña; en las demás, las del centro (nunca planos)."""
    if pestana == MAPA.pestana_de('areas'):
        urls = [portada_de_area(a) for a in c.areas]
    else:
        urls = [_portada_de(centro)] + [i.imagen.url for i in centro.imagenes.filter(componente__isnull=True, es_plano=False)]
    vistas = []
    for url in urls:
        if url and url not in vistas:
            vistas.append(url)
    return vistas[:cuantas]


def reporte_view(request, slug):
    """El reporte institucional del centro en PDF, armado en el momento con lo publicado."""
    from apps.centros_id.reportes import reporte_del_centro

    return reporte_del_centro(_centro(slug))
