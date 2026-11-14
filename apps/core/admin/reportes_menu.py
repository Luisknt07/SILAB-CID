"""Orden de lectura del menú de reportes, después de aplicar sus permisos."""
from django.utils.translation import gettext


TIPOS_ACCESO = {
    'evaluacion': ('Panel de evaluación', 'Revisa los documentos entregados y los resultados de las unidades; desde aquí se toman las decisiones.'),
    'documentos': ('Documentos y remisiones', 'Archivos entregados por las unidades e informes que se revisan, archivan o remiten.'),
    'sistema': ('Consulta del sistema', 'Resumen o estadística obtenido de los registros; no constituye una entrega documental adicional.'),
    'gestion': ('Gestión operativa', 'Registros y herramientas para atender alertas, movimientos e identificación de equipos.'),
}
TIPO_POR_ACCESO = {
    'reportes-cumplimiento-expediente': 'evaluacion',
    'reportes-evidencias-por-tipo': 'documentos',
    'reportes-necesidades-decanato': 'documentos',
    'documentos_informemejora_changelist': 'documentos',
    **dict.fromkeys((
        'reportes-expediente-por-tipo', 'equipamiento_institucional',
        'recursos_unidadequipo_transparencia', 'reportes-institucional',
        'gestion_unidades_reporteoperativounidad_changelist', 'reportes_centros_id',
        'reservas-estadisticas', 'reservas-reporte-uso', 'reservas-reporte-listado',
    ), 'sistema'),
    **dict.fromkeys(('AlertaUsoEquipo', 'TraspasoEquipo', 'lector_equipos'), 'gestion'),
}


def _tipo_acceso(codigo):
    nombre, descripcion = TIPOS_ACCESO[codigo]
    return dict(codigo=codigo, nombre=gettext(nombre), descripcion=gettext(descripcion))


CATEGORIAS_REPORTES = (
    ('evaluacion', 'Evaluación y seguimiento', 'Revisión de entregas y acciones posteriores a la evaluación.', (
        ('Entregas y mejora', 'Consulta el historial de entregas y el seguimiento de las correcciones.', (
            'reportes-expediente-por-tipo', 'documentos_informemejora_changelist')),
    )),
    ('compras_equipos', 'Compras y equipos', 'Necesidades de inversión, recursos existentes y aprovechamiento.', (
        ('Necesidades e inventario institucional', 'Revisa las solicitudes y los equipos disponibles antes de decidir una compra.', (
            'reportes-necesidades-decanato', 'equipamiento_institucional')),
        ('Uso y redistribución', 'Identifica el uso de cada equipo y atiende sus alertas o posibles traspasos.', (
            'recursos_unidadequipo_transparencia', 'AlertaUsoEquipo', 'TraspasoEquipo')),
    )),
    ('actividad', 'Actividad y resultados', 'Consultas para ampliar el análisis de las unidades.', (
        ('Resultados y estado de las unidades', 'Consulta la actividad del período y la condición operativa de las unidades.', (
            'reportes-institucional', 'gestion_unidades_reporteoperativounidad_changelist')),
        ('Reservas y usuarios', 'Analiza la demanda, quién utiliza las unidades y las solicitudes registradas.', (
            'reservas-estadisticas', 'reservas-reporte-uso', 'reservas-reporte-listado')),
    )),
    ('apoyo', 'Herramientas de apoyo', 'Accesos para tareas puntuales de consulta.', (
        ('Identificación de equipos', 'Abre la ficha de un equipo mediante su etiqueta o código QR.', ('lector_equipos',)),
    )),
)


