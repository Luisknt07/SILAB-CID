"""Planificación: qué producir, qué pedir y cuándo.

El plan maestro reúne las corridas del período: las que ya están comprometidas
(un encargo aceptado, una práctica programada) y las que la unidad decide
hacer para reponer existencias. Sobre esas corridas corren tres cuentas:

* la **explosión de materiales**, que suma lo que las recetas piden día a día,
  descuenta lo que hay en bodega y lo que ya viene en camino, y deja lo que
  falta con la fecha en que hay que pedirlo (la fecha de necesidad menos el
  plazo de reposición del insumo);
* la **carga de la capacidad**, que compara las horas de proceso de cada día
  con las horas de jornada de la unidad y enciende su semáforo;
* la **orden de producción** de cada línea firme, que es donde el plan deja de
  ser un papel y entra en la agenda.

Un pedido de abastecimiento lleva sus entregas porque la leche cruda no llega
toda de una vez: llega el día que se procesa. Cada entrega recibida entra al
inventario como su lote, con su costo.
"""

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.plantas_piloto.domain.planificacion import (
    PeriodoDemanda,
    decimal_tres,
    equivalente_base,
    periodos_demanda,
    promedio_movil,
    ventanas_historicas,
)

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.plantas_piloto.operacion.models.planificacion import EntregaPedido, LineaPlanMaestro, LineaPlanVentas, PedidoAbastecimiento, PlanMaestro, PlanVentas
from apps.plantas_piloto.operacion.models.erp import ExistenciaSesion
from apps.finanzas.models.compras import OrdenCompra, Proveedor
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, Receta, MovimientoProducto
from apps.reservas.models.reservas import Reserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.finanzas.presentation.compras import contexto_compras, operar_orden_compra, operar_proveedor

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.plantas_piloto.operacion.presentation.sesiones_erp import exigir_misma_sesion, puede_consultar_en, sesion_de
from apps.reservas.presentation.proceso import seleccion_por_proceso

# Los estados de una reserva que todavía obligan a la unidad a producir.
ESTADOS_COMPROMETIDOS = ('pendiente', 'confirmada', 'en_proceso')


def _decimal(valor):
    return Decimal(valor).quantize(Decimal('0.001'))


# ------------------------------------------------------------- la demanda
def demanda_comprometida(unidad, desde, hasta):
    """Encargos y prácticas por proceso del período que todavía no están en el plan."""
    reservas = (
        Reserva.objects.filter(
            laboratorio=unidad,
            receta__isnull=False,
            fecha__gte=desde,
            fecha__lte=hasta,
            estado__in=ESTADOS_COMPROMETIDOS,
        )
        .select_related('receta', 'receta__producto', 'usuario')
        .order_by('fecha', 'pk')
    )
    planificadas = set(
        LineaPlanMaestro.objects.filter(
            plan__unidad=unidad, reserva__isnull=False,
        ).values_list('reserva_id', flat=True)
    )
    pendientes = []
    for reserva in reservas:
        if reserva.pk in planificadas:
            continue
        pendientes.append({
            'reserva': reserva,
            'receta': reserva.receta,
            'factor': Decimal(reserva.factor_proceso or 1),
            'fecha': reserva.fecha,
            'origen': 'maquila' if reserva.tipo_solicitud == 'servicio' else 'docencia',
        })
    return pendientes


def proponer_lineas(plan):
    """Lleva al plan la demanda ya comprometida que todavía no estaba en él."""
    if not plan.abierto:
        raise ValidationError('Un plan cerrado ya no admite nuevas corridas.')
    creadas = []
    for item in demanda_comprometida(plan.unidad, plan.desde, plan.hasta):
        linea = LineaPlanMaestro(
            plan=plan,
            receta=item['receta'],
            fecha=item['fecha'],
            factor=item['factor'],
            origen=item['origen'],
            reserva=item['reserva'],
            observaciones=f"{item['reserva'].codigo_reserva or item['reserva'].pk}",
        )
        linea.full_clean(exclude=['producto', 'cantidad'])
        linea.save()
        creadas.append(linea)
    return creadas


# ------------------------------------ previsión, ventas y plan agregado
def _ventas_del_periodo(unidad, producto_id, periodo):
    total = MovimientoProducto.objects.reales().filter(
        unidad=unidad,
        lote__producto_id=producto_id,
        tipo='venta',
        fecha__date__gte=periodo.inicio,
        fecha__date__lte=periodo.fin,
    ).aggregate(total=Sum('cantidad'))['total']
    return decimal_tres(total)


def _componentes_comprometidos(unidad, producto_id, periodo):
    compromisos = Decimal('0')
    docencia = Decimal('0')
    reservas = (
        Reserva.objects.filter(
            laboratorio=unidad,
            receta__producto_id=producto_id,
            fecha__gte=periodo.inicio,
            fecha__lte=periodo.fin,
            estado__in=ESTADOS_COMPROMETIDOS,
        )
        .select_related('receta')
        .order_by('pk')
    )
    for reserva in reservas:
        cantidad = decimal_tres(
            Decimal(reserva.receta.rendimiento_esperado) * Decimal(reserva.factor_proceso or 1)
        )
        if reserva.tipo_solicitud == 'servicio':
            compromisos += cantidad
        else:
            docencia += cantidad
    return decimal_tres(compromisos), decimal_tres(docencia)


def _componentes_linea_ventas(plan, receta, periodo):
    ventanas = ventanas_historicas(periodo.inicio, plan.periodicidad)
    historicos = [_ventas_del_periodo(plan.unidad, receta.producto_id, ventana) for ventana in ventanas]
    historico_promedio = promedio_movil(historicos)
    compromisos, docencia = _componentes_comprometidos(plan.unidad, receta.producto_id, periodo)
    return historico_promedio, compromisos, docencia


