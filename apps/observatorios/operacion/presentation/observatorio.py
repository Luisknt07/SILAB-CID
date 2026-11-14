"""Las páginas propias de un observatorio: indicadores, series, fichas, alertas, publicaciones, encuestas, aliados,
solicitudes de datos y datos abiertos.

Se abren en el visualizador de la ficha (secciones 2.x a 6.x del mapa de observatorios) y muestran solo lo
publicado. Los datos agregados son abiertos (CSV y JSON con licencia CC BY 4.0); las solicitudes de datos exigen
cuenta y cada persona solo ve las suyas, salvo quien gestiona el observatorio.
"""
import csv

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.observatorios.operacion.models.observatorios import numero_legible
from apps.observatorios.operacion.models.observatorios import AliadoObservatorio, DescargaDatos, IndicadorObservatorio, PoliticaDatosObservatorio, SolicitudDatos, ValorIndicador
from apps.directorio_unidades.models.core import Unidad

from apps.directorio_unidades.presentation.catalogos_publicos import _contexto
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

LICENCIA = ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/deed.es')
# Las publicaciones por sección del mapa: 4.1 boletines y 4.2 informes, perfiles y notas de política pública.
TIPOS_POR_SECCION = {'boletines': ('boletin',), 'informes': ('informe', 'perfil', 'nota_politica')}
TITULOS_PUBLICACION = {'boletines': 'Boletines', 'informes': 'Informes y notas de política pública'}


def _observatorio(slug):
    return get_object_or_404(Unidad, slug=slug, activo=True, dependencia='observatorios')


def indicadores_publicados(unidad):
    return unidad.indicadores_observatorio.filter(publicado=True).prefetch_related('valores')


_numero = numero_legible


def _puntos(valores, ancho=160, alto=40):
    """Los puntos de una línea SVG para una serie, escalados a la caja; vacío con menos de dos valores."""
    if len(valores) < 2:
        return ''
    numeros = [float(valor.valor) for valor in valores]
    minimo, maximo = min(numeros), max(numeros)
    rango = (maximo - minimo) or 1
    paso = ancho / (len(numeros) - 1)
    return ' '.join(f'{indice * paso:.1f},{alto - 4 - (numero - minimo) / rango * (alto - 8):.1f}'
                    for indice, numero in enumerate(numeros))


def resumen(indicador):
    """Lo que la tarjeta de un indicador muestra: último valor, cambio, tendencia, alerta y la línea de la serie."""
    serie = [valor for valor in indicador.valores.all() if valor.territorio == indicador.territorio_principal]
    serie.sort(key=lambda valor: valor.fecha)
    ultimo = serie[-1] if serie else None
    anterior = serie[-2] if len(serie) > 1 else None
    cambio = (ultimo.valor - anterior.valor) if ultimo and anterior else None
    direccion = '' if cambio is None else ('sube' if cambio > 0 else 'baja' if cambio < 0 else 'igual')
    favorable = None
    if direccion in ('sube', 'baja') and indicador.sentido in ('subir', 'bajar'):
        favorable = (direccion == 'sube') == (indicador.sentido == 'subir')
    return {
        'indicador': indicador,
        'ultimo': ultimo,
        'ultimo_texto': _numero(ultimo.valor) if ultimo else '—',
        'anterior': anterior,
        'cambio_texto': ('+' if cambio and cambio > 0 else '') + _numero(cambio) if cambio is not None else '',
        'direccion': direccion,
        'favorable': favorable,
        'alerta': indicador.alerta(ultimo, anterior) if ultimo else '',
        'puntos': _puntos(serie[-12:]),
        'total_valores': len(serie),
    }


def alertas_vigentes(unidad):
    return [fila for fila in map(resumen, indicadores_publicados(unidad)) if fila['alerta']]


@xframe_options_sameorigin
def indicadores_view(request, slug):
    """2.1 · Los indicadores clave con su último valor, su cambio y su tendencia."""
    from apps.observatorios.operacion.presentation.observatorio_lineas import agrupar_por_linea

    unidad = _observatorio(slug)
    filas = [resumen(indicador) for indicador in indicadores_publicados(unidad).select_related('linea')]
    return render(request, 'portal/pages/unidades/observatorio/indicadores.html', {
        **_contexto(unidad, 'indicadores', request.user),
        'filas': filas,
        'grupos': agrupar_por_linea(unidad, filas),
        'con_valor': sum(1 for fila in filas if fila['ultimo']),
        'alertas': sum(1 for fila in filas if fila['alerta']),
    })


@xframe_options_sameorigin
def indicador_view(request, slug, codigo):
    """La ficha de un indicador: su metodología, su serie completa por territorio y la descarga en CSV."""
    unidad = _observatorio(slug)
    indicador = get_object_or_404(IndicadorObservatorio, unidad=unidad, codigo=codigo, publicado=True)
    valores = list(indicador.valores.order_by('territorio', 'fecha'))
    territorios = []
    for valor in valores:
        if not territorios or territorios[-1]['nombre'] != valor.territorio:
            territorios.append({'nombre': valor.territorio, 'valores': []})
        territorios[-1]['valores'].append(valor)
    for territorio in territorios:
        recientes = territorio['valores'][-24:]
        # Una línea con dos puntos no dice más que la tabla: el gráfico aparece desde tres valores, con su escala.
        territorio['puntos'] = _puntos(recientes, ancho=560, alto=120) if len(recientes) > 2 else ''
        territorio['minimo'] = _numero(min(valor.valor for valor in recientes))
        territorio['maximo'] = _numero(max(valor.valor for valor in recientes))
        territorio['desde'], territorio['hasta'] = recientes[0].periodo, recientes[-1].periodo
    territorios.sort(key=lambda territorio: territorio['nombre'] != indicador.territorio_principal)
    # Con varios territorios, la comparación de su último valor (cantones, por ejemplo) es lo primero que se lee.
    comparacion = []
    if len(territorios) > 1:
        ultimos = [(territorio['nombre'], territorio['valores'][-1]) for territorio in territorios]
        tope = max((abs(valor.valor) for _nombre, valor in ultimos), default=0) or 1
        comparacion = sorted(({'nombre': nombre, 'valor': valor, 'texto': _numero(valor.valor),
                               'ancho': round(float(abs(valor.valor) / tope) * 100)} for nombre, valor in ultimos),
                             key=lambda fila: fila['valor'].valor, reverse=True)
    return render(request, 'portal/pages/unidades/observatorio/indicador.html', {
        **_contexto(unidad, 'fichas_metodologicas', request.user),
        'indicador': indicador,
        'fila': resumen(indicador),
        'territorios': territorios,
        'comparacion': comparacion,
        'publicaciones': indicador.publicaciones.filter(estado='publicada'),
    })


