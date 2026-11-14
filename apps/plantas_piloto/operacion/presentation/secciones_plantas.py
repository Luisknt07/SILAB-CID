"""Mapa canónico de la ficha pública de cada tipo de unidad: pestañas y secciones numeradas.

Cada tipo con mapa (plantas piloto, laboratorios, observatorios y centros experimentales) comparte la misma
estructura entre sus unidades; la plataforma llena las secciones con sus datos y cada unidad solo
las renombra u oculta. El árbol conserva las secciones aunque todavía no tengan contenido:
en ese caso muestra el estado pendiente, sin inventar contenido técnico.

Cada sección tiene un número (lo que ve el visitante), un título común y una clave
estable (lo que usa el código): la misma clave puede tener distinto número en cada
mapa, por ejemplo «guias» es 2.6 en una planta y 4.1 en un laboratorio.
"""

from collections import OrderedDict


class Mapa:
    """Las pestañas y secciones de un tipo de unidad, con acceso por número y por clave."""

    def __init__(self, tipo, app_label, pestanas, origen):
        self.tipo = tipo
        self.app_label = app_label
        # Compatibilidad con quien lee (titulo, ((numero, titulo), ...)) por pestaña.
        self.pestanas = OrderedDict(
            (modulo, (titulo, tuple((numero, nombre) for numero, nombre, _clave in secciones)))
            for modulo, (titulo, secciones) in pestanas.items()
        )
        self.secciones = OrderedDict(
            (numero, {'numero': numero, 'titulo': nombre, 'modulo': modulo, 'clave': clave})
            for modulo, (_titulo, secciones) in pestanas.items()
            for numero, nombre, clave in secciones
        )
        self.claves = {seccion['clave']: numero for numero, seccion in self.secciones.items()}
        self.origen = origen

    def numero(self, clave):
        """El número de una clave en este mapa, o '' si el mapa no tiene esa sección."""
        return self.claves.get(clave, '')

    def numeros(self, claves):
        return [self.claves[clave] for clave in claves if clave in self.claves]

    def modulo_de(self, numero):
        return self.secciones[numero]['modulo']

    @property
    def modulo_reservas(self):
        """La pestaña que la plantilla dibuja con las herramientas de reserva; '' si el tipo no reserva (observatorios)."""
        return self.modulo_de(self.claves['reservar']) if 'reservar' in self.claves else ''


_PLANTA = OrderedDict((
    ('informacion-general', ('Información general', (
        ('1.1', 'Presentación', 'presentacion'),
        ('1.2', 'La unidad', 'unidad'),
        ('1.3', 'La planta por dentro', 'interior'),
        ('1.4', 'Normativa y marco sanitario', 'normativa'),
        ('1.5', 'Repositorio y descargas', 'repositorio'),
        ('1.6', 'Novedades y avisos', 'novedades'),
    ))),
    ('procesos-protocolos', ('Procesos y protocolos', (
        ('2.1', 'Sistemas de producción', 'sistemas'),
        ('2.2', 'Materiales e insumos', 'materiales_insumos'),
        ('2.3', 'Métodos y tiempos', 'metodos'),
        ('2.4', 'Simuladores y cálculo del proceso', 'simuladores'),
        ('2.5', 'Documentación de los procesos', 'documentacion'),
        ('2.6', 'Guías de práctica', 'guias'),
    ))),
    ('equipos-infraestructura', ('Equipos e infraestructura', (
        ('3.1', 'Áreas y equipos', 'areas_equipos'),
        ('3.2', 'Fichas de equipo', 'fichas_equipo'),
        ('3.3', 'Servicios industriales', 'servicios_industriales'),
        ('3.4', 'Capacidad, cuellos de botella y equilibrado', 'capacidad'),
    ))),
    ('produccion-lotes', ('Producción y lotes', (
        ('4.1', 'Lo que produce la planta', 'productos'),
        ('4.2', 'Fichas técnicas de producto', 'fichas_producto'),
        ('4.3', 'Empaque y presentación', 'empaque'),
        ('4.4', 'Requerimiento de materiales', 'requerimiento'),
        ('4.5', 'Corridas y lotes', 'corridas'),
        ('4.6', 'Desarrollo de producto', 'desarrollo'),
    ))),
    ('calidad-inocuidad', ('Calidad e inocuidad', (
        ('5.1', 'Protocolos de control', 'protocolos'),
        ('5.2', 'Especificaciones', 'especificaciones'),
        ('5.3', 'Plan HACCP', 'haccp'),
        ('5.4', 'Control de calidad y requisitos', 'control_calidad'),
        ('5.5', 'Buenas prácticas', 'buenas_practicas'),
    ))),
    ('reservas-servicios', ('Reservas y servicios', (
        ('6.1', 'Reservar la unidad', 'reservar'),
        ('6.2', 'Catálogo de servicios y tarifas', 'servicios'),
        ('6.3', 'Agenda y disponibilidad', 'agenda'),
        ('6.4', 'Requisitos de acceso', 'requisitos'),
        ('6.5', 'Mis guías de práctica', 'mis_guias'),
        ('6.6', 'Reglamento de uso', 'reglamento'),
        ('6.7', 'Visitas y uso de la unidad', 'visitas'),
    ))),
))

