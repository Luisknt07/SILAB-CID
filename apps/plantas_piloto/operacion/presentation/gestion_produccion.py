"""Producción en el panel: productos, recetas, órdenes, lotes y salidas.

Los operadores siguen el contrato del panel: reciben la solicitud y la
unidad, devuelven ``(objeto, mensaje, creado)`` y lanzan ``ValidationError``
con el texto que verá la persona. El despachador de ``gestion.py`` los
registra en la bitácora y en la auditoría como a los demás.
"""

import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from itertools import islice

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time

from apps.finanzas.models.ventas import Cliente
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, InsumoReceta, LoteProducto, MovimientoProducto, OrdenProduccion, Producto, Receta, SalidaReceta
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import ESTADOS_OCUPAN_AGENDA

from apps.plantas_piloto.operacion.presentation.calidad import plan_para_orden
from apps.finanzas.presentation.costos import costo_estandar, costo_real, costos_de_entradas
from apps.plantas_piloto.operacion.presentation.despacho import TIPOS_CON_DESPACHO, cliente_de_la_venta, contexto_clientes, operar_cliente, validar_cadena_de_frio
from apps.plantas_piloto.operacion.presentation.sesiones_erp import exigir_misma_sesion, sesion_de
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.plantas_piloto.operacion.presentation.diagramas import diagramas_de_ficha
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa, cronograma, cursograma_analitico, datos_de_receta, diagrama_flujo_svg, guia_desde_proceso, resumen_proceso
from apps.reservas.presentation.availability import reservation_unit_ids
from apps.reservas.presentation.proceso import seleccion_por_proceso


# ------------------------------------------------------------------ ayudas
def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or "").strip()
    return valor[:maximo] if maximo else valor


def _booleano(request, nombre):
    return (request.POST.get(nombre) or "").strip().lower() in {"on", "true", "1", "si", "sí"}


def _decimal(valor, etiqueta, *, minimo=Decimal("0"), permitir_vacio=False):
    texto = str(valor or "").strip().replace(",", ".")
    if not texto:
        if permitir_vacio:
            return None
        raise ValidationError(f"{etiqueta} es obligatorio.")
    try:
        numero = Decimal(texto)
    except InvalidOperation as error:
        raise ValidationError(f"{etiqueta} debe ser un número.") from error
    if numero < minimo:
        raise ValidationError(f"{etiqueta} no puede ser menor que {minimo}.")
    return numero


def _entero(valor, etiqueta):
    texto = str(valor or "0").strip()
    try:
        numero = int(texto)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{etiqueta} debe ser un número entero.") from error
    if numero < 0:
        raise ValidationError(f"{etiqueta} no puede ser negativo.")
    return numero


def _fecha(valor, etiqueta):
    fecha = parse_date((valor or "").strip())
    if fecha is None:
        raise ValidationError(f"Registra {etiqueta} con una fecha válida.")
    return fecha


def _hora(valor):
    texto = (valor or "").strip()
    if not texto:
        return None
    hora = parse_time(texto)
    if hora is None:
        raise ValidationError("Registra las horas de la corrida con un formato válido.")
    return hora


def _equipos_de_unidad(unidad):
    return UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()


# --------------------------------------------------------------- productos
def operar_producto(request, unidad):
    registro_id = _texto(request, "registro_id")
    if registro_id:
        objeto = get_object_or_404(Producto.objects.select_for_update(), pk=registro_id, unidad=unidad)
        creado = False
    else:
        objeto = Producto(unidad=unidad)
        creado = True
    if _texto(request, "accion") == "desactivar":
        objeto.activo = False
        objeto.publico = False
        objeto.save(update_fields=["activo", "publico", "actualizado_en"])
        return objeto, "Producto desactivado", False
    objeto.codigo = _texto(request, "codigo", 50)
    objeto.nombre = _texto(request, "nombre", 200)
    objeto.tipo = _texto(request, "tipo") or "terminado"
    familia_id = _texto(request, "familia_id")
    objeto.familia = (
        get_object_or_404(FamiliaProducto, pk=familia_id, unidad=unidad, activa=True)
        if familia_id else None
    )
    if objeto.tipo not in dict(Producto.TIPOS):
        raise ValidationError("Indica si es producto terminado, intermedio, subproducto o residuo.")
    objeto.unidad_medida = _texto(request, "unidad_medida", 50)
    objeto.presentacion = _texto(request, "presentacion", 120)
    objeto.precio_venta = _decimal(request.POST.get("precio_venta") or "0", "El precio de venta")
    objeto.vida_util_dias = _entero(request.POST.get("vida_util_dias"), "La vida útil")
    objeto.requiere_frio = _booleano(request, "requiere_frio")
    objeto.temperatura_maxima = (
        _decimal(request.POST.get("temperatura_maxima"), "La temperatura máxima", minimo=Decimal("-40"),
                 permitir_vacio=True)
        if objeto.requiere_frio else None
    )
    objeto.descripcion = _texto(request, "descripcion")
    objeto.publico = _booleano(request, "publico") and objeto.tipo != "residuo"
    objeto.activo = _booleano(request, "activo")
    objeto.full_clean()
    objeto.save()
    objeto.recetas.update(familia=objeto.familia)
    EtapaReceta.objects.filter(receta__producto=objeto).update(familia=objeto.familia)
    objeto.planes_calidad.update(familia=objeto.familia)
    return objeto, "Producto creado" if creado else "Producto actualizado", creado


# ----------------------------------------------------------------- recetas
def _lineas(request, prefijo, campo_id):
    """Filas repetidas del formulario: (id, cantidad, extra, etapa) sin las vacías."""
    ids = request.POST.getlist(f"{prefijo}_{campo_id}")
    cantidades = request.POST.getlist(f"{prefijo}_cantidad")
    extras = request.POST.getlist(f"{prefijo}_obligatorio")
    etapas = request.POST.getlist(f"{prefijo}_etapa")
    formas = request.POST.getlist(f"{prefijo}_forma_parte" if prefijo == "insumo" else "salida_externa_al_flujo")
    lineas = []
    for indice, identificador in enumerate(ids):
        identificador = (identificador or "").strip()
        cantidad = cantidades[indice] if indice < len(cantidades) else ""
        extra = extras[indice] if indice < len(extras) else "si"
        etapa = (etapas[indice] if indice < len(etapas) else "").strip()
        forma = (formas[indice] if indice < len(formas) else ("si" if prefijo == "insumo" else "no")).strip()
        if not str(cantidad).strip():
            # Una fila sin cantidad es una fila vacía, no un error.
            continue
        if not identificador:
            raise ValidationError("Cada fila de la receta necesita un elemento seleccionado.")
        lineas.append((identificador, cantidad, extra, etapa, forma))
    return lineas


