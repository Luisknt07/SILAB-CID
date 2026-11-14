"""El proceso de una receta como datos, y lo que se deriva de él.

Todo lo que aquí se calcula trabaja sobre una estructura de datos plana (la
que devuelve ``datos_de_receta``), no sobre los modelos: así el balance de
masa, el cronograma y los diagramas sirven igual para la receta real de la
planta y, más adelante, para un escenario de simulación que el estudiante
edite sin tocar la base.

Los diagramas siguen la convención del cursograma: operación, inspección,
transporte, espera y almacenamiento. El diagrama de flujo muestra todas las
etapas por bloques; el sinóptico, solo operaciones e inspecciones con los
materiales que entran; el analítico es la tabla con los cinco símbolos, los
tiempos y las distancias.
"""

from decimal import Decimal, ROUND_HALF_UP
from html import escape

TIPOS = ('operacion', 'inspeccion', 'transporte', 'espera', 'almacenamiento')
NOMBRES_TIPO = {
    'operacion': 'Operación',
    'inspeccion': 'Inspección',
    'transporte': 'Transporte',
    'espera': 'Espera',
    'almacenamiento': 'Almacenamiento',
}
SIMBOLOS = {
    'operacion': '○',
    'inspeccion': '□',
    'transporte': '⇨',
    'espera': 'D',
    'almacenamiento': '▽',
}
TRES = Decimal('0.001')


def _num(valor):
    return Decimal(str(valor if valor is not None else 0))


def unidad_en_plural(unidad, cantidad):
    """«58 litros», «8 kg», «1 unidad»: la unidad concuerda con la cantidad."""
    unidad = (unidad or '').strip()
    if not unidad or _num(cantidad) == 1 or len(unidad) <= 3 or unidad.endswith('s') or any(c.isdigit() or c == '/' for c in unidad):
        return unidad
    palabras = unidad.split(' ', 1)
    primera = palabras[0]
    if primera[-1].lower() in 'aeiouáéíóú':
        primera += 's'
    elif primera[-1].lower() in 'dlnrj':
        primera += 'es'
    elif primera[-1].lower() == 'z':
        primera = primera[:-1] + 'ces'
    else:
        return unidad
    return ' '.join([primera, *palabras[1:]])


def _texto_cantidad(valor):
    return format(_num(valor).quantize(TRES, rounding=ROUND_HALF_UP).normalize(), 'f')


def _minutos(valor):
    valor = int(valor or 0)
    if valor >= 60 and valor % 60 == 0:
        return f'{valor // 60} h'
    if valor >= 60:
        return f'{valor // 60} h {valor % 60} min'
    return f'{valor} min'


