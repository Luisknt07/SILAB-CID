"""Catálogo institucional de documentos exigidos, en su estado vigente.

Las migraciones 0211, 0213 y 0229 lo sembraron y lo ajustaron; este módulo es
la misma definición en un solo lugar, para volver a sembrarla cuando la tabla
está vacía (una instalación nueva o una base de pruebas vaciada) sin tocar lo
que la institución ya haya editado desde el admin.

La regla que lo ordena: la unidad firma dos documentos por período, la
planificación al abrir y el informe al cerrar. Todo lo que el sistema produce
con lo ya registrado viaja dentro de ellos como anexo y se valida con ellos.
Aparte quedan los documentos de una sola vez, que se heredan cada año.
"""

from apps.documentos.models.expediente import DocumentoExigido

# codigo, nombre, carpeta, periodicidad, origen, firma, condicional, plazo_regla, plazo_dias, fuente, orden,
# descripcion, anexo_de
CATALOGO = (
    # -- Una sola vez; se actualizan cuando cambian y se heredan cada año -----------------------
    ('RESOLUCION-CREACION', 'Resolución de creación de la unidad', 'planeacion', 'unica', 'unidad', False, False,
     'ninguno', 0, '', 10, 'Resolución que aprueba la unidad y sus reformas; se hereda cada año. Cumplimiento obligatorio: la '
     'Dirección la aprueba una vez por versión; no se califica.', ''),
    ('PROTOCOLO-BIOSEGURIDAD', 'Protocolo de seguridad y condiciones de operación', 'planeacion', 'unica',
     'ambos', True, False, 'ninguno', 0, 'protocolo', 15,
     'Se elabora con el editor de la unidad: alcance, responsables, riesgos, controles, operación y '
     'emergencias. Se envía y aprueba en la plataforma con QR; se conserva mientras siga vigente. La '
     'bioseguridad y otras medidas específicas se incluyen cuando correspondan a las actividades. '
     'Cumplimiento obligatorio: se aprueba una vez y se conserva mientras siga vigente; no se califica.', ''),

    # -- Una vez por año: necesidades del año siguiente, convocatoria ordinaria en mayo -----
    ('PLAN-COMPRAS-ANUAL', 'Plan anual de compras y presupuesto para el año siguiente', 'planeacion',
     'anual', 'ambos', True, False, 'meses', 0, 'compras', 40,
     'Lo que la unidad necesitará comprar el año siguiente, con su justificación frente al inventario, la '
     'vida útil de los equipos y sus actividades. Se prepara con el editor y se emite en la plataforma '
     'para revisión y aprobación; la ventana de entrega se consulta en el expediente. Si no requiere '
     'compras, lo justifica. Cumplimiento obligatorio: la Dirección confirma su conformidad documental; no '
     'se califica ni compromete fondos.', ''),

    # -- Apertura del período: la planificación firmada y sus anexos ---------------------------
    ('PLANIFICACION', 'Planificación semestral de actividades de la unidad', 'planeacion', 'semestral', 'ambos', True,
     False, 'inicio', 15, 'planificacion', 20,
     'Se redacta con el editor guiado: el sistema llena lo que ya sabe (datos de la unidad, espacios, '
     'servicios, inventario) y la unidad revisa objetivos, diagnóstico, actividades, metas y recursos. Al '
     'emitir se registra al responsable; la aprobación se consulta mediante el mismo QR. Cumplimiento '
     'obligatorio: la Dirección confirma su conformidad; no se califica. Sus metas son las que mide el '
     'informe semestral.', ''),
    ('INDICADORES-PLAN', 'Plan semestral de prácticas por asignatura', 'planeacion', 'semestral', 'sistema',
     False, False, 'inicio', 15, 'asignaturas', 30,
     'Programación consolidada del semestre: asignatura, fecha, escenario y responsable de cada práctica, '
     'con su FT02 y su guía vinculados. Respalda la planificación; no tiene meta propia (las prácticas '
     'aprobadas se miden en el FT02).', 'PLANIFICACION'),
    ('PLAN-MANTENIMIENTO', 'Plan anual de mantenimiento preventivo y correctivo', 'planeacion', 'anual', 'sistema',
     False, False, 'inicio', 15, 'mantenimiento', 50,
     'Equipos e infraestructura, criticidad, intervenciones, frecuencia, responsables y calendario del '
     'año; viaja con la planificación del período A. Respalda la meta de mantenimiento, que se mide en el '
     'informe semestral: 80 % de lo programado en equipos críticos.', 'PLANIFICACION'),

    # -- Cierre del período: el informe firmado y sus anexos de evidencia ----------------------
    ('INFORME-SEMESTRAL', 'Informe semestral de actividades y cumplimiento de la planificación', 'evaluacion', 'semestral', 'ambos', True,
     False, 'cierre', 15, 'informe', 10,
     'Se redacta con el editor guiado sobre lo que el sistema registró en el período: cumplimiento del '
     'plan, uso, logros, dificultades y acciones de mejora. Al emitir registra al responsable y conserva '
     'las evidencias del período; la aprobación se consulta mediante el mismo QR. Los plazos se consultan '
     'en el expediente. Es el único documento que se califica: su nota es el cumplimiento de las metas de '
     'la planificación, medido con los registros y las evidencias del período, y no se obtiene por haberlo '
     'entregado. Una entrega tardía descuenta los puntos que fija la política de calidad.', ''),
    ('REGISTRO-USO', 'Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'reservas', 10,
     'Sesiones registradas en la plataforma durante el período, agrupadas por propósito, con fecha, '
     'horario, solicitante y estado. Respalda la meta de registrar todas las sesiones de uso; el uso '
     'efectivo frente a la capacidad se detalla en los indicadores del informe.',
     'INFORME-SEMESTRAL'),
    ('PRACTICAS-FT02', 'FT02 · Planificación de cada práctica', 'ejecucion', 'semestral', 'sistema', False, False,
     'cierre', 15, 'planificaciones', 20, 'Matriz FT02 del período: cada práctica planificada con asignatura, fecha, escenario, docente, '
     'responsable y guía, y la comprobación de su aprobación y su respaldo. Respalda la meta de prácticas '
     'planificadas.', 'INFORME-SEMESTRAL'),
    ('PRACTICAS-FT03', 'FT03 · Registro de ejecución con asistencia, bitácora y evidencias', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'ejecuciones', 30, 'Registro FT03 del período: ejecución de cada práctica con asistencia, bitácora, resultados y '
     'evidencias, y la comprobación de su respaldo. Respalda la meta de prácticas ejecutadas.', 'INFORME-SEMESTRAL'),
    ('GUIAS', 'Guías de prácticas: aprobación y vínculo con el syllabus', 'ejecucion', 'semestral', 'sistema',
     False, False, 'cierre', 15, 'guias', 40, 'Guías de práctica vigentes usadas en el período: código, versión, aprobación y vínculo con la '
     'asignatura y el syllabus. Respalda la meta de guías.',
     'INFORME-SEMESTRAL'),
    ('PRESTAMOS-EQUIPOS', 'Registro de préstamos de equipos', 'ejecucion', 'semestral', 'sistema', False, False,
     'cierre', 15, 'prestamos', 50,
     'Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo. Sale de los '
     'préstamos registrados en la consola; el externo además exige su acta. Respalda la meta opcional de '
     'préstamos de equipos: cuenta en la nota solo si la planificación la incluyó.', 'INFORME-SEMESTRAL'),
    ('INDUCCION-SEGURIDAD', 'Registro de inducciones y controles de seguridad', 'ejecucion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'seguridad', 70, 'Requisitos de acceso, inducciones y habilitaciones de usuarios nuevos, inspecciones de seguridad del '
     'período, incidentes y estado del protocolo vigente. Respalda las metas de inducción de seguridad y '
     'de inspecciones.', 'INFORME-SEMESTRAL'),
    ('DESECHOS', 'Registro de desechos peligrosos y especiales', 'ejecucion', 'semestral', 'sistema', False, False,
     'cierre', 15, 'desechos', 80, 'Desechos peligrosos y especiales del período: tipo, origen, cantidad, almacenamiento, responsable y, '
     'cuando se entregan, gestor autorizado y manifiesto. Respalda la meta de gestión de desechos.', 'INFORME-SEMESTRAL'),
    ('EQUIPAMIENTO', 'Equipamiento: disponibilidad y funcionalidad del período', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'equipamiento', 40, 'Disponibilidad y funcionalidad del equipamiento en el período: estado al corte, días fuera de '
     'servicio, verificaciones funcionales e incidencias. El inventario completo va en el anexo de '
     'recursos. Respalda la meta opcional de disponibilidad del equipamiento: cuenta en la nota solo si la '
     'planificación la incluyó.', 'INFORME-SEMESTRAL'),
    ('INSUMOS-CORTE', 'Reactivos e insumos: existencias y movimientos del período', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'inventario', 50,
     'Movimientos de reactivos e insumos del período (entradas, consumos y ajustes) y existencias y lotes '
     'vigentes con sus vencimientos; complementa el inventario integral. Respalda la meta opcional de '
     'movimientos de insumos: cuenta en la nota solo si la planificación la incluyó.', 'INFORME-SEMESTRAL'),
    ('INVENTARIO-CORTE', 'Inventario anual de equipos, software y espacios', 'evaluacion', 'anual',
     'sistema', False, False, 'cierre', 15, 'recursos', 30,
     'Inventario integral de la unidad al generarlo: equipos, software, espacios y, donde aplica, insumos, '
     'con custodio, ubicación y condición. Respalda la meta de revisión física del inventario, que se '
     'acredita con el acta verificada.', 'INFORME-SEMESTRAL'),
    ('INVESTIGACION', 'Resultados de investigación aplicada y desarrollo tecnológico', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'investigacion', 60,
     'Productos de investigación aplicada y desarrollo tecnológico obtenidos en el período, con su '
     'proyecto, responsable y respaldo verificable; el uso de la unidad para investigación y titulación se '
     'muestra aparte. Respalda la meta de resultados de investigación.',
     'INFORME-SEMESTRAL'),
    ('TRANSFERENCIA', 'Transferencia de conocimiento y servicios especializados a la sociedad', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'transferencia', 70,
     'Entregables de transferencia de conocimiento y servicios especializados, con su destinatario y su '
     'aceptación documentada; las solicitudes de servicio y las reservas se muestran aparte. Respalda las '
     'metas de transferencia y de servicios.', 'INFORME-SEMESTRAL'),
    ('ACCIONES-MEJORA', 'Seguimiento de acciones de mejora', 'mejora', 'semestral', 'sistema', False, False, 'cierre',
     15, 'mejora', 10,
     'Acciones de mejora consolidadas desde los informes: hallazgo, acción, responsable, plazo, estado y '
     'evidencia de cierre; su vista previa es el mismo documento que se archiva. Respalda la meta opcional '
     'de seguimiento de acciones de mejora: cuenta en la nota solo si la planificación la incluyó.', 'INFORME-SEMESTRAL'),
)