def _guardar_etapas(request, receta, unidad):
    """Las filas de etapas del formulario, en orden; devuelve {orden: etapa}."""
    if "etapa_nombre" not in request.POST:
        # El formulario no trajo etapas: se conservan las que hay.
        return {etapa.orden: etapa for etapa in receta.etapas.all()}

    def lista(nombre):
        return request.POST.getlist(nombre)

    def valor(coleccion, indice, predeterminado=""):
        return coleccion[indice] if indice < len(coleccion) else predeterminado

    nombres = lista("etapa_nombre")
    tipos, equipos_ids, espacios_ids = lista("etapa_tipo"), lista("etapa_equipo"), lista("etapa_espacio")
    duraciones, esperas, personas = lista("etapa_duracion"), lista("etapa_espera"), lista("etapa_personas")
    rendimientos, distancias, criticos = lista("etapa_rendimiento"), lista("etapa_distancia"), lista("etapa_punto_critico")
    parametros, limites, instrucciones = lista("etapa_parametro"), lista("etapa_limite"), lista("etapa_instrucciones")
    catalogo = {
        str(equipo.pk): equipo
        for equipo in EquiposServicios.objects.filter(
            pk__in=_equipos_de_unidad(unidad).values_list("equipo_id", flat=True)
        )
    }
    espacios = {str(espacio.pk): espacio for espacio in EspacioReservable.objects.filter(unidad=unidad)}
    etapas, orden = {}, 0
    for indice, nombre in enumerate(nombres):
        nombre = (nombre or "").strip()
        if not nombre:
            continue
        orden += 1
        tipo = (valor(tipos, indice) or "operacion").strip()
        if tipo not in dict(EtapaReceta.TIPOS):
            raise ValidationError(f"La etapa {orden} necesita un tipo válido.")
        equipo_id = (valor(equipos_ids, indice) or "").strip()
        espacio_id = (valor(espacios_ids, indice) or "").strip()
        if equipo_id and equipo_id not in catalogo:
            raise ValidationError(f"La etapa {orden} usa un equipo que no pertenece a esta unidad.")
        if espacio_id and espacio_id not in espacios:
            raise ValidationError(f"La etapa {orden} usa un área que no pertenece a esta unidad.")
        rendimiento = _decimal(valor(rendimientos, indice, "100") or "100", f"El rendimiento de la etapa {orden}")
        if rendimiento > 100:
            raise ValidationError(f"El rendimiento de la etapa {orden} no puede superar el 100 %.")
        etapa, _ = EtapaReceta.objects.update_or_create(
            receta=receta,
            orden=orden,
            defaults={
                "nombre": nombre[:160],
                "familia": receta.familia,
                "tipo": tipo,
                "equipo": catalogo.get(equipo_id),
                "espacio": espacios.get(espacio_id),
                "duracion_min": _entero(valor(duraciones, indice, "0") or "0", f"El trabajo de la etapa {orden}"),
                "espera_min": _entero(valor(esperas, indice, "0") or "0", f"La espera de la etapa {orden}"),
                "personas": _entero(valor(personas, indice, "1") or "0", f"Las personas de la etapa {orden}"),
                "rendimiento_pct": rendimiento,
                "distancia_m": _decimal(valor(distancias, indice, "0") or "0", f"La distancia de la etapa {orden}"),
                # «si» = PCC (inocuidad); «pc» = punto de control de calidad.
                "punto_critico": (valor(criticos, indice, "no") or "no").strip().lower() == "si",
                "punto_control": (valor(criticos, indice, "no") or "no").strip().lower() == "pc",
                "parametro": (valor(parametros, indice) or "").strip()[:160],
                "limite": (valor(limites, indice) or "").strip()[:120],
                "instrucciones": (valor(instrucciones, indice) or "").strip(),
            },
        )
        etapa.full_clean()
        etapas[orden] = etapa
    receta.etapas.filter(orden__gt=orden).delete()
    return etapas


def _etapa_de(etapas, numero, nombre):
    """La etapa a la que apunta una fila de insumo o salida, o ninguna."""
    if not numero:
        return None
    try:
        orden = int(numero)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{nombre} apunta a una etapa inválida.") from error
    if orden not in etapas:
        raise ValidationError(f"{nombre} apunta a la etapa {orden}, que no existe en la receta.")
    return etapas[orden]


def _codigo_de_version(original):
    """El código libre siguiente para una versión del proceso: QUESO-100-V1, -V2…"""
    base, numero = original.codigo[:44], 1
    while Receta.objects.filter(codigo=f"{base}-V{numero}").exists():
        numero += 1
    return f"{base}-V{numero}"


