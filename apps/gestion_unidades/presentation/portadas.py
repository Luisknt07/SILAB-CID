"""La portada de cada pestaña de la ficha: qué es esta sección y qué hay dentro.

Se presenta con un estilo tecnológico animado que alude a la pestaña (órbitas, cubos, engranajes, red, anillos,
molécula u ondas). La unidad puede cambiar su frase, su texto, el estilo, la imagen de fondo o poner en su lugar una
escena 3D publicada (PortadaPestana).

Antes, al cambiar de pestaña el visor se quedaba con el documento de la
anterior: quien pasaba de «Procesos y protocolos» a «Calidad e inocuidad»
seguía viendo la ficha del proceso que acababa de abrir. El visor ahora vuelve
a la portada de la pestaña, y la portada explica lo que esa sección contiene:
qué es, qué vas a encontrar, de dónde salen los datos y cómo se lee.

El texto de cada sección vive aquí, junto a la lógica de la ficha, porque no es
un dato que la unidad edite: describe lo que la plataforma publica en esa
pestaña. Lo que sí sale de la unidad es la lista de lo que hay dentro, que se
arma de las carpetas reales del módulo.
"""

from apps.recursos.models.recursos import CarpetaRecurso
from apps.gestion_unidades.models.portadas import PortadaPestana

# El estilo animado con que se presenta cada pestaña si la unidad no elige otro: alude a lo que contiene.
TEMA_POR_PESTANA = {
    'informacion-general': 'orbitas', 'areas-equipos': 'cubos', 'equipos-infraestructura': 'cubos',
    'procesos-productos': 'engranajes', 'procesos-protocolos': 'engranajes', 'produccion-lotes': 'engranajes',
    'docencia-capacitacion': 'red', 'reservas-servicios': 'reloj', 'investigacion-formativa': 'molecula',
    'calidad-inocuidad': 'ondas',
    # Observatorios.
    'datos-indicadores': 'red', 'reportes-publicaciones': 'cubos',
    'investigacion-vinculacion': 'molecula', 'acceso-servicios': 'orbitas',
    # Centros experimentales.
    'areas-productivas': 'ondas', 'produccion-ensayos': 'engranajes', 'infraestructura-equipos': 'cubos',
    'visitas-servicios': 'reloj',
}
# Secciones que la ficha dibuja siempre con sus propios botones (video, datos, reservas…), aunque no tengan carpeta.
# y el ícono con que se presentan en la portada.
SECCIONES_CON_CONTENIDO_FIJO = {
    'presentacion': 'fas fa-play-circle', 'unidad': 'fas fa-info-circle', 'interior': 'fas fa-drafting-compass',
    'repositorio': 'fas fa-folder-open', 'reservar': 'fas fa-calendar-check', 'servicios': 'fas fa-concierge-bell',
    'agenda': 'fas fa-calendar-alt', 'requisitos': 'fas fa-id-badge', 'mis_guias': 'fas fa-book-reader',
    'reglamento': 'fas fa-file-contract', 'visitas': 'fas fa-users',
}

