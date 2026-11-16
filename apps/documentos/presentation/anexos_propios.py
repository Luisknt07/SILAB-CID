"""Anexos propios de planta piloto, centro experimental y observatorio.

Tablas y columnas: docs/estructura-anexos-por-tipo-de-unidad.md, sección 5. Cada función
pública recibe un :class:`~apps.documentos.presentation.anexos_evidencia.Contexto` y devuelve
la lista de :class:`~apps.documentos.presentation.anexos_evidencia.Registro` del anexo, en el
orden de la especificación. El motor numera las tablas y dibuja el PDF.

- Planta piloto: producción (5.1) y control de calidad (5.2). Las corridas demostrativas,
  que incluyen las de sesiones de práctica, se marcan en la tabla de órdenes y no cuentan para
  la meta; sus lotes y salidas no se presentan.
- Centro experimental: ensayos (5.3) y producción agropecuaria (5.4). Un ciclo marcado como
  ensayo va solo en el primero; los demás, solo en el segundo.
- Observatorio: datos (5.5), publicaciones (5.6) y socialización (5.7).

La columna «Revisión técnica» sale de las evidencias de gestión verificadas, tal como las
mide el informe (``contexto.registros``): un registro publicado o cerrado no la sustituye.
"""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from .anexos_evidencia import (
    Grupo, Par, Registro, cifra, enlace, enlace_archivo, enlace_recurso, evidencias_de_gestion, fecha, nombre_de,
    par, plural, si_no, texto, verificacion,
)

# Cómo se escribe en una celda lo que el modelo guarda con una frase larga.
DESPERDICIOS = {'desperdicio_equipo': 'por falla del equipo', 'desperdicio_calidad': 'por calidad o proceso'}
ORIGENES_DEL_DATO = {'cargador': 'Cargador', 'manual': 'Manual', 'csv': 'CSV', 'api': 'API'}
CICLOS_CON_ANIMALES = ('hato', 'lote')
TRATAMIENTOS_RECIENTES = 2  # Los últimos tratamientos de sanidad que resume la tabla de animales.


# -- escritura de celdas -----------------------------------------------------------------

def _numero(valor):
    """Cantidad o medición con todos sus decimales y la escritura local: 4,05 · 1.250 · -18."""
    if valor is None or valor == '':
        return '—'
    numero = Decimal(str(valor))
    entero, _, decimales = format(abs(numero), 'f').partition('.')
    decimales = decimales.rstrip('0')
    return ('-' if numero < 0 else '') + f'{int(entero):,}'.replace(',', '.') + (f',{decimales}' if decimales else '')


def _cantidad(valor, unidad=''):
    """Cantidad con su unidad de medida: «230 kg»; «—» si no hay cantidad."""
    return '—' if valor is None else f'{_numero(valor)} {unidad or ""}'.strip()


def _dinero(valor):
    return '—' if not valor else f'USD {cifra(valor, 2)}'


def _detalle(evidencia):
    return evidencia.detalle if isinstance(evidencia.detalle, dict) else {}


def _fecha_iso(valor):
    """Una fecha guardada como texto «aaaa-mm-dd», en la escritura local; '' si no es una fecha."""
    try:
        return fecha(date.fromisoformat(str(valor or '')))
    except ValueError:
        return ''


def _respaldo(evidencia):
    return enlace_recurso(evidencia.recurso) if evidencia.recurso_id else enlace(evidencia.enlace)


def _con_enlace(rotulo, direccion):
    """El texto como enlace si hay dirección; si no, el texto solo."""
    return enlace(direccion, rotulo) if str(direccion or '').strip() else rotulo


def _corto(rotulo):
    """«Labor (siembra, poda…)» se escribe «Labor»."""
    return str(rotulo).split(' (')[0]


def _lineas(valor):
    return [linea.strip(' -•\t') for linea in str(valor or '').splitlines() if linea.strip(' -•\t')]


def _dia_local(instante):
    """El día local de un instante con hora."""
    from django.utils import timezone
    return timezone.localdate(instante) if timezone.is_aware(instante) else instante.date()


# -- revisión técnica --------------------------------------------------------------------

def _fuentes_verificadas(contexto, actividad):
    """Las evidencias con revisión técnica vigente de una meta, tal como las mide el informe."""
    return (contexto.registros.get('fuentes_gestion') or {}).get(actividad) or []


def _revisiones(contexto, actividad):
    """{registro de origen: evidencia verificada} de una meta."""
    return {(fuente.get('origen') or {}).get('id'): fuente for fuente in _fuentes_verificadas(contexto, actividad)}


def _revision_tecnica(fuente):
    """«Vigente», con el código de la evidencia que la acredita, o «Pendiente»."""
    return par('Vigente', texto(fuente.get('codigo'), 40)) if fuente else 'Pendiente'


# -- planta piloto: producción (5.1) -----------------------------------------------------

def _tabla_ordenes(contexto):
    from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion

    del_periodo = OrdenProduccion.objects.filter(unidad=contexto.unidad, fecha_inicio__lte=contexto.fin,
                                                 fecha_fin__gte=contexto.inicio)
    # Toda orden nacida de una sesión de práctica es una corrida demostrativa (lo fija el modelo al guardar).
    ordenes = list(del_periodo.select_related('producto', 'receta', 'linea', 'responsable__usuario')
                   .order_by('fecha_inicio', 'codigo', 'pk'))
    filas = []
    for orden in ordenes:
        medida = orden.producto.unidad_medida
        filas.append([
            texto(orden.codigo),
            par(texto(orden.producto.nombre, 60), texto(orden.receta.nombre, 80)),
            par(orden.get_origen_display(), 'Corrida demostrativa' if orden.demostrativa else ''),
            par(fecha(orden.fecha_inicio), f'al {fecha(orden.fecha_fin)}'),
            texto((orden.linea.codigo or orden.linea.nombre) if orden.linea_id else '', 50),
            par(_cantidad(orden.cantidad_planificada, medida),
                f'obtenida {_cantidad(orden.cantidad_obtenida, medida)}' if orden.cantidad_obtenida is not None
                else ''),
            par(f'{_numero(orden.rendimiento_real_pct)} %',
                f'merma {_cantidad(orden.merma, medida)}' if orden.merma is not None else '')
            if orden.rendimiento_real_pct is not None else '—',
            orden.get_estado_display(),
            texto(orden.responsable.nombre_publico, 50) if orden.responsable_id else '—',
        ])
    reales = [o for o in ordenes if not o.demostrativa]
    terminadas = [o for o in reales if o.estado == 'terminada']
    obtenido = defaultdict(Decimal)
    for orden in terminadas:
        if orden.cantidad_obtenida is not None:
            obtenido[orden.producto.unidad_medida] += orden.cantidad_obtenida
    rendimientos = [o.rendimiento_real_pct for o in terminadas if o.rendimiento_real_pct is not None]
    pie = (f'Total: {plural(len(reales), "orden", "órdenes")} de producción real · terminadas: '
           f'{cifra(len(terminadas))} · cantidad obtenida: '
           f'{", ".join(_cantidad(v, m) for m, v in sorted(obtenido.items())) or "—"} · rendimiento medio: '
           + (f'{cifra(sum(rendimientos) / len(rendimientos))} %' if rendimientos else '—'))
    if len(ordenes) > len(reales):
        pie += f' · corridas demostrativas, que no cuentan para la meta: {cifra(len(ordenes) - len(reales))}'
    return Registro('Órdenes de producción',
                    ('Orden', 'Producto / receta', 'Origen', 'Fechas', 'Línea', 'Cantidad', 'Rendimiento / merma',
                     'Estado', 'Responsable'),
                    filas, pesos=(10, 17, 12, 9, 12, 11, 10, 8, 11), total=pie,
                    vacio='No hay órdenes de producción en el período.')