# ------------------------------------------------------------------ datos
def datos_de_receta(receta, factor=1):
    """Serializa la receta y sus etapas a la estructura que usan los motores."""
    factor = _num(factor)
    etapas = []
    for etapa in receta.etapas.select_related('equipo', 'espacio').order_by('orden'):
        auxiliares = (
            [aux.nombre for aux in etapa.equipo.auxiliares.filter(estado='disponible')]
            if etapa.equipo_id else []
        )
        etapas.append({
            'orden': etapa.orden,
            'nombre': etapa.nombre,
            'tipo': etapa.tipo,
            'tipo_nombre': NOMBRES_TIPO.get(etapa.tipo, etapa.tipo),
            'equipo': etapa.equipo.nombre if etapa.equipo_id else '',
            'equipo_id': etapa.equipo_id,
            # Coordenadas del levantamiento de planta: alimentan el diagrama de recorrido.
            'equipo_x': str(etapa.equipo.coordenada_x) if etapa.equipo_id and etapa.equipo.coordenada_x is not None else None,
            'equipo_y': str(etapa.equipo.coordenada_y) if etapa.equipo_id and etapa.equipo.coordenada_y is not None else None,
            'auxiliares': auxiliares,
            'espacio': etapa.espacio.nombre if etapa.espacio_id else '',
            'espacio_id': etapa.espacio_id,
            'duracion_min': etapa.duracion_min,
            'espera_min': etapa.espera_min,
            'personas': etapa.personas,
            'rendimiento_pct': str(etapa.rendimiento_pct),
            'distancia_m': str(etapa.distancia_m),
            'punto_critico': etapa.punto_critico,
            'punto_control': etapa.punto_control,
            'parametro': etapa.parametro,
            'limite': etapa.limite,
            'instrucciones': etapa.instrucciones,
            'insumos': [],
            'salidas': [],
        })
    por_orden = {etapa['orden']: etapa for etapa in etapas}
    sin_etapa_insumos, sin_etapa_salidas = [], []
    for item in receta.insumos_para(factor):
        dato = {
            'nombre': item['consumible'].nombre,
            'cantidad': str(item['cantidad']),
            'unidad': item['consumible'].unidad_medida,
            'clasificacion': item['consumible'].clasificacion,
            'obligatorio': item['obligatorio'],
            'forma_parte': item.get('forma_parte', 'si'),
        }
        destino = por_orden.get(item['etapa'])
        (destino['insumos'] if destino else sin_etapa_insumos).append(dato)
    for item in receta.salidas_para(factor):
        if item['principal']:
            continue
        dato = {
            'nombre': item['producto'].nombre,
            'cantidad': str(item['cantidad']),
            'unidad': item['producto'].unidad_medida,
            'tipo': item['producto'].tipo,
            'externa_al_flujo': item['externa_al_flujo'],
        }
        destino = por_orden.get(item['etapa'])
        (destino['salidas'] if destino else sin_etapa_salidas).append(dato)
    return {
        'codigo': receta.codigo,
        'nombre': receta.nombre_publico,
        'unidad': receta.unidad.nombre,
        'producto': receta.producto.nombre,
        'unidad_producto': receta.producto.unidad_medida,
        # Sin normalizar, un Decimal('60.000') se lee como sesenta mil en la ficha.
        'cantidad_base': _texto_cantidad(receta.cantidad_base),
        'unidad_base': receta.unidad_base,
        'rendimiento_esperado': _texto_cantidad(receta.rendimiento_esperado),
        'factor': _texto_cantidad(factor),
        'instrucciones': receta.instrucciones,
        'software': [programa.nombre for programa in receta.software.filter(activo=True).order_by('nombre')],
        'etapas': etapas,
        'insumos_sin_etapa': sin_etapa_insumos,
        'salidas_sin_etapa': sin_etapa_salidas,
    }


# ----------------------------------------------------------------- resumen
def resumen_proceso(datos):
    etapas = datos.get('etapas', [])
    conteo = {tipo: 0 for tipo in TIPOS}
    tiempo_por_tipo = {tipo: 0 for tipo in TIPOS}
    distancia = Decimal('0')
    for etapa in etapas:
        tipo = etapa['tipo'] if etapa['tipo'] in conteo else 'operacion'
        conteo[tipo] += 1
        tiempo_por_tipo[tipo] += int(etapa['duracion_min']) + int(etapa['espera_min'])
        distancia += _num(etapa.get('distancia_m'))
    trabajo = sum(int(etapa['duracion_min']) for etapa in etapas)
    espera = sum(int(etapa['espera_min']) for etapa in etapas)
    return {
        'etapas': len(etapas),
        'trabajo_min': trabajo,
        'espera_min': espera,
        'duracion_min': trabajo + espera,
        'duracion_texto': _minutos(trabajo + espera),
        'trabajo_texto': _minutos(trabajo),
        'personas_max': max((int(etapa['personas']) for etapa in etapas), default=0),
        'puntos_criticos': sum(1 for etapa in etapas if etapa.get('punto_critico')),
        'puntos_control': sum(1 for etapa in etapas if etapa.get('punto_control')),
        'conteo': conteo,
        'tiempo_por_tipo': tiempo_por_tipo,
        'distancia_m': _texto_cantidad(distancia),
    }


