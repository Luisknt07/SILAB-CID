"""La ruta de cada dato hasta la ficha pública: dónde se guarda y en qué parte se ve.

Una sola tabla alimenta las dos puntas. El organizador «Contenidos de la ficha» dice,
sección por sección, dónde se edita lo que muestra; el editor de la unidad rotula cada
bloque con las secciones a las que llega y cada archivo con el lugar donde aparece.
Lo que no llega a ninguna parte se nombra como tal, para que no quede información suelta.

Las tablas hablan en claves de sección («unidad», «guias», «reservar»), que cada mapa
traduce a sus números: la misma tabla sirve a una planta y a un laboratorio.
"""
from django.utils.text import slugify

from apps.plantas_piloto.operacion.presentation.secciones_plantas import seccion_de

CABECERA = 'cabecera'
MENU = 'menu'
CARPETAS = 'carpetas'
FIJAS = (CABECERA, MENU, CARPETAS)

# Campos de la unidad → claves de sección que los leen. Sin entrada: uso interno.
SECCIONES_DE_CAMPO = {
    **dict.fromkeys(('descripcion', 'categorias', 'tipos_laboratorio', 'visitas', 'likes', 'ultima_actualizacion'),
                    (CABECERA,)),
    **dict.fromkeys(('nombre', 'nombre_corto', 'codigo', 'descripcion_corta', 'imagen'), (CABECERA, 'unidad')),
    **dict.fromkeys((
        'dependencia', 'estado_catalogo', 'area_conocimiento', 'modo_operacion', 'fecha_inicio', 'administrador',
        'resolucion_numero', 'fecha_resolucion', 'facultad', 'adscrita_a', 'carreras', 'centro_vinculado',
        'horario_atencion', 'capacidad_personas', 'contacto_email', 'telefono', 'celular', 'sitio_web',
        'ubicacion', 'piso', 'direccion', 'latitud', 'longitud', 'mapa_ubicacion',
    ), ('unidad',)),
    'video_unidad': ('presentacion',),
    **dict.fromkeys(('plano_espacios', 'recorrido_espacios_youtube_url', 'recorrido_360_ruta'), ('interior',)),
}

# Campos que solo llevan a otra pantalla: su bloque no guarda datos de la ficha.
CAMPOS_DE_NAVEGACION = frozenset({'contenidos_de_la_ficha', 'contenido_propio'})

# Bloques en línea del editor, por su modelo → claves de sección que alimentan.
SECCIONES_DE_BLOQUE = {
    'PresentacionUnidad': ('unidad',),
    'LineaAccionUnidad': ('unidad',),
    'HitoUnidad': ('unidad',),
    'NovedadUnidad': ('novedades',),
    'ResponsableUnidad': ('unidad',),
    'MedioInterior': ('unidad', 'interior'),
    'EspacioReservable': ('interior', 'areas_equipos', 'reservar', 'visitas'),
    'HorarioOperacionUnidad': ('unidad', 'reservar', 'agenda'),
    'ConfiguracionOperativaUnidad': ('reservar', 'visitas'),
    'CapacidadOperativaUnidad': ('reservar',),
    'BloqueoAgendaUnidad': ('agenda',),
    'SoftwareDisponible': ('software', 'reservar'),
    'ReglamentoUnidad': ('reglamento',),
    'ModuloUnidad': (MENU,),
    'Recurso': (CARPETAS,),
}