_LABORATORIO = OrderedDict((
    ('informacion-general', ('Información general', (
        ('1.1', 'Presentación', 'presentacion'),
        ('1.2', 'El laboratorio', 'unidad'),
        ('1.3', 'El laboratorio por dentro', 'interior'),
        ('1.4', 'Normativa y seguridad', 'normativa'),
        ('1.5', 'Repositorio y descargas', 'repositorio'),
        ('1.6', 'Novedades y avisos', 'novedades'),
    ))),
    ('areas-equipos', ('Áreas y equipos', (
        ('2.1', 'Áreas del laboratorio', 'areas_equipos'),
        ('2.2', 'Equipos y fichas técnicas', 'fichas_equipo'),
        ('2.3', 'Software y plataformas', 'software'),
        ('2.4', 'Materiales e insumos', 'materiales'),
    ))),
    ('procesos-productos', ('Procesos y productos', (
        ('3.1', 'Procesos y protocolos', 'procesos'),
        ('3.2', 'Métodos, normas y especificaciones', 'metodos'),
        ('3.3', 'Productos y resultados', 'productos'),
    ))),
    ('docencia-capacitacion', ('Docencia y capacitación', (
        ('4.1', 'Guías de práctica', 'guias'),
        ('4.2', 'Asignaturas y carreras que atiende', 'asignaturas'),
        ('4.3', 'Cursos y capacitaciones', 'cursos'),
        ('4.4', 'Recursos de aprendizaje y simuladores', 'recursos_aprendizaje'),
    ))),
    ('reservas-servicios', ('Reservas y servicios', (
        ('5.1', 'Reservar el laboratorio', 'reservar'),
        ('5.2', 'Servicios y tarifas', 'servicios'),
        ('5.3', 'Agenda y disponibilidad', 'agenda'),
        ('5.4', 'Requisitos de acceso', 'requisitos'),
        ('5.5', 'Mis guías de práctica', 'mis_guias'),
        ('5.6', 'Reglamento de uso', 'reglamento'),
        ('5.7', 'Visitas y uso del laboratorio', 'visitas'),
    ))),
    # Investigación formativa: la científica es de los centros de I+D, con los que el laboratorio colabora.
    ('investigacion-formativa', ('Investigación formativa y vinculación', (
        ('6.1', 'Proyectos formativos', 'proyectos_formativos'),
        ('6.2', 'Colaboración con centros de I+D', 'colaboracion_centros'),
        ('6.3', 'Resultados', 'resultados'),
        ('6.4', 'Vinculación y convenios', 'vinculacion'),
    ))),
))
# La pestaña que solo muestran los laboratorios cuyo modo de uso incluye investigación.
PESTANA_INVESTIGACION = 'investigacion-formativa'