# ---------------------------------------------------------- balance de masa
# Unidades que el balance sabe sumar, llevadas a kilos o litros (la leche pesa
# casi un kilo por litro; la simplificación es la habitual en una planta).
FACTOR_MASA = {'kg': Decimal('1'), 'litro': Decimal('1'), 'l': Decimal('1'), 'g': Decimal('0.001'), 'ml': Decimal('0.001')}


def _masa_agregada(etapa):
    """Lo que entra al producto en la etapa: insumos que se incorporan, en kilos o litros."""
    total = Decimal('0')
    for insumo in etapa.get('insumos', []):
        if insumo.get('forma_parte', 'si') != 'si':
            continue
        factor = FACTOR_MASA.get(str(insumo.get('unidad', '')).strip().lower())
        if factor is None:
            continue
        total += _num(insumo['cantidad']) * factor
    return total.quantize(TRES, rounding=ROUND_HALF_UP)


def balance_de_masa(datos, entrada=None):
    """Cuánto sigue, cuánto sale declarado y cuánto se pierde en cada etapa.

    Corre en la unidad de la corrida base (litros de leche) por porcentaje.
    Lo que se incorpora al producto (azúcar, pulpa, sal en seco) se suma en
    su etapa; la materia prima base es lo que entra y los auxiliares del
    proceso (salmuera, empaque) no cuentan. Cada salida declara si es externa
    al flujo, independientemente del rendimiento de su etapa. La última
    cantidad que continúa es lo que llega al producto y se compara con el
    rendimiento esperado.
    """
    entra = _num(entrada) if entrada is not None else _num(datos['cantidad_base']) * _num(datos['factor'])
    filas = []
    for etapa in datos.get('etapas', []):
        agregado = _masa_agregada(etapa)
        entra_total = entra + agregado
        rendimiento = _num(etapa.get('rendimiento_pct', 100)) / Decimal('100')
        continua = (entra_total * rendimiento).quantize(TRES, rounding=ROUND_HALF_UP)
        sale_del_flujo = (entra_total - continua).quantize(TRES, rounding=ROUND_HALF_UP)
        salidas = etapa.get('salidas', [])
        declarado = sum((_num(salida['cantidad']) * FACTOR_MASA.get(
            str(salida['unidad']).strip().lower(), Decimal('1')
        ) for salida in salidas), Decimal('0'))
        externo = sum((_num(salida['cantidad']) * FACTOR_MASA.get(
            str(salida['unidad']).strip().lower(), Decimal('1')
        ) for salida in salidas if salida.get('externa_al_flujo', False)), Decimal('0'))
        interno = declarado - externo
        perdida = max(sale_del_flujo - interno, Decimal('0'))
        exceso = max(interno - sale_del_flujo, Decimal('0'))
        filas.append({
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'tipo': etapa['tipo'],
            'entra': _texto_cantidad(entra),
            'agregado': _texto_cantidad(agregado),
            'continua': _texto_cantidad(continua),
            'declarado': _texto_cantidad(declarado),
            'salidas': [
                f"{salida['nombre']} {_texto_cantidad(salida['cantidad'])} {unidad_en_plural(salida['unidad'], salida['cantidad'])}"
                + (' (salida externa al flujo)' if salida.get('externa_al_flujo') else '')
                for salida in etapa.get('salidas', [])
            ],
            'perdida': _texto_cantidad(perdida),
            'externo': _texto_cantidad(externo) if externo else '',
            'exceso': _texto_cantidad(exceso) if exceso else '',
            'rendimiento_pct': _texto_cantidad(etapa.get('rendimiento_pct', 100)),
        })
        entra = continua
    esperado = _num(datos['rendimiento_esperado']) * _num(datos['factor'])
    return {
        'unidad_base': datos['unidad_base'],
        'entrada': _texto_cantidad(_num(entrada) if entrada is not None else _num(datos['cantidad_base']) * _num(datos['factor'])),
        'filas': filas,
        'producto_por_balance': _texto_cantidad(entra),
        'producto_esperado': _texto_cantidad(esperado),
        'unidad_producto': datos['unidad_producto'],
        'diferencia': _texto_cantidad(entra - esperado),
    }