@xframe_options_sameorigin
def fichas_view(request, slug):
    """2.4 · Las fichas metodológicas de todos los indicadores, en una tabla."""
    unidad = _observatorio(slug)
    indicadores = list(indicadores_publicados(unidad))
    return render(request, 'portal/pages/unidades/observatorio/fichas.html', {
        **_contexto(unidad, 'fichas_metodologicas', request.user),
        'indicadores': indicadores,
    })


@xframe_options_sameorigin
def datos_view(request, slug):
    """2.2 · Las series descargables: por indicador y todo el observatorio."""
    unidad = _observatorio(slug)
    filas = [resumen(indicador) for indicador in indicadores_publicados(unidad)]
    return render(request, 'portal/pages/unidades/observatorio/datos.html', {
        **_contexto(unidad, 'datos', request.user),
        'filas': filas,
        'total_valores': ValorIndicador.objects.filter(indicador__unidad=unidad, indicador__publicado=True).count(),
        'licencia': LICENCIA,
    })


def _filas_de_datos(unidad, codigo=None):
    valores = (ValorIndicador.objects.filter(indicador__unidad=unidad, indicador__publicado=True)
               .select_related('indicador').order_by('indicador__orden', 'indicador__nombre', 'territorio', 'fecha'))
    if codigo:
        valores = valores.filter(indicador__codigo=codigo)
    return valores


def datos_csv_view(request, slug, codigo=None):
    """Las series en CSV (separado por punto y coma, como lo abre Excel en español), con su licencia. Con ?eje=,
    solo las de un eje temático."""
    unidad = _observatorio(slug)
    valores = _filas_de_datos(unidad, codigo)
    if codigo and not valores.exists() and not unidad.indicadores_observatorio.filter(codigo=codigo, publicado=True).exists():
        raise Http404('Indicador desconocido')
    eje = '' if codigo else request.GET.get('eje', '')
    if eje:
        valores = valores.filter(indicador__linea=get_object_or_404(unidad.lineas_observatorio, codigo=eje, publicada=True))
    DescargaDatos.registrar(unidad, 'csv', codigo or (f'linea:{eje}' if eje else ''))
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    nombre = f'{unidad.slug}-{codigo or eje or "datos"}.csv'
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    respuesta.write('﻿')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(['indicador', 'codigo', 'periodo', 'fecha', 'territorio', 'valor', 'unidad_medida', 'provisional',
                       'fuente', 'nota'])
    for valor in valores:
        escritor.writerow([valor.indicador.nombre, valor.indicador.codigo, valor.periodo, valor.fecha.isoformat(),
                           valor.territorio, str(valor.valor.normalize()).replace('.', ','), valor.indicador.unidad_medida,
                           'sí' if valor.provisional else 'no', valor.indicador.fuente, valor.nota])
    escritor.writerow([])
    escritor.writerow([f'Fuente: {unidad.nombre}. Licencia {LICENCIA[0]} ({LICENCIA[1]}).'])
    return respuesta


def datos_json_view(request, slug):
    """Los datos abiertos del observatorio en JSON: indicadores con su ficha y sus valores."""
    unidad = _observatorio(slug)
    indicadores = []
    for indicador in indicadores_publicados(unidad):
        indicadores.append({
            'codigo': indicador.codigo, 'nombre': indicador.nombre, 'definicion': indicador.definicion,
            'formula': indicador.formula, 'unidad_medida': indicador.unidad_medida, 'fuente': indicador.fuente,
            'url_fuente': indicador.url_fuente, 'periodicidad': indicador.periodicidad,
            'desagregacion': indicador.desagregacion, 'limitaciones': indicador.limitaciones,
            'valores': [{'periodo': valor.periodo, 'fecha': valor.fecha.isoformat(), 'territorio': valor.territorio,
                         'valor': float(valor.valor), 'provisional': valor.provisional}
                        for valor in sorted(indicador.valores.all(), key=lambda valor: (valor.territorio, valor.fecha))],
        })
    DescargaDatos.registrar(unidad, 'json')
    respuesta = JsonResponse({
        'observatorio': unidad.nombre, 'licencia': LICENCIA[0], 'licencia_url': LICENCIA[1],
        'generado': timezone.now().isoformat(), 'indicadores': indicadores,
    }, json_dumps_params={'ensure_ascii': False})
    respuesta['Access-Control-Allow-Origin'] = '*'
    return respuesta


@xframe_options_sameorigin
def alertas_view(request, slug):
    """3.1 y 3.2 · Las alertas vigentes y los umbrales de cada indicador."""
    unidad = _observatorio(slug)
    filas = [resumen(indicador) for indicador in indicadores_publicados(unidad)]
    return render(request, 'portal/pages/unidades/observatorio/alertas.html', {
        **_contexto(unidad, 'alertas', request.user),
        'alertas': [fila for fila in filas if fila['alerta']],
        'con_umbral': [fila for fila in filas
                       if fila['indicador'].vigilado],
    })


@xframe_options_sameorigin
def publicaciones_view(request, slug, clave):
    """4.1 a 4.3 · Los boletines, informes o notas de política publicados."""
    if clave not in TIPOS_POR_SECCION:
        raise Http404('Sección desconocida')
    unidad = _observatorio(slug)
    publicaciones = unidad.publicaciones_observatorio.filter(estado='publicada', tipo__in=TIPOS_POR_SECCION[clave])
    return render(request, 'portal/pages/unidades/observatorio/publicaciones.html', {
        **_contexto(unidad, clave, request.user),
        'titulo_seccion': TITULOS_PUBLICACION[clave],
        'publicaciones': publicaciones.order_by('-fecha_publicada', 'titulo'),
    })


def cumplimiento(unidad):
    """Lo planificado frente a lo publicado mediante un agregado, sin cargar archivos."""
    from django.db.models import Count, F, Q
    vencidas = unidad.publicaciones_observatorio.exclude(estado='cancelada').filter(
        fecha_planificada__lte=timezone.localdate())
    resumen = vencidas.order_by().aggregate(vencidas=Count('pk'),
        cumplidas=Count('pk', filter=Q(estado='publicada')),
        a_tiempo=Count('pk', filter=Q(estado='publicada', fecha_publicada__lte=F('fecha_planificada'))))
    resumen['porcentaje'] = round(resumen['cumplidas'] * 100 / resumen['vencidas']) if resumen['vencidas'] else None
    return resumen


@xframe_options_sameorigin
def calendario_view(request, slug):
    """4.4 · El calendario de publicaciones: lo planificado, lo publicado y lo atrasado."""
    unidad = _observatorio(slug)
    publicaciones = list(unidad.publicaciones_observatorio.exclude(estado='cancelada').order_by('fecha_planificada'))
    return render(request, 'portal/pages/unidades/observatorio/calendario.html', {
        **_contexto(unidad, 'calendario', request.user),
        'publicaciones': publicaciones,
        'cumplimiento': cumplimiento(unidad),
        'hoy': timezone.localdate(),
    })