def operar_receta(request, unidad):
    registro_id = _texto(request, "registro_id")
    original = None
    if registro_id:
        objeto = get_object_or_404(Receta.objects.select_for_update(), pk=registro_id, unidad=unidad)
        creado = False
        if _texto(request, "guardar_como") == "version" and _texto(request, "accion") != "desactivar":
            # Lo editado se guarda como una versión nueva del proceso; el original no cambia.
            original = objeto
            objeto = Receta(unidad=unidad, origen="derivado", derivado_de=original)
            creado = True
    else:
        objeto = Receta(unidad=unidad)
        creado = True
    if _texto(request, "accion") == "desactivar":
        objeto.activa = False
        objeto.save(update_fields=["activa", "actualizado_en"])
        return objeto, "Receta desactivada", False
    objeto.producto = get_object_or_404(
        Producto, pk=request.POST.get("producto_id") or None, unidad=unidad, activo=True
    )
    objeto.familia = objeto.producto.familia
    objeto.codigo = _texto(request, "codigo", 50)
    objeto.nombre = _texto(request, "nombre", 200)
    objeto.cantidad_base = _decimal(request.POST.get("cantidad_base"), "La cantidad base", minimo=Decimal("0.001"))
    objeto.unidad_base = _texto(request, "unidad_base", 60)
    objeto.rendimiento_esperado = _decimal(
        request.POST.get("rendimiento_esperado"), "El producto esperado", minimo=Decimal("0.001")
    )
    if original is not None:
        if objeto.codigo == original.codigo:
            objeto.codigo = _codigo_de_version(original)
        if objeto.nombre == original.nombre:
            objeto.nombre = f"{original.nombre} · versión de la planta"[:200]
    elif _texto(request, "origen") in dict(Receta.ORIGENES):
        objeto.origen = _texto(request, "origen")
    objeto.duracion_horas = _decimal(request.POST.get("duracion_horas") or "0", "La duración")
    responsable_id = _texto(request, "responsable_id")
    objeto.responsable = (
        get_object_or_404(ResponsableUnidad, pk=responsable_id, unidad=unidad, activo=True) if responsable_id else None
    )
    objeto.instrucciones = _texto(request, "instrucciones")
    objeto.activa = _booleano(request, "activa")
    objeto.full_clean()
    objeto.save()
    if "software" in request.POST or not creado:
        ids = {int(valor) for valor in request.POST.getlist("software") if str(valor).isdigit()}
        programas = list(SoftwareDisponible.objects.filter(unidad=unidad, pk__in=ids))
        if len(programas) != len(ids):
            raise ValidationError("Solo puedes ligar al proceso software de esta unidad.")
        objeto.software.set(programas)
    etapas = _guardar_etapas(request, objeto, unidad)

    insumos = _lineas(request, "insumo", "consumible")
    if not insumos:
        raise ValidationError("Una receta necesita al menos un insumo.")
    consumibles = {
        str(item.pk): item
        for item in Consumible.objects.filter(unidad=unidad, activo=True)
    }
    vistos = set()
    for identificador, cantidad, obligatorio, numero_etapa, forma_parte in insumos:
        consumible = consumibles.get(identificador)
        if consumible is None:
            raise ValidationError("Solo entran en la receta los insumos activos de esta unidad.")
        if identificador in vistos:
            raise ValidationError(f"{consumible.nombre} aparece dos veces en la receta.")
        vistos.add(identificador)
        linea, _ = InsumoReceta.objects.update_or_create(
            receta=objeto,
            consumible=consumible,
            defaults={
                "cantidad": _decimal(cantidad, f"La cantidad de {consumible.nombre}", minimo=Decimal("0.001")),
                "obligatorio": str(obligatorio).strip().lower() != "no",
                "etapa": _etapa_de(etapas, numero_etapa, consumible.nombre),
                "forma_parte": forma_parte if forma_parte in dict(InsumoReceta.FORMA_PARTE) else "si",
            },
        )
        linea.full_clean()
    objeto.insumos.exclude(consumible_id__in=[int(v) for v in vistos]).delete()

    salidas = _lineas(request, "salida", "producto")
    productos = {
        str(item.pk): item
        for item in Producto.objects.filter(unidad=unidad, activo=True).exclude(pk=objeto.producto_id)
    }
    vistas = set()
    for identificador, cantidad, _extra, numero_etapa, externa in salidas:
        if externa not in ("si", "no"):
            raise ValidationError("Indica si la salida es externa al flujo.")
        producto = productos.get(identificador)
        if producto is None:
            raise ValidationError("Las salidas son productos activos de esta unidad distintos del principal.")
        if identificador in vistas:
            raise ValidationError(f"{producto.nombre} aparece dos veces en las salidas.")
        vistas.add(identificador)
        linea, _ = SalidaReceta.objects.update_or_create(
            receta=objeto,
            producto=producto,
            defaults={
                "cantidad": _decimal(cantidad, f"La cantidad de {producto.nombre}", minimo=Decimal("0.001")),
                "etapa": _etapa_de(etapas, numero_etapa, producto.nombre),
                "externa_al_flujo": externa == "si",
            },
        )
        linea.full_clean()
    objeto.salidas.exclude(producto_id__in=[int(v) for v in vistas]).delete()
    if original is not None:
        return objeto, f"Versión {objeto.codigo} creada; «{original.nombre}» no cambió", creado
    return objeto, "Receta creada" if creado else "Receta actualizada", creado


# ----------------------------------------------------------------- órdenes
def _reservas_en_conflicto(orden, equipos):
    """Reservas vigentes que ya ocupan la línea o los equipos de la corrida."""
    reservas = Reserva.objects.filter(
        laboratorio=orden.unidad,
        fecha__range=(orden.fecha_inicio, orden.fecha_fin),
        estado__in=ESTADOS_OCUPAN_AGENDA,
    ).prefetch_related("espacios_solicitados")
    if orden.reserva_id:
        reservas = reservas.exclude(pk=orden.reserva_id)
    if orden.hora_inicio and orden.hora_fin:
        reservas = reservas.filter(hora_inicio__lt=orden.hora_fin, hora_fin__gt=orden.hora_inicio)
    equipos_ids = {equipo.pk for equipo in equipos}
    conflictos = []
    for reserva in reservas:
        ocupa_linea = orden.linea_id and any(
            espacio.pk == orden.linea_id for espacio in reserva.espacios_solicitados.all()
        )
        ocupa_equipo = bool(equipos_ids & reservation_unit_ids(reserva))
        if ocupa_linea or ocupa_equipo:
            conflictos.append(reserva.codigo_reserva or f"#{reserva.pk}")
    return conflictos