# Evidencias propias de las otras implementaciones. Conservan fuentes y
# nombres distintos de los formatos de prácticas de los laboratorios.
CATALOGO_PERFILES = (
    ('PP-PRODUCCION', 'Informe de producción de la planta piloto: órdenes, lotes y entregas',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'produccion', 90,
     'Producción realizada frente al plan, cantidades, estados y trazabilidad de lotes y entregas. '
     'Respalda la meta de lotes o procesos de producción ejecutados.', 'INFORME-SEMESTRAL'),
    ('PP-CALIDAD', 'Informe de control de calidad y no conformidades de la planta piloto',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'control-calidad', 95,
     'Parámetros, mediciones y resultados por lote u orden; liberación, rechazo y seguimiento. Respalda la '
     'meta de control de calidad de los lotes finalizados.', 'INFORME-SEMESTRAL'),
    ('CE-ENSAYOS', 'Informe de ensayos y seguimiento de parcelas experimentales',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'ensayos', 90,
     'Objetivo, escenario, fechas, manejo, mediciones y resultados respaldados de los ensayos. Respalda la '
     'meta de ensayos y parcelas con seguimiento.', 'INFORME-SEMESTRAL'),
    ('OBS-DATOS', 'Registro de fuentes, metodología y actualización de indicadores del observatorio',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'datos-observatorio', 20,
     'Fichas metodológicas, fuentes y actualizaciones con período de referencia, territorio y '
     'trazabilidad. Respalda la meta de actualización de series y fuentes del observatorio.', 'INFORME-SEMESTRAL'),
    ('OBS-BOLETINES', 'Informe de publicaciones y cumplimiento del calendario del observatorio',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'boletines', 30,
     'Publicaciones previstas y efectivas, fecha, responsable, indicadores y respaldo consultable. '
     'Respalda la meta de boletines, informes o bases de datos publicados.', 'INFORME-SEMESTRAL'),
    ('OBS-EVENTOS', 'Informe de socialización de resultados y vinculación del observatorio',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'eventos', 40,
     'Actividades realizadas, propósito, destinatarios, productos difundidos y respaldo. Respalda la meta '
     'de eventos de socialización de resultados.', 'INFORME-SEMESTRAL'),
)
TIPOS_CATALOGO_PERFILES = {'PP-PRODUCCION': ['plantas_piloto'], 'PP-CALIDAD': ['plantas_piloto'],
                         'CE-ENSAYOS': ['centro_experimental'], 'OBS-DATOS': ['observatorios'],
                         'OBS-BOLETINES': ['observatorios'], 'OBS-EVENTOS': ['observatorios']}