# Un observatorio produce información para decidir: indicadores con ficha, series, boletines y alertas. También tiene
# su espacio de trabajo (sala de análisis, estaciones), equipos y software, que se reservan y se visitan como en un
# laboratorio, y ofrece capacitaciones; lo que no hace (analizar muestras, producir) lo explica la sección 1.4.
_OBSERVATORIO = OrderedDict((
    ('informacion-general', ('Información general', (
        ('1.1', 'Presentación', 'presentacion'),
        ('1.2', 'El observatorio', 'unidad'),
        ('1.3', 'Ejes temáticos', 'lineas'),
        ('1.4', 'Qué ofrece y qué no', 'oferta'),
        ('1.5', 'Política de datos y acceso', 'politica_datos'),
    ))),
    ('datos-indicadores', ('Datos y monitoreo', (
        ('2.1', 'Indicadores por eje', 'indicadores'),
        ('2.2', 'Alertas y criterios', 'alertas'),
        ('2.3', 'Tableros y mapas', 'tableros'),
        ('2.4', 'Visores de otras instituciones', 'visores'),
        ('2.5', 'Datos abiertos e históricos', 'datos'),
        ('2.6', 'Fichas metodológicas', 'fichas_metodologicas'),
        ('2.7', 'Fuentes y actualización', 'fuentes'),
    ))),
    ('reportes-publicaciones', ('Reportes y publicaciones', (
        ('3.1', 'Boletín de indicadores', 'boletines'),
        ('3.2', 'Reportes por eje e informes', 'informes'),
        ('3.3', 'Calendario de publicaciones', 'calendario'),
    ))),
    ('investigacion-vinculacion', ('Investigación y vinculación', (
        ('4.1', 'Temas de investigación y estudios', 'estudios'),
        ('4.2', 'Encuestas y levantamientos propios', 'encuestas'),
        ('4.3', 'Aliados y convenios', 'aliados'),
        ('4.4', 'Participa: prácticas, tesis y encuestas', 'participa'),
        ('4.5', 'Uso e impacto de los datos', 'impacto'),
    ))),
    ('acceso-servicios', ('Acceso y servicios', (
        ('5.1', 'Solicitar datos o un análisis', 'solicitudes'),
        ('5.2', 'Estudios y servicios con tarifa', 'servicios_datos'),
        ('5.3', 'Datos abiertos y API', 'api_datos'),
        ('5.4', 'Cursos y capacitaciones', 'cursos'),
        ('5.5', 'Sala, equipos y visitas', 'sala'),
    ))),
))

# Un centro experimental es una finca que produce y experimenta a la vez: su trabajo se organiza en ejes productivos
# (ganadería de leche, café, frutales…), cada uno con su página como las áreas de un laboratorio; lo que produce va a
# las plantas piloto, a la venta o a las prácticas, y se reserva para prácticas, recorridos y servicios.
_CENTRO = OrderedDict((
    ('informacion-general', ('Información general', (
        ('1.1', 'Presentación', 'presentacion'),
        ('1.2', 'El centro', 'unidad'),
        ('1.3', 'El centro por dentro', 'interior'),
        ('1.4', 'Cómo funciona el centro', 'funcionamiento'),
        ('1.5', 'Repositorio y descargas', 'repositorio'),
        ('1.6', 'Novedades y avisos', 'novedades'),
    ))),
    ('areas-productivas', ('Áreas y sistemas productivos', (
        ('2.1', 'Ejes productivos', 'ejes'),
        ('2.2', 'Calendario productivo', 'calendario_productivo'),
        ('2.3', 'Simuladores de producción', 'simuladores_campo'),
    ))),
    ('produccion-ensayos', ('Producción y ensayos', (
        ('3.1', 'Plan y registros de producción', 'registros_produccion'),
        ('3.2', 'Ensayos de campo', 'ensayos'),
        ('3.3', 'Guías de práctica', 'guias'),
        ('3.4', 'A dónde va lo que produce', 'destino'),
    ))),
    ('infraestructura-equipos', ('Infraestructura y equipos', (
        ('4.1', 'Áreas e instalaciones', 'areas_equipos'),
        ('4.2', 'Fichas de equipo', 'fichas_equipo'),
    ))),
    ('investigacion-vinculacion', ('Investigación y vinculación', (
        ('5.1', 'Temas de investigación', 'temas_investigacion'),
        ('5.2', 'Cursos y capacitaciones', 'cursos'),
        ('5.3', 'Unidades relacionadas', 'relaciones'),
    ))),
    ('visitas-servicios', ('Visitas y servicios', (
        ('6.1', 'Cómo se reserva, por eje', 'como_reservar'),
        ('6.2', 'Reservar el centro', 'reservar'),
        ('6.3', 'Servicios y tarifas', 'servicios'),
        ('6.4', 'Agenda y disponibilidad', 'agenda'),
        ('6.5', 'Requisitos de acceso', 'requisitos'),
        ('6.6', 'Recorridos y visitas', 'visitas'),
        ('6.7', 'Reglamento de uso', 'reglamento'),
    ))),
))