# -------------------------------------------------------------- cronograma
def cronograma(datos):
    """Las etapas una tras otra, en minutos desde el inicio de la corrida."""
    filas, minuto = [], 0
    for etapa in datos.get('etapas', []):
        duracion = int(etapa['duracion_min']) + int(etapa['espera_min'])
        filas.append({
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'tipo': etapa['tipo'],
            'equipo': etapa.get('equipo', ''),
            'espacio': etapa.get('espacio', ''),
            'inicio_min': minuto,
            'fin_min': minuto + duracion,
            'duracion_min': duracion,
            'personas': int(etapa['personas']),
        })
        minuto += duracion
    return {'filas': filas, 'total_min': minuto, 'total_texto': _minutos(minuto)}


# ---------------------------------------------------------------- diagramas
# Se dibujan en ``diagramas.py`` (una geometría para la web y el PDF).
def diagrama_flujo_svg(datos):
    """Flujo del proceso entre inicio y fin, con entradas, salidas y PCC numerados."""
    from apps.plantas_piloto.operacion.presentation.diagramas import diagrama_flujo
    return diagrama_flujo(datos).svg()


def diagrama_sinoptico_svg(datos):
    """Diagrama de operaciones (DOP): O-n e I-n con los materiales que se incorporan."""
    from apps.plantas_piloto.operacion.presentation.diagramas import diagrama_operaciones
    return diagrama_operaciones(datos).svg()


def cursograma_analitico(datos):
    """La tabla del cursograma: símbolo, tiempo y distancia por etapa, con totales."""
    filas = []
    resumen = {tipo: {'cantidad': 0, 'tiempo_min': 0, 'distancia_m': Decimal('0')} for tipo in TIPOS}
    for etapa in datos.get('etapas', []):
        tipo = etapa['tipo'] if etapa['tipo'] in resumen else 'operacion'
        # ASME: la espera declarada dentro de una etapa es una demora, no tiempo de su símbolo.
        tiempo = int(etapa['duracion_min'])
        espera = int(etapa['espera_min'])
        distancia = _num(etapa.get('distancia_m'))
        resumen[tipo]['cantidad'] += 1
        resumen[tipo]['tiempo_min'] += tiempo
        resumen['espera']['tiempo_min'] += espera
        resumen[tipo]['distancia_m'] += distancia
        filas.append({
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'tipo': tipo,
            'simbolo': SIMBOLOS[tipo],
            'marcas': {t: t == tipo for t in TIPOS},
            'tiempo_min': tiempo,
            'tiempo_texto': _minutos(tiempo),
            'espera_min': espera,
            'distancia_m': _texto_cantidad(distancia),
            'donde': etapa.get('equipo') or etapa.get('espacio') or '',
            'personas': int(etapa['personas']),
            'observacion': ' · '.join(filter(None, [
                f"PCC: {etapa['parametro']} ({etapa['limite']})" if etapa.get('punto_critico') else '',
                f"PC: {etapa['parametro']} ({etapa['limite']})" if etapa.get('punto_control') else '',
                ', '.join(f"{i['nombre']}" for i in etapa.get('insumos', [])),
            ])),
        })
    return {
        'tipos': [(tipo, NOMBRES_TIPO[tipo], SIMBOLOS[tipo]) for tipo in TIPOS],
        'filas': filas,
        'resumen': {
            tipo: {
                'cantidad': valores['cantidad'],
                'tiempo_min': valores['tiempo_min'],
                'tiempo_texto': _minutos(valores['tiempo_min']),
                'distancia_m': _texto_cantidad(valores['distancia_m']),
            }
            for tipo, valores in resumen.items()
        },
        'resumen_por_tipo': [
            {
                'tipo': tipo,
                'nombre': NOMBRES_TIPO[tipo],
                'simbolo': SIMBOLOS[tipo],
                'cantidad': resumen[tipo]['cantidad'],
                'tiempo_texto': _minutos(resumen[tipo]['tiempo_min']),
                'distancia_m': _texto_cantidad(resumen[tipo]['distancia_m']),
            }
            for tipo in TIPOS
        ],
        'total_min': sum(v['tiempo_min'] for v in resumen.values()),
        'total_distancia_m': _texto_cantidad(sum((v['distancia_m'] for v in resumen.values()), Decimal('0'))),
    }


