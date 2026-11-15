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
    # Anexos del informe (documentos.0025): cinco, cada uno respalda un grupo de metas.
    'REGISTRO-USO': 'Uso de la unidad: sesiones, horas y usuarios',
    'PRACTICAS-FT02': 'Prácticas académicas: planificación, ejecución y guías',
    'INDUCCION-SEGURIDAD': 'Seguridad y desechos: inducciones, inspecciones y desechos',
    'EQUIPAMIENTO': 'Equipos e inventario: revisión física, mantenimiento y existencias',
    'INVESTIGACION': 'Investigación y vinculación: resultados, transferencia y servicios',
    # Retirados en documentos.0025; sus nombres se conservan para leer lo ya archivado.
    'PRACTICAS-FT03': 'Registro de ejecución y evaluación de prácticas',
    'GUIAS': 'Registro de guías de práctica y vinculación con el syllabus',
    'DESECHOS': 'Registro de generación y gestión de desechos peligrosos y especiales',
    'INVENTARIO-CORTE': 'Inventario integral de recursos de la unidad',
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
    'REGISTRO-USO': ('Sesiones efectivamente realizadas, fechas, horas, usuarios y finalidad.',
                     'Conciliación independiente que permita comprobar la cobertura del registro; no confundir reservas con atenciones.'),
    'PRACTICAS-FT02': ('Prácticas aprobadas con asignatura, fecha, escenario, docente, responsable técnico y guía.',
                       'Prácticas ejecutadas con asistencia y evidencia; guías vigentes, aprobadas y vinculadas al syllabus.'),
    'PRACTICAS-FT03': ('Referencia a la práctica planificada, ejecución, asistencia, bitácora y evaluación de resultados.',
                       'Evidencias identificadas de la sesión: fotografías, capturas, informes o productos, según corresponda.'),
    'GUIAS': ('Guías individuales FT04 vigentes, con elaboración, revisión y aprobación documentadas.',
              'Vínculo verificable con asignatura, tema y resultado del syllabus; el listado no sustituye las guías.'),
    'INDUCCION-SEGURIDAD': ('Inducción verificable de usuarios nuevos e inspecciones mensuales al corte, con respaldo.',
                            'Desechos generados con cantidad, almacenamiento, responsable y entrega al gestor autorizado.'),
    'DESECHOS': ('Tipo, origen, cantidad, fecha, envase, etiquetado, almacenamiento y responsable.',
                 'Cuando se entregue: gestor, autorización o licencia, manifiesto y respaldo de recepción.'),
    'EQUIPAMIENTO': ('Acta de revisión física del inventario y datos pendientes de identificación de los equipos.',
                     'Mantenimientos del período frente al programa crítico (80 %), equipos fuera de servicio e '
                     'insumos bajo su mínimo de reposición.'),
    'INVENTARIO-CORTE': ('Corte de cada semestre: equipos, software, simuladores, espacios, reactivos e insumos.',
                         'Custodios, ubicación, condición, existencia física y acta integral respaldada; existencias, lotes y '
                         'movimientos de insumos del período, con diferencias conciliadas.'),
    'INVESTIGACION': ('Solo si el plan lo compromete: productos de investigación con su proyecto, responsable y respaldo.',
                       'Transferencias y servicios entregados y aceptados; una solicitud o reserva no acredita resultados.'),
    'TRANSFERENCIA': ('Producto o servicio entregado, responsable, destinatario y fecha.',
                       'Respaldo de entrega y aceptación del beneficiario; una solicitud o reserva no acredita transferencia.'),
    'ACCIONES-MEJORA': ('Hallazgo, acción concreta, responsable, plazo, avance y respaldo.',
                        'Comprobación del cierre; una acción redactada o un PDF generado no equivalen a una mejora ejecutada.'),
}

# Nombres de las categorías del Centro de reportes. Las que no son anexos
# (asignaturas, mantenimiento, inventario, préstamos…) son consultas de gestión.
REPORTES = {
    'asignaturas': 'Planificación semestral de prácticas por asignatura',
    # Consultas de detalle; el anexo del informe reúne planificación, ejecución y guías.
    'planificaciones': 'Prácticas planificadas: asignatura, docente, escenario y guía',
    'ejecuciones': 'Prácticas ejecutadas: asistencia, bitácora y evidencias',
    'reservas': NOMBRES['REGISTRO-USO'],
    'mantenimiento': 'Informe de mantenimiento: planificación, ejecución e incidencias',
    'equipamiento': 'Mantenimiento, disponibilidad y funcionalidad del equipamiento',
    'recursos': NOMBRES['INVENTARIO-CORTE'],
    'inventario': 'Inventario de reactivos e insumos: existencias, lotes y movimientos',
    'prestamos': 'Registro de préstamos y devoluciones de equipos',
    'guias': NOMBRES['GUIAS'],
    'seguridad': 'Inducciones, inspecciones y controles de seguridad',
    'desechos': NOMBRES['DESECHOS'],
    'investigacion': 'Resultados de investigación aplicada y desarrollo tecnológico',
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
              'PROTOCOLO-BIOSEGURIDAD': 'SEGURIDAD', 'REGISTRO-USO': 'USO', 'PRACTICAS-FT02': 'PRACTICAS',
              'INDUCCION-SEGURIDAD': 'SEGURIDAD-DESECHOS', 'EQUIPAMIENTO': 'EQUIPOS-INVENTARIO',
              'INVESTIGACION': 'INVESTIGACION-VINCULACION'}.get(
                  documento.exigido.codigo, documento.exigido.codigo)
    perfil = {'laboratorios': 'LAB', 'plantas_piloto': 'PP',
              'centro_experimental': 'CE', 'observatorios': 'OBS'}.get(
                  base_de(documento.unidad), 'UNIDAD')
    return f'SLCID-{perfil}-{sufijo}'