def generar_demanda_estimada(plan):
    """Calcula una previsión transparente y conserva los ajustes del coordinador."""
    if plan.estado != 'borrador':
        raise ValidationError('Solo un plan de ventas en borrador recalcula su demanda.')
    recetas = (
        Receta.objects.filter(
            unidad=plan.unidad,
            activa=True,
            producto__activo=True,
            producto__tipo='terminado',
            producto__precio_venta__gt=0,
        )
        .select_related('producto', 'producto__familia')
        .order_by('producto_id', 'pk')
    )
    # Un producto conserva una sola fuente técnica para convertir su demanda en
    # corridas. Si existen alternativas, la coordinación puede cambiarla en la línea.
    recetas_por_producto = {}
    for receta in recetas:
        recetas_por_producto.setdefault(receta.producto_id, receta)
    creadas = actualizadas = 0
    for periodo in periodos_demanda(plan.desde, plan.hasta, plan.periodicidad):
        for receta in recetas_por_producto.values():
            historico, compromisos, docencia = _componentes_linea_ventas(plan, receta, periodo)
            linea, creada = LineaPlanVentas.objects.get_or_create(
                plan=plan,
                producto=receta.producto,
                periodo_inicio=periodo.inicio,
                defaults={
                    'receta': receta,
                    'periodo_fin': periodo.fin,
                    'historico_promedio': historico,
                    'pronostico': historico if plan.metodo == 'promedio_movil_3' else Decimal('0'),
                    'compromisos': compromisos,
                    'docencia': docencia,
                },
            )
            if creada:
                creadas += 1
                continue
            linea.periodo_fin = periodo.fin
            linea.historico_promedio = historico
            linea.compromisos = compromisos
            linea.docencia = docencia
            if plan.metodo == 'promedio_movil_3':
                linea.pronostico = historico
            linea.full_clean(exclude=['cantidad_planificada'])
            linea.save()
            actualizadas += 1
    return creadas, actualizadas


def resumen_plan_agregado(plan):
    """Consolida demanda por familia y unidad base sin copiar recetas ni inventario."""
    grupos = {}
    lineas = plan.lineas.select_related('producto__familia', 'receta').order_by(
        'periodo_inicio', 'producto__familia__orden', 'producto__nombre'
    )
    for linea in lineas:
        familia = linea.producto.familia
        clave = (
            linea.periodo_inicio,
            linea.periodo_fin,
            familia.pk if familia else None,
            linea.receta.unidad_base,
        )
        grupo = grupos.setdefault(clave, {
            'periodo_inicio': linea.periodo_inicio,
            'periodo_fin': linea.periodo_fin,
            'familia': familia,
            'familia_nombre': familia.nombre if familia else 'Sin familia',
            'unidad_base': linea.receta.unidad_base,
            'equivalente_base': Decimal('0'),
            'valor_estimado': Decimal('0'),
            'productos': [],
        })
        grupo['equivalente_base'] += equivalente_base(
            linea.cantidad_planificada,
            linea.receta.rendimiento_esperado,
            linea.receta.cantidad_base,
        )
        grupo['valor_estimado'] += linea.valor_estimado
        grupo['productos'].append(linea)
    resultado = []
    for grupo in grupos.values():
        grupo['equivalente_base'] = decimal_tres(grupo['equivalente_base'])
        grupo['valor_estimado'] = grupo['valor_estimado'].quantize(Decimal('0.01'))
        resultado.append(grupo)
    return resultado


def incorporar_plan_ventas(plan, usuario):
    """Convierte demanda abierta en corridas y trae aparte los compromisos reales."""
    if plan.estado != 'aprobado':
        raise ValidationError('Aprueba el plan de ventas antes de llevarlo al plan maestro.')
    if not plan.plan_maestro_id:
        raise ValidationError('Vincula un plan maestro que cubra el horizonte de ventas.')
    maestro = PlanMaestro.objects.select_for_update().get(pk=plan.plan_maestro_id, unidad=plan.unidad)
    if maestro.estado != 'borrador':
        raise ValidationError('La demanda se incorpora antes de firmar el plan maestro.')
    creadas = actualizadas = retiradas = 0
    for linea in plan.lineas.select_for_update().select_related('receta', 'producto'):
        cantidad = linea.demanda_no_comprometida
        maestra = LineaPlanMaestro.objects.select_for_update().filter(linea_ventas=linea).first()
        if cantidad <= 0:
            if maestra and not maestra.orden_id:
                maestra.delete()
                retiradas += 1
            continue
        factor = decimal_tres(cantidad / Decimal(linea.receta.rendimiento_esperado))
        fecha = max(maestro.desde, linea.periodo_inicio)
        if maestra is None:
            maestra = LineaPlanMaestro(
                plan=maestro,
                linea_ventas=linea,
                receta=linea.receta,
                fecha=fecha,
                factor=factor,
                origen='demanda',
                observaciones=f'Demanda abierta de {plan.codigo}.',
            )
            creada = True
        else:
            if maestra.orden_id:
                continue
            maestra.receta = linea.receta
            maestra.fecha = fecha
            maestra.factor = factor
            maestra.origen = 'demanda'
            maestra.observaciones = f'Demanda abierta de {plan.codigo}.'
            creada = False
        maestra.full_clean(exclude=['producto', 'cantidad'])
        maestra.save()
        if creada:
            creadas += 1
        else:
            actualizadas += 1
    comprometidas = len(proponer_lineas(maestro))
    return {
        'creadas': creadas,
        'actualizadas': actualizadas,
        'retiradas': retiradas,
        'comprometidas': comprometidas,
        'usuario': usuario,
    }


# --------------------------------------------- la explosión de materiales
def _necesidades(plan):
    """Cuánto de cada insumo piden las recetas del plan, día por día."""
    necesidad = {}
    for linea in plan.lineas.select_related('receta').order_by('fecha', 'pk'):
        for item in linea.receta.insumos_para(linea.factor):
            clave = (item['consumible'].pk, linea.fecha)
            actual = necesidad.setdefault(clave, {'consumible': item['consumible'], 'cantidad': Decimal('0')})
            actual['cantidad'] += Decimal(item['cantidad'])
    return necesidad


def _en_camino(unidad, consumibles, sesion=None):
    """Las entregas comprometidas con los proveedores y todavía no recibidas, en la misma sesión."""
    llegadas = {}
    entregas = (
        EntregaPedido.objects.filter(
            pedido__unidad=unidad,
            pedido__sesion=sesion,
            pedido__consumible_id__in=consumibles,
            pedido__estado__in=PedidoAbastecimiento.ESTADOS_EN_CAMINO,
            recibida=False,
        )
        .select_related('pedido')
    )
    for entrega in entregas:
        clave = (entrega.pedido.consumible_id, entrega.fecha)
        llegadas[clave] = llegadas.get(clave, Decimal('0')) + Decimal(entrega.cantidad)
    return llegadas


