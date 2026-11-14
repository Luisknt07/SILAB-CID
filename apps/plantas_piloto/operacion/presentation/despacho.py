"""Despacho de producto: a quién sale cada lote y a qué temperatura.

Una venta, una transferencia o una muestra de un producto con cadena de frío
registra su temperatura al salir y no se despacha por encima del límite de
conservación del producto (4 °C refrigerado, −18 °C congelado). Cada despacho
tiene su guía, con el lote, el cliente o destino y la temperatura: es el
registro de distribución que piden las BPM para retirar un lote si hace falta.
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Max, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.finanzas.models.ventas import Cliente
from apps.plantas_piloto.operacion.models.produccion import MovimientoProducto
from apps.directorio_unidades.models.core import Unidad

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.sesiones_erp import puede_consultar_en, sesion_de

TIPOS_CON_DESPACHO = ('venta', 'transferencia', 'muestra')


def _grados(valor):
    return format(Decimal(valor).normalize(), 'f')


def validar_cadena_de_frio(lote, tipo, temperatura):
    """El producto con cadena de frío sale con su temperatura y dentro de su límite."""
    producto = lote.producto
    if tipo not in TIPOS_CON_DESPACHO or not producto.requiere_frio:
        return
    if temperatura is None:
        raise ValidationError(
            f'{producto.nombre} requiere cadena de frío: registra su temperatura al despacho.'
        )
    limite = producto.limite_frio
    if temperatura > limite:
        raise ValidationError(
            f'{producto.nombre} sale a {_grados(temperatura)} °C, por encima de su límite de '
            f'{_grados(limite)} °C: la cadena de frío no se cumple y el lote no se despacha.'
        )


def cliente_de_la_venta(request, nombre):
    """El cliente de una venta; en una sesión, uno registrado: la práctica no amplía el maestro."""
    nombre = ' '.join((nombre or '').split())[:160]
    if not nombre:
        return None
    if sesion_de(request) is not None:
        cliente = Cliente.objects.filter(nombre__iexact=nombre).first()
        if cliente is None:
            raise ValidationError('En una sesión se elige un cliente ya registrado o se vende al consumidor final.')
        return cliente
    return Cliente.por_nombre(nombre)


def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def operar_cliente(request, unidad):
    """Los datos del cliente; es uno solo para la institución y lo corrige quien le vende."""
    registro_id = _texto(request, 'registro_id')
    if registro_id:
        objeto = get_object_or_404(Cliente.objects.select_for_update(), pk=registro_id)
        if not MovimientoProducto.objects.filter(unidad=unidad, cliente=objeto).exists():
            raise PermissionDenied('Ese cliente no le compra a esta planta.')
    else:
        objeto = Cliente()
    objeto.nombre = ' '.join(_texto(request, 'nombre', 160).split())
    if not objeto.nombre:
        raise ValidationError('Escribe el nombre del cliente.')
    if Cliente.objects.filter(nombre__iexact=objeto.nombre).exclude(pk=objeto.pk).exists():
        raise ValidationError('Ya hay un cliente con ese nombre.')
    objeto.tipo = _texto(request, 'tipo') or 'persona'
    if objeto.tipo not in dict(Cliente.TIPOS):
        raise ValidationError('Elige el tipo de cliente.')
    for campo, maximo in (('ruc', 13), ('contacto', 160), ('telefono', 40), ('email', 254), ('direccion', 240)):
        setattr(objeto, campo, _texto(request, campo, maximo))
    objeto.observaciones = _texto(request, 'observaciones', 2000)
    # Casilla del formulario: desmarcada no se envía, y el cliente deja de ofrecerse en las ventas.
    objeto.activo = request.POST.get('activo') in {'1', 'true', 'on'}
    objeto.full_clean()
    objeto.save()
    return objeto, 'Cliente registrado' if not registro_id else 'Cliente actualizado', not registro_id


def contexto_clientes(unidad, sesion=None):
    """Los clientes de la planta con lo que compraron, en la producción real o en la sesión."""
    ambito = Q(compras__unidad=unidad) & (
        Q(compras__lote__orden__sesion=sesion) if sesion is not None else Q(compras__lote__demostrativo=False)
    )
    ventas = ambito & Q(compras__tipo='venta')
    return {
        'clientes_planta': list(
            Cliente.objects.filter(ambito).distinct()
            .annotate(
                ventas=Count('compras', filter=ventas),
                monto=Sum('compras__valor_total', filter=ventas),
                ultimo_despacho=Max('compras__fecha', filter=ambito),
            )
            .order_by('-ultimo_despacho')[:30]
        ),
        'clientes_activos': list(Cliente.objects.filter(activo=True).order_by('nombre')),
        'tipos_cliente': Cliente.TIPOS,
    }


@login_required
def guia_despacho_view(request, slug, movimiento_id):
    """La guía de un despacho: qué lote salió, a quién y a qué temperatura; su PDF es la misma página."""
    unidad = get_object_or_404(Unidad, slug=slug)
    movimiento = get_object_or_404(
        MovimientoProducto.objects.select_related(
            'lote__producto', 'lote__orden__sesion', 'cliente', 'unidad_destino', 'registrado_por',
        ),
        pk=movimiento_id, unidad=unidad,
    )
    sesion = movimiento.lote.orden.sesion if movimiento.lote.orden_id else None
    permitido = (
        puede_consultar_en(request.user, unidad, sesion) if sesion is not None
        else puede_operar_modulo_unidad(request.user, unidad, 'produccion')
        or puede_operar_modulo_unidad(request.user, unidad, 'inventario')
    )
    if not permitido:
        raise PermissionDenied('Solo quien opera la producción, o participa en la sesión, ve la guía de despacho.')
    if movimiento.tipo not in TIPOS_CON_DESPACHO:
        raise Http404('Esa salida no es un despacho.')
    producto = movimiento.lote.producto
    limite = producto.limite_frio
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/guia_despacho.html', {
        'unidad': unidad,
        'movimiento': movimiento,
        'lote': movimiento.lote,
        'producto': producto,
        'limite_texto': f'{_grados(limite)} °C' if limite is not None else '',
        'temperatura_texto': (
            f'{_grados(movimiento.temperatura_despacho)} °C' if movimiento.temperatura_despacho is not None else ''
        ),
        'cumple_frio': (
            limite is None or (movimiento.temperatura_despacho is not None
                               and movimiento.temperatura_despacho <= limite)
        ),
        'generado_en': timezone.localtime(),
        'volver_url': reverse('erp_planta', args=[unidad.slug]) + '?view=produccion' + (
            f'&sesion={sesion.codigo}' if sesion is not None else ''
        ),
    })
