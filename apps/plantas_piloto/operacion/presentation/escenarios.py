"""Las variables que el aula mueve, sin tocar la receta de la planta.

``datos_de_receta`` devuelve una estructura plana y todo lo que se deriva de
ella -el balance de masa, el flujo de entradas y salidas, el cronograma- trabaja
sobre esa estructura, no sobre los modelos. Aquí se le aplican los cambios que
el estudiante escribe en el simulador y se devuelve otra estructura igual, de
modo que el escenario pasa por el mismo cálculo que la corrida real: si el
balance cambia, cambia porque cambiaron los datos, no porque exista un segundo
cálculo para el aula.

Un escenario guarda solo lo que se movió. Un rendimiento que sigue siendo el de
la receta no se guarda, así la simulación dice qué se cambió y qué se dejó como
está, y volver a la receta es borrar el ajuste.

Además de rendimientos, insumos y salidas, el escenario mueve el trabajo y la
espera de cada etapa y puede quitar etapas: «¿qué pasa si no escaldo?». El
balance, el cronograma y los diagramas se recalculan con el proceso que resulta.
"""

import copy
import re
from decimal import Decimal, InvalidOperation

from apps.plantas_piloto.operacion.presentation.procesos import _texto_cantidad, unidad_en_plural

CAMPO_RENDIMIENTO = re.compile(r'^rendimiento_(\d+)$')
CAMPO_INSUMO = re.compile(r'^insumo_(\d+)_(\d+)$')
CAMPO_SALIDA = re.compile(r'^salida_(\d+)_(\d+)$')
CAMPO_DURACION = re.compile(r'^duracion_(\d+)$')
CAMPO_ESPERA = re.compile(r'^espera_(\d+)$')
CAMPO_OMITIR = re.compile(r'^omitir_(\d+)$')
CAMPO_ESPERADO = 'rendimiento_esperado'
SIN_ETAPA = 0
# Lo que no depende del tamaño de la corrida y sobrevive a un cambio de escala.
CAMPOS_SIN_ESCALA = (CAMPO_RENDIMIENTO, CAMPO_DURACION, CAMPO_ESPERA, CAMPO_OMITIR)
MARCADO = {'1', 'on', 'true', 'si', 'sí'}


def _num(valor):
    return Decimal(str(valor if valor is not None else 0))


def _leer(texto):
    """Un número escrito a mano; si no lo es, el escenario lo ignora."""
    if texto is None:
        return None
    texto = str(texto).strip().replace(',', '.')
    if not texto:
        return None
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    return valor if valor >= 0 else None


def _insumos_de(datos, orden):
    if orden == SIN_ETAPA:
        return datos.get('insumos_sin_etapa', [])
    etapa = next((item for item in datos.get('etapas', []) if item['orden'] == orden), None)
    return etapa['insumos'] if etapa else []


def _salidas_de(datos, orden):
    if orden == SIN_ETAPA:
        return datos.get('salidas_sin_etapa', [])
    etapa = next((item for item in datos.get('etapas', []) if item['orden'] == orden), None)
    return etapa['salidas'] if etapa else []