# Lo que cada pestaña explica. La clave es la del módulo; una unidad que
# invente su propia pestaña recibe la explicación genérica de abajo.
EXPLICACIONES = {
    'informacion-general': {
        'entrada': (
            'La presentación de la unidad: qué hace, de quién depende, dónde está y a quién atiende.'
        ),
        'datos': 'Sale de la ficha institucional de la unidad y de su reglamento publicado.',
        'como_leerlo': [
            'El video y la descripción dicen a qué se dedica la unidad.',
            'Los datos de contacto y el horario dicen cuándo y con quién hablar.',
            'El reglamento de uso es la norma que acepta quien reserva.',
        ],
    },
    'procesos-protocolos': {
        'entrada': (
            'Los sistemas de producción de la planta, proceso por proceso: qué entra, qué pasa en cada '
            'etapa, qué sale y qué se controla.'
        ),
        'datos': (
            'Cada ficha se arma de la receta cargada en la planta: sus etapas con equipo, área, tiempos, '
            'personas y rendimiento, sus insumos por etapa y sus salidas. Los simuladores corren sobre esa '
            'misma receta, así que lo que muestran es lo que la planta produce de verdad.'
        ),
        'como_leerlo': [
            'La ficha de un proceso trae su diagrama de flujo, su diagrama sinóptico, el cursograma '
            'analítico con tiempos y distancias, el balance de masa y el cronograma de la corrida.',
            'Los puntos críticos de control aparecen marcados en la ficha y en los protocolos, con su '
            'parámetro y su límite.',
            'Los simuladores toman los datos de una reserva o de una programación, o corren libres para '
            'comparar escenarios.',
        ],
    },
    'equipos-infraestructura': {
        'entrada': 'Las áreas de la unidad y los equipos que aloja cada una, con sus auxiliares.',
        'datos': (
            'Sale del catálogo de equipos y espacios de la unidad: lo mismo que el asistente de reservas '
            'ofrece y lo que las etapas de cada proceso ocupan.'
        ),
        'como_leerlo': [
            'Cada área dice su capacidad, su política de reserva y lo que contiene.',
            'Cada equipo dice para qué sirve, qué necesita y en qué área está.',
        ],
    },
    'produccion-lotes': {
        'entrada': (
            'El catálogo estable de productos, el requerimiento de materiales y el resumen público de '
            'la actividad de la planta.'
        ),
        'datos': (
            'El catálogo sale de los productos publicados y de su familia institucional. La actividad '
            'muestra solo totales del mes; el detalle diario de corridas y lotes permanece en gestión.'
        ),
        'como_leerlo': [
            'Cada producto tiene su propia ficha; si existe una receta publicada, esa ficha enlaza al '
            'proceso técnico sin copiarlo.',
            'El requerimiento de materiales dice qué hace falta en bodega para un plan de corridas.',
            'El resumen de actividad informa corridas cerradas y lotes vigentes sin exponer registros.',
        ],
    },
    'calidad-inocuidad': {
        'entrada': (
            'Qué mide la unidad, con qué límite y en qué momento; los puntos críticos de cada proceso y '
            'las normas que exige para entrar.'
        ),
        'datos': (
            'Sale de los planes de calidad de la unidad (recepción de materia prima, control en proceso y '
            'liberación de producto) y de los puntos críticos declarados en cada receta.'
        ),
        'como_leerlo': [
            'Cada parámetro dice su límite y el método con que se mide.',
            'El plan HACCP cruza los puntos críticos de cada proceso con los parámetros que los vigilan.',
            'Lo que sale del límite se registra como no conformidad y el lote espera su disposición.',
        ],
    },
    'reservas-servicios': {
        'entrada': 'Cómo se pide la unidad: sus servicios, su agenda y lo que exige antes de entrar.',
        'datos': 'Sale del catálogo de servicios de la unidad y de su agenda de disponibilidad.',
        'como_leerlo': [
            'El asistente de reservas pide la actividad, el proceso y la escala, y marca lo que hace falta.',
            'Los requisitos de acceso se verifican al reservar y al ingresar.',
        ],
    },
    'areas-equipos': {
        'entrada': 'Las áreas del laboratorio, sus equipos con ficha técnica, el software y los materiales.',
        'datos': 'Sale de las áreas, los equipos y el software que la unidad registra.',
        'como_leerlo': [
            'Cada equipo tiene su ficha con uso autorizado y estado.',
            'El software dice su versión, sus licencias y si se usa en sala o en remoto.',
        ],
    },
    'procesos-productos': {
        'entrada': 'Cómo se hace cada cosa en el laboratorio, con qué métodos y normas, y qué entrega.',
        'datos': 'Sale de las carpetas que la unidad publica en cada sección.',
        'como_leerlo': ['Cada proceso dice sus pasos, sus equipos y lo que produce.'],
    },
    'docencia-capacitacion': {
        'entrada': 'Las guías de práctica, las asignaturas que practican aquí, los cursos y los recursos de aprendizaje.',
        'datos': 'Sale de las guías aprobadas, las asignaturas vinculadas y los recursos publicados.',
        'como_leerlo': [
            'Cada guía lleva su código y su versión.',
            'Los recursos de aprendizaje se abren en este mismo visor.',
        ],
    },
    'investigacion-formativa': {
        'entrada': 'Los proyectos formativos de estudiantes, la colaboración con los centros de I+D, '
                   'sus resultados y los convenios del laboratorio.',
        'datos': 'Sale de las carpetas que la unidad publica en esta pestaña.',
        'como_leerlo': ['La investigación científica es de los centros de I+D: aquí se ve lo que se hace '
                        'en el laboratorio y con qué centros colabora.'],
    },
}

