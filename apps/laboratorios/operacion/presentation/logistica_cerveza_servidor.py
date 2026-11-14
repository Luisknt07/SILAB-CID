"""Motor autoritativo propio para el juego de distribución UPEC (sin E/S ni Django).

Versión 2.0.0: conserva las ecuaciones, demanda y retardos de la versión JS
1.0.0; admite decisiones simultáneas de los cuatro roles. La fábrica produce
como máximo 24 unidades/semana (4 durante la disrupción): es una adaptación
pedagógica explícita, no una reproducción exacta del tablero MIT, sin capacidad
limitada. La semilla solo afecta al caso pico. No hay datos operativos reales.

El estado completo es PRIVADO del servidor. La API recibe únicamente pedidos;
para responder a participantes debe usar observacion, nunca serializar estado.
Todos los puntos públicos reconstruyen/verifican el estado contra su registro
de decisiones: no aceptan inventarios, costos o resultados calculados por el
cliente. La autorización, concurrencia y persistencia pertenecen a la API.

Orden del turno: recibir envíos y pedidos vencidos; atender primero el atraso;
recoger decisiones simultáneas; registrar pedidos/producción y nuevos envíos;
cobrar inventario y atraso al cierre. Un pedido o envío nuevo nunca llega en el
mismo turno. La observación de decisión presenta la recepción/demanda LOCAL
que ya ocurrió al abrir ese turno, sin pedidos aún en tránsito ni demanda futura.

Fuentes conceptuales (implementación original, no software MIT):
https://web.mit.edu/jsterman/www/SDG/beergame.html
https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf
"""

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import math


VERSION = '2.0.0'
DATASET = 'cadena-sintetica-upec-1'
ROLES = ('minorista', 'mayorista', 'distribuidor', 'fabrica')
NOMBRES = dict(zip(ROLES, ('Minorista', 'Mayorista', 'Distribuidor', 'Fábrica')))
MAX_PEDIDO = 200
MAX_SEMANAS = 52
PARAMETROS_PREDETERMINADOS = {
    'semanas': 24, 'retardo_pedido': 1, 'retardo_envio': 2,
    'retardo_produccion': 2, 'inventario_inicial': 12,
    'costo_inventario': 0.5, 'costo_pendiente': 1.0,
}
_REGLAS = [
    'Cuatro roles deciden simultáneamente; solo reciben información local.',
    'Los pedidos y envíos tienen retardos; el atraso no se pierde y se atiende primero.',
    'El costo semanal se calcula sobre inventario y atraso al cierre.',
    'Los roles sin decisión usan una política local de reposición declarada.',
    'La fábrica tiene capacidad limitada; el pedido solicitado y la producción efectiva se registran por separado.',
]
CASOS = {
    'base': {
        'titulo': 'Cadena con cambio de demanda',
        'descripcion': 'Observa cómo las decisiones locales y los retardos pueden amplificar un cambio de demanda.',
        'parametros': deepcopy(PARAMETROS_PREDETERMINADOS), 'reglas': deepcopy(_REGLAS),
    },
    'pico': {
        'titulo': 'Variación y pico de demanda',
        'descripcion': 'Gestiona variaciones reproducibles de pedidos, reveladas únicamente al llegar a cada rol.',
        'parametros': deepcopy(PARAMETROS_PREDETERMINADOS), 'reglas': deepcopy(_REGLAS),
    },
    'disrupcion': {
        'titulo': 'Resiliencia ante una disrupción',
        'descripcion': 'Gestiona una interrupción temporal; sus efectos locales se anuncian cuando ocurren.',
        'parametros': deepcopy(PARAMETROS_PREDETERMINADOS), 'reglas': deepcopy(_REGLAS),
    },
}


def _entero(valor, minimo, maximo, nombre):
    # bool es subclase de int: la comprobación exacta evita aceptar true como 1.
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValueError(f'{nombre}: use un entero de {minimo} a {maximo}.')
    return valor


def _costo(valor, nombre):
    if type(valor) not in (int, float):
        raise ValueError(f'{nombre}: use un número de 0 a 10 con hasta dos decimales.')
    try:
        decimal = Decimal(str(valor))
    except InvalidOperation as exc:
        raise ValueError(f'{nombre}: costo inválido.') from exc
    if not decimal.is_finite() or not 0 <= decimal <= 10 or decimal * 100 != (decimal * 100).to_integral_value():
        raise ValueError(f'{nombre}: use un número de 0 a 10 con hasta dos decimales.')
    return float(decimal)


