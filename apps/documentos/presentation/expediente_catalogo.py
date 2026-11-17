"""Catálogo institucional de documentos exigidos, en su estado vigente.

Las migraciones 0211, 0213 y 0229 lo sembraron y lo ajustaron; este módulo es
la misma definición en un solo lugar, para volver a sembrarla cuando la tabla
está vacía (una instalación nueva o una base de pruebas vaciada) sin tocar lo
que la institución ya haya editado desde el admin.

La regla que lo ordena: la unidad firma dos documentos por período, la
planificación al abrir y el informe al cerrar. Todo lo que el sistema produce
con lo ya registrado viaja dentro de ellos como anexo y se valida con ellos.
Aparte quedan los documentos de una sola vez, que se heredan cada año.

Los anexos del informe responden, uno a uno, a los documentos que pide la
universidad (documentos.0027). Su estructura, tabla por tabla, está en
``docs/estructura-anexos-por-tipo-de-unidad.md``.
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
    # La planificación viaja sin anexos: la carga por asignatura y los mantenimientos previstos son
    # secciones de su propio PDF, y su ejecución se presenta en los anexos del informe.

    # -- Cierre del período: el informe firmado y sus anexos de evidencia ----------------------
    ('INFORME-SEMESTRAL', 'Informe semestral de actividades y cumplimiento de la planificación', 'evaluacion', 'semestral', 'ambos', True,
     False, 'cierre', 15, 'informe', 10,
     'Se redacta con el editor guiado sobre lo que el sistema registró en el período: cumplimiento del '
     'plan, uso, logros, dificultades y acciones de mejora. Al emitir registra al responsable y conserva '
     'las evidencias del período; la aprobación se consulta mediante el mismo QR. Los plazos se consultan '
     'en el expediente. Es el único documento que se califica: su nota es el cumplimiento de las metas de '
     'la planificación, medido con los registros y las evidencias del período, y no se obtiene por haberlo '
     'entregado. Una entrega tardía descuenta los puntos que fija la política de calidad.', ''),
    # Anexos comunes: uno por cada documento que pide la universidad, en su mismo orden
    # (documentos.0027). El orden numera los anexos; los tres últimos son condicionales.
    ('REGISTRO-USO', 'Registros de uso de la unidad', 'ejecucion', 'semestral', 'sistema', False,
     False, 'cierre', 15, 'reservas', 10,
     'Todas las sesiones del período con su horario previsto y real, espacio o recurso, propósito, '
     'solicitante, participantes, cierre y horas efectivas; totales por propósito y por mes, y visitas. '
     'Respalda las metas de registro de sesiones y de uso efectivo.', 'INFORME-SEMESTRAL'),
    ('EQUIPAMIENTO', 'Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'equipamiento', 20,
     'Plan de mantenimiento vigente por equipo, mantenimientos del período con su informe, cumplimiento del '
     'plan en los equipos críticos, fallas y días fuera de servicio, pruebas funcionales, estado de los '
     'equipos al corte y mantenimiento de la infraestructura. Respalda la meta de mantenimiento.',
     'INFORME-SEMESTRAL'),
    ('INVENTARIO-CORTE', 'Inventario de equipamiento, reactivos e insumos', 'evaluacion', 'anual',
     'sistema', False, False, 'cierre', 15, 'recursos', 30,
     'Acta de revisión física, equipos con su identificación, custodia y estado, bajas y traspasos, '
     'reactivos por lote, insumos y materiales, y movimientos del período. Se presenta cada semestre; en '
     'los observatorios, una vez al año con el informe B. Respalda la meta de revisión física del '
     'inventario.', 'INFORME-SEMESTRAL'),
    ('FICHAS-TECNICAS', 'Fichas técnicas de laboratorios, talleres, software, simuladores y espacios utilizados',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'fichas-tecnicas', 40,
     'Ficha de la unidad (ubicación, responsable, horario y capacidad), espacios y talleres con su '
     'capacidad, mobiliario y equipos asociados, y software y simuladores con su versión, acceso y '
     'licencias. Es registro del período, sin meta propia.', 'INFORME-SEMESTRAL'),
    ('PRACTICAS-FT02', 'Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable', 'ejecucion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'planificaciones', 50,
     'Todas las prácticas planificadas, por asignatura: unidad y tema del syllabus, fecha, escenario, '
     'responsable técnico, estudiantes previstos, guía y estado de su revisión; sesiones programadas sin '
     'planificación y resumen por asignatura. Respalda la meta de prácticas planificadas.',
     'INFORME-SEMESTRAL'),
    ('GUIAS', 'Guías de prácticas aprobadas y vinculadas con los contenidos del syllabus', 'ejecucion', 'semestral', 'sistema',
     False, False, 'cierre', 15, 'guias', 60,
     'Guías vigentes con su versión, vínculo con la asignatura y el syllabus, aprobación y enlace al '
     'documento; comprobación de su contenido mínimo y versiones sustituidas en el período. Respalda la '
     'meta de guías.', 'INFORME-SEMESTRAL'),
    ('PRACTICAS-FT03', 'Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'ejecuciones', 70,
     'Ejecución de cada práctica, asistencia nominal e índice de evidencias por tipo (asistencia firmada, '
     'bitácora, fotografías identificadas, capturas de simulador, informes de estudiantes y productos '
     'desarrollados), con enlace a cada archivo. Respalda la meta de prácticas ejecutadas.',
     'INFORME-SEMESTRAL'),
    ('INDUCCION-SEGURIDAD', 'Reportes de seguridad y condiciones de operación', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'seguridad', 80,
     'Requisitos de acceso, inducciones y habilitaciones, inspecciones de condiciones con sus hallazgos y '
     'acciones correctivas, cobertura mensual, control de ingresos e incidentes de seguridad. Respalda las '
     'metas de inducción y de inspecciones.', 'INFORME-SEMESTRAL'),
    ('DESECHOS', 'Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable', 'ejecucion', 'semestral', 'sistema',
     False, False, 'cierre', 15, 'desechos', 110,
     'Generación y almacenamiento de cada desecho, entregas al gestor autorizado con su manifiesto y lo '
     'almacenado al corte. Se presenta cuando la unidad genera desechos o guarda reactivos, agroquímicos o '
     'medicamentos veterinarios. Respalda la meta de gestión de desechos.', 'INFORME-SEMESTRAL'),
    ('INVESTIGACION', 'Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros', 'evaluacion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'investigacion', 120,
     'Resultados de investigación con su proyecto, producto, responsable y respaldo verificable, y uso de '
     'la unidad para investigación. Se presenta cuando la planificación compromete la meta. Respalda la '
     'meta de resultados de investigación.', 'INFORME-SEMESTRAL'),
    ('TRANSFERENCIA', 'Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'transferencia', 130,
     'Transferencias con su destinatario y aceptación documentada, y servicios especializados atendidos. '
     'Se presenta cuando la planificación los compromete o hubo servicios atendidos. Respalda las metas de '
     'transferencia y de servicios.', 'INFORME-SEMESTRAL'),
)

# Anexos propios de planta piloto, centro experimental y observatorio. Van después de los
# comunes y antes de los condicionales.
CATALOGO_PERFILES = (
    ('PP-PRODUCCION', 'Producción de la planta piloto: órdenes, lotes y entregas',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'produccion', 90,
     'Producción realizada frente al plan, cantidades, estados y trazabilidad de lotes y entregas. '
     'Respalda la meta de lotes o procesos de producción ejecutados.', 'INFORME-SEMESTRAL'),
    ('PP-CALIDAD', 'Control de calidad de la planta piloto: controles y no conformidades',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'control-calidad', 95,
     'Parámetros, mediciones y resultados por lote u orden; liberación, rechazo y seguimiento. Respalda la '
     'meta de control de calidad de los lotes finalizados.', 'INFORME-SEMESTRAL'),
    ('CE-ENSAYOS', 'Ensayos y parcelas experimentales',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'ensayos', 90,
     'Ensayos con su objetivo, diseño, parcela, fechas y responsable; seguimiento y mediciones, y '
     'resultados respaldados. Respalda la meta de ensayos y parcelas con seguimiento.', 'INFORME-SEMESTRAL'),
    ('CE-PRODUCCION', 'Producción agropecuaria: ciclos, labores, sanidad y cosechas',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'produccion-agropecuaria', 95,
     'Ciclos productivos que no son ensayos, con su meta y lo obtenido; labores, sanidad e insumos '
     'aplicados; producción obtenida y su destino, y animales al corte. Es registro del período, sin meta '
     'propia.', 'INFORME-SEMESTRAL'),
    ('OBS-DATOS', 'Datos del observatorio: fuentes, metodología y actualización de indicadores',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'datos-observatorio', 90,
     'Fichas metodológicas, fuentes y actualizaciones con período de referencia, territorio y '
     'trazabilidad. Respalda la meta de actualización de series y fuentes del observatorio.', 'INFORME-SEMESTRAL'),
    ('OBS-BOLETINES', 'Publicaciones del observatorio: boletines y calendario',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'boletines', 92,
     'Publicaciones previstas y efectivas, fecha, responsable, indicadores y respaldo consultable. '
     'Respalda la meta de boletines, informes o bases de datos publicados.', 'INFORME-SEMESTRAL'),
    ('OBS-EVENTOS', 'Socialización del observatorio: eventos y participantes',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'eventos', 94,
     'Actividades realizadas, propósito, destinatarios, productos difundidos y respaldo. Respalda la meta '
     'de eventos de socialización de resultados.', 'INFORME-SEMESTRAL'),
)
TIPOS_CATALOGO_PERFILES = {'PP-PRODUCCION': ['plantas_piloto'], 'PP-CALIDAD': ['plantas_piloto'],
                         'CE-ENSAYOS': ['centro_experimental'], 'CE-PRODUCCION': ['centro_experimental'],
                         'OBS-DATOS': ['observatorios'],
                         'OBS-BOLETINES': ['observatorios'], 'OBS-EVENTOS': ['observatorios']}

# Lo que dejó de exigirse aparte y no debe volver a sembrarse. Las migraciones
# los desactivan (activo=False) sin borrar sus filas ni sus archivos:
# - CHEQUEO-SEGURIDAD: las listas de chequeo eran una carga semestral a mano; su
#   lugar lo ocupan el protocolo (permanente) y el registro de controles.
# - INDICADORES-PLAN: repetía columnas de la planificación de prácticas y no tenía meta; la
#   planificación ya trae la carga programada por asignatura (documentos.0024).
# - PLAN-MANTENIMIENTO: repetía los mantenimientos previstos de la planificación;
#   el plan por equipo y su ejecución van en EQUIPAMIENTO (documentos.0024).
# - PRESTAMOS-EQUIPOS: registro sin meta; queda como consulta de gestión (documentos.0024).
# - INSUMOS-CORTE: repetía existencias y lotes del inventario; sus movimientos
#   van en INVENTARIO-CORTE (documentos.0024).
# - ACCIONES-MEJORA: las acciones van en la sección 8 del informe (documentos.0025).
# Guías, evidencias de prácticas, desechos, inventario y transferencia se retiraron en
# documentos.0025 y volvieron en documentos.0027, cada uno con la exigencia que responde.
RETIRADOS = ('CHEQUEO-SEGURIDAD', 'INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE',
             'ACCIONES-MEJORA')

# Se reconocen sólo los nombres anteriores del catálogo distribuido. Permite
# presentar su denominación actual sin reescribir catálogos editados ni archivos.
NOMBRES_ESTANDAR_ANTERIORES = {
    'PLAN-COMPRAS-ANUAL': frozenset(('Plan anual de compras y presupuesto del año siguiente (firmado)',)),
    'PLANIFICACION': frozenset(('Planificación semestral de la unidad (firmada)',)),
    'INFORME-SEMESTRAL': frozenset(('Informe semestral de actividades (firmado)',)),
    'EQUIPAMIENTO': frozenset(('Equipamiento: disponibilidad y funcionalidad del período',
                               'Mantenimiento, disponibilidad y funcionalidad del equipamiento',
                               'Equipos e inventario: revisión física, mantenimiento y existencias',
                               'Plan de mantenimiento de equipos e informe de equipamiento, disponibilidad y '
                               'funcionalidad')),
    'INVENTARIO-CORTE': frozenset(('Inventario anual de equipos, software y espacios',
                                   'Inventario de equipos, software, espacios e insumos al corte')),
    'REGISTRO-USO': frozenset(('Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad',
                               'Uso de la unidad: sesiones, horas y usuarios')),
    'PRACTICAS-FT02': frozenset(('FT02 · Planificación de cada práctica',
                                 'Prácticas académicas: planificación, ejecución y guías',
                                 'Planificación semestral de ' 'las prácticas')),
    'PRACTICAS-FT03': frozenset(('FT03 · Registro de ejecución con asistencia, bitácora y evidencias',
                                 'Registros de asistencia y evidencias ' 'de las prácticas')),
    'GUIAS': frozenset(('Guías de prácticas: aprobación y vínculo con el syllabus', 'Guías de ' 'prácticas')),
    'INDUCCION-SEGURIDAD': frozenset(('Seguridad y condiciones de operación: protocolo, inducciones y controles',
                                      'Registro de inducciones y controles de seguridad',
                                      'Seguridad y desechos: inducciones, inspecciones y desechos')),
    'DESECHOS': frozenset(('Registro de desechos peligrosos y especiales',
                           'Registros de gestión de desechos ' 'peligrosos y especiales')),
    'INVESTIGACION': frozenset(('Resultados de investigación aplicada y desarrollo tecnológico',
                                'Investigación y vinculación: resultados, transferencia y servicios',
                                'Informe de resultados de investigación aplicada y ' 'desarrollo tecnológico')),
    'TRANSFERENCIA': frozenset(('Transferencia de conocimiento y servicios especializados a la sociedad',
                                'Informe de transferencia de conocimiento, tecnología y servicios '
                                'especializados a la sociedad')),
    # Nombres recortados de documentos.0027; documentos.0028 los lleva a la redacción de la universidad.
    'FICHAS-TECNICAS': frozenset(('Fichas técnicas de laboratorios, talleres, software, simuladores y '
                                  'espacios',)),
    # Anexos propios con nombre de informe (documentos.0026).
    'PP-PRODUCCION': frozenset(('Informe de producción de la planta piloto: órdenes, lotes y entregas',)),
    'PP-CALIDAD': frozenset(('Informe de control de calidad y no conformidades de la planta piloto',)),
    'CE-ENSAYOS': frozenset(('Informe de ensayos y seguimiento de parcelas experimentales',
                             'Ensayos del centro experimental: parcelas y seguimiento')),
    'OBS-DATOS': frozenset(('Registro de fuentes, metodología y actualización de indicadores del observatorio',)),
    'OBS-BOLETINES': frozenset(('Informe de publicaciones y cumplimiento del calendario del observatorio',)),
    'OBS-EVENTOS': frozenset(('Informe de socialización de resultados y vinculación del observatorio',)),
}

# Ventanas fijas en el calendario (plazo «entre dos meses»): de qué mes a qué mes.
VENTANAS = {'PLAN-COMPRAS-ANUAL': (5, 5)}


def asegurar_catalogo():
    """Siembra el catálogo vigente solo si la tabla está vacía; nunca pisa lo editado.

    No toca una tabla con filas: lo retirado sigue inactivo y lo editado por la
    institución se conserva. Los cambios del catálogo distribuido llegan por migración.
    """
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