def variables_del_escenario(datos):
    """Todo lo que se puede mover, agrupado como se presenta en el formulario.

    Cada variable dice de dónde sale su valor y qué cambia al moverla, porque un
    campo sin explicación es un número que el estudiante cambia sin saber qué
    mide.
    """
    grupos = [{
        'clave': 'corrida',
        'titulo': 'La corrida completa',
        'detalle': 'El tamaño del lote y lo que la receta promete entregar.',
        'campos': [{
            'campo': CAMPO_ESPERADO,
            'etiqueta': f"Rendimiento esperado ({datos['unidad_producto']})",
            'valor': datos['rendimiento_esperado'],
            'receta': datos['rendimiento_esperado'],
            'ayuda': 'Lo que la receta promete por corrida. La diferencia con el balance dice si el proceso cumple.',
            'paso': '0.001',
        }],
    }]
    for etapa in datos.get('etapas', []):
        campos = [{
            'campo': f"rendimiento_{etapa['orden']}",
            'etiqueta': 'Rendimiento de la etapa (%)',
            'valor': etapa['rendimiento_pct'],
            'receta': etapa['rendimiento_pct'],
            'ayuda': 'Cuánta masa continúa. Bajarlo es simular una etapa que pierde más: la merma sube.',
            'paso': '0.01',
            'maximo': '100',
        }, {
            'campo': f"duracion_{etapa['orden']}",
            'etiqueta': 'Trabajo de la etapa (min)',
            'valor': etapa['duracion_min'],
            'receta': etapa['duracion_min'],
            'ayuda': 'Tiempo de trabajo de las personas y el equipo. Cambia la duración y la capacidad de la línea.',
            'paso': '1',
        }, {
            'campo': f"espera_{etapa['orden']}",
            'etiqueta': 'Espera de la etapa (min)',
            'valor': etapa['espera_min'],
            'receta': etapa['espera_min'],
            'ayuda': 'Reposo, fermentación o frío: el producto espera sin trabajo. Alarga la corrida.',
            'paso': '1',
        }, {
            'campo': f"omitir_{etapa['orden']}",
            'tipo': 'casilla',
            'etiqueta': 'Quitar esta etapa del escenario',
            'valor': '',
            'receta': '',
            'ayuda': 'El proceso sigue sin ella: sus insumos, salidas, tiempos y controles desaparecen del cálculo.',
        }]
        for indice, insumo in enumerate(etapa.get('insumos', [])):
            campos.append({
                'campo': f"insumo_{etapa['orden']}_{indice}",
                'etiqueta': f"{insumo['nombre']} ({insumo['unidad']})",
                'valor': insumo['cantidad'],
                'receta': insumo['cantidad'],
                'ayuda': (
                    'Se incorpora al producto: sube la masa que continúa.'
                    if insumo.get('forma_parte', 'si') == 'si'
                    else 'Auxiliar del proceso: se consume pero no queda en el producto.'
                ),
                'paso': '0.001',
            })
        for indice, salida in enumerate(etapa.get('salidas', [])):
            campos.append({
                'campo': f"salida_{etapa['orden']}_{indice}",
                'etiqueta': f"{salida['nombre']} ({salida['unidad']})",
                'valor': salida['cantidad'],
                'receta': salida['cantidad'],
                'ayuda': (
                    'Salida externa al flujo: se registra sin descontarla de la masa del producto.'
                    if salida.get('externa_al_flujo') else
                    'Subproducto o residuo declarado. Lo que la etapa pierde y no se declara aquí queda como merma.'
                ),
                'paso': '0.001',
            })
        grupos.append({
            'clave': f"etapa-{etapa['orden']}",
            'titulo': f"{etapa['orden']}. {etapa['nombre']}",
            'detalle': etapa['equipo'] or 'Sin equipo declarado',
            'campos': campos,
        })
    sueltos = []
    for indice, insumo in enumerate(datos.get('insumos_sin_etapa', [])):
        sueltos.append({
            'campo': f"insumo_{SIN_ETAPA}_{indice}",
            'etiqueta': f"{insumo['nombre']} ({insumo['unidad']})",
            'valor': insumo['cantidad'],
            'receta': insumo['cantidad'],
            'ayuda': 'La receta lo pide sin decir en qué etapa: cuenta como consumo, no entra al flujo.',
            'paso': '0.001',
        })
    if sueltos:
        grupos.append({
            'clave': 'sin-etapa',
            'titulo': 'Insumos sin etapa declarada',
            'detalle': 'Se consumen en la corrida, pero la receta no dice dónde.',
            'campos': sueltos,
        })
    return grupos