def explosion_de_materiales(plan):
    """Lo que falta comprar para que el plan se pueda hacer, y cuándo pedirlo.

    Camina el calendario por insumo: parte del saldo en bodega, suma lo que ya
    viene en camino y resta lo que cada día pide el plan. Cuando el saldo se
    va a negativo, ese hueco es lo que falta ese día; la fecha de pedido sale
    de restarle el plazo de reposición del insumo.
    """
    necesidad = _necesidades(plan)
    if not necesidad:
        return []
    consumibles = {clave[0] for clave in necesidad}
    llegadas = _en_camino(plan.unidad, consumibles, plan.sesion)
    # En una sesión el saldo de partida es el de sus existencias, no el de la bodega real.
    existencias = (
        dict(ExistenciaSesion.objects.filter(sesion=plan.sesion, consumible_id__in=consumibles)
             .values_list('consumible_id', 'cantidad'))
        if plan.sesion_id else None
    )
    por_consumible = {}
    for (consumible_id, fecha), datos in necesidad.items():
        por_consumible.setdefault(consumible_id, {'consumible': datos['consumible'], 'fechas': {}})
        por_consumible[consumible_id]['fechas'][fecha] = datos['cantidad']
    for (consumible_id, fecha), cantidad in llegadas.items():
        if consumible_id in por_consumible:
            por_consumible[consumible_id]['fechas'].setdefault(fecha, Decimal('0'))

    resultado = []
    for consumible_id, datos in por_consumible.items():
        consumible = datos['consumible']
        saldo = Decimal((existencias.get(consumible_id, 0) if existencias is not None else consumible.stock_total) or 0)
        plazo = int(consumible.plazo_reposicion_dias or 0)
        seguridad = Decimal(consumible.stock_seguridad or 0)
        filas, falta_total = [], Decimal('0')
        for fecha in sorted(datos['fechas']):
            entra = llegadas.get((consumible_id, fecha), Decimal('0'))
            pide = datos['fechas'][fecha]
            saldo += entra
            disponible = saldo
            saldo -= pide
            falta = Decimal('0')
            # El stock de seguridad no se toca: lo que lo rompe también falta.
            if saldo < seguridad:
                falta = _decimal(seguridad - saldo)
                saldo = seguridad
                falta_total += falta
            filas.append({
                'fecha': fecha,
                'disponible': _decimal(disponible),
                'en_camino': _decimal(entra),
                'requerido': _decimal(pide),
                'falta': falta,
                'pedir_el': fecha - timedelta(days=plazo),
                'saldo': _decimal(saldo),
            })
        pendientes = [fila for fila in filas if fila['falta'] > 0]
        resultado.append({
            'consumible': consumible,
            'filas': filas,
            'requerido_total': _decimal(sum(fila['requerido'] for fila in filas)),
            'en_camino_total': _decimal(sum(fila['en_camino'] for fila in filas)),
            'falta_total': _decimal(falta_total),
            'pedir_antes_de': min((fila['pedir_el'] for fila in pendientes), default=None),
            'primera_falta': min((fila['fecha'] for fila in pendientes), default=None),
            'plazo': plazo,
        })
    resultado.sort(key=lambda item: (item['falta_total'] == 0, item['consumible'].nombre))
    return resultado


def crear_pedidos_sugeridos(plan, usuario):
    """Un pedido por insumo que falta, con una entrega el día que hace falta."""
    if not plan.abierto:
        raise ValidationError('Un plan cerrado ya no genera pedidos.')
    creados = []
    for item in explosion_de_materiales(plan):
        if item['falta_total'] <= 0:
            continue
        consumible = item['consumible']
        if PedidoAbastecimiento.objects.filter(
            plan=plan, consumible=consumible,
        ).exclude(estado='cancelado').exists():
            continue
        faltantes = [fila for fila in item['filas'] if fila['falta'] > 0]
        # Se pide lo antes posible: hoy, o el día que el plazo de reposición exige.
        fecha_pedido = min(min(fila['pedir_el'] for fila in faltantes), timezone.localdate())
        pedido = PedidoAbastecimiento(
            unidad=plan.unidad,
            sesion=plan.sesion,
            consumible=consumible,
            plan=plan,
            proveedor=Proveedor.por_nombre(consumible.proveedor_referencia),
            cantidad=item['falta_total'],
            costo_unitario=consumible.precio_unitario,
            fecha_pedido=fecha_pedido,
            fecha_entrega_prevista=max(faltantes[0]['fecha'], fecha_pedido),
            observaciones=f'Sugerido por la explosión de materiales de {plan.codigo}.',
            creado_por=usuario,
        )
        pedido.full_clean(exclude=['codigo'])
        pedido.save()
        EntregaPedido.objects.bulk_create([
            EntregaPedido(pedido=pedido, fecha=fila['fecha'], cantidad=fila['falta'])
            for fila in faltantes
        ])
        creados.append(pedido)
    return creados


# ------------------------------------------------------------ la capacidad
def horas_de_jornada(unidad):
    """Las horas de trabajo de cada día: las jornadas declaradas o el horario de atención.

    Una unidad que todavía no publicó sus jornadas igual tiene un horario de
    atención; se toma ese, de lunes a viernes, para no dejar la capacidad en
    cero y pintar de rojo un plan que cabe de sobra.
    """
    horas = {dia: Decimal('0') for dia in range(7)}
    jornadas = list(HorarioOperacionUnidad.objects.filter(unidad=unidad, activo=True))
    for jornada in jornadas:
        inicio = jornada.hora_inicio.hour * 60 + jornada.hora_inicio.minute
        fin = jornada.hora_fin.hour * 60 + jornada.hora_fin.minute
        if fin > inicio:
            horas[jornada.dia_semana] += Decimal(fin - inicio) / Decimal('60')
    if not any(valor > 0 for valor in horas.values()):
        configuracion = ConfiguracionOperativaUnidad.objects.filter(unidad=unidad).first()
        apertura = getattr(configuracion, 'hora_apertura_atencion', None)
        cierre = getattr(configuracion, 'hora_cierre_atencion', None)
        if apertura and cierre:
            minutos = (cierre.hour * 60 + cierre.minute) - (apertura.hour * 60 + apertura.minute)
            if minutos > 0:
                for dia in range(5):
                    horas[dia] = Decimal(minutos) / Decimal('60')
    return {dia: _decimal(valor) for dia, valor in horas.items()}