def _lotes_reales(contexto):
    """Los lotes de producto del período que son existencia real, y cuántos no lo son."""
    from apps.plantas_piloto.operacion.models.produccion import LoteProducto

    del_periodo = LoteProducto.objects.filter(unidad=contexto.unidad,
                                              fecha_produccion__range=(contexto.inicio, contexto.fin))
    lotes = list(del_periodo.filter(demostrativo=False, orden__sesion__isnull=True)
                 .select_related('producto', 'orden').order_by('fecha_produccion', 'codigo', 'pk'))
    return lotes, del_periodo.count() - len(lotes)


def _tabla_lotes(lotes, sin_listar):
    filas = []
    for lote in lotes:
        medida = lote.producto.unidad_medida
        filas.append([
            texto(lote.codigo),
            texto(lote.producto.nombre, 60),
            texto(lote.orden.codigo) if lote.orden_id else '—',
            par(fecha(lote.fecha_produccion), f'vence {fecha(lote.fecha_vencimiento)}' if lote.fecha_vencimiento else ''),
            par(_cantidad(lote.cantidad_inicial, medida), f'disponible {_cantidad(lote.cantidad_disponible, medida)}'),
            lote.get_control_calidad_display(),
            lote.get_estado_display(),
            texto(lote.ubicacion, 70),
        ])
    calidad = Counter(lote.control_calidad for lote in lotes)
    pie = (f'Total: {plural(len(lotes), "lote", "lotes")} · aprobados: {cifra(calidad["aprobado"])} · pendientes '
           f'de control: {cifra(calidad["pendiente"])} · rechazados: {cifra(calidad["rechazado"])} · sin control '
           f'exigible: {cifra(calidad["no_aplica"])}')
    if sin_listar:
        pie += (' · lotes demostrativos o de sesiones de práctica, que no son existencia real y no se listan: '
                f'{cifra(sin_listar)}')
    return Registro('Lotes producidos',
                    ('Lote', 'Producto', 'Orden', 'Producción / vencimiento', 'Cantidad', 'Control de calidad',
                     'Estado', 'Ubicación'),
                    filas, pesos=(22, 15, 10, 11, 11, 11, 8, 12), total=pie,
                    vacio='No hay lotes producidos en el período.')


def _tabla_consumos(contexto):
    from apps.recursos.models.consumibles import EntradaInventario

    entradas = list(EntradaInventario.objects.filter(
        consumible__unidad=contexto.unidad, tipo='salida', motivo__in=('consumo_produccion', *DESPERDICIOS),
        fecha__date__range=(contexto.inicio, contexto.fin))
        .select_related('consumible', 'lote_inventario').order_by('fecha', 'pk'))
    # Un renglón por orden, materia prima y lote: lo consumido y, si lo hubo, lo desperdiciado.
    renglones, turno = {}, {}
    for entrada in entradas:
        if entrada.motivo == 'consumo_produccion':
            turno.setdefault(entrada.referencia, len(turno))
            clave = (entrada.referencia, entrada.consumible_id, entrada.lote_inventario_id)
            renglones.setdefault(clave, [entrada, Decimal(0), Decimal(0), []])[1] += entrada.cantidad
    for entrada in entradas:
        # Un desperdicio es de producción cuando lleva la referencia de una orden con consumos.
        if entrada.motivo in DESPERDICIOS and entrada.referencia and entrada.referencia in turno:
            clave = (entrada.referencia, entrada.consumible_id, entrada.lote_inventario_id)
            renglon = renglones.setdefault(clave, [entrada, Decimal(0), Decimal(0), []])
            renglon[2] += entrada.cantidad
            if DESPERDICIOS[entrada.motivo] not in renglon[3]:
                renglon[3].append(DESPERDICIOS[entrada.motivo])
    filas = []
    del_cliente = 0
    for (referencia, _consumible, _lote), (entrada, consumido, desperdicio, motivos) in sorted(
            renglones.items(), key=lambda renglon: (turno[renglon[0][0]], renglon[1][0].fecha, renglon[1][0].pk)):
        articulo, lote = entrada.consumible, entrada.lote_inventario
        ajeno = bool(lote and lote.material_cliente)
        del_cliente += ajeno
        filas.append([
            texto(referencia),
            par(texto(articulo.codigo), texto(articulo.nombre, 60)),
            texto(lote.codigo if lote else ''),
            _cantidad(consumido, articulo.unidad_medida) if consumido else '—',
            par(_cantidad(desperdicio, articulo.unidad_medida), ' y '.join(motivos)) if desperdicio else '—',
            'Del cliente' if ajeno else 'Propia',
        ])
    pie = (f'Total: {plural(len(filas), "consumo", "consumos")} · órdenes: {cifra(len(turno))} · con desperdicio: '
           f'{cifra(sum(bool(r[2]) for r in renglones.values()))} · de materia prima del cliente: '
           f'{cifra(del_cliente)}')
    return Registro('Consumo de materias primas por orden',
                    ('Orden', 'Materia prima', 'Lote', 'Cantidad', 'Desperdicio', 'Propia o del cliente'),
                    filas, pesos=(14, 30, 20, 12, 14, 10), total=pie,
                    vacio='No hay consumos de materias primas en producción registrados en el período.')


def _temperatura_al_despacho(movimiento):
    if movimiento.temperatura_despacho is not None:
        return f'{_numero(movimiento.temperatura_despacho)} °C'
    return 'Sin registrar' if movimiento.lote.producto.requiere_frio else 'No requiere frío'


def _destino_de(movimiento):
    receptora = movimiento.unidad_destino.nombre if movimiento.unidad_destino_id else ''
    destino = movimiento.destino.strip() or receptora
    segundo = movimiento.cliente.nombre if movimiento.cliente_id else receptora if receptora != destino else ''
    if not segundo and movimiento.tipo == 'baja':
        segundo = movimiento.motivo
    return par(texto(destino, 80), texto(segundo, 80) if str(segundo or '').strip() else '')


