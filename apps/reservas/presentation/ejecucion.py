"""Cierre operativo de reservas y efectos trazables derivados."""

import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.utils.translation import gettext

from apps.formacion.models.practicas import EjecucionPractica
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.recursos.models.mantenimiento import IncidenciaEquipo
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.reservas.models.reservas import RegistroParticipanteReserva, Reserva, ReservaConsumible
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import validar_accion_reserva

from apps.gestion_unidades.presentation.permisos import puede_corregir_reservas_cerradas_unidad
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cotizaciones import calcular_liquidacion_real


def _booleano(datos, nombre):
    return str(datos.get(nombre) or "").strip().lower() in {
        "1", "true", "on", "si", "sí", "yes",
    }


def _decimal(valor, etiqueta, *, requerido=False):
    texto = str(valor or "").strip().replace(",", ".")
    if not texto:
        if requerido:
            raise ValueError(f"{etiqueta} es obligatorio.")
        return Decimal("0")
    try:
        numero = Decimal(texto)
    except InvalidOperation as error:
        raise ValueError(f"{etiqueta} debe ser un número válido.") from error
    if not numero.is_finite():
        raise ValueError(f"{etiqueta} debe ser un número finito.")
    if numero < 0:
        raise ValueError(f"{etiqueta} no puede ser negativo.")
    return numero


def _lista(datos, nombre):
    if hasattr(datos, "getlist"):
        return datos.getlist(nombre)
    valor = datos.get(nombre, [])
    return valor if isinstance(valor, (list, tuple, set)) else [valor]


def _ids(datos, nombre):
    try:
        return {int(valor) for valor in _lista(datos, nombre) if str(valor).strip()}
    except (TypeError, ValueError) as error:
        raise ValueError("Uno de los recursos utilizados no es válido.") from error


def _pertenece_equipo(equipo, unidad_id):
    return equipo.laboratorio_id == unidad_id or equipo.laboratorios.filter(
        pk=unidad_id
    ).exists()


def _equipos_solicitados_ids(reserva):
    ids = set()
    for item in reserva.get_unidades_seleccionadas_list():
        if not isinstance(item, dict):
            continue
        try:
            ids.add(int(item.get("id")))
        except (TypeError, ValueError):
            continue
    return ids


def _snapshot_recursos(reserva, datos, captura_explicita):
    unidad = reserva.laboratorio
    equipos_ids = (
        _ids(datos, "ejecucion_equipos_ids")
        if captura_explicita
        else _equipos_solicitados_ids(reserva)
    )
    software_ids = (
        _ids(datos, "ejecucion_software_ids")
        if captura_explicita
        else set(reserva.software_solicitado.values_list("pk", flat=True))
    )
    espacios_ids = (
        _ids(datos, "ejecucion_espacios_ids")
        if captura_explicita
        else set(reserva.espacios_solicitados.values_list("pk", flat=True))
    )
    servicios_ids = (
        _ids(datos, "ejecucion_servicios_ids")
        if captura_explicita
        else set(reserva.servicios_solicitados.values_list("pk", flat=True))
    )

    equipos = list(
        UnidadEquipo.objects.filter(pk__in=equipos_ids)
        .select_related("equipo")
        .prefetch_related("laboratorios")
    )
    software = list(SoftwareDisponible.objects.filter(pk__in=software_ids, unidad=unidad))
    espacios = list(EspacioReservable.objects.filter(pk__in=espacios_ids, unidad=unidad))
    servicios = list(
        FablabService.objects.filter(pk__in=servicios_ids).filter(
            models_q_unidad_servicio(unidad)
        )
    )
    if len(equipos) != len(equipos_ids) or any(
        not _pertenece_equipo(item, unidad.pk) for item in equipos
    ):
        raise ValueError("Uno de los equipos utilizados no pertenece a esta unidad.")
    if len(software) != len(software_ids):
        raise ValueError("Uno de los programas utilizados no pertenece a esta unidad.")
    if len(espacios) != len(espacios_ids):
        raise ValueError("Uno de los espacios utilizados no pertenece a esta unidad.")
    if len(servicios) != len(servicios_ids):
        raise ValueError("Uno de los servicios realizados no pertenece a esta unidad.")

    return {
        "equipos": [
            {
                "id": str(item.pk),
                "codigo": item.codigo_unidad,
                "nombre": item.equipo.nombre,
                "ubicacion": item.ubicacion_especifica or "",
                "estado_al_cierre": item.get_estado_unidad_display(),
            }
            for item in equipos
        ],
        "software": [
            {"id": str(item.pk), "codigo": item.codigo, "nombre": item.nombre, "version": item.version}
            for item in software
        ],
        "espacios": [
            {"id": str(item.pk), "codigo": item.codigo, "nombre": item.nombre, "ubicacion": item.ubicacion}
            for item in espacios
        ],
        "servicios": [
            {"id": str(item.pk), "codigo": item.code, "nombre": item.nombre}
            for item in servicios
        ],
    }, {item.pk: item for item in equipos}