def carga_por_dia(plan):
    """Las horas de proceso de cada día frente a las horas de jornada."""
    jornada = horas_de_jornada(plan.unidad)
    lineas = list(plan.lineas.select_related('receta').order_by('fecha', 'pk'))
    por_fecha = {}
    for linea in lineas:
        por_fecha.setdefault(linea.fecha, []).append(linea)
    filas = []
    for fecha in plan.fechas():
        del_dia = por_fecha.get(fecha, [])
        if not del_dia and jornada[fecha.weekday()] <= 0:
            continue
        carga = _decimal(sum((linea.horas for linea in del_dia), Decimal('0')))
        disponible = jornada[fecha.weekday()]
        porcentaje = int(carga / disponible * 100) if disponible > 0 else (200 if carga > 0 else 0)
        filas.append({
            'fecha': fecha,
            'lineas': del_dia,
            'corridas': len(del_dia),
            'horas': carga,
            'disponibles': disponible,
            'porcentaje': porcentaje,
            'semaforo': 'holgado' if porcentaje <= 80 else ('ajustado' if porcentaje <= 100 else 'excedido'),
        })
    return filas


# --------------------------------------------------------- de plan a orden
def _orden_de_linea(linea, usuario):
    """La corrida del plan entra en la agenda como orden de producción propia."""
    seleccion = seleccion_por_proceso(linea.receta, linea.factor)
    etapas = list(linea.receta.etapas.select_related('espacio').order_by('orden'))
    # La corrida ocupa la línea de proceso; si la receta no la declara, su primera área.
    espacio = next((etapa.espacio for etapa in etapas if etapa.espacio_id and etapa.espacio.tipo == 'linea'), None)
    if espacio is None:
        espacio = next((etapa.espacio for etapa in etapas if etapa.espacio_id), None)
    orden = OrdenProduccion(
        unidad=linea.plan.unidad,
        sesion=linea.plan.sesion,
        receta=linea.receta,
        factor=linea.factor,
        origen='maquila' if linea.origen == 'maquila' else (
            'practica' if linea.origen == 'docencia' else 'propia'
        ),
        reserva=linea.reserva,
        fecha_inicio=linea.fecha,
        fecha_fin=linea.fecha + timedelta(days=seleccion['sesion']['dias_extra']),
        linea=espacio,
        creada_por=usuario,
        observaciones=f'Plan maestro {linea.plan.codigo}: {linea.receta.nombre}.',
    )
    orden.planificar_cantidades()
    orden.full_clean()
    orden.save()
    orden.equipos.set(UnidadEquipo.objects.filter(pk__in=[item['id'] for item in seleccion['equipos']]))
    orden.sincronizar_bloqueo(usuario)
    return orden


def generar_ordenes(plan, usuario):
    """Cada línea firme sin orden se convierte en una, con su línea bloqueada."""
    if plan.estado != 'firme':
        raise ValidationError('Solo un plan firme genera órdenes de producción.')
    creadas = []
    for linea in plan.lineas.select_related('receta', 'reserva').filter(orden__isnull=True).order_by('fecha', 'pk'):
        if linea.reserva_id and linea.reserva.ordenes_produccion.exists():
            # La práctica o el encargo ya trajo la suya al aprobarse.
            linea.orden = linea.reserva.ordenes_produccion.first()
            linea.save(update_fields=['orden'])
            continue
        linea.orden = _orden_de_linea(linea, usuario)
        linea.save(update_fields=['orden'])
        creadas.append(linea.orden)
    return creadas


# ------------------------------------------------------- recibir una entrega
def recibir_entrega(entrega, datos, usuario):
    """La entrega llega: nace su lote y el insumo entra al inventario con su costo."""
    if entrega.recibida:
        raise ValidationError('Esa entrega ya se recibió.')
    pedido = entrega.pedido
    if pedido.estado == 'cancelado':
        raise ValidationError('El pedido está cancelado.')
    try:
        cantidad = Decimal(str(datos.get('cantidad') or entrega.cantidad).replace(',', '.'))
    except InvalidOperation as error:
        raise ValidationError('La cantidad recibida debe ser un número.') from error
    if cantidad <= 0:
        raise ValidationError('La cantidad recibida debe ser mayor que cero.')
    consumible = pedido.consumible
    if pedido.sesion_id:
        # En una sesión la entrega suma a sus existencias; el inventario real no se toca.
        with transaction.atomic():
            existencia, _ = ExistenciaSesion.objects.select_for_update().get_or_create(
                sesion_id=pedido.sesion_id, consumible=consumible,
            )
            existencia.cantidad += cantidad
            existencia.save(update_fields=['cantidad'])
            entrega.cantidad = cantidad
            entrega.recibida = True
            entrega.recibida_en = timezone.now()
            entrega.observaciones = (datos.get('observaciones') or '').strip()[:240]
            entrega.save()
            pedido.actualizar_estado_por_entregas()
        return entrega
    codigo = (datos.get('lote_codigo') or '').strip()[:100] or (
        f'{consumible.codigo}-{entrega.fecha:%y%m%d}-{entrega.pk}'
    )
    vence = (datos.get('fecha_vencimiento') or '').strip()
    with transaction.atomic():
        lote = LoteConsumible(
            consumible=consumible,
            codigo=codigo,
            cantidad_inicial=cantidad,
            cantidad_actual=Decimal('0'),
            estado='bodega',
            bodega=(datos.get('bodega') or consumible.ubicacion or 'Bodega de insumos')[:120],
            fecha_ingreso=entrega.fecha,
            fecha_vencimiento=datetime.strptime(vence, '%Y-%m-%d').date() if vence else None,
            costo_unitario=pedido.costo_unitario,
            documento_recepcion=(datos.get('documento') or pedido.codigo)[:120],
            creado_por=usuario,
            observaciones=f'Entrega del pedido {pedido.codigo}.',
        )
        lote.save()
        entrada = EntradaInventario.objects.create(
            consumible=consumible,
            unidad=pedido.unidad,
            tipo='ingreso',
            motivo='recepcion',
            cantidad=cantidad,
            lote_inventario=lote,
            costo_unitario=pedido.costo_unitario,
            responsable_costo='laboratorio',
            usuario=usuario,
            referencia=pedido.codigo,
            nota=f'Entrega del {entrega.fecha:%d/%m/%Y} del pedido {pedido.codigo}.',
            clave_idempotencia=f'pedido:{pedido.pk}:entrega:{entrega.pk}',
        )
        entrega.cantidad = cantidad
        entrega.recibida = True
        entrega.recibida_en = timezone.now()
        entrega.lote_codigo = lote.codigo
        entrega.entrada = entrada
        entrega.observaciones = (datos.get('observaciones') or '').strip()[:240]
        entrega.save()
        pedido.actualizar_estado_por_entregas()
    return entrega