@xframe_options_sameorigin
def encuestas_view(request, slug):
    """5.2 · Las encuestas propias con su metodología."""
    unidad = _observatorio(slug)
    return render(request, 'portal/pages/unidades/observatorio/encuestas.html', {
        **_contexto(unidad, 'encuestas', request.user),
        'encuestas': unidad.encuestas_observatorio.filter(activa=True),
    })


@xframe_options_sameorigin
def aliados_view(request, slug):
    """5.3 · Las instituciones aliadas: quién aporta datos, quién los usa y quién integra el comité."""
    unidad = _observatorio(slug)
    aliados = unidad.aliados_observatorio.filter(activo=True)
    grupos = [{'titulo': titulo, 'aliados': [aliado for aliado in aliados if aliado.rol == clave]}
              for clave, titulo in AliadoObservatorio.ROLES]
    return render(request, 'portal/pages/unidades/observatorio/aliados.html', {
        **_contexto(unidad, 'aliados', request.user),
        'grupos': [grupo for grupo in grupos if grupo['aliados']],
        'total': aliados.count(),
    })


@xframe_options_sameorigin
def solicitudes_view(request, slug):
    """6.1 · Pedir datos, un análisis o una asesoría. Exige cuenta; cada persona ve sus solicitudes y quien gestiona,
    todas."""
    unidad = _observatorio(slug)
    gestor = puede_gestionar_unidad(request.user, unidad)
    errores = {}
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        solicitud = SolicitudDatos(
            unidad=unidad, usuario=request.user,
            tipo=request.POST.get('tipo') if request.POST.get('tipo') in dict(SolicitudDatos.TIPOS) else 'datos',
            institucion=request.POST.get('institucion', '').strip()[:160],
            descripcion=request.POST.get('descripcion', '').strip(),
            finalidad=request.POST.get('finalidad', '').strip()[:255])
        if not solicitud.descripcion:
            errores['descripcion'] = 'Describe qué datos necesitas, de qué periodo y de qué territorio.'
        if not solicitud.finalidad:
            errores['finalidad'] = 'Cuéntanos para qué los usarás.'
        if not errores:
            solicitud.save()
            return redirect(f"{reverse('solicitudes_observatorio', args=[slug])}?enviada=1")
    propias = SolicitudDatos.objects.none()
    if request.user.is_authenticated:
        propias = unidad.solicitudes_datos.all() if gestor else unidad.solicitudes_datos.filter(usuario=request.user)
    return render(request, 'portal/pages/unidades/observatorio/solicitudes.html', {
        **_contexto(unidad, 'solicitudes', request.user),
        'tipos': SolicitudDatos.TIPOS,
        'solicitudes': propias.select_related('usuario'),
        'gestor': gestor,
        'errores': errores,
        'enviada': request.GET.get('enviada') == '1',
        # Desde la página de capacitaciones llega el tema elegido para no tener que escribirlo.
        'datos': request.POST or {'tipo': request.GET.get('tipo', ''), 'descripcion': request.GET.get('tema', '')[:200]},
    })


@xframe_options_sameorigin
def api_datos_view(request, slug):
    """6.4 · Cómo reutilizar los datos: descargas, JSON y licencia."""
    unidad = _observatorio(slug)
    return render(request, 'portal/pages/unidades/observatorio/api_datos.html', {
        **_contexto(unidad, 'api_datos', request.user),
        'licencia': LICENCIA,
        'indicadores': list(indicadores_publicados(unidad)),
        'url_json': request.build_absolute_uri(reverse('datos_json_observatorio', args=[slug])),
        'url_csv': request.build_absolute_uri(reverse('datos_csv_observatorio', args=[slug])),
    })


# Lo que todo observatorio ofrece y lo que no: la sección 1.4 lo explica con enlaces a cada servicio.
OFRECE = (
    ('fas fa-chart-line', 'Datos e indicadores abiertos', 'Indicadores con ficha metodológica y series descargables en CSV '
     'y JSON, con licencia CC BY 4.0.', 'indicadores_observatorio'),
    ('fas fa-file-pdf', 'Boletines e informes', 'Boletines periódicos, informes anuales y notas de política pública, con un '
     'calendario que se cumple.', 'calendario_observatorio'),
    ('fas fa-inbox', 'Datos y análisis a pedido', 'Series no publicadas, análisis a medida y asesoría metodológica para '
     'estudiantes, docentes, gobiernos locales y empresas.', 'solicitudes_observatorio'),
    ('fas fa-chalkboard-teacher', 'Cursos y capacitaciones', 'Talleres para leer indicadores, levantar encuestas, '
     'trabajar con mapas y armar tableros: se piden para un grupo o se abren con inscripción y certificado.',
     'capacitaciones_observatorio'),
    ('fas fa-laptop-house', 'Su sala de análisis', 'Estaciones con software estadístico y de mapas que se piden con una '
     'solicitud para tesis, proyectos y clases.', 'equipos_observatorio'),
    ('fas fa-users', 'Visitas guiadas', 'Para colegios, instituciones y gremios que quieran conocer cómo se producen los '
     'datos.', None),
    ('fas fa-user-plus', 'Prácticas, tesis y encuestas', 'Prácticas preprofesionales, vinculación, temas de tesis y '
     'levantamiento de encuestas con formación previa.', 'participa_observatorio'),
)
NO_OFRECE = (
    ('Análisis de muestras o ensayos', 'Los hacen los laboratorios de la universidad; el observatorio usa sus resultados '
     'como fuente.'),
    ('Producción o venta de productos', 'Es tarea de las plantas piloto y los centros experimentales.'),
    ('Microdatos con datos personales', 'Solo entrega datos agregados; los microdatos de encuestas van anonimizados y por '
     'convenio, conforme a la Ley Orgánica de Protección de Datos Personales.'),
    ('Estadística oficial certificada', 'La certifica el INEC; el observatorio cita sus fuentes y documenta sus métodos.'),
    ('Opinión partidista', 'Publica evidencia y notas técnicas; no toma partido en contiendas políticas.'),
)


def equipos_del_observatorio(unidad):
    """Los equipos que usa el observatorio: propios o compartidos con un laboratorio (una estación, un GNSS)."""
    from django.db.models import Q

    from apps.recursos.models.unidades import UnidadEquipo
    return UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct().select_related('equipo')


def _contenido(slug):
    from apps.observatorios.operacion.management.observatorios.contenidos import OBSERVATORIOS
    return OBSERVATORIOS.get(slug, {})