def _tabla_salidas(contexto):
    from apps.plantas_piloto.operacion.models.produccion import MovimientoProducto

    del_periodo = MovimientoProducto.objects.filter(unidad=contexto.unidad,
                                                    fecha__date__range=(contexto.inicio, contexto.fin))
    movimientos = list(del_periodo.filter(lote__demostrativo=False, lote__orden__sesion__isnull=True)
                       .select_related('lote__producto', 'cliente', 'unidad_destino').order_by('fecha', 'pk'))
    sin_listar = del_periodo.count() - len(movimientos)
    filas = []
    for movimiento in movimientos:
        producto = movimiento.lote.producto
        filas.append([
            fecha(movimiento.fecha),
            par(texto(movimiento.lote.codigo), texto(producto.nombre, 60)),
            movimiento.get_tipo_display(),
            _cantidad(movimiento.cantidad, producto.unidad_medida),
            _destino_de(movimiento),
            _dinero(movimiento.valor_total),
            _temperatura_al_despacho(movimiento),
            texto(movimiento.referencia, 60),
        ])
    ventas = [m for m in movimientos if m.tipo == 'venta']
    pie = (f'Total: {plural(len(filas), "salida", "salidas")} · ventas: {cifra(len(ventas))} · valor total: '
           f'{_dinero(sum((m.valor_total or 0 for m in movimientos), Decimal(0)))}')
    if sin_listar:
        pie += f' · salidas de lotes demostrativos o de sesiones de práctica, que no se listan: {cifra(sin_listar)}'
    return Registro('Salidas de producto',
                    ('Fecha', 'Lote / producto', 'Tipo', 'Cantidad', 'Destino / cliente', 'Valor',
                     'Temperatura al despacho', 'Referencia'),
                    filas, pesos=(8, 22, 12, 9, 19, 9, 10, 11), total=pie,
                    vacio='No hay salidas de producto en el período.')


def produccion_planta(contexto):
    """Anexo de producción de la planta piloto (sección 5.1): órdenes, lotes, consumos y salidas."""
    lotes, sin_listar = _lotes_reales(contexto)
    return [_tabla_ordenes(contexto), _tabla_lotes(lotes, sin_listar), _tabla_consumos(contexto),
            _tabla_salidas(contexto)]


# -- planta piloto: control de calidad (5.2) ---------------------------------------------

def _limites(parametro):
    """«mín. 6,1 · máx. 6,8 pH»; en un parámetro cualitativo, el valor esperado."""
    medida = f' {parametro.unidad_medida}' if parametro.unidad_medida else ''
    limites = ' · '.join(f'{rotulo} {_numero(valor)}{medida}' for rotulo, valor in (
        ('mín.', parametro.minimo), ('máx.', parametro.maximo)) if valor is not None)
    esperado = texto(parametro.valor_esperado, 70) if parametro.valor_esperado.strip() else ''
    if parametro.tipo == 'cualitativo':
        return esperado or 'Conforme'
    return par(limites, esperado) if limites else esperado or 'Sin límite'


def _valor_medido(medicion):
    if medicion.valor_numerico is not None:
        return _cantidad(medicion.valor_numerico, medicion.parametro.unidad_medida)
    return texto(medicion.valor_texto, 70)


def _objeto_del_control(control):
    if control.lote_producto_id:
        return par(texto(control.lote_producto.codigo), 'Lote de producto')
    if control.lote_consumible_id:
        return par(texto(control.lote_consumible.codigo), 'Lote de materia prima')
    if control.orden_id:
        return par(texto(control.orden.codigo), 'Orden')
    return '—'


def _tabla_controles(contexto):
    from apps.plantas_piloto.operacion.models.calidad import ControlCalidad

    controles = list(ControlCalidad.objects.reales().filter(
        unidad=contexto.unidad, fecha__date__range=(contexto.inicio, contexto.fin),
        lote_producto__orden__sesion__isnull=True, orden__sesion__isnull=True)
        .select_related('plan', 'lote_producto', 'lote_consumible', 'orden', 'registrado_por')
        .prefetch_related('mediciones__parametro').order_by('fecha', 'pk'))
    filas = []
    for control in controles:
        antes = [fecha(control.fecha), par(texto(control.plan.nombre, 70), control.plan.get_momento_display()),
                 _objeto_del_control(control)]
        despues = [control.get_resultado_display(), nombre_de(control.registrado_por)]
        mediciones = sorted(control.mediciones.all(), key=lambda m: (m.parametro.orden, m.pk))
        if not mediciones:
            filas.append([*antes, 'Sin mediciones registradas', '—', '—', '—', *despues])
        for medicion in mediciones:
            filas.append([*antes, texto(medicion.parametro.nombre, 70), _limites(medicion.parametro),
                          _valor_medido(medicion), si_no(medicion.conforme), *despues])
    conformes = sum(c.resultado == 'conforme' for c in controles)
    pie = (f'Total: {plural(len(filas), "medición", "mediciones")} de {plural(len(controles), "control", "controles")}'
           f' · controles conformes: {cifra(conformes)} · no conformes: {cifra(len(controles) - conformes)}')
    return Registro('Controles del período',
                    ('Fecha', 'Plan / momento', 'Lote u orden', 'Parámetro', 'Límites', 'Valor medido', 'Conforme',
                     'Resultado del control', 'Registrado por'),
                    filas, pesos=(8, 15, 20, 13, 11, 9, 6, 8, 10), total=pie,
                    vacio='No hay controles de calidad registrados en el período.')


def _tabla_liberacion(lotes, corte):
    from apps.plantas_piloto.operacion.models.calidad import ControlCalidad

    # Subproductos y residuos no se liberan: su control «No aplica».
    exigibles = [lote for lote in lotes if lote.control_calidad != 'no_aplica']
    por_lote = defaultdict(list)
    for control in (ControlCalidad.objects.filter(lote_producto__in=exigibles, fecha__date__lte=corte)
                    .select_related('plan', 'registrado_por').order_by('fecha', 'pk')):
        por_lote[control.lote_producto_id].append(control)
    filas = []
    for lote in exigibles:
        controles = por_lote[lote.pk]
        no_conformes = sum(c.resultado == 'no_conforme' for c in controles)
        # El lote no guarda quién ni cuándo lo liberó: lo dice su último control de liberación.
        decisivo = next((c for c in reversed(controles) if c.plan.momento == 'liberacion'),
                        controles[-1] if controles else None)
        decidido = lote.control_calidad in ('aprobado', 'rechazado') and decisivo is not None
        filas.append([
            texto(lote.codigo),
            texto(lote.producto.nombre, 60),
            par(cifra(len(controles)), f'no conformes: {cifra(no_conformes)}' if no_conformes else ''),
            lote.get_control_calidad_display(),
            fecha(decisivo.fecha) if decidido else '—',
            nombre_de(decisivo.registrado_por) if decidido else '—',
        ])
    calidad = Counter(lote.control_calidad for lote in exigibles)
    pie = (f'Total: {plural(len(filas), "lote", "lotes")} · aprobados: {cifra(calidad["aprobado"])} · rechazados: '
           f'{cifra(calidad["rechazado"])} · pendientes: {cifra(calidad["pendiente"])}')
    if len(lotes) > len(exigibles):
        pie += f' · lotes sin control exigible, que no se liberan: {cifra(len(lotes) - len(exigibles))}'
    return Registro('Liberación de lotes',
                    ('Lote', 'Producto', 'Controles realizados', 'Decisión', 'Fecha', 'Responsable'),
                    filas, pesos=(26, 22, 12, 14, 10, 16), total=pie,
                    vacio='No hay lotes del período que requieran liberación.')