def _cerrar_orden(request, orden):
    consumos = [
        {
            "consumible_id": item["consumible"].pk,
            "lote_id": _texto(request, f"consumo_lote_{item['consumible'].pk}") or None,
            "cantidad": request.POST.get(f"consumo_cantidad_{item['consumible'].pk}") or "0",
        }
        for item in orden.insumos_planificados()
    ]
    salidas = [
        {
            "producto_id": item["producto"].pk,
            "cantidad": request.POST.get(f"salida_cantidad_{item['producto'].pk}") or "0",
        }
        for item in orden.salidas_planificadas()
    ]
    for consumo in consumos:
        _decimal(consumo["cantidad"], "La cantidad consumida")
    for salida in salidas:
        _decimal(salida["cantidad"], "La cantidad obtenida")
    orden.cerrar(
        usuario=request.user,
        consumos=consumos,
        salidas=salidas,
        observaciones=_texto(request, "observaciones_cierre"),
        ubicacion=_texto(request, "ubicacion_lotes", 160),
    )
    lotes = orden.lotes.count()
    return orden, f"Corrida terminada con {lotes} lote{'s' if lotes != 1 else ''} de producto", False


def operar_orden_produccion(request, unidad):
    registro_id = _texto(request, "registro_id")
    if registro_id:
        objeto = get_object_or_404(
            OrdenProduccion.objects.select_for_update(), pk=registro_id, unidad=unidad
        )
        exigir_misma_sesion(objeto.sesion_id, request)
        creado = False
    else:
        objeto = OrdenProduccion(unidad=unidad, creada_por=request.user, sesion=sesion_de(request))
        creado = True
    accion = _texto(request, "accion")
    avance = _texto(request, "accion_orden")
    if accion == "desactivar":
        if creado:
            raise ValidationError("Selecciona la orden que quieres cancelar.")
        objeto.cancelar(motivo=_texto(request, "observacion"))
        return objeto, "Orden cancelada", False
    if avance == "iniciar":
        if creado:
            raise ValidationError("Selecciona la orden que vas a iniciar.")
        objeto.iniciar()
        objeto.sincronizar_bloqueo(request.user)
        return objeto, "Corrida iniciada", False
    if avance == "cerrar":
        if creado:
            raise ValidationError("Selecciona la orden que vas a cerrar.")
        return _cerrar_orden(request, objeto)
    if not creado and not objeto.abierta:
        raise ValidationError("Una orden terminada o cancelada no se edita; planifica otra.")

    objeto.receta = get_object_or_404(
        Receta, pk=request.POST.get("receta_id") or None, unidad=unidad, activa=True
    )
    objeto.factor = _decimal(request.POST.get("factor") or "1", "El número de corridas base", minimo=Decimal("0.001"))
    objeto.planificar_cantidades()
    objeto.fecha_inicio = _fecha(request.POST.get("fecha_inicio"), "el inicio de la corrida")
    objeto.fecha_fin = _fecha(request.POST.get("fecha_fin") or request.POST.get("fecha_inicio"), "el fin de la corrida")
    objeto.hora_inicio = _hora(request.POST.get("hora_inicio"))
    objeto.hora_fin = _hora(request.POST.get("hora_fin"))
    linea_id = _texto(request, "linea_id")
    objeto.linea = (
        get_object_or_404(EspacioReservable, pk=linea_id, unidad=unidad, activo=True) if linea_id else None
    )
    responsable_id = _texto(request, "responsable_id")
    objeto.responsable = (
        get_object_or_404(ResponsableUnidad, pk=responsable_id, unidad=unidad, activo=True)
        if responsable_id
        else None
    )
    objeto.origen = _texto(request, "origen") or "propia"
    if objeto.origen not in dict(OrdenProduccion.ORIGENES):
        raise ValidationError("Indica el origen de la corrida.")
    reserva_id = _texto(request, "reserva_id")
    objeto.reserva = get_object_or_404(Reserva, pk=reserva_id, laboratorio=unidad) if reserva_id else None
    objeto.observaciones = _texto(request, "observaciones")
    equipos_ids = {int(valor) for valor in request.POST.getlist("equipos") if str(valor).isdigit()}
    equipos = list(_equipos_de_unidad(unidad).filter(pk__in=equipos_ids)) if equipos_ids else []
    if len(equipos) != len(equipos_ids):
        raise ValidationError("Solo puedes asignar equipos de esta unidad a la corrida.")
    objeto.full_clean()
    # Una corrida de sesión no ocupa la agenda real: no choca con sus reservas.
    conflictos = [] if objeto.sesion_id else _reservas_en_conflicto(objeto, equipos)
    if conflictos:
        raise ValidationError(
            "La línea o los equipos ya tienen reservas vigentes esos días: "
            + ", ".join(conflictos)
            + ". Reprograma la corrida o resuelve esas reservas antes."
        )
    objeto.save()
    objeto.equipos.set(equipos)
    objeto.sincronizar_bloqueo(request.user)
    return objeto, "Orden planificada" if creado else "Orden actualizada", creado


# ------------------------------------------------------------------- lotes
def operar_lote_producto(request, unidad):
    registro_id = _texto(request, "registro_id")
    if not registro_id:
        raise ValidationError("Los lotes de producto nacen al cerrar una orden de producción.")
    if _texto(request, "accion") == "desactivar":
        raise ValidationError("Un lote se retira con una baja o con el rechazo del control de calidad.")
    objeto = get_object_or_404(LoteProducto.objects.select_for_update(), pk=registro_id, unidad=unidad)
    exigir_misma_sesion(objeto.orden.sesion_id if objeto.orden_id else None, request)
    objeto.ubicacion = _texto(request, "ubicacion", 160)
    observaciones = _texto(request, "observaciones")
    if observaciones:
        objeto.observaciones = observaciones
    objeto.full_clean()
    objeto.save()
    decision = _texto(request, "decision_calidad") or "mantener"
    if decision == "aprobar":
        objeto.aprobar_calidad()
        return objeto, "Lote aprobado y disponible", False
    if decision == "rechazar":
        objeto.rechazar_calidad(usuario=request.user, motivo=observaciones)
        return objeto, "Lote rechazado y retirado", False
    if decision != "mantener":
        raise ValidationError("Indica la decisión del control de calidad.")
    return objeto, "Lote actualizado", False


