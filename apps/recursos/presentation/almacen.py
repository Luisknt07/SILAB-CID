"""El almacén: lo que el plan va a pedir, lo que está por vencer y lo que hay de verdad.

Tres cosas que el kardex por sí solo no responde:

* **la cobertura desde el plan**, que compara las existencias con lo que las
  corridas programadas van a consumir, no con el promedio de lo que se gastó;
* **la salida por vencimiento**, que ordena los lotes por la fecha en que
  caducan para que salga primero el que primero vence, y da de baja el que ya
  venció con su saldo completo;
* **el conteo cíclico**, que congela lo que el sistema cree tener, recoge lo
  que el bodeguero encuentra y convierte cada diferencia en un ajuste del
  kardex con su nombre y su responsable.

Y el material del cliente, que está en la bodega pero no es de la unidad: se
lista aparte para que nadie lo cuente como existencia propia.
"""

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.almacen import ConteoInventario, LineaConteo
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.plantas_piloto.operacion.models.planificacion import PlanMaestro

from apps.plantas_piloto.operacion.presentation.planificacion import explosion_de_materiales

# Los estados en que un lote todavía ocupa un lugar en el estante.
ESTADOS_VIVOS = ('bodega', 'en_uso')


def _decimal(valor):
    return Decimal(valor).quantize(Decimal('0.001'))


# ------------------------------------------------------- cobertura del plan
def plan_vigente(unidad):
    """El plan maestro que manda hoy: el abierto que aún no termina, o el último."""
    hoy = timezone.localdate()
    return (
        PlanMaestro.objects.filter(unidad=unidad, hasta__gte=hoy).exclude(estado='cerrado')
        .order_by('desde', 'pk').first()
        or PlanMaestro.objects.filter(unidad=unidad).order_by('-desde', '-pk').first()
    )


def cobertura_del_plan(unidad):
    """Lo que el plan va a consumir de cada insumo frente a lo que hay en bodega."""
    plan = plan_vigente(unidad)
    if plan is None:
        return {'plan': None, 'filas': [], 'sin_cubrir': 0}
    filas = []
    for item in explosion_de_materiales(plan):
        consumible = item['consumible']
        stock = Decimal(consumible.stock_total or 0)
        pide = item['requerido_total']
        filas.append({
            'consumible': consumible,
            'requerido': pide,
            'stock': _decimal(stock),
            'seguridad': _decimal(consumible.stock_seguridad or 0),
            'en_camino': item['en_camino_total'],
            'falta': item['falta_total'],
            'cobertura_pct': int(min(stock / pide * 100, Decimal('999'))) if pide > 0 else 100,
            'primera_falta': item['primera_falta'],
        })
    return {
        'plan': plan,
        'filas': filas,
        'sin_cubrir': sum(1 for fila in filas if fila['falta'] > 0),
    }


# ---------------------------------------------------- salida por vencimiento
def lotes_por_vencer(unidad, dias=30):
    """Los lotes con saldo ordenados por la fecha en que vencen: primero el que primero vence."""
    hoy = timezone.localdate()
    limite = hoy + timedelta(days=dias)
    lotes = (
        LoteConsumible.objects.filter(
            consumible__unidad=unidad, consumible__activo=True,
            estado__in=ESTADOS_VIVOS,
            cantidad_actual__gt=0,
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=limite,
        )
        .select_related('consumible', 'equipo_en_uso')
        .order_by('fecha_vencimiento', 'pk')
    )
    filas = []
    for lote in lotes:
        dias_restantes = (lote.fecha_vencimiento - hoy).days
        filas.append({
            'lote': lote,
            'dias': dias_restantes,
            'vencido': dias_restantes < 0,
            'del_cliente': lote.material_cliente,
        })
    return filas


