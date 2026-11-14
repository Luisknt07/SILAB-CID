"""Orientación del expediente a partir de su catálogo y de sus estados reales.

No genera documentos ni decide obligatoriedad, notas o aprobaciones. La guía
reutiliza el árbol ya leído por la pantalla y enlaza los circuitos existentes.
"""
from urllib.parse import urlencode

from django.urls import reverse

from apps.documentos.presentation.perfil_unidades import base_de
from apps.gestion_unidades.presentation.reportes_alcance import notas_del_reporte


PERFILES = {
    'laboratorios': ('Laboratorio', 'Docencia, uso de recursos, investigación y servicios'),
    'plantas_piloto': ('Planta piloto', 'Producción, calidad, prácticas y servicios'),
    'centro_experimental': ('Centro experimental', 'Ensayos, escenarios y actividades de campo'),
    'observatorios': ('Observatorio', 'Fuentes, indicadores, publicaciones y vinculación'),
}

# Propósito y circuito de origen; los nombres y exigencias pertenecen al
# catálogo institucional, no a esta ayuda. Ninguna consulta agrega una meta.
REPORTES = {
    'asignaturas': ('apertura', 'Organizar las prácticas por asignatura y comparar lo previsto con su ejecución.',
                    'Asignaturas, syllabus y programación de prácticas.', 'practicas'),
    'planificaciones': ('apertura', 'Preparar cada práctica antes de realizarla, con escenario, responsable y recursos.',
                        'Planificación de prácticas (FT02).', 'practicas'),
    'ejecuciones': ('registros', 'Documentar las prácticas realizadas, su asistencia, resultados y evidencias.',
                    'Ejecución y validación de prácticas (FT03).', 'practicas'),
    'reservas': ('registros', 'Demostrar el uso y la atención efectiva de la unidad durante el período.',
                 'Reservas y atenciones cerradas; solicitudes pendientes por separado.', 'reservas'),
    'visitas': ('registros', 'Consultar las visitas guiadas, sus recorridos y la asistencia registrada.',
                'Reservas de visitas internas y externas, sus responsables, horarios y participantes.', 'reservas'),
    'uso-capacidad': ('registros', 'Comparar capacidad disponible, uso efectivo y compromiso de horas, con seguimiento semanal y mensual.',
                      'Jornadas, capacidad operativa con fundamento, bloqueos y ejecuciones con horario y asistencia reales.', 'reportes'),
    'aula': ('registros', 'Consultar ejercicios y resultados de aprendizaje registrados en el aula.',
              'Intentos y resultados del aula de aprendizaje.', 'practicas'),
    'mantenimiento': ('apertura', 'Relacionar el plan de mantenimiento con las órdenes, su ejecución y las incidencias.',
                      'Plan de mantenimiento, órdenes e incidencias de equipos.', 'mantenimiento'),
    'equipamiento': ('registros', 'Revisar la disponibilidad y las limitaciones de los equipos durante el período.',
                      'Inventario y cambios de estado del equipamiento.', 'recursos'),
    'retiros': ('cierre', 'Dar seguimiento a equipos retirados y sus sustituciones con su justificación e historial.',
                 'Ficha de cada equipo, baja técnica, sustituto y eventos de su ciclo de vida.', 'recursos'),
    'recursos': ('registros', 'Conocer los recursos de la unidad y respaldar su revisión física.',
                  'Equipos, software, espacios e inventario de la unidad.', 'recursos'),
    'inventario': ('registros', 'Conciliar existencias, entradas, consumos y necesidades de reposición.',
                    'Insumos y reactivos, lotes y movimientos registrados.', 'recursos'),
    'prestamos': ('registros', 'Controlar las salidas de equipos, sus plazos, actas y devoluciones.',
                   'Préstamos y devoluciones de equipos.', 'recursos'),
    'guias': ('registros', 'Identificar las guías vigentes y su aprobación y vínculo con el syllabus.',
               'Guías de prácticas, versiones, aprobación y asignaturas.', 'practicas'),
    'seguridad': ('registros', 'Reunir inducciones y controles de las condiciones de operación.',
                   'Seguridad y acceso: inducciones, inspecciones y controles.', 'seguridad'),
    'desechos': ('registros', 'Seguir los desechos desde su generación hasta su almacenamiento y entrega.',
                  'Registros de desechos y sus respaldos de entrega.', 'seguridad'),
    'investigacion': ('registros', 'Respaldar productos de investigación y desarrollo efectivamente obtenidos.',
                       'Resultados de investigación y sus evidencias verificadas.', 'reportes'),
    'transferencia': ('registros', 'Respaldar entregables, destinatarios y aceptación de los servicios o transferencias.',
                       'Resultados de transferencia y servicios, con sus respaldos.', 'reportes'),
    'cursos': ('registros', 'Consultar la oferta formativa, ediciones, inscripciones y certificados.',
                'Cursos propios y actividades externas identificadas por plataforma y organizador.', 'cursos'),
    'finanzas': ('registros', 'Seguir ingresos y gastos de los servicios sin equipararlos con su impacto.',
                  'Movimientos financieros registrados en la unidad.', ''),
    'produccion': ('registros', 'Revisar órdenes, lotes y entregas de producción frente al plan.',
                     'Órdenes y lotes, consumos y salidas de la planta piloto.', ''),
    'procesos': ('registros', 'Conservar la trazabilidad de etapas, tiempos y puntos críticos de los procesos.',
                   'Procesos y etapas registrados en las órdenes de producción.', ''),
    'calidad': ('registros', 'Consultar controles de calidad y no conformidades de la producción.',
                  'Parámetros, mediciones y no conformidades de los lotes.', ''),
    'control-calidad': ('registros', 'Respaldar las mediciones y decisiones de calidad de los lotes.',
                          'Plan de calidad, mediciones y no conformidades de la planta piloto.', ''),
    'ensayos': ('registros', 'Relacionar el diseño de los ensayos con sus registros de campo y resultados.',
                 'Ensayos y escenarios experimentales, mediciones y evidencias.', ''),
    'datos-observatorio': ('registros', 'Mantener trazables las fuentes, metodologías y actualizaciones de indicadores.',
                            'Fuentes de datos, fichas metodológicas y valores publicados.', ''),
    'boletines': ('registros', 'Comparar el calendario editorial con las publicaciones efectivamente realizadas.',
                   'Publicaciones, archivos o enlaces, fuentes y fechas del observatorio.', ''),
    'eventos': ('registros', 'Respaldar la socialización de resultados y sus destinatarios.',
                 'Eventos de vinculación del observatorio y sus evidencias.', ''),
    'mejora': ('cierre', 'Seguir hallazgos, compromisos, responsables, plazos y evidencia de cierre.',
                'Acciones del informe semestral y del trámite de mejora, con sus seguimientos identificados por separado. '
                'Este anexo no sustituye el informe de mejora continua que se tramita cuando corresponde.', 'reportes'),
    'auditoria': ('cierre', 'Consultar quién realizó cada cambio y cuándo para revisar incidencias y decisiones.',
                   'Eventos de auditoría de la unidad.', ''),
}