# ----------------------------------------------------------------- el panel
def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def _fecha(texto, nombre):
    texto = (texto or '').strip()
    if not texto:
        raise ValidationError(f'{nombre} es obligatoria.')
    try:
        return datetime.strptime(texto, '%Y-%m-%d').date()
    except ValueError as error:
        raise ValidationError(f'{nombre} no tiene un formato de fecha válido.') from error


def _cantidad(texto, nombre):
    try:
        valor = Decimal(str(texto or '').strip().replace(',', '.'))
    except InvalidOperation as error:
        raise ValidationError(f'{nombre} debe ser un número.') from error
    if valor <= 0:
        raise ValidationError(f'{nombre} debe ser mayor que cero.')
    return valor


def _cantidad_no_negativa(texto, nombre, *, predeterminado=Decimal('0')):
    texto = str(texto or '').strip()
    if not texto:
        return Decimal(predeterminado)
    try:
        valor = Decimal(texto.replace(',', '.'))
    except InvalidOperation as error:
        raise ValidationError(f'{nombre} debe ser un número.') from error
    if valor < 0:
        raise ValidationError(f'{nombre} no puede ser menor que cero.')
    return decimal_tres(valor)


def _ajuste(texto):
    texto = str(texto or '').strip()
    if not texto:
        return Decimal('0')
    try:
        return decimal_tres(Decimal(texto.replace(',', '.')))
    except InvalidOperation as error:
        raise ValidationError('El ajuste manual debe ser un número.') from error


def contexto_planificacion(unidad, permisos_operativos, configuracion, sesion=None):
    """Lo que la pestaña de planificación muestra; una unidad que no produce no la abre."""
    puede = bool(permisos_operativos.get('produccion'))
    if not configuracion.registra_produccion:
        return {'planificacion_habilitada': False, 'puede_operar_planificacion': False}
    hoy = timezone.localdate()
    planes = list(
        PlanMaestro.objects.filter(unidad=unidad, sesion=sesion)
        .prefetch_related('lineas__receta__producto', 'lineas__orden')
        .order_by('-desde', '-pk')[:12]
    )
    vigente = next((plan for plan in planes if plan.abierto and plan.hasta >= hoy), None) or (
        planes[0] if planes else None
    )
    planes_ventas = list(
        PlanVentas.objects.filter(unidad=unidad, sesion=sesion)
        .select_related('plan_maestro')
        .prefetch_related('lineas__producto__familia', 'lineas__receta')
        .order_by('-desde', '-pk')[:12]
    )
    ventas_vigente = next(
        (plan for plan in planes_ventas if vigente and plan.plan_maestro_id == vigente.pk),
        None,
    ) or next(
        (plan for plan in planes_ventas if plan.abierto and plan.hasta >= hoy),
        None,
    ) or (planes_ventas[0] if planes_ventas else None)
    detalle = {}
    if vigente is not None:
        materiales = explosion_de_materiales(vigente)
        carga = carga_por_dia(vigente)
        detalle = {
            'plan_vigente': vigente,
            'lineas_plan': list(vigente.lineas.select_related('receta__producto', 'orden', 'reserva').all()),
            'materiales_plan': materiales,
            'materiales_faltantes': [item for item in materiales if item['falta_total'] > 0],
            'carga_plan': carga,
            'dias_excedidos': [fila for fila in carga if fila['semaforo'] == 'excedido'],
            'demanda_sin_planificar': demanda_comprometida(unidad, vigente.desde, vigente.hasta),
            'plan_url': reverse('plan_maestro', args=[unidad.slug, vigente.pk]),
        }
    detalle_ventas = {}
    if ventas_vigente is not None:
        lineas_ventas = list(
            ventas_vigente.lineas.select_related('producto__familia', 'receta').order_by(
                'periodo_inicio', 'producto__nombre'
            )
        )
        agregado = resumen_plan_agregado(ventas_vigente)
        detalle_ventas = {
            'plan_ventas_vigente': ventas_vigente,
            'lineas_plan_ventas': lineas_ventas,
            'plan_agregado': agregado,
            'familias_planificadas': len({
                item['familia'].pk if item['familia'] else None for item in agregado
            }),
            'valor_plan_ventas': sum((linea.valor_estimado for linea in lineas_ventas), Decimal('0')),
        }
    pedidos = list(
        PedidoAbastecimiento.objects.filter(unidad=unidad, sesion=sesion)
        .exclude(estado='cancelado')
        .select_related('consumible', 'plan', 'proveedor', 'orden_compra')
        .prefetch_related('entregas')
        .order_by('estado', 'fecha_entrega_prevista', '-pk')[:40]
    )
    entregas_pendientes = list(
        EntregaPedido.objects.filter(
            pedido__unidad=unidad, pedido__sesion=sesion, recibida=False,
        ).exclude(pedido__estado__in=('cancelado', 'borrador'))
        .select_related('pedido__consumible')
        .order_by('fecha', 'pk')[:40]
    )
    return {
        # El personal de la planta consulta el plan; lo opera con el permiso de producción.
        'planificacion_habilitada': True,
        'puede_operar_planificacion': puede,
        'planes_maestros': planes,
        'planes_ventas': planes_ventas,
        'pedidos_abastecimiento': pedidos,
        **contexto_compras(unidad, sesion),
        'entregas_pendientes': entregas_pendientes,
        'entregas_atrasadas': [entrega for entrega in entregas_pendientes if entrega.atrasada],
        'estados_plan': PlanMaestro.ESTADOS,
        'periodicidades_plan_ventas': PlanVentas.PERIODICIDADES,
        'metodos_plan_ventas': PlanVentas.METODOS,
        'origenes_linea': LineaPlanMaestro.ORIGENES,
        'estados_pedido': PedidoAbastecimiento.ESTADOS,
        'recetas_para_plan': list(
            Receta.objects.filter(unidad=unidad, activa=True).select_related('producto').order_by('nombre')
        ),
        'recetas_para_ventas': list(
            Receta.objects.filter(
                unidad=unidad,
                activa=True,
                producto__activo=True,
                producto__tipo='terminado',
                producto__precio_venta__gt=0,
            ).select_related('producto').order_by('producto__nombre', 'nombre')
        ),
        'planes_maestros_para_ventas': [plan for plan in planes if plan.estado == 'borrador'],
        'consumibles_para_pedido': list(
            Consumible.objects.filter(unidad=unidad, activo=True).order_by('nombre')
        ),
        'hoy_planificacion': hoy,
        **detalle,
        **detalle_ventas,
    }