def _parametros(entrada=None):
    if entrada is None:
        entrada = {}
    if type(entrada) is not dict or set(entrada) - set(PARAMETROS_PREDETERMINADOS):
        raise ValueError('Parámetros desconocidos o formato inválido.')
    parametros = {**PARAMETROS_PREDETERMINADOS, **entrada}
    for clave, minimo, maximo in (
        ('semanas', 12, MAX_SEMANAS), ('retardo_pedido', 1, 3),
        ('retardo_envio', 1, 4), ('retardo_produccion', 1, 4), ('inventario_inicial', 0, 100),
    ):
        _entero(parametros[clave], minimo, maximo, clave)
    for clave in ('costo_inventario', 'costo_pendiente'):
        parametros[clave] = _costo(parametros[clave], clave)
    return parametros


def _decisiones(entrada):
    if type(entrada) is not dict or set(entrada) - set(ROLES):
        raise ValueError('Las decisiones deben ser un objeto con roles conocidos.')
    return {rol: _entero(entrada[rol], 0, MAX_PEDIDO, f'Pedido de {rol}') for rol in ROLES if rol in entrada}


def _centavos(valor):
    return int(Decimal(str(valor)) * 100)


def _moneda(centavos):
    return centavos / 100


def _aleatorio(semilla, semana):
    valor = semilla
    for _ in range(semana):
        valor = valor * 16807 % 2147483647
    return valor / 2147483647


def _demanda(estado, semana):
    if semana <= 4:
        return 4
    if estado['caso'] == 'pico':
        base = 16 if 9 <= semana <= 12 else 8
        return base + math.floor(_aleatorio(estado['semilla'], semana) * 3) - 1
    return 8


def _disrupcion(estado, semana):
    return estado['caso'] == 'disrupcion' and 9 <= semana <= 12


def _capacidad(estado, semana):
    return 4 if _disrupcion(estado, semana) else 24


def _fisico(estado):
    return sum(etapa['inventario'] + sum(item['cantidad'] for item in etapa['envios'])
               for etapa in estado['etapas'].values())


def crear_estado(caso='base', semilla=42, parametros=None):
    """Crea JSON privado; parámetros opcionales acotados, sin reloj ni azar global."""
    if type(caso) is not str or caso not in CASOS:
        raise ValueError('Caso desconocido.')
    _entero(semilla, 1, 2147483647, 'Semilla')
    parametros = _parametros(parametros)
    etapas = {}
    for indice, rol in enumerate(ROLES):
        retardo = parametros['retardo_produccion'] if indice == 3 else parametros['retardo_envio']
        etapas[rol] = {
            'inventario': parametros['inventario_inicial'], 'pendiente': 0,
            'pronostico': 4.0, 'costo_centavos': 0,
            'suministro_pendiente': 4 * (retardo + (parametros['retardo_pedido'] if indice < 3 else 0)),
            'envios': [{'vence': semana + 1, 'cantidad': 4} for semana in range(retardo)],
            'pedidos': [] if indice == 0 else [
                {'vence': semana + 1, 'cantidad': 4} for semana in range(parametros['retardo_pedido'])],
        }
    estado = {
        'version_motor': VERSION, 'version_datos': DATASET, 'caso': caso, 'semilla': semilla,
        'parametros': parametros, 'semana': 0, 'etapas': etapas, 'decisiones': [], 'historial': [],
        'producido': 0, 'entregado': 0, 'demanda_total': 0, 'fisico_inicial': 0,
    }
    estado['fisico_inicial'] = _fisico(estado)
    return estado


def _vencidos(cola, semana):
    return sum(item['cantidad'] for item in cola if item['vence'] <= semana)


def _preparar(estado):
    semana = estado['semana'] + 1
    cambios = {}
    for indice, rol in enumerate(ROLES):
        etapa = estado['etapas'][rol]
        recibido = _vencidos(etapa['envios'], semana)
        pedido = _demanda(estado, semana) if indice == 0 else _vencidos(etapa['pedidos'], semana)
        disponible = etapa['inventario'] + recibido
        obligacion = etapa['pendiente'] + pedido
        despachado = min(disponible, obligacion)
        cambios[rol] = {
            'recibido': recibido, 'demanda_visible': pedido, 'despachado': despachado,
            'atendido_en_semana': max(0, despachado - etapa['pendiente']),
            'inventario': disponible - despachado, 'pendiente': obligacion - despachado,
            'suministro_pendiente': etapa['suministro_pendiente'] - recibido,
            'pronostico': 0.3 * pedido + 0.7 * etapa['pronostico'],
        }
    return cambios