def leer_escenario(fuente, datos):
    """Los ajustes que trae el formulario, solo los que existen y se movieron."""
    ajustes = {}
    esperado = _leer(fuente.get(CAMPO_ESPERADO))
    if esperado is not None and esperado != _num(datos['rendimiento_esperado']):
        ajustes[CAMPO_ESPERADO] = _texto_cantidad(esperado)
    for clave in fuente:
        coincide = CAMPO_RENDIMIENTO.match(clave)
        if coincide:
            orden = int(coincide.group(1))
            etapa = next((item for item in datos.get('etapas', []) if item['orden'] == orden), None)
            valor = _leer(fuente.get(clave))
            if etapa is None or valor is None or valor > 100:
                continue
            if valor != _num(etapa['rendimiento_pct']):
                ajustes[clave] = _texto_cantidad(valor)
            continue
        tiempo = CAMPO_DURACION.match(clave) or CAMPO_ESPERA.match(clave)
        if tiempo:
            orden = int(tiempo.group(1))
            etapa = next((item for item in datos.get('etapas', []) if item['orden'] == orden), None)
            valor = _leer(fuente.get(clave))
            if etapa is None or valor is None:
                continue
            actual = etapa['duracion_min'] if clave.startswith('duracion_') else etapa['espera_min']
            if int(valor) != int(actual):
                ajustes[clave] = str(int(valor))
            continue
        quitar = CAMPO_OMITIR.match(clave)
        if quitar:
            orden = int(quitar.group(1))
            existe = any(item['orden'] == orden for item in datos.get('etapas', []))
            if existe and str(fuente.get(clave) or '').strip().lower() in MARCADO:
                ajustes[clave] = '1'
            continue
        for patron, lector in ((CAMPO_INSUMO, _insumos_de), (CAMPO_SALIDA, _salidas_de)):
            coincide = patron.match(clave)
            if not coincide:
                continue
            orden, indice = int(coincide.group(1)), int(coincide.group(2))
            lista = lector(datos, orden)
            valor = _leer(fuente.get(clave))
            if valor is None or indice >= len(lista):
                continue
            if valor != _num(lista[indice]['cantidad']):
                ajustes[clave] = _texto_cantidad(valor)
    return ajustes


def escenario_del_formulario(fuente, datos, origen_actual):
    """Los ajustes del formulario, descartando los que se escribieron para otra cosa.

    Un insumo se escribe en su cantidad, y esa cantidad depende del tamaño de la
    corrida: los 6 kg de sal de una corrida de 100 litros no son los mismos de
    una de 200. Cuando cambia la escala, el formulario que el navegador reenvía
    trae los números viejos, así que de él solo sobreviven los rendimientos, que
    son porcentajes, los tiempos y las etapas quitadas, que no dependen del
    tamaño. Y si lo que cambió fue el proceso,
    no sobrevive nada: las etapas de una receta no son las de otra.
    """
    ajustes = leer_escenario(fuente, datos)
    origen = str(fuente.get('origen') or '')
    if not origen or origen == origen_actual:
        return ajustes
    if origen.split(':')[0] != origen_actual.split(':')[0]:
        return {}
    return {
        clave: valor for clave, valor in ajustes.items()
        if any(patron.match(clave) for patron in CAMPOS_SIN_ESCALA)
    }


def aplicar_escenario(datos, ajustes):
    """La misma estructura de la receta, con los valores del escenario puestos."""
    if not ajustes:
        return datos
    escenario = copy.deepcopy(datos)
    if CAMPO_ESPERADO in ajustes:
        escenario['rendimiento_esperado'] = _texto_cantidad(ajustes[CAMPO_ESPERADO])
    quitadas = set()
    for clave, valor in ajustes.items():
        coincide = CAMPO_RENDIMIENTO.match(clave)
        if coincide:
            orden = int(coincide.group(1))
            for etapa in escenario.get('etapas', []):
                if etapa['orden'] == orden:
                    etapa['rendimiento_pct'] = _texto_cantidad(valor)
            continue
        tiempo = CAMPO_DURACION.match(clave) or CAMPO_ESPERA.match(clave)
        if tiempo:
            orden = int(tiempo.group(1))
            campo = 'duracion_min' if clave.startswith('duracion_') else 'espera_min'
            for etapa in escenario.get('etapas', []):
                if etapa['orden'] == orden:
                    etapa[campo] = int(Decimal(str(valor)))
            continue
        quitar = CAMPO_OMITIR.match(clave)
        if quitar:
            quitadas.add(int(quitar.group(1)))
            continue
        for patron, lector in ((CAMPO_INSUMO, _insumos_de), (CAMPO_SALIDA, _salidas_de)):
            coincide = patron.match(clave)
            if not coincide:
                continue
            orden, indice = int(coincide.group(1)), int(coincide.group(2))
            lista = lector(escenario, orden)
            if indice < len(lista):
                lista[indice]['cantidad'] = _texto_cantidad(valor)
    if quitadas:
        escenario['etapas'] = [etapa for etapa in escenario.get('etapas', []) if etapa['orden'] not in quitadas]
    return escenario


