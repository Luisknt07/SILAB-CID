"""Registro de motores por caso; las reglas anteriores conservan su implementación.

La selección es explícita: una versión desconocida se consulta mediante la
observación persistida, sin reinterpretarla al desplegar escenarios nuevos.
"""

from copy import deepcopy

from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as distribucion
from apps.laboratorios.operacion.presentation import logistica_operaciones_motor as operaciones

CASOS = {**operaciones.CASOS, **distribucion.CASOS}


def motor(caso):
    if not isinstance(caso, str) or caso not in CASOS:
        raise ValueError("Caso de operaciones inválido.")
    return distribucion if caso in distribucion.CASOS else operaciones


def version(caso):
    return motor(caso).VERSION


def version_caso(caso):
    return motor(caso).VERSION_CASO


def vigente(caso, version_motor, version_escenario):
    return (
        caso in CASOS
        and version(caso) == version_motor
        and version_caso(caso) == version_escenario
    )


def catalogo():
    return [
        {
            **deepcopy(fila),
            "version_motor": version(fila["id"]),
            "version_caso": version_caso(fila["id"]),
        }
        for fila in operaciones.catalogo() + distribucion.catalogo()
    ]


def crear_estado(caso="almacen-trazabilidad", semilla=42):
    return motor(caso).crear_estado(caso, semilla)


def actuar(estado, decision):
    return motor(estado.get("caso")).actuar(estado, decision)


def observacion(estado):
    return motor(estado.get("caso")).observacion(estado)


def resultado(estado):
    return motor(estado.get("caso")).resultado(estado)