# Expedientes de la sección del tipo en el admin → claves de sección que llenan solas.
SECCIONES_DE_EXPEDIENTE = {
    'Adjunto': ('repositorio',),
    'ArtefactoExterno': ('repositorio', 'simuladores', 'recursos_aprendizaje'),
    'Receta': ('sistemas', 'procesos', 'materiales_insumos', 'metodos', 'simuladores', 'documentacion',
               'servicios_industriales', 'capacidad', 'empaque', 'requerimiento'),
    'FamiliaProducto': ('sistemas', 'guias', 'productos', 'fichas_producto', 'protocolos', 'especificaciones',
                        'haccp', 'control_calidad'),
    'Producto': ('sistemas', 'productos', 'fichas_producto', 'empaque'),
    'FichaContenido': ('sistemas', 'fichas_equipo', 'fichas_producto', 'corridas'),
    'GuiaActividadReserva': ('guias', 'mis_guias'),
    'CatalogoActividadReserva': ('cursos', 'proyectos_formativos', 'colaboracion_centros', 'vinculacion'),
    'Asignatura': ('asignaturas',),
    'Curso': ('cursos',),
    'UnidadEquipo': ('areas_equipos', 'fichas_equipo', 'servicios_industriales', 'capacidad'),
    'EquiposServicios': ('fichas_equipo',),
    'OrdenProduccion': ('corridas',),
    'LoteProducto': ('corridas',),
    'PlanCalidad': ('protocolos', 'especificaciones', 'haccp', 'control_calidad'),
    'FablabService': ('servicios', 'visitas'),
    'Reserva': ('reservar', 'agenda', 'proyectos_formativos', 'colaboracion_centros', 'vinculacion'),
}

# Lo que se administra en el panel de la unidad, fuera del admin: vista → (nombre, claves).
SECCIONES_DEL_PANEL = {
    'seguridad': ('Requisitos de acceso (panel de la unidad, Seguridad)', ('requisitos', 'visitas')),
}


def partes_de(claves, mapa):
    """Traduce claves a partes de la ficha de este mapa: sus números más cabecera, menú y carpetas."""
    fijas = [clave for clave in claves if clave in FIJAS]
    if mapa is None:
        return fijas
    return fijas + mapa.numeros([clave for clave in claves if clave not in FIJAS])


def nombre_de_parte(parte, ajustes, mapa):
    """«1.2 La unidad» con el nombre que la unidad le dio, o el de las partes que no son secciones."""
    if parte == CABECERA:
        return 'Cabecera de la ficha'
    if parte == MENU:
        return 'Menú de pestañas'
    if parte == CARPETAS:
        return 'Según su carpeta'
    return f"{parte} {seccion_de(parte, ajustes, mapa)['titulo']}"


def _orden(parte, mapa):
    if parte in (CABECERA, MENU):
        return (0, 0)
    if parte == CARPETAS:
        return (2, 0)
    return (1, list(mapa.secciones).index(parte))


def orden_de_partes(partes, mapa):
    """Dónde va un bloque: primero la cabecera y el menú, luego por sección, después los archivos, al final lo interno."""
    return min((_orden(parte, mapa) for parte in partes), default=(3, 0))


def ancla_de_bloque(nombre):
    return 'bloque-' + slugify(nombre)


def partes_de_campos(campos, mapa):
    """Las partes de la ficha que leen estos campos, en el orden de la ficha."""
    claves = {clave for campo in campos for clave in SECCIONES_DE_CAMPO.get(campo, ())}
    return sorted(partes_de(claves, mapa), key=lambda parte: _orden(parte, mapa))


def partes_de_bloque(modelo, mapa):
    """Las partes de la ficha que alimenta un bloque en línea, por el nombre de su modelo."""
    return partes_de(SECCIONES_DE_BLOQUE.get(modelo, ()), mapa)


def campos_planos(campos):
    for campo in campos:
        if isinstance(campo, (list, tuple)):
            yield from campos_planos(campo)
        else:
            yield campo


def rotulo(nombre, partes, ajustes, mapa):
    """El título del bloque con adónde llega: «1.2 La unidad — Atención»."""
    if not partes:
        return f'Uso interno — {nombre}'
    if len(partes) == 1:
        return f'{nombre_de_parte(partes[0], ajustes, mapa)} — {nombre}'
    etiquetas = ['Cabecera' if parte == CABECERA else parte for parte in partes]
    return f"{', '.join(etiquetas[:-1])} y {etiquetas[-1]} — {nombre}"


