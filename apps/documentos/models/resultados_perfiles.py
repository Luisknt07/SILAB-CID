"""Contrato documental de resultados propios de observatorios, plantas y centros."""
from datetime import date

TIPOS_PERFIL = ('BOLETINES', 'EVENTOS', 'ENSAYOS', 'PRODUCCION')
CLAVES_PERFIL = ('subtipo', 'publicacion_id', 'indicador_id', 'valores_ids', 'orden_id',
                 'control_id', 'ciclo_id', 'registros_ids', 'objetivo', 'metodo', 'resultado',
                 'beneficiario', 'participantes', 'fecha_evento', 'referencia_acta',
                 'periodo_desde', 'periodo_hasta', 'justificacion_sin_produccion')


def entero_positivo(valor):
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def errores_perfil(tipo, detalle, fecha):
    """La evidencia identifica un resultado y las filas reales que lo respaldan."""
    if tipo not in TIPOS_PERFIL:
        return {}
    if not isinstance(detalle, dict):
        return {'resultado': 'Identifica el resultado realizado y su registro de origen.'}
    errores = {}
    for clave in ('objetivo', 'metodo', 'resultado'):
        if not isinstance(detalle.get(clave), str) or not detalle[clave].strip():
            errores[clave] = 'Describe este dato para que el responsable pueda comprobar el resultado.'
        elif len(detalle[clave]) > 3000:
            errores[clave] = 'Usa hasta 3000 caracteres.'
    subtipo = detalle.get('subtipo')
    campos = {'BOLETINES': {'publicacion': 'publicacion_id', 'datos': 'indicador_id'},
              'PRODUCCION': {'produccion': 'orden_id', 'control_calidad': 'control_id', 'sin_produccion': None},
              'ENSAYOS': {'ensayo': 'ciclo_id'}, 'EVENTOS': {'socializacion': None}}
    if subtipo not in campos[tipo]:
        errores['subtipo'] = 'Selecciona el resultado específico que se está documentando.'
    elif campos[tipo][subtipo] and not entero_positivo(detalle.get(campos[tipo][subtipo])):
        errores[campos[tipo][subtipo]] = 'Selecciona un registro real de esta unidad.'
    for subtipo_lista, clave in (('datos', 'valores_ids'), ('ensayo', 'registros_ids')):
        if subtipo == subtipo_lista:
            valores = detalle.get(clave)
            if (not isinstance(valores, list) or not valores or
                    any(not entero_positivo(v) for v in valores) or len(set(valores)) != len(valores)):
                errores[clave] = 'Selecciona registros de seguimiento sin repetirlos.'
    if tipo == 'EVENTOS':
        if not entero_positivo(detalle.get('participantes')):
            errores['participantes'] = 'Registra el número de participantes comprobados en el acta.'
        for clave in ('beneficiario', 'referencia_acta'):
            if not isinstance(detalle.get(clave), str) or not detalle[clave].strip():
                errores[clave] = 'Identifica los destinatarios y el acta que respalda la actividad.'
        try:
            realizada = date.fromisoformat(str(detalle.get('fecha_evento') or ''))
            if not fecha or realizada > fecha:
                raise ValueError
        except (TypeError, ValueError):
            errores['fecha_evento'] = 'La socialización debe tener fecha y haber ocurrido a la fecha de la evidencia.'
    if subtipo == 'sin_produccion':
        if not str(detalle.get('justificacion_sin_produccion') or '').strip():
            errores['justificacion_sin_produccion'] = 'Justifica y respalda por qué no hubo producción finalizada en este tramo.'
        try:
            desde = date.fromisoformat(str(detalle.get('periodo_desde') or ''))
            hasta = date.fromisoformat(str(detalle.get('periodo_hasta') or ''))
            if not fecha or desde > hasta or hasta > fecha:
                raise ValueError
        except (ValueError, TypeError):
            errores['periodo_hasta'] = 'El tramo justificado debe estar ordenado y haber terminado a la fecha del acta.'
    return errores
