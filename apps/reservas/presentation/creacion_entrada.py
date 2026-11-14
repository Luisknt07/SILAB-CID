"""Entrada validada del caso de uso de creación de reservas.

Este módulo no conoce HTTP ni construye respuestas. Convierte los valores del
formulario en datos tipados y resuelve la selección inicial de producto o
proceso antes de que la vista coordine el resto del caso de uso.
"""

import json
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal

from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.reservas.models.reservas import Reserva

from apps.reservas.presentation.cotizaciones import normalizar_piezas
from apps.reservas.presentation.proceso import factor_valido


VALORES_BOOLEANOS = {"1", "true", "on", "si"}
VALORES_ACEPTACION = {*VALORES_BOOLEANOS, "sí"}
PROVISIONES_VALIDAS = {"ninguno", "unidad"}
LEGACY_PROPOSITOS = {
    "Docencia": "docencia_practica",
    "Investigación": "investigacion_innovacion",
    "Vinculación": "vinculacion",
    "Capacitación": "capacitacion",
    "Servicios": "servicio_cientifico_tecnologico",
    "Proyecto de Titulación": "titulacion",
    "Otro": "otro",
}

INTENCION_MIN_PALABRAS = 50
INTENCION_MAX_PALABRAS = 200
INTENCION_BREVE_MIN_PALABRAS = 30
INTENCION_BREVE_MAX_PALABRAS = 150


@dataclass(frozen=True)
class EntradaBasicaReserva:
    unidad_id: str
    tipo_solicitud: str
    provision_consumibles: str
    piezas_por_sesion: int
    requisitos_especiales: str
    modalidad_servicio: str
    intencion_solicitud: str
    incluye_espacio_solicitado: bool
    metodo_pago: str
    cotizacion_aceptada: bool
    proposito_codigo: str
    proposito: str
    fecha_inicio_texto: str
    fecha_fin_texto: str


@dataclass(frozen=True)
class IntervaloReserva:
    fecha_inicio: datetime
    fecha_fin: datetime
    horas: list[int]
    hora_inicio: time
    hora_fin: time
    duracion: int


@dataclass(frozen=True)
class SeleccionProceso:
    receta: Receta | None
    producto: Producto | None
    factor: Decimal | None


def normalizar_proposito(valor):
    """Acepta códigos vigentes y conserva los nombres de clientes anteriores."""
    codigos = dict(Reserva.PROPOSITO_INSTITUCIONAL_CHOICES)
    codigo = valor if valor in codigos else LEGACY_PROPOSITOS.get(valor, "")
    if not codigo:
        raise ValueError("Selecciona uno de los propósitos institucionales disponibles")
    return codigo, codigos[codigo]


def validar_intencion_solicitud(texto, *, breve=False):
    """Valida 50-200 palabras, o 30-150 cuando no acompaña una guía docente."""
    minimo = INTENCION_BREVE_MIN_PALABRAS if breve else INTENCION_MIN_PALABRAS
    maximo = INTENCION_BREVE_MAX_PALABRAS if breve else INTENCION_MAX_PALABRAS
    palabras = len(texto.split())
    if palabras < minimo:
        raise ValueError(
            f"Describe lo que pretendes realizar con al menos {minimo} "
            f"palabras (llevas {palabras})"
        )
    if palabras > maximo:
        raise ValueError(
            f"La descripción admite hasta {maximo} palabras (llevas {palabras})"
        )
    return texto


def normalizar_entrada_basica(post):
    """Lee y valida los campos comunes sin consultar la base de datos."""
    unidad_id = post.get("unidad_id") or post.get("proyecto_id")
    tipo_solicitud = post.get("tipo_solicitud", "equipo")
    provision_consumibles = post.get("provision_consumibles", "ninguno")
    piezas_por_sesion = normalizar_piezas(post.get("piezas_por_sesion"))
    requisitos_especiales = post.get("requisitos_especiales", "").strip()
    modalidad_servicio = post.get("modalidad_servicio", "")
    intencion_solicitud = post.get("intencion_solicitud", "").strip()[:2500]
    incluye_espacio_solicitado = post.get("incluye_espacio") in VALORES_BOOLEANOS
    metodo_pago = post.get("metodo_pago", "")
    cotizacion_aceptada = post.get("cotizacion_aceptada") in VALORES_BOOLEANOS

    if tipo_solicitud not in {choice[0] for choice in Reserva.TIPO_SOLICITUD_CHOICES}:
        raise ValueError("El tipo de solicitud no es válido")
    if provision_consumibles not in PROVISIONES_VALIDAS:
        raise ValueError("Indica cómo se cubrirán los materiales de la actividad")
    if post.get("aceptar_terminos") not in VALORES_ACEPTACION:
        raise ValueError(
            "Acepta las condiciones de uso, seguridad y responsabilidad antes de enviar"
        )

    proposito_codigo, proposito = normalizar_proposito(
        post.get("proposito_codigo") or post.get("proposito", "")
    )
    if "intencion_solicitud" in post:
        validar_intencion_solicitud(
            intencion_solicitud,
            breve=(
                tipo_solicitud != "servicio"
                and proposito_codigo != "docencia_practica"
            ),
        )

    fecha_inicio_texto = post.get("fecha_inicio")
    fecha_fin_texto = post.get("fecha_fin")
    if not all((unidad_id, fecha_inicio_texto, fecha_fin_texto)):
        raise ValueError("Faltan datos requeridos en el formulario")

    return EntradaBasicaReserva(
        unidad_id=unidad_id,
        tipo_solicitud=tipo_solicitud,
        provision_consumibles=provision_consumibles,
        piezas_por_sesion=piezas_por_sesion,
        requisitos_especiales=requisitos_especiales,
        modalidad_servicio=modalidad_servicio,
        intencion_solicitud=intencion_solicitud,
        incluye_espacio_solicitado=incluye_espacio_solicitado,
        metodo_pago=metodo_pago,
        cotizacion_aceptada=cotizacion_aceptada,
        proposito_codigo=proposito_codigo,
        proposito=proposito,
        fecha_inicio_texto=fecha_inicio_texto,
        fecha_fin_texto=fecha_fin_texto,
    )