@xframe_options_sameorigin
def oferta_view(request, slug):
    """1.4 · Qué ofrece el observatorio y qué no, con las capacitaciones que dicta."""
    unidad = _observatorio(slug)
    ofrece = [{'icono': icono, 'titulo': titulo, 'texto': texto, 'url': reverse(ruta, args=[slug]) if ruta else ''}
              for icono, titulo, texto, ruta in OFRECE]
    return render(request, 'portal/pages/unidades/observatorio/oferta.html', {
        **_contexto(unidad, 'oferta', request.user),
        'ofrece': ofrece,
        'no_ofrece': NO_OFRECE,
        'capacitaciones': _contenido(slug).get('capacitaciones', ()),
    })


def comparaciones_de(indicadores):
    """Para cada indicador con más de un territorio, el último valor de cada uno, de mayor a menor, con su barra."""
    comparaciones = []
    for indicador in indicadores:
        ultimos = {}
        for valor in sorted(indicador.valores.all(), key=lambda valor: valor.fecha):
            ultimos[valor.territorio] = valor
        if len(ultimos) < 2:
            continue
        tope = max(abs(valor.valor) for valor in ultimos.values()) or 1
        filas = sorted(({'nombre': nombre, 'valor': valor, 'texto': _numero(valor.valor),
                         'ancho': round(float(abs(valor.valor) / tope) * 100)} for nombre, valor in ultimos.items()),
                       key=lambda fila: fila['valor'].valor, reverse=True)
        comparaciones.append({'indicador': indicador, 'filas': filas})
    return comparaciones


# Cómo se pide y se dicta una capacitación del observatorio, de la solicitud al certificado.
PASOS_CAPACITACION = (
    ('fas fa-inbox', 'Se pide', 'Una carrera, un docente, un GAD, un gremio o una empresa hace una solicitud de tipo '
     '«Capacitación o curso» con el tema, el grupo, cuántas personas y las fechas posibles.'),
    ('fas fa-handshake', 'Se acuerda', 'El observatorio responde en la misma solicitud con el contenido, la modalidad '
     '(presencial en su sala o virtual), la fecha y, si corresponde, la tarifa aprobada por la universidad.'),
    ('fas fa-chalkboard-teacher', 'Se dicta', 'Se abre como curso en esta plataforma: inscripción en línea, materiales, '
     'sesiones en vivo o autoguiadas y registro de asistencia; se trabaja con los datos reales del observatorio.'),
    ('fas fa-certificate', 'Se certifica', 'Quien aprueba recibe un certificado con código QR que cualquiera puede '
     'verificar en línea.'),
)


@xframe_options_sameorigin
def capacitaciones_view(request, slug):
    """Cursos y capacitaciones: los que tienen inscripción abierta, los que el observatorio puede dictar a pedido y
    cómo se piden, se dictan y se certifican."""
    from apps.formacion.presentation.cursos import cursos_visibles, resumen_de

    unidad = _observatorio(slug)
    cursos = cursos_visibles(unidad, request.user)
    for curso in cursos:
        curso.resumen = resumen_de(curso)
    politica = PoliticaDatosObservatorio.objects.filter(unidad=unidad).first()
    return render(request, 'portal/pages/unidades/observatorio/capacitaciones.html', {
        **_contexto(unidad, 'cursos', request.user),
        'cursos': cursos,
        'capacitaciones': _contenido(slug).get('capacitaciones', ()),
        'pasos': PASOS_CAPACITACION,
        'tarifa': politica.servicios_pagados if politica else PoliticaDatosObservatorio._meta.get_field('servicios_pagados').default,
    })


@xframe_options_sameorigin
def servicios_view(request, slug):
    """6.2 · Los estudios y servicios con tarifa: qué se cobra (nunca el dato), el catálogo y cómo cotizar."""
    from apps.reservas.presentation.reservas_publicas import catalogo_servicios_publico

    unidad = _observatorio(slug)
    politica, _ = PoliticaDatosObservatorio.objects.get_or_create(unidad=unidad)
    familias = catalogo_servicios_publico(unidad)
    return render(request, 'portal/pages/unidades/observatorio/servicios.html', {
        **_contexto(unidad, 'servicios_datos', request.user),
        'politica': politica,
        'familias': familias,
        'total_servicios': sum(len(familia['servicios']) for familia in familias),
        'capacitaciones': _contenido(slug).get('capacitaciones', ()),
    })


@xframe_options_sameorigin
def mapas_view(request, slug):
    """La comparación por territorio de cada indicador desagregado (cantones, puntos de control)."""
    unidad = _observatorio(slug)
    return render(request, 'portal/pages/unidades/observatorio/mapas.html', {
        **_contexto(unidad, 'tableros', request.user),
        'comparaciones': comparaciones_de(indicadores_publicados(unidad)),
    })


@xframe_options_sameorigin
def equipos_view(request, slug):
    """6.5 · La sala del observatorio, sus equipos y software, cómo pedir su uso y las visitas guiadas."""
    from apps.reservas.presentation.visitas import oferta_de_visitas

    unidad = _observatorio(slug)
    return render(request, 'portal/pages/unidades/observatorio/equipos.html', {
        **_contexto(unidad, 'sala', request.user),
        'espacios': unidad.espacios_reservables.filter(activo=True).order_by('orden', 'nombre'),
        'equipos': equipos_del_observatorio(unidad),
        'software': unidad.software_disponible.filter(activo=True).order_by('nombre'),
        'visitas': oferta_de_visitas(unidad),
    })


@xframe_options_sameorigin
def participa_view(request, slug):
    """5.4 · Cómo sumarse: prácticas, vinculación, encuestas activas y los datos que faltan por levantar."""
    unidad = _observatorio(slug)
    sin_datos = [indicador for indicador in indicadores_publicados(unidad) if not indicador.valores.all()]
    return render(request, 'portal/pages/unidades/observatorio/participa.html', {
        **_contexto(unidad, 'participa', request.user),
        'encuestas': unidad.encuestas_observatorio.filter(activa=True),
        'sin_datos': sin_datos,
        'lineas': _contenido(slug).get('participa', ()),
    })


