"""Los motores de cálculo del aula: balance de energía, de línea y de materiales.

Trabajan sobre la estructura plana que devuelve ``datos_de_receta``, no sobre
los modelos ni sobre la petición, así que sirven igual para la corrida real de
la planta, para el escenario que el estudiante edita en el simulador y para el
documento de una simulación guardada. Viven aparte de las vistas justamente por
eso: quien necesita calcular no tiene que arrastrar media aula consigo.

Las constantes térmicas son de la leche y sus derivados líquidos; una planta
que procese otra cosa necesitará las suyas.
"""

import math
import re
from collections import OrderedDict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TRES = Decimal('0.001')

# Propiedades térmicas de la leche y sus derivados líquidos, y el calor
# latente del vapor saturado que entrega una caldera a 100 °C.
CALOR_ESPECIFICO = Decimal('3.93')     # kJ/(kg·K)
DENSIDAD = Decimal('1.03')             # kg por litro
CALOR_LATENTE_VAPOR = Decimal('2257')  # kJ/kg
COP_FRIO = Decimal('2.5')              # kJ retirados por cada kJ eléctrico
ETAPAS_CALIENTES = re.compile(r'pasteur|calent|cocc|coci|hilad|escald|concentr|evapor|termiz|incub|ferment', re.I)
ETAPAS_FRIAS = re.compile(r'enfri|refriger|c[aá]mara|madur|fr[ií]o', re.I)
TEMPERATURA = re.compile(r'(-?\d+(?:[.,]\d+)?)\s*°\s*C')


def _num(valor):
    return Decimal(str(valor if valor is not None else 0))


