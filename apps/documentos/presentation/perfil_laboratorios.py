"""Alcance documental de laboratorios, sin modificar el catálogo de otras unidades.

Los códigos del expediente son identificadores internos. Sólo los formatos de
prácticas tienen código institucional confirmado en las fuentes aportadas.
"""

NOMBRES = {
    'RESOLUCION-CREACION': 'Resolución de creación de la unidad',
    'PROTOCOLO-BIOSEGURIDAD': 'Protocolo de seguridad y condiciones de operación',
    'PLAN-COMPRAS-ANUAL': 'Plan anual de compras y presupuesto para el año siguiente',
    'PLANIFICACION': 'Planificación semestral de actividades de la unidad',
    'INFORME-SEMESTRAL': 'Informe semestral de actividades y cumplimiento de la planificación',
    'INDICADORES-PLAN': 'Planificación semestral de prácticas por asignatura',
    'PLAN-MANTENIMIENTO': 'Plan anual de mantenimiento preventivo y correctivo',
    'REGISTRO-USO': 'Registro de uso de laboratorios: sesiones, horas y usuarios por finalidad',
    'PRACTICAS-FT02': 'FT02 · Planificación de uso de laboratorios',
    'PRACTICAS-FT03': 'FT03 · Registro de ejecución y evaluación de prácticas',
    'GUIAS': 'Registro de guías de práctica y vinculación con el syllabus',
    'PRESTAMOS-EQUIPOS': 'Registro de préstamos y devoluciones de equipos',
    'INDUCCION-SEGURIDAD': 'Registro de inducciones e inspecciones de seguridad',
    'DESECHOS': 'Registro de generación y gestión de desechos peligrosos y especiales',
    'EQUIPAMIENTO': 'Informe de estado, disponibilidad y funcionalidad del equipamiento',
    'INSUMOS-CORTE': 'Inventario de reactivos e insumos: existencias, lotes y movimientos',
    'INVENTARIO-CORTE': 'Inventario integral de recursos de la unidad',
    'INVESTIGACION': 'Informe de resultados de investigación aplicada y desarrollo tecnológico',
    'TRANSFERENCIA': 'Informe de transferencia de conocimiento, tecnología y servicios especializados a la sociedad',
    'ACCIONES-MEJORA': 'Seguimiento de acciones de mejora',
}

REQUISITOS = {
    'RESOLUCION-CREACION': ('Resolución auténtica correspondiente al laboratorio, con autoridad, número y fecha.',),
    'PROTOCOLO-BIOSEGURIDAD': ('Alcance, responsables, peligros y controles, acceso, operación y emergencias de la unidad.',
                              'Medidas específicas según las actividades; emisión y aprobación en la plataforma con QR.'),
    'PLAN-COMPRAS-ANUAL': ('Necesidades y compras del año siguiente, cantidades, costos, prioridad y financiamiento.',
                          'Justificación frente a inventario, capacidad instalada, personal y actividades; emisión y aprobación en la plataforma.'),
    'PLANIFICACION': ('Objetivos, diagnóstico, actividades, metas mínimas, responsables, recursos y cronograma.',
                      'Datos actuales del laboratorio, atención de observaciones y anexos revisados antes de emitir.'),
    'INFORME-SEMESTRAL': ('Resultados frente a cada meta, registros del período y explicación de diferencias.',
                          'Anexos revisados, evidencias reales, dificultades y acciones de mejora; emisión y aprobación en la plataforma.'),
    'INDICADORES-PLAN': ('Todas las prácticas aplicables, incluidas las registradas individualmente.',
                         'Asignatura, fecha, escenario, responsable, FT02 y guía vinculados; pendientes identificados.'),
    'PLAN-MANTENIMIENTO': ('Equipos e infraestructura, criticidad, intervenciones, frecuencia y responsables.',
                           'Cronograma anual y ejecución respaldada por órdenes, resultados e informes; separar avance operativo y documental.'),
    'REGISTRO-USO': ('Sesiones efectivamente realizadas, fechas, horas, usuarios y finalidad.',
                     'Conciliación independiente que permita comprobar la cobertura del registro; no confundir reservas con atenciones.'),
    'PRACTICAS-FT02': ('Asignatura, unidad, fecha, escenario, docente y responsable técnico.',
                       'Tema, objetivos, resultados de aprendizaje, recursos, seguridad y guía; aprobación y versión verificables.'),
    'PRACTICAS-FT03': ('Referencia al FT02, ejecución, asistencia, bitácora y evaluación de resultados.',
                       'Evidencias identificadas de la sesión: fotografías, capturas, informes o productos, según corresponda.'),
    'GUIAS': ('Guías individuales FT04 vigentes, con elaboración, revisión y aprobación documentadas.',
              'Vínculo verificable con asignatura, tema y resultado del syllabus; el listado no sustituye las guías.'),
    'PRESTAMOS-EQUIPOS': ('Equipo, receptor, finalidad, autorización, condiciones de salida y plazo.',
                          'Responsable de entrega, acta externa cuando corresponda y devolución con condiciones de recepción.'),
    'INDUCCION-SEGURIDAD': ('Protocolo vigente e inducción verificable de usuarios nuevos.',
                            'Inspecciones mensuales al corte, hallazgos, responsables, acciones, plazos y respaldo.'),
    'DESECHOS': ('Tipo, origen, cantidad, fecha, envase, etiquetado, almacenamiento y responsable.',
                 'Cuando se entregue: gestor, autorización o licencia, manifiesto y respaldo de recepción.'),
    'EQUIPAMIENTO': ('Identificación, ubicación, estado y períodos de indisponibilidad al corte real.',
                      'Verificaciones funcionales, incidencias e informes técnicos; disponibilidad no equivale a funcionalidad comprobada.'),
    'INSUMOS-CORTE': ('Existencias, unidad, ubicación, lotes, vencimientos aplicables y referencias de recepción.',
                      'Entradas, salidas, diferencias conciliadas y verificación física; separar datos DEMO.'),
    'INVENTARIO-CORTE': ('Corte de cada semestre: equipos, software, simuladores, espacios, reactivos e insumos.',
                         'Custodios, ubicación, condición, existencia física y acta integral respaldada; registrar diferencias.'),
    'INVESTIGACION': ('Proyecto o trabajo, responsable, producto obtenido y resultado verificable.',
                       'Respaldo real del informe, prototipo, publicación, conjunto de datos u otro producto; una reserva no acredita resultados.'),
    'TRANSFERENCIA': ('Producto o servicio entregado, responsable, destinatario y fecha.',
                       'Respaldo de entrega y aceptación del beneficiario; una solicitud o reserva no acredita transferencia.'),
    'ACCIONES-MEJORA': ('Hallazgo, acción concreta, responsable, plazo, avance y respaldo.',
                        'Comprobación del cierre; una acción redactada o un PDF generado no equivalen a una mejora ejecutada.'),
}