def pdf_de_indicadores(unidad, formato, titulo, introduccion, filas, archivo, conjunto):
    """Un PDF institucional con una introducción y la tabla de indicadores con su último valor, cambio y fuente."""
    from io import BytesIO
    from xml.sax.saxutils import escape

    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.pdf_institucional import marco_institucional

    hoy = timezone.localdate()
    dibujar, lienzo, medidas = marco_institucional(formato=formato,
                                                   metadatos=[f'Generado: {hoy:%d/%m/%Y}', f'{len(filas)} indicadores'],
                                                   pie=unidad.nombre)
    tinta = medidas['colores']
    estilo_titulo = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=tinta['primario'],
                                   spaceAfter=4)
    cuerpo = ParagraphStyle('c', fontName='Helvetica', fontSize=9, leading=12.5, textColor=tinta['oscuro'], spaceAfter=4)
    celda = ParagraphStyle('d', fontName='Helvetica', fontSize=8, leading=10, textColor=tinta['oscuro'])
    flujo = [Paragraph(escape(titulo), estilo_titulo)]
    flujo += [Paragraph(escape(parrafo), cuerpo) for parrafo in introduccion if parrafo]
    flujo += [Paragraph(escape(f'Indicadores con su último valor publicado al {hoy:%d/%m/%Y}. Las cifras marcadas como '
                               'provisionales son aproximadas en su fuente. Datos abiertos con licencia CC BY 4.0.'), cuerpo),
              Spacer(1, 4 * mm)]
    datos = [[Paragraph(f'<b>{texto}</b>', celda) for texto in ('Indicador', 'Valor', 'Periodo', 'Cambio', 'Fuente')]]
    for fila in filas:
        indicador = fila['indicador']
        datos.append([Paragraph(escape(indicador.nombre + (' (ALERTA)' if fila['alerta'] else '')), celda),
                      Paragraph(escape(f"{fila['ultimo_texto']} {indicador.unidad_medida}"
                                       + (' (prov.)' if fila['ultimo'].provisional else '')), celda),
                      Paragraph(escape(fila['ultimo'].periodo), celda),
                      Paragraph(escape(fila['cambio_texto'] or '—'), celda),
                      Paragraph(escape(indicador.fuente), celda)])
    if len(datos) == 1:
        datos.append([Paragraph('Todavía no hay valores publicados.', celda), '', '', '', ''])
    tabla = Table(datos, colWidths=[62 * mm, 32 * mm, 18 * mm, 18 * mm, 50 * mm], repeatRows=1)
    tabla.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, 0), 0.8, tinta['primario']),
                               ('LINEBELOW', (0, 1), (-1, -1), 0.25, tinta['oscuro']),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    flujo.append(tabla)
    salida = BytesIO()
    SimpleDocTemplate(salida, pagesize=medidas['pagesize'], leftMargin=medidas['margen'], rightMargin=medidas['margen'],
                      topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
                      title=titulo).build(flujo, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=lienzo)
    DescargaDatos.registrar(unidad, 'pdf', conjunto)
    respuesta = HttpResponse(salida.getvalue(), content_type='application/pdf')
    respuesta['Content-Disposition'] = f'inline; filename="{archivo}-{hoy:%Y%m%d}.pdf"'
    return respuesta


@xframe_options_sameorigin
def boletin_view(request, slug):
    """El boletín de indicadores vigentes en PDF institucional: se arma en el momento con lo publicado."""
    unidad = _observatorio(slug)
    filas = [fila for fila in map(resumen, indicadores_publicados(unidad)) if fila['ultimo']]
    return pdf_de_indicadores(unidad, formato='BOLETÍN DE INDICADORES', titulo=unidad.nombre, introduccion=[],
                              filas=filas, archivo=f'boletin-{unidad.slug}', conjunto='boletin')


def _serie_grafico(indicador, ancho=520, alto=150):
    """La serie del territorio principal lista para un gráfico con escala: puntos, mínimo, máximo y extremos."""
    serie = sorted((valor for valor in indicador.valores.all() if valor.territorio == indicador.territorio_principal),
                   key=lambda valor: valor.fecha)
    if not serie:
        return None
    return {
        'puntos': _puntos(serie[-24:], ancho=ancho, alto=alto) if len(serie) > 1 else '',
        'minimo': _numero(min(valor.valor for valor in serie)), 'maximo': _numero(max(valor.valor for valor in serie)),
        'desde': serie[0].periodo, 'hasta': serie[-1].periodo, 'valores': serie[-6:],
    }


@xframe_options_sameorigin
def tableros_view(request, slug):
    """2.2 · Los tableros armados con los datos del observatorio, por eje, con la vista de cada uno."""
    unidad = _observatorio(slug)
    tableros = list(unidad.tableros_observatorio.filter(publicado=True).select_related('linea')
                    .prefetch_related('indicadores'))
    return render(request, 'portal/pages/unidades/observatorio/tableros.html', {
        **_contexto(unidad, 'tableros', request.user),
        'tableros': tableros,
        'vistas': sorted({tablero.get_vista_display().split(':')[0] for tablero in tableros}),
        'territoriales': len(comparaciones_de(indicadores_publicados(unidad))),
    })


@xframe_options_sameorigin
def visores_view(request, slug):
    """2.3 · Los tableros de otras instituciones insertados, con su fecha de corte y sus datos."""
    unidad = _observatorio(slug)
    return render(request, 'portal/pages/unidades/observatorio/visores.html', {
        **_contexto(unidad, 'visores', request.user),
        'visores': unidad.visores_observatorio.filter(publicado=True).select_related('linea'),
    })


def _semaforo(fila):
    """El color de un indicador: rojo si cruzó su umbral, verde si está dentro o mejora, ámbar si empeora."""
    if fila['alerta']:
        return 'rojo', 'Fuera de su criterio de alerta'
    if fila['indicador'].vigilado:
        return 'verde', 'Dentro de su criterio de alerta'
    if fila['favorable'] is True:
        return 'verde', 'Mejora frente al periodo anterior'
    if fila['favorable'] is False:
        return 'ambar', 'Empeora frente al periodo anterior'
    return 'gris', 'Sin umbral ni tendencia que valorar'


def _mapa_cantonal(indicador):
    """El último valor de cada cantón del Carchi pintado en el mapa, con cinco tonos de menor a mayor."""
    from apps.core.presentation.cantones_carchi import CREDITO, TRAZOS, VISTA

    ultimos = {}
    for valor in sorted(indicador.valores.all(), key=lambda valor: valor.fecha):
        if valor.territorio in TRAZOS:
            ultimos[valor.territorio] = valor
    if len(ultimos) < 3:
        return None
    cifras = [valor.valor for valor in ultimos.values()]
    minimo, maximo = min(cifras), max(cifras)
    rango = (maximo - minimo) or 1
    cantones = []
    for nombre, trazo in TRAZOS.items():
        valor = ultimos.get(nombre)
        tono = min(4, int((valor.valor - minimo) / rango * 5)) if valor else None
        cantones.append({'nombre': nombre, 'trazo': trazo, 'valor': valor, 'tono': tono,
                         'texto': _numero(valor.valor) if valor else 'sin dato'})
    periodos = sorted({valor.periodo for valor in ultimos.values()})
    return {'vista': VISTA, 'credito': CREDITO, 'cantones': cantones, 'minimo': _numero(minimo),
            'maximo': _numero(maximo), 'periodos': ', '.join(periodos)}


