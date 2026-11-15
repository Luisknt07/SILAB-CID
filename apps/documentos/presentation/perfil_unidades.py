"""Alcance del expediente según las funciones de cada tipo de unidad.

El catálogo explícito de la institución tiene prioridad. Los perfiles sólo
ajustan las definiciones estándar que antes se proponían a todas las unidades;
no reescriben el catálogo ni eliminan documentos que ya fueron enviados.
"""
BASES_AUDITABLES = frozenset(('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'))

# El observatorio no tiene meta de uso de sesiones (politica_metas_unidades): sus
# atenciones se consultan en el Centro de reportes, sin un anexo que respalde nada.
EXCLUIDOS_POR_BASE = {
    'observatorios': frozenset(('REGISTRO-USO', 'PRACTICAS-FT02',
                               'PRACTICAS-FT03', 'GUIAS', 'INDUCCION-SEGURIDAD', 'DESECHOS')),
}

NOMBRES_POR_BASE = {
    'plantas_piloto': {
        'PLANIFICACION': 'Planificación semestral de producción, prácticas y servicios de la planta piloto',
        'INFORME-SEMESTRAL': 'Informe semestral de producción, prácticas y cumplimiento de la planta piloto',
        'REGISTRO-USO': 'Uso de la planta piloto: sesiones, horas y usuarios',
        'EQUIPAMIENTO': 'Equipos e inventario de la planta piloto: revisión física, mantenimiento y existencias',
        'INVESTIGACION': 'Investigación y vinculación de la planta piloto: resultados, entregas y servicios',
    },
    'centro_experimental': {
        'PLANIFICACION': 'Planificación semestral de actividades de campo y ensayos del centro experimental',
        'INFORME-SEMESTRAL': 'Informe semestral de actividades de campo, ensayos y cumplimiento',
        'REGISTRO-USO': 'Uso de los escenarios experimentales: sesiones, horas y usuarios',
        'EQUIPAMIENTO': 'Equipos e inventario del centro experimental: revisión física, mantenimiento y existencias',
        'INVESTIGACION': 'Investigación y vinculación del centro experimental: resultados, entregas y servicios',
    },
    'observatorios': {
        'PLANIFICACION': 'Planificación semestral de indicadores, publicaciones y servicios del observatorio',
        'INFORME-SEMESTRAL': 'Informe semestral de datos, publicaciones y cumplimiento del observatorio',
        # Nombre de su consulta de atenciones; no es anexo del observatorio.
        'REGISTRO-USO': 'Registro de atenciones y uso de espacios del observatorio',
        'EQUIPAMIENTO': 'Equipos e inventario del observatorio: revisión física, mantenimiento y software',
        'INVESTIGACION': 'Investigación y vinculación del observatorio: resultados, entrega de información y servicios',
    },
}

# Consultas de gestión con nombre propio del perfil: ya no son anexos del
# expediente, pero conservan la denominación de la unidad en el Centro de reportes.
NOMBRES_CONSULTAS_POR_BASE = {
    'plantas_piloto': {
        'asignaturas': 'Planificación semestral de prácticas y procesos de la planta piloto',
        'inventario': 'Materias primas e insumos: lotes, existencias y movimientos',
    },
    'centro_experimental': {
        'asignaturas': 'Planificación semestral de prácticas en escenarios experimentales',
        'inventario': 'Insumos de campo: lotes, existencias y movimientos',
    },
}

