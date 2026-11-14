"""Costo de una corrida: insumos, energía de los equipos y mano de obra.

El costo estándar sale de la receta escalada: cada insumo por su precio, la
potencia de cada equipo por el tiempo que trabaja en su etapa y las
horas-persona de cada etapa. Como en el plan maestro, el tiempo crece con las
corridas base. El costo real de una orden cerrada toma lo que de verdad se
consumió, al costo del lote del que salió, y lo reparte sobre lo obtenido.

Sin precio o sin tarifa, esa parte queda «sin dato» en lugar de contarse en
cero: un costo incompleto no se presenta como si fuera total.
"""
from decimal import ROUND_HALF_UP, Decimal

from apps.recursos.models.consumibles import EntradaInventario

CENTAVO = Decimal('0.01')
SESENTA = Decimal('60')
KW_POR_HP = Decimal('0.7457')


def _dinero(valor):
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _energia_y_mano_de_obra(receta, factor, configuracion):
    etapas = sorted(receta.etapas.all(), key=lambda etapa: etapa.orden)
    kwh = Decimal('0')
    horas_persona = Decimal('0')
    equipos_sin_potencia = []
    for etapa in etapas:
        # El equipo sigue encendido en la espera (fermentación, maduración); las personas no.
        minutos = Decimal(etapa.duracion_min + etapa.espera_min) * factor
        if etapa.equipo_id:
            potencia = etapa.equipo.potencia_kw
            if potencia is None and etapa.equipo.potencia_hp is not None:
                potencia = etapa.equipo.potencia_hp * KW_POR_HP
            if potencia is not None:
                kwh += potencia * minutos / SESENTA
            elif etapa.equipo.nombre not in equipos_sin_potencia:
                equipos_sin_potencia.append(etapa.equipo.nombre)
        horas_persona += Decimal(etapa.personas * etapa.duracion_min) * factor / SESENTA
    # El monto sale de la cifra que se muestra, para que cada fila cuadre a la vista.
    kwh = kwh.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    horas_persona = horas_persona.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    tarifa_kwh = getattr(configuracion, 'tarifa_energia_kwh', None)
    costo_hora = getattr(configuracion, 'costo_hora_persona', None)
    return {
        'sin_etapas': not etapas,
        'kwh': kwh,
        'tarifa_kwh': tarifa_kwh,
        'energia': _dinero(kwh * tarifa_kwh) if etapas and tarifa_kwh is not None else None,
        'equipos_sin_potencia': equipos_sin_potencia,
        'horas_persona': horas_persona,
        'costo_hora': costo_hora,
        'mano_de_obra': _dinero(horas_persona * costo_hora) if etapas and costo_hora is not None else None,
    }


def _fila(nombre, cantidad, unidad, precio):
    return {
        'nombre': nombre, 'cantidad': cantidad, 'unidad': unidad, 'precio': precio,
        'subtotal': _dinero(cantidad * precio) if precio is not None else None,
    }


def _numero(valor, lugares='0.001'):
    return format(Decimal(valor).quantize(Decimal(lugares), rounding=ROUND_HALF_UP).normalize(), 'f')


def _monto(valor, sin_dato):
    return f'${valor}' if valor is not None else sin_dato


def _tabla(costo):
    """Las filas y las advertencias que la página y el PDF muestran igual."""
    filas = [
        [fila['nombre'],
         f"{_numero(fila['cantidad'])} {fila['unidad']} × ${_numero(fila['precio'], '0.0001')}"
         if fila['precio'] is not None else f"{_numero(fila['cantidad'])} {fila['unidad']}",
         _monto(fila['subtotal'], 'sin precio')]
        for fila in costo['insumos']
    ]
    filas.append([
        'Energía eléctrica de los equipos',
        f"{costo['kwh']} kWh" + (f" × ${costo['tarifa_kwh']}/kWh" if costo['tarifa_kwh'] is not None else ''),
        _monto(costo['energia'], 'sin tarifa'),
    ])
    filas.append([
        'Mano de obra',
        f"{costo['horas_persona']} h-persona" + (f" × ${costo['costo_hora']}/h" if costo['costo_hora'] is not None else ''),
        _monto(costo['mano_de_obra'], 'sin tarifa'),
    ])
    filas.append([
        'Total de la corrida' if costo['completo'] else 'Total parcial de la corrida',
        f"{_numero(costo['cantidad_producto'])} {costo['unidad_producto']} de producto",
        costo['total_texto'],
    ])
    if costo['unitario'] is not None:
        filas.append([f"Costo por {costo['unidad_producto']}", '', costo['unitario_texto']])
    avisos = []
    if costo['sin_etapas']:
        avisos.append('La receta no declara etapas: sin ellas no hay energía ni mano de obra que contar.')
    if costo['sin_precio']:
        avisos.append(f"Sin precio en el inventario: {', '.join(costo['sin_precio'])}.")
    if costo['equipos_sin_potencia']:
        avisos.append(
            f"Equipos sin potencia registrada, que no suman energía: {', '.join(costo['equipos_sin_potencia'])}."
        )
    if costo['tarifa_kwh'] is None or costo['costo_hora'] is None:
        avisos.append('La tarifa de energía y el costo de la hora-persona se fijan en los permisos operativos de la planta.')
    # Los avisos van en la tabla: el PDF solo dibuja tablas, y así dice lo mismo que la página.
    filas.extend(['Nota', aviso, ''] for aviso in avisos)
    return filas, avisos