# Los observatorios producen información para decidir, no prestan equipos: sus pestañas se explican aparte,
# porque algunas claves (investigación y vinculación) las comparten con los centros experimentales.
EXPLICACIONES_OBSERVATORIO = {
    'datos-indicadores': {
        'entrada': 'Los indicadores de cada eje con su último valor y su tendencia, las alertas, los tableros y mapas, '
                   'los visores de otras instituciones, los datos abiertos y de dónde sale cada dato.',
        'datos': 'Sale de los indicadores que el observatorio publica, de las fuentes oficiales y encuestas que los '
                 'alimentan y de las conexiones que los mantienen al día.',
        'como_leerlo': [
            'Cada indicador dice qué mide, cómo se calcula, de dónde sale el dato y cada cuánto se actualiza.',
            'Una alerta no es una predicción: avisa que un valor salió de su criterio (un umbral o un cambio brusco).',
            'Las series y su historial de correcciones se descargan en CSV con licencia abierta.',
        ],
    },
    'reportes-publicaciones': {
        'entrada': 'Los boletines, los informes y las notas de política pública del observatorio, con su calendario.',
        'datos': 'Sale de las publicaciones registradas y de su calendario: lo planificado y lo cumplido.',
        'como_leerlo': ['Cada publicación indica su periodo, su fecha y los indicadores en que se basa.'],
    },
    'investigacion-vinculacion': {
        'entrada': 'Los estudios y encuestas propias del observatorio, sus aliados y convenios, la formación que '
                   'ofrece y el uso que se da a sus datos.',
        'datos': 'Sale de las encuestas, los aliados y los cursos registrados por el observatorio.',
        'como_leerlo': ['Las encuestas propias publican su metodología: muestra, periodo y cuestionario.'],
    },
    'acceso-servicios': {
        'entrada': 'Cómo pedir datos o un análisis, los estudios a medida, cómo participar y el acceso a los datos '
                   'abiertos.',
        'datos': 'Sale del catálogo de servicios y de la política de datos del observatorio.',
        'como_leerlo': ['Los datos agregados son abiertos; los microdatos se entregan anonimizados, por convenio.'],
    },
}