# Contenido verificable del documento, sin inventar cuotas ni atribuir estas
# orientaciones a una norma universitaria. Los perfiles especializan lo común.
REQUISITOS_COMUNES = {
    'RESOLUCION-CREACION': ('Resolución correspondiente a la unidad, con autoridad, número, fecha y alcance.',),
    'PROTOCOLO-BIOSEGURIDAD': ('Alcance, responsables, peligros y controles según las actividades de la unidad.',
                              'Acceso, operación, emergencias y actualización; medidas específicas sólo cuando apliquen.'),
    'PLAN-COMPRAS-ANUAL': ('Necesidades del año siguiente, cantidades, costos estimados, prioridad y financiamiento.',
                          'Justificación frente a recursos, capacidad y actividades; revisión, emisión y aprobación en la plataforma.'),
    'REGISTRO-USO': ('Sesiones registradas y atendidas, horas de uso efectivo, usuarios y propósito.',
                     'Detalle de las sesiones atendidas; las que no se cerraron se cuentan aparte, sin sumarlas al uso.'),
    'PRACTICAS-FT02': ('Prácticas aprobadas con asignatura, escenario, fecha, docente y guía; prácticas ejecutadas '
                       'con asistencia y evidencia.',
                       'Guías vigentes, aprobadas y vinculadas al syllabus; lo que falta a cada registro para contar.'),
    'PRACTICAS-FT03': ('Referencia a la planificación, ejecución, asistencia, bitácora y resultados.',
                       'Evidencias de la sesión identificadas y evaluación; diferenciar registros pendientes y prácticas validadas.'),
    'GUIAS': ('Guía vigente, responsables de elaboración, revisión y aprobación.',
              'Asignatura, tema y resultado de aprendizaje vinculados con el syllabus; el listado no sustituye cada guía.'),
    'INDUCCION-SEGURIDAD': ('Inducciones de usuarios nuevos e inspecciones mensuales, con su respaldo.',
                            'Desechos generados con cantidad, almacenamiento, responsable y entrega al gestor autorizado.'),
    'DESECHOS': ('Desechos realmente generados: tipo, origen, cantidad, fecha, responsable y almacenamiento.',
                 'Entrega y respaldo de recepción cuando corresponda; una ausencia de registros no demuestra que no hubo generación.'),
    'EQUIPAMIENTO': ('Acta de revisión física del inventario y datos pendientes de los equipos.',
                     'Mantenimientos frente al programa crítico, equipos fuera de servicio e insumos bajo su mínimo.'),
    'INVENTARIO-CORTE': ('Equipos, software, espacios e insumos aplicables, con custodio, ubicación y condición.',
                         'Fecha del corte, revisión física y diferencias respaldadas; existencias, lotes y movimientos '
                         'de insumos del período cuando apliquen.'),
    'INVESTIGACION': ('Solo si el plan lo compromete: productos de investigación con proyecto, responsable y respaldo.',
                       'Transferencias y servicios entregados y aceptados; una solicitud o reserva no es un resultado.'),
    'TRANSFERENCIA': ('Producto o servicio entregado, responsable, destinatario y fecha.',
                       'Evidencia de entrega y aceptación; separar solicitudes, actividades programadas y resultados obtenidos.'),
    'ACCIONES-MEJORA': ('Hallazgo o compromiso, acción, responsable, plazo, estado y evidencia de cierre.',
                        'Distinguir los compromisos ordinarios del informe semestral y las acciones del trámite de mejora, cuando exista.'),
}

REQUISITOS_POR_BASE = {
    'plantas_piloto': {
        'PLANIFICACION': ('Productos, procesos, prácticas y servicios previstos, con metas, responsables y fechas.',
                         'Capacidad de equipos y personal, materias primas, limpieza, controles de calidad y recursos previstos.'),
        'INFORME-SEMESTRAL': ('Órdenes y lotes ejecutados frente al plan, rendimientos, consumos, mermas y causas de diferencias.',
                             'Trazabilidad de materias primas y entregas; calidad, no conformidades y acciones respaldadas.'),
        'PP-PRODUCCION': ('Órdenes y lotes del período, producto, fecha, cantidades y estado real.',
                          'Origen de insumos, consumos, salidas y destinatarios; distinguir producción de ventas y entregas.'),
        'PP-CALIDAD': ('Parámetros y límites del plan de calidad, mediciones, fecha, lote y responsable.',
                      'Resultados, liberación o rechazo, no conformidades y seguimiento de acciones.'),
    },
    'centro_experimental': {
        'PLANIFICACION': ('Prácticas, ensayos y ciclos previstos, con área o escenario, responsable y calendario.',
                         'Capacidad de parcelas, instalaciones, equipos, personal e insumos; manejo y seguridad propios de las actividades.'),
        'INFORME-SEMESTRAL': ('Actividades de campo, ensayos y ciclos realizados frente al plan, sin mezclar unidades de medida.',
                             'Registros de manejo, mediciones, resultados, incidencias y entregas con respaldo.'),
        'CE-ENSAYOS': ('Objetivo y diseño del ensayo, ubicación o parcela, fechas y responsable.',
                      'Tratamientos o manejo, variables medidas, registros de campo, resultados y evidencia identificada.'),
    },
    'observatorios': {
        'PROTOCOLO-BIOSEGURIDAD': ('Alcance, responsables y controles para instalaciones, información y equipos informáticos.',
                                  'Acceso, uso de recursos, respaldo de información y respuesta ante incidentes; bioseguridad sólo si la actividad lo requiere.'),
        'PLANIFICACION': ('Indicadores y fuentes que se actualizarán, periodicidad, responsables y calendario de publicaciones.',
                         'Metodología, acceso a datos, recursos de análisis y servicios o eventos de vinculación previstos.'),
        'INFORME-SEMESTRAL': ('Actualizaciones y publicaciones realizadas frente al calendario, con fuentes y períodos de referencia.',
                             'Calidad y limitaciones del dato, productos verificables, solicitudes atendidas y acciones de mejora.'),
        'OBS-DATOS': ('Ficha del indicador: definición, fórmula, unidad, ámbito, periodicidad y responsable.',
                      'Fuente identificada, método y fecha de actualización; valor, período y territorio, limitaciones y trazabilidad de la revisión.'),
        'OBS-BOLETINES': ('Publicación, tipo, fecha prevista y fecha real, autor o responsable y alcance.',
                         'Archivo o enlace verificable, fuentes citadas e indicadores que respalden los resultados; separar borradores y publicaciones.'),
        'OBS-EVENTOS': ('Actividad de socialización, fecha, propósito, responsable y público destinatario.',
                       'Productos difundidos, participantes o destinatarios y respaldo de realización; una actividad programada no acredita ejecución.'),
        'INVENTARIO-CORTE': ('Equipos informáticos, software, licencias y espacios, con custodio, ubicación y condición.',
                             'Revisión y diferencias al corte; el inventario no sustituye el catálogo de fuentes y fichas metodológicas.'),
    },
}

