"""Autoridad institucional para las operaciones que modifican reservas."""

from contextlib import contextmanager
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.core.management.base import CommandError
from django.utils.translation import gettext

from apps.core.presentation.capacidades import (
    con_capacidad_bloqueada,
    control_actual,
)


MODULO_RESERVAS = "reservas"
CAPACIDAD_RESERVAS = "reservas_operativas"
MENSAJE_SUSPENDIDA = (
    "La operación de reservas está suspendida temporalmente por la institución."
)


class CapacidadReservasSuspendida(PermissionDenied):
    """Distingue la suspensión institucional de un permiso de negocio."""


def mensaje_capacidad_suspendida():
    return gettext(
        "La operación de reservas está suspendida temporalmente por la institución."
    )


def reservas_habilitadas():
    """Consulta fresca; sirve para presentación y procesos que pueden omitirse."""
    return control_actual(MODULO_RESERVAS, CAPACIDAD_RESERVAS).autoriza(True)


def exigir_reservas_habilitadas():
    if not reservas_habilitadas():
        raise CapacidadReservasSuspendida(mensaje_capacidad_suspendida())


@contextmanager
def bloquear_operacion_reservas():
    """Bloquea la autoridad sin confundir denegaciones del caso de uso."""
    entrada_completa = False
    try:
        with con_capacidad_bloqueada(MODULO_RESERVAS, CAPACIDAD_RESERVAS):
            entrada_completa = True
            yield
    except PermissionDenied:
        if entrada_completa:
            raise
        raise CapacidadReservasSuspendida(mensaje_capacidad_suspendida()) from None


def operacion_reservas(funcion):
    """Bloquea el estado antes de abrir la transacción propia del caso de uso."""

    @wraps(funcion)
    def protegida(*args, **kwargs):
        with bloquear_operacion_reservas():
            return funcion(*args, **kwargs)

    return protegida


def comando_reservas(funcion):
    """Traduce la suspensión a una salida CLI operativa y sin traceback."""

    @wraps(funcion)
    def ejecutar(*args, **kwargs):
        try:
            with bloquear_operacion_reservas():
                return funcion(*args, **kwargs)
        except CapacidadReservasSuspendida as error:
            raise CommandError(str(error)) from None

    return ejecutar