def models_q_unidad_servicio(unidad):
    # Importación local para mantener este módulo independiente de las vistas.
    from django.db.models import Q

    return Q(unidad=unidad) | Q(unidad__isnull=True)


def _crear_incidencia(reserva, actor, datos, equipos_por_id):
    if not _booleano(datos, "ejecucion_tuvo_incidencia"):
        return None
    try:
        equipo_id = int(datos.get("ejecucion_incidencia_equipo_id") or 0)
    except (TypeError, ValueError) as error:
        raise ValueError("Selecciona el equipo relacionado con la incidencia.") from error
    equipo = equipos_por_id.get(equipo_id)
    if not equipo:
        raise ValueError("La incidencia debe vincularse con un equipo realmente utilizado.")
    titulo = str(datos.get("ejecucion_incidencia_titulo") or "").strip()
    descripcion = str(datos.get("ejecucion_incidencia_descripcion") or "").strip()
    tipo = str(datos.get("ejecucion_incidencia_tipo") or "falla").strip()
    prioridad = str(datos.get("ejecucion_incidencia_prioridad") or "media").strip()
    if not titulo or not descripcion:
        raise ValueError("Completa el título y la descripción de la incidencia.")
    if tipo not in dict(IncidenciaEquipo.TIPOS) or prioridad not in dict(IncidenciaEquipo.PRIORIDADES):
        raise ValueError("La clasificación de la incidencia no es válida.")
    responsable = getattr(reserva.responsable_asignado, "usuario", None)
    return IncidenciaEquipo.objects.create(
        equipo=equipo,
        reserva=reserva,
        unidad=reserva.laboratorio,
        titulo=titulo,
        descripcion=descripcion,
        tipo=tipo,
        prioridad=prioridad,
        detiene_operacion=_booleano(datos, "ejecucion_incidencia_detiene"),
        reportada_por=actor,
        asignada_a=responsable,
    )


def _detalle_por_pieza(fila, consumida, piezas, nombre):
    """Reparto declarado pieza por pieza; debe sumar lo que salió del lote."""
    detalle = fila.get("detalle_piezas") or []
    if not detalle:
        return []
    if not isinstance(detalle, list):
        raise ValueError("El detalle por pieza no tiene un formato válido.")
    if len(detalle) != piezas:
        raise ValueError(
            f"El detalle por pieza de {nombre} debe cubrir las {piezas} piezas obtenidas."
        )
    valores = [_decimal(valor, "La cantidad de una pieza") for valor in detalle]
    suma = sum(valores, Decimal("0"))
    if abs(suma - consumida) > Decimal("0.001"):
        raise ValueError(
            f"El detalle por pieza de {nombre} suma {suma} y el uso "
            f"registrado es {consumida}."
        )
    return [valor.quantize(Decimal("0.001")) for valor in valores]