# -------------------------------------------------------------- movimientos
def operar_movimiento_producto(request, unidad):
    if _texto(request, "registro_id") or _texto(request, "accion") == "desactivar":
        raise ValidationError("Una salida registrada no se edita ni se borra; el lote conserva su historia.")
    lote = get_object_or_404(LoteProducto, pk=request.POST.get("lote_id") or None, unidad=unidad)
    exigir_misma_sesion(lote.orden.sesion_id if lote.orden_id else None, request)
    tipo = _texto(request, "tipo")
    if tipo not in dict(MovimientoProducto.TIPOS):
        raise ValidationError("Indica cómo sale el producto.")
    objeto = MovimientoProducto(
        unidad=unidad,
        lote=lote,
        tipo=tipo,
        cantidad=_decimal(request.POST.get("cantidad"), "La cantidad", minimo=Decimal("0.001")),
        precio_unitario=_decimal(request.POST.get("precio_unitario"), "El precio", permitir_vacio=True),
        destino=_texto(request, "destino", 200),
        referencia=_texto(request, "referencia", 120),
        motivo=_texto(request, "motivo"),
        registrado_por=request.user,
        temperatura_despacho=_decimal(
            request.POST.get("temperatura_despacho"), "La temperatura al despacho", minimo=Decimal("-40"),
            permitir_vacio=True,
        ),
    )
    if tipo == "venta":
        objeto.cliente = cliente_de_la_venta(request, _texto(request, "cliente", 160))
    validar_cadena_de_frio(lote, tipo, objeto.temperatura_despacho)
    unidad_destino_id = _texto(request, "unidad_destino_id")
    consumible_destino_id = _texto(request, "consumible_destino_id")
    if tipo == "transferencia":
        objeto.unidad_destino = get_object_or_404(Unidad, pk=unidad_destino_id or None, activo=True)
        if consumible_destino_id:
            objeto.consumible_destino = get_object_or_404(
                Consumible, pk=consumible_destino_id, unidad=objeto.unidad_destino, activo=True
            )
        if not objeto.destino:
            objeto.destino = objeto.unidad_destino.nombre
    elif tipo == "consumo_interno" and consumible_destino_id:
        objeto.consumible_destino = get_object_or_404(
            Consumible, pk=consumible_destino_id, unidad=unidad, activo=True
        )
        if not objeto.destino:
            objeto.destino = f"Inventario de la planta: {objeto.consumible_destino.nombre}"
    objeto.save()
    mensajes = {
        "venta": "Venta registrada",
        "transferencia": "Transferencia registrada",
        "muestra": "Muestra registrada",
        "consumo_interno": "Consumo interno registrado",
        "baja": "Baja registrada",
    }
    return objeto, mensajes[tipo], True


# ---------------------------------------------------- práctica por proceso
def orden_de_practica(reserva, usuario):
    """Al aprobar una práctica por proceso nace su orden, con la línea bloqueada."""
    existente = reserva.ordenes_produccion.first()
    if existente is not None or not reserva.receta_id:
        return existente
    receta = reserva.receta
    seleccion = seleccion_por_proceso(receta, reserva.factor_proceso or Decimal("1"), hora_inicio=reserva.hora_inicio)
    # Un encargo (servicio) no reserva máquinas: la corrida toma los equipos del proceso.
    ids_equipos = list(reservation_unit_ids(reserva)) or [item["id"] for item in seleccion["equipos"]]
    equipos = list(UnidadEquipo.objects.filter(pk__in=ids_equipos))
    es_maquila = reserva.tipo_solicitud == "servicio"
    codigo_reserva = reserva.codigo_reserva or reserva.pk
    etapas = list(receta.etapas.select_related("espacio").order_by("orden"))
    linea = next((e.espacio for e in etapas if e.espacio_id and e.espacio.tipo == "linea"), None)
    if linea is None:
        linea = next((e.espacio for e in etapas if e.espacio_id), None)
    orden = OrdenProduccion(
        unidad=reserva.laboratorio,
        receta=receta,
        factor=reserva.factor_proceso or Decimal("1"),
        origen=(
            "maquila" if es_maquila
            else "practica" if reserva.proposito_codigo == "docencia_practica" else "investigacion"
        ),
        reserva=reserva,
        fecha_inicio=reserva.fecha,
        fecha_fin=reserva.fecha + timedelta(days=seleccion["sesion"]["dias_extra"]),
        linea=linea,
        creada_por=usuario,
        observaciones=(
            f"Encargo {codigo_reserva}: {reserva.titulo_solicitud or reserva.detalle_trabajo}"
            if es_maquila
            else f"Práctica {codigo_reserva}: {reserva.referencia_actividad or reserva.titulo_solicitud}"
        ),
    )
    orden.planificar_cantidades()
    orden.full_clean()
    orden.save()
    orden.equipos.set(equipos)
    orden.sincronizar_bloqueo(usuario)
    return orden


def cancelar_orden_de_practica(reserva, motivo):
    """La orden de una práctica que no se hará se cancela y libera la línea."""
    for orden in reserva.ordenes_produccion.filter(estado__in=OrdenProduccion.ESTADOS_ABIERTOS):
        orden.cancelar(motivo=motivo)


OPERADORES_PRODUCCION = {
    "producto": operar_producto,
    "receta": operar_receta,
    "orden_produccion": operar_orden_produccion,
    "lote_producto": operar_lote_producto,
    "movimiento_producto": operar_movimiento_producto,
    "cliente": operar_cliente,
}
PERMISOS_PRODUCCION = {clave: "produccion" for clave in OPERADORES_PRODUCCION}
MODELOS_PRODUCCION = {
    "producto": Producto,
    "receta": Receta,
    "orden_produccion": OrdenProduccion,
    "lote_producto": LoteProducto,
    "movimiento_producto": MovimientoProducto,
    "cliente": Cliente,
}


# ---------------------------------------------------------------- contexto
def _plan_json(orden):
    # Lo que la práctica ya descontó al cerrar la reserva no se descuenta otra vez.
    consumidos = set()
    if orden.reserva_id:
        consumidos = set(
            EntradaInventario.objects.filter(reserva_id=orden.reserva_id, tipo="salida")
            .values_list("consumible_id", flat=True)
        )
    return json.dumps({
        "demostrativa": orden.demostrativa,
        "insumos": [
            {
                "consumible_id": item["consumible"].pk,
                "nombre": item["consumible"].nombre,
                "cantidad": "0" if item["consumible"].pk in consumidos else str(item["cantidad"]),
                "unidad": item["consumible"].unidad_medida,
                "obligatorio": item["obligatorio"],
                "descontado_en_reserva": item["consumible"].pk in consumidos,
            }
            for item in orden.insumos_planificados()
        ],
        "salidas": [
            {
                "producto_id": item["producto"].pk,
                "nombre": item["producto"].nombre,
                "tipo": item["producto"].get_tipo_display(),
                "cantidad": str(item["cantidad"]),
                "unidad": item["producto"].unidad_medida,
                "principal": item["principal"],
            }
            for item in orden.salidas_planificadas()
        ],
    })


