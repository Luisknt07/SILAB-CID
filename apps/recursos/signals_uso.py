"""Actualizar alertas después de confirmar cambios de actividad, sin enviar mensajes."""
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.reservas.models.reservas import Reserva


@receiver(post_save, sender=Reserva, dispatch_uid='recursos.uso.reserva.guardada')
@receiver(post_delete, sender=Reserva, dispatch_uid='recursos.uso.reserva.eliminada')
def revisar_uso_tras_actividad(sender, instance, **kwargs):
    if kwargs.get('raw') or kwargs.get('update_fields') == frozenset({'codigo_reserva'}):
        return
    from apps.recursos.presentation.traspasos import detectar_equipos_sin_uso

    # Nunca publica una lectura del estado a medio guardar o de una
    # transacción revertida. La lectura inmediata funciona aun sin esta tarea.
    unidad_id = instance.laboratorio_id
    transaction.on_commit(lambda: detectar_equipos_sin_uso(unidad=unidad_id),
                          using=kwargs.get('using'), robust=True)
