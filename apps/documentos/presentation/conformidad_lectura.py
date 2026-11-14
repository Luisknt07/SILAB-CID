"""Estado documental de los planes; una nota histórica no es una aprobación nueva."""
from django.utils.dateparse import parse_datetime

CODIGOS = frozenset(('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'))


def es_plan(documento):
    return getattr(documento.exigido, 'codigo', '') in CODIGOS and not getattr(documento.exigido, 'es_anexo', False)


def completar_conformidades(documentos, *, forzar=False):
    """Una consulta por lote; no recalcula controles, abre archivos ni cambia notas."""
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad

    planes = [d for d in documentos if es_plan(d) and (forzar or not hasattr(d, '_conformidad_plan_registro'))]
    ids = {str(d.pk) for d in planes if d.pk}
    ultimos = {}
    if ids:
        for r in RegistroAuditoriaUnidad.objects.filter(
                entidad='documentos.DocumentoExpediente', objeto_id__in=ids,
                descripcion='conformidad_documental:confirmar').select_related('usuario').order_by('-pk'):
            ultimos.setdefault(r.objeto_id, r)
    for d in planes:
        d._conformidad_plan_registro = ultimos.get(str(d.pk))


def lectura_conformidad(documento, *, integridad=None, control=None):
    """Sólo una confirmación vinculada al archivo o control vigente acredita conformidad."""
    if not es_plan(documento):
        return None
    control = control if control is not None else getattr(documento, 'automatizacion', {}) or {}
    integridad = integridad if integridad is not None else getattr(documento, 'integridad_documental', {}) or {}
    r = getattr(documento, '_conformidad_plan_registro', None)
    datos = r.datos_nuevos if r and isinstance(r.datos_nuevos, dict) else {}
    recurso = documento.recurso if documento.recurso_id else None
    vigente = bool(documento.estado == 'validado' and recurso and recurso.activo
        and recurso.estado == 'vigente' and recurso.version == documento.version
        and recurso.unidad_id == documento.unidad_id and recurso.archivo and len(recurso.hash_sha256) == 64
        and (not documento.exigido.requiere_firma or documento.firma_verificada or getattr(documento, 'verificacion_qr', None)))
    humana = bool(vigente and r and r.unidad_id == documento.unidad_id and r.usuario_id
        and datos.get('version') == documento.version and datos.get('recurso_id') == documento.recurso_id
        and datos.get('sha256') == recurso.hash_sha256 and datos.get('alcance') == 'documental')
    automatica = bool(vigente and control.get('vigente') and control.get('aplicado')
        and control.get('estado') == 'automatico' and not (control.get('resumen') or {}).get('manual_preservada')
        and (control.get('resumen') or {}).get('conformidad_documental'))
    historica = {}
    if not humana and documento.evaluacion is not None:
        historica = dict(nota=documento.evaluacion, fuente='Dirección' if documento.evaluado_por_id else 'Registro histórico',
            fecha=documento.evaluado_en, observacion=documento.evaluacion_observacion,
            version=documento.evaluacion_version)
    fuente = 'Dirección' if humana else 'Sistema' if automatica else ''
    fecha = r.creado_en if humana else control.get('comprobado_en') if automatica else None
    if isinstance(fecha, str):
        fecha = parse_datetime(fecha)
    estado, etiqueta = 'pendiente', 'Conformidad pendiente'
    if documento.estado == 'observado' or control.get('vigente') and control.get('estado') == 'bloqueado':
        estado, etiqueta = 'corregir', 'Requiere corrección'
    elif documento.recurso_id and integridad.get('aplica') and not integridad.get('correspondencia_verificada'):
        estado, etiqueta = 'verificar', 'Correspondencia por verificar'
    elif humana or automatica:
        estado, etiqueta = 'conforme', 'Conforme'
    lectura = dict(estado=estado, etiqueta=etiqueta, fuente=fuente, fecha=fecha, historica=historica,
        explicacion='Se comprueban integridad, correspondencia y coherencia del plan. No se asigna una nota de desempeño. '
            'La prioridad de inversión y el cumplimiento del informe semestral se revisan por separado.')
    from .expediente_interfaz import etapa_actual_del_plan
    lectura['etapa_actual'] = etapa_actual_del_plan(documento, lectura, integridad=integridad, control=control)
    if lectura['etapa_actual']:
        lectura['explicacion'] = lectura['etapa_actual']['descripcion'] + ' ' + lectura['explicacion']
    return lectura
