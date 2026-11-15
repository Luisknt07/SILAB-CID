"""Revisión asistida: evidencia visible y criterios explícitos para que la Dirección revise lo enviado.

Es una guía de lectura, no una calificación. Solo el informe semestral se califica, y su nota sale del cierre
calculado con las metas de la planificación (evaluacion_cierre); los demás documentos son de cumplimiento
obligatorio y se aceptan u observan.
"""

from apps.documentos.models.expediente import DocumentoElaborado
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.documentos.models.expediente import es_calificable, minimo_vigente, penalizacion_vigente

VERSION = 'gestion-unidades-1'
NIVELES = (
    (0, 'Sin evidencia: no presenta lo solicitado'),
    (25, 'Insuficiente: menciona el tema, sin respaldo verificable'),
    (50, 'Parcial: presenta información, pero faltan elementos importantes'),
    (75, 'Adecuado: cumple lo esencial y permite verificarlo'),
    (100, 'Completo: cumple todo el criterio con evidencia consistente'),
)
CRITERIOS = {
    'PLANIFICACION': (
        ('Integridad del plan', 'Apartados obligatorios completos; diagnóstico y necesidades identificados.'),
        ('Metas y responsables', 'Objetivos medibles, indicadores, metas, responsables y cronograma coherentes.'),
        ('Viabilidad y cobertura', 'Actividades acordes a la función de la unidad, recursos y presupuesto justificados; seguridad prevista.'),
        ('Fortalecimiento y mejora', 'Acciones concretas para atender debilidades previas y fortalecer docencia, investigación o servicios según su función.'),
    ),
    'INFORME-SEMESTRAL': (
        ('Integridad del informe', 'Resultados, limitaciones y anexos completos para el período evaluado.'),
        ('Evidencia y trazabilidad', 'Actividades y resultados respaldados por registros; cifras y fechas coinciden con el documento.'),
        ('Cumplimiento de metas', 'Contrasta metas del plan con resultados verificables; explica desviaciones y limitaciones.'),
        ('Mejora de la gestión', 'Demuestra acciones de mejora, uso responsable de recursos y beneficios obtenidos; propone correcciones concretas.'),
    ),
    'PLAN-COMPRAS-ANUAL': (
        ('Integridad del presupuesto', 'Necesidades, cantidades, costos y fuentes completos o ausencia de compras justificada.'),
        ('Justificación y prioridades', 'Compras ligadas a necesidades reales, prioridades y objetivos de la unidad.'),
        ('Viabilidad de ejecución', 'Costos sustentados, financiamiento, responsables y plazos realistas.'),
        ('Beneficio y sostenibilidad', 'Explica el beneficio esperado, mantenimiento y aprovechamiento de los recursos existentes.'),
    ),
    'PROTOCOLO-BIOSEGURIDAD': (
        ('Cobertura del protocolo', 'Identifica actividades, riesgos y personas expuestas según la operación de la unidad.'),
        ('Medidas de prevención', 'Define acceso, protección, manejo de equipos y materiales, y gestión de desechos aplicables.'),
        ('Respuesta y responsables', 'Procedimientos de emergencia, responsables y contactos claros y vigentes.'),
        ('Aplicación y seguimiento', 'Evidencia de difusión, formación, revisión y seguimiento del protocolo.'),
    ),
    'RESOLUCION-CREACION': (
        ('Identificación', 'Unidad, número y fecha identificables en el documento.'),
        ('Autoridad y aprobación', 'Acto aprobado por la autoridad competente, verificable en el documento.'),
        ('Objeto y alcance', 'Define propósito, funciones y alcance de la unidad.'),
        ('Vigencia y correspondencia', 'Documento vigente y coherente con la identidad y dependencia actuales de la unidad.'),
    ),
}


def criterios_de(documento):
    return [{'clave': f'criterio_{i}', 'nombre': nombre, 'exige': exige, 'peso': 25}
            for i, (nombre, exige) in enumerate(CRITERIOS.get(documento.exigido.codigo, (
                ('Integridad', 'Contiene los apartados y datos solicitados.'),
                ('Evidencia', 'Aporta respaldo verificable de sus afirmaciones.'),
                ('Coherencia', 'Corresponde a la unidad, período y objetivo solicitado.'),
                ('Resultados y mejora', 'Permite verificar el cumplimiento y orientar acciones de mejora.'),
            ))) ]