# Un centro experimental es una finca que produce y experimenta: sus pestañas hablan de ejes productivos, de lo que
# produce y a dónde va, de sus instalaciones y de cómo se visita, no de equipos de laboratorio ni de datos.
EXPLICACIONES_CENTRO = {
    'informacion-general': {
        'entrada': 'El centro: dónde está, qué produce, cómo funciona, quién hace qué (por rol) y cómo se usa.',
        'datos': 'Sale de la ficha institucional del centro y de sus datos con fuente: altitud, superficie, hato e '
                 'instalaciones.',
        'como_leerlo': [
            '«Cómo funciona el centro» explica el ciclo con que deja de producir solo en temporada de prácticas.',
            'La ficha nombra roles (administración, familias cuidadoras, docentes); nunca a las personas.',
        ],
    },
    'areas-productivas': {
        'entrada': 'Los ejes productivos del centro (ganadería, cultivos, frutales, invernaderos, especies menores) '
                   'y su calendario: qué produce cada uno, cómo trabaja y en qué temporada.',
        'datos': 'Sale de la ficha de cada eje que mantiene el centro, con fotos con crédito y videos verificados.',
        'como_leerlo': [
            'Cada eje abre su página: qué produce, cómo trabaja paso a paso, sus áreas, a dónde va y qué le falta.',
            'El calendario reúne lo que hace cada eje en cada temporada, para planificar prácticas y visitas.',
        ],
    },
    'produccion-ensayos': {
        'entrada': 'Lo que el centro produce y a dónde va (las plantas piloto que abastece, la venta, la semilla y '
                   'las prácticas), sus ensayos de campo y las guías de práctica.',
        'datos': 'Sale de las relaciones del centro con las plantas piloto y del destino que declara cada eje.',
        'como_leerlo': ['Una planta «en creación» todavía no opera: el centro ya produce la materia prima que '
                        'transformará.'],
    },
    'infraestructura-equipos': {
        'entrada': 'Las áreas, potreros, parcelas, invernaderos y galpones del centro, con sus equipos y su '
                   'responsable.',
        'datos': 'Sale de las áreas y los equipos registrados por el centro.',
        'como_leerlo': ['Cada área dice qué se hace en ella, cuántas personas caben y cómo se reserva.'],
    },
    'investigacion-vinculacion': {
        'entrada': 'Los temas de investigación abiertos en cada eje, los cursos y capacitaciones del centro y las '
                   'unidades con que trabaja: las plantas que aloja y abastece y los laboratorios que analizan sus '
                   'muestras.',
        'datos': 'Sale de los temas de cada eje, del catálogo de cursos y de las relaciones registradas entre unidades.',
        'como_leerlo': ['Un tema abierto es una pregunta para una tesis o un proyecto: se propone reservando el área '
                        'con el tipo «Investigación».'],
    },
    'visitas-servicios': {
        'entrada': 'Cómo reservar el centro para prácticas de campo, ensayos, recorridos agroturísticos y visitas '
                   'técnicas, con su agenda, sus requisitos y su reglamento.',
        'datos': 'Sale del sistema de reservas, de la agenda del centro y de su reglamento de uso.',
        'como_leerlo': [
            'Las prácticas y los ensayos se piden con la guía y el docente responsable.',
            'Los recorridos se abren en fechas y grupos que fija el centro; se ingresa con inducción de bioseguridad.',
        ],
    },
}

GENERICA = {
    'entrada': 'Lo que la unidad publica en esta sección.',
    'datos': 'Sale del contenido que la unidad mantiene en su panel de gestión.',
    'como_leerlo': ['Elige un elemento de la derecha para abrirlo en este visor.'],
}


def _carpetas_de_contenido(unidad):
    """Las carpetas que la unidad publica, agrupadas por el módulo al que cuelgan."""
    por_modulo = {}
    carpetas = (
        CarpetaRecurso.objects.filter(unidad=unidad, modulo_config__isnull=False, activa=True)
        .select_related('modulo_config')
        .prefetch_related('recursos')
        .order_by('nombre')
    )
    for carpeta in carpetas:
        por_modulo.setdefault(carpeta.modulo_config.clave, []).append(carpeta)
    return por_modulo


def _elementos_del_modulo(clave, carpetas, carpetas_contenido):
    """Lo que esta pestaña publica de verdad, para que la portada no prometa de más."""
    elementos = []
    for carpeta in carpetas:
        if carpeta.get('modulo') != clave:
            continue
        if carpeta.get('pendiente'):
            continue
        for grupo in carpeta.get('grupos', []):
            for boton in grupo.get('botones', []):
                elementos.append({
                    'nombre': boton['nombre'],
                    'icono': boton.get('icono', 'fas fa-file'),
                    'detalle': boton.get('titulo', ''),
                    'carpeta': carpeta['titulo'],
                })
    def recursos_de(carpeta):
        yield from getattr(carpeta, 'recursos_publicos', carpeta.recursos.all())
        for hija in getattr(carpeta, 'subcarpetas_publicas', []):
            yield from recursos_de(hija)

    for carpeta in carpetas_contenido.get(clave, []):
        for recurso in recursos_de(carpeta):
            if not recurso.activo or not (recurso.archivo or recurso.url):
                continue
            elementos.append({
                'nombre': recurso.nombre,
                'icono': 'fas fa-lock' if recurso.visibilidad == 'restringida' else 'fas fa-file',
                'detalle': 'Requiere cuenta institucional' if recurso.visibilidad == 'restringida' else '',
                'carpeta': carpeta.nombre,
            })
    return elementos