def cambios_del_escenario(datos, ajustes):
    """Qué se movió y desde qué valor: la lista que encabeza la simulación."""
    cambios = []
    if CAMPO_ESPERADO in ajustes:
        cambios.append({
            'variable': 'Rendimiento esperado',
            'de': f"{datos['rendimiento_esperado']} {datos['unidad_producto']}",
            'a': f"{_texto_cantidad(ajustes[CAMPO_ESPERADO])} {datos['unidad_producto']}",
        })
    for clave, valor in ajustes.items():
        coincide = CAMPO_RENDIMIENTO.match(clave)
        if coincide:
            orden = int(coincide.group(1))
            etapa = next((item for item in datos.get('etapas', []) if item['orden'] == orden), None)
            if etapa:
                cambios.append({
                    'variable': f"{etapa['orden']}. {etapa['nombre']} · rendimiento",
                    'de': f"{etapa['rendimiento_pct']} %",
                    'a': f"{_texto_cantidad(valor)} %",
                })
            continue
        tiempo = CAMPO_DURACION.match(clave) or CAMPO_ESPERA.match(clave)
        quitar = CAMPO_OMITIR.match(clave)
        if tiempo or quitar:
            orden = int((tiempo or quitar).group(1))
            etapa = next((item for item in datos.get('etapas', []) if item['orden'] == orden), None)
            if etapa is None:
                continue
            if quitar:
                cambios.append({'variable': f"{etapa['orden']}. {etapa['nombre']}", 'de': 'en el proceso', 'a': 'quitada'})
            elif clave.startswith('duracion_'):
                cambios.append({
                    'variable': f"{etapa['orden']}. {etapa['nombre']} · trabajo",
                    'de': f"{etapa['duracion_min']} min", 'a': f'{valor} min',
                })
            else:
                cambios.append({
                    'variable': f"{etapa['orden']}. {etapa['nombre']} · espera",
                    'de': f"{etapa['espera_min']} min", 'a': f'{valor} min',
                })
            continue
        for patron, lector in ((CAMPO_INSUMO, _insumos_de), (CAMPO_SALIDA, _salidas_de)):
            coincide = patron.match(clave)
            if not coincide:
                continue
            orden, indice = int(coincide.group(1)), int(coincide.group(2))
            lista = lector(datos, orden)
            if indice >= len(lista):
                continue
            item = lista[indice]
            etiqueta = f"{orden}. {item['nombre']}" if orden else item['nombre']
            cambios.append({
                'variable': etiqueta,
                'de': f"{item['cantidad']} {unidad_en_plural(item['unidad'], item['cantidad'])}",
                'a': f"{_texto_cantidad(valor)} {unidad_en_plural(item['unidad'], valor)}",
            })
    return sorted(cambios, key=lambda cambio: cambio['variable'])


def valores_del_formulario(datos, ajustes):
    """Cada campo con el valor que debe mostrar y si viene de la receta o del escenario."""
    grupos = variables_del_escenario(datos)
    for grupo in grupos:
        for campo in grupo['campos']:
            ajustado = ajustes.get(campo['campo'])
            campo['movido'] = ajustado is not None
            if ajustado is not None:
                campo['valor'] = ajustado if campo.get('tipo') == 'casilla' else _texto_cantidad(ajustado)
        # El grupo que tiene algo movido se abre solo: el estudiante ve dónde
        # tocó sin abrir etapa por etapa.
        grupo['movido'] = any(campo['movido'] for campo in grupo['campos'])
    return grupos
