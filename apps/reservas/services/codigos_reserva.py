"""Asignacion/reconciliacion interna; permisos corresponden al llamador.

No importa modelos, vistas o dominios al cargar. No modifica un codigo existente
y limita la transaccion a una reserva; no publica datos en logs.
"""
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)
EVENTO_ASIGNACION_FALLIDA = 'reserva_codigo_asignacion_fallida'
EVENTO_RECUPERACION_FALLIDA = 'reserva_codigo_recuperacion_fallida'


@dataclass(frozen=True, slots=True)
class ResultadoCodigoReserva:
    codigo: str
    asignado: bool


class ReservaFueraDeAlcance(ValueError):
    """La reserva ya no pertenece a la unidad confirmada por el operador."""


def asegurar_codigo_reserva(reserva, *, using=None, unidad_esperada=None):
    """Lee fila fresca bajo bloqueo y escribe solo si falta codigo.

    Atomic abre un savepoint si el llamador ya tiene transaccion. Una excepcion
    se propaga al llamador despues de revertir esta asignacion, sin invalidar su
    transaccion. La señal decide mantener el comportamiento no bloqueante.
    """
    from django.apps import apps
    from django.db import router, transaction

    if reserva.pk is None or reserva._state.adding:
        raise ValueError('La reserva debe estar persistida.')
    modelo = apps.get_model('reservas', 'Reserva')
    alias = using or reserva._state.db or router.db_for_write(modelo, instance=reserva)
    with transaction.atomic(using=alias):
        persistida = modelo._base_manager.using(alias).select_for_update().only(
            'pk', 'laboratorio_id', 'codigo_reserva').get(pk=reserva.pk)
        if unidad_esperada is not None and persistida.laboratorio_id != unidad_esperada:
            raise ReservaFueraDeAlcance('La reserva no pertenece al alcance confirmado.')
        asignado = not bool(persistida.codigo_reserva)
        codigo = persistida.codigo_reserva or persistida.construir_codigo_reserva()
        if asignado:
            modelo._base_manager.using(alias).filter(pk=persistida.pk).update(codigo_reserva=codigo)
    # No anticipa exito en memoria cuando el savepoint fracasa.
    reserva.codigo_reserva = codigo
    return ResultadoCodigoReserva(codigo, asignado)