def _secciones_del_modulo(modulo, carpetas, mapa, ajustes):
    """Las secciones numeradas de la pestaña que tienen contenido, con cuánto publican, y sus secciones con plantilla."""
    from apps.formacion.presentation.aula import _icono
    from apps.plantas_piloto.operacion.presentation.secciones_plantas import seccion_de
    por_numero = {carpeta['numero']: carpeta for carpeta in carpetas if carpeta.get('numero')}
    elementos = []
    for numero, _titulo in (mapa.pestanas[modulo.clave][1] if modulo.clave in mapa.pestanas else ()):
        seccion = seccion_de(numero, ajustes, mapa)
        carpeta = por_numero.get(numero)
        if seccion['oculta']:
            continue
        pendiente = False
        if carpeta and not carpeta.get('pendiente'):
            total = carpeta.get('total', 0)
        elif mapa.secciones[numero]['clave'] in SECCIONES_CON_CONTENIDO_FIJO:
            total = None
        elif carpeta:
            # Solo quien gestiona recibe las secciones pendientes: la portada le muestra lo que falta completar.
            total, pendiente = None, True
        else:
            continue
        elementos.append({
            'nombre': seccion['titulo'], 'icono': (carpeta['icono'] if carpeta else SECCIONES_CON_CONTENIDO_FIJO.get(
                mapa.secciones[numero]['clave']) or _icono(mapa, numero)),
            'detalle': ('Pendiente de publicación' if pendiente else
                        f"{total} publicado{'' if total == 1 else 's'}" if total is not None else 'Abrir la sección'),
            'carpeta': '', 'numero': numero, 'abrir': '', 'total': total, 'pendiente': pendiente,
        })
    for carpeta in carpetas:
        if carpeta.get('propia') and carpeta.get('modulo') == modulo.clave:
            elementos.append({'nombre': carpeta['titulo'], 'icono': carpeta['icono'], 'carpeta': '', 'numero': '',
                              'detalle': f"{carpeta['total']} publicado{'' if carpeta['total'] == 1 else 's'}",
                              'abrir': f"collapse{carpeta['id']}", 'total': carpeta['total']})
    return elementos


# De dónde toma cada pestaña las imágenes animadas de su portada: fotos de la unidad, de sus áreas o de sus equipos.
IMAGENES_POR_PESTANA = {
    'informacion-general': ('unidad', 'areas'), 'areas-equipos': ('areas', 'unidad', 'equipos'),
    'equipos-infraestructura': ('areas', 'unidad', 'equipos'), 'procesos-productos': ('areas', 'unidad', 'equipos'),
    'procesos-protocolos': ('areas', 'unidad', 'equipos'), 'docencia-capacitacion': ('unidad', 'areas'),
    'reservas-servicios': ('areas', 'unidad'), 'investigacion-formativa': ('unidad', 'areas', 'equipos'),
    'datos-indicadores': ('unidad',), 'reportes-publicaciones': ('unidad',),
    'acceso-servicios': ('unidad',),
    'areas-productivas': ('areas', 'unidad'), 'produccion-ensayos': ('areas', 'unidad'),
    'infraestructura-equipos': ('areas', 'unidad', 'equipos'), 'visitas-servicios': ('areas', 'unidad'),
}


