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
    # Cinco anexos, cada uno respalda un grupo de metas con las mismas cifras del informe
    # (documentos.0025). Las listas completas quedan como consultas del Centro de reportes.
    ('PRACTICAS-FT02', 'Prácticas académicas: planificación, ejecución y guías', 'ejecucion', 'semestral',
     'sistema', False, False, 'cierre', 15, 'planificaciones', 20,
     'Prácticas planificadas y aprobadas, prácticas ejecutadas con asistencia y evidencias, y guías de práctica '
     'vigentes, con lo que falta a cada registro para contar. Respalda las metas de prácticas planificadas, '
     'prácticas ejecutadas y guías.', 'INFORME-SEMESTRAL'),
    ('REGISTRO-USO', 'Uso de la unidad: sesiones, horas y usuarios', 'ejecucion', 'semestral', 'sistema', False,
     False, 'cierre', 15, 'reservas', 10,
     'Sesiones registradas y atendidas del período, horas de uso efectivo y usuarios, por propósito, con el detalle '
     'de las sesiones atendidas. Respalda las metas de registro de sesiones y de uso efectivo.',
     'INFORME-SEMESTRAL'),
    ('INDUCCION-SEGURIDAD', 'Seguridad y desechos: inducciones, inspecciones y desechos', 'ejecucion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'seguridad', 70,
     'Inspecciones mensuales, inducciones y habilitaciones de usuarios nuevos, ingresos a la unidad y desechos '
     'peligrosos y especiales generados y entregados. Respalda las metas de inducción, inspecciones y gestión '
     'de desechos.', 'INFORME-SEMESTRAL'),
    ('EQUIPAMIENTO', 'Equipos e inventario: revisión física, mantenimiento y existencias', 'evaluacion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'equipamiento', 40,
     'Acta de revisión física del inventario, datos pendientes de los equipos, mantenimientos del período frente '
     'al programa crítico (80 %), equipos fuera de servicio e insumos bajo su mínimo. Respalda las metas de '
     'revisión del inventario y de mantenimiento.', 'INFORME-SEMESTRAL'),
    ('INVESTIGACION', 'Investigación y vinculación: resultados, transferencia y servicios', 'evaluacion',
     'semestral', 'sistema', False, False, 'cierre', 15, 'investigacion', 60,
     'Solo cuando la planificación compromete estas metas: productos de investigación, transferencias y '
     'servicios entregados y aceptados, con su respaldo. Respalda las metas de investigación, transferencia y '
     'servicios.', 'INFORME-SEMESTRAL'),
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

# Lo que dejó de exigirse aparte y no debe volver a sembrarse. Las migraciones
# los desactivan (activo=False) sin borrar sus filas ni sus archivos:
# - CHEQUEO-SEGURIDAD: las listas de chequeo eran una carga semestral a mano; su
#   lugar lo ocupan el protocolo (permanente) y el registro de controles.
# - INDICADORES-PLAN: repetía columnas del FT02 y no tenía meta; la planificación
#   ya trae la carga programada por asignatura (documentos.0024).
# - PLAN-MANTENIMIENTO: repetía los mantenimientos previstos de la planificación;
#   la ejecución y la meta del 80 % van en EQUIPAMIENTO (documentos.0024).
# - PRESTAMOS-EQUIPOS: registro sin meta; queda como consulta de gestión (documentos.0024).
# - INSUMOS-CORTE: repetía existencias y lotes del inventario; sus movimientos
#   van en INVENTARIO-CORTE (documentos.0024).
# - PRACTICAS-FT03 y GUIAS: van con la planificación de prácticas en un solo anexo de
#   prácticas académicas (documentos.0025).
# - DESECHOS: va con las inducciones e inspecciones en el anexo de seguridad (documentos.0025).
# - INVENTARIO-CORTE: el acta y el resumen van en el anexo de equipos e inventario; la lista
#   completa es consulta del Centro de reportes (documentos.0025).
# - TRANSFERENCIA: va con la investigación, que solo se presenta si el plan la compromete
#   (documentos.0025).
# - ACCIONES-MEJORA: las acciones van en la sección 8 del informe (documentos.0025).
RETIRADOS = ('CHEQUEO-SEGURIDAD', 'INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE',
             'PRACTICAS-FT03', 'GUIAS', 'DESECHOS', 'INVENTARIO-CORTE', 'TRANSFERENCIA', 'ACCIONES-MEJORA')

# Se reconocen sólo los nombres anteriores del catálogo distribuido. Permite
# presentar su denominación actual sin reescribir catálogos editados ni archivos.
NOMBRES_ESTANDAR_ANTERIORES = {
    'PLAN-COMPRAS-ANUAL': frozenset(('Plan anual de compras y presupuesto del año siguiente (firmado)',)),
    'PLANIFICACION': frozenset(('Planificación semestral de la unidad (firmada)',)),
    'INFORME-SEMESTRAL': frozenset(('Informe semestral de actividades (firmado)',)),
    'EQUIPAMIENTO': frozenset(('Equipamiento: disponibilidad y funcionalidad del período',
                               'Mantenimiento, disponibilidad y funcionalidad del equipamiento')),
    'INVENTARIO-CORTE': frozenset(('Inventario anual de equipos, software y espacios',)),
    'REGISTRO-USO': frozenset(('Registro de uso del período: sesiones, horas y usuarios por tipo y finalidad',)),
    'PRACTICAS-FT02': frozenset(('FT02 · Planificación de cada práctica',)),
    'INDUCCION-SEGURIDAD': frozenset(('Seguridad y condiciones de operación: protocolo, inducciones y controles',
                                      'Registro de inducciones y controles de seguridad')),
    'INVESTIGACION': frozenset(('Resultados de investigación aplicada y desarrollo tecnológico',)),
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