def orden_de_salida(unidad):
    """Qué lote debe salir primero de cada insumo que tiene más de uno abierto.

    Primero el que antes vence; entre los que no vencen, el que antes entró.
    Los insumos con un solo lote no necesitan regla y no aparecen.
    """
    lotes = (
        LoteConsumible.objects.filter(
            consumible__unidad=unidad, consumible__activo=True, estado__in=ESTADOS_VIVOS, cantidad_actual__gt=0,
        )
        .select_related('consumible')
        .order_by('consumible__nombre', F('fecha_vencimiento').asc(nulls_last=True), 'fecha_ingreso', 'pk')
    )
    por_consumible = {}
    for lote in lotes:
        por_consumible.setdefault(lote.consumible_id, {'consumible': lote.consumible, 'lotes': []})
        por_consumible[lote.consumible_id]['lotes'].append(lote)
    return [
        {'consumible': datos['consumible'], 'primero': datos['lotes'][0], 'siguientes': datos['lotes'][1:]}
        for datos in por_consumible.values()
        if len(datos['lotes']) > 1
    ]


def dar_de_baja_por_caducidad(lote, usuario, observaciones=''):
    """El lote vencido sale entero del inventario y queda marcado como caducado."""
    if lote.estado not in ESTADOS_VIVOS:
        raise ValidationError('Ese lote ya está cerrado.')
    saldo = Decimal(lote.cantidad_actual or 0)
    if saldo <= 0:
        raise ValidationError('El lote ya no tiene saldo que dar de baja.')
    return EntradaInventario.objects.create(
        consumible=lote.consumible,
        unidad=lote.consumible.unidad,
        tipo='salida',
        motivo='caducidad',
        cantidad=saldo,
        lote_inventario=lote,
        responsable_costo='laboratorio',
        usuario=usuario,
        referencia=lote.codigo,
        nota=observaciones or f'Baja por caducidad del lote {lote.codigo}.',
    )


# ----------------------------------------------------------- conteo cíclico
def lotes_del_alcance(unidad, alcance, referencia):
    """Los lotes que entran en un conteo, según lo que se decidió contar."""
    lotes = LoteConsumible.objects.filter(
        consumible__unidad=unidad, consumible__activo=True, estado__in=ESTADOS_VIVOS,
    ).select_related('consumible')
    if alcance == 'bodega' and referencia:
        lotes = lotes.filter(bodega__icontains=referencia)
    elif alcance == 'clasificacion' and referencia:
        lotes = lotes.filter(consumible__clasificacion=referencia)
    return lotes.order_by('consumible__nombre', 'codigo', 'pk')


def abrir_conteo(unidad, usuario, datos):
    """Congela lo que el sistema cree tener de cada lote del alcance."""
    alcance = (datos.get('alcance') or 'todo').strip()
    if alcance not in dict(ConteoInventario.ALCANCES):
        raise ValidationError('Elige un alcance válido para el conteo.')
    referencia = (datos.get('referencia') or '').strip()[:120]
    if alcance != 'todo' and not referencia:
        raise ValidationError('Di qué bodega o qué clasificación se cuenta.')
    lotes = list(lotes_del_alcance(unidad, alcance, referencia))
    if not lotes:
        raise ValidationError('No hay lotes con saldo en ese alcance.')
    with transaction.atomic():
        conteo = ConteoInventario(
            unidad=unidad,
            nombre=(datos.get('nombre') or '').strip()[:160] or f'Conteo del {timezone.localdate():%d/%m/%Y}',
            alcance=alcance,
            referencia=referencia,
            responsable=usuario,
            observaciones=(datos.get('observaciones') or '').strip(),
        )
        conteo.full_clean(exclude=['codigo'])
        conteo.save()
        LineaConteo.objects.bulk_create([
            LineaConteo(
                conteo=conteo,
                lote=lote,
                consumible=lote.consumible,
                cantidad_sistema=lote.cantidad_actual,
            )
            for lote in lotes
        ])
    return conteo


@transaction.atomic
def registrar_linea(linea, cantidad, observaciones=''):
    """Lo que el bodeguero encontró en el estante."""
    conteo = ConteoInventario.objects.select_for_update().get(pk=linea.conteo_id)
    linea = LineaConteo.objects.select_for_update().get(pk=linea.pk, conteo=conteo)
    if not conteo.abierto:
        raise ValidationError('El conteo ya está cerrado.')
    try:
        valor = Decimal(str(cantidad).strip().replace(',', '.'))
    except (InvalidOperation, AttributeError) as error:
        raise ValidationError('La cantidad contada debe ser un número.') from error
    if not valor.is_finite():
        raise ValidationError('La cantidad contada debe ser un número finito.')
    if valor < 0:
        raise ValidationError('Lo contado no puede ser negativo.')
    linea.cantidad_contada = valor
    linea.observaciones = (observaciones or '').strip()[:240]
    linea.full_clean()
    linea.save()
    return linea