def _imagenes_de(unidad):
    """Las fotos reales con que la portada se ilustra, por origen."""
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from apps.recursos.models.unidades import UnidadEquipo
    from apps.gestion_unidades.presentation.conoce import foto_de_portada, muestra_de_la_galeria
    from apps.recursos.presentation.equipo_publico import imagen_de
    equipos, vistos = [], set()
    for fisica in UnidadEquipo.objects.filter(laboratorio=unidad, activa=True).select_related('equipo').order_by('codigo_unidad'):
        if fisica.equipo_id not in vistos:
            vistos.add(fisica.equipo_id)
            equipos.append(imagen_de(fisica.equipo)[0])
    return {
        'unidad': [foto_de_portada(unidad), *muestra_de_la_galeria(unidad, 4)[0]],
        'areas': [area.imagen_propia_url for area in EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden')[:8]],
        'equipos': equipos[:12],
    }


def _elegir_imagenes(fuentes, origenes, cantidad=5):
    elegidas = []
    for origen in origenes:
        for imagen in fuentes.get(origen, []):
            if imagen and imagen not in elegidas:
                elegidas.append(imagen)
    return elegidas[:cantidad]


def _escena(url):
    """La dirección que se incrusta: la escena de Spline tal cual; un modelo de Sketchfab, en su forma de inserción."""
    if 'sketchfab.com' in url and '/embed' not in url:
        return url.rstrip('/') + '/embed?autostart=1&ui_theme=dark&transparent=1'
    return url


def portadas_de(unidad, modulos, carpetas=(), carpetas_contenido=None):
    """Una portada por pestaña, con su explicación y lo que contiene.

    `carpetas` son las del aula (`aula.carpetas_del_aula`); las carpetas de
    contenido que la unidad publica se consultan aquí. De ahí sale la lista de
    «qué vas a encontrar», que es real y no un texto fijo. En Plantas Piloto
    la portada resume secciones; los objetos viven una sola vez dentro de ellas.
    """
    if carpetas_contenido is None:
        carpetas_contenido = _carpetas_de_contenido(unidad)
    from apps.plantas_piloto.operacion.presentation.secciones_plantas import ajustes_de, mapa_de
    mapa = mapa_de(unidad)
    ajustes = ajustes_de(unidad) if mapa else {}
    editadas = {portada.modulo_id: portada for portada in PortadaPestana.objects.filter(modulo__in=modulos)}
    fuentes = _imagenes_de(unidad)
    portadas = []
    propias = {'observatorios': EXPLICACIONES_OBSERVATORIO,
               'centro_experimental': EXPLICACIONES_CENTRO}.get(getattr(mapa, 'tipo', ''), {})
    for modulo in modulos:
        explicacion = propias.get(modulo.clave) or EXPLICACIONES.get(modulo.clave, GENERICA)
        # Con mapa numerado, la portada resume las secciones; sin él, lista lo que cada carpeta publica.
        elementos = (_secciones_del_modulo(modulo, carpetas, mapa, ajustes) if mapa is not None
                     else _elementos_del_modulo(modulo.clave, carpetas, carpetas_contenido))
        editada = editadas.get(modulo.pk)
        portadas.append({
            'clave': modulo.clave,
            'pk': modulo.pk,
            'titulo': modulo.nombre,
            'icono': modulo.icono,
            'entrada': (editada.descripcion if editada and editada.descripcion else explicacion['entrada']),
            'lema': editada.lema if editada else '',
            'tema': (editada.tema if editada and editada.tema else TEMA_POR_PESTANA.get(modulo.clave, 'ondas')),
            'escena': _escena(editada.escena_3d) if editada and editada.escena_3d else '',
            'datos': explicacion['datos'],
            'como_leerlo': explicacion['como_leerlo'],
            'elementos': elementos,
            'cifras': [elemento for elemento in elementos if elemento.get('total')][:4],
            # La imagen que la unidad eligió para la portada abre la serie de fotos que se funden.
            'imagenes': _elegir_imagenes({**fuentes, 'propia': [editada.imagen.url] if editada and editada.imagen else []},
                                         ('propia', *IMAGENES_POR_PESTANA.get(modulo.clave, ('unidad', 'areas', 'equipos')))),
            'vacia': not elementos,
        })
    return portadas
