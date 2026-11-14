"""Preparación económica y técnica previa a crear una reserva o servicio."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from apps.core.presentation.regional import instante_institucional

from apps.reservas.models.reservas import Reserva
from apps.recursos.models.unidades import UnidadEquipo

from apps.plantas_piloto.operacion.presentation.maquila import servicio_de_proceso, trae_materia_prima_el_cliente
from apps.reservas.presentation.cotizaciones import calcular_costo_referencial_recursos, calcular_cotizacion, consumibles_sugeridos_servicios, normalizar_cantidades_servicio, normalizar_piezas, normalizar_seleccion_servicio, validar_cantidades_servicio


@dataclass(frozen=True)
class PreparacionSolicitud:
    consumibles_a_registrar: list[tuple]
    provision_consumibles: str
    modalidad_servicio: str
    metodo_pago: str
    cotizacion_aceptada: bool
    incluye_espacio: bool
    trabajo_servicio: dict | None
    fecha_entrega_prevista: Any
    fin_servicio_programado: Any
    equipo_servicio: Any
    detalle_trabajo: str
    receta_proceso: Any
    factor_proceso: Decimal | None
    materia_prima_cliente: bool
    cotizacion: dict


def parametros_trabajo_servicio(datos):
    """Normaliza piezas, urgencia y selección de insumos del servicio."""
    urgencia = (
        datos.get("urgencia_servicio") or datos.get("urgencia") or "normal"
    ).strip()
    if urgencia not in dict(Reserva.URGENCIA_SERVICIO_CHOICES):
        raise ValueError("La urgencia indicada no es válida")
    seleccion = (
        datos.get("materiales_seleccionados")
        if "materiales_seleccionados" in datos
        else datos.get("seleccion")
    )
    return {
        "piezas": normalizar_piezas(
            datos.get("cantidad_piezas") or datos.get("piezas")
        ),
        "seleccion": normalizar_seleccion_servicio(seleccion),
        "urgencia": urgencia,
    }


def fecha_entrega_prevista(valor, fecha_atencion):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        entrega = datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("La fecha de entrega prevista no es válida") from error
    if entrega < fecha_atencion:
        raise ValueError(
            "La fecha de entrega no puede ser anterior a la fecha de atención"
        )
    return entrega


def equipo_servicio(valor, unidad):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        equipo_id = int(valor)
    except ValueError as error:
        raise ValueError("El equipo indicado para el servicio no es válido") from error
    unidad_equipo = (
        UnidadEquipo.objects.filter(
            laboratorio=unidad,
            equipo_id=equipo_id,
            activa=True,
        )
        .select_related("equipo")
        .first()
    )
    if unidad_equipo is None:
        raise ValueError("El equipo indicado no pertenece a esta unidad")
    return unidad_equipo.equipo


def preparar_solicitud(
    post,
    *,
    usuario,
    unidad,
    configuracion,
    tipo_solicitud,
    modalidad_servicio,
    metodo_pago,
    cotizacion_aceptada,
    provision_consumibles,
    incluye_espacio_solicitado,
    requiere_espacio,
    recursos,
    equipos,
    software,
    espacios,
    servicios,
    consumibles,
    fecha_inicio,
    hora_fin,
    duracion,
    sesiones_programa,
    receta_proceso,
    factor_proceso,
):
    """Completa modalidad, cotización e insumos sin persistir el expediente."""
    if recursos and not configuracion.reservas_equipos:
        raise ValueError("La reserva de equipos no está habilitada para esta unidad")
    if provision_consumibles == "unidad" and not consumibles:
        raise ValueError("Selecciona al menos un material o consumible del inventario")
    if provision_consumibles != "unidad" and consumibles:
        raise ValueError(
            "La selección de inventario no coincide con la forma de provisión indicada"
        )

    consumibles_a_registrar = consumibles
    materia_prima_cliente = False
    fin_servicio_programado = None
    if tipo_solicitud == "servicio":
        modalidades_validas = {
            choice[0] for choice in Reserva.MODALIDAD_SERVICIO_CHOICES
        }
        pagos_validos = {choice[0] for choice in Reserva.METODO_PAGO_CHOICES}
        if modalidad_servicio not in modalidades_validas:
            raise ValueError(
                "Selecciona cómo participarás en la realización del servicio"
            )
        campo_modalidad = {
            "modelo_listo": "permite_modelo_listo",
            "diseno_asistido": "permite_diseno_asistido",
            "diseno_completo": "permite_diseno_completo",
        }[modalidad_servicio]
        incompatibles = [
            servicio.nombre
            for servicio in servicios
            if not getattr(servicio, campo_modalidad)
        ]
        if incompatibles:
            raise ValueError(
                "La modalidad elegida no está disponible para: "
                + ", ".join(incompatibles)
            )
        if modalidad_servicio == "diseno_asistido":
            if not configuracion.reservas_espacios:
                raise ValueError(
                    "La modalidad con diseño en la unidad no está habilitada para este laboratorio"
                )
            incluye_espacio = True
        else:
            incluye_espacio = False
            if recursos or software or espacios or incluye_espacio_solicitado:
                raise ValueError(
                    "Los recursos complementarios solo aplican cuando diseñarás en el laboratorio con asesoría"
                )
        if provision_consumibles != "ninguno" or consumibles:
            raise ValueError(
                "En una solicitud de servicio los insumos se obtienen automáticamente "
                "del catálogo técnico del servicio"
            )
        requiere_cotizacion = any(
            servicio.requiere_cotizacion for servicio in servicios
        )
        if requiere_cotizacion:
            if not cotizacion_aceptada:
                raise ValueError(
                    "Debes aceptar el valor estimado antes de enviar el servicio"
                )
            if metodo_pago not in pagos_validos:
                raise ValueError("Selecciona un método de pago")
        else:
            cotizacion_aceptada = False
            metodo_pago = ""

        trabajo_servicio = parametros_trabajo_servicio(post)
        cantidades_servicio = normalizar_cantidades_servicio(
            post.get("consumibles_servicio", "")
        )
        validar_cantidades_servicio(servicios, cantidades_servicio)
        entrega_prevista = fecha_entrega_prevista(
            post.get("fecha_entrega_prevista"),
            fecha_inicio.date(),
        )
        fin_servicio_programado = instante_institucional(
            datetime.combine(entrega_prevista or fecha_inicio.date(), hora_fin)
        )
        equipo_asignado = equipo_servicio(post.get("equipo_servicio"), unidad)
        detalle_trabajo = post.get("detalle_trabajo", "").strip()[:2000]
        servicio_proceso = servicio_de_proceso(servicios)
        if servicio_proceso is not None:
            receta_proceso = servicio_proceso.receta
            factor_proceso = Decimal(trabajo_servicio["piezas"])
            materia_prima_cliente = trae_materia_prima_el_cliente(
                servicio_proceso,
                trabajo_servicio["seleccion"],
            )
        consumibles_a_registrar = consumibles_sugeridos_servicios(
            servicios,
            cantidades_servicio,
            piezas=trabajo_servicio["piezas"],
            seleccion=trabajo_servicio["seleccion"],
        )
        provision_consumibles = "unidad" if consumibles_a_registrar else "ninguno"
        cotizacion = calcular_cotizacion(
            servicios,
            modalidad_servicio,
            usuario,
            cantidades_servicio,
            configuracion=configuracion,
            piezas=trabajo_servicio["piezas"],
            seleccion=trabajo_servicio["seleccion"],
            urgencia=trabajo_servicio["urgencia"],
        )
        cotizacion["trabajo"] = {
            "piezas": trabajo_servicio["piezas"],
            "urgencia": trabajo_servicio["urgencia"],
            "detalle": detalle_trabajo,
            "fecha_entrega_prevista": (
                entrega_prevista.isoformat() if entrega_prevista else None
            ),
            "equipo": (
                {"id": equipo_asignado.pk, "nombre": equipo_asignado.nombre}
                if equipo_asignado
                else None
            ),
        }
    else:
        trabajo_servicio = None
        entrega_prevista = None
        equipo_asignado = None
        detalle_trabajo = post.get("detalle_trabajo_recursos", "").strip()[:2000]
        incluye_espacio = requiere_espacio
        if tipo_solicitud == "recursos" and not (
            recursos or software or espacios or incluye_espacio
        ):
            raise ValueError(
                "Selecciona al menos un espacio, equipo, software o licencia"
            )
        if incluye_espacio and not configuracion.reservas_espacios:
            raise ValueError("La reserva del espacio no está habilitada para esta unidad")
        modalidad_servicio = ""
        metodo_pago = ""
        cotizacion_aceptada = False
        cotizacion = calcular_costo_referencial_recursos(
            consumibles,
            usuario,
            configuracion=configuracion,
            recursos=recursos,
            software=software,
            espacios=espacios,
            incluye_espacio=incluye_espacio,
            duracion_horas=duracion,
            sesiones=sesiones_programa,
        )

    return PreparacionSolicitud(
        consumibles_a_registrar=consumibles_a_registrar,
        provision_consumibles=provision_consumibles,
        modalidad_servicio=modalidad_servicio,
        metodo_pago=metodo_pago,
        cotizacion_aceptada=cotizacion_aceptada,
        incluye_espacio=incluye_espacio,
        trabajo_servicio=trabajo_servicio,
        fecha_entrega_prevista=entrega_prevista,
        fin_servicio_programado=fin_servicio_programado,
        equipo_servicio=equipo_asignado,
        detalle_trabajo=detalle_trabajo,
        receta_proceso=receta_proceso,
        factor_proceso=factor_proceso,
        materia_prima_cliente=materia_prima_cliente,
        cotizacion=cotizacion,
    )
