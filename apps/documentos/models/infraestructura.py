"""Contrato del mantenimiento de infraestructura de las unidades auditables.

La inspección describe condiciones. Estos registros documentan una intervención
prevista y su ejecución; no conceden autorizaciones de operación.
"""
from datetime import date

from django.core.exceptions import ValidationError


TIPOS_INFRAESTRUCTURA = ('PLAN-INFRA', 'EJECUCION-INFRA')
CRITICIDADES_INFRAESTRUCTURA = (
    ('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('critica', 'Crítica'),
)
CLAVES_PLAN_INFRA = ('alcance_infraestructura', 'justificacion_alcance', 'alcance_todo_laboratorio',
                    'espacios_alcance', 'espacio_id', 'ubicacion', 'intervencion', 'criticidad',
                    'fecha_programada', 'frecuencia_dias', 'fecha_fin_programacion')
CLAVES_EJECUCION_INFRA = ('plan_id', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
                         'resultado', 'espacio_id', 'ubicacion', 'plan_codigo',
                         'plan_huella', 'plan_sha256')
CLAVES_INFRAESTRUCTURA = tuple(dict.fromkeys(CLAVES_PLAN_INFRA + CLAVES_EJECUCION_INFRA))


def fecha_detalle(detalle, clave):
    try:
        return date.fromisoformat(str(detalle.get(clave) or ''))
    except (ValueError, TypeError):
        return None


def es_laboratorio_infraestructura(unidad):
    """Nombre conservado por compatibilidad; el alcance depende del perfil."""
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    return es_unidad_auditable(unidad)


def es_ocurrencia_programada(detalle, fecha):
    primera = fecha_detalle(detalle, 'fecha_programada')
    ultima = fecha_detalle(detalle, 'fecha_fin_programacion')
    frecuencia = detalle.get('frecuencia_dias')
    if not primera or not fecha or fecha < primera or ultima and fecha > ultima:
        return False
    if not isinstance(frecuencia, int) or isinstance(frecuencia, bool) or not 0 <= frecuencia <= 3660:
        return False
    return fecha == primera if not frecuencia else (fecha - primera).days % frecuencia == 0


def errores_infraestructura(tipo, detalle, fecha):
    if not isinstance(detalle, dict):
        return {'__all__': 'Completa los datos de la intervención de infraestructura.'}
    errores = {}
    programada = fecha_detalle(detalle, 'fecha_programada')
    if tipo == 'PLAN-INFRA':
        alcance = detalle.get('alcance_infraestructura')
        if alcance not in ('aplica', 'no_aplica'):
            errores['alcance_infraestructura'] = 'Declara si el mantenimiento de infraestructura aplica a esta unidad.'
        justificacion = detalle.get('justificacion_alcance', '')
        if not isinstance(justificacion, str) or len(justificacion) > 3000:
            errores['justificacion_alcance'] = 'Explica el alcance con texto de hasta 3000 caracteres.'
        if alcance == 'no_aplica':
            if not isinstance(justificacion, str) or not justificacion.strip():
                errores['justificacion_alcance'] = 'Justifica por qué el mantenimiento de infraestructura no aplica en el año declarado.'
            if any(detalle.get(k) for k in ('alcance_todo_laboratorio', 'espacio_id', 'ubicacion', 'intervencion', 'criticidad',
                    'fecha_programada', 'fecha_fin_programacion', 'frecuencia_dias')):
                errores['alcance_infraestructura'] = 'Una declaración de no aplicación no debe contener un cronograma o una intervención contradictorios.'
            return errores
        if detalle.get('alcance_todo_laboratorio') is True and not str(justificacion or '').strip():
            errores['justificacion_alcance'] = 'Explica cómo el plan adjunto cubre todos los espacios e instalaciones de la unidad.'
    if not programada:
        errores['fecha_programada'] = 'Indica la fecha de la intervención programada.'
    if tipo == 'PLAN-INFRA':
        for clave, etiqueta in (('ubicacion', 'el espacio o área de la intervención'),
                                ('intervencion', 'la intervención que se realizará')):
            if not isinstance(detalle.get(clave), str) or not detalle[clave].strip():
                errores[clave] = f'Describe {etiqueta}.'
            elif len(detalle[clave]) > 300:
                errores[clave] = 'Usa hasta 300 caracteres; amplía los detalles en la descripción.'
        if not isinstance(detalle.get('criticidad'), str) or detalle['criticidad'] not in dict(CRITICIDADES_INFRAESTRUCTURA):
            errores['criticidad'] = 'Define la criticidad de la intervención.'
        frecuencia = detalle.get('frecuencia_dias')
        if not isinstance(frecuencia, int) or isinstance(frecuencia, bool) or not 0 <= frecuencia <= 3660:
            errores['frecuencia_dias'] = 'Indica la frecuencia en días: 0 para una intervención única, o de 1 a 3660.'
        if programada and fecha and programada < fecha:
            errores['fecha_programada'] = 'La programación no puede ser anterior a la fecha del plan.'
        if detalle.get('fecha_fin_programacion'):
            ultima = fecha_detalle(detalle, 'fecha_fin_programacion')
            if not ultima or programada and ultima < programada:
                errores['fecha_fin_programacion'] = 'El fin de la programación debe ser igual o posterior a su primera intervención.'
    elif tipo == 'EJECUCION-INFRA':
        if not isinstance(detalle.get('plan_id'), int) or isinstance(detalle.get('plan_id'), bool):
            errores['plan_id'] = 'Selecciona el plan de infraestructura de esta unidad.'
        inicio, fin = fecha_detalle(detalle, 'fecha_inicio'), fecha_detalle(detalle, 'fecha_fin')
        if not inicio:
            errores['fecha_inicio'] = 'Indica el inicio real de la intervención.'
        if not fin or inicio and fin < inicio or fecha and fin and fin > fecha:
            errores['fecha_fin'] = 'El cierre real debe ser posterior al inicio y no superar la fecha de la evidencia.'
        if not isinstance(detalle.get('resultado'), str) or not detalle['resultado'].strip():
            errores['resultado'] = 'Describe el resultado comprobado de la intervención finalizada.'
        elif len(detalle['resultado']) > 3000:
            errores['resultado'] = 'Describe el resultado con hasta 3000 caracteres.'
    return errores


def errores_relaciones_infraestructura(evidencia):
    """También protege llamadas directas al servicio, no sólo el formulario."""
    if evidencia.tipo not in TIPOS_INFRAESTRUCTURA:
        return {}
    if not evidencia.unidad_id or not es_laboratorio_infraestructura(evidencia.unidad):
        return {'__all__': ['El registro de infraestructura corresponde a laboratorios, plantas piloto, centros experimentales y observatorios.']}
    detalle = evidencia.detalle if isinstance(evidencia.detalle, dict) else {}
    errores = {}
    espacio = detalle.get('espacio_id')
    if espacio not in (None, ''):
        from apps.gestion_unidades.models.espacios import EspacioReservable
        if (not isinstance(espacio, int) or isinstance(espacio, bool) or not
                EspacioReservable.objects.filter(pk=espacio, unidad_id=evidencia.unidad_id).exists()):
            errores['__all__'] = ['El espacio debe pertenecer a la misma unidad.']
    if evidencia.estado != 'validado':
        return errores
    if evidencia.tipo == 'PLAN-INFRA' and not evidencia.pk and detalle.get('alcance_todo_laboratorio') is True:
        from apps.gestion_unidades.models.espacios import EspacioReservable
        # La cobertura procede del inventario actual, no de IDs suministrados por el navegador.
        evidencia.detalle = dict(detalle, espacios_alcance=list(EspacioReservable.objects.filter(
            unidad_id=evidencia.unidad_id, activo=True).order_by('pk').values_list('pk', flat=True)))
    if not evidencia.recurso_id:
        errores['recurso'] = 'Adjunta el archivo del plan o del informe de ejecución; un enlace no acredita mantenimiento de infraestructura.'
    if evidencia.tipo != 'EJECUCION-INFRA':
        return errores
    plan_id = detalle.get('plan_id')
    if not isinstance(plan_id, int) or isinstance(plan_id, bool):
        return errores  # La validación estructural informa el campo pendiente.
    from .medicion import EvidenciaGestionUnidad
    from .resultados_gestion import huella_resultado
    plan = EvidenciaGestionUnidad.objects.filter(pk=plan_id, unidad_id=evidencia.unidad_id,
        tipo='PLAN-INFRA', estado='validado').select_related('recurso').first()
    if not plan:
        errores['__all__'] = ['La ejecución debe enlazarse a un plan verificado de la misma unidad.']
        return errores
    if not isinstance(plan.detalle, dict) or plan.detalle.get('alcance_infraestructura') != 'aplica':
        errores['__all__'] = ['Una ejecución requiere un plan de intervención aplicable, no una declaración de no aplicación.']
        return errores
    try:
        plan.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError:
        errores['__all__'] = ['El plan seleccionado está incompleto o su respaldo dejó de ser válido.']
        return errores
    # La lectura usa evidencias_verificadas para todos los tipos. Esta comprobación
    # protege además el alta de una ejecución, antes de que esa lectura exista.
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad
    auditoria = RegistroAuditoriaUnidad.objects.filter(unidad_id=evidencia.unidad_id,
        entidad=plan._meta.label, objeto_id=str(plan.pk), accion='crear').order_by('-pk').first()
    original = auditoria.datos_nuevos if auditoria else {}
    if (not auditoria or original.get('estado') != 'validado' or
            original.get('demostracion') is not plan.demostracion or auditoria.usuario_id != plan.validado_por_id or
            'validado_por' in original and original['validado_por'] != plan.validado_por_id or
            'validado_en' in original and original['validado_en'] != (plan.validado_en.isoformat() if plan.validado_en else None) or
            original.get('contenido_sha256') != huella_resultado(plan) or
            not plan.recurso_id or original.get('sha256') != plan.recurso.hash_sha256):
        errores['__all__'] = ['El plan seleccionado no conserva la verificación original, su ámbito y su respaldo.']
        return errores
    if bool(plan.demostracion) != bool(evidencia.demostracion):
        errores['__all__'] = ['El plan y la ejecución deben pertenecer al mismo ámbito real o de demostración.']
    programada = fecha_detalle(detalle, 'fecha_programada')
    if not es_ocurrencia_programada(plan.detalle, programada):
        errores['__all__'] = ['La fecha prevista no corresponde a una ocurrencia de ese plan.']
    inicio = fecha_detalle(detalle, 'fecha_inicio')
    if inicio and inicio < plan.fecha:
        errores['__all__'] = ['La ejecución no puede comenzar antes de la fecha del plan.']
    vinculacion = dict(espacio_id=plan.detalle.get('espacio_id') or None,
        ubicacion=plan.detalle.get('ubicacion', ''), plan_codigo=plan.codigo,
        plan_huella=huella_resultado(plan), plan_sha256=plan.recurso.hash_sha256 if plan.recurso_id else '')
    if evidencia.pk:
        if any(detalle.get(k) != v for k, v in vinculacion.items()):
            errores['__all__'] = ['El plan o su ubicación cambiaron después de registrar la ejecución; conserva el historial y rectifica.']
    else:
        evidencia.detalle = dict(detalle, **vinculacion)
    if evidencia.estado == 'validado' and programada:
        candidatas = EvidenciaGestionUnidad.objects.filter(unidad_id=evidencia.unidad_id,
            tipo='EJECUCION-INFRA', estado='validado', detalle__plan_id=plan_id,
            detalle__fecha_programada=programada.isoformat()).exclude(pk=evidencia.pk)
        if candidatas.exists():
            errores['__all__'] = ['Esta intervención programada ya tiene una ejecución verificada; rectifícala antes de sustituirla.']
    return errores
