"""Fuente única del ciclo institucional de una reserva.

El estado de una reserva representa una decisión institucional, no la pantalla
desde la que se gestiona. Las correcciones futuras se modelarán como revisiones
vinculadas; no se añadirán estados transitorios para cada formulario o permiso.
"""

from dataclasses import dataclass


RESERVA_ESTADO_CHOICES = (
    ("pendiente", "Pendiente"),
    ("confirmada", "Confirmada"),
    ("en_proceso", "En Proceso"),
    ("completada", "Completada"),
    ("rechazada", "Rechazada"),
    ("cancelada", "Cancelada"),
    ("no_presentado", "No se Presentó"),
    ("no_atendida", "No atendida por la unidad"),
    ("vencida", "Vencida sin aprobación"),
)

ESTADOS_RESERVA = frozenset(codigo for codigo, _etiqueta in RESERVA_ESTADO_CHOICES)
ESTADOS_OCUPAN_AGENDA = frozenset({"pendiente", "confirmada", "en_proceso"})
ESTADOS_EN_EVALUACION = frozenset({"pendiente"})
ESTADOS_APROBADOS = frozenset({"confirmada", "en_proceso", "completada"})
ESTADOS_EN_EJECUCION = frozenset({"en_proceso"})
ESTADOS_CERRADOS = frozenset(
    {
        "completada",
        "rechazada",
        "cancelada",
        "no_presentado",
        "no_atendida",
        "vencida",
    }
)
ESTADOS_ATENCION_EFECTIVA = frozenset({"completada"})


@dataclass(frozen=True)
class ReglaTransicion:
    """Estados de origen y destino institucional de una acción."""

    origenes: frozenset[str]
    destino: str | None = None
    exige_motivo: bool = False


REGLAS_TRANSICION = {
    "actualizar": ReglaTransicion(frozenset({"pendiente", "confirmada"})),
    "asignar": ReglaTransicion(
        frozenset({"pendiente", "confirmada", "en_proceso"})
    ),
    "aprobar": ReglaTransicion(frozenset({"pendiente"}), "confirmada"),
    "rechazar": ReglaTransicion(
        frozenset({"pendiente"}), "rechazada", exige_motivo=True
    ),
    "cancelar": ReglaTransicion(
        frozenset({"pendiente", "confirmada"}),
        "cancelada",
        exige_motivo=True,
    ),
    "iniciar": ReglaTransicion(frozenset({"confirmada"}), "en_proceso"),
    "completar": ReglaTransicion(
        frozenset({"confirmada", "en_proceso"}), "completada"
    ),
    "no_presentado": ReglaTransicion(
        frozenset({"confirmada", "en_proceso"}),
        "no_presentado",
        exige_motivo=True,
    ),
    "no_atendida": ReglaTransicion(
        frozenset({"confirmada", "en_proceso"}),
        "no_atendida",
        exige_motivo=True,
    ),
    "vencer": ReglaTransicion(frozenset({"pendiente"}), "vencida"),
    "solicitar_info": ReglaTransicion(
        frozenset({"pendiente", "confirmada"}), exige_motivo=True
    ),
    "anotar": ReglaTransicion(ESTADOS_RESERVA, exige_motivo=True),
}


class TransicionReservaNoPermitida(ValueError):
    """Una acción no corresponde al estado institucional actual."""


def estados_permitidos_para_accion(
    accion,
    *,
    puede_corregir_cerradas=False,
    permite_regularizacion=False,
):
    """Retorna orígenes válidos aplicando permisos excepcionales explícitos."""
    regla = REGLAS_TRANSICION.get(accion)
    if regla is None:
        return frozenset()
    permitidos = regla.origenes
    if accion == "actualizar" and puede_corregir_cerradas:
        permitidos = ESTADOS_RESERVA
    if (
        accion in {"completar", "no_presentado", "no_atendida"}
        and puede_corregir_cerradas
        and permite_regularizacion
    ):
        permitidos = permitidos | {"completada"}
    return frozenset(permitidos)


def validar_accion_reserva(
    estado,
    accion,
    *,
    motivo="",
    puede_corregir_cerradas=False,
    permite_regularizacion=False,
):
    """Valida una acción y devuelve su destino, si cambia el estado.

    La función no guarda nada. Así puede utilizarse dentro de una transacción
    tanto desde el panel como desde tareas automáticas y endpoints del usuario.
    """
    regla = REGLAS_TRANSICION.get(accion)
    if regla is None:
        raise TransicionReservaNoPermitida("Selecciona una acción válida.")
    permitidos = estados_permitidos_para_accion(
        accion,
        puede_corregir_cerradas=puede_corregir_cerradas,
        permite_regularizacion=permite_regularizacion,
    )
    if estado not in permitidos:
        raise TransicionReservaNoPermitida(
            f'La acción "{accion}" no corresponde al estado "{estado}".'
        )
    if regla.exige_motivo and not str(motivo or "").strip():
        raise TransicionReservaNoPermitida(
            "Registra el motivo de esta decisión."
        )
    return regla.destino


def etapa_institucional(estado):
    """Agrupa estados técnicos en etapas comprensibles para reportes y UI."""
    if estado in ESTADOS_EN_EVALUACION:
        return "evaluacion"
    if estado == "confirmada":
        return "programacion_confirmada"
    if estado in ESTADOS_EN_EJECUCION:
        return "ejecucion"
    if estado in ESTADOS_CERRADOS:
        return "cierre"
    return "desconocida"