@xframe_options_sameorigin
def tablero_view(request, slug, pk):
    """Un tablero nativo, dibujado según su vista: series, semáforo, comparación entre territorios o mapa cantonal."""
    unidad = _observatorio(slug)
    tablero = get_object_or_404(unidad.tableros_observatorio, pk=pk, publicado=True)
    indicadores = list(tablero.indicadores.filter(publicado=True).prefetch_related('valores').order_by('orden', 'nombre'))
    paneles = []
    for indicador in indicadores:
        fila = resumen(indicador)
        color, estado = _semaforo(fila)
        paneles.append({'fila': fila, 'grafico': _serie_grafico(indicador), 'color': color, 'estado': estado,
                        'mapa': _mapa_cantonal(indicador) if tablero.vista == 'mapa' else None})
    return render(request, 'portal/pages/unidades/observatorio/tablero.html', {
        **_contexto(unidad, 'tableros', request.user),
        'tablero': tablero,
        'paneles': paneles,
        'comparaciones': comparaciones_de(indicadores) if tablero.vista == 'comparacion' else [],
        'codigos': ','.join(indicador.codigo for indicador in indicadores),
    })


@xframe_options_sameorigin
def visor_view(request, slug, pk):
    """Un visor externo, siempre con sus datos descargables, su fecha de corte y quién lo mantiene."""
    unidad = _observatorio(slug)
    visor = get_object_or_404(unidad.visores_observatorio, pk=pk, publicado=True)
    return render(request, 'portal/pages/unidades/observatorio/visor.html', {
        **_contexto(unidad, 'tableros', request.user),
        'visor': visor,
    })


@xframe_options_sameorigin
def politica_view(request, slug):
    """1.3 · La política de datos del observatorio: niveles de acceso, licencia, cita y servicios con tarifa."""
    unidad = _observatorio(slug)
    politica, _ = PoliticaDatosObservatorio.objects.get_or_create(unidad=unidad)
    niveles = [
        ('fas fa-lock-open', 'Abiertos', 'Gratuitos, sin registro', politica.abiertos),
        ('fas fa-inbox', 'Por solicitud', 'Gratuitos', politica.por_solicitud),
        ('fas fa-file-signature', 'Por convenio', 'Sin cobro por el dato', politica.por_convenio),
        ('fas fa-user-shield', 'Reservados', 'No se entregan', politica.reservados),
        ('fas fa-concierge-bell', 'Servicios con tarifa', 'Se cobra el servicio, no el dato', politica.servicios_pagados),
    ]
    return render(request, 'portal/pages/unidades/observatorio/politica.html', {
        **_contexto(unidad, 'politica_datos', request.user),
        'politica': politica,
        'niveles': niveles,
        'cita': politica.cita or f'{unidad.nombre}, Universidad Politécnica Estatal del Carchi',
    })


@xframe_options_sameorigin
def impacto_view(request, slug):
    """5.5 · Uso e impacto: descargas por formato, solicitudes atendidas y cumplimiento del calendario."""
    from django.db.models import Sum

    unidad = _observatorio(slug)
    descargas = unidad.descargas_datos.all()
    por_formato = {fila['formato']: fila['total'] for fila in descargas.values('formato').annotate(total=Sum('veces'))}
    por_mes = {}
    for fila in descargas:
        clave = fila.fecha.strftime('%Y-%m')
        por_mes[clave] = por_mes.get(clave, 0) + fila.veces
    solicitudes = unidad.solicitudes_datos.all()
    return render(request, 'portal/pages/unidades/observatorio/impacto.html', {
        **_contexto(unidad, 'impacto', request.user),
        'total_descargas': sum(por_formato.values()),
        'por_formato': sorted(por_formato.items()),
        'por_mes': sorted(por_mes.items())[-12:],
        'solicitudes': solicitudes.count(),
        'atendidas': solicitudes.filter(estado='atendida').count(),
        'cumplimiento': cumplimiento(unidad),
        'aliados_usuarios': unidad.aliados_observatorio.filter(activo=True, rol='usuario'),
    })