def _objeto_de_la_no_conformidad(hallazgo):
    if hallazgo.lote_producto_id:
        return texto(hallazgo.lote_producto.codigo)
    if hallazgo.lote_consumible_id:
        return texto(hallazgo.lote_consumible.codigo)
    return _objeto_del_control(hallazgo.control) if hallazgo.control_id else 'Proceso'


def _no_conformidades(contexto):
    """Las del período y las anteriores que seguían abiertas o se cerraron en él."""
    from django.db.models import Q
    from apps.plantas_piloto.operacion.models.calidad import NoConformidad

    return list(NoConformidad.objects.reales().filter(
        unidad=contexto.unidad, detectada_en__date__lte=contexto.fin,
        lote_producto__orden__sesion__isnull=True, control__orden__sesion__isnull=True,
        control__lote_producto__orden__sesion__isnull=True)
        .filter(Q(detectada_en__date__gte=contexto.inicio) | Q(cerrada_en__date__gte=contexto.inicio)
                | ~Q(estado='cerrada'))
        .select_related('lote_producto', 'lote_consumible', 'control__lote_producto', 'control__lote_consumible',
                        'control__orden', 'detectada_por')
        .prefetch_related('acciones__responsable').order_by('detectada_en', 'pk'))


def _tabla_no_conformidades(contexto, hallazgos):
    filas = [[
        texto(hallazgo.codigo),
        par(fecha(hallazgo.detectada_en), nombre_de(hallazgo.detectada_por)),
        _objeto_de_la_no_conformidad(hallazgo),
        par(texto(hallazgo.descripcion, 220), texto(hallazgo.causa, 160) if hallazgo.causa.strip() else ''),
        hallazgo.get_gravedad_display(),
        hallazgo.get_disposicion_display(),
        hallazgo.get_estado_display(),
        fecha(hallazgo.cerrada_en),
    ] for hallazgo in hallazgos]
    estados = Counter(hallazgo.estado for hallazgo in hallazgos)
    anteriores = sum(_dia_local(h.detectada_en) < contexto.inicio for h in hallazgos)
    pie = (f'Total: {plural(len(filas), "no conformidad", "no conformidades")} · abiertas: '
           f'{cifra(estados["abierta"])} · en tratamiento: {cifra(estados["en_tratamiento"])} · cerradas: '
           f'{cifra(estados["cerrada"])}')
    if anteriores:
        pie += f' · detectadas antes del período y abiertas o cerradas en él: {cifra(anteriores)}'
    return Registro('No conformidades',
                    ('Código', 'Detección', 'Lote o proceso', 'Hallazgo / causa', 'Gravedad', 'Disposición',
                     'Estado', 'Cierre'),
                    filas, pesos=(7, 11, 20, 28, 7, 10, 9, 8), total=pie,
                    vacio='No hay no conformidades en el período ni pendientes de períodos anteriores.')


def _tabla_acciones(hallazgos):
    filas = []
    estados = Counter()
    for hallazgo in hallazgos:
        for accion in hallazgo.acciones.all():
            estados[accion.estado] += 1
            filas.append([
                texto(hallazgo.codigo),
                texto(accion.descripcion, 240),
                nombre_de(accion.responsable),
                par(fecha(accion.fecha_compromiso), f'cierre {fecha(accion.fecha_cierre)}' if accion.fecha_cierre
                    else ''),
                accion.get_estado_display(),
                texto(accion.verificacion, 200),
            ])
    pie = (f'Total: {plural(len(filas), "acción", "acciones")} · pendientes: {cifra(estados["pendiente"])} · '
           f'cumplidas: {cifra(estados["cumplida"])} · verificadas: {cifra(estados["verificada"])}')
    return Registro('Acciones correctivas',
                    ('No conformidad', 'Acción', 'Responsable', 'Compromiso / cierre', 'Estado', 'Verificación'),
                    filas, pesos=(11, 34, 15, 12, 9, 19), total=pie,
                    vacio='No hay acciones correctivas registradas para las no conformidades de la tabla anterior.')


def calidad_planta(contexto):
    """Anexo de control de calidad de la planta piloto (sección 5.2).

    Controles con sus mediciones, liberación de los lotes del período (los del anexo de
    producción, citados por su código), no conformidades y acciones correctivas.
    """
    lotes, _sin_listar = _lotes_reales(contexto)
    hallazgos = _no_conformidades(contexto)
    return [_tabla_controles(contexto), _tabla_liberacion(lotes, contexto.corte),
            _tabla_no_conformidades(contexto, hallazgos), _tabla_acciones(hallazgos)]


# -- centro experimental: ensayos (5.3) --------------------------------------------------

def codigo_de_ensayo(ciclo):
    """La referencia con que los anexos citan un ensayo: «ENS-0007».

    El ciclo no tiene código propio; se deriva de su número de registro, que no cambia.
    Acepta el ciclo o su identificador.
    """
    return f'ENS-{int(getattr(ciclo, "pk", ciclo)):04d}'


def _area_de(ciclo):
    """Código del área (anexo de fichas técnicas) y, debajo, la superficie o los animales."""
    extension = ' · '.join(parte for parte in (
        f'{_numero(ciclo.superficie_ha)} ha' if ciclo.superficie_ha else '',
        plural(ciclo.animales, 'animal', 'animales') if ciclo.animales else '') if parte)
    lugar = texto(ciclo.lugar.codigo or ciclo.lugar.nombre, 50) if ciclo.lugar_id else '—'
    return par(lugar, extension)


def _diseno_de(ciclo):
    tratamientos = _lineas(ciclo.tratamientos)
    partes = [texto('; '.join(tratamientos), 150)] if tratamientos else []
    if ciclo.repeticiones:
        partes.append(plural(ciclo.repeticiones, 'repetición', 'repeticiones'))
    variables = ' '.join(str(ciclo.variables or '').split())
    return par(' · '.join(partes) or '—', texto(f'Variables: {variables}', 160) if variables else '')