def _resumen(insumos, otros, cantidad_producto, unidad_producto):
    sin_precio = [fila['nombre'] for fila in insumos if fila['precio'] is None]
    insumos_total = _dinero(sum((fila['subtotal'] or 0 for fila in insumos), Decimal('0')))
    total = insumos_total + (otros['energia'] or 0) + (otros['mano_de_obra'] or 0)
    costo = {
        'insumos': insumos,
        'insumos_total': insumos_total,
        'sin_precio': sin_precio,
        **otros,
        'total': _dinero(total),
        'completo': not sin_precio and otros['energia'] is not None and otros['mano_de_obra'] is not None,
        'cantidad_producto': cantidad_producto,
        'unidad_producto': unidad_producto,
        'unitario': (total / cantidad_producto).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        if cantidad_producto else None,
    }
    # En texto, para que la consola, la ficha y el PDF escriban la misma cifra.
    costo['total_texto'] = f"${costo['total']}"
    costo['unitario_texto'] = f"${_numero(costo['unitario'], '0.0001')}" if costo['unitario'] is not None else ''
    costo['filas'], costo['avisos'] = _tabla(costo)
    return costo


def costo_estandar(receta, configuracion, factor=1):
    """Lo que cuesta la corrida según la receta: la referencia para planificar y fijar precios."""
    factor = Decimal(str(factor))
    insumos = [
        _fila(linea.consumible.nombre, linea.cantidad * factor, linea.consumible.unidad_medida,
              linea.consumible.precio_unitario)
        for linea in sorted(receta.insumos.all(), key=lambda linea: linea.pk)
    ]
    return _resumen(
        insumos, _energia_y_mano_de_obra(receta, factor, configuracion),
        receta.rendimiento_esperado * factor, receta.producto.unidad_medida,
    )


def costos_de_entradas(ordenes):
    """El costo unitario de cada salida de inventario de las órdenes cerradas, en una consulta."""
    ids = {
        consumo['entrada_id']
        for orden in ordenes if orden.estado == 'terminada'
        for consumo in (orden.detalle_cierre or {}).get('consumos', []) if consumo.get('entrada_id')
    }
    return dict(EntradaInventario.objects.filter(pk__in=ids).values_list('pk', 'costo_unitario')) if ids else {}


def costo_real(orden, configuracion, costos_entrada=None):
    """El costo de una orden cerrada con lo que se consumió y lo que se obtuvo; abierta, no tiene."""
    if orden.estado != 'terminada':
        return None
    if costos_entrada is None:
        costos_entrada = costos_de_entradas([orden])
    precios = {linea.consumible_id: linea.consumible.precio_unitario for linea in orden.receta.insumos.all()}
    insumos = []
    for consumo in (orden.detalle_cierre or {}).get('consumos', []):
        # El costo del lote consumido; lo simulado de una corrida demostrativa, al precio de referencia.
        precio = costos_entrada.get(consumo.get('entrada_id'))
        if precio is None:
            precio = precios.get(consumo.get('consumible_id'))
        insumos.append(_fila(
            consumo.get('consumible', ''), Decimal(str(consumo.get('consumido') or 0)),
            consumo.get('unidad', ''), precio,
        ))
    return _resumen(
        insumos, _energia_y_mano_de_obra(orden.receta, Decimal(str(orden.factor)), configuracion),
        orden.cantidad_obtenida or Decimal('0'), orden.producto.unidad_medida,
    )