REPORTES = {
    'asignaturas': NOMBRES['INDICADORES-PLAN'],
    'planificaciones': NOMBRES['PRACTICAS-FT02'],
    'ejecuciones': NOMBRES['PRACTICAS-FT03'],
    'reservas': NOMBRES['REGISTRO-USO'],
    'mantenimiento': 'Informe de mantenimiento: planificación, ejecución e incidencias',
    'equipamiento': NOMBRES['EQUIPAMIENTO'],
    'recursos': NOMBRES['INVENTARIO-CORTE'],
    'inventario': NOMBRES['INSUMOS-CORTE'],
    'prestamos': NOMBRES['PRESTAMOS-EQUIPOS'],
    'guias': NOMBRES['GUIAS'],
    'seguridad': NOMBRES['INDUCCION-SEGURIDAD'],
    'desechos': NOMBRES['DESECHOS'],
    'investigacion': NOMBRES['INVESTIGACION'],
    'transferencia': NOMBRES['TRANSFERENCIA'],
    'cursos': 'Formación: cursos y eventos, ediciones, inscripciones y certificados',
    'finanzas': 'Informe financiero de servicios: ingresos, egresos y costos',
}


def es_laboratorio(unidad):
    if getattr(unidad, 'dependencia', '') == 'laboratorios':
        return True
    return getattr(unidad, 'codigo_base', '') == 'laboratorios'


def nombre_para(exigido, unidad):
    from apps.documentos.presentation.perfil_unidades import nombre_para as nombre_del_perfil
    return nombre_del_perfil(exigido, unidad)


def periodicidad_para(exigido, unidad):
    from apps.documentos.presentation.perfil_unidades import periodicidad_para as periodicidad_del_perfil
    return periodicidad_del_perfil(exigido, unidad)


def requisitos_para(documento):
    from apps.documentos.presentation.perfil_unidades import requisitos_para as requisitos_del_perfil
    return requisitos_del_perfil(documento)


def referencia_interna(documento):
    # Referencias breves para que se lean completas en el encabezado A4.
    from apps.documentos.presentation.perfil_unidades import base_de

    sufijo = {'PLANIFICACION': 'PLAN', 'INFORME-SEMESTRAL': 'INFORME',
              'PLAN-COMPRAS-ANUAL': 'COMPRAS', 'ACCIONES-MEJORA': 'MEJORA',
              'PROTOCOLO-BIOSEGURIDAD': 'SEGURIDAD'}.get(
                  documento.exigido.codigo, documento.exigido.codigo)
    perfil = {'laboratorios': 'LAB', 'plantas_piloto': 'PP',
              'centro_experimental': 'CE', 'observatorios': 'OBS'}.get(
                  base_de(documento.unidad), 'UNIDAD')
    return f'SLCID-{perfil}-{sufijo}'