# ---------------------------------------------------------------- secciones del aula
def carpetas_de_observatorio(unidad, mapa, claves, usuario):
    """Las secciones del mapa de observatorios, cada una armada con sus registros y agrupada por eje temático cuando ayuda.

    Ninguna sección se arma vacía: las que dependen de un registro (indicadores, tableros, visores, encuestas) solo
    aparecen cuando existe; las demás (líneas, política, fuentes, reportes, servicios, sala) siempre tienen contenido.
    """
    from apps.formacion.presentation.aula import _boton, _carpeta, _icono
    from apps.observatorios.operacion.presentation.observatorio_lineas import agrupar_por_linea, lineas_publicadas
    from apps.gestion_unidades.presentation.repositorio import artefactos_publicos

    slug = unidad.slug
    carpetas = []

    def agregar(clave, identificador, botones, grupos=None):
        numero = mapa.numero(clave)
        grupos = grupos if grupos is not None else ([{'nombre': '', 'botones': botones}] if botones else [])
        grupos = [grupo for grupo in grupos if grupo['botones']]
        if numero and mapa.modulo_de(numero) in claves and grupos:
            carpetas.append(_carpeta(mapa.modulo_de(numero), identificador, '', _icono(mapa, numero), grupos,
                                     abierta=False, numero=numero, seccion=True, mapa=mapa))

    def ruta(nombre, *args):
        return reverse(nombre, args=[slug, *args])

    lineas = list(lineas_publicadas(unidad))
    indicadores = list(indicadores_publicados(unidad).select_related('linea', 'fuente_datos', 'conector'))
    filas = [resumen(indicador) for indicador in indicadores]
    grupos_linea = agrupar_por_linea(unidad, filas)

    # 1 · Información general
    por_linea = {}
    for indicador in indicadores:
        por_linea[indicador.linea_id] = por_linea.get(indicador.linea_id, 0) + 1
    # Como las áreas de un laboratorio: cada eje abre su página con su ficha, sus datos, fotos y videos.
    agregar('lineas', 'EjesTematicos', [
        _boton(f'linea-{linea.codigo}', linea.titulo, ruta('linea_observatorio', linea.codigo), linea.icono,
               f'Eje temático: {linea.titulo}',
               subtitulo=f'Eje temático · {por_linea.get(linea.pk, 0)} indicadores')
        for linea in lineas
    ] if lineas else [])
    agregar('oferta', 'OfertaObservatorio', [
        _boton('oferta-observatorio', 'Qué ofrece y qué no', ruta('oferta_observatorio'), 'fas fa-hand-holding',
               'Datos, estudios, capacitaciones, sala, visitas y prácticas; y lo que no hace'),
    ])
    agregar('politica_datos', 'PoliticaDatos', [
        _boton('politica-observatorio', 'Política de datos', ruta('politica_observatorio'), 'fas fa-balance-scale',
               'Qué es abierto, qué se pide, qué requiere convenio, qué nunca se entrega y qué se cobra'),
        _boton('fuentes-acceso', 'Acceso de cada fuente', ruta('fuentes_observatorio'), 'fas fa-key',
               'Qué bases son abiertas, por solicitud, por convenio o con costo'),
    ])

    # 2 · Datos y monitoreo
    agregar('indicadores', 'IndicadoresPorEje', [], grupos=[
        {'nombre': '', 'botones': [
            _boton('indicadores-observatorio', f'Todos los indicadores ({len(indicadores)})', ruta('indicadores_observatorio'),
                   'fas fa-chart-line', 'El último valor de cada indicador, su cambio y su tendencia, por eje')]},
    ] + [
        {'nombre': grupo['linea'].titulo if grupo['linea'] else 'Otros indicadores', 'botones': [
            _boton(f'indicador-{fila["indicador"].codigo}', fila['indicador'].nombre,
                   ruta('indicador_observatorio', fila['indicador'].codigo), 'fas fa-chart-area',
                   f'{fila["indicador"].nombre}: ficha y serie', subtitulo=(
                       f'{fila["ultimo_texto"]} {fila["indicador"].unidad_medida} · {fila["ultimo"].periodo}'
                       if fila['ultimo'] else 'Sin datos todavía'))
            for fila in grupo['filas']]}
        for grupo in grupos_linea
    ] if indicadores else [])
    tableros = list(unidad.tableros_observatorio.filter(publicado=True).select_related('linea'))
    territoriales = comparaciones_de(indicadores)
    agregar('tableros', 'TablerosObservatorio', [
        _boton(f'tablero-{tablero.pk}', tablero.titulo, ruta('tablero_observatorio', tablero.pk), 'fas fa-th-large',
               f'Tablero: {tablero.titulo}', subtitulo=tablero.get_vista_display().split(':')[0])
        for tablero in tableros
    ] + ([
        _boton('mapas-observatorio', f'Comparación por territorio ({len(territoriales)})', ruta('mapas_observatorio'),
               'fas fa-map-marked-alt', 'Cada indicador desagregado, territorio por territorio'),
    ] if territoriales else []))
    visores = list(unidad.visores_observatorio.filter(publicado=True))
    agregar('visores', 'VisoresExternos', [
        _boton(f'visor-{visor.pk}', visor.titulo, ruta('visor_observatorio', visor.pk), 'fas fa-external-link-square-alt',
               f'Visor de {visor.institucion or visor.get_plataforma_display()}: {visor.titulo}',
               subtitulo=' · '.join(filter(None, [visor.institucion, visor.get_plataforma_display()])))
        for visor in visores
    ])
    total_valores = sum(fila['total_valores'] for fila in filas)
    agregar('datos', 'DatosAbiertosHistoricos', [
        _boton('datos-observatorio', f'Series y descargas ({total_valores} valores)', ruta('datos_observatorio'),
               'fas fa-table', 'Las series por periodo y territorio, con su vía de entrada'),
        _boton('datos-csv', 'Todo en CSV', ruta('datos_csv_observatorio'), 'fas fa-file-csv',
               'Las series completas, con licencia CC BY 4.0'),
        _boton('historial-observatorio', 'Historial de correcciones (CSV)', ruta('historial_observatorio'),
               'fas fa-history', 'Cada valor publicado que se corrigió: antes, después, cuándo y por qué vía'),
    ] if indicadores else [])
    agregar('fichas_metodologicas', 'FichasMetodologicas', [
        _boton('fichas-observatorio', f'Fichas metodológicas ({len(indicadores)})', ruta('fichas_observatorio'),
               'fas fa-clipboard-list', 'Qué mide cada indicador, cómo se calcula, su fuente y su periodicidad'),
    ] if indicadores else [])

    # Las alertas son una lectura de los mismos indicadores: van en la misma pestaña, con sus criterios.
    alertas = [fila for fila in filas if fila['alerta']]
    con_umbral = [fila for fila in filas if fila['indicador'].vigilado]
    agregar('alertas', 'AlertasCriterios', [
        _boton('alertas-observatorio', f'Estado de las alertas ({len(alertas)} de {len(con_umbral)} vigilados)',
               ruta('alertas_observatorio'), 'fas fa-bell', 'Qué indicadores salieron de su criterio y cuáles están dentro'),
        _boton('umbrales-observatorio', f'Criterios de alerta ({len(con_umbral)})', ruta('alertas_observatorio') + '#umbrales',
               'fas fa-sliders-h', 'Umbrales con norma (OMS, OPS, precio mínimo) y variación admitida frente al periodo anterior'),
    ] + [
        _boton(f'alerta-{fila["indicador"].codigo}', fila['indicador'].nombre,
               ruta('indicador_observatorio', fila['indicador'].codigo), 'fas fa-exclamation-triangle',
               fila['indicador'].mensaje_alerta or fila['indicador'].nombre,
               subtitulo=f'{fila["ultimo_texto"]} {fila["indicador"].unidad_medida} · {fila["ultimo"].periodo}')
        for fila in alertas
    ] if con_umbral else [])
    ultimo = max((valor.modificado for indicador in indicadores for valor in indicador.valores.all()), default=None)
    automaticos = sum(1 for indicador in indicadores if hasattr(indicador, 'conector') and indicador.conector.activo)
    fuentes = len({indicador.fuente_datos_id for indicador in indicadores if indicador.fuente_datos_id})
    agregar('fuentes', 'FuentesActualizacion', [
        _boton('fuentes-observatorio', f'Fuentes y bases de datos ({fuentes})', ruta('fuentes_observatorio'),
               'fas fa-database', 'Quién produce cada dato, cómo se obtiene, su licencia y su nivel de acceso'),
        _boton('conexiones-observatorio', f'Conexiones automáticas ({automaticos})',
               ruta('fuentes_observatorio') + '#conexiones', 'fas fa-plug',
               'Los indicadores que se actualizan solos desde una API, con su última ejecución'),
        _boton('actualizaciones-observatorio', 'Actualizaciones recientes', ruta('actualizaciones_observatorio'),
               'fas fa-sync-alt', 'Los últimos valores que entraron, de qué fuente y por qué vía',
               subtitulo=f'Última: {timezone.localtime(ultimo):%d/%m/%Y %H:%M}' if ultimo else ''),
    ] if indicadores else [])

    # 4 · Reportes y publicaciones
    publicadas = unidad.publicaciones_observatorio.filter(estado='publicada')
    boletines = publicadas.filter(tipo__in=TIPOS_POR_SECCION['boletines']).count()
    agregar('boletines', 'BoletinIndicadores', ([
        # El boletín se arma en el momento con los últimos valores publicados: nunca envejece.
        _boton('boletin-vigente', 'Boletín de indicadores vigentes (PDF)', ruta('boletin_observatorio'), 'fas fa-file-pdf',
               'Los indicadores con su último valor, cambio y fuente, en un PDF institucional'),
    ] if any(fila['ultimo'] for fila in filas) else []) + ([
        _boton('publicaciones-boletines', f'Boletines publicados ({boletines})', ruta('publicaciones_observatorio', 'boletines'),
               'fas fa-newspaper', 'Los boletines que el observatorio publicó'),
    ] if boletines else []))
    informes = publicadas.filter(tipo__in=TIPOS_POR_SECCION['informes']).count()
    agregar('informes', 'ReportesInformes', [], grupos=[
        {'nombre': 'Reporte de cada eje', 'botones': [
            _boton(f'reporte-{linea.codigo}', f'{linea.titulo} (PDF)', ruta('informe_linea_observatorio', linea.codigo),
                   'fas fa-file-pdf', f'Reporte del eje {linea.titulo} con sus últimos valores')
            for linea in lineas if any(fila['indicador'].linea_id == linea.pk for fila in filas)]},
        {'nombre': 'Publicados', 'botones': [
            _boton('publicaciones-informes', f'Informes y notas de política ({informes})',
                   ruta('publicaciones_observatorio', 'informes'), 'fas fa-file-alt',
                   'Informes anuales y temáticos, perfiles y notas de política pública')] if informes else []},
    ])
    if unidad.publicaciones_observatorio.exclude(estado='cancelada').exists():
        estado = cumplimiento(unidad)
        agregar('calendario', 'CalendarioPublicaciones', [
            _boton('calendario-observatorio', 'Calendario de publicaciones', ruta('calendario_observatorio'),
                   'fas fa-calendar-alt', 'Lo planificado, lo publicado y lo atrasado',
                   subtitulo=(f'{estado["porcentaje"]} % cumplido' if estado['porcentaje'] is not None else '')),
        ])

    # 5 · Investigación y vinculación
    temas = sum(len(linea.lista_temas) for linea in lineas)
    artefactos = list(artefactos_publicos(unidad, usuario).order_by('nombre'))
    agregar('estudios', 'TemasEstudios', ([
        _boton('estudios-observatorio', f'Temas de investigación ({temas})', ruta('estudios_observatorio'), 'fas fa-search',
               'Preguntas abiertas por eje para tesis, prácticas y proyectos, y los estudios publicados'),
    ] if temas or artefactos or informes else []) + [
        _boton(f'artefacto-{artefacto.pk}', artefacto.nombre, reverse('artefacto_externo', args=[slug, artefacto.codigo]),
               'fas fa-cube', f'{artefacto.get_tipo_display()}: {artefacto.nombre}')
        for artefacto in artefactos
    ])
    encuestas = unidad.encuestas_observatorio.filter(activa=True)
    en_diseno = sum(1 for encuesta in encuestas if encuesta.etapa == 'diseno')
    agregar('encuestas', 'EncuestasLevantamientos', [
        _boton('encuestas-observatorio', f'Encuestas y levantamientos ({len(encuestas)})', ruta('encuestas_observatorio'),
               'fas fa-poll', 'Objetivo, población, muestra y periodicidad de cada levantamiento propio',
               subtitulo=f'{en_diseno} en diseño' if en_diseno else ''),
    ] if encuestas else [])
    aliados = unidad.aliados_observatorio.filter(activo=True).count()
    agregar('aliados', 'AliadosConvenios', [
        _boton('aliados-observatorio', f'Aliados y convenios ({aliados})', ruta('aliados_observatorio'),
               'fas fa-handshake', 'Quién aporta datos, quién los usa y quién integra el comité'),
    ] if aliados else [])
    agregar('participa', 'ParticipaObservatorio', [
        _boton('participa-observatorio', 'Prácticas, tesis y encuestas', ruta('participa_observatorio'),
               'fas fa-user-plus', 'Cómo sumarse al observatorio y qué datos faltan por levantar'),
    ])
    agregar('impacto', 'UsoImpacto', [
        _boton('impacto-observatorio', 'Uso e impacto de los datos', ruta('impacto_observatorio'),
               'fas fa-bullseye', 'Descargas, solicitudes atendidas y cumplimiento del calendario'),
    ])

    # 6 · Acceso y servicios
    agregar('solicitudes', 'SolicitarDatos', [
        _boton('solicitudes-observatorio', 'Solicitar datos o un análisis', ruta('solicitudes_observatorio'),
               'fas fa-inbox', 'Pide series, un análisis, una asesoría o el uso de la sala'),
    ])
    agregar('servicios_datos', 'EstudiosServicios', [
        _boton('servicios-observatorio', 'Estudios y servicios con tarifa', ruta('servicios_observatorio'),
               'fas fa-concierge-bell', 'Qué se cobra (nunca el dato abierto) y cómo pedir una cotización'),
    ])
    agregar('api_datos', 'DatosAbiertosApi', [
        _boton('api-observatorio', 'Datos abiertos y API', ruta('api_datos_observatorio'),
               'fas fa-code', 'Descarga en CSV y JSON, con licencia CC BY 4.0'),
    ] if indicadores else [])
    # Mientras no publique cursos, la sección lleva a las capacitaciones que el observatorio dicta y cómo se piden.
    from apps.formacion.presentation.cursos import grupos_de_cursos
    capacitaciones = _contenido(slug).get('capacitaciones', ())
    agregar('cursos', 'CapacitacionesObservatorio', [
        _boton('capacitaciones-observatorio', f'Capacitaciones que ofrece ({len(capacitaciones)})',
               ruta('capacitaciones_observatorio'), 'fas fa-chalkboard-teacher',
               'Qué dicta, para quién, cómo se pide y cómo se certifica'),
    ] if capacitaciones and not grupos_de_cursos(unidad, usuario) else [])
    from apps.reservas.presentation.visitas import oferta_de_visitas
    botones_sala = []
    if unidad.espacios_reservables.filter(activo=True).exists():
        botones_sala += [
            _boton('sala-observatorio', 'La sala, sus equipos y software', ruta('equipos_observatorio'),
                   'fas fa-laptop-house', 'Dónde está, cuántas personas caben y qué programas tiene'),
            _boton('sala-solicitar', 'Pedir el uso de la sala', ruta('solicitudes_observatorio') + '?tipo=sala',
                   'fas fa-door-open', 'Para tesis, proyectos y clases que trabajen con los datos del observatorio'),
        ]
    if oferta_de_visitas(unidad)['acepta_configurada']:
        botones_sala += [
            _boton('visitas-oferta', 'Visitas guiadas', reverse('oferta_visitas', args=[slug]), 'fas fa-users',
                   'Qué se recorre, cuánto dura y para quién'),
            _boton('visitas-solicitar', 'Pedir una visita', reverse('solicitar_visita', args=[slug]), 'fas fa-calendar-plus',
                   'Para colegios, instituciones y gremios'),
        ]
    agregar('sala', 'SalaEquiposVisitas', botones_sala)
    return carpetas