# De dónde sale lo que la plataforma pone sola en cada sección; lo explica el organizador del admin.
_ORIGEN_COMUN = {
    'presentacion': 'El video de presentación de la unidad o, si no tiene, el institucional.',
    'unidad': 'Conoce la unidad, la ficha de identidad y contacto, y la ubicación en el mapa.',
    'interior': 'Plano y recorrido en video, galería de fotos y videos por área, y recorrido 360°.',
    'normativa': 'Ninguno: se llena solo con carpetas propias.',
    'repositorio': 'El repositorio institucional: adjuntos gobernados y artefactos generales.',
    'novedades': 'Las novedades publicadas por la unidad: noticias, logros, eventos y convocatorias.',
    'guias': 'Las guías de práctica aprobadas.',
    'areas_equipos': 'Las áreas con sus equipos, software, recursos en línea y responsable.',
    'fichas_equipo': 'La ficha técnica de cada equipo.',
    'reservar': 'El sistema de reservas y las reservas de quien entra.',
    'servicios': 'El catálogo de servicios con sus tarifas.',
    'agenda': 'La agenda y la disponibilidad de la unidad.',
    'requisitos': 'Los requisitos para ingresar.',
    'mis_guias': 'Las guías de práctica de quien inicia sesión.',
    'reglamento': 'El reglamento de uso.',
    'visitas': 'La oferta de visitas guiadas; solo la ve quien gestiona la unidad.',
}
_ORIGEN_PLANTA = {
    **_ORIGEN_COMUN,
    'sistemas': 'Las fichas de proceso de cada producto, agrupadas por línea.',
    'materiales_insumos': 'La matriz de materiales e insumos de los procesos.',
    'metodos': 'Los métodos, tiempos y secuencia de cada proceso.',
    'simuladores': 'Los simuladores y el cálculo de cada proceso.',
    'documentacion': 'La ruta del saber y la documentación técnica de los procesos.',
    'guias': 'Las guías de práctica aprobadas, por línea de producto.',
    'servicios_industriales': 'Los servicios industriales que piden equipos y procesos.',
    'capacidad': 'La capacidad, los cuellos de botella y el equilibrado de la línea.',
    'productos': 'Los productos de la planta.',
    'fichas_producto': 'Las fichas técnicas de producto.',
    'empaque': 'El empaque y la presentación de cada producto.',
    'requerimiento': 'El requerimiento de materiales de la producción.',
    'corridas': 'Las corridas de producción y sus lotes.',
    'desarrollo': 'Ninguno: se llena solo con carpetas propias.',
    'protocolos': 'Los protocolos de control de los planes de calidad.',
    'especificaciones': 'Las especificaciones de producto.',
    'haccp': 'El plan HACCP.',
    'control_calidad': 'El control de calidad y sus requisitos.',
    'buenas_practicas': 'Ninguno: se llena solo con carpetas propias.',
}
_ORIGEN_LABORATORIO = {
    **_ORIGEN_COMUN,
    'software': 'El software y las plataformas disponibles en el laboratorio.',
    'materiales': 'Ninguno por ahora: se llena con carpetas propias.',
    'procesos': 'Los procesos activos de la unidad, cada uno paso a paso con sus equipos, insumos y controles.',
    'metodos': 'Cómo se hace cada etapa de los procesos y qué parámetros se controlan.',
    'productos': 'Los productos y servicios públicos de la unidad, con el proceso que los entrega.',
    'asignaturas': 'Las asignaturas y carreras registradas que usan el laboratorio.',
    'cursos': 'Los cursos, talleres e inducciones publicados en el catálogo de actividades.',
    'recursos_aprendizaje': 'Los simuladores, sitios interactivos y artefactos publicados, agrupados por área.',
    'proyectos_formativos': 'Las reservas aprobadas de titulación, semilleros, proyectos integradores e innovación.',
    'colaboracion_centros': 'Las reservas aprobadas de centros y grupos de investigación.',
    'resultados': 'Ninguno: se llena solo con carpetas propias.',
    'vinculacion': 'Las reservas aprobadas de vinculación y transferencia.',
}
_ORIGEN_OBSERVATORIO = {
    **{clave: _ORIGEN_COMUN[clave] for clave in ('presentacion', 'unidad')},
    'lineas': 'Los ejes temáticos: qué estudia cada uno, qué aporta, cómo trabaja, sus datos, fotos y videos.',
    'oferta': 'Lo que el observatorio ofrece y lo que no, con enlace a cada servicio y las capacitaciones que dicta.',
    'politica_datos': 'Qué datos son abiertos, cuáles se piden o requieren convenio, cuáles nunca se entregan y qué se cobra.',
    'indicadores': 'Los indicadores publicados, agrupados por eje temático, con su último valor y su tendencia.',
    'tableros': 'Los tableros armados con los datos del observatorio: series, semáforo, comparación y mapa cantonal.',
    'visores': 'Los tableros de otras instituciones insertados, con su fecha de corte y sus datos descargables.',
    'datos': 'Las series completas en CSV y JSON, con licencia abierta, y el historial de correcciones.',
    'fichas_metodologicas': 'La ficha de cada indicador: definición, fórmula, unidad, fuente, periodicidad y límites.',
    'alertas': 'Las alertas activas y el estado de cada indicador vigilado frente a su umbral.',
    'umbrales': 'Los umbrales definidos para cada indicador, de dónde salen y qué significa cruzarlos.',
    'actualizaciones': 'Los últimos valores que entraron, de qué fuente y por qué vía (automática, plantilla o registro).',
    'fuentes': 'El catálogo de fuentes y bases de datos, las conexiones automáticas y los últimos valores que entraron.',
    'boletines': 'El boletín que se genera con los indicadores vigentes y los boletines publicados.',
    'informes': 'El reporte de cada eje en PDF, generado con sus datos, y los informes y notas publicados.',
    'calendario': 'El calendario de publicaciones: lo planificado y lo cumplido.',
    'estudios': 'Los temas de investigación abiertos por eje y los estudios publicados por el observatorio.',
    'encuestas': 'Las encuestas y levantamientos propios con su metodología, los activos y los que están en diseño.',
    'aliados': 'Las instituciones aliadas y los convenios de datos.',
    'participa': 'Cómo sumarse: prácticas, vinculación, encuestas activas y temas de tesis con los datos que faltan.',
    'impacto': 'Las descargas por formato y mes, las solicitudes atendidas y el cumplimiento del calendario.',
    'solicitudes': 'El formulario para pedir datos, un análisis o el uso de la sala, y las solicitudes de quien entra.',
    'servicios_datos': 'Los estudios y servicios que se cobran (nunca el dato) y cómo pedir una cotización.',
    'api_datos': 'Los datos abiertos del observatorio en CSV y JSON, con su licencia.',
    'cursos': 'Los cursos publicados o, mientras no los haya, las capacitaciones que el observatorio puede dictar.',
    'sala': 'La sala de análisis, sus equipos y software, cómo pedir su uso y las visitas guiadas.',
}