def _decimal(texto, predeterminado):
    """Un número escrito por la persona (con coma o con punto) o el valor por defecto."""
    try:
        return Decimal(str(texto).strip().replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return Decimal(str(predeterminado))


def _texto(valor, decimales=TRES):
    return format(_num(valor).quantize(decimales, rounding=ROUND_HALF_UP).normalize(), 'f')


# ------------------------------------------------------ balance de materia y energía
def temperatura_de(etapa):
    """La temperatura escrita en el parámetro, el límite o las instrucciones de la etapa."""
    for texto in (etapa.get('parametro'), etapa.get('limite'), etapa.get('instrucciones')):
        encontrado = TEMPERATURA.search(texto or '')
        if encontrado:
            return Decimal(encontrado.group(1).replace(',', '.'))
    return None


def etapas_termicas(datos):
    """Las etapas que calientan y las que enfrían, con la temperatura que declaran."""
    calientes, frias = [], []
    for etapa in datos['etapas']:
        texto = f"{etapa['nombre']} {etapa.get('parametro') or ''}"
        fila = {
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'parametro': etapa.get('parametro') or '',
            'limite': etapa.get('limite') or '',
            'temperatura': temperatura_de(etapa),
            'equipo': etapa.get('equipo') or '',
        }
        if ETAPAS_CALIENTES.search(texto):
            calientes.append(fila)
        elif ETAPAS_FRIAS.search(texto):
            frias.append(fila)
    return calientes, frias


def masa_de(datos, densidad=DENSIDAD):
    """Masa de la corrida; los volúmenes usan la densidad declarada."""
    cantidad = _num(datos['cantidad_base']) * _num(datos['factor'])
    unidad = (datos.get('unidad_base') or '').strip().lower()
    if unidad.startswith('l') or 'litro' in unidad:
        return cantidad * _num(densidad)
    return cantidad


def balance_de_energia(
    datos, *, t_inicial, t_proceso, t_final, eficiencia, potencia_kw,
    densidad=DENSIDAD, calor_especifico=CALOR_ESPECIFICO,
    calor_latente_vapor=CALOR_LATENTE_VAPOR, cop_frio=COP_FRIO,
):
    """El calor que exige llevar la corrida a su temperatura de proceso y volver a enfriarla."""
    masa = masa_de(datos, densidad)
    calor_especifico = _num(calor_especifico)
    calor_latente_vapor = _num(calor_latente_vapor)
    cop_frio = _num(cop_frio)
    eficiencia = eficiencia if Decimal('0') < eficiencia <= Decimal('1') else Decimal('0.85')
    salto_calor = max(_num(t_proceso) - _num(t_inicial), Decimal('0'))
    salto_frio = max(_num(t_proceso) - _num(t_final), Decimal('0'))
    calor_util = masa * calor_especifico * salto_calor
    calor_suministrado = calor_util / eficiencia
    frio_util = masa * calor_especifico * salto_frio
    potencia_kw = _num(potencia_kw)
    minutos = calor_suministrado / (potencia_kw * 60) if potencia_kw > 0 else None
    return {
        'masa_kg': _texto(masa, Decimal('0.1')),
        'salto_calor': _texto(salto_calor, Decimal('0.1')),
        'salto_frio': _texto(salto_frio, Decimal('0.1')),
        'calor_util_kj': _texto(calor_util, Decimal('1')),
        'calor_suministrado_kj': _texto(calor_suministrado, Decimal('1')),
        'calor_kwh': _texto(calor_suministrado / 3600, Decimal('0.01')),
        'vapor_kg': _texto(calor_suministrado / calor_latente_vapor, Decimal('0.1')) if calor_latente_vapor > 0 else '',
        'frio_kj': _texto(frio_util, Decimal('1')),
        'frio_kwh': _texto(frio_util / 3600 / cop_frio, Decimal('0.01')) if cop_frio > 0 else '',
        'minutos': _texto(minutos, Decimal('1')) if minutos is not None else '',
        'eficiencia_pct': _texto(eficiencia * 100, Decimal('1')),
        'densidad': _texto(densidad, Decimal('0.01')),
        'calor_especifico': _texto(calor_especifico, Decimal('0.01')),
        'calor_latente_vapor': _texto(calor_latente_vapor, Decimal('1')),
        'cop_frio': _texto(cop_frio, Decimal('0.1')),
    }


# ------------------------------------------------------------- balance de línea
def balance_de_linea(datos, *, corridas, jornada_min):
    """Las etapas frente al ritmo que pide la jornada: takt, cuello de botella y estaciones."""
    etapas = [
        {
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'tipo': etapa['tipo'],
            'equipo': etapa.get('equipo') or '',
            'trabajo': int(etapa['duracion_min']),
            'espera': int(etapa['espera_min']),
            'personas': int(etapa['personas']),
        }
        for etapa in datos['etapas']
    ]
    corridas = _num(corridas) if _num(corridas) > 0 else Decimal('1')
    jornada_min = _num(jornada_min)
    trabajo_total = sum(etapa['trabajo'] for etapa in etapas)
    espera_total = sum(etapa['espera'] for etapa in etapas)
    takt = (jornada_min / corridas).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    cuello = max(etapas, key=lambda etapa: etapa['trabajo'], default=None)
    ciclo = Decimal(cuello['trabajo']) if cuello else Decimal('0')
    capacidad = int(jornada_min // ciclo) if ciclo > 0 else 0
    minimo = math.ceil(Decimal(trabajo_total) / takt) if takt > 0 else 0
    # Asignación: etapas consecutivas mientras quepan en el takt; la que lo supera va sola.
    estaciones, actual = [], None
    for etapa in etapas:
        etapa['utilizacion'] = _texto(Decimal(etapa['trabajo']) / takt * 100, Decimal('1')) if takt > 0 else '0'
        if (
            actual is not None
            and Decimal(actual['tiempo'] + etapa['trabajo']) <= takt
            and Decimal(etapa['trabajo']) <= takt
        ):
            actual['etapas'].append(etapa)
            actual['tiempo'] += etapa['trabajo']
            actual['personas'] = max(actual['personas'], etapa['personas'])
        else:
            actual = {
                'numero': len(estaciones) + 1,
                'etapas': [etapa],
                'tiempo': etapa['trabajo'],
                'personas': etapa['personas'],
            }
            estaciones.append(actual)
    for estacion in estaciones:
        estacion['ocupacion'] = _texto(Decimal(estacion['tiempo']) / takt * 100, Decimal('1')) if takt > 0 else '0'
        estacion['excede'] = Decimal(estacion['tiempo']) > takt
    numero = len(estaciones)
    eficiencia = (Decimal(trabajo_total) / (numero * takt) * 100) if numero and takt > 0 else Decimal('0')
    return {
        'takt': _texto(takt, Decimal('0.1')),
        'corridas': _texto(corridas),
        'jornada_min': int(jornada_min),
        'trabajo_total': trabajo_total,
        'espera_total': espera_total,
        'cuello': cuello,
        'ciclo': int(ciclo),
        'capacidad': capacidad,
        'estaciones_minimas': minimo,
        'estaciones': estaciones,
        'numero_estaciones': numero,
        'eficiencia': _texto(min(eficiencia, Decimal('100')), Decimal('0.1')),
        'retraso': _texto(max(Decimal('100') - eficiencia, Decimal('0')), Decimal('0.1')),
        'alcanza': ciclo <= takt,
        'etapas': etapas,
        'personas_max': max((etapa['personas'] for etapa in etapas), default=0),
    }


# ------------------------------------------------------ requerimiento de materiales
def requerimiento_de_materiales(plan):
    """Un plan de corridas (receta, factor, etiqueta) frente al inventario: lo bruto, lo disponible y lo que falta."""
    insumos, salidas = OrderedDict(), OrderedDict()
    for fila in plan:
        receta, factor = fila['receta'], fila['factor']
        for item in receta.insumos_para(factor):
            consumible = item['consumible']
            acumulado = insumos.setdefault(consumible.pk, {
                'consumible': consumible, 'bruto': Decimal('0'), 'procesos': [], 'obligatorio': False,
            })
            acumulado['bruto'] += _num(item['cantidad'])
            acumulado['obligatorio'] = acumulado['obligatorio'] or item['obligatorio']
            if receta.nombre not in acumulado['procesos']:
                acumulado['procesos'].append(receta.nombre)
        for item in receta.salidas_para(factor):
            producto = item['producto']
            acumulada = salidas.setdefault(producto.pk, {
                'producto': producto, 'cantidad': Decimal('0'), 'principal': item['principal'],
            })
            acumulada['cantidad'] += _num(item['cantidad'])
            acumulada['principal'] = acumulada['principal'] or item['principal']
    filas = []
    for acumulado in insumos.values():
        consumible = acumulado['consumible']
        disponible = max(_num(consumible.stock_total) - _num(consumible.stock_seguridad), Decimal('0'))
        neto = max(acumulado['bruto'] - disponible, Decimal('0'))
        filas.append({
            'nombre': consumible.nombre,
            'unidad': consumible.unidad_medida,
            'clasificacion': consumible.get_clasificacion_display(),
            'procesos': acumulado['procesos'],
            'obligatorio': acumulado['obligatorio'],
            'bruto': _texto(acumulado['bruto']),
            'stock': _texto(consumible.stock_total),
            'seguridad': _texto(consumible.stock_seguridad),
            'disponible': _texto(disponible),
            'neto': _texto(neto),
            'cubre': neto == 0,
        })
    filas.sort(key=lambda fila: (fila['cubre'], fila['nombre'].lower()))
    return {
        'filas': filas,
        'salidas': [
            {
                'nombre': salida['producto'].nombre,
                'unidad': salida['producto'].unidad_medida,
                'tipo': salida['producto'].get_tipo_display(),
                'principal': salida['principal'],
                'cantidad': _texto(salida['cantidad']),
            }
            for salida in salidas.values()
        ],
        'faltantes': sum(1 for fila in filas if not fila['cubre']),
        'cubiertos': sum(1 for fila in filas if fila['cubre']),
        'insumos': len(filas),
        'corridas': _texto(sum((_num(fila['factor']) for fila in plan), Decimal('0'))),
    }

