"""Los ejes temáticos de un observatorio: lo que en un laboratorio es un área.

Cada eje tiene su página con qué estudia, qué aporta al Carchi, qué preguntas responde, cómo trabaja paso a
paso, sus indicadores vivos, sus tableros y visores, sus fuentes, qué produce, quién usa sus datos, qué carreras
aportan y sus videos; y su reporte en PDF, que se arma en el momento con los últimos valores publicados. La sección de
estudios reúne los temas de investigación abiertos de todos los ejes y lo que el observatorio ya publicó.
"""
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.observatorios.operacion.models.observatorios import LineaObservatorio

from apps.directorio_unidades.presentation.catalogos_publicos import _contexto
from apps.observatorios.operacion.presentation.observatorio import _observatorio, indicadores_publicados, pdf_de_indicadores, resumen


# El ícono de cada público en «Para quién sirve»; un público nuevo lleva el genérico.
ICONOS_PUBLICO = {'Docentes': 'fas fa-chalkboard-teacher', 'Estudiantes': 'fas fa-user-graduate',
                  'Empresas y gremios': 'fas fa-briefcase', 'Gobierno y comunidad': 'fas fa-landmark'}


def lineas_publicadas(unidad):
    return unidad.lineas_observatorio.filter(publicada=True).order_by('orden', 'titulo')


def agrupar_por_linea(unidad, filas):
    """Las filas de indicadores agrupadas por eje, en el orden de los ejes; las que no tienen eje van al final."""
    grupos = [{'linea': linea, 'filas': [fila for fila in filas if fila['indicador'].linea_id == linea.pk]}
              for linea in lineas_publicadas(unidad)]
    sueltas = [fila for fila in filas if fila['indicador'].linea_id is None
               or fila['indicador'].linea_id not in {grupo['linea'].pk for grupo in grupos}]
    if sueltas:
        grupos.append({'linea': None, 'filas': sueltas})
    return [grupo for grupo in grupos if grupo['filas']]


@xframe_options_sameorigin
def lineas_view(request, slug):
    """1.3 · Los ejes temáticos del observatorio, cada uno con lo que estudia y sus cifras."""
    unidad = _observatorio(slug)
    filas = [resumen(indicador) for indicador in indicadores_publicados(unidad)]
    lineas = []
    for linea in lineas_publicadas(unidad):
        propias = [fila for fila in filas if fila['indicador'].linea_id == linea.pk]
        lineas.append({'linea': linea, 'indicadores': len(propias),
                       'con_datos': sum(1 for fila in propias if fila['ultimo']),
                       'alertas': sum(1 for fila in propias if fila['alerta']),
                       'destacado': next((fila for fila in propias if fila['ultimo']), None),
                       'portada': linea.imagenes.first()})
    return render(request, 'portal/pages/unidades/observatorio/lineas.html', {
        **_contexto(unidad, 'lineas', request.user),
        'lineas': lineas,
    })