def _registrar_consumos(reserva, actor, datos, equipos_por_id, incidencia, piezas=1):
    if "ejecucion_consumibles_json" not in datos:
        return []
    try:
        filas = json.loads(datos.get("ejecucion_consumibles_json") or "[]")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("El detalle de consumo no tiene un formato válido.") from error
    if not isinstance(filas, list):
        raise ValueError("El detalle de consumo no tiene un formato válido.")
    ids = []
    for fila in filas:
        try:
            ids.append(int(fila.get("reserva_consumible_id")))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("Uno de los consumos no corresponde a la reserva.") from error
    if len(ids) != len(set(ids)):
        raise ValueError("Un insumo no puede registrarse dos veces en el mismo cierre.")
    registros = {
        item.pk: item
        for item in ReservaConsumible.objects.select_for_update(of=('self',))
        .filter(reserva=reserva, pk__in=ids)
        .select_related("consumible")
        .order_by('pk')
    }
    if len(registros) != len(ids):
        raise ValueError("Uno de los consumos no corresponde a esta reserva.")

    # Mismo orden que el kardex y los conteos, incluso con varios materiales.
    list(Consumible.objects.select_for_update().filter(
        pk__in={item.consumible_id for item in registros.values()},
    ).order_by('pk'))

    resultados = []
    for fila in filas:
        registro = registros[int(fila["reserva_consumible_id"])]
        consumida = _decimal(fila.get("consumida"), "La cantidad consumida")
        desperdiciada = _decimal(fila.get("desperdiciada"), "La cantidad desperdiciada")
        total = consumida + desperdiciada
        por_pieza = _detalle_por_pieza(
            fila, consumida, piezas, registro.consumible.nombre
        )
        lote = None
        equipo = None
        if total:
            try:
                lote_id = int(fila.get("lote_id") or 0)
                equipo_id = int(fila.get("equipo_id") or 0)
            except (TypeError, ValueError) as error:
                raise ValueError("Selecciona el lote abierto y el equipo para cada consumo.") from error
            lote = (
                LoteConsumible.objects.select_for_update()
                .filter(pk=lote_id, consumible=registro.consumible)
                .first()
            )
            equipo = equipos_por_id.get(equipo_id)
            if not lote or lote.estado != "en_uso":
                raise ValueError(
                    f"Selecciona una presentación abierta y en uso para {registro.consumible.nombre}."
                )
            if not equipo or lote.equipo_en_uso_id != equipo.pk:
                raise ValueError(
                    f"El lote de {registro.consumible.nombre} debe estar asignado al equipo utilizado."
                )
            if total > lote.cantidad_actual:
                raise ValueError(
                    f"El consumo de {registro.consumible.nombre} supera el saldo del lote {lote.codigo}."
                )

        registro.cantidad_consumida = consumida
        registro.cantidad_desperdiciada = desperdiciada
        registro.full_clean()
        registro.save(update_fields=["cantidad_consumida", "cantidad_desperdiciada"])
        movimientos = []
        if consumida:
            movimiento, _ = EntradaInventario.objects.get_or_create(
                clave_idempotencia=f"reserva:{reserva.pk}:consumo:{registro.pk}",
                defaults={
                    "consumible": registro.consumible,
                    "unidad": reserva.laboratorio,
                    "tipo": "salida",
                    "motivo": (
                        "consumo_practica"
                        if reserva.proposito_codigo == "docencia_practica"
                        else "consumo_produccion"
                    ),
                    "cantidad": consumida,
                    "lote_inventario": lote,
                    "equipo": equipo,
                    "reserva": reserva,
                    "usuario": actor,
                    "responsable_costo": "usuario",
                    "referencia": reserva.codigo_reserva or str(reserva.pk),
                    "nota": "Consumo real registrado al cerrar la atención.",
                },
            )
            movimientos.append(movimiento)
        if desperdiciada:
            motivo = str(fila.get("motivo_desperdicio") or "desperdicio_calidad").strip()
            if motivo not in {"desperdicio_equipo", "desperdicio_calidad"}:
                raise ValueError("Selecciona una causa válida para el desperdicio.")
            if motivo == "desperdicio_equipo" and not incidencia:
                raise ValueError("El desperdicio por falla debe vincular la incidencia del cierre.")
            movimiento, _ = EntradaInventario.objects.get_or_create(
                clave_idempotencia=f"reserva:{reserva.pk}:desperdicio:{registro.pk}",
                defaults={
                    "consumible": registro.consumible,
                    "unidad": reserva.laboratorio,
                    "tipo": "salida",
                    "motivo": motivo,
                    "cantidad": desperdiciada,
                    "lote_inventario": lote,
                    "equipo": equipo,
                    "reserva": reserva,
                    "incidencia": incidencia if motivo == "desperdicio_equipo" else None,
                    "usuario": actor,
                    "responsable_costo": "laboratorio",
                    "referencia": reserva.codigo_reserva or str(reserva.pk),
                    "nota": "Pérdida registrada durante el cierre operativo.",
                },
            )
            movimientos.append(movimiento)
        costo_consumido = sum(
            (
                movimiento.costo_total or Decimal("0")
                for movimiento in movimientos
                if movimiento.motivo in {"consumo_practica", "consumo_produccion"}
            ),
            Decimal("0"),
        )
        costo_desperdicio = sum(
            (
                movimiento.costo_total or Decimal("0")
                for movimiento in movimientos
                if movimiento.motivo in {"desperdicio_equipo", "desperdicio_calidad"}
            ),
            Decimal("0"),
        )
        resultados.append(
            {
                "reserva_consumible_id": str(registro.pk),
                "consumible_id": str(registro.consumible_id),
                "nombre": registro.consumible.nombre,
                "unidad": registro.consumible.unidad_medida or "unidades",
                "consumida": str(consumida),
                "desperdiciada": str(desperdiciada),
                "total_retirado": str(total),
                "piezas": piezas,
                "detalle_piezas": [str(valor) for valor in por_pieza],
                "por_pieza": (
                    str((consumida / piezas).quantize(Decimal("0.001")))
                    if piezas and consumida and not por_pieza
                    else ""
                ),
                "lote_id": str(lote.pk) if lote else "",
                "lote": lote.codigo if lote else "",
                "equipo_id": str(equipo.pk) if equipo else "",
                "equipo": equipo.codigo_unidad if equipo else "",
                "movimientos_ids": [item.pk for item in movimientos],
                "costo_consumido": str(costo_consumido),
                "costo_desperdicio": str(costo_desperdicio),
                "costo_total": str(costo_consumido + costo_desperdicio),
            }
        )
    return resultados