def _lineas_json(receta):
    def numero(valor):
        return format(Decimal(valor).normalize(), "f")

    return json.dumps({
        "etapas": [
            {
                "nombre": etapa.nombre,
                "tipo": etapa.tipo,
                "equipo_id": etapa.equipo_id or "",
                "espacio_id": etapa.espacio_id or "",
                "duracion_min": etapa.duracion_min,
                "espera_min": etapa.espera_min,
                "personas": etapa.personas,
                "rendimiento_pct": numero(etapa.rendimiento_pct),
                "distancia_m": numero(etapa.distancia_m),
                "punto_critico": "si" if etapa.punto_critico else ("pc" if etapa.punto_control else "no"),
                "parametro": etapa.parametro,
                "limite": etapa.limite,
                "instrucciones": etapa.instrucciones,
            }
            for etapa in receta.etapas.all()
        ],
        "insumos": [
            {
                "consumible_id": insumo.consumible_id,
                "cantidad": str(insumo.cantidad),
                "obligatorio": "si" if insumo.obligatorio else "no",
                "etapa": insumo.etapa.orden if insumo.etapa_id else "",
                "forma_parte": insumo.forma_parte,
            }
            for insumo in receta.insumos.all()
        ],
        "salidas": [
            {
                "producto_id": salida.producto_id,
                "cantidad": str(salida.cantidad),
                "etapa": salida.etapa.orden if salida.etapa_id else "",
                "externa_al_flujo": "si" if salida.externa_al_flujo else "no",
            }
            for salida in receta.salidas.all()
        ],
    })


def contexto_produccion(unidad, permisos_operativos, configuracion, sesion=None):
    """Todo lo que la pestaña de producción y sus formularios necesitan."""
    # Quien entra a la consola de la planta consulta la producción; la opera con su permiso.
    habilitada = bool(configuracion.registra_produccion)
    hoy = timezone.localdate()
    productos = list(Producto.objects.filter(unidad=unidad, activo=True).select_related('familia'))
    for producto in productos:
        producto.existencia = producto.existencia_disponible
    recetas = list(
        Receta.objects.filter(unidad=unidad, activa=True)
        .select_related("producto", "familia", "responsable")
        .prefetch_related(
            "etapas__equipo", "etapas__espacio",
            "insumos__consumible", "insumos__etapa", "salidas__producto", "salidas__etapa", "software",
        )
    )
    for receta in recetas:
        receta.lineas_json = _lineas_json(receta)
        receta.software_ids_csv = ",".join(str(programa.pk) for programa in receta.software.all())
        receta.proceso = datos_de_receta(receta)
        receta.resumen_proceso = resumen_proceso(receta.proceso)
        receta.diagrama_flujo_svg = diagrama_flujo_svg(receta.proceso) if receta.proceso["etapas"] else ""
        receta.costo = costo_estandar(receta, configuracion)
    ordenes = list(
        OrdenProduccion.objects.en_sesion(sesion).filter(unidad=unidad)
        .select_related("receta", "producto", "linea", "responsable", "reserva", "linea_plan__plan")
        .prefetch_related("equipos__equipo", "lotes", "receta__etapas__equipo", "receta__insumos__consumible")[:40]
    )
    costos_entrada = costos_de_entradas(ordenes)
    for orden in ordenes:
        orden.costo = costo_real(orden, configuracion, costos_entrada)
        orden.plan_json = _plan_json(orden) if orden.abierta else ""
        orden.equipos_ids_csv = ",".join(str(equipo.pk) for equipo in orden.equipos.all())
        orden.lotes_creados = orden.lotes.count()
        # La corrida abierta se controla en proceso con el plan de su producto, si lo tiene.
        orden.control_url = (
            reverse("control_calidad", args=[unidad.slug]) + f"?orden={orden.pk}"
            if orden.abierta and plan_para_orden(orden) else ""
        )
    lotes = list(
        LoteProducto.objects.en_sesion(sesion).filter(unidad=unidad)
        .select_related("producto", "orden")[:60]
    )
    movimientos = list(
        MovimientoProducto.objects.en_sesion(sesion).filter(unidad=unidad)
        .select_related("lote__producto", "unidad_destino", "cliente")[:40]
    )
    # En una sesión el consumo sale de sus existencias: no se eligen lotes del inventario real.
    consumibles_recetas = set() if sesion is not None else {
        insumo.consumible_id for receta in recetas for insumo in receta.insumos.all()
    }
    lotes_por_insumo = {}
    for lote in (
        LoteConsumible.objects.filter(
            consumible_id__in=consumibles_recetas, estado__in=("en_uso", "bodega")
        )
        .select_related("equipo_en_uso__equipo")
        .order_by("fecha_vencimiento", "codigo")
    ):
        lotes_por_insumo.setdefault(str(lote.consumible_id), []).append({
            "id": lote.pk,
            "codigo": lote.codigo,
            "cantidad": str(lote.cantidad_actual),
            "estado": lote.estado,
            "vence": lote.fecha_vencimiento.isoformat() if lote.fecha_vencimiento else "",
            "equipo": lote.equipo_en_uso.codigo_unidad if lote.equipo_en_uso_id else "",
        })
    ventas_30 = (
        MovimientoProducto.objects.en_sesion(sesion).filter(
            unidad=unidad, tipo="venta", fecha__gte=timezone.now() - timedelta(days=30)
        ).aggregate(total=Sum("valor_total"))["total"]
        or Decimal("0")
    )
    # Las métricas y las listas son de la producción real o de la sesión, nunca mezcladas.
    lotes_disponibles = [lote for lote in lotes if lote.estado == "disponible"]
    por_vencer = [
        lote for lote in lotes_disponibles
        if lote.fecha_vencimiento and lote.fecha_vencimiento <= hoy + timedelta(days=3)
    ]
    metricas = {
        "ordenes_abiertas": sum(orden.abierta for orden in ordenes),
        "lotes_disponibles": len(lotes_disponibles),
        "lotes_por_vencer": len(por_vencer),
        "ventas_30": ventas_30,
        "lotes_en_cuarentena": sum(lote.estado == "cuarentena" for lote in lotes),
    }
    # Los encargos de servicio son de la producción real; una sesión no los atiende.
    reservas_origen = [] if sesion is not None else (
        Reserva.objects.filter(
            laboratorio=unidad,
            tipo_solicitud="servicio",
            estado__in=ESTADOS_OCUPAN_AGENDA,
        )
        .select_related("usuario")
        .order_by("fecha")[:30]
    )
    otras_unidades = list(Unidad.objects.filter(activo=True).exclude(pk=unidad.pk).order_by("nombre"))
    # Los de otras unidades reciben una transferencia; los propios, un intermedio que vuelve a entrar.
    consumibles_destino = list(
        Consumible.objects.filter(Q(unidad__in=otras_unidades) | Q(unidad=unidad), activo=True)
        .select_related("unidad")
        .order_by("unidad__nombre", "nombre")
    )
    return {
        "produccion_habilitada": habilitada,
        "puede_operar_produccion": bool(permisos_operativos.get("produccion")),
        "produccion_detalle_visibilidad": (
            FichaContenido.objects.filter(
                unidad=unidad,
                tipo="documento",
                codigo__endswith="-DOC-CORRIDAS-DETALLE",
                estado="publicada",
            ).values_list("visibilidad", flat=True).first()
            or "interna"
        ),
        "productos_unidad": productos,
        "recetas_unidad": recetas,
        "ordenes_produccion": ordenes,
        "lotes_producto": lotes,
        "movimientos_producto": movimientos,
        "tipos_con_despacho": TIPOS_CON_DESPACHO,
        **contexto_clientes(unidad, sesion),
        "produccion_metricas": metricas,
        "produccion_lotes_por_insumo": lotes_por_insumo,
        "reservas_origen_produccion": reservas_origen,
        "unidades_destino_producto": otras_unidades,
        "consumibles_destino_producto": consumibles_destino,
        "tipos_producto": Producto.TIPOS,
        "familias_producto": list(FamiliaProducto.objects.filter(unidad=unidad, activa=True).order_by('orden')),
        "detalle_tipos_producto": Producto.TIPO_DETALLE,
        "origenes_orden_produccion": OrdenProduccion.ORIGENES,
        "origenes_receta": Receta.ORIGENES,
        "tipos_movimiento_producto": MovimientoProducto.TIPOS,
        "tipos_etapa": EtapaReceta.TIPOS,
        "consumibles_receta": list(
            Consumible.objects.filter(unidad=unidad, activo=True).order_by("clasificacion", "nombre")
        ),
    }


