"""Reconstrucción conservadora del contador de stock, sin inventar movimientos."""
from decimal import Decimal

from django.db import transaction

from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible


@transaction.atomic
def conciliar_saldo(consumible_id, *, aplicar=False):
    """Solo restaura el contador si kardex completo y lotes se corroboran.

    No representa un conteo físico ni modifica recepciones, consumos o lotes.
    El mismo orden de bloqueo que las operaciones de almacén evita leer un
    saldo intermedio mientras se registra una entrada o salida.
    """
    articulo = Consumible.objects.select_for_update().get(pk=consumible_id)
    lotes = list(LoteConsumible.objects.select_for_update().filter(consumible=articulo).order_by('pk'))
    movimientos = list(EntradaInventario.objects.filter(consumible=articulo).order_by('pk'))
    resultado = {'id': articulo.pk, 'estado': 'revision_fisica'}
    if not lotes or not movimientos or not articulo.unidad_id or any(lote.material_cliente for lote in lotes):
        return resultado
    cantidades = [articulo.stock_total, *(lote.cantidad_actual for lote in lotes),
                  *(lote.cantidad_inicial for lote in lotes), *(m.cantidad for m in movimientos),
                  *(m.saldo_resultante for m in movimientos)]
    if any(v is None or not Decimal(v).is_finite() or v < 0 for v in cantidades):
        return resultado
    total_lotes = sum((lote.cantidad_actual for lote in lotes), Decimal('0'))
    if total_lotes == articulo.stock_total:
        return {**resultado, 'estado': 'sin_diferencia'}

    def cambio(movimiento):
        return movimiento.cantidad * (1 if movimiento.tipo == 'ingreso' else -1)

    apertura = movimientos[0].saldo_resultante - cambio(movimientos[0])
    saldo = apertura
    if apertura < 0:
        return resultado
    por_lote = {lote.pk: [] for lote in lotes}
    for movimiento in movimientos:
        if movimiento.unidad_id != articulo.unidad_id or movimiento.tipo not in {'ingreso', 'salida'}:
            return resultado
        saldo += cambio(movimiento)
        if saldo != movimiento.saldo_resultante:
            return resultado
        if movimiento.lote_inventario_id:
            if movimiento.lote_inventario_id not in por_lote:
                return resultado
            por_lote[movimiento.lote_inventario_id].append(movimiento)
    inicial_sin_recepcion = Decimal('0')
    for lote in lotes:
        registros = por_lote[lote.pk]
        recepciones = [m for m in registros if m.motivo == 'recepcion']
        if recepciones:
            # Una recepción parcial o posterior no permite inferir la apertura.
            if len(recepciones) != 1 or registros[0] != recepciones[0] or recepciones[0].cantidad != lote.cantidad_inicial:
                return resultado
            base = Decimal('0')
        else:
            base = lote.cantidad_inicial
            inicial_sin_recepcion += base
        if base + sum((cambio(m) for m in registros), Decimal('0')) != lote.cantidad_actual:
            return resultado
    if inicial_sin_recepcion != apertura or total_lotes != saldo:
        return resultado
    evidencia = {'stock_total': str(saldo), 'primer_movimiento': movimientos[0].pk,
                 'ultimo_movimiento': movimientos[-1].pk, 'movimientos': len(movimientos),
                 'lotes': [lote.pk for lote in lotes], 'criterio': 'kardex_continuo_y_lotes_corroborados'}
    if aplicar:
        anterior = str(articulo.stock_total)
        articulo.stock_total = saldo
        articulo.save(update_fields=['stock_total', 'fecha_actualizacion'])
        RegistroAuditoriaUnidad.objects.create(
            unidad=articulo.unidad, accion='actualizar', entidad='Consumible', objeto_id=str(articulo.pk),
            descripcion='Mantenimiento: contador de stock reconstruido desde kardex y lotes; sin movimiento físico.',
            datos_anteriores={'stock_total': anterior}, datos_nuevos=evidencia,
        )
    return {**resultado, 'estado': 'corregido' if aplicar else 'reconstruible'}