def _registrar_ingreso(reserva, actor, datos, liquidacion):
    if reserva.tipo_solicitud != "servicio":
        return None, None
    monto_calculado = Decimal(liquidacion["valor_final_usuario"])
    monto_manual_texto = str(datos.get("ejecucion_monto_cobrado") or "").strip()
    monto = (
        _decimal(monto_manual_texto, "El monto cobrado")
        if monto_manual_texto
        else monto_calculado
    )
    justificacion = str(datos.get("ejecucion_justificacion_ajuste") or "").strip()
    diferencia = monto - monto_calculado
    if diferencia and len(justificacion) < 5:
        raise ValueError(
            "Explica el ajuste cuando el monto registrado difiere de la liquidación automática."
        )
    if diferencia > 0:
        raise ValueError(
            "El cobro no puede superar los materiales consumidos y sus impuestos configurados. "
            "Corrige el consumo registrado si falta algún material; los recursos y el personal los asume la UPEC."
        )
    liquidacion["monto_registrado"] = str(monto.quantize(Decimal("0.01")))
    liquidacion["ajuste_manual"] = str(diferencia.quantize(Decimal("0.01")))
    liquidacion["justificacion_ajuste"] = justificacion
    if not monto:
        return None, {
            "monto_calculado": str(monto_calculado.quantize(Decimal("0.01"))),
            "monto_registrado": "0.00",
            "ajuste": str(diferencia.quantize(Decimal("0.01"))),
            "justificacion": justificacion,
        }
    referencia = str(datos.get("ejecucion_referencia_pago") or "").strip()
    confirmado = _booleano(datos, "ejecucion_pago_confirmado")
    if confirmado and not referencia:
        raise ValueError("Registra el comprobante o referencia antes de confirmar el cobro.")
    movimiento, _ = MovimientoFinancieroUnidad.objects.get_or_create(
        clave_idempotencia=f"reserva:{reserva.pk}:ingreso-servicio",
        defaults={
            "unidad": reserva.laboratorio,
            "tipo": "ingreso",
            "categoria": "servicio",
            "fuente_fondos": "autogestion",
            "estado": "confirmado" if confirmado else "pendiente",
            "fecha_movimiento": timezone.localdate(),
            "monto": monto,
            "metodo": (
                reserva.metodo_pago
                if reserva.metodo_pago in dict(MovimientoFinancieroUnidad.METODO_CHOICES)
                else "no_aplica"
            ),
            "referencia": referencia,
            "descripcion": f"Servicio de la reserva {reserva.codigo_reserva or reserva.pk}",
            "reserva": reserva,
            "observaciones": (
                "Generado desde la liquidación automática del cierre operativo."
                + (f" Ajuste justificado: {justificacion}" if justificacion else "")
            ),
            "creado_por": actor,
            "actualizado_por": actor,
        },
    )
    return movimiento, {
        "monto_calculado": str(monto_calculado.quantize(Decimal("0.01"))),
        "monto_registrado": str(monto.quantize(Decimal("0.01"))),
        "ajuste": str(diferencia.quantize(Decimal("0.01"))),
        "justificacion": justificacion,
    }