_ORIGEN_CENTRO = {
    **_ORIGEN_COMUN,
    'funcionamiento': 'Quién hace qué (por rol), el ciclo de producción, los datos del centro, sus ejes y cómo se usa.',
    'ejes': 'Los ejes productivos: qué produce cada uno, cómo trabaja, sus áreas, a dónde va, fotos y videos.',
    'calendario_productivo': 'Lo que hace cada eje en cada temporada, tomado del calendario de cada eje.',
    'simuladores_campo': 'Los simuladores de producción del centro, cuando se publiquen.',
    'registros_produccion': 'El plan y los registros de producción de cada eje, cuando el centro los lleve.',
    'ensayos': 'Ninguno: se llena solo con carpetas propias.',
    'destino': 'Las plantas piloto que abastece el centro y el destino de lo que produce cada eje.',
    'temas_investigacion': 'Los temas de investigación abiertos de cada eje, con sus prácticas.',
    'cursos': 'Los cursos, talleres e inducciones publicados en el catálogo de actividades.',
    'relaciones': 'Las plantas que aloja y abastece, y los laboratorios y observatorios que trabajan con él.',
    'areas_equipos': 'Las áreas, potreros, parcelas e instalaciones del centro, con sus equipos y responsable.',
    'visitas': 'La oferta de recorridos y visitas guiadas; solo la ve quien gestiona la unidad.',
    'como_reservar': 'Qué se reserva en cada eje (prácticas, ensayos, recorridos, cursos), los pasos y los cuidados.',
}