def _tabla_ensayos(ciclos, revisiones):
    filas = [[
        par(codigo_de_ensayo(ciclo), texto(ciclo.nombre, 80)),
        par(texto(ciclo.eje.titulo, 50), texto(ciclo.rubro, 50)),
        _area_de(ciclo),
        texto(ciclo.objetivo, 220),
        _diseno_de(ciclo),
        par(fecha(ciclo.inicio), f'hasta {fecha(ciclo.fin_previsto)}'),
        par(ciclo.get_estado_display(), f'fin {fecha(ciclo.fin)}' if ciclo.fin else ''),
        nombre_de(ciclo.responsable),
        _revision_tecnica(revisiones.get(ciclo.pk)),
    ] for ciclo in ciclos]
    estados = Counter(ciclo.estado for ciclo in ciclos)
    pie = (f'Total: {plural(len(filas), "ensayo", "ensayos")} · planificados: {cifra(estados["planificado"])} · '
           f'en curso: {cifra(estados["en_curso"])} · cerrados: {cifra(estados["cerrado"])} · con revisión técnica '
           f'vigente: {cifra(sum(ciclo.pk in revisiones for ciclo in ciclos))}')
    return Registro('Ensayos',
                    ('Código / nombre', 'Eje / rubro', 'Parcela o área', 'Objetivo', 'Diseño',
                     'Inicio / fin previsto', 'Estado', 'Responsable', 'Revisión técnica'),
                    filas, pesos=(13, 10, 10, 17, 17, 9, 7, 9, 8), total=pie,
                    vacio='No hay ensayos registrados en el período.')


def _tabla_seguimiento(ciclos):
    filas = [[
        codigo_de_ensayo(ciclo),
        fecha(registro.fecha),
        _corto(registro.get_tipo_display()),
        _cantidad(registro.cantidad, registro.unidad_medida),
        texto(registro.detalle, 240),
        nombre_de(registro.registrado_por),
    ] for ciclo in ciclos for registro in ciclo.registros_del_periodo]
    con_seguimiento = sum(bool(ciclo.registros_del_periodo) for ciclo in ciclos)
    return Registro('Seguimiento y mediciones',
                    ('Ensayo', 'Fecha', 'Variable / registro', 'Valor', 'Detalle', 'Registrado por'),
                    filas, pesos=(9, 9, 14, 11, 41, 16),
                    total=(f'Total: {plural(len(filas), "registro", "registros")} · ensayos con seguimiento en el '
                           f'período: {cifra(con_seguimiento)} de {cifra(len(ciclos))}'),
                    vacio='No hay seguimientos ni mediciones de los ensayos en el período.')


def _resultado_y_limitaciones(detalle):
    """El resultado y sus limitaciones, que la evidencia guarda juntos en un solo campo.

    Se separan cuando el texto las anuncia con «Limitaciones:»; si no, la columna lo dice.
    """
    resultado = ' '.join(str(detalle.get('resultado') or '').split())
    corte = resultado.lower().find('limitaciones:')
    if corte < 0:
        return resultado, 'No se registran aparte'
    return resultado[:corte].rstrip(' .;,') + '.', resultado[corte + len('limitaciones:'):].strip()


def _tabla_resultados(contexto, ciclos):
    from apps.centros_experimentales.operacion.models.centros import CicloProductivo

    evidencias = [e for e in evidencias_de_gestion(contexto.unidad, 'ENSAYOS', contexto.inicio, contexto.fin)
                  if _detalle(e).get('subtipo') == 'ensayo']
    # Un resultado puede ser de un ensayo que cerró antes del período: se reconoce por su marca.
    ensayos = {ciclo.pk for ciclo in ciclos}
    otros = {_detalle(e).get('ciclo_id') for e in evidencias} - ensayos - {None}
    if otros:
        ensayos |= set(CicloProductivo.objects.filter(pk__in=[pk for pk in otros if isinstance(pk, int)],
                                                      eje__unidad=contexto.unidad, es_ensayo=True)
                       .values_list('pk', flat=True))
    filas = []
    for evidencia in evidencias:
        detalle = _detalle(evidencia)
        if detalle.get('ciclo_id') not in ensayos:
            continue
        resultado, limitaciones = _resultado_y_limitaciones(detalle)
        filas.append([
            codigo_de_ensayo(detalle['ciclo_id']),
            par(texto(resultado, 260), f'{texto(evidencia.codigo, 40)} · {fecha(evidencia.fecha)}'),
            texto(limitaciones, 200),
            par(_respaldo(evidencia), verificacion(evidencia)),
            # La evidencia de investigación no guarda de qué ensayo salió.
            '—',
        ])
    pie = f'Total: {plural(len(filas), "resultado", "resultados")}'
    if len(evidencias) > len(filas):
        pie += (' · evidencias de ciclos que no están marcados como ensayo, que no se listan: '
                f'{cifra(len(evidencias) - len(filas))}')
    return Registro('Resultados del ensayo',
                    ('Ensayo', 'Resultado', 'Limitaciones', 'Respaldo', 'Producto de investigación'),
                    filas, pesos=(9, 42, 24, 12, 13), total=pie,
                    vacio='No hay resultados de ensayos documentados en el período.')


def ensayos(contexto):
    """Anexo de ensayos y parcelas experimentales (sección 5.3).

    Solo los ciclos marcados como ensayo: su diseño, el seguimiento del período y los
    resultados documentados. La producción del centro va en su propio anexo.
    """
    from apps.gestion_unidades.presentation.reportes_perfiles import ciclos_del_periodo

    ciclos = ciclos_del_periodo(contexto.unidad, contexto.inicio, contexto.fin, ensayos=True)
    return [_tabla_ensayos(ciclos, _revisiones(contexto, 'ENSAYOS')), _tabla_seguimiento(ciclos),
            _tabla_resultados(contexto, ciclos)]


# -- centro experimental: producción agropecuaria (5.4) ----------------------------------

def _tabla_ciclos(ciclos, obtenido):
    filas = []
    for ciclo in ciclos:
        medida = ciclo.unidad_medida
        total, del_periodo = obtenido[ciclo.pk]
        filas.append([
            texto(ciclo.nombre, 90),
            _corto(ciclo.get_tipo_display()),
            par(texto(ciclo.eje.titulo, 50), texto(ciclo.rubro, 50)),
            _area_de(ciclo),
            par(fecha(ciclo.inicio), f'previsto {fecha(ciclo.fin_previsto)}'
                + (f' · real {fecha(ciclo.fin)}' if ciclo.fin else '')),
            par(_cantidad(ciclo.meta, medida), texto(ciclo.referencia, 70) if ciclo.referencia.strip() else ''),
            par(_cantidad(total, medida), f'en el período {_cantidad(del_periodo, medida)}'),
            ciclo.get_estado_display(),
        ])
    estados = Counter(ciclo.estado for ciclo in ciclos)
    pie = (f'Total: {plural(len(filas), "ciclo", "ciclos")} · planificados: {cifra(estados["planificado"])} · '
           f'en curso: {cifra(estados["en_curso"])} · cerrados: {cifra(estados["cerrado"])}')
    return Registro('Ciclos productivos',
                    ('Ciclo', 'Tipo', 'Eje / rubro', 'Área', 'Inicio / fin', 'Meta', 'Obtenido', 'Estado'),
                    filas, pesos=(20, 11, 14, 12, 13, 13, 10, 7), total=pie,
                    vacio='No hay ciclos productivos en el período.')