def _sincronizar_ejecucion_practica(reserva, actor, detalle, incidencia):
    try:
        plan = reserva.planificacion_practica
    except ObjectDoesNotExist:
        return None
    participantes = detalle.get("participantes", [])
    datos = {
        "fecha_ejecucion": reserva.fecha,
        "hora_inicio_real": parse_time(detalle["horario_real"]["inicio"]),
        "hora_fin_real": parse_time(detalle["horario_real"]["fin"]),
        "resultado": "ejecutada",
        "estudiantes_asistentes": detalle["asistentes_total"],
        "recursos_utilizados": "; ".join(
            f"{clave.title()}: {', '.join(item['nombre'] for item in detalle.get(clave, []))}"
            for clave in ("equipos", "software", "espacios", "servicios")
            if detalle.get(clave)
        ),
        "detalle_operativo": {
            "equipos": detalle.get("equipos", []),
            "software": detalle.get("software", []),
            "espacios": detalle.get("espacios", []),
            "servicios": detalle.get("servicios", []),
            "participantes": participantes,
            "consumibles": detalle.get("consumibles", []),
        },
        "tuvo_incidente": bool(incidencia),
        "incidencia": incidencia,
        "observaciones_docente": detalle.get("observaciones", ""),
        "cumplimiento_resultado": detalle.get("cumplimiento_resultado", "si"),
        "responsable_tecnico": reserva.responsable_asignado,
        "estado": "revision" if plan.estado == "aprobada" else "borrador",
        "creado_por": actor,
    }
    ejecucion, creada = EjecucionPractica.objects.get_or_create(
        planificacion=plan,
        defaults=datos,
    )
    if not creada and ejecucion.estado != "validada":
        for campo, valor in datos.items():
            if campo != "creado_por":
                setattr(ejecucion, campo, valor)
        ejecucion.full_clean()
        ejecucion.save()
    return ejecucion


