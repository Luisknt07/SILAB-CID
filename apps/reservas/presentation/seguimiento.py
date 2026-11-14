"""Línea cronológica institucional de una reserva.

Una reserva recorre siempre las mismas etapas: se envía, el laboratorio la
revisa, queda confirmada, se ejecuta y se cierra. Un desenlace distinto de
«completada» corta la línea en la etapa donde ocurrió y se conserva como
evidencia; nunca desaparece del expediente.

El mismo recorrido alimenta el panel del solicitante y el del laboratorio,
para que ambos vean idéntica información.
"""

from django.utils import timezone


ETAPAS_RESERVA = (
    (
        "solicitud",
        "Solicitud enviada",
        "La unidad recibió la solicitud con sus recursos, horario y documentación.",
    ),
    (
        "revision",
        "Revisión del laboratorio",
        "El laboratorista verifica disponibilidad, recursos, guía y condiciones.",
    ),
    (
        "confirmada",
        "Reserva confirmada",
        "El horario y los recursos quedan reservados a nombre del solicitante.",
    ),
    (
        "ejecucion",
        "Atención en curso",
        "La actividad se realiza en el laboratorio con acompañamiento técnico.",
    ),
    (
        "cierre",
        "Atención finalizada",
        "La unidad registra lo que ocurrió y emite el comprobante final.",
    ),
)

# Desenlaces que interrumpen el recorrido antes de la finalización.
DESENLACES_INTERRUMPIDOS = {
    "rechazada": "Solicitud rechazada",
    "cancelada": "Reserva cancelada",
    "vencida": "Solicitud vencida sin aprobación",
    "no_presentado": "Inasistencia registrada",
    "no_atendida": "No atendida por la unidad",
}


def _momento(valor):
    """Fecha local legible; vacío cuando el hito todavía no ocurrió."""
    if not valor:
        return ""
    if timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return f"{valor:%d/%m/%Y %H:%M}"


def _etapa_actual(estado):
    return {
        "pendiente": "revision",
        "confirmada": "confirmada",
        "en_proceso": "ejecucion",
        "completada": "cierre",
    }.get(estado, "")


def _etapa_detenida(estado, *, aprobada, iniciada):
    """Etapa en la que se detuvo el recorrido de una reserva interrumpida."""
    if estado in {"rechazada", "vencida"}:
        return "revision"
    if estado == "cancelada":
        return "confirmada" if aprobada else "revision"
    return "ejecucion" if iniciada else "confirmada"


def linea_tiempo_reserva(reserva, *, nota_cierre=""):
    """Etapas del ciclo con su situación, fecha y nota para el expediente."""
    estado = reserva.estado
    aprobada = bool(reserva.fecha_validacion) and estado not in {"rechazada", "vencida"}
    iniciada = bool(reserva.fecha_inicio_atencion) or estado in {"en_proceso", "completada"}
    finalizada = estado == "completada"
    interrumpida = estado in DESENLACES_INTERRUMPIDOS

    fechas = {
        "solicitud": _momento(reserva.fecha_reserva),
        "revision": _momento(reserva.fecha_validacion),
        "confirmada": _momento(reserva.fecha_validacion) if aprobada else "",
        "ejecucion": _momento(reserva.fecha_inicio_atencion),
        "cierre": _momento(reserva.fecha_cierre) if finalizada else "",
    }
    alcanzadas = {
        "solicitud": True,
        "revision": estado != "pendiente",
        "confirmada": aprobada,
        "ejecucion": iniciada,
        "cierre": finalizada,
    }
    actual = _etapa_actual(estado)
    detenida = (
        _etapa_detenida(estado, aprobada=aprobada, iniciada=iniciada)
        if interrumpida
        else ""
    )
    codigos = [codigo for codigo, _titulo, _detalle in ETAPAS_RESERVA]
    corte = codigos.index(detenida) if detenida else None

    pasos = []
    for indice, (codigo, titulo, detalle) in enumerate(ETAPAS_RESERVA):
        nota = ""
        if interrumpida:
            if indice < corte:
                situacion = "hecho"
            elif indice == corte:
                situacion = "detenido"
                titulo = DESENLACES_INTERRUMPIDOS[estado]
                detalle = (
                    nota_cierre
                    or "La solicitud se conserva como registro y evidencia; ya no ocupa la agenda."
                )
                nota = reserva.get_estado_display()
            else:
                situacion = "descartado"
        elif codigo == actual:
            situacion = "hecho" if finalizada else "actual"
        elif alcanzadas[codigo]:
            situacion = "hecho"
        else:
            situacion = "pendiente"
        pasos.append(
            {
                "codigo": codigo,
                "titulo": titulo,
                "detalle": detalle,
                "situacion": situacion,
                "fecha": fechas.get(codigo, ""),
                "nota": nota,
            }
        )

    if interrumpida:
        resumen = "interrumpida"
    elif finalizada:
        resumen = "finalizada"
    else:
        resumen = "en_curso"
    hechos = sum(1 for paso in pasos if paso["situacion"] == "hecho")
    return {
        "estado": estado,
        "estado_display": reserva.get_estado_display(),
        "situacion": resumen,
        "etapa_actual": detenida or actual,
        "completadas": hechos,
        "total": len(pasos),
        "pasos": pasos,
    }