def _registros_de(ciclos, manejo):
    """Los registros del período de todos los ciclos, por fecha: los de manejo o los que mueven producto."""
    from apps.gestion_unidades.presentation.reportes_perfiles import MOVIMIENTOS_DE_PRODUCCION

    registros = [(registro, ciclo) for ciclo in ciclos for registro in ciclo.registros_del_periodo
                 if (registro.tipo not in MOVIMIENTOS_DE_PRODUCCION) == manejo]
    return sorted(registros, key=lambda pareja: (pareja[0].fecha, pareja[0].pk))


def _tabla_manejo(ciclos):
    registros = _registros_de(ciclos, manejo=True)
    filas = [[
        fecha(registro.fecha),
        texto(ciclo.nombre, 70),
        _corto(registro.get_tipo_display()),
        texto(registro.detalle, 240),
        _cantidad(registro.cantidad, registro.unidad_medida),
        nombre_de(registro.registrado_por),
    ] for registro, ciclo in registros]
    tipos = Counter(registro.tipo for registro, _ciclo in registros)
    pie = (f'Total: {plural(len(filas), "registro", "registros")} · labores: {cifra(tipos["labor"])} · sanidad: '
           f'{cifra(tipos["sanidad"])} · insumos aplicados: {cifra(tipos["insumo"])} · pesajes o conteos: '
           f'{cifra(tipos["pesaje"])} · novedades o pérdidas: {cifra(tipos["novedad"])}')
    return Registro('Labores, sanidad e insumos aplicados',
                    ('Fecha', 'Ciclo', 'Registro', 'Detalle', 'Cantidad', 'Registrado por'),
                    filas, pesos=(9, 21, 12, 32, 11, 15), total=pie,
                    vacio='No hay labores, tratamientos ni insumos aplicados registrados en el período.')


def _tabla_movimientos(ciclos):
    registros = _registros_de(ciclos, manejo=False)
    filas = [[
        fecha(registro.fecha),
        texto(ciclo.nombre, 70),
        _corto(registro.get_tipo_display()),
        _cantidad(registro.cantidad, registro.unidad_medida),
        par(_corto(registro.get_destino_display()) if registro.destino else '—',
            texto(registro.detalle, 120) if registro.detalle.strip() else ''),
        nombre_de(registro.registrado_por),
    ] for registro, ciclo in registros]
    tipos = Counter(registro.tipo for registro, _ciclo in registros)
    pie = (f'Total: {plural(len(filas), "movimiento", "movimientos")} · cosechas: {cifra(tipos["cosecha"])} · '
           f'ordeños: {cifra(tipos["ordeno"])} · posturas: {cifra(tipos["postura"])} · salidas: '
           f'{cifra(tipos["salida"])} · entregas: {cifra(tipos["entrega"])}')
    return Registro('Producción obtenida y salidas',
                    ('Fecha', 'Ciclo', 'Movimiento', 'Cantidad', 'Destino', 'Registrado por'),
                    filas, pesos=(9, 25, 14, 12, 24, 16), total=pie,
                    vacio='No hay cosechas, ordeños, posturas, salidas ni entregas registradas en el período.')


def _novedades_de(ciclo):
    """Salidas y novedades del período en un hato o lote: el resumen y, debajo, lo que se anotó."""
    salidas = [r for r in ciclo.registros_del_periodo if r.tipo == 'salida']
    novedades = [r for r in ciclo.registros_del_periodo if r.tipo == 'novedad']
    partes = []
    if salidas:
        animales = sum((r.cantidad or 0 for r in salidas if r.unidad_medida == 'animales'), Decimal(0))
        partes.append(f'Salidas: {plural(animales, "animal", "animales")}' if animales
                      else f'Salidas: {plural(len(salidas), "registro", "registros")}')
    if novedades:
        partes.append(f'Novedades o pérdidas: {cifra(len(novedades))}')
    notas = '; '.join(f'{fecha(r.fecha, "%d/%m")} {r.detalle.strip()}' for r in (*salidas, *novedades)
                      if r.detalle.strip())
    return par(' · '.join(partes) or 'Sin novedades', texto(notas, 220) if notas else '')


def _tabla_animales(ciclos, corte):
    from apps.centros_experimentales.operacion.models.centros import RegistroProduccion

    hatos = [ciclo for ciclo in ciclos if ciclo.tipo in CICLOS_CON_ANIMALES]
    conteos, tratamientos = {}, defaultdict(list)
    # El último conteo y los últimos tratamientos pueden ser anteriores al período.
    for registro in (RegistroProduccion.objects.filter(ciclo__in=hatos, fecha__lte=corte,
                                                       tipo__in=('pesaje', 'sanidad'))
                     .order_by('-fecha', '-pk')):
        if registro.tipo == 'sanidad':
            if len(tratamientos[registro.ciclo_id]) < TRATAMIENTOS_RECIENTES:
                tratamientos[registro.ciclo_id].append(registro)
        elif registro.unidad_medida == 'animales' and registro.cantidad is not None:
            conteos.setdefault(registro.ciclo_id, registro)
    filas = []
    for ciclo in hatos:
        conteo = conteos.get(ciclo.pk)
        filas.append([
            texto(ciclo.nombre, 90),
            texto(ciclo.rubro, 60),
            par(f'{cifra(ciclo.animales)} al inicio' if ciclo.animales is not None else 'Sin registrar al inicio',
                f'último conteo: {_numero(conteo.cantidad)} ({fecha(conteo.fecha)})' if conteo
                else 'sin conteos registrados'),
            _novedades_de(ciclo),
            texto('; '.join(f'{fecha(r.fecha)} {r.detalle.strip() or "sin detalle"}'
                            for r in tratamientos[ciclo.pk]), 240),
        ])
    return Registro('Animales al corte',
                    ('Hato o lote', 'Rubro', 'Animales', 'Novedades del período', 'Sanidad'),
                    filas, pesos=(22, 12, 16, 25, 25),
                    total=f'Total: {plural(len(filas), "hato o lote", "hatos o lotes")}',
                    vacio='No hay hatos ni lotes de animales en el período.')


