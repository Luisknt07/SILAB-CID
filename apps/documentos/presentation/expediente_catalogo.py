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
     'ninguno', 0, '', 10, 'Resolución que aprueba la unidad y sus reformas; se hereda cada año.', ''),
    ('PROTOCOLO-BIOSEGURIDAD', 'Protocolo de seguridad y condiciones de operación', 'planeacion', 'unica',
     'ambos', True, False, 'ninguno', 0, 'protocolo', 15,
     'Se elabora con el editor de la unidad: alcance, responsables, riesgos, controles, operación y emergencias. '
     'Se envía y aprueba en la plataforma con QR; se conserva mientras siga vigente. '
     'La bioseguridad y otras medidas específicas se incluyen cuando correspondan a las actividades.', ''),

    # -- Una vez por año: necesidades del año siguiente, convocatoria ordinaria en mayo -----
    ('PLAN-COMPRAS-ANUAL', 'Plan anual de compras y presupuesto para el año siguiente', 'planeacion',
     'anual', 'ambos', True, False, 'meses', 0, 'compras', 40,
     'Lo que la unidad necesitará comprar el año siguiente, con su justificación frente al inventario, la vida '
     'útil de los equipos y sus actividades. Se prepara con el editor y se emite en la plataforma para '
     'revisión y aprobación; la ventana de entrega se consulta en el expediente. Si no requiere compras, lo justifica.', ''),

    # -- Apertura del período: la planificación firmada y sus anexos ---------------------------
    ('PLANIFICACION', 'Planificación semestral de actividades de la unidad', 'planeacion', 'semestral', 'ambos', True,
     False, 'inicio', 15, 'planificacion', 20,
     'Se redacta con el editor guiado: el sistema llena lo que ya sabe (datos de la unidad, espacios, servicios, '
     'inventario) y la unidad revisa objetivos, diagnóstico, actividades, metas y recursos. Al emitir se registra '
     'al responsable; la aprobación se consulta mediante el mismo QR.', ''),
    ('INDICADORES-PLAN', 'Plan semestral de prácticas por asignatura', 'planeacion', 'semestral', 'sistema',
     False, False, 'inicio', 15, 'asignaturas', 30,
     'Un documento consolidado del semestre reúne fecha, escenario y responsable de las prácticas por '
     'asignatura. Respalda la planificación semestral; la cantidad de prácticas aprobadas se mide en FT02, '
     'sin otra meta ni puntos independientes por este anexo.', 'PLANIFICACION'),
    ('PLAN-MANTENIMIENTO', 'Plan anual de mantenimiento preventivo y correctivo', 'planeacion', 'anual', 'sistema',
     False, False, 'inicio', 15, 'mantenimiento', 50,
     'Respalda la planificación del período A con equipos, criticidad, intervenciones, responsables y calendario. '
     'Su ejecución se contrasta con las intervenciones exigibles y las metas aprobadas.', 'PLANIFICACION'),

    # -- Cierre del período: el informe firmado y sus anexos de evidencia ----------------------
    ('INFORME-SEMESTRAL', 'Informe semestral de actividades y cumplimiento de la planificación', 'evaluacion', 'semestral', 'ambos', True,
     False, 'cierre', 15, 'informe', 10,
     'Se redacta con el editor guiado sobre lo que el sistema registró en el período: cumplimiento del plan, uso, '
     'logros, dificultades y acciones de mejora. Al emitir registra al responsable y conserva las evidencias '
     'del período; la aprobación se consulta mediante el mismo QR. Los plazos se consultan en el expediente.', ''),
    ('REGISTRO-USO', 'Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'reservas', 10,
     'Lo produce el sistema con las reservas registradas; el 100 % de las sesiones debe pasar por la plataforma.',
     'INFORME-SEMESTRAL'),
    ('PRACTICAS-FT02', 'FT02 · Planificación de cada práctica', 'ejecucion', 'semestral', 'sistema', False, False,
     'cierre', 15, 'planificaciones', 20, '', 'INFORME-SEMESTRAL'),
    ('PRACTICAS-FT03', 'FT03 · Registro de ejecución con asistencia, bitácora y evidencias', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'ejecuciones', 30, '', 'INFORME-SEMESTRAL'),
    ('GUIAS', 'Guías de prácticas: aprobación y vínculo con el syllabus', 'ejecucion', 'semestral', 'sistema',
     False, False, 'cierre', 15, 'guias', 40, 'Guías vigentes utilizadas en las prácticas programadas, con aprobación y vínculo con el syllabus.',
     'INFORME-SEMESTRAL'),
    ('PRESTAMOS-EQUIPOS', 'Registro de préstamos de equipos', 'ejecucion', 'semestral', 'sistema', False, False,
     'cierre', 15, 'prestamos', 50,
     'Quién retira, cuándo, para qué actividad y cuándo devuelve, con el estado del equipo. '
     'Sale de los préstamos registrados en la consola; el externo además exige su acta.', 'INFORME-SEMESTRAL'),
    ('INDUCCION-SEGURIDAD', 'Registro de inducciones y controles de seguridad', 'ejecucion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'seguridad', 70, '', 'INFORME-SEMESTRAL'),
    ('DESECHOS', 'Registro de desechos peligrosos y especiales', 'ejecucion', 'semestral', 'sistema', False, False,
     'cierre', 15, 'desechos', 80, '', 'INFORME-SEMESTRAL'),
    ('EQUIPAMIENTO', 'Equipamiento: disponibilidad y funcionalidad del período', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'equipamiento', 40, '', 'INFORME-SEMESTRAL'),
    ('INSUMOS-CORTE', 'Reactivos e insumos: existencias y movimientos del período', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'inventario', 50,
     'Existencias al corte, lotes aplicables, entradas y consumos del período; complementa el inventario integral de recursos.', 'INFORME-SEMESTRAL'),
    ('INVENTARIO-CORTE', 'Inventario anual de equipos, software y espacios', 'evaluacion', 'anual',
     'sistema', False, False, 'cierre', 15, 'recursos', 30,
     'Un corte al año, con el informe del período B: altas, bajas y fuera de servicio.', 'INFORME-SEMESTRAL'),
    ('INVESTIGACION', 'Resultados de investigación aplicada y desarrollo tecnológico', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'investigacion', 60,
     'Productos obtenidos, proyecto, responsable y respaldo verificable. El uso para investigación y titulación se muestra por separado.',
     'INFORME-SEMESTRAL'),
    ('TRANSFERENCIA', 'Transferencia de conocimiento y servicios especializados a la sociedad', 'evaluacion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'transferencia', 70,
     'Entregable, destinatario y aceptación documentada. Las solicitudes de servicio y reservas se muestran por separado.', 'INFORME-SEMESTRAL'),
    ('ACCIONES-MEJORA', 'Seguimiento de acciones de mejora', 'mejora', 'semestral', 'sistema', False, False, 'cierre',
     15, 'mejora', 10,
     'Se consolida desde las acciones registradas en los informes semestrales: hallazgo, acción, responsable, '
     'plazo y estado.', 'INFORME-SEMESTRAL'),
)

