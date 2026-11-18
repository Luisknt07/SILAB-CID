"""Alcance documental de laboratorios, sin modificar el catálogo de otras unidades.

Los códigos del expediente son identificadores internos. Sólo los formatos de
prácticas tienen código institucional confirmado en las fuentes aportadas.
"""

NOMBRES = {
    'RESOLUCION-CREACION': 'Resolución de creación de la unidad',
    'PROTOCOLO-BIOSEGURIDAD': 'Protocolo de bioseguridad',
    'PLAN-COMPRAS-ANUAL': 'Plan anual de compras y presupuesto para el año siguiente',
    'PLANIFICACION': 'Planificación semestral del laboratorio',
    'INFORME-SEMESTRAL': 'Informe semestral de actividades y cumplimiento de la planificación',
    # Anexos del informe: uno por cada documento que pide la universidad (documentos.0027).
    'REGISTRO-USO': 'Registros de uso del laboratorio',
    'EQUIPAMIENTO': 'Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad',
    'INVENTARIO-CORTE': 'Inventario de equipamiento, reactivos e insumos',
    'FICHAS-TECNICAS': 'Fichas técnicas de laboratorios, talleres, software, simuladores y espacios utilizados',
    'PRACTICAS-FT02': 'Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable',
    'GUIAS': 'Guías de prácticas de laboratorio aprobadas y vinculadas con los contenidos del syllabus',
    'PRACTICAS-FT03': 'Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados',
    'INDUCCION-SEGURIDAD': 'Reportes de seguridad y condiciones de operación',
    'DESECHOS': 'Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable',
    'INVESTIGACION': 'Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros',
    'TRANSFERENCIA': 'Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad',
    # Retirado en documentos.0025; su nombre se conserva para leer lo ya archivado.
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
    'REGISTRO-USO': ('Todas las sesiones del período: horario previsto y real, espacio o recurso, propósito y solicitante.',
                     'Participantes, cierre y horas efectivas; totales por propósito y por mes, y visitas.'),
    'EQUIPAMIENTO': ('Plan de mantenimiento vigente por equipo y mantenimientos del período, con su informe.',
                     'Cumplimiento en los equipos críticos, fallas y días fuera de servicio, y pruebas funcionales.'),
    'INVENTARIO-CORTE': ('Acta de revisión física y equipos con serie, código del bien, custodio, ubicación y estado.',
                         'Bajas y traspasos; reactivos por lote y vencimiento; insumos y movimientos del período.'),
    'FICHAS-TECNICAS': ('Ficha de la unidad: ubicación, responsable, horario y capacidad.',
                        'Espacios y talleres con capacidad, mobiliario y equipos; software y simuladores con versión y licencias.'),
    'PRACTICAS-FT02': ('Todas las prácticas planificadas, por asignatura: unidad y tema del syllabus, fecha y escenario.',
                       'Responsable técnico, estudiantes previstos, guía y estado de la revisión de cada una.'),
    'GUIAS': ('Guías vigentes con versión, aprobación y enlace al documento.',
              'Vínculo con la asignatura, el tema y el resultado de aprendizaje del syllabus; contenido mínimo completo.'),
    'PRACTICAS-FT03': ('Ejecución de cada práctica y asistencia nominal.',
                       'Evidencias identificadas: asistencia firmada, bitácora, fotografías, capturas, informes y productos.'),
    'INDUCCION-SEGURIDAD': ('Requisitos de acceso, inducciones y habilitaciones, y control de ingresos.',
                            'Inspecciones mensuales con hallazgos y acciones correctivas, e incidentes de seguridad.'),
    'DESECHOS': ('Cada desecho generado: clase, clave, origen, cantidad, envase, etiquetado y almacenamiento.',
                 'Entregas al gestor autorizado con licencia y manifiesto; lo almacenado al corte.'),
    'INVESTIGACION': ('Solo si el plan la compromete: resultados con proyecto, producto, responsable y respaldo.',
                       'Uso de la unidad para investigación; una reserva no acredita un resultado.'),
    'TRANSFERENCIA': ('Transferencias con destinatario, entregable y aceptación documentada.',
                       'Servicios especializados atendidos, con solicitante, horas y valor; una solicitud no es una entrega.'),
    'ACCIONES-MEJORA': ('Hallazgo, acción concreta, responsable, plazo, avance y respaldo.',
                        'Comprobación del cierre; una acción redactada o un PDF generado no equivalen a una mejora ejecutada.'),
}

# Nombres de las categorías del Centro de reportes. Las que no son anexos
# (asignaturas, mantenimiento, inventario, préstamos…) son consultas de gestión.
REPORTES = {
    'asignaturas': 'Planificación semestral de prácticas por asignatura',
    'planificaciones': NOMBRES['PRACTICAS-FT02'],
    'ejecuciones': NOMBRES['PRACTICAS-FT03'],
    'reservas': NOMBRES['REGISTRO-USO'],
    'mantenimiento': 'Informe de mantenimiento: planificación, ejecución e incidencias',
    'equipamiento': NOMBRES['EQUIPAMIENTO'],
    'recursos': NOMBRES['INVENTARIO-CORTE'],
    'inventario': 'Inventario de reactivos e insumos: existencias, lotes y movimientos',
    'prestamos': 'Registro de préstamos y devoluciones de equipos',
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


# Código de referencia de cada documento: SLCID-<tipo de unidad>-<sufijo>.
SUFIJOS_DE_REFERENCIA = {
    'PLANIFICACION': 'PLAN', 'INFORME-SEMESTRAL': 'INFORME', 'PLAN-COMPRAS-ANUAL': 'COMPRAS',
    'ACCIONES-MEJORA': 'MEJORA', 'PROTOCOLO-BIOSEGURIDAD': 'SEGURIDAD',
    'REGISTRO-USO': 'USO', 'EQUIPAMIENTO': 'EQUIPAMIENTO', 'INVENTARIO-CORTE': 'INVENTARIO',
    'FICHAS-TECNICAS': 'FICHAS', 'PRACTICAS-FT02': 'PRACTICAS-PLAN', 'GUIAS': 'GUIAS',
    'PRACTICAS-FT03': 'PRACTICAS-EVIDENCIAS', 'INDUCCION-SEGURIDAD': 'REPORTES-SEGURIDAD',
    'DESECHOS': 'DESECHOS', 'INVESTIGACION': 'INVESTIGACION', 'TRANSFERENCIA': 'TRANSFERENCIA',
    'PP-PRODUCCION': 'PRODUCCION', 'PP-CALIDAD': 'CALIDAD', 'CE-ENSAYOS': 'ENSAYOS',
    'CE-PRODUCCION': 'PRODUCCION-AGRO', 'OBS-DATOS': 'DATOS', 'OBS-BOLETINES': 'PUBLICACIONES',
    'OBS-EVENTOS': 'SOCIALIZACION',
}


def referencia_interna(documento):
    # Referencias breves para que se lean completas en el encabezado A4.
    from apps.documentos.presentation.perfil_unidades import base_de

    sufijo = SUFIJOS_DE_REFERENCIA.get(documento.exigido.codigo, documento.exigido.codigo)
    perfil = {'laboratorios': 'LAB', 'plantas_piloto': 'PP',
              'centro_experimental': 'CE', 'observatorios': 'OBS'}.get(
                  base_de(documento.unidad), 'UNIDAD')
    return f'SLCID-{perfil}-{sufijo}'