def descripcion_de_ruta(partes, ajustes, mapa):
    if not partes:
        return 'No se muestra en la ficha pública: ordena el trabajo interno de la unidad.'
    return 'Se ve en la ficha: ' + '; '.join(nombre_de_parte(parte, ajustes, mapa) for parte in partes) + '.'


def ruta_de_carpeta(carpeta, ajustes, mapa):
    """Pestaña › sección › carpeta superior › carpeta, o None si la carpeta no llega a la ficha."""
    raiz = carpeta.carpeta_padre or carpeta
    nombres = [c.nombre for c in (carpeta.carpeta_padre, carpeta) if c]
    if raiz.ficha_id:
        return ' › '.join([f'Ficha «{raiz.ficha}»', *nombres])
    if raiz.modulo_config_id is None:
        return None
    # En una pestaña común, la carpeta va dentro de una sección numerada; en una pestaña propia, directo en ella.
    if mapa is not None and (raiz.seccion_planta or raiz.modulo_config.clave in mapa.pestanas):
        numero = raiz.seccion_planta
        if numero not in mapa.secciones or mapa.modulo_de(numero) != raiz.modulo_config.clave:
            return None
        return ' › '.join([raiz.modulo_config.nombre, nombre_de_parte(numero, ajustes, mapa), *nombres])
    return ' › '.join([raiz.modulo_config.nombre, *nombres])


def ruta_del_archivo(recurso, ajustes, mapa, ocultas=frozenset()):
    """Dónde aparece un archivo y lo que hoy le impide verse; sin lugares, no aparece en ninguna parte."""
    lugares, avisos = [], []
    carpeta = recurso.carpeta if recurso.carpeta_id else None
    if recurso.ficha_id:
        lugares.append(f'Ficha «{recurso.ficha}»')
    elif carpeta is not None:
        ruta = ruta_de_carpeta(carpeta, ajustes, mapa)
        if ruta:
            lugares.append(ruta)
    elif recurso.tipo_adjunto == 'recorrido_360':
        interior = nombre_de_parte(mapa.numero('interior'), ajustes, mapa) if mapa else 'Ficha'
        lugares.append(f'{interior} › Recorrido 360°')
    lugares.extend(f'Artefacto «{artefacto}»' for artefacto in {
        *recurso.artefactos_externos.all(), *recurso.artefactos_validados.all()})
    # El repositorio reúne lo gobernado de la unidad que no respalda a una ficha.
    if (not recurso.ficha_id and recurso.estado == 'vigente' and recurso.seguridad_verificada
            and recurso.metadatos_completos):
        lugares.append(nombre_de_parte(mapa.numero('repositorio'), ajustes, mapa) if mapa
                       else 'Repositorio de la unidad')
    if not recurso.activo:
        avisos.append('Está inactivo.')
    if carpeta is not None:
        if not carpeta.activa or (carpeta.carpeta_padre_id and not carpeta.carpeta_padre.activa):
            avisos.append('Su carpeta está oculta.')
        raiz = carpeta.carpeta_padre or carpeta
        if raiz.seccion_planta in ocultas:
            avisos.append('Su sección está oculta.')
        if raiz.modulo_config_id and not raiz.modulo_config.activo:
            avisos.append('Su pestaña está oculta.')
    if recurso.visibilidad == 'interna':
        avisos.append('Solo lo ve el personal de la unidad.')
    if recurso.descripcion and not recurso.seguridad_verificada and not recurso.es_microproyecto:
        avisos.append('Espera la verificación de seguridad.')
    return {'lugares': lugares, 'avisos': avisos}