def organizar_reportes(modelos):
    """No concede accesos ni calcula indicadores: sólo organiza tarjetas visibles.

    El listado plano del administrador se conserva. Cada tarjeta se presenta
    una vez; una herramienta nueva sin clasificación sigue siendo accesible.
    """
    tarjetas = [dict(modelo) for modelo in modelos]
    descripciones = {
        'AlertaUsoEquipo': 'Atiende los avisos de uso insuficiente y registra la respuesta de la unidad.',
        'TraspasoEquipo': 'Consulta y gestiona las propuestas de traslado de equipos entre unidades, con su autorización y trazabilidad.',
    }
    for tarjeta in tarjetas:
        if tarjeta['object_name'] in descripciones:
            tarjeta['descripcion'] = gettext(descripciones[tarjeta['object_name']])
        codigo_tipo = TIPO_POR_ACCESO.get(tarjeta['object_name'])
        if codigo_tipo:
            tarjeta['tipo_menu'] = _tipo_acceso(codigo_tipo)
    por_clave = {tarjeta['object_name']: tarjeta for tarjeta in tarjetas}
    principal = por_clave.get('reportes-cumplimiento-expediente') or por_clave.get('reportes-evidencias-por-tipo')
    centros = por_clave.get('reportes_centros_id')
    utilizados = set()
    if principal:
        utilizados.add(principal['object_name'])
        principal['es_evaluacion'] = principal['object_name'] == 'reportes-cumplimiento-expediente'
        principal['texto_entrada'] = gettext('Evaluar unidades' if principal['es_evaluacion'] else 'Abrir expedientes')
    if centros:
        utilizados.add(centros['object_name'])
        centros['texto_entrada'] = gettext('Consultar reportes')
    categorias = []
    for codigo, nombre, descripcion, grupos in CATEGORIAS_REPORTES:
        subcategorias = []
        for titulo, ayuda, claves in grupos:
            visibles = [por_clave[clave] for clave in claves if clave in por_clave and clave not in utilizados]
            if visibles:
                subcategorias.append(dict(nombre=gettext(titulo), descripcion=gettext(ayuda), models=visibles))
                utilizados.update(tarjeta['object_name'] for tarjeta in visibles)
        if subcategorias:
            categorias.append(dict(codigo=codigo, nombre=gettext(nombre), descripcion=gettext(descripcion),
                                   total=sum(len(sub['models']) for sub in subcategorias),
                                   subcategorias=subcategorias))
    secciones = []
    if principal or categorias:
        secciones.append(dict(codigo='unidades', nombre=gettext('Unidades'),
            descripcion=gettext('Laboratorios, plantas piloto, centros experimentales y observatorios.'),
            nombre_detalle=gettext('Seguimiento y consultas de las unidades'), principal=principal, categorias=categorias))
    if centros:
        secciones.append(dict(codigo='centros_id', nombre=gettext('Centros de Investigación y Desarrollo'),
            descripcion=gettext('Proyectos, producción científica, transferencia y actividad de los Centros I+D.'),
            nombre_detalle=gettext('Seguimiento y consultas de los Centros I+D'), principal=centros, categorias=[]))
    otras = [tarjeta for tarjeta in tarjetas if tarjeta['object_name'] not in utilizados]
    if otras:
        secciones.append(dict(codigo='otras', nombre=gettext('Otros accesos'), descripcion='',
            nombre_detalle=gettext('Otros accesos'), principal=None, categorias=[dict(
                codigo='otras', nombre=gettext('Otras consultas'), descripcion='', total=len(otras),
                subcategorias=[dict(nombre=gettext('Consultas adicionales'), descripcion='', models=otras)])]))
    for seccion in secciones:
        accesos = ([seccion['principal']] if seccion['principal'] else []) + [
            tarjeta for categoria in seccion['categorias']
            for subcategoria in categoria['subcategorias'] for tarjeta in subcategoria['models']]
        tipos_visibles = {tarjeta['tipo_menu']['codigo'] for tarjeta in accesos if tarjeta.get('tipo_menu')}
        seccion['tipos'] = [_tipo_acceso(codigo) for codigo in ('documentos', 'sistema', 'gestion') if codigo in tipos_visibles]
    return dict(secciones=secciones)