def produccion_agropecuaria(contexto):
    """Anexo de producción agropecuaria del centro experimental (sección 5.4).

    Los ciclos que no son ensayos: su meta y lo obtenido, el manejo del período (labores,
    sanidad, insumos, pesajes y novedades), la producción y sus salidas, y los animales al corte.
    """
    from apps.gestion_unidades.presentation.reportes_perfiles import ciclos_del_periodo, produccion_de_los_ciclos

    ciclos = ciclos_del_periodo(contexto.unidad, contexto.inicio, contexto.fin, ensayos=False)
    obtenido = produccion_de_los_ciclos(ciclos, contexto.inicio, contexto.corte)
    return [_tabla_ciclos(ciclos, obtenido), _tabla_manejo(ciclos), _tabla_movimientos(ciclos),
            _tabla_animales(ciclos, contexto.corte)]


# -- observatorio: datos (5.5) -----------------------------------------------------------

def _indicadores(contexto):
    """Las series del observatorio con su período más reciente y su última incorporación al corte."""
    from django.db.models import OuterRef, Subquery
    from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio, ValorIndicador

    al_corte = ValorIndicador.objects.filter(indicador=OuterRef('pk'), registrado__date__lte=contexto.corte)
    return list(IndicadorObservatorio.objects.filter(unidad=contexto.unidad).select_related('fuente_datos')
                .annotate(periodo_reciente=Subquery(al_corte.order_by('-fecha', '-pk').values('periodo')[:1]),
                          ultima_incorporacion=Subquery(al_corte.order_by('-registrado').values('registrado')[:1]))
                .order_by('orden', 'nombre', 'pk'))


def _datos_incorporados(contexto):
    """{indicador: sus valores incorporados en el semestre}, por fecha de referencia y territorio."""
    from apps.observatorios.operacion.models.observatorios import ValorIndicador

    por_indicador = defaultdict(list)
    for valor in (ValorIndicador.objects.filter(indicador__unidad=contexto.unidad,
                                                registrado__date__range=(contexto.inicio, contexto.fin))
                  .order_by('indicador_id', 'fecha', 'territorio', 'pk')):
        por_indicador[valor.indicador_id].append(valor)
    return por_indicador


def _tabla_fichas(indicadores):
    filas = [[
        par(texto(indicador.codigo), texto(indicador.nombre + ('' if indicador.publicado else ' (no publicado)'), 90)),
        texto(indicador.definicion, 240),
        texto(indicador.formula, 160),
        texto(indicador.unidad_medida, 40),
        par(texto(indicador.desagregacion, 80), texto(indicador.territorio_principal, 50)),
        indicador.get_periodicidad_display(),
        Par(_con_enlace(texto(indicador.fuente, 120), indicador.url_fuente), indicador.get_tipo_fuente_display()),
        texto(indicador.limitaciones, 240),
    ] for indicador in indicadores]
    publicados = sum(indicador.publicado for indicador in indicadores)
    return Registro('Ficha metodológica de las series',
                    ('Código / indicador', 'Definición', 'Fórmula o método', 'Unidad', 'Desagregación / territorio',
                     'Periodicidad', 'Fuente', 'Limitaciones'),
                    filas, pesos=(17, 17, 11, 8, 11, 8, 14, 14),
                    total=f'Total: {plural(len(filas), "serie", "series")} · publicadas: {cifra(publicados)}',
                    vacio='El observatorio no tiene series registradas.')


def _tabla_actualizacion(indicadores, incorporados, revisiones):
    filas = []
    provisionales = 0
    for indicador in indicadores:
        valores = incorporados.get(indicador.pk, [])
        en_revision = sum(valor.provisional for valor in valores)
        provisionales += en_revision
        filas.append([
            texto(indicador.codigo),
            cifra(len(valores)),
            texto(indicador.periodo_reciente, 30),
            fecha(indicador.ultima_incorporacion),
            cifra(en_revision),
            # Sin datos nuevos no hay nada que revisar en el semestre.
            _revision_tecnica(revisiones.get(indicador.pk)) if valores or indicador.pk in revisiones else '—',
        ])
    actualizadas = sum(bool(incorporados.get(indicador.pk)) for indicador in indicadores)
    pie = (f'Total: {plural(len(filas), "serie", "series")} · con datos incorporados en el semestre: '
           f'{cifra(actualizadas)} · datos incorporados: {cifra(sum(len(v) for v in incorporados.values()))} · '
           f'provisionales: {cifra(provisionales)} · con revisión técnica vigente: '
           f'{cifra(sum(indicador.pk in revisiones for indicador in indicadores))}')
    return Registro('Actualización de las series en el semestre',
                    ('Indicador', 'Datos incorporados', 'Período más reciente', 'Última actualización',
                     'Provisionales', 'Revisión técnica'),
                    filas, pesos=(30, 13, 15, 14, 12, 16), total=pie,
                    vacio='El observatorio no tiene series registradas.')


def _tabla_datos(indicadores, incorporados):
    filas = []
    for indicador in indicadores:
        valores = incorporados.get(indicador.pk)
        if not valores:
            continue
        filas.append(Grupo(' · '.join(parte for parte in (
            indicador.codigo, indicador.nombre, indicador.unidad_medida, plural(len(valores), 'dato', 'datos'))
            if parte)))
        filas += [[
            texto(indicador.codigo),
            texto(valor.periodo, 30),
            fecha(valor.fecha),
            texto(valor.territorio, 60),
            _numero(valor.valor),
            si_no(valor.provisional),
            ORIGENES_DEL_DATO.get(valor.origen, valor.get_origen_display()),
            fecha(valor.registrado),
        ] for valor in valores]
    datos = sum(len(valores) for valores in incorporados.values())
    return Registro('Datos incorporados en el semestre',
                    ('Indicador', 'Período', 'Fecha de referencia', 'Territorio', 'Valor', 'Provisional',
                     'Cómo entró', 'Registrado'),
                    filas, pesos=(24, 10, 12, 18, 12, 8, 8, 8),
                    total=(f'Total: {plural(datos, "dato", "datos")} de '
                           f'{plural(len(incorporados), "serie", "series")}'),
                    vacio='No se incorporaron datos en el semestre.')


def _tabla_fuentes(indicadores):
    # El catálogo de fuentes es común a todos los observatorios: aquí van las de sus series.
    fuentes = sorted({i.fuente_datos for i in indicadores if i.fuente_datos_id},
                     key=lambda fuente: (fuente.institucion, fuente.nombre, fuente.pk))
    filas = [[
        par(texto(fuente.nombre, 110), texto(fuente.institucion, 80)),
        texto(fuente.descripcion, 240),
        _corto(fuente.get_metodo_display()).split(':')[0],
        par(fuente.get_acceso_display(), texto(fuente.licencia, 80) if fuente.licencia.strip() else ''),
        texto(fuente.periodicidad, 60),
        enlace(fuente.url),
    ] for fuente in fuentes]
    sin_fuente = sum(not indicador.fuente_datos_id for indicador in indicadores)
    pie = f'Total: {plural(len(filas), "fuente", "fuentes")}'
    if sin_fuente:
        pie += f' · series sin fuente del catálogo, descritas solo en su ficha: {cifra(sin_fuente)}'
    return Registro('Fuentes de datos',
                    ('Fuente / institución', 'Qué contiene', 'Cómo se obtiene', 'Acceso / licencia', 'Periodicidad',
                     'Dónde está'),
                    filas, pesos=(26, 30, 12, 14, 11, 7), total=pie,
                    vacio='Las series del observatorio no tienen fuentes del catálogo asociadas.')