PRINCIPALES = {
    'RESOLUCION-CREACION': (
        'base', 'Acreditar la creación, identidad y alcance de la unidad.',
        'Documento institucional emitido por la autoridad competente.',
        'Aprobación inicial del documento y su alcance; no se califica con una rúbrica ni se vuelve a pedir cada semestre.'),
    'PROTOCOLO-BIOSEGURIDAD': (
        'base', 'Definir las reglas de seguridad y operación según las actividades de la unidad.',
        'Editor del protocolo: alcance, responsables, riesgos, controles y emergencias; permite cargar un protocolo existente.',
        'Envío y aprobación en la plataforma con QR. Se conserva mientras siga vigente; las inducciones e inspecciones se comprueban por separado.'),
    'PLAN-COMPRAS-ANUAL': (
        'base', 'Priorizar las necesidades del próximo año según la capacidad y el estado de los recursos.',
        'Editor del plan anual de necesidades para el año siguiente; convocatoria ordinaria en mayo. '
        'Incluye sugerencias del inventario y exportación al formato de requerimientos de la Universidad.',
        'El sistema comprueba integridad y correspondencia. No requerir compras puede justificarse sin penalización. '
        'La prioridad de inversión consulta el último semestre cerrado, sus metas ejecutadas y las limitaciones argumentadas; '
        'es independiente de la conformidad y no autoriza gasto.'),
    'PLANIFICACION': (
        'apertura', 'Definir actividades, metas realistas, responsables, recursos y calendario del semestre.',
        'Editor de actividades, metas, capacidad y cobertura de recursos del semestre. Consulta las necesidades '
        'anuales del año vigente sin volver a capturar sus cantidades y costos.',
        'El sistema comprueba la integridad y coherencia del plan. La aprobación del plan no acredita actividades ejecutadas.'),
    'INFORME-SEMESTRAL': (
        'cierre', 'Comparar los resultados del semestre con la planificación y explicar brechas y acciones.',
        'Editor del informe, indicadores y evidencias del período; anexos conservados al enviar.',
        'El cierre utiliza la planificación y las evidencias verificables; conserva faltantes y resultados parciales. Dirección atiende excepciones y puede revisar la decisión.'),
}