def _origen_por_numero(pestanas, origen_por_clave):
    return {numero: origen_por_clave[clave]
            for _modulo, (_titulo, secciones) in pestanas.items() for numero, _nombre, clave in secciones}


MAPA_PLANTA = Mapa('plantas_piloto', 'plantas_piloto', _PLANTA, _origen_por_numero(_PLANTA, _ORIGEN_PLANTA))
MAPA_LABORATORIO = Mapa('laboratorios', 'laboratorios', _LABORATORIO,
                        _origen_por_numero(_LABORATORIO, _ORIGEN_LABORATORIO))
MAPA_OBSERVATORIO = Mapa('observatorios', 'observatorios', _OBSERVATORIO,
                         _origen_por_numero(_OBSERVATORIO, _ORIGEN_OBSERVATORIO))
MAPA_CENTRO = Mapa('centro_experimental', 'centros_experimentales', _CENTRO,
                  _origen_por_numero(_CENTRO, _ORIGEN_CENTRO))
MAPAS = {MAPA_PLANTA.tipo: MAPA_PLANTA, MAPA_LABORATORIO.tipo: MAPA_LABORATORIO,
         MAPA_OBSERVATORIO.tipo: MAPA_OBSERVATORIO, MAPA_CENTRO.tipo: MAPA_CENTRO}

# Lo que el resto del código conoce de las plantas, con el mismo nombre de siempre.
PESTANAS_PLANTA = MAPA_PLANTA.pestanas
SECCIONES_PLANTA = MAPA_PLANTA.secciones
ORIGEN_SECCIONES = MAPA_PLANTA.origen

# Todos los números que existen en algún mapa: lo que puede guardar un ajuste o una carpeta.
NUMEROS_DE_SECCION = sorted({numero for mapa in MAPAS.values() for numero in mapa.secciones},
                            key=lambda numero: tuple(int(parte) for parte in numero.split('.')))


def mapa_por_tipo(codigo_base):
    """El mapa de un tipo de unidad, o None si ese tipo no tiene ficha numerada."""
    return MAPAS.get(codigo_base)


def mapa_de(unidad):
    """El mapa que le corresponde a una unidad, o None si su tipo no tiene ficha numerada."""
    if unidad is None:
        return None
    return mapa_por_tipo(getattr(unidad, 'codigo_base', None) or unidad.dependencia)


def seccion_planta(numero):
    """Devuelve la definición oficial de una planta; un número desconocido es un error de código."""
    return SECCIONES_PLANTA[numero]


def ajustes_de(unidad):
    """El nombre propio y la visibilidad que la unidad dio a sus secciones, por número."""
    from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
    return {ajuste.numero: ajuste for ajuste in AjusteSeccionPlanta.objects.filter(unidad=unidad)}


def secciones_ocultas(unidad):
    """Los números de las secciones que la unidad sacó de su ficha."""
    from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
    return set(AjusteSeccionPlanta.objects.filter(unidad=unidad, oculta=True).values_list('numero', flat=True))


def seccion_de(numero, ajustes, mapa=MAPA_PLANTA):
    """La sección con el nombre y la visibilidad de la unidad; la estructura común no cambia."""
    ajuste = ajustes.get(numero)
    comun = mapa.secciones[numero]
    return {
        **comun,
        'titulo': ajuste.titulo if ajuste and ajuste.titulo else comun['titulo'],
        'oculta': bool(ajuste and ajuste.oculta),
    }


def secciones_con_nombre(unidad, ajustes, mapa=None):
    """Las secciones de la unidad por clave, listas para la plantilla; vacío sin mapa."""
    mapa = mapa or mapa_de(unidad)
    if mapa is None:
        return {}
    return {clave: seccion_de(numero, ajustes, mapa) for clave, numero in mapa.claves.items()}
