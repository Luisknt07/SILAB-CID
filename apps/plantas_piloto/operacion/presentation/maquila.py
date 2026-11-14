"""Servicios y maquila por proceso: producción por encargo, controlada.

Un servicio ligado a un proceso se pide en lotes (corridas base): sus
materiales por lote son los insumos del proceso y la cotización sale de esa
lista escalada, la tarifa y las horas, como cualquier servicio. La materia
prima puede traerla el cliente (maquila) o ponerla la planta. Al aprobarse
nace la orden de producción de origen «maquila»; la planta recibe la materia
prima del cliente como lote propio con su control de recepción, cierra la
corrida con sus lotes y su control de calidad, y entrega con acta y
certificado. El cliente sigue el avance desde su comprobante y «Mis reservas».
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.recursos.models.consumibles import EntradaInventario, LoteConsumible
from apps.laboratorios.operacion.models.fablab import FablabServiceConsumible
from apps.plantas_piloto.operacion.models.produccion import MovimientoProducto, OrdenProduccion
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.procesos import unidad_en_plural

TRES = Decimal('0.001')
ETAPAS = [
    ('solicitada', 'Solicitud recibida'),
    ('planificada', 'Corrida planificada'),
    ('en_proceso', 'En producción'),
    ('terminada', 'Producida, en control de calidad'),
    ('lista', 'Lista para entrega'),
    ('entregada', 'Entregada'),
    ('cancelada', 'Cancelada'),
]
NOMBRES_ETAPA = dict(ETAPAS)


def _texto(valor):
    return format(Decimal(str(valor)).quantize(TRES, rounding=ROUND_HALF_UP).normalize(), 'f')


def _decimal(texto, nombre):
    try:
        valor = Decimal(str(texto or '').strip().replace(',', '.'))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError(f'{nombre} no es válida.') from error
    if valor <= 0:
        raise ValidationError(f'{nombre} debe ser mayor que cero.')
    return valor.quantize(TRES, rounding=ROUND_HALF_UP)


def _si(valor):
    return str(valor or '').strip().lower() in {'on', 'true', '1', 'si', 'sí'}


# ------------------------------------------------------ el servicio por proceso
def sincronizar_insumos_del_proceso(servicio):
    """Los materiales por lote del servicio son los insumos del proceso al que se liga."""
    receta = servicio.receta
    if receta is None:
        return 0
    vigentes = []
    for insumo in receta.insumos.select_related('consumible').order_by('pk'):
        del_cliente = insumo.forma_parte == 'base' and servicio.materia_prima_cliente
        FablabServiceConsumible.objects.update_or_create(
            service=servicio,
            consumible=insumo.consumible,
            defaults={
                'cantidad_sugerida': insumo.cantidad,
                'obligatorio': bool(insumo.obligatorio) and not del_cliente,
                'notas': (
                    'Materia prima de la corrida base: la trae el cliente o la pone la planta.'
                    if del_cliente else 'Cantidad del proceso por lote (corrida base).'
                ),
            },
        )
        vigentes.append(insumo.consumible_id)
    servicio.service_consumibles.exclude(consumible_id__in=vigentes).delete()
    return len(vigentes)


def servicio_de_proceso(servicios):
    """El servicio ligado a un proceso entre los pedidos, si lo hay."""
    return next((servicio for servicio in servicios if servicio.receta_id), None)


def ids_materia_prima_base(servicio):
    if not servicio.receta_id:
        return set()
    return set(servicio.receta.insumos.filter(forma_parte='base').values_list('consumible_id', flat=True))


def trae_materia_prima_el_cliente(servicio, seleccion):
    """El cliente trae la materia prima cuando el servicio lo admite y no se la pidió a la planta."""
    if not servicio.materia_prima_cliente or seleccion is None:
        return False
    base = ids_materia_prima_base(servicio)
    return bool(base) and not any(consumible_id in seleccion for consumible_id in base)


def insumos_base(reserva):
    if not reserva.receta_id:
        return []
    return list(
        reserva.receta.insumos.filter(forma_parte='base')
        .select_related('consumible', 'etapa', 'etapa__equipo')
        .order_by('pk')
    )


def equipo_que_recibe(reserva, insumo):
    """El equipo donde entra la materia prima: el de su etapa o el de la primera etapa del proceso."""
    etapa = insumo.etapa if insumo.etapa_id else reserva.receta.etapas.select_related('equipo').order_by('orden').first()
    if etapa is None or not etapa.equipo_id:
        return None
    return (
        UnidadEquipo.objects.filter(equipo_id=etapa.equipo_id, activa=True)
        .filter(Q(laboratorio=reserva.laboratorio) | Q(laboratorios=reserva.laboratorio))
        .order_by('codigo_unidad')
        .first()
    )


# ------------------------------------------------------------- el expediente
def expediente_maquila(reserva):
    """Lo que el cliente y la planta ven del encargo: orden, materia prima, lotes y entregas."""
    if reserva.tipo_solicitud != 'servicio' or not reserva.receta_id:
        return None
    receta = reserva.receta
    factor = Decimal(reserva.factor_proceso or 1)
    orden = reserva.ordenes_produccion.select_related('receta', 'producto').order_by('-pk').first()
    lotes = list(orden.lotes.select_related('producto').order_by('pk')) if orden else []
    entregas = list(
        MovimientoProducto.objects.filter(lote__in=lotes, tipo='venta')
        .select_related('lote', 'lote__producto', 'registrado_por')
        .order_by('pk')
    ) if lotes else []
    material = list(
        LoteConsumible.objects.filter(reserva=reserva, material_cliente=True)
        .select_related('consumible')
        .order_by('pk')
    )
    principales = [lote for lote in lotes if lote.producto_id == receta.producto_id]
    aprobados = [lote for lote in principales if lote.control_calidad == 'aprobado']
    entregado = sum((movimiento.cantidad for movimiento in entregas), Decimal('0'))
    esperado = Decimal(receta.rendimiento_esperado) * factor
    unidad_producto = receta.producto.unidad_medida
    if reserva.estado in ('cancelada', 'rechazada', 'vencida') or (orden is not None and orden.estado == 'cancelada'):
        etapa = 'cancelada'
    elif orden is None:
        etapa = 'solicitada'
    elif orden.estado == 'planificada':
        etapa = 'planificada'
    elif orden.estado == 'en_proceso':
        etapa = 'en_proceso'
    elif entregado > 0 and all(lote.cantidad_disponible <= 0 for lote in aprobados):
        etapa = 'entregada'
    elif aprobados:
        etapa = 'lista'
    else:
        etapa = 'terminada'
    orden_abierta = orden is not None and orden.estado in OrdenProduccion.ESTADOS_ABIERTOS
    pasos = [
        {'nombre': 'Solicitud recibida', 'hecho': True},
        {'nombre': 'Aprobada y planificada', 'hecho': orden is not None and etapa != 'cancelada'},
        (
            {'nombre': 'Materia prima del cliente recibida', 'hecho': bool(material)}
            if reserva.materia_prima_cliente else None
        ),
        {'nombre': 'Producida', 'hecho': etapa in ('terminada', 'lista', 'entregada')},
        {'nombre': 'Control de calidad aprobado', 'hecho': etapa in ('lista', 'entregada')},
        {'nombre': 'Entregada con acta', 'hecho': etapa == 'entregada'},
    ]
    return {
        'reserva': reserva,
        'receta': receta,
        'factor': _texto(factor),
        'escala': f'{_texto(Decimal(receta.cantidad_base) * factor)} {receta.unidad_base}',
        'producto': receta.producto.nombre,
        'unidad_producto': unidad_producto,
        'producto_esperado': f'{_texto(esperado)} {unidad_en_plural(unidad_producto, esperado)}',
        'entregado_texto': f'{_texto(entregado)} {unidad_en_plural(unidad_producto, entregado)}',
        'materia_prima_cliente': reserva.materia_prima_cliente,
        'material': material,
        'material_recibido': _texto(sum((lote.cantidad_inicial for lote in material), Decimal('0'))),
        'orden': orden,
        'orden_abierta': orden_abierta,
        'lotes': lotes,
        'aprobados': aprobados,
        'entregables': [
            lote for lote in aprobados if lote.estado == 'disponible' and lote.cantidad_disponible > 0
        ],
        'entregas': entregas,
        'entregado': _texto(entregado),
        'etapa': etapa,
        'etapa_display': NOMBRES_ETAPA[etapa],
        'pasos': [paso for paso in pasos if paso],
        'pendiente_recepcion': bool(reserva.materia_prima_cliente and not material and orden_abierta),
    }


# ------------------------------------------------- la materia prima del cliente
def recibir_material_cliente(reserva, datos, usuario):
    """La leche del cliente entra como lote propio, con su control de recepción, para la corrida del encargo."""
    expediente = expediente_maquila(reserva)
    if expediente is None or not reserva.materia_prima_cliente:
        raise ValidationError('Este encargo no trae materia prima del cliente.')
    if not expediente['orden_abierta']:
        raise ValidationError('La materia prima se recibe con la corrida aprobada y todavía abierta.')
    bases = {str(insumo.consumible_id): insumo for insumo in insumos_base(reserva)}
    elegido = str(datos.get('consumible_id') or '').strip()
    insumo = bases.get(elegido) or (next(iter(bases.values())) if len(bases) == 1 else None)
    if insumo is None:
        raise ValidationError('Elige la materia prima que entra.')
    cantidad = _decimal(datos.get('cantidad'), 'La cantidad recibida')
    control = str(datos.get('control_recepcion') or '').strip()[:600]
    if not control:
        raise ValidationError('Anota el control de recepción (prueba de alcohol, acidez, temperatura…).')
    if not _si(datos.get('aprobado')):
        raise ValidationError(
            'Registra la recepción solo cuando la materia prima pasa el control; si no pasa, '
            'devuélvela y anótalo en las observaciones de la orden.'
        )
    documento = str(datos.get('documento') or '').strip()[:120]
    orden = expediente['orden']
    consumible = insumo.consumible
    # Entra directamente al equipo que la recibe (el tanque de recepción del proceso), lista para la corrida.
    unidad_equipo = equipo_que_recibe(reserva, insumo)
    if unidad_equipo is None:
        raise ValidationError(
            'El proceso no dice en qué equipo entra la materia prima: define el equipo de su etapa en la ficha del proceso.'
        )
    codigo_reserva = reserva.codigo_reserva or str(reserva.pk)
    with transaction.atomic():
        numero = LoteConsumible.objects.filter(consumible=consumible, reserva=reserva).count() + 1
        lote = LoteConsumible.objects.create(
            consumible=consumible,
            codigo=f'CLI-{codigo_reserva}-{numero:02d}'[:100],
            cantidad_inicial=cantidad,
            cantidad_actual=Decimal('0'),
            estado='en_uso',
            equipo_en_uso=unidad_equipo,
            bodega='Materia prima del cliente',
            fecha_ingreso=timezone.localdate(),
            fecha_apertura=timezone.localdate(),
            costo_unitario=Decimal('0'),
            documento_recepcion=documento,
            observaciones=(
                f'Materia prima del cliente ({reserva.nombre_solicitante or reserva.usuario}). '
                f'Control de recepción: {control}'
            ),
            creado_por=usuario,
            material_cliente=True,
            reserva=reserva,
        )
        EntradaInventario.objects.create(
            consumible=consumible,
            unidad=reserva.laboratorio,
            tipo='ingreso',
            motivo='recepcion',
            cantidad=cantidad,
            lote_inventario=lote,
            reserva=reserva,
            costo_unitario=Decimal('0'),
            responsable_costo='usuario',
            usuario=usuario,
            nota=f'Materia prima del cliente para {orden.codigo}: {control}',
            referencia=orden.codigo[:100],
            clave_idempotencia=f'reserva:{reserva.pk}:material-cliente:{lote.pk}',
        )
    return lote


# --------------------------------------------------------------- la entrega
def entregar_lote(reserva, datos, usuario):
    """La entrega del producto al cliente: un movimiento del lote aprobado, con acta; se cobró como servicio."""
    expediente = expediente_maquila(reserva)
    if expediente is None:
        raise ValidationError('La reserva no es un encargo por proceso.')
    elegido = str(datos.get('lote_id') or '').strip()
    lote = next((item for item in expediente['entregables'] if str(item.pk) == elegido), None)
    if lote is None:
        raise ValidationError('Elige un lote aprobado por calidad y con producto disponible.')
    cantidad = _decimal(datos.get('cantidad') or lote.cantidad_disponible, 'La cantidad entregada')
    if cantidad > lote.cantidad_disponible:
        raise ValidationError(
            f'El lote {lote.codigo} tiene {_texto(lote.cantidad_disponible)} {lote.producto.unidad_medida} disponibles.'
        )
    codigo_reserva = reserva.codigo_reserva or str(reserva.pk)
    referencia = str(datos.get('referencia') or '').strip()[:120] or f'Acta de entrega {codigo_reserva}'
    cliente = reserva.nombre_solicitante or reserva.usuario.get_full_name() or reserva.usuario.username
    destino = f'{cliente} · {reserva.institucion}' if reserva.institucion else cliente
    movimiento = MovimientoProducto(
        unidad=reserva.laboratorio,
        lote=lote,
        tipo='venta',
        cantidad=cantidad,
        destino=destino[:200],
        precio_unitario=Decimal('0'),
        referencia=referencia,
        motivo=f'Entrega del encargo {codigo_reserva}: el producto es del cliente y se cobró como servicio.',
        registrado_por=usuario,
    )
    movimiento.full_clean()
    movimiento.save()
    return movimiento


# ---------------------------------------------------------------- las vistas
def _reserva_de_encargo(unidad, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related('receta', 'receta__producto', 'usuario', 'laboratorio'),
        pk=reserva_id,
        laboratorio=unidad,
        tipo_solicitud='servicio',
    )
    if not reserva.receta_id:
        raise Http404('La reserva no es un encargo por proceso')
    return reserva


@login_required
@require_http_methods(['GET', 'POST'])
def maquila_view(request, slug, reserva_id):
    """El expediente del encargo para la planta: materia prima del cliente, corrida, lotes y entrega."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, 'produccion'):
        raise PermissionDenied('Solo quien opera la producción atiende un encargo.')
    reserva = _reserva_de_encargo(unidad, reserva_id)
    error = ''
    if request.method == 'POST':
        accion = (request.POST.get('accion') or '').strip()
        try:
            with transaction.atomic():
                if accion == 'recepcion':
                    recibir_material_cliente(reserva, request.POST, request.user)
                elif accion == 'entrega':
                    entregar_lote(reserva, request.POST, request.user)
                else:
                    raise ValidationError('Acción desconocida.')
        except ValidationError as excepcion:
            error = ' '.join(excepcion.messages)
        else:
            return redirect(f"{reverse('maquila_expediente', args=[unidad.slug, reserva.pk])}?hecho={accion}")
    expediente = expediente_maquila(reserva)
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/maquila.html', {
        'unidad': unidad,
        'reserva': reserva,
        'expediente': expediente,
        'bases': insumos_base(reserva),
        'error': error,
        'hecho': (request.GET.get('hecho') or '').strip(),
        'generado_en': timezone.localtime(),
        'volver_url': reverse('erp_planta', args=[unidad.slug]) + '?view=produccion',
        'acta_url': reverse('acta_entrega_maquila', args=[unidad.slug, reserva.pk]),
    })


@login_required
def acta_entrega_view(request, slug, reserva_id):
    """El acta de entrega con el certificado de calidad: para la planta y para el cliente."""
    unidad = get_object_or_404(Unidad, slug=slug)
    reserva = _reserva_de_encargo(unidad, reserva_id)
    es_titular = reserva.usuario_id == request.user.pk
    if not es_titular and not any(
        puede_operar_modulo_unidad(request.user, unidad, modulo) for modulo in ('produccion', 'reservas')
    ):
        raise PermissionDenied('Solo el cliente y la planta ven el acta de entrega.')
    expediente = expediente_maquila(reserva)
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/acta_entrega.html', {
        'unidad': unidad,
        'reserva': reserva,
        'expediente': expediente,
        'generado_en': timezone.localtime(),
        'volver_url': (
            reverse('comprobante_reserva', args=[reserva.pk]) if es_titular
            else reverse('maquila_expediente', args=[unidad.slug, reserva.pk])
        ),
    })