GRUPOS = (
    ('base', 'Vigencia y plan anual', 'Conserva la base institucional y prepara las necesidades del próximo año.',
     'Documentos permanentes: se actualizan si cambia su contenido o alcance. Compras una vez al año.', '#entregas-documentos', 'Ver documentos principales'),
    ('apertura', 'Planificar el semestre', 'Define lo que la unidad puede realizar y programa su ejecución.',
     'Antes de las actividades; los cambios deben quedar justificados.', '#entregas-documentos', 'Ver planificación'),
    ('registros', 'Evidencias del período', 'Registra la actividad una vez y consulta los informes que la respaldan.',
     'Durante el semestre, según las funciones y la planificación de la unidad.', '#reportes-anexos', 'Ver evidencias y metas'),
    ('cierre', 'Cierre y seguimiento', 'Contrasta metas y resultados, explica las brechas y sigue los compromisos.',
     'Al cierre y hasta resolver los compromisos pendientes.', '#resultado-seguimiento', 'Ver resultado y seguimiento'),
)

ORIGENES = {
    'cursos': ('practicas', dict(view='cursos')),
    'inventario': ('inventario', dict(view='recursos', modo_recursos='inventario')),
    'finanzas': ('finanzas', dict(view='recursos', modo_recursos='finanzas')),
    'datos-observatorio': ('reportes', dict(view='obs_indicadores')),
    'boletines': ('reportes', dict(view='obs_publicaciones')),
    'produccion': ('produccion', dict(view='produccion')),
    'procesos': ('produccion', dict(view='produccion')),
    'calidad': ('produccion', dict(view='produccion')),
    'control-calidad': ('produccion', dict(view='produccion')),
}


def _accion(etiqueta, url, tipo='pagina', **extra):
    return dict(etiqueta=etiqueta, url=url, tipo=tipo, **extra)


def _frecuencia(exigido, unidad):
    if exigido.periodicidad_para(unidad) == 'unica':
        return 'Una vez; se reutiliza mientras su identidad, alcance y aprobación sigan vigentes.'
    etiqueta = dict(exigido.PERIODICIDADES).get(exigido.periodicidad_para(unidad), exigido.periodicidad_para(unidad))
    return f'{etiqueta}. Según la aplicabilidad y los plazos configurados en el expediente.'


