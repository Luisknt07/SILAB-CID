"""Compras de la planta: órdenes de compra y evaluación de proveedores.

Los pedidos en borrador de un mismo proveedor salen en una sola orden de compra
con número, que se imprime y se envía; sus pedidos pasan a «enviado» y cuentan
como existencia en camino. Anular la orden devuelve sus pedidos al borrador,
mientras nada se haya recibido.

La evaluación del proveedor sale de lo que ya registra la planta: entregas
recibidas a tiempo y controles de recepción conformes. Es el criterio que piden
las BPM y la norma ISO 9001 (8.4) para mantener la lista de proveedores
aprobados, sin una planilla aparte.
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.plantas_piloto.operacion.models.calidad import ControlCalidad
from apps.plantas_piloto.operacion.models.planificacion import EntregaPedido, PedidoAbastecimiento
from apps.finanzas.models.compras import OrdenCompra, Proveedor
from apps.directorio_unidades.models.core import Unidad

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.sesiones_erp import exigir_misma_sesion, puede_consultar_en, sesion_de

# Por encima de estos umbrales el proveedor es confiable; por debajo del segundo, crítico.
A_TIEMPO_CONFIABLE = 90
A_TIEMPO_OBSERVACION = 75


def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def emitir_ordenes_de_compra(unidad, usuario, condiciones='', sesion=None):
    """Una orden por proveedor con sus pedidos en borrador; sin proveedor, el pedido espera."""
    pendientes = list(
        PedidoAbastecimiento.objects.select_for_update()
        .filter(unidad=unidad, sesion=sesion, estado='borrador', orden_compra__isnull=True)
        .order_by('proveedor_id', 'fecha_entrega_prevista', 'pk')
    )
    por_proveedor = {}
    for pedido in pendientes:
        if pedido.proveedor_id:
            por_proveedor.setdefault(pedido.proveedor_id, []).append(pedido)
    ordenes = []
    for proveedor_id, pedidos in por_proveedor.items():
        orden = OrdenCompra.objects.create(
            unidad=unidad, proveedor_id=proveedor_id, condiciones=condiciones, emitida_por=usuario,
            sesion=sesion,
        )
        PedidoAbastecimiento.objects.filter(pk__in=[pedido.pk for pedido in pedidos]).update(
            orden_compra=orden, estado='enviado', actualizado_en=timezone.now(),
        )
        ordenes.append(orden)
    sin_proveedor = sum(1 for pedido in pendientes if not pedido.proveedor_id)
    return ordenes, sin_proveedor


def confirmar_orden(orden):
    if orden.estado != 'emitida':
        raise ValidationError('Solo se confirma una orden emitida.')
    orden.estado = 'confirmada'
    orden.save(update_fields=['estado', 'actualizado_en'])
    orden.pedidos.filter(estado='enviado').update(estado='confirmado', actualizado_en=timezone.now())


def anular_orden(orden):
    if orden.estado in ('anulada', 'recibida'):
        raise ValidationError('La orden ya está cerrada.')
    if EntregaPedido.objects.filter(pedido__orden_compra=orden, recibida=True).exists():
        raise ValidationError('La orden ya tiene entregas recibidas: no se anula.')
    # Sus pedidos vuelven al borrador para corregirse o salir en otra orden.
    orden.pedidos.exclude(estado='cancelado').update(
        orden_compra=None, estado='borrador', actualizado_en=timezone.now(),
    )
    orden.estado = 'anulada'
    orden.save(update_fields=['estado', 'actualizado_en'])


def operar_orden_compra(request, unidad):
    # El panel envía «guardar»: sin orden elegida emite, con una elegida la confirma.
    accion = _texto(request, 'accion')
    if accion == 'guardar':
        accion = 'confirmar' if _texto(request, 'registro_id') else 'emitir'
    if accion == 'emitir':
        ordenes, sin_proveedor = emitir_ordenes_de_compra(
            unidad, request.user, _texto(request, 'condiciones', 2000), sesion_de(request),
        )
        if not ordenes:
            raise ValidationError(
                'No hay pedidos en borrador con proveedor: asígnale un proveedor a cada pedido antes de emitir.'
            )
        # La consola completa el mensaje con «correctamente»: lo emitido va al final.
        emitidas = f'{len(ordenes)} órdenes de compra emitidas' if len(ordenes) > 1 else 'Orden de compra emitida'
        if sin_proveedor:
            pendientes = (f'{sin_proveedor} pedidos sin proveedor siguen' if sin_proveedor > 1
                          else '1 pedido sin proveedor sigue')
            emitidas = f'{pendientes} en borrador; {emitidas[0].lower()}{emitidas[1:]}'
        return ordenes[0], emitidas, True
    orden = get_object_or_404(OrdenCompra.objects.select_for_update(), pk=_texto(request, 'registro_id') or None,
                              unidad=unidad)
    exigir_misma_sesion(orden.sesion_id, request)
    if accion == 'confirmar':
        confirmar_orden(orden)
        return orden, 'Orden de compra confirmada', False
    if accion == 'anular':
        anular_orden(orden)
        return orden, 'Orden de compra anulada', False
    raise ValidationError('Elige qué hacer con la orden de compra.')


def operar_proveedor(request, unidad):
    """Los datos del proveedor; es uno solo para la institución y lo corrige quien le compra."""
    registro_id = _texto(request, 'registro_id')
    if registro_id:
        objeto = get_object_or_404(Proveedor.objects.select_for_update(), pk=registro_id)
        if not Proveedor.objects.filter(
            Q(pedidos__unidad=unidad) | Q(ordenes_compra__unidad=unidad), pk=objeto.pk,
        ).exists():
            raise PermissionDenied('Ese proveedor no abastece a esta planta.')
    else:
        objeto = Proveedor()
    objeto.nombre = ' '.join(_texto(request, 'nombre', 160).split())
    if not objeto.nombre:
        raise ValidationError('Escribe el nombre del proveedor.')
    repetido = Proveedor.objects.filter(nombre__iexact=objeto.nombre).exclude(pk=objeto.pk).exists()
    if repetido:
        raise ValidationError('Ya hay un proveedor con ese nombre.')
    for campo, maximo in (('ruc', 13), ('contacto', 160), ('telefono', 40), ('email', 254),
                          ('direccion', 240), ('rubro', 240)):
        setattr(objeto, campo, _texto(request, campo, maximo))
    objeto.observaciones = _texto(request, 'observaciones', 2000)
    # Casilla del formulario: desmarcada no se envía, y el proveedor deja de ofrecerse en los pedidos.
    objeto.activo = request.POST.get('activo') in {'1', 'true', 'on'}
    objeto.full_clean()
    objeto.save()
    return objeto, 'Proveedor registrado' if not registro_id else 'Proveedor actualizado', not registro_id


def _calificacion(a_tiempo_pct, rechazos, recibidas):
    if not recibidas:
        return 'sin_historial', 'Sin historial'
    if a_tiempo_pct >= A_TIEMPO_CONFIABLE and not rechazos:
        return 'confiable', 'Confiable'
    if a_tiempo_pct >= A_TIEMPO_OBSERVACION and rechazos <= 1:
        return 'observacion', 'En observación'
    return 'critico', 'Crítico'


def evaluacion_de_proveedores(unidad, sesion=None):
    """Cada proveedor que abasteció a la planta, con su puntualidad y sus recepciones."""
    proveedores = list(
        Proveedor.objects.filter(pedidos__unidad=unidad, pedidos__sesion=sesion).distinct().order_by('nombre')
    )
    filas = []
    for proveedor in proveedores:
        pedidos = PedidoAbastecimiento.objects.filter(
            unidad=unidad, sesion=sesion, proveedor=proveedor,
        ).exclude(estado='cancelado')
        recibidas = list(
            EntregaPedido.objects.filter(pedido__in=pedidos, recibida=True).select_related('entrada')
        )
        # La puntualidad se mide sobre las entregas con fecha de recepción; sin ella no hay dato.
        fechadas = [entrega for entrega in recibidas if entrega.recibida_en]
        a_tiempo = sum(
            1 for entrega in fechadas if timezone.localtime(entrega.recibida_en).date() <= entrega.fecha
        )
        lotes = [entrega.entrada.lote_inventario_id for entrega in recibidas if entrega.entrada_id]
        controles = ControlCalidad.objects.filter(lote_consumible_id__in=[lote for lote in lotes if lote])
        rechazos = controles.filter(resultado='no_conforme').count()
        a_tiempo_pct = round(a_tiempo * 100 / len(fechadas)) if fechadas else 0
        clave, nombre = _calificacion(a_tiempo_pct, rechazos, len(fechadas))
        filas.append({
            'proveedor': proveedor,
            'pedidos': pedidos.count(),
            'comprado': sum((pedido.costo_total for pedido in pedidos), Decimal('0')),
            'recibidas': len(recibidas),
            'a_tiempo': a_tiempo,
            'a_tiempo_pct': a_tiempo_pct,
            'controles': controles.count(),
            'rechazos': rechazos,
            'calificacion': clave,
            'calificacion_nombre': nombre,
        })
    return filas


def _numero(valor, lugares='0.001'):
    return format(Decimal(valor).quantize(Decimal(lugares)).normalize(), 'f')


@login_required
def orden_compra_view(request, slug, orden_id):
    """La orden de compra en una hoja, lista para enviarse al proveedor; su PDF es la misma página."""
    unidad = get_object_or_404(Unidad, slug=slug)
    orden = get_object_or_404(OrdenCompra.objects.select_related('proveedor', 'emitida_por', 'sesion'), pk=orden_id,
                              unidad=unidad)
    permitido = (
        puede_consultar_en(request.user, unidad, orden.sesion) if orden.sesion_id
        else puede_operar_modulo_unidad(request.user, unidad, 'produccion')
        or puede_operar_modulo_unidad(request.user, unidad, 'inventario')
    )
    if not permitido:
        raise PermissionDenied('Solo quien opera el abastecimiento, o participa en la sesión, ve la orden de compra.')
    pedidos = list(
        orden.pedidos.exclude(estado='cancelado').select_related('consumible', 'plan')
        .prefetch_related('entregas').order_by('pk')
    )
    lineas = []
    for pedido in pedidos:
        lineas.append({
            'pedido': pedido,
            'cantidad': _numero(pedido.cantidad),
            'costo_unitario': f'${_numero(pedido.costo_unitario, "0.0001")}' if pedido.costo_unitario is not None else '',
            'subtotal': f'${pedido.costo_total}',
            'entregas': [
                {'fecha': entrega.fecha, 'cantidad': _numero(entrega.cantidad), 'recibida': entrega.recibida}
                for entrega in pedido.entregas.all()
            ],
        })
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/orden_compra.html', {
        'unidad': unidad,
        'orden_compra': orden,
        'lineas': lineas,
        'total_texto': f'${sum((pedido.costo_total for pedido in pedidos), Decimal("0.00"))}',
        'generado_en': timezone.localtime(),
        'volver_url': reverse('erp_planta', args=[unidad.slug]) + '?view=planificacion' + (
            f'&sesion={orden.sesion.codigo}' if orden.sesion_id else ''
        ),
    })


def contexto_compras(unidad, sesion=None):
    """Lo que la pestaña de planificación muestra de las compras."""
    return {
        'ordenes_compra': list(
            OrdenCompra.objects.filter(unidad=unidad, sesion=sesion).select_related('proveedor')
            .prefetch_related('pedidos__consumible')[:20]
        ),
        'evaluacion_proveedores': evaluacion_de_proveedores(unidad, sesion),
        'proveedores_activos': list(Proveedor.objects.filter(activo=True).order_by('nombre')),
        'pedidos_por_emitir': PedidoAbastecimiento.objects.filter(
            unidad=unidad, sesion=sesion, estado='borrador', orden_compra__isnull=True, proveedor__isnull=False,
        ).count(),
    }
