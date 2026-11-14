"""Comentarios completos por canal, con correcciones trazables del texto actual.

Cambiar una observación no reabre entregas ni modifica resultados, firmas,
plazos o aprobaciones. Los textos de evaluación se conservan como antecedentes.
"""
from hashlib import sha256

from django.core.exceptions import ValidationError

from apps.documentos.presentation.expediente_operaciones import comando
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad


CANALES = (
    ('observacion', 'Observación actual de Dirección'),
    ('evaluacion_observacion', 'Observación de la evaluación conservada'),
    ('evaluacion_fortalezas', 'Fortalezas de la evaluación'),
    ('evaluacion_debilidades', 'Debilidades de la evaluación'),
    ('evaluacion_recomendaciones', 'Recomendaciones de la evaluación'),
    ('tardanza_motivo', 'Justificación de entrega fuera de plazo'),
)
AUDITORIA_CORRECCION = 'observacion_documental:corregir'


def huella_texto(texto):
    return sha256(str(texto or '').encode('utf-8')).hexdigest()


def identidad_comentario(documento, campo):
    return dict(version=documento.version, recurso_id=documento.recurso_id or '',
        huella=documento.recurso.hash_sha256 if documento.recurso_id else '',
        huella_texto=huella_texto(getattr(documento, campo, '')))


def _guardar_texto(documento, usuario, campo, texto, *, version, recurso_id, huella,
                   huella_anterior, motivo):
    identidad = identidad_comentario(documento, campo)
    if (str(version) != str(identidad['version'])
            or str(recurso_id or '') != str(identidad['recurso_id'])
            or str(huella or '') != identidad['huella']
            or str(huella_anterior or '') != identidad['huella_texto']):
        raise ValidationError('El documento o su comentario cambió. Abre de nuevo Observaciones antes de corregirlo.')
    if documento.recurso_id and documento.recurso.unidad_id != documento.unidad_id:
        raise ValidationError('El archivo pertenece a otra unidad. Revisa su correspondencia antes de corregir el comentario.')
    texto, motivo = str(texto or '').strip(), str(motivo or '').strip()
    if len(texto) > 12000 or not 3 <= len(motivo) <= 1200:
        raise ValidationError('La observación admite hasta 12000 caracteres y el motivo debe tener entre 3 y 1200.')
    anterior = getattr(documento, campo, '') or ''
    if texto == anterior:
        raise ValidationError('No hay cambios en el texto.')
    if not texto and (campo == 'tardanza_motivo' or documento.estado in ('observado', 'no_aplica')):
        raise ValidationError('Conserva una justificación comprensible; no se puede dejar vacío el motivo pendiente.')
    if campo == 'observacion' and (anterior.startswith('Heredado del año ') or texto.startswith('Heredado del año ')):
        raise ValidationError('Esta anotación identifica una herencia documental del sistema y se conserva como antecedente.')
    setattr(documento, campo, texto)
    documento.save(update_fields=[campo, 'actualizado_en'])
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='actualizar', objeto=documento,
        descripcion=AUDITORIA_CORRECCION,
        anteriores={campo: anterior}, nuevos={campo: texto, 'canal': campo, 'motivo': motivo,
            'version': documento.version, 'recurso_id': documento.recurso_id,
            'sha256': identidad['huella'], 'sin_cambio_de_resultado': True})


@comando
def corregir_justificacion_tardia(documento, usuario, texto, *, version, recurso_id, huella,
                                  huella_anterior, motivo):
    if not usuario.is_active or not puede_operar_modulo_unidad(usuario, documento.unidad, 'reportes'):
        raise ValidationError('Solo la Dirección o quienes gestionan los reportes de esta unidad pueden aclarar su justificación.')
    if not documento.tardanza_motivo:
        raise ValidationError('No hay una justificación previa que corregir. Solicita la reapertura por su circuito habitual.')
    _guardar_texto(documento, usuario, 'tardanza_motivo', texto, version=version,
        recurso_id=recurso_id, huella=huella, huella_anterior=huella_anterior, motivo=motivo)


def contexto_observaciones(documento, usuario):
    """Lectura completa de una entrega seleccionada, nunca una consulta por fila."""
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad

    registros = list(RegistroAuditoriaUnidad.objects.filter(unidad_id=documento.unidad_id,
        entidad=documento._meta.label, objeto_id=str(documento.pk)).select_related('usuario').order_by('-pk')) if documento.pk else []
    manuales = set()
    for r in registros:
        if r.descripcion == AUDITORIA_CORRECCION:
            antes, despues = r.datos_anteriores or {}, r.datos_nuevos or {}
            campo = despues.get('canal')
            manuales.add((r.usuario_id, campo, antes.get(campo), despues.get(campo), despues.get('version')))
    historial, origenes, vistos = [], {}, set()
    for registro in registros:
        antes, despues = registro.datos_anteriores or {}, registro.datos_nuevos or {}
        autor = (registro.usuario.get_full_name() or registro.usuario.get_username()) if registro.usuario else 'Sistema'
        for campo, etiqueta in CANALES:
            if campo not in despues or antes.get(campo, '') == despues.get(campo, ''):
                continue
            actual = getattr(documento, campo, '') or ''
            if despues.get(campo) == actual:
                origenes.setdefault(campo, dict(autor=autor, fecha=registro.creado_en))
            duplicado = (registro.usuario_id, campo, antes.get(campo), despues.get(campo), despues.get('version'))
            if registro.descripcion != AUDITORIA_CORRECCION and duplicado in manuales:
                continue
            clave = (campo, str(despues.get(campo, '')), despues.get('version', documento.version),
                autor, registro.creado_en.replace(second=0, microsecond=0))
            if clave in vistos:
                continue
            vistos.add(clave)
            historial.append(dict(campo=campo, canal=etiqueta, antes=antes.get(campo, ''), texto=despues.get(campo, ''),
                autor=autor, fecha=registro.creado_en, version=despues.get('version'),
                motivo=despues.get('motivo') if registro.descripcion == AUDITORIA_CORRECCION else '',
                operacion=registro.descripcion))
    direccion = bool(usuario.is_active and usuario.is_superuser)
    opera = bool(puede_operar_modulo_unidad(usuario, documento.unidad, 'reportes'))
    canales = [dict(campo=campo, etiqueta=etiqueta, texto=getattr(documento, campo, ''),
                   origen=origenes.get(campo)) for campo, etiqueta in CANALES if getattr(documento, campo, '')]
    editores = []
    if documento.pk and direccion and not documento.observacion.startswith('Heredado del año '):
        editores.append(dict(campo='observacion', etiqueta='Observación',
            accion='corregir_observacion', texto=documento.observacion, **identidad_comentario(documento, 'observacion')))
    if documento.pk and opera and documento.tardanza_motivo:
        editores.append(dict(campo='tardanza_motivo', etiqueta='Justificación de entrega',
            accion='corregir_justificacion_tardia', texto=documento.tardanza_motivo,
            **identidad_comentario(documento, 'tardanza_motivo')))
    representados = {(h['campo'], h['texto']) for h in historial}
    antecedentes = [c for c in canales if c['campo'] not in ('observacion', 'tardanza_motivo')
        and (c['campo'], c['texto']) not in representados]
    return dict(canales=canales, historial=historial, editores=editores, antecedentes=antecedentes,
        campos_editables=[e['campo'] for e in editores])