def seccion_planificacion(contexto):
    plan = contexto.get('plan_vigente')
    faltantes = len(contexto.get('materiales_faltantes', []))
    return {
        'clave': 'planificacion',
        'titulo': 'Planificación',
        'descripcion': 'Demanda, plan de ventas, agregado, plan maestro, materiales, capacidad y pedidos.',
        'icono': 'iconsminds-calendar-4',
        'dato': f'{len(contexto.get("lineas_plan", []))} corridas' if plan else 'Sin plan',
        'etiqueta': (f'{faltantes} insumos por pedir' if plan else 'crea el plan del período')
        + ('' if contexto['puede_operar_planificacion'] else ' · solo consulta'),
        'habilitada': contexto['planificacion_habilitada'],
    }


def operar_plan_ventas(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(PlanVentas.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id else PlanVentas(unidad=unidad, creado_por=request.user, sesion=sesion_de(request))
    )
    exigir_misma_sesion(objeto.sesion_id, request)
    horizonte_anterior = (
        (objeto.desde, objeto.hasta, objeto.periodicidad)
        if not creado else None
    )
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el plan de ventas que quieres cerrar.')
        objeto.estado = 'cerrado'
        objeto.save(update_fields=['estado', 'actualizado_en'])
        return objeto, 'Plan de ventas cerrado', False
    accion = _texto(request, 'accion_plan_ventas')
    if accion:
        if creado:
            raise ValidationError('Selecciona el plan de ventas sobre el que quieres actuar.')
        if accion == 'pronosticar':
            creadas, actualizadas = generar_demanda_estimada(objeto)
            return objeto, f'Demanda estimada: {creadas} líneas creadas y {actualizadas} actualizadas', False
        if accion == 'aprobar':
            if objeto.estado != 'borrador':
                raise ValidationError('Solo un plan de ventas en borrador se puede aprobar.')
            if not objeto.plan_maestro_id:
                raise ValidationError('Vincula el plan maestro antes de aprobar la demanda.')
            if objeto.plan_maestro.estado != 'borrador':
                raise ValidationError('El plan maestro debe seguir en borrador.')
            if not objeto.lineas.filter(cantidad_planificada__gt=0).exists():
                raise ValidationError('El plan de ventas no tiene demanda para aprobar.')
            objeto.estado = 'aprobado'
            objeto.save(update_fields=['estado', 'actualizado_en'])
            return objeto, 'Plan de ventas aprobado', False
        if accion == 'incorporar':
            resultado = incorporar_plan_ventas(objeto, request.user)
            return objeto, (
                f'Demanda incorporada: {resultado["creadas"]} corridas creadas, '
                f'{resultado["actualizadas"]} actualizadas y '
                f'{resultado["comprometidas"]} compromisos añadidos'
            ), False
        raise ValidationError('Esa acción no existe para un plan de ventas.')
    if not creado and objeto.estado != 'borrador':
        raise ValidationError('Un plan de ventas aprobado o cerrado ya no se edita.')
    objeto.nombre = _texto(request, 'nombre', 160)
    objeto.desde = _fecha(request.POST.get('desde'), 'La fecha de inicio')
    objeto.hasta = _fecha(request.POST.get('hasta'), 'La fecha de fin')
    periodicidad = _texto(request, 'periodicidad') or 'semanal'
    if periodicidad not in dict(PlanVentas.PERIODICIDADES):
        raise ValidationError('Elige una periodicidad válida.')
    objeto.periodicidad = periodicidad
    if (
        horizonte_anterior
        and horizonte_anterior != (objeto.desde, objeto.hasta, objeto.periodicidad)
        and objeto.lineas.exists()
    ):
        raise ValidationError(
            'Quita la demanda calculada antes de cambiar las fechas o la periodicidad del plan.'
        )
    metodo = _texto(request, 'metodo') or 'promedio_movil_3'
    if metodo not in dict(PlanVentas.METODOS):
        raise ValidationError('Elige un método de previsión válido.')
    objeto.metodo = metodo
    plan_maestro_id = _texto(request, 'plan_maestro_id')
    objeto.plan_maestro = (
        get_object_or_404(PlanMaestro, pk=plan_maestro_id, unidad=unidad, estado='borrador', sesion=sesion_de(request))
        if plan_maestro_id else None
    )
    objeto.observaciones = _texto(request, 'observaciones')
    objeto.full_clean(exclude=['codigo'])
    objeto.save()
    return objeto, 'Plan de ventas creado' if creado else 'Plan de ventas actualizado', creado


def operar_linea_plan_ventas(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(
            LineaPlanVentas.objects.select_for_update().select_related('plan', 'receta'),
            pk=registro_id,
            plan__unidad=unidad,
        )
        if registro_id else LineaPlanVentas()
    )
    if registro_id:
        exigir_misma_sesion(objeto.plan.sesion_id, request)
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona la demanda que quieres quitar.')
        if objeto.plan.estado != 'borrador':
            raise ValidationError('La demanda aprobada ya no se elimina.')
        maestra = LineaPlanMaestro.objects.select_for_update().filter(linea_ventas=objeto).first()
        if maestra and maestra.orden_id:
            raise ValidationError('La demanda ya tiene una orden de producción.')
        if maestra:
            maestra.delete()
        objeto.delete()
        return objeto, 'Demanda quitada del plan de ventas', False
    if creado:
        plan_id = _texto(request, 'plan_id')
        if not plan_id:
            raise ValidationError('Selecciona el plan de ventas.')
        objeto.plan = get_object_or_404(PlanVentas, pk=plan_id, unidad=unidad, sesion=sesion_de(request))
    if objeto.plan.estado != 'borrador':
        raise ValidationError('Un plan de ventas aprobado o cerrado ya no se edita.')
    receta_id = _texto(request, 'receta_id')
    if not receta_id:
        raise ValidationError('Selecciona el proceso que producirá la demanda.')
    objeto.receta = get_object_or_404(
        Receta,
        pk=receta_id,
        unidad=unidad,
        activa=True,
        producto__activo=True,
        producto__tipo='terminado',
        producto__precio_venta__gt=0,
    )
    objeto.producto = objeto.receta.producto
    objeto.periodo_inicio = _fecha(request.POST.get('periodo_inicio'), 'El inicio del período')
    objeto.periodo_fin = _fecha(request.POST.get('periodo_fin'), 'El fin del período')
    periodo = PeriodoDemanda(objeto.periodo_inicio, objeto.periodo_fin)
    historico, compromisos, docencia = _componentes_linea_ventas(objeto.plan, objeto.receta, periodo)
    objeto.historico_promedio = historico
    objeto.compromisos = compromisos
    objeto.docencia = docencia
    if objeto.plan.metodo == 'promedio_movil_3':
        objeto.pronostico = historico
    else:
        objeto.pronostico = _cantidad_no_negativa(
            request.POST.get('pronostico'),
            'El pronóstico',
            predeterminado=objeto.pronostico,
        )
    objeto.ajuste_manual = _ajuste(request.POST.get('ajuste_manual'))
    objeto.observaciones = _texto(request, 'observaciones', 240)
    objeto.full_clean(exclude=['cantidad_planificada'])
    objeto.save()
    return objeto, 'Demanda añadida al plan de ventas' if creado else 'Demanda actualizada', creado


def operar_plan_maestro(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(PlanMaestro.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id else PlanMaestro(unidad=unidad, creado_por=request.user, sesion=sesion_de(request))
    )
    exigir_misma_sesion(objeto.sesion_id, request)
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el plan que quieres cerrar.')
        objeto.estado = 'cerrado'
        objeto.save(update_fields=['estado', 'actualizado_en'])
        return objeto, 'Plan maestro cerrado', False
    # Las acciones del plan viajan aparte: el cajón del panel reserva «accion» para guardar.
    accion_plan = _texto(request, 'accion_plan')
    if accion_plan:
        if creado:
            raise ValidationError('Selecciona el plan sobre el que quieres actuar.')
        if accion_plan == 'proponer':
            creadas = proponer_lineas(objeto)
            return objeto, f'Demanda llevada al plan: {len(creadas)} corridas', False
        if accion_plan == 'firmar':
            if not objeto.lineas.exists():
                raise ValidationError('Un plan sin corridas no se puede firmar.')
            objeto.estado = 'firme'
            objeto.save(update_fields=['estado', 'actualizado_en'])
            return objeto, 'Plan maestro firmado', False
        if accion_plan == 'ordenes':
            creadas = generar_ordenes(objeto, request.user)
            return objeto, f'Órdenes de producción creadas: {len(creadas)}', False
        if accion_plan == 'pedidos':
            creados = crear_pedidos_sugeridos(objeto, request.user)
            return objeto, f'Pedidos de abastecimiento sugeridos: {len(creados)}', False
        raise ValidationError('Esa acción no existe para un plan maestro.')
    objeto.nombre = _texto(request, 'nombre', 160)
    objeto.desde = _fecha(request.POST.get('desde'), 'La fecha de inicio')
    objeto.hasta = _fecha(request.POST.get('hasta'), 'La fecha de fin')
    estado = _texto(request, 'estado') or objeto.estado
    if estado not in dict(PlanMaestro.ESTADOS):
        raise ValidationError('Elige un estado válido para el plan.')
    objeto.estado = estado
    objeto.observaciones = _texto(request, 'observaciones')
    responsable_id = _texto(request, 'responsable_id')
    objeto.responsable = (
        get_object_or_404(ResponsableUnidad, pk=responsable_id, unidad=unidad, activo=True) if responsable_id else None
    )
    objeto.full_clean(exclude=['codigo'])
    objeto.save()
    return objeto, 'Plan maestro creado' if creado else 'Plan maestro actualizado', creado


def operar_linea_plan(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(LineaPlanMaestro.objects.select_for_update(), pk=registro_id, plan__unidad=unidad)
        if registro_id else LineaPlanMaestro()
    )
    if registro_id:
        exigir_misma_sesion(objeto.plan.sesion_id, request)
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona la corrida que quieres quitar del plan.')
        if objeto.orden_id:
            raise ValidationError('La corrida ya tiene su orden: cancélala desde producción.')
        objeto.delete()
        return objeto, 'Corrida quitada del plan', False
    if creado:
        plan_id = _texto(request, 'plan_id')
        if not plan_id:
            raise ValidationError('Selecciona el plan de la corrida.')
        objeto.plan = get_object_or_404(PlanMaestro, pk=plan_id, unidad=unidad, sesion=sesion_de(request))
    if not objeto.plan.abierto:
        raise ValidationError('Un plan cerrado ya no se edita.')
    receta_id = _texto(request, 'receta_id')
    if not receta_id:
        raise ValidationError('Selecciona el proceso de la corrida.')
    objeto.receta = get_object_or_404(Receta, pk=receta_id, unidad=unidad, activa=True)
    objeto.fecha = _fecha(request.POST.get('fecha'), 'La fecha de la corrida')
    objeto.factor = _cantidad(request.POST.get('factor'), 'La escala')
    origen = _texto(request, 'origen') or 'demanda'
    if origen not in dict(LineaPlanMaestro.ORIGENES):
        raise ValidationError('Elige el origen de la corrida.')
    objeto.origen = origen
    objeto.observaciones = _texto(request, 'observaciones', 240)
    objeto.full_clean(exclude=['producto', 'cantidad'])
    objeto.save()
    return objeto, 'Corrida añadida al plan' if creado else 'Corrida actualizada', creado


def operar_pedido_abastecimiento(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(PedidoAbastecimiento.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id else PedidoAbastecimiento(unidad=unidad, creado_por=request.user, sesion=sesion_de(request))
    )
    exigir_misma_sesion(objeto.sesion_id, request)
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el pedido que quieres anular.')
        if objeto.entregas.filter(recibida=True).exists():
            raise ValidationError('El pedido ya tiene entregas recibidas: no se anula.')
        objeto.estado = 'cancelado'
        objeto.save(update_fields=['estado', 'actualizado_en'])
        return objeto, 'Pedido anulado', False
    consumible_id = _texto(request, 'consumible_id')
    if not consumible_id:
        raise ValidationError('Selecciona el insumo del pedido.')
    objeto.consumible = get_object_or_404(Consumible, pk=consumible_id, unidad=unidad)
    escrito = _texto(request, 'proveedor', 160)
    if escrito and sesion_de(request) is not None:
        # En una sesión se elige entre los proveedores registrados: el maestro de la institución no crece.
        proveedor = Proveedor.objects.filter(nombre__iexact=' '.join(escrito.split())).first()
        if proveedor is None:
            raise ValidationError('En una sesión se elige un proveedor ya registrado.')
    else:
        proveedor = Proveedor.por_nombre(escrito or objeto.consumible.proveedor_referencia)
    if objeto.orden_compra_id and proveedor != objeto.proveedor:
        raise ValidationError(
            f'El pedido salió en la orden {objeto.orden_compra.codigo}: anúlala para cambiarle el proveedor.'
        )
    objeto.proveedor = proveedor
    objeto.cantidad = _cantidad(request.POST.get('cantidad'), 'La cantidad')
    costo = (request.POST.get('costo_unitario') or '').strip()
    if costo:
        try:
            objeto.costo_unitario = Decimal(costo.replace(',', '.'))
        except InvalidOperation as error:
            raise ValidationError('El costo unitario debe ser un número.') from error
    elif objeto.costo_unitario is None:
        objeto.costo_unitario = objeto.consumible.precio_unitario
    objeto.fecha_pedido = _fecha(request.POST.get('fecha_pedido'), 'La fecha del pedido')
    objeto.fecha_entrega_prevista = _fecha(request.POST.get('fecha_entrega_prevista'), 'La fecha de entrega')
    estado = _texto(request, 'estado') or objeto.estado
    if estado not in dict(PedidoAbastecimiento.ESTADOS):
        raise ValidationError('Elige un estado válido para el pedido.')
    objeto.estado = estado
    objeto.observaciones = _texto(request, 'observaciones')
    objeto.full_clean(exclude=['codigo'])
    objeto.save()
    entregas = _texto(request, 'entregas_diarias')
    if creado:
        # Sin entregas partidas, el pedido llega de una sola vez el día previsto.
        dias = int(entregas) if entregas.isdigit() and int(entregas) > 0 else 1
        por_entrega = (Decimal(objeto.cantidad) / dias).quantize(Decimal('0.001'), rounding=ROUND_CEILING)
        restante = Decimal(objeto.cantidad)
        filas = []
        for paso in range(dias):
            cantidad = min(por_entrega, restante)
            if cantidad <= 0:
                break
            restante -= cantidad
            filas.append(EntregaPedido(
                pedido=objeto,
                fecha=objeto.fecha_entrega_prevista + timedelta(days=paso),
                cantidad=cantidad,
            ))
        EntregaPedido.objects.bulk_create(filas)
    return objeto, 'Pedido registrado' if creado else 'Pedido actualizado', creado


def operar_entrega_pedido(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if not registro_id:
        raise ValidationError('Selecciona la entrega que llegó.')
    objeto = get_object_or_404(
        EntregaPedido.objects.select_for_update(), pk=registro_id, pedido__unidad=unidad,
    )
    exigir_misma_sesion(objeto.pedido.sesion_id, request)
    recibir_entrega(objeto, request.POST, request.user)
    return objeto, 'Entrega recibida', False


OPERADORES_PLANIFICACION = {
    'plan_ventas': operar_plan_ventas,
    'linea_plan_ventas': operar_linea_plan_ventas,
    'plan_maestro': operar_plan_maestro,
    'linea_plan': operar_linea_plan,
    'pedido_abastecimiento': operar_pedido_abastecimiento,
    'entrega_pedido': operar_entrega_pedido,
    'orden_compra': operar_orden_compra,
    'proveedor': operar_proveedor,
}
PERMISOS_PLANIFICACION = {clave: 'produccion' for clave in OPERADORES_PLANIFICACION}
MODELOS_PLANIFICACION = {
    'plan_ventas': PlanVentas,
    'linea_plan_ventas': LineaPlanVentas,
    'plan_maestro': PlanMaestro,
    'linea_plan': LineaPlanMaestro,
    'pedido_abastecimiento': PedidoAbastecimiento,
    'entrega_pedido': EntregaPedido,
    'orden_compra': OrdenCompra,
    'proveedor': Proveedor,
}


# ----------------------------------------------------------------- la vista
@login_required
def plan_maestro_view(request, slug, plan_id):
    """El plan del período en una hoja: qué producir, qué pedir y cuándo."""
    unidad = get_object_or_404(Unidad, slug=slug)
    plan = get_object_or_404(
        PlanMaestro.objects.select_related('sesion').prefetch_related('lineas__receta__producto', 'lineas__orden'),
        pk=plan_id, unidad=unidad,
    )
    if not puede_consultar_en(request.user, unidad, plan.sesion):
        raise PermissionDenied('Solo quien opera la producción, o participa en la sesión, ve el plan maestro.')
    materiales = explosion_de_materiales(plan)
    carga = carga_por_dia(plan)
    plan_ventas = (
        PlanVentas.objects.filter(plan_maestro=plan)
        .prefetch_related('lineas__producto__familia', 'lineas__receta')
        .first()
    )
    lineas_ventas = list(plan_ventas.lineas.all()) if plan_ventas else []
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/plan_maestro.html', {
        'unidad': unidad,
        'plan': plan,
        'lineas': list(plan.lineas.select_related('receta__producto', 'orden', 'reserva').all()),
        'carga': carga,
        'materiales': materiales,
        'faltantes': [item for item in materiales if item['falta_total'] > 0],
        'plan_ventas': plan_ventas,
        'lineas_ventas': lineas_ventas,
        'plan_agregado': resumen_plan_agregado(plan_ventas) if plan_ventas else [],
        'valor_plan_ventas': sum((linea.valor_estimado for linea in lineas_ventas), Decimal('0')),
        'pedidos': list(
            plan.pedidos.exclude(estado='cancelado').select_related('consumible').prefetch_related('entregas')
        ),
        'horas_totales': _decimal(sum((fila['horas'] for fila in carga), Decimal('0'))),
        'generado_en': timezone.localtime(),
        'volver_url': reverse('erp_planta', args=[unidad.slug]) + '?view=planificacion' + (
            f'&sesion={plan.sesion.codigo}' if plan.sesion_id else ''
        ),
    })