# Evidencias propias de las otras implementaciones. Conservan fuentes y
# nombres distintos de los formatos de prácticas de los laboratorios.
CATALOGO_PERFILES = (
    ('PP-PRODUCCION', 'Informe de producción de la planta piloto: órdenes, lotes y entregas',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'produccion', 90,
     'Producción realizada frente al plan, cantidades, estados y trazabilidad de lotes y entregas.', 'INFORME-SEMESTRAL'),
    ('PP-CALIDAD', 'Informe de control de calidad y no conformidades de la planta piloto',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'control-calidad', 95,
     'Parámetros, mediciones y resultados por lote u orden; liberación, rechazo y seguimiento.', 'INFORME-SEMESTRAL'),
    ('CE-ENSAYOS', 'Informe de ensayos y seguimiento de parcelas experimentales',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'ensayos', 90,
     'Objetivo, escenario, fechas, manejo, mediciones y resultados respaldados de los ensayos.', 'INFORME-SEMESTRAL'),
    ('OBS-DATOS', 'Registro de fuentes, metodología y actualización de indicadores del observatorio',
     'ejecucion', 'semestral', 'sistema', False, False, 'cierre', 15, 'datos-observatorio', 20,
     'Fichas metodológicas, fuentes y actualizaciones con período de referencia, territorio y trazabilidad.', 'INFORME-SEMESTRAL'),
    ('OBS-BOLETINES', 'Informe de publicaciones y cumplimiento del calendario del observatorio',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'boletines', 30,
     'Publicaciones previstas y efectivas, fecha, responsable, indicadores y respaldo consultable.', 'INFORME-SEMESTRAL'),
    ('OBS-EVENTOS', 'Informe de socialización de resultados y vinculación del observatorio',
     'evaluacion', 'semestral', 'sistema', False, False, 'cierre', 15, 'eventos', 40,
     'Actividades realizadas, propósito, destinatarios, productos difundidos y respaldo.', 'INFORME-SEMESTRAL'),
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