def _politica(parametros, etapa, rol):
    retardo = (parametros['retardo_produccion'] if rol == 'fabrica'
               else parametros['retardo_pedido'] + parametros['retardo_envio'])
    objetivo = 12 + etapa['pronostico'] * retardo
    posicion = etapa['inventario'] - etapa['pendiente'] + etapa['suministro_pendiente']
    # floor(x + .5) conserva Math.round de JS para pedidos no negativos.
    return max(0, min(MAX_PEDIDO, math.floor(objetivo - posicion + 0.5)))


def _comprobar_balances(estado):
    if _fisico(estado) != estado['fisico_inicial'] + estado['producido'] - estado['entregado']:
        raise ValueError('No se conserva el balance físico de la cadena.')
    for indice, rol in enumerate(ROLES):
        etapa = estado['etapas'][rol]
        filas = [turno['roles'][rol] for turno in estado['historial']]
        if any(type(etapa[clave]) is not int or etapa[clave] < 0
               for clave in ('inventario', 'pendiente', 'suministro_pendiente', 'costo_centavos')):
            raise ValueError('Estado local negativo o no entero.')
        if etapa['inventario'] and etapa['pendiente']:
            raise ValueError('No puede quedar inventario sin atender un atraso.')
        if etapa['pendiente'] != sum(fila['demanda_visible'] - fila['despachado'] for fila in filas):
            raise ValueError('No se conserva el balance de pedidos pendientes.')
        if etapa['inventario'] != estado['parametros']['inventario_inicial'] + sum(
            fila['recibido'] - fila['despachado'] for fila in filas
        ):
            raise ValueError('No se conserva el inventario local.')
        retardo = (estado['parametros']['retardo_produccion'] if indice == 3 else
                   estado['parametros']['retardo_envio'] + estado['parametros']['retardo_pedido'])
        if etapa['suministro_pendiente'] != 4 * retardo + sum(
            fila['pedido'] - fila['recibido'] for fila in filas
        ):
            raise ValueError('No se conserva el suministro solicitado.')
        if etapa['costo_centavos'] != sum(fila['costo_centavos'] for fila in filas):
            raise ValueError('No se conserva el costo local.')


def _avanzar_interno(estado, decisiones):
    """Muta únicamente una reconstrucción nueva, nunca un estado del llamador."""
    if estado['semana'] >= estado['parametros']['semanas']:
        raise ValueError('La partida ya terminó.')
    decisiones = _decisiones(decisiones)
    parametros = estado['parametros']
    semana = estado['semana'] + 1
    cambios = _preparar(estado)
    filas = {}
    for rol in ROLES:
        etapa, cambio = estado['etapas'][rol], cambios[rol]
        solicitado = decisiones.get(rol, _politica(parametros, cambio, rol))
        pedido = min(solicitado, _capacidad(estado, semana)) if rol == 'fabrica' else solicitado
        etapa['envios'] = [item for item in etapa['envios'] if item['vence'] > semana]
        etapa['pedidos'] = [item for item in etapa['pedidos'] if item['vence'] > semana]
        etapa.update({clave: cambio[clave] for clave in ('inventario', 'pendiente', 'pronostico')})
        etapa['suministro_pendiente'] = cambio['suministro_pendiente'] + pedido
        costo = (etapa['inventario'] * _centavos(parametros['costo_inventario'])
                 + etapa['pendiente'] * _centavos(parametros['costo_pendiente']))
        etapa['costo_centavos'] += costo
        filas[rol] = {
            **{clave: cambio[clave] for clave in (
                'recibido', 'demanda_visible', 'despachado', 'atendido_en_semana', 'inventario', 'pendiente')},
            'pedido_solicitado': solicitado, 'pedido': pedido, 'automatico': rol not in decisiones,
            'suministro_pendiente': etapa['suministro_pendiente'], 'costo_centavos': costo,
            'costo_acumulado_centavos': etapa['costo_centavos'],
        }
    for indice in range(3):
        rol, superior = ROLES[indice], ROLES[indice + 1]
        estado['etapas'][superior]['pedidos'].append({
            'vence': semana + parametros['retardo_pedido'], 'cantidad': filas[rol]['pedido']})
        retardo = parametros['retardo_envio'] + (2 if indice == 0 and _disrupcion(estado, semana) else 0)
        estado['etapas'][rol]['envios'].append({
            'vence': semana + retardo, 'cantidad': filas[superior]['despachado']})
    estado['etapas']['fabrica']['envios'].append({
        'vence': semana + parametros['retardo_produccion'], 'cantidad': filas['fabrica']['pedido']})
    for rol in ROLES:
        filas[rol]['en_transito'] = sum(item['cantidad'] for item in estado['etapas'][rol]['envios'])
    estado['producido'] += filas['fabrica']['pedido']
    estado['entregado'] += filas['minorista']['despachado']
    estado['demanda_total'] += filas['minorista']['demanda_visible']
    estado['semana'] = semana
    estado['decisiones'].append(decisiones)
    estado['historial'].append({
        'semana': semana, 'demanda': filas['minorista']['demanda_visible'],
        'disrupcion': _disrupcion(estado, semana), 'roles': filas,
        'costo_total_centavos': sum(etapa['costo_centavos'] for etapa in estado['etapas'].values()),
    })
    _comprobar_balances(estado)
    return estado