def revisar_documento(documento):
    """Solo lectura. Los registros actuales orientan; no prueban el contenido del PDF."""
    criterios = criterios_de(documento)
    comprobaciones = []
    faltantes = []
    fuente = documento.exigido.fuente_reporte
    if fuente in ('planificacion', 'informe', 'compras'):
        from apps.documentos.presentation.expediente_redaccion import avance
        redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
        if redaccion:
            datos = avance(fuente, redaccion.contenido)
            comprobaciones.append(f"Editor actual: {datos['llenos']}/{datos['requeridos']} campos obligatorios completos ({datos['porcentaje']} %).")
            faltantes = [f'{seccion.titulo}: {campo.etiqueta}' for seccion, campo in datos['faltantes']]
            criterios[0]['sugerencia'] = min(NIVELES, key=lambda nivel: abs(nivel[0] - datos['porcentaje']))[0]
        else:
            comprobaciones.append('Sin redacción estructurada: revisar los apartados directamente en el PDF.')
    if documento.exigido.codigo == 'INFORME-SEMESTRAL':
        from apps.documentos.presentation.expediente_redaccion import metas_del_periodo
        metas = metas_del_periodo(documento)
        comprobaciones.append(f"Registros actuales: {metas['cumplidas']}/{metas['medibles']} metas medibles cumplidas. Las metas sin medición requieren revisión.")
    cierre = None
    if documento.exigido.codigo == 'INFORME-SEMESTRAL':
        from apps.documentos.presentation.evaluacion_cierre import lectura_cierre
        cierre = lectura_cierre(documento, metas)
    penalizacion = penalizacion_vigente() if documento.entregado_tarde else 0
    from apps.documentos.presentation.conformidad_permanente import es_permanente, completar_aprobaciones
    from apps.documentos.presentation.automatizacion_documental import completar_controles
    if not hasattr(documento, 'automatizacion'):
        completar_controles([documento])
    completar_aprobaciones([documento])
    permanente = es_permanente(documento)
    aprobacion = dict(documento.aprobacion_permanente or {})
    from django.utils.dateparse import parse_datetime
    aprobacion['fecha'] = parse_datetime(aprobacion.get('decidido_en') or '')
    modalidad = ('permanente' if permanente else 'conformidad' if documento.exigido.codigo in
                 ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL') else 'cierre' if es_calificable(documento.exigido)
                 else 'cumplimiento')
    from apps.documentos.presentation.conformidad_lectura import lectura_conformidad
    conformidad = lectura_conformidad(documento)
    from apps.documentos.presentation.expediente_interfaz import resumen_de_entrega
    documento.resumen_interfaz = resumen_de_entrega(documento)
    priorizacion = None
    if documento.exigido.codigo == 'PLAN-COMPRAS-ANUAL':
        from apps.documentos.presentation.priorizacion_compras import analizar_priorizacion
        redaccion = DocumentoElaborado.objects.filter(documento=documento).first()
        priorizacion = analizar_priorizacion(documento, redaccion.contenido if redaccion else {})
    return {'documento': documento, 'criterios': criterios, 'niveles': NIVELES,
            'modalidad': modalidad, 'permanente': permanente, 'aprobacion': aprobacion,
            'priorizacion_inversion': priorizacion,
            'conformidad': conformidad, 'conformidad_plan': bool(conformidad),
            'conforme': bool(aprobacion.get('vigente') if permanente else conformidad['estado'] == 'conforme'
                if conformidad else documento.estado == 'validado' and documento.cumple is True),
            'control': documento.automatizacion,
            'comprobaciones': comprobaciones, 'faltantes': faltantes,
            'penalizacion': penalizacion, 'minimo': minimo_vigente(),
            'evaluable': bool(documento.recurso_id and documento.estado == 'validado'
                                and not documento.firma_pendiente),
            'recibible': bool(documento.recurso_id and documento.estado != 'validado'
                                and not documento.firma_pendiente),
            'cierre': cierre,
            'version': VERSION, 'historial': RegistroAuditoriaUnidad.objects.filter(
                unidad_id=documento.unidad_id, entidad=documento._meta.label, objeto_id=str(documento.pk),
                datos_nuevos__rubrica__isnull=False).select_related('usuario').order_by('-pk')[:5]}