def normalizar_intervalo(post, fecha_inicio_texto, fecha_fin_texto):
    """Convierte el calendario enviado en un intervalo local consecutivo."""
    try:
        fecha_inicio = datetime.fromisoformat(fecha_inicio_texto.replace("T", " "))
        fecha_fin = datetime.fromisoformat(fecha_fin_texto.replace("T", " "))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Formato de fecha inválido: {error}") from error

    if fecha_inicio.tzinfo is not None or fecha_fin.tzinfo is not None:
        raise ValueError(
            "Introduce fecha y hora locales de la institucion, sin desplazamiento UTC"
        )
    if fecha_fin <= fecha_inicio or fecha_fin.date() != fecha_inicio.date():
        raise ValueError("Selecciona un horario válido dentro de una misma fecha")

    try:
        horas_json = post.get("horas_seleccionadas")
        horas = json.loads(horas_json) if horas_json else []
        if not isinstance(horas, list) or not horas:
            raise ValueError("Selecciona al menos un horario en el calendario")
        horas = sorted({int(hora) for hora in horas})
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        mensaje = str(error)
        if mensaje == "Selecciona al menos un horario en el calendario":
            raise
        raise ValueError(f"Formato de fecha inválido: {error}") from error

    if any(hora < 0 or hora > 23 for hora in horas):
        raise ValueError("El horario seleccionado no es válido")
    if horas != list(range(min(horas), max(horas) + 1)):
        raise ValueError(
            "Selecciona bloques consecutivos para definir un único horario de reserva"
        )

    hora_inicio = time(min(horas), 0)
    hora_fin = time(max(horas) + 1, 0) if max(horas) < 23 else time(23, 59)
    duracion = int(
        (
            datetime.combine(fecha_inicio.date(), hora_fin)
            - datetime.combine(fecha_inicio.date(), hora_inicio)
        ).total_seconds()
        / 3600
    )
    return IntervaloReserva(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        horas=horas,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        duracion=duracion,
    )


def resolver_seleccion_proceso(post, unidad, tipo_solicitud):
    """Resuelve producto, proceso y escala dentro de la unidad indicada."""
    receta, producto, factor = None, None, None
    producto_id = (post.get("producto_id") or "").strip()
    if producto_id:
        if tipo_solicitud != "recursos":
            raise ValueError("Un producto de planta se solicita como reserva de recursos")
        producto = (
            Producto.objects.filter(
                pk=producto_id,
                unidad=unidad,
                activo=True,
                publico=True,
                tipo__in=Producto.TIPOS_PUBLICOS,
                familia__activa=True,
            ).first()
            if producto_id.isdigit()
            else None
        )
        if producto is None:
            raise ValueError("El producto seleccionado no está disponible en esta unidad")

    receta_id = (post.get("receta_id") or "").strip()
    if receta_id:
        if tipo_solicitud != "recursos":
            raise ValueError("Una práctica por proceso se solicita como reserva de recursos")
        receta = (
            Receta.objects.filter(pk=receta_id, unidad=unidad, activa=True)
            .select_related("producto")
            .first()
            if receta_id.isdigit()
            else None
        )
        if receta is None or not receta.etapas.exists():
            raise ValueError("El proceso seleccionado no está disponible en esta unidad")
        if producto and producto.pk != receta.producto_id:
            raise ValueError("El producto no corresponde al proceso seleccionado")
        producto = receta.producto
        factor = factor_valido(post.get("factor_proceso"))

    return SeleccionProceso(receta=receta, producto=producto, factor=factor)