# Grupos del editor de una unidad, en su orden: el editor muestra uno a la vez para no abrumar.
# (clave, título, qué reúne, ícono)
GRUPOS_EDITOR = (
    ('unidad', 'Identidad y contacto', 'Nombre, clasificación, fechas, atención, ubicación y responsables.',
     'building'),
    ('presentacion', 'Presentación', 'Imagen, video, «Conoce la unidad» y las novedades que publica.',
     'academic'),
    ('espacios', 'Espacios y recorridos', 'Áreas, plano, recorridos en video y 360°, y fotos por área.',
     'inventory'),
    ('reservas', 'Reservas y reglamento',
     'Configuración, horarios, capacidad, cierres de agenda, software y reglamento.', 'calendar'),
    ('contenidos', 'Pestañas y archivos', 'Las pestañas del menú y los archivos; la carpeta decide dónde se ve cada uno.',
     'file'),
    ('pantallas', 'Registros que alimentan la ficha', 'Se editan en sus propias listas; aquí están los accesos.',
     'reports'),
    ('interno', 'Reglas internas', 'Cómo opera la unidad; no se muestra en la ficha pública.',
     'maintenance'),
)

# Las secciones que alimenta cada grupo, en la numeración de cada tipo de unidad.
SECCIONES_DE_GRUPO = {
    'plantas_piloto': {'unidad': 'Cabecera y 1.2', 'presentacion': '1.1, 1.2 y 1.6', 'espacios': '1.3, 3.1 y 6.7',
                       'reservas': '6.1 a 6.7', 'contenidos': 'Menú y carpetas', 'pantallas': '2 a 5',
                       'interno': 'Fuera de la ficha'},
    'laboratorios': {'unidad': 'Cabecera y 1.2', 'presentacion': '1.1, 1.2 y 1.6', 'espacios': '1.3, 2.1 y 5.7',
                     'reservas': '5.1 a 5.7', 'contenidos': 'Menú y carpetas', 'pantallas': '2, 3, 4 y 6',
                     'interno': 'Fuera de la ficha'},
}


def grupos_editor(mapa):
    """Los grupos del editor con las secciones que alimentan en el mapa de esta unidad."""
    etiquetas = SECCIONES_DE_GRUPO.get(mapa.tipo, {}) if mapa else {}
    return [{'clave': clave, 'titulo': titulo, 'descripcion': descripcion, 'icono': icono,
             'secciones': etiquetas.get(clave, '')}
            for clave, titulo, descripcion, icono in GRUPOS_EDITOR]


GRUPO_DE_CAMPO = {
    **dict.fromkeys(('imagen', 'video_unidad'), 'presentacion'),
    **dict.fromkeys(('plano_espacios', 'recorrido_espacios_youtube_url', 'recorrido_360_ruta'), 'espacios'),
    'contenido_propio': 'pantallas',
}

GRUPO_DE_BLOQUE = {
    'ResponsableUnidad': 'unidad',
    **dict.fromkeys(('PresentacionUnidad', 'LineaAccionUnidad', 'HitoUnidad', 'NovedadUnidad'), 'presentacion'),
    **dict.fromkeys(('MedioInterior', 'EspacioReservable'), 'espacios'),
    **dict.fromkeys(('ConfiguracionOperativaUnidad', 'HorarioOperacionUnidad', 'CapacidadOperativaUnidad',
                     'BloqueoAgendaUnidad', 'SoftwareDisponible', 'ReglamentoUnidad'), 'reservas'),
    **dict.fromkeys(('ModuloUnidad', 'Recurso'), 'contenidos'),
}


def grupo_de_campos(campos):
    """El grupo de un bloque de campos: lo decide su campo más específico; el resto es identidad."""
    return next((GRUPO_DE_CAMPO[campo] for campo in campos if campo in GRUPO_DE_CAMPO), 'unidad')


def grupo_de_bloque(modelo):
    """El grupo de un bloque en línea por su modelo; lo no mapeado (perfiles operativos) es interno."""
    return GRUPO_DE_BLOQUE.get(modelo, 'interno')


def orden_de_grupo(grupo):
    return [clave for clave, *_ in GRUPOS_EDITOR].index(grupo)