# --------------------------------------------------------------------- guía
def guia_desde_proceso(datos):
    """Lo que la guía de práctica toma del proceso: recursos y procedimiento."""
    etapas = datos.get('etapas', [])
    equipos, software = [], list(datos.get('software', []))
    for etapa in etapas:
        nombre = etapa.get('equipo')
        if nombre and nombre not in equipos:
            equipos.append(nombre)
        for auxiliar in etapa.get('auxiliares', []):
            etiqueta = f'{auxiliar} (auxiliar)'
            if etiqueta not in equipos:
                equipos.append(etiqueta)
    materiales = []
    for etapa in etapas:
        for insumo in etapa.get('insumos', []):
            materiales.append(f"{insumo['nombre']}: {_texto_cantidad(insumo['cantidad'])} {insumo['unidad']} (etapa {etapa['orden']})")
    for insumo in datos.get('insumos_sin_etapa', []):
        materiales.append(f"{insumo['nombre']}: {_texto_cantidad(insumo['cantidad'])} {insumo['unidad']}")
    pasos = []
    for etapa in etapas:
        donde = ' · '.join(filter(None, [etapa.get('equipo'), etapa.get('espacio')]))
        tiempo = _minutos(int(etapa['duracion_min']) + int(etapa['espera_min']))
        detalle = escape(etapa.get('instrucciones') or '')
        entra = ', '.join(f"{i['nombre']} {_texto_cantidad(i['cantidad'])} {i['unidad']}" for i in etapa.get('insumos', []))
        sale = ', '.join(f"{s['nombre']} {_texto_cantidad(s['cantidad'])} {s['unidad']}"
                        + (' (salida externa al flujo)' if s.get('externa_al_flujo') else '')
                        for s in etapa.get('salidas', []))
        partes = [f'<p><strong>{escape(etapa["nombre"])}</strong> ({escape(_nombre_tipo(etapa["tipo"]))}{", " + escape(donde) if donde else ""}, {escape(tiempo)}).']
        if detalle:
            partes.append(f' {detalle}')
        if entra:
            partes.append(f' Entra: {escape(entra)}.')
        if sale:
            partes.append(f' Sale: {escape(sale)}.')
        if etapa.get('punto_critico'):
            partes.append(f' <em>Punto crítico de control: {escape(etapa.get("parametro") or "")}, {escape(etapa.get("limite") or "")}.</em>')
        partes.append('</p>')
        pasos.append(f'<li>{"".join(partes)}</li>')
    criticos = [
        f'<li>{escape(etapa["nombre"])}: {escape(etapa.get("parametro") or "")} ({escape(etapa.get("limite") or "")}).</li>'
        for etapa in etapas if etapa.get('punto_critico')
    ]
    resumen = resumen_proceso(datos)
    balance = balance_de_masa(datos)
    return {
        'proceso': datos.get('nombre', ''),
        'equipos': equipos,
        'software': software,
        'materiales': materiales,
        'duracion': f"{resumen['duracion_texto']} ({resumen['trabajo_texto']} de trabajo)" if etapas else '',
        'procedimiento_html': f'<ol class="guide-steps">{"".join(pasos)}</ol>' if pasos else '',
        'seguridad_html': (
            '<p>Puntos críticos de control del proceso, que se registran en cada corrida:</p>'
            f'<ul>{"".join(criticos)}</ul>'
        ) if criticos else '',
        'resultados_html': (
            f'<p>Con {escape(balance["entrada"])} {escape(balance["unidad_base"])} se esperan '
            f'{escape(balance["producto_esperado"])} {escape(balance["unidad_producto"])} de {escape(datos.get("producto", ""))}; '
            f'el balance de masa por etapas da {escape(balance["producto_por_balance"])}.</p>'
        ) if etapas else '',
    }


def _nombre_tipo(tipo):
    return NOMBRES_TIPO.get(tipo, 'Operación').lower()