@operacion_reservas
@transaction.atomic
def registrar_cierre_operativo(reserva, actor, datos, *, unidad_esperada=None):
    """Bloquea, autoriza y persiste un cierre; rechaza efectos repetidos.

    Trabaja sobre default. Copia solo el resultado al objeto recibido, para
    conservar la interfaz del panel sin aceptar sus campos obsoletos.
    """
    if reserva._state.db not in {None, 'default'}:
        raise ValueError(gettext('El cierre operativo requiere la base de datos principal.'))
    original = reserva
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    reserva = (Reserva.objects.select_for_update(of=('self',))
               .select_related('laboratorio').filter(pk=reserva.pk).first())
    if reserva is None:
        raise ValueError(gettext('La sesión ya no está disponible.'))
    actor = exigir_autoridad_reserva(
        reserva, actor, operacion='cerrar_operacion', unidad_esperada=alcance)
    if reserva.detalle_ejecucion:
        raise ValueError(gettext('La reserva ya tiene un cierre operativo registrado.'))
    validar_accion_reserva(
        reserva.estado, 'completar',
        puede_corregir_cerradas=puede_corregir_reservas_cerradas_unidad(actor, reserva.laboratorio),
        permite_regularizacion=reserva.requiere_regularizacion_operativa)
    if reserva.estado == 'confirmada' and not reserva.requiere_cierre_operativo:
        raise ValueError(gettext('La atención solo puede cerrarse cuando finalice su horario.'))
    # Protege también los cierres invocados desde tareas o futuras interfaces.
    from apps.formacion.presentation.practicas_integracion import validar_compuerta_documental

    validar_compuerta_documental(reserva, "completar")
    captura_explicita = _booleano(datos, "ejecucion_registrada")
    inicio = parse_time(str(datos.get("ejecucion_hora_inicio") or "").strip())
    fin = parse_time(str(datos.get("ejecucion_hora_fin") or "").strip())
    if not inicio:
        inicio = (
            timezone.localtime(reserva.fecha_inicio_atencion).time().replace(second=0, microsecond=0)
            if reserva.fecha_inicio_atencion
            else reserva.hora_inicio
        )
    if not fin:
        fin = reserva.hora_fin
    if not inicio or not fin or fin <= inicio:
        raise ValueError("El horario real de ejecución no es válido.")

    registros = list(
        RegistroParticipanteReserva.objects.filter(reserva=reserva).order_by("rol", "nombre")
    )
    if captura_explicita and any(item.asistencia == "prevista" for item in registros):
        raise ValueError("Confirma la asistencia o inasistencia de todas las personas identificadas.")
    if not captura_explicita:
        RegistroParticipanteReserva.objects.filter(
            reserva=reserva, asistencia="prevista"
        ).update(asistencia="asistio")
        for item in registros:
            if item.asistencia == "prevista":
                item.asistencia = "asistio"
    asistentes_identificados = sum(item.asistencia == "asistio" for item in registros)
    try:
        asistentes_total = int(
            datos.get("ejecucion_asistentes_total")
            or asistentes_identificados
            or reserva.numero_participantes
            or 1
        )
    except (TypeError, ValueError) as error:
        raise ValueError("El total real de asistentes no es válido.") from error
    if asistentes_total < asistentes_identificados:
        raise ValueError("El total real no puede ser menor que las personas marcadas como asistentes.")

    cumplimiento = str(datos.get("ejecucion_cumplimiento") or "si").strip()
    if cumplimiento not in {"si", "parcial", "no"}:
        raise ValueError("Selecciona el cumplimiento real del resultado esperado.")
    # Cuántas piezas salieron de verdad: la solicitud no se toca, pero el
    # material se reparte y se lee sobre lo que realmente se produjo.
    piezas_solicitadas = reserva.cantidad_piezas or 1
    piezas_declaradas = datos.get("ejecucion_piezas")
    if piezas_declaradas in (None, ""):
        piezas_producidas = piezas_solicitadas
    else:
        try:
            piezas_producidas = int(piezas_declaradas)
        except (TypeError, ValueError) as error:
            raise ValueError("El número de piezas obtenidas no es válido.") from error
        if piezas_producidas < 0:
            raise ValueError("El número de piezas obtenidas no es válido.")
    recursos, equipos_por_id = _snapshot_recursos(reserva, datos, captura_explicita)
    incidencia = _crear_incidencia(reserva, actor, datos, equipos_por_id)
    consumos = _registrar_consumos(
        reserva,
        actor,
        datos,
        equipos_por_id,
        incidencia,
        piezas=piezas_producidas,
    )
    liquidacion = calcular_liquidacion_real(
        reserva,
        inicio=inicio,
        fin=fin,
        recursos=recursos,
        consumos=consumos,
    )
    ingreso, conciliacion_ingreso = _registrar_ingreso(
        reserva,
        actor,
        datos,
        liquidacion,
    )
    participantes = [
        {
            "id": str(item.pk),
            "usuario_id": item.usuario_id,
            "nombre": item.nombre,
            "rol": item.get_rol_display(),
            "asistencia_codigo": item.asistencia,
            "asistencia": item.get_asistencia_display(),
        }
        for item in registros
    ]
    detalle = {
        "version": 2,
        "registrada_en": timezone.now().isoformat(),
        "registrada_por_id": actor.pk,
        "registrada_por": actor.get_full_name() or actor.username,
        "horario_real": {"inicio": inicio.strftime("%H:%M"), "fin": fin.strftime("%H:%M")},
        "asistentes_total": asistentes_total,
        "asistentes_identificados": asistentes_identificados,
        "piezas_solicitadas": piezas_solicitadas,
        "piezas_producidas": piezas_producidas,
        "participantes": participantes,
        **recursos,
        "consumibles": consumos,
        "incidencia": (
            {
                "id": incidencia.pk,
                "equipo": incidencia.equipo.codigo_unidad,
                "titulo": incidencia.titulo,
                "prioridad": incidencia.get_prioridad_display(),
                "detiene_operacion": incidencia.detiene_operacion,
            }
            if incidencia
            else None
        ),
        "cumplimiento_resultado": cumplimiento,
        "observaciones": str(datos.get("ejecucion_observaciones") or "").strip(),
        "liquidacion": liquidacion,
        "ingreso": (
            {
                "id": ingreso.pk,
                "monto": str(ingreso.monto),
                "estado": ingreso.estado,
                "referencia": ingreso.referencia,
                "conciliacion": conciliacion_ingreso,
            }
            if ingreso
            else None
        ),
    }
    ejecucion = _sincronizar_ejecucion_practica(reserva, actor, detalle, incidencia)
    if ejecucion:
        detalle["ejecucion_practica_id"] = ejecucion.pk
        detalle["ejecucion_practica_estado"] = ejecucion.estado
    reserva.desglose_liquidacion = liquidacion
    reserva.costo_real = Decimal(liquidacion["costo_operativo_real"])
    reserva.aporte_institucional_real = Decimal(
        liquidacion["aporte_institucional_real"]
    )
    reserva.valor_final_usuario = Decimal(liquidacion["valor_final_usuario"])
    reserva.detalle_ejecucion = detalle
    reserva.estado = 'completada'
    reserva.resultado_cierre = 'atendida'
    reserva.fecha_cierre = timezone.now()
    reserva.detalle_cierre = detalle['observaciones'] or str(datos.get('observacion') or '').strip()
    campos = ['desglose_liquidacion', 'costo_real', 'aporte_institucional_real',
              'valor_final_usuario', 'detalle_ejecucion', 'estado', 'resultado_cierre',
              'fecha_cierre', 'detalle_cierre']
    reserva.save(update_fields=campos)
    for campo in campos:
        setattr(original, campo, getattr(reserva, campo))
    return detalle