FAMILIAS_PROPIAS = {
    'plantas_piloto': (('Producción y calidad de la planta piloto', (
        ('produccion', 'Órdenes, lotes y entregas de producción'),
        ('procesos', 'Procesos, etapas y trazabilidad'),
        ('control-calidad', 'Control de calidad, mediciones y no conformidades'))),),
    'centro_experimental': (('Experimentación y actividades de campo', (
        ('ensayos', 'Ensayos, parcelas y resultados de campo'),)),),
    'observatorios': (('Datos y publicaciones del observatorio', (
        ('datos-observatorio', 'Fuentes, fichas metodológicas y actualización de indicadores'),
        ('boletines', 'Calendario y publicaciones del observatorio'),
        ('eventos', 'Socialización de resultados y vinculación'))),),
}

CODIGOS_POR_FUENTE = {'reservas': 'REGISTRO-USO', 'recursos': 'INVENTARIO-CORTE',
                     'equipamiento': 'EQUIPAMIENTO', 'investigacion': 'INVESTIGACION',
                     'transferencia': 'TRANSFERENCIA'}

# Donde hay insumos el inventario lleva sus movimientos del período y se presenta cada semestre.
BASES_INVENTARIO_ANUAL = frozenset(('observatorios',))


def base_de(unidad, *, base=None):
    if base:
        return base
    dependencia = unidad if isinstance(unidad, str) else getattr(unidad, 'dependencia', '')
    if dependencia in BASES_AUDITABLES:
        return dependencia
    if not isinstance(unidad, str):
        return getattr(unidad, 'codigo_base', '') or dependencia
    from apps.core.presentation.tipologias import tipologia
    actual = tipologia(dependencia)
    return actual.base if actual else dependencia


def es_unidad_auditable(unidad):
    return base_de(unidad) in BASES_AUDITABLES


def _definicion_estandar(exigido):
    from apps.documentos.presentation.expediente_catalogo import CATALOGO, CATALOGO_PERFILES
    return next((fila for fila in (*CATALOGO, *CATALOGO_PERFILES) if fila[0] == exigido.codigo), None)


def _conserva_definicion_estandar(exigido, estandar):
    if estandar is None:
        return False
    from apps.documentos.presentation.expediente_catalogo import NOMBRES_ESTANDAR_ANTERIORES
    nombres = NOMBRES_ESTANDAR_ANTERIORES.get(exigido.codigo, frozenset()) | {estandar[1]}
    return (exigido.nombre in nombres and getattr(exigido, 'fuente_reporte', '') == estandar[9])


def aplica_documento(exigido, dependencia, *, base=None):
    """La asignación explícita y las definiciones personalizadas tienen prioridad."""
    tipos = getattr(exigido, 'tipos_unidad', ())
    if tipos:
        if dependencia in tipos:
            return True
        base = base_de(dependencia, base=base)
        return dependencia in tipos or base in tipos
    estandar = _definicion_estandar(exigido)
    if not _conserva_definicion_estandar(exigido, estandar):
        return True
    base = base_de(dependencia, base=base)
    return exigido.codigo not in EXCLUIDOS_POR_BASE.get(base, ())