def repetir_partida(decisiones, *, caso='base', semilla=42, parametros=None):
    """Recalcula todo desde pedidos, nunca desde resultados importados."""
    estado = crear_estado(caso, semilla, parametros)
    if type(decisiones) is not list or len(decisiones) > estado['parametros']['semanas']:
        raise ValueError('Registro de decisiones inválido o demasiado largo.')
    for pedidos in decisiones:
        _avanzar_interno(estado, pedidos)
    return estado


def _json_canonico(valor):
    try:
        serializado = json.dumps(valor, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError('El estado debe contener únicamente datos JSON válidos.') from exc
    if len(serializado) > 512_000:
        raise ValueError('Estado demasiado grande.')
    return serializado


def validar_estado(estado):
    """Restaura un estado JSON privado y verifica cada resultado por repetición.

    No sustituye autenticación/autorización: una partida válida de otra persona
    sigue sin dar derecho a acceder a ella. La API debe cargar su propio estado
    desde persistencia, nunca tomarlo del cuerpo de una petición.
    """
    if type(estado) is not dict or estado.get('version_motor') != VERSION or estado.get('version_datos') != DATASET:
        raise ValueError('Versión de motor o datos incompatible.')
    requerido = set(crear_estado())
    if set(estado) != requerido or type(estado['historial']) is not list or len(estado['historial']) > MAX_SEMANAS:
        raise ValueError('Estructura del estado inválida.')
    reconstruido = repetir_partida(
        estado['decisiones'], caso=estado['caso'], semilla=estado['semilla'], parametros=estado['parametros'])
    if _json_canonico(estado) != _json_canonico(reconstruido):
        raise ValueError('El estado o sus resultados no coinciden con sus decisiones.')
    return reconstruido


def avanzar(estado, decisiones):
    """Resuelve un turno simultáneo; roles ausentes automáticos, sin mutar entrada."""
    decisiones = _decisiones(decisiones)
    nuevo = validar_estado(estado)
    return _avanzar_interno(nuevo, decisiones)


def _fila_publica(fila, semana):
    return {
        'semana': semana,
        **{clave: fila[clave] for clave in (
            'demanda_visible', 'recibido', 'despachado', 'atendido_en_semana', 'inventario', 'pendiente',
            'pedido', 'pedido_solicitado', 'en_transito', 'suministro_pendiente', 'automatico')},
        'costo_semana': _moneda(fila['costo_centavos']),
        'costo_acumulado': _moneda(fila['costo_acumulado_centavos']),
    }


def observacion(estado, rol, final=False):
    """Vista local; final=True abre el informe global solo si la partida terminó."""
    if type(rol) is not str or rol not in ROLES or type(final) is not bool:
        raise ValueError('Rol o modo de observación inválido.')
    estado = validar_estado(estado)
    terminado = estado['semana'] == estado['parametros']['semanas']
    if final and not terminado:
        raise ValueError('El análisis global solo está disponible al finalizar.')
    semana = estado['semana'] if terminado else estado['semana'] + 1
    etapa = estado['etapas'][rol]
    actual = estado['historial'][-1]['roles'][rol] if terminado else _preparar(estado)[rol]
    evento = ''
    if not terminado and _disrupcion(estado, semana):
        if rol == 'minorista':
            evento = 'Los envíos despachados hacia tu estación este turno tardan dos semanas adicionales.'
        elif rol == 'fabrica':
            evento = 'La capacidad de producción de este turno está limitada a cuatro unidades.'
    sugerido = None if terminado else _politica(estado['parametros'], actual, rol)
    if rol == 'fabrica' and sugerido is not None:
        sugerido = min(sugerido, _capacidad(estado, semana))
    vista = {
        'version_motor': VERSION, 'version_datos': DATASET, 'rol': rol, 'nombre': NOMBRES[rol],
        'semana': semana, 'horizonte': estado['parametros']['semanas'], 'semanas_resueltas': estado['semana'],
        'finalizado': terminado, 'inventario': actual['inventario'], 'pendiente': actual['pendiente'],
        'en_transito': sum(item['cantidad'] for item in etapa['envios'] if terminado or item['vence'] > semana),
        'suministro_pendiente': actual['suministro_pendiente'], 'costo_acumulado': _moneda(etapa['costo_centavos']),
        'demanda_visible': actual['demanda_visible'], 'recibido': actual['recibido'], 'despachado': actual['despachado'],
        'pedido_sugerido': sugerido, 'pedido_maximo': MAX_PEDIDO, 'evento': evento,
        'parametros': deepcopy(estado['parametros']),
        'historial': [_fila_publica(turno['roles'][rol], turno['semana']) for turno in estado['historial']],
    }
    if rol == 'fabrica':
        vista['capacidad_produccion'] = _capacidad(estado, semana)
    if final:
        vista['resultado'] = _resultado(estado)
    return vista


def _varianza(valores):
    if not valores:
        return 0.0
    media = sum(valores) / len(valores)
    return sum((valor - media) ** 2 for valor in valores) / len(valores)


def _porcentaje(numerador, denominador):
    return 100 * numerador / denominador if denominador else 100.0


def _indicadores(estado):
    historial = estado['historial']
    varianza_demanda = _varianza([turno['demanda'] for turno in historial])
    por_rol = {}
    for rol in ROLES:
        filas = [turno['roles'][rol] for turno in historial]
        pedidos = [fila['pedido'] for fila in filas]
        demanda = sum(fila['demanda_visible'] for fila in filas)
        por_rol[rol] = {
            'costo': _moneda(estado['etapas'][rol]['costo_centavos']),
            'inventario_final': estado['etapas'][rol]['inventario'],
            'pendiente_final': estado['etapas'][rol]['pendiente'],
            'suministro_pendiente_final': estado['etapas'][rol]['suministro_pendiente'],
            'en_transito_final': sum(item['cantidad'] for item in estado['etapas'][rol]['envios']),
            'inventario_promedio': sum(fila['inventario'] for fila in filas) / len(filas) if filas else 0.0,
            'pendiente_promedio': sum(fila['pendiente'] for fila in filas) / len(filas) if filas else 0.0,
            'pendiente_maximo': max((fila['pendiente'] for fila in filas), default=0),
            'semanas_con_pendiente': sum(fila['pendiente'] > 0 for fila in filas),
            'servicio_acumulado_pct': _porcentaje(sum(fila['despachado'] for fila in filas), demanda),
            'servicio_inmediato_pct': _porcentaje(sum(fila['atendido_en_semana'] for fila in filas), demanda),
            'pedido_maximo': max(pedidos, default=0), 'varianza_pedidos': _varianza(pedidos),
            'efecto_latigo': _varianza(pedidos) / varianza_demanda if varianza_demanda > 0 else None,
            'variacion_total_pedidos': sum(abs(actual - anterior) for anterior, actual in zip(pedidos, pedidos[1:])),
        }
    return {
        'costo_total': _moneda(sum(etapa['costo_centavos'] for etapa in estado['etapas'].values())),
        'demanda_total': estado['demanda_total'], 'entregado_total': estado['entregado'],
        'producido_total': estado['producido'],
        'servicio_pct': _porcentaje(estado['entregado'], estado['demanda_total']),
        'servicio_inmediato_pct': por_rol['minorista']['servicio_inmediato_pct'],
        'inventario_fisico_final': _fisico(estado),
        'balance_fisico': _fisico(estado) - estado['fisico_inicial'] - estado['producido'] + estado['entregado'],
        'pendiente_cliente_final': estado['etapas']['minorista']['pendiente'],
        'varianza_demanda': varianza_demanda,
        'utilizacion_produccion_pct': _porcentaje(estado['producido'], sum(
            _capacidad(estado, turno['semana']) for turno in historial)),
        'por_rol': por_rol,
    }


def _resultado(estado):
    indicadores = _indicadores(estado)
    referencia = repetir_partida([{} for _ in estado['decisiones']], caso=estado['caso'],
                                  semilla=estado['semilla'], parametros=estado['parametros'])
    base = _indicadores(referencia)
    costo, costo_base = indicadores['costo_total'], base['costo_total']
    razon_costo = min(1.0, costo_base / costo) if costo else 1.0
    latigos = [dato['efecto_latigo'] for dato in indicadores['por_rol'].values() if dato['efecto_latigo'] is not None]
    peor_latigo = max(latigos, default=1.0)
    estabilidad = 1 / max(1.0, peor_latigo)
    criterios = [
        {'id': 'servicio', 'titulo': 'Atención de demanda acumulada', 'peso': 35,
         'valor': indicadores['servicio_pct'], 'puntos': round(35 * indicadores['servicio_pct'] / 100, 2),
         'formula': '35 × entregado al cliente / demanda acumulada',
         'interpretacion': 'La entrega tardía cuenta aquí; revisar además el servicio inmediato y el atraso final.'},
        {'id': 'costo', 'titulo': 'Costo respecto a la política de referencia', 'peso': 40,
         'valor': razon_costo, 'puntos': round(40 * razon_costo, 2),
         'formula': '40 × min(1, costo referencia / costo equipo); si costo equipo = 0, obtiene 40',
         'interpretacion': 'La referencia usa información local y los mismos parámetros; no es un óptimo universal.'},
        {'id': 'estabilidad', 'titulo': 'Amplificación de pedidos', 'peso': 25,
         'valor': peor_latigo, 'puntos': round(25 * estabilidad, 2),
         'formula': '25 / max(1, máximo efecto látigo de los cuatro roles)',
         'interpretacion': 'Efecto látigo = varianza poblacional de pedidos / varianza de demanda del cliente. '
                           'Sin varianza de demanda se informa nulo y se asignan 25 puntos a este criterio.'},
    ]
    return {
        'version_motor': VERSION, 'version_datos': DATASET, 'caso': estado['caso'], 'semilla': estado['semilla'],
        'semana': estado['semana'], 'horizonte': estado['parametros']['semanas'], 'finalizado': True,
        'parametros': deepcopy(estado['parametros']), 'indicadores': indicadores,
        'puntaje': min(100.0, max(0.0, round(sum(criterio['puntos'] for criterio in criterios), 2))),
        'rubrica': {'version': 'upec-operacion-1', 'maximo': 100, 'criterios': criterios,
                    'aviso': 'Índice pedagógico de esta simulación: no certifica competencias ni rentabilidad real.'},
        'referencia': {
            'politica': 'Reposición local: objetivo 12 + pronóstico × retardo; pronóstico 0.3 × pedido recibido '
                        '+ 0.7 × pronóstico anterior; descontar posición inventario − atraso + suministro pendiente.',
            'nota': 'Caso, semilla, horizonte y retardos idénticos; todos los roles automáticos. No es un óptimo universal.',
            'indicadores': base, 'diferencia_costo': round(costo - costo_base, 2),
        },
        'definiciones': {
            'unidades': 'Unidades sintéticas y unidades monetarias (u.m.) sintéticas; costo registrado a centavos.',
            'servicio_inmediato': 'Demanda nueva atendida en su misma semana después de atender el atraso previo.',
            'efecto_latigo': 'Comparación con demanda del cliente final, no con la demanda recibida por cada eslabón.',
            'cierre': 'No se liquidan existencias ni tránsito al final. Se publican saldos para discutir el efecto horizonte.',
        },
        'historial': [
            {'semana': turno['semana'], 'demanda': turno['demanda'], 'disrupcion': turno['disrupcion'],
             'costo_total': _moneda(turno['costo_total_centavos']),
             'roles': {rol: _fila_publica(turno['roles'][rol], turno['semana']) for rol in ROLES}}
            for turno in estado['historial']
        ],
    }


def resultado(estado):
    """Analítica global y rúbrica únicamente al terminar; todo recalculado."""
    estado = validar_estado(estado)
    if estado['semana'] != estado['parametros']['semanas']:
        raise ValueError('El resultado global solo está disponible al finalizar.')
    return _resultado(estado)