@transaction.atomic
def cerrar_conteo(conteo, usuario):
    """Cada diferencia contada entra al kardex como su ajuste; lo no contado queda igual."""
    solicitado = conteo
    conteo = ConteoInventario.objects.select_for_update().get(pk=conteo.pk)
    if not conteo.abierto:
        raise ValidationError('El conteo ya está cerrado.')
    lineas = list(conteo.lineas.select_for_update().order_by('pk'))
    if not any(linea.contada for linea in lineas):
        raise ValidationError('Todavía no se contó ningún lote.')
    ajustes = []
    with transaction.atomic():
        # El kardex bloquea primero el artículo y después su lote. Conservar
        # ese orden evita interbloqueos con una salida registrada a la vez.
        contadas = [linea for linea in lineas if linea.contada]
        list(Consumible.objects.select_for_update().filter(
            pk__in={linea.consumible_id for linea in contadas},
        ).order_by('pk'))
        lotes = {lote.pk: lote for lote in LoteConsumible.objects.select_for_update().filter(
            pk__in={linea.lote_id for linea in contadas},
        ).order_by('pk')}
        for linea in contadas:
            linea.full_clean()
            if lotes[linea.lote_id].cantidad_actual != linea.cantidad_sistema:
                raise ValidationError(
                    'El saldo de un lote cambió desde la apertura del conteo. '
                    'Anula este conteo y abre uno nuevo antes de ajustar el inventario.'
                )
        for linea in lineas:
            diferencia = linea.diferencia
            if diferencia is None or diferencia == 0 or linea.ajuste_id:
                continue
            lote = lotes[linea.lote_id]
            if diferencia > 0 and Decimal(lote.cantidad_actual) + diferencia > Decimal(lote.cantidad_inicial):
                # Apareció más de lo que el lote decía haber recibido: el conteo manda.
                lote.cantidad_inicial = Decimal(lote.cantidad_actual) + diferencia
                lote.save(update_fields=['cantidad_inicial', 'actualizado_en'])
            entrada = EntradaInventario.objects.create(
                consumible=linea.consumible,
                unidad=conteo.unidad,
                tipo='ingreso' if diferencia > 0 else 'salida',
                motivo='ajuste_positivo' if diferencia > 0 else 'ajuste_negativo',
                cantidad=abs(diferencia),
                lote_inventario=lote,
                responsable_costo='laboratorio',
                usuario=usuario,
                referencia=conteo.codigo,
                nota=f'Ajuste del conteo {conteo.codigo} sobre el lote {lote.codigo}.',
                clave_idempotencia=f'conteo:{conteo.pk}:linea:{linea.pk}',
            )
            linea.ajuste = entrada
            linea.save(update_fields=['ajuste'])
            ajustes.append(entrada)
        conteo.estado = 'cerrado'
        conteo.cerrado_en = timezone.now()
        conteo.save(update_fields=['estado', 'cerrado_en'])
        solicitado.estado, solicitado.cerrado_en = conteo.estado, conteo.cerrado_en
    return ajustes


def resumen_conteo(conteo):
    lineas = list(conteo.lineas.select_related('lote', 'consumible', 'ajuste'))
    contadas = [linea for linea in lineas if linea.contada]
    return {
        'conteo': conteo,
        'lineas': lineas,
        'total': len(lineas),
        'contadas': len(contadas),
        'pendientes': len(lineas) - len(contadas),
        'diferencias': sum(1 for linea in contadas if linea.diferencia != 0),
    }


# ------------------------------------------------------- material del cliente
def material_del_cliente(unidad):
    """Lo que está en la bodega pero es de quien encargó el trabajo."""
    return list(
        LoteConsumible.objects.filter(consumible__unidad=unidad, material_cliente=True)
        .exclude(estado__in=('retirado',))
        .select_related('consumible', 'reserva')
        .order_by('-fecha_ingreso', '-pk')[:30]
    )