def seccion_produccion(contexto):
    metricas = contexto["produccion_metricas"]
    return {
        "clave": "produccion",
        "titulo": "Producción",
        "descripcion": "Productos, recetas, órdenes de producción, lotes y salidas.",
        "icono": "iconsminds-factory",
        "dato": f'{metricas["ordenes_abiertas"]} órdenes',
        "etiqueta": f'{metricas["lotes_disponibles"]} lotes disponibles'
        + ("" if contexto["puede_operar_produccion"] else " · solo consulta"),
        "habilitada": contexto["produccion_habilitada"],
    }


# ----------------------------------------------------------------- reporte
def reporte_produccion(unit, start_date, end_date, state="", search=""):
    """Órdenes del período con lo planificado, lo obtenido y lo vendido.

    Una corrida de varios días cuenta si toca el período por cualquiera de
    sus extremos, como una campaña que empezó antes y terminó dentro.
    """
    state_choices = OrdenProduccion.ESTADOS
    queryset = (
        OrdenProduccion.objects.reales().filter(
            unidad=unit, sesion=None, fecha_inicio__lte=end_date, fecha_fin__gte=start_date,
        )
        .select_related("producto", "receta", "linea", "responsable")
    )
    if state in dict(state_choices):
        queryset = queryset.filter(estado=state)
    if search:
        queryset = queryset.filter(
            Q(codigo__icontains=search)
            | Q(producto__nombre__icontains=search)
            | Q(receta__nombre__icontains=search)
            | Q(linea__nombre__icontains=search)
            | Q(observaciones__icontains=search)
        )
    headers = [
        "Código", "Producto", "Origen", "Inicio", "Fin", "Línea", "Planificado",
        "Obtenido", "Merma", "Rendimiento", "Lotes", "Costo real", "Estado",
    ]
    rows = []
    ordenes = queryset.annotate(_numero_lotes_reporte=Count("lotes")).order_by(
        *OrdenProduccion._meta.ordering
    ).prefetch_related(
        "receta__etapas__equipo", "receta__insumos__consumible"
    ).iterator(chunk_size=200)
    configuracion = ConfiguracionOperativaUnidad.objects.filter(unidad=unit).first()
    costo_producido = Decimal("0")

    def cantidad(valor, unidad_medida):
        if valor is None:
            return "—"
        return f"{format(Decimal(valor).normalize(), 'f')} {unidad_medida}"

    # El costo histórico conserva su función canónica y se concilia para todas
    # las órdenes. Tanto modelos como IDs de entradas viven sólo en este bloque.
    while lote := list(islice(ordenes, 200)):
        costos_entrada = costos_de_entradas(lote)
        for orden in lote:
            costo = costo_real(orden, configuracion, costos_entrada)
            if costo:
                costo_producido += costo["total"]
            if len(rows) >= 501:
                continue
            unidad_medida = orden.producto.unidad_medida
            rows.append([
                orden.codigo,
                orden.producto.nombre,
                orden.get_origen_display(),
                orden.fecha_inicio.strftime("%d/%m/%Y"),
                orden.fecha_fin.strftime("%d/%m/%Y"),
                orden.linea.nombre if orden.linea_id else "—",
                cantidad(orden.cantidad_planificada, unidad_medida),
                cantidad(orden.cantidad_obtenida, unidad_medida),
                cantidad(orden.merma, unidad_medida),
                f"{orden.rendimiento_real_pct}%" if orden.rendimiento_real_pct is not None else "—",
                orden._numero_lotes_reporte,
                f'{costo["total_texto"]}{"" if costo["completo"] else " (parcial)"}' if costo else "—",
                orden.get_estado_display(),
            ])
    ventas = (
        MovimientoProducto.objects.reales().filter(
            unidad=unit, tipo="venta", fecha__date__range=(start_date, end_date)
        ).aggregate(total=Sum("valor_total"))["total"]
        or Decimal("0")
    )
    # El reporte de la unidad es de la producción real: las sesiones de práctica no entran.
    cards = [
        ("Órdenes", queryset.count()),
        ("Terminadas", queryset.filter(estado="terminada").count()),
        ("Lotes de producto", LoteProducto.objects.filter(orden__in=queryset).count()),
        ("Ventas del período", f"${ventas:.2f}"),
        ("Costo de lo producido", f"${costo_producido:.2f}"),
    ]
    return headers, rows, cards, state_choices