def datos_observatorio(contexto):
    """Anexo de datos del observatorio (sección 5.5).

    La ficha metodológica de cada serie, su actualización en el semestre, todos los datos
    incorporados (agrupados por indicador) y las fuentes de donde salen.
    """
    indicadores = _indicadores(contexto)
    incorporados = _datos_incorporados(contexto)
    return [_tabla_fichas(indicadores),
            _tabla_actualizacion(indicadores, incorporados, _revisiones(contexto, 'DATOS-ACTUALIZADOS')),
            _tabla_datos(indicadores, incorporados), _tabla_fuentes(indicadores)]


# -- observatorio: publicaciones (5.6) ---------------------------------------------------

def publicaciones_observatorio(contexto):
    """Anexo de publicaciones del observatorio (sección 5.6): el calendario y lo publicado."""
    from django.db.models import Q
    from apps.observatorios.operacion.models.observatorios import PublicacionObservatorio

    periodo = (contexto.inicio, contexto.fin)
    publicaciones = list(PublicacionObservatorio.objects.filter(unidad=contexto.unidad)
                         .filter(Q(fecha_planificada__range=periodo) | Q(fecha_publicada__range=periodo))
                         .prefetch_related('indicadores').order_by('fecha_planificada', 'titulo', 'pk'))
    revisiones = _revisiones(contexto, 'BOLETINES')
    filas = []
    for publicacion in publicaciones:
        publicada = publicacion.estado == 'publicada'
        filas.append([
            texto(publicacion.titulo, 160),
            publicacion.get_tipo_display(),
            texto(publicacion.periodo, 40),
            par(fecha(publicacion.fecha_planificada),
                f'publicada {fecha(publicacion.fecha_publicada)}' if publicacion.fecha_publicada else ''),
            publicacion.get_estado_display(),
            texto(', '.join(indicador.codigo for indicador in publicacion.indicadores.all()), 200),
            # Lo que aún no se publica no tiene qué revisar.
            _revision_tecnica(revisiones.get(publicacion.pk)) if publicada else '—',
            enlace_archivo(publicacion.archivo) if publicacion.archivo else enlace(publicacion.enlace),
        ])
    previstas = [p for p in publicaciones if contexto.inicio <= p.fecha_planificada <= contexto.fin]
    a_tiempo = sum(p.a_tiempo is True for p in publicaciones)
    con_atraso = sum(p.a_tiempo is False for p in publicaciones)
    estados = Counter(p.estado for p in publicaciones)
    pie = (f'Total: {plural(len(filas), "publicación", "publicaciones")} · previstas en el período: '
           f'{cifra(len(previstas))} · publicadas a tiempo: {cifra(a_tiempo)} · publicadas con atraso: '
           f'{cifra(con_atraso)} · pendientes: {cifra(estados["planificada"])}')
    if estados['cancelada']:
        pie += f' · canceladas: {cifra(estados["cancelada"])}'
    return [Registro('Calendario de publicaciones',
                     ('Publicación', 'Tipo', 'Período que cubre', 'Fecha prevista / publicada', 'Estado',
                      'Indicadores', 'Revisión técnica', 'Documento'),
                     filas, pesos=(25, 10, 9, 12, 9, 18, 10, 7), total=pie,
                     vacio='No hay publicaciones previstas ni publicadas en el período.')]


# -- observatorio: socialización (5.7) ---------------------------------------------------

def _revision_del_evento(evidencia, vigentes):
    if evidencia.pk in vigentes:
        return 'Vigente'
    # Una evidencia verificada cuyo origen cambió o que ya se contó no acredita.
    return par('Pendiente', 'Verificación no vigente' if evidencia.estado == 'validado' and not evidencia.demostracion
               else verificacion(evidencia))


def _realizado_en_el_periodo(evidencia, contexto):
    """El evento cuenta en el período en que se realizó, como en el informe; sin fecha propia, vale la del registro."""
    try:
        dia = date.fromisoformat(str(_detalle(evidencia).get('fecha_evento') or ''))
    except ValueError:
        return True
    return contexto.inicio <= dia <= contexto.fin


def socializacion_observatorio(contexto):
    """Anexo de socialización del observatorio (sección 5.7): los eventos realizados.

    Un evento es una evidencia de gestión; las anuladas no se presentan.
    """
    eventos = [e for e in evidencias_de_gestion(contexto.unidad, 'EVENTOS', contexto.inicio, contexto.fin)
               if _detalle(e).get('subtipo') == 'socializacion' and _realizado_en_el_periodo(e, contexto)]
    eventos.sort(key=lambda e: (str(_detalle(e).get('fecha_evento') or e.fecha.isoformat()), e.pk))
    vigentes = {fuente.get('evidencia') for fuente in _fuentes_verificadas(contexto, 'EVENTOS')}
    filas = []
    participantes = 0
    for evidencia in eventos:
        detalle = _detalle(evidencia)
        asistentes = detalle.get('participantes') if isinstance(detalle.get('participantes'), int) else None
        participantes += asistentes or 0
        acta = texto(detalle.get('referencia_acta'), 60) if str(detalle.get('referencia_acta') or '').strip() else ''
        filas.append([
            _fecha_iso(detalle.get('fecha_evento')) or fecha(evidencia.fecha),
            texto(evidencia.titulo, 120),
            # El público no se registra aparte: es el dato de la columna de destinatarios.
            texto(detalle.get('objetivo'), 200),
            # La evidencia no guarda qué publicaciones se difundieron.
            texto(detalle.get('productos_difundidos'), 160),
            texto(detalle.get('beneficiario'), 120),
            cifra(asistentes),
            texto(detalle.get('resultado'), 220),
            par(_respaldo(evidencia), acta),
            _revision_del_evento(evidencia, vigentes),
        ])
    pie = (f'Total: {plural(len(filas), "evento", "eventos")} · participantes comprobados: {cifra(participantes)} · '
           f'con revisión técnica vigente: {cifra(sum(e.pk in vigentes for e in eventos))}')
    return [Registro('Eventos realizados',
                     ('Fecha', 'Actividad', 'Propósito / público', 'Productos difundidos', 'Destinatarios',
                      'Participantes comprobados', 'Resultado', 'Acta', 'Revisión técnica'),
                     filas, pesos=(8, 14, 16, 10, 12, 9, 15, 8, 8), total=pie,
                     vacio='No hay eventos de socialización registrados en el período.')]