def documento_visible(documento, unidad=None):
    unidad = unidad or documento.unidad
    if aplica_documento(documento.exigido, unidad.dependencia, base=base_de(unidad)):
        return True
    # Conservar la historia ya enviada o evaluada; ocultar pendientes y
    # borradores inapropiados no elimina sus filas ni sus archivos.
    return bool(documento.estado == 'validado' or any(getattr(documento, campo, None) is not None
        for campo in ('entregado_en', 'validado_en', 'recibido_en', 'evaluado_en', 'evaluacion')))


def nombre_para(exigido, unidad):
    estandar = _definicion_estandar(exigido)
    if not _conserva_definicion_estandar(exigido, estandar):
        return exigido.nombre
    base = base_de(unidad)
    if base == 'laboratorios':
        from apps.documentos.presentation.perfil_laboratorios import NOMBRES
        return NOMBRES.get(exigido.codigo, estandar[1])
    return NOMBRES_POR_BASE.get(base, {}).get(exigido.codigo, estandar[1])


def periodicidad_para(exigido, unidad):
    """El inventario integral es semestral donde reúne los movimientos de insumos; anual en los observatorios."""
    if (exigido.codigo == 'INVENTARIO-CORTE' and exigido.periodicidad == 'anual'
            and base_de(unidad) not in BASES_INVENTARIO_ANUAL):
        return 'semestral'
    return exigido.periodicidad


def requisitos_para(documento):
    base = base_de(documento.unidad)
    if base == 'laboratorios':
        from apps.documentos.presentation.perfil_laboratorios import REQUISITOS
        return REQUISITOS.get(documento.exigido.codigo, ())
    especificos = REQUISITOS_POR_BASE.get(base, {}).get(documento.exigido.codigo)
    if especificos is not None:
        return especificos
    return REQUISITOS_COMUNES.get(documento.exigido.codigo, ())


def familias_de_perfil(unidad, familias, *, catalogo=()):
    """Categorías de consulta pertinentes; no convierte un informe en aprobación."""
    base = base_de(unidad)
    if base not in BASES_AUDITABLES:
        return familias
    personalizados = {}
    for exigido in catalogo:
        if not aplica_documento(exigido, unidad.dependencia, base=base):
            continue
        estandar = _definicion_estandar(exigido)
        if (getattr(exigido, 'tipos_unidad', ())
                or not _conserva_definicion_estandar(exigido, estandar)):
            personalizados[exigido.fuente_reporte] = exigido.nombre
    if base == 'laboratorios':
        from apps.documentos.presentation.perfil_laboratorios import REPORTES
        return tuple((('8 · Transferencia de conocimiento, tecnología y servicios especializados a la sociedad'
                       if familia.startswith('8 ·') else familia),
                      tuple((codigo, personalizados.get(codigo, REPORTES.get(codigo, nombre))) for codigo, nombre in opciones))
                     for familia, opciones in familias)
    excluidas = {'produccion', 'procesos', 'calidad'}
    if base == 'observatorios':
        excluidas.update(('asignaturas', 'planificaciones', 'ejecuciones', 'guias', 'seguridad', 'desechos', 'inventario', 'aula'))
    excluidas.difference_update(personalizados)
    resultado = []
    for familia, opciones in familias:
        seleccion = tuple((codigo, personalizados.get(codigo, NOMBRES_CONSULTAS_POR_BASE.get(base, {}).get(codigo)
            or NOMBRES_POR_BASE.get(base, {}).get(CODIGOS_POR_FUENTE.get(codigo), nombre)))
                          for codigo, nombre in opciones if codigo not in excluidas)
        if not seleccion:
            continue
        if familia.startswith('1 ·'):
            familia = {'observatorios': 'Atenciones y uso de espacios del observatorio',
                       'plantas_piloto': 'Prácticas y uso de la planta piloto',
                       'centro_experimental': 'Prácticas y uso de escenarios experimentales'}[base]
        elif familia.startswith('3 ·') and base == 'observatorios':
            familia = 'Equipos informáticos, software y espacios'
        resultado.append((familia, seleccion))
    propias = tuple((familia, tuple((codigo, personalizados.get(codigo, nombre))
                                   for codigo, nombre in opciones))
                    for familia, opciones in FAMILIAS_PROPIAS.get(base, ()))
    # Una asignación explícita puede habilitar también la categoría genérica.
    # Mantener una sola entrada por fuente, con prioridad del grupo del perfil.
    fuentes, unicas = set(), []
    for familia, opciones in (*propias, *resultado):
        seleccion = []
        for codigo, nombre in opciones:
            if codigo not in fuentes:
                seleccion.append((codigo, nombre))
                fuentes.add(codigo)
        if seleccion:
            unicas.append((familia, tuple(seleccion)))
    return tuple(unicas)
