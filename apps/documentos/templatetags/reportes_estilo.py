"""Agrupación visual de indicadores, sin modificar sus cálculos ni instantáneas."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()
GRUPOS = (
    ('obligatorio', 'Obligatorios'),
    ('opcional', 'Opcionales'),
    ('informativo', 'Anexos automáticos · sin meta independiente'),
    ('segun-programacion', 'Según programación · sin compromiso este período'),
    ('sin-definir', 'Por definir en planificación'),
    ('no-aplica', 'No aplican'),
)


@register.filter
def semaforo_avance(valor):
    """Color del avance hacia la meta completa; no cambia la nota ni su mínimo."""
    try:
        porcentaje = Decimal(str(valor))
        if not porcentaje.is_finite() or not 0 <= porcentaje <= 100:
            return 'neutro'
    except (InvalidOperation, TypeError, ValueError):
        return 'neutro'
    if porcentaje == 100:
        return 'verde'
    return 'amarillo' if porcentaje >= 50 else 'rojo'


@register.filter
def etiqueta_avance(valor):
    return {'rojo': 'Avance bajo: menos del 50 %',
            'amarillo': 'En progreso: del 50 % a menos del 100 %',
            'verde': 'Completo: 100 %',
            'neutro': 'Sin medición válida'}[semaforo_avance(valor)]


@register.filter
def es_unidad_auditable(unidad):
    """Comparte el alcance del control documental con las pantallas y formularios."""
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable as aplica
    return bool(unidad and aplica(unidad))


@register.filter
def exigencia_estilo(fila):
    if fila.get('estado') == 'Anexo automático':
        return 'informativo'
    exigencia = fila.get('exigencia', '')
    if exigencia == 'Según programación':
        return 'segun-programacion'
    if exigencia.startswith('Obligatorio') or exigencia == 'Comprometido en planificación':
        return 'obligatorio'
    if exigencia == 'Sin definir' or fila.get('definida') is False:
        return 'sin-definir'
    if exigencia == 'No aplica' or fila.get('aplica') is False:
        return 'no-aplica'
    if fila.get('exigible'):
        return 'obligatorio'
    if exigencia == 'Opcional' or fila.get('obligatoria') is False:
        return 'opcional'
    # Las instantáneas v1 no incluían exigencia; eran metas comprometidas.
    return 'obligatorio' if not exigencia and 'porcentaje' in fila else 'sin-definir'


@register.filter
def estado_meta(fila):
    estado = fila.get('estado', '')
    if estado == 'Cumple':
        return {'clase': 'cumple', 'icono': '✓'}
    if estado == 'No cumple':
        return {'clase': 'opcional' if exigencia_estilo(fila) == 'opcional' else 'no-cumple', 'icono': '!'}
    if estado.startswith('Pendiente'):
        return {'clase': 'pendiente', 'icono': '◷'}
    return {'clase': 'neutro', 'icono': '—'}


def _agrupar(elementos, indicadores):
    grupos = {codigo: [] for codigo, _ in GRUPOS}
    prioridad = {codigo: indice for indice, (codigo, _) in enumerate(GRUPOS)}
    for elemento in elementos:
        clases = [exigencia_estilo(fila) for fila in indicadores(elemento)]
        categoria = min(clases, key=prioridad.get) if clases else 'sin-definir'
        grupos[categoria].append(elemento)
    return [dict(codigo=codigo, titulo=titulo, elementos=grupos[codigo])
            for codigo, titulo in GRUPOS if grupos[codigo]]


@register.filter
def grupos_metas(filas):
    return _agrupar(filas, lambda fila: [fila])


@register.filter
def grupos_anexos(anexos):
    def indicadores(anexo):
        if isinstance(anexo, dict):
            if anexo.get('es_soporte_planificacion'):
                return [dict(estado='Anexo automático')]
            return anexo.get('detalle_indicadores', [])
        return getattr(anexo, 'indicadores_cierre', [])
    return _agrupar(anexos, indicadores)


@register.simple_tag
def evidencias_cierre(cierre, anexos):
    """Una proyección de metas y archivos; no cambia cálculos ni datos enviados."""
    bloques, representados = [], set()
    for anexo in anexos or []:
        extras = {}
        if isinstance(anexo, dict):
            nombre, recurso = anexo['nombre'], anexo.get('recurso')
            indicadores = anexo.get('detalle_indicadores', [])
            extras = {k: anexo.get(k) for k in
                      ('documento_padre', 'entrega_padre', 'es_soporte_planificacion', 'origen_documental')}
            objeto_anexo = anexo.get('anexo', anexo)
        else:
            nombre, recurso = getattr(anexo, 'nombre_documental', anexo.exigido.nombre), anexo.recurso_id
            indicadores = getattr(anexo, 'indicadores_cierre', [])
            objeto_anexo = anexo
        representados.update(f['codigo'] for f in indicadores if f.get('codigo'))
        bloques.append(dict(nombre=nombre, recurso=recurso, anexo=objeto_anexo,
                            detalle_indicadores=indicadores, sin_anexo=False, **extras))
    for fila in (cierre or {}).get('filas', []):
        if fila.get('codigo') not in representados:
            lectura = dict(fila)
            lectura.setdefault('indicador', fila['nombre'])
            if 'exigencia' not in lectura:
                lectura['exigencia'] = 'Comprometido en planificación'
                lectura.setdefault('estado', 'Pendiente de medición' if fila.get('pendiente') else
                                   'Cumple' if fila.get('porcentaje') == 100 else 'No cumple')
            bloques.append(dict(nombre=fila['nombre'], recurso=None, anexo=None,
                                detalle_indicadores=[lectura], sin_anexo=True))
    grupos = grupos_anexos(bloques)
    numero = 0
    for grupo in grupos:
        for bloque in grupo['elementos']:
            numero += 1
            bloque['numero_item'] = numero
    return grupos


@register.simple_tag
def anexos_del_periodo(periodo):
    """Una tabla de lectura, conservando el padre y el circuito de cada anexo."""
    entregas = periodo.get('entregas', [])
    cierre = next((e for e in entregas if e.get('cierre')), {})
    anexos = []
    for entrega in entregas:
        padre = entrega['documento']
        soporte = padre.exigido.codigo == 'PLANIFICACION'
        for anexo in entrega.get('anexos', []):
            anexos.append(dict(nombre=anexo.nombre_documental, recurso=anexo.recurso_id,
                anexo=anexo, documento_padre=padre, entrega_padre=entrega,
                es_soporte_planificacion=soporte,
                origen_documental='Planificación' if soporte else 'Informe de cierre',
                # El consolidado de prácticas respalda FT02; no duplica su meta.
                detalle_indicadores=[] if soporte else getattr(anexo, 'indicadores_cierre', [])))
    return dict(anexos=anexos, cierre=cierre.get('cierre', {}), entrega=cierre,
                documento=cierre.get('documento'))


@register.filter
def cantidad_items(grupos):
    return sum(len(grupo['elementos']) for grupo in grupos)


@register.filter
def clasificacion_meta(fila):
    """Clasifica el avance visible, sin sustituir el estado ni la evaluación."""
    if (fila.get('aplica') is False or fila.get('estado') in (
            'No aplica', 'Anexo automático', 'Según programación', 'Sin definir en planificación')
            or fila.get('exigencia') in ('No aplica', 'Sin definir', 'Según programación')):
        return 'neutro'
    if fila.get('pendiente') or str(fila.get('estado', '')).startswith('Pendiente'):
        return 'pendiente'
    try:
        porcentaje = Decimal(str(fila.get('porcentaje')))
        if not porcentaje.is_finite() or not 0 <= porcentaje <= 100:
            return 'pendiente'
    except (InvalidOperation, TypeError, ValueError):
        return 'pendiente'
    if porcentaje == 100:
        return 'cumple'
    return 'parcial' if porcentaje > 0 else 'sin-avance'


@register.simple_tag
def resumen_metas_cierre(grupos):
    """Cuenta metas obligatorias únicas de la misma proyección que muestra la tabla."""
    conteo = dict(cumplidas=0, parciales=0, sin_acreditar=0, pendientes=0, total=0)
    representadas = set()
    for grupo in grupos:
        for bloque in grupo['elementos']:
            for fila in bloque.get('detalle_indicadores', []):
                if exigencia_estilo(fila) != 'obligatorio':
                    continue
                codigo = fila.get('codigo')
                if codigo and codigo in representadas:
                    continue
                if codigo:
                    representadas.add(codigo)
                conteo['total'] += 1
                estado = clasificacion_meta(fila)
                if estado == 'cumple':
                    conteo['cumplidas'] += 1
                elif estado == 'parcial':
                    conteo['parciales'] += 1
                else:
                    conteo['sin_acreditar'] += 1
                    conteo['pendientes'] += estado == 'pendiente'
    for clave in ('cumplidas', 'parciales', 'sin_acreditar'):
        conteo[f'{clave}_porcentaje'] = (
            Decimal(conteo[clave]) * 100 / conteo['total'] if conteo['total'] else Decimal(0))
    return conteo