@xframe_options_sameorigin
def linea_view(request, slug, codigo):
    """La página de un eje temático, como la de un área de laboratorio: portada con foto, cifras, qué estudia,
    galería, qué ofrece, videos, cómo trabaja, sus indicadores vivos, tableros, fuentes, quién lo usa y otros ejes."""
    from apps.gestion_unidades.presentation.edicion_registro import ediciones_de

    unidad = _observatorio(slug)
    linea = get_object_or_404(LineaObservatorio, unidad=unidad, codigo=codigo, publicada=True)
    filas = [resumen(indicador) for indicador in
             indicadores_publicados(unidad).filter(linea=linea).select_related('fuente_datos', 'conector')]
    fuentes = {}
    for fila in filas:
        fuente = fila['indicador'].fuente_datos
        if fuente is not None:
            fuentes.setdefault(fuente.pk, {'fuente': fuente, 'indicadores': []})['indicadores'].append(fila['indicador'])
    valores = [valor for fila in filas for valor in fila['indicador'].valores.all()]
    con_valor = [fila for fila in filas if fila['ultimo']]
    ficha = {
        'territorios': ', '.join(sorted({valor.territorio for valor in valores})),
        'desde': min((valor.fecha.year for valor in valores), default=None),
        'hasta': max((valor.fecha.year for valor in valores), default=None),
        'valores': len(valores),
        'periodicidades': ', '.join(sorted({fila['indicador'].get_periodicidad_display().lower() for fila in filas})),
        'ultima': max((valor.modificado for valor in valores), default=None),
        'indicador_reciente': max(con_valor, key=lambda fila: fila['ultimo'].fecha) if con_valor else None,
        'alertas': sum(1 for fila in filas if fila['alerta']),
    }
    imagenes = list(linea.imagenes.all())
    tableros = list(linea.tableros.filter(publicado=True))
    visores = list(linea.visores.filter(publicado=True))
    otras = [{'linea': otra, 'indicadores': otra.indicadores.filter(publicado=True).count()}
             for otra in lineas_publicadas(unidad).exclude(pk=linea.pk)]
    return render(request, 'portal/pages/unidades/observatorio/area.html', {
        'unidad': unidad,
        'linea': linea,
        'filas': filas,
        'portada': imagenes[0] if imagenes else None,
        'galeria': imagenes,
        'franja': imagenes[1] if len(imagenes) > 1 else None,
        'videos': linea.lista_videos,
        'tableros': tableros,
        'visores': visores,
        'paneles': len(tableros) + len(visores),
        'encuestas': linea.encuestas.filter(activa=True),
        'fuentes': list(fuentes.values()),
        # Lo que no se descarga aquí: las fuentes que piden solicitud, convenio o pago en su origen.
        'en_origen': [item['fuente'] for item in fuentes.values() if item['fuente'].acceso != 'abierto'],
        'para_quien': [{'publico': publico, 'uso': uso, 'icono': ICONOS_PUBLICO.get(publico, 'fas fa-users')}
                       for publico, uso in linea.para_quien],
        'vigilados': sum(1 for fila in filas if fila['indicador'].vigilado),
        'automaticos': sum(1 for fila in filas if getattr(fila['indicador'], 'conector', None) and fila['indicador'].conector.activo),
        'otras': otras,
        'ficha': ficha,
        'puede_editar': 'linea_observatorio' in ediciones_de(request.user, unidad),
    })


@xframe_options_sameorigin
def informe_linea_view(request, slug, codigo):
    """El reporte de una línea en PDF institucional: qué estudia y sus indicadores con el último valor publicado."""
    unidad = _observatorio(slug)
    linea = get_object_or_404(LineaObservatorio, unidad=unidad, codigo=codigo, publicada=True)
    filas = [fila for fila in map(resumen, indicadores_publicados(unidad).filter(linea=linea)) if fila['ultimo']]
    introduccion = [linea.que_estudia, linea.por_que_importa]
    if linea.lista_preguntas:
        introduccion.append('Preguntas que responde: ' + ' · '.join(linea.lista_preguntas))
    return pdf_de_indicadores(unidad, formato='REPORTE DEL EJE TEMÁTICO', titulo=f'{linea.titulo} · {unidad.nombre_corto or unidad.nombre}',
                              introduccion=introduccion, filas=filas, archivo=f'reporte-{unidad.slug}-{linea.codigo}',
                              conjunto=f'linea:{linea.codigo}')


@xframe_options_sameorigin
def estudios_view(request, slug):
    """5.1 · Los temas de investigación abiertos de cada línea y los estudios que el observatorio ya publicó."""
    from apps.gestion_unidades.presentation.repositorio import artefactos_publicos

    unidad = _observatorio(slug)
    publicadas = list(unidad.publicaciones_observatorio.filter(estado='publicada', tipo__in=('informe', 'perfil', 'nota_politica'))
                      .order_by('-fecha_publicada'))
    artefactos = list(artefactos_publicos(unidad, request.user).order_by('nombre'))
    return render(request, 'portal/pages/unidades/observatorio/estudios.html', {
        **_contexto(unidad, 'estudios', request.user),
        'lineas': [linea for linea in lineas_publicadas(unidad) if linea.lista_temas],
        'artefactos': artefactos,
        'publicaciones': publicadas,
        'total_estudios': len(publicadas) + len(artefactos),
    })