def construir_guia_reportes(unidad, anio, corte, inicio, fin, documentos, entregas, usuario=None):
    """Construye navegación sin leer archivos ni escribir actividad o estados."""
    from apps.gestion_unidades.presentation.gestion_reportes import familias_para, _registra_produccion
    from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad

    base = base_de(unidad)
    perfil, enfoque = PERFILES.get(base, ('Unidad', 'Documentos y seguimiento de sus actividades'))
    expediente_url = reverse('gestion_expediente_unidad', args=[unidad.slug])
    consulta_pdf = reverse('gestion_reporte_unidad_pdf', args=[unidad.slug])
    consulta_html = reverse('gestion_reporte_unidad', args=[unidad.slug])
    permisos = permisos_operativos_unidad(usuario, unidad)
    operar = permisos.get('reportes', False)
    por_carpeta = {clave: [] for clave, *_ in GRUPOS}
    todos = list(documentos)
    from .organizacion_expediente import contextualizar_soportes_planificacion
    contextualizar_soportes_planificacion(todos)
    padres = {(d.exigido_id, d.corte): d for d in todos}

    def ruta(documento, **extra):
        return expediente_url + '?' + urlencode(dict(
            anio=documento.anio, corte=documento.corte,
            gestionar=documento.pk or documento.exigido.codigo, **extra))

    def detalles(documento):
        lectura = getattr(documento, 'resumen_interfaz', {}) or {}
        paso = lectura.get('paso_unidad', '')
        if paso == 'Esperar apertura del período':
            paso = ('Prepara los registros que correspondan; el anexo se conserva al enviar la entrega.'
                    if documento.exigido.es_anexo else
                    'Prepara el borrador; el envío se habilita desde ' + documento.abre_el.strftime('%d/%m/%Y') + '.'
                    if documento.abre_el else
                    'Prepara la información y consulta la apertura de la entrega.')
        return dict(estado=lectura.get('estado_unidad', ''),
                    proximo_paso=paso)

    def base_item(documento):
        requisitos = documento.requisitos_documentales
        if isinstance(requisitos, str):
            requisitos = (requisitos,)
        soporte = getattr(documento, 'soporte_planificacion', None)
        return dict(codigo=documento.exigido.codigo, nombre=documento.nombre_documental,
                    alcance=' '.join(requisitos) + (' ' + soporte['descripcion'] if soporte else ''),
                    soporte_planificacion=soporte,
                    frecuencia=_frecuencia(documento.exigido, unidad),
                    **detalles(documento))

    for documento in entregas:
        exigido = documento.exigido
        clave, proposito, origen, validacion = PRINCIPALES.get(exigido.codigo, (
            'base' if exigido.periodicidad in ('unica', 'anual') else 'cierre',
            'Preparar la entrega definida por el catálogo institucional.',
            'Documento y respaldos requeridos en el expediente.',
            'Se aplica el circuito de control configurado para este documento.'))
        acciones = [_accion('Ver entrega y seguimiento', ruta(documento), 'entrega')]
        if documento.recurso_id:
            acciones.append(_accion('Ver documento archivado',
                reverse('recurso_unidad', args=[documento.recurso_id]), 'documento'))
        if operar and exigido.redactable and documento.pk and documento.estado != 'validado':
            acciones.append(_accion('Editar documento',
                reverse('redactar_documento_expediente', args=[unidad.slug, documento.pk]), 'editor'))
        por_carpeta[clave].append(dict(**base_item(documento), proposito=proposito,
            prioridad='Documento principal', origen=origen, validacion=validacion,
            seguimiento='Consulta aquí su estado, observaciones y plazo efectivo. Los documentos permanentes vigentes se conservan para los siguientes períodos.'
                        if exigido.periodicidad == 'unica' else
                        'El estado, las comprobaciones y el plazo efectivo se consultan en la entrega; el avance operativo se contrasta con sus evidencias.',
            acciones=acciones))

    # Las categorías propias del perfil también aparecen aunque todavía no
    # tengan un archivo archivado. No se inventa un estado de cumplimiento.
    fuentes = {}
    for documento in todos:
        if documento.exigido.es_anexo and (not corte or documento.corte == corte
                or documento.exigido.periodicidad_para(unidad) == 'anual'):
            fuente = documento.exigido.fuente_reporte
            fuentes.setdefault(fuente, []).append(documento)
    categorias = dict(opcion for _, opciones in familias_para(unidad) for opcion in opciones)
    for codigo, nombre in categorias.items():
        clave, proposito, origen, modulo = REPORTES.get(codigo, (
            'registros', 'Consultar los registros de esta actividad.', 'Registros de la unidad.', ''))
        documentos_fuente = fuentes.get(codigo, [])
        documento = next((d for d in documentos_fuente if d.corte == corte),
                         documentos_fuente[0] if documentos_fuente else None)
        consulta = urlencode(dict(categoria_reporte=codigo, desde=inicio.isoformat(), hasta=fin.isoformat()))
        acciones = [_accion('Ver informe y exportar', consulta_html + '?' + consulta),
                    _accion('Vista previa PDF', consulta_pdf + '?' + consulta, 'consulta',
                            descarga=consulta_pdf + '?' + consulta,
                            rango=consulta_pdf + '?' + urlencode(dict(categoria_reporte=codigo)),
                            desde=inicio.isoformat(), hasta=fin.isoformat())]
        permiso_origen, parametros_origen = ORIGENES.get(codigo, (modulo, dict(view=modulo)))
        origen_habilitado = permiso_origen != 'produccion' or _registra_produccion(unidad)
        if operar and permiso_origen and origen_habilitado and permisos.get(permiso_origen, False):
            acciones.append(_accion('Ir al registro de origen',
                reverse('gestion_unidad', args=[unidad.slug]) + '?' + urlencode(parametros_origen), 'registro'))
        if documento:
            item = base_item(documento)
            if not corte and len(documentos_fuente) > 1:
                # La consulta anual no hereda el estado de un solo semestre.
                item.update(estado='', proximo_paso='Consulta cada entrega semestral y sus anexos conservados.')
            for fuente in documentos_fuente:
                sufijo = ' · ' + fuente.etiqueta_corte if len(documentos_fuente) > 1 else ''
                padre = padres.get((fuente.exigido.anexo_de_id, fuente.corte))
                if padre:
                    acciones.append(_accion('Ver entrega que lo conserva' + sufijo, ruta(padre), 'entrega'))
                if fuente.recurso_id:
                    acciones.append(_accion('Ver anexo archivado' + sufijo,
                        reverse('recurso_unidad', args=[fuente.recurso_id]), 'documento'))
            prioridad = 'Evidencia de la planificación' if clave == 'apertura' else 'Evidencia del cierre'
            seguimiento = ('Se conserva como anexo de ' + documento.exigido.anexo_de.nombre_para(unidad)
                + '. La consulta al día puede cambiar; el anexo enviado conserva los registros de la entrega.')
            if getattr(documento, 'soporte_planificacion', None):
                prioridad = 'Soporte de la planificación semestral'
                seguimiento += ' ' + documento.soporte_planificacion['descripcion']
        else:
            item = dict(codigo=codigo, nombre=nombre,
                alcance=' '.join(notas_del_reporte(codigo)) or proposito,
                frecuencia='Consulta cuando la actividad aplique; no crea una entrega o meta adicional.',
                estado='', proximo_paso='')
            prioridad = 'Consulta de seguimiento' if codigo in ('mejora', 'retiros', 'auditoria') else 'Consulta de apoyo'
            seguimiento = 'Apoya la gestión y el seguimiento. Consultar o descargar el informe no registra una entrega ni acredita cumplimiento.'
        item.update(proposito=proposito, prioridad=prioridad, origen=origen, seguimiento=seguimiento,
            validacion='Presenta los controles y limitaciones de los registros; no verifica por sí solo el contenido de un adjunto ni convierte una declaración en resultado acreditado.',
            acciones=acciones)
        por_carpeta[clave].append(item)

    # Un documento propio o histórico no desaparece si su fuente no tiene un
    # proveedor de consulta actual. El archivo y su circuito siguen accesibles.
    for documento in todos:
        if not documento.exigido.es_anexo or documento.exigido.fuente_reporte in categorias:
            continue
        if corte and documento.corte != corte and documento.exigido.periodicidad_para(unidad) != 'anual':
            continue
        padre = padres.get((documento.exigido.anexo_de_id, documento.corte))
        acciones = [_accion('Ver entrega que lo conserva', ruta(padre or documento), 'entrega')]
        if documento.recurso_id:
            acciones.append(_accion('Ver anexo archivado', reverse('recurso_unidad', args=[documento.recurso_id]), 'documento'))
        por_carpeta['registros'].append(dict(**base_item(documento),
            proposito='Conservar la evidencia específica definida para esta unidad.', prioridad='Evidencia del expediente',
            origen='Catálogo y archivo del expediente.', validacion='Sigue las comprobaciones y decisiones de su entrega.',
            seguimiento='Consulta su archivo y observaciones en la entrega de origen.', acciones=acciones))

    grupos = []
    for clave, titulo, resumen, cuando, ancla, etiqueta in GRUPOS:
        items = por_carpeta[clave]
        pendientes = [item for item in items if item.get('estado') in (
            'Pendiente', 'Pendiente de registro', 'Pendiente de aprobación', 'Observado',
            'Falta firma', 'Borrador', 'Listo para enviar')]
        grupos.append(dict(clave=clave, titulo=titulo, resumen=resumen, cuando=cuando,
            items=items, conteo=len(items), pendientes=len(pendientes),
            proximo_paso=pendientes[0]['proximo_paso'] if pendientes else '',
            accion=_accion(etiqueta, ancla, 'ancla')))
    return dict(perfil=dict(nombre=perfil, enfoque=enfoque), grupos=grupos)