# Lo que dejó de exigirse aparte y no debe volver a sembrarse: las listas de
# chequeo eran una carga semestral a mano; su lugar lo ocupan el protocolo de
# seguridad y condiciones de operación (permanente) y el registro de controles.
RETIRADOS = ('CHEQUEO-SEGURIDAD',)

# Se reconocen sólo los nombres anteriores del catálogo distribuido. Permite
# presentar su denominación actual sin reescribir catálogos editados ni archivos.
NOMBRES_ESTANDAR_ANTERIORES = {
    'PLAN-COMPRAS-ANUAL': frozenset(('Plan anual de compras y presupuesto del año siguiente (firmado)',)),
    'PLANIFICACION': frozenset(('Planificación semestral de la unidad (firmada)',)),
    'INFORME-SEMESTRAL': frozenset(('Informe semestral de actividades (firmado)',)),
    'INDUCCION-SEGURIDAD': frozenset(('Seguridad y condiciones de operación: protocolo, inducciones y controles',)),
}

# Ventanas fijas en el calendario (plazo «entre dos meses»): de qué mes a qué mes.
VENTANAS = {'PLAN-COMPRAS-ANUAL': (5, 5)}


def asegurar_catalogo():
    """Siembra el catálogo vigente solo si la tabla está vacía; nunca pisa lo editado."""
    if DocumentoExigido.objects.exists():
        return 0
    creados = 0
    for (codigo, nombre, carpeta, periodicidad, origen, firma, condicional, regla, dias, fuente, orden,
         descripcion, _anexo) in (*CATALOGO, *CATALOGO_PERFILES):
        DocumentoExigido.objects.get_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'carpeta': carpeta, 'periodicidad': periodicidad, 'origen': origen,
            'requiere_firma': firma, 'condicional': condicional, 'plazo_regla': regla, 'plazo_dias': dias,
            'fuente_reporte': fuente, 'orden': orden, 'descripcion': descripcion,
            'tipos_unidad': TIPOS_CATALOGO_PERFILES.get(codigo, []), 'activo': True,
            'abre_mes': VENTANAS.get(codigo, (None, None))[0], 'vence_mes': VENTANAS.get(codigo, (None, None))[1],
        })
        creados += 1
    # Los anexos apuntan a su documento firmado una vez que todos existen.
    por_codigo = {e.codigo: e for e in DocumentoExigido.objects.all()}
    for fila in (*CATALOGO, *CATALOGO_PERFILES):
        codigo, anexo = fila[0], fila[-1]
        if anexo:
            DocumentoExigido.objects.filter(codigo=codigo).update(anexo_de=por_codigo[anexo])
    return creados