def reporte_procesos(unit, start_date, end_date, state="", search=""):
    """Las etapas de cada receta: tipo, dónde, tiempos, lo que entra y lo que sale."""
    state_choices = EtapaReceta.TIPOS
    queryset = (
        EtapaReceta.objects.filter(receta__unidad=unit, receta__activa=True)
        .select_related("receta", "receta__producto", "equipo", "espacio")
        .prefetch_related("insumos__consumible", "salidas__producto")
        .order_by("receta__nombre", "orden")
    )
    if state in dict(state_choices):
        queryset = queryset.filter(tipo=state)
    if search:
        queryset = queryset.filter(
            Q(receta__nombre__icontains=search)
            | Q(nombre__icontains=search)
            | Q(equipo__nombre__icontains=search)
            | Q(espacio__nombre__icontains=search)
            | Q(parametro__icontains=search)
        )
    headers = [
        "Receta", "N.º", "Etapa", "Tipo", "Dónde", "Trabajo (min)", "Espera (min)",
        "Personas", "Continúa (%)", "Entra", "Sale", "Punto crítico",
    ]
    rows = []
    for etapa in queryset[:501]:
        rows.append([
            etapa.receta.nombre,
            etapa.orden,
            etapa.nombre,
            etapa.get_tipo_display(),
            etapa.equipo.nombre if etapa.equipo_id else (etapa.espacio.nombre if etapa.espacio_id else "—"),
            etapa.duracion_min,
            etapa.espera_min,
            etapa.personas,
            format(Decimal(etapa.rendimiento_pct).normalize(), "f"),
            ", ".join(f"{i.consumible.nombre} {format(Decimal(i.cantidad).normalize(), 'f')} {i.consumible.unidad_medida}" for i in etapa.insumos.all()) or "—",
            ", ".join(f"{s.producto.nombre} {format(Decimal(s.cantidad).normalize(), 'f')} {s.producto.unidad_medida}" for s in etapa.salidas.all()) or "—",
            f"{'PCC' if etapa.punto_critico else 'PC'}: {etapa.parametro} ({etapa.limite})"
            if etapa.punto_critico or etapa.punto_control else "—",
        ])
    totales = queryset.aggregate(
        recetas=Count("receta_id", distinct=True), etapas=Count("pk"),
        trabajo=Sum("duracion_min"), espera=Sum("espera_min"),
        criticos=Count("pk", filter=Q(punto_critico=True)),
        control=Count("pk", filter=Q(punto_control=True)),
    )
    # Sumar ambas columnas por separado evita desbordar un entero de 32 bits
    # en una fila histórica antes de que PostgreSQL aplique SUM.
    minutos = (totales["trabajo"] or 0) + (totales["espera"] or 0)
    cards = [
        ("Recetas", totales["recetas"]),
        ("Etapas", totales["etapas"]),
        ("Horas estándar", f"{minutos / 60:.1f}"),
        ("Puntos críticos (PCC)", totales["criticos"]),
        ("Puntos de control (PC)", totales["control"]),
    ]
    return headers, rows, cards, state_choices


# ------------------------------------------------------------------ vistas
@login_required
def ficha_proceso_view(request, slug, receta_id):
    """La ficha del proceso: diagramas, etapas, cursograma, balance y cronograma."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not (
        puede_operar_modulo_unidad(request.user, unidad, "produccion")
        or puede_operar_modulo_unidad(request.user, unidad, "reportes")
    ):
        raise PermissionDenied("No tienes autorización para consultar los procesos de esta unidad.")
    receta = get_object_or_404(Receta.objects.select_related("producto", "unidad"), pk=receta_id, unidad=unidad)
    datos = datos_de_receta(receta)
    contexto = {
        "unidad": unidad,
        "receta": receta,
        "proceso": datos,
        "resumen": resumen_proceso(datos),
        "balance": balance_de_masa(datos),
        "cronograma": cronograma(datos),
        "cursograma": cursograma_analitico(datos),
        **diagramas_de_ficha(datos, cursograma_analitico(datos)),
        "generado_en": timezone.localtime(),
        "costo": costo_estandar(receta, ConfiguracionOperativaUnidad.objects.filter(unidad=unidad).first()),
    }
    from apps.documentos.presentation.documentos import enlaces_de_documento, formato_pedido, respuesta_pdf
    from apps.formacion.presentation.documentos_aula import documento_de_ficha

    formato = formato_pedido(request)
    if formato:
        return respuesta_pdf(documento_de_ficha(contexto), f'ficha-proceso-{receta.pk}.pdf', formato)
    contexto.update(enlaces_de_documento(request))
    return render(request, "portal/pages/unidades/gestion/ficha_proceso.html", contexto)


@login_required
def guia_desde_proceso_view(request, slug, receta_id):
    """Lo que el editor de guías toma del proceso: recursos y procedimiento."""
    unidad = get_object_or_404(Unidad, slug=slug)
    receta = get_object_or_404(Receta.objects.select_related("producto", "unidad"), pk=receta_id, unidad=unidad, activa=True)
    return JsonResponse(guia_desde_proceso(datos_de_receta(receta)))
