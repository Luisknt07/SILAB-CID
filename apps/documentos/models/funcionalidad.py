"""Verificación funcional documentada; disponibilidad y seguridad son datos distintos."""
from django.db.models import Q


TIPO_FUNCIONALIDAD = 'FUNCIONALIDAD'
RESULTADOS_FUNCIONALES = (
    ('operativo', 'Operativo en la prueba realizada'),
    ('observado', 'Con observaciones o limitaciones'),
    ('no_operativo', 'No operativo en la prueba realizada'),
)
CLAVES_FUNCIONALIDAD = ('equipo_id', 'procedimiento', 'criterio', 'resultado_funcional',
                        'hallazgos_funcionales', 'equipo_snapshot')


def equipos_del_alcance(unidad):
    from apps.recursos.models.unidades import UnidadEquipo
    return UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()


def errores_funcionalidad(detalle):
    if not isinstance(detalle, dict):
        return {'equipo_id': 'Identifica el equipo y la prueba funcional realizada.'}
    errores = {}
    if type(detalle.get('equipo_id')) is not int or detalle['equipo_id'] <= 0:
        errores['equipo_id'] = 'Selecciona el equipo de esta unidad o compartido con ella.'
    for clave, etiqueta, limite in (('procedimiento', 'el procedimiento o ensayo realizado', 3000),
                                    ('criterio', 'el criterio de aceptación o referencia técnica', 1500)):
        if not isinstance(detalle.get(clave), str) or not detalle[clave].strip():
            errores[clave] = f'Describe {etiqueta}.'
        elif len(detalle[clave]) > limite:
            errores[clave] = f'Usa hasta {limite} caracteres.'
    resultado = detalle.get('resultado_funcional')
    if not isinstance(resultado, str) or resultado not in dict(RESULTADOS_FUNCIONALES):
        errores['resultado_funcional'] = 'Indica el resultado funcional observado en la prueba.'
    hallazgos = detalle.get('hallazgos_funcionales', '')
    if not isinstance(hallazgos, str) or len(hallazgos) > 3000:
        errores['hallazgos_funcionales'] = 'Describe los hallazgos con texto de hasta 3000 caracteres.'
    elif resultado in ('observado', 'no_operativo') and not hallazgos.strip():
        errores['hallazgos_funcionales'] = 'Documenta las limitaciones o fallas detectadas.'
    return errores


def errores_relaciones_funcionalidad(evidencia):
    if evidencia.tipo != TIPO_FUNCIONALIDAD:
        return {}
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    if not evidencia.unidad_id or not es_unidad_auditable(evidencia.unidad):
        return {'__all__': ['La verificación funcional corresponde a laboratorios, plantas piloto, centros experimentales y observatorios.']}
    detalle = evidencia.detalle if isinstance(evidencia.detalle, dict) else {}
    equipo_id = detalle.get('equipo_id')
    errores = {}
    if equipo_id in (None, '') and evidencia.estado != 'validado':
        return errores
    if type(equipo_id) is not int or equipo_id <= 0:
        return {'__all__': ['Identifica un equipo del alcance de esta unidad.']}
    from apps.recursos.models.unidades import UnidadEquipo
    consulta = UnidadEquipo.objects.filter(pk=equipo_id) if evidencia.pk else equipos_del_alcance(evidencia.unidad).filter(pk=equipo_id)
    equipo = consulta.select_related('equipo').prefetch_related('laboratorios').first()
    if not equipo:
        return {'__all__': ['El equipo debe existir y pertenecer a esta unidad o estar compartido con ella.']}
    if evidencia.estado != 'validado':
        return errores
    if not evidencia.recurso_id:
        errores['recurso'] = 'Adjunta el informe o respaldo legible de la prueba funcional; un enlace no sustituye este documento.'
    if not evidencia.pk:
        evidencia.detalle = dict(detalle, equipo_snapshot=dict(equipo=equipo.pk,
            codigo=equipo.codigo_unidad, nombre=equipo.equipo.nombre, serie=equipo.numero_serie or '',
            codigo_bien=equipo.codigo_bien or '', unidad_registro=evidencia.unidad_id,
            laboratorio=equipo.laboratorio_id, laboratorios=sorted(u.pk for u in equipo.laboratorios.all())))
    else:
        snapshot = detalle.get('equipo_snapshot')
        if (not isinstance(snapshot, dict) or snapshot.get('equipo') != equipo_id or
                snapshot.get('unidad_registro') != evidencia.unidad_id or
                not isinstance(snapshot.get('laboratorios'), list) or
                evidencia.unidad_id not in [snapshot.get('laboratorio'), *snapshot.get('laboratorios', [])]):
            errores['__all__'] = ['La prueba no conserva la identidad del equipo y su alcance originales. Registra una nueva evidencia.']
    return errores