# ------------------------------------------------------------------ el panel
def contexto_almacen(unidad, permisos_operativos, configuracion):
    """Lo que el modo «Almacén» del panel necesita."""
    puede = bool(permisos_operativos.get('inventario') and configuracion.consumibles)
    if not puede:
        return {'almacen_habilitado': False, 'puede_operar_almacen': False}
    conteos = list(
        ConteoInventario.objects.filter(unidad=unidad)
        .select_related('responsable')
        .prefetch_related('lineas__lote', 'lineas__consumible', 'lineas__ajuste')
        .order_by('-fecha', '-pk')[:8]
    )
    abierto = next((conteo for conteo in conteos if conteo.abierto), None)
    cobertura = cobertura_del_plan(unidad)
    vencimientos = lotes_por_vencer(unidad)
    return {
        'almacen_habilitado': True,
        'puede_operar_almacen': True,
        'cobertura_plan': cobertura,
        'cobertura_plan_url': (
            reverse('plan_maestro', args=[unidad.slug, cobertura['plan'].pk]) if cobertura['plan'] else ''
        ),
        'lotes_por_vencer': vencimientos,
        'lotes_vencidos': [fila for fila in vencimientos if fila['vencido']],
        'orden_de_salida': orden_de_salida(unidad),
        'conteos_almacen': conteos,
        'conteo_abierto': resumen_conteo(abierto) if abierto is not None else None,
        'material_cliente_almacen': material_del_cliente(unidad),
        'alcances_conteo': ConteoInventario.ALCANCES,
        'clasificaciones_conteo': Consumible.CLASIFICACIONES,
        'bodegas_almacen': sorted({
            lote.bodega for lote in LoteConsumible.objects.filter(
                consumible__unidad=unidad, estado__in=ESTADOS_VIVOS,
            ).exclude(bodega='')
        }),
    }


def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def operar_conteo_inventario(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if not registro_id:
        conteo = abrir_conteo(unidad, request.user, request.POST)
        return conteo, f'Conteo abierto con {conteo.lineas.count()} lotes', True
    objeto = get_object_or_404(ConteoInventario.objects.select_for_update(), pk=registro_id, unidad=unidad)
    accion = _texto(request, 'accion_conteo') or _texto(request, 'accion')
    if accion == 'desactivar':
        if not objeto.abierto:
            raise ValidationError('Un conteo cerrado ya no se anula.')
        objeto.estado = 'anulado'
        objeto.save(update_fields=['estado'])
        return objeto, 'Conteo anulado', False
    if accion == 'cerrar':
        ajustes = cerrar_conteo(objeto, request.user)
        return objeto, f'Conteo cerrado con {len(ajustes)} ajustes', False
    objeto.nombre = _texto(request, 'nombre', 160) or objeto.nombre
    objeto.observaciones = _texto(request, 'observaciones')
    fecha = _texto(request, 'fecha')
    if fecha:
        objeto.fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    objeto.full_clean(exclude=['codigo'])
    objeto.save()
    return objeto, 'Conteo actualizado', False


def operar_linea_conteo(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if not registro_id:
        raise ValidationError('Selecciona el lote que contaste.')
    objeto = get_object_or_404(
        LineaConteo.objects.all(), pk=registro_id, conteo__unidad=unidad,
    )
    objeto = registrar_linea(objeto, request.POST.get('cantidad_contada'), _texto(request, 'observaciones'))
    return objeto, 'Conteo del lote registrado', False


def operar_baja_lote(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if not registro_id:
        raise ValidationError('Selecciona el lote que vas a dar de baja.')
    objeto = get_object_or_404(
        LoteConsumible.objects.select_for_update(), pk=registro_id, consumible__unidad=unidad,
    )
    dar_de_baja_por_caducidad(objeto, request.user, _texto(request, 'observaciones'))
    return objeto, 'Lote dado de baja por caducidad', False


OPERADORES_ALMACEN = {
    'conteo_inventario': operar_conteo_inventario,
    'linea_conteo': operar_linea_conteo,
    'baja_lote': operar_baja_lote,
}
PERMISOS_ALMACEN = {clave: 'inventario' for clave in OPERADORES_ALMACEN}
MODELOS_ALMACEN = {
    'conteo_inventario': ConteoInventario,
    'linea_conteo': LineaConteo,
    'baja_lote': LoteConsumible,
}
