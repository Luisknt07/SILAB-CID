"""Autoridad de escritores internos; no representa habilitacion comercial.

El llamador debe cargar y bloquear la reserva vigente dentro de su transaccion.
No concede derechos ni instala controles de suspension de toda la capacidad.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext

from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, puede_operar_reservas_unidad


def exigir_autoridad_reserva(reserva, actor, *, operacion, unidad_esperada=None):
    """Revalida cuenta persistida y delegacion de la unidad de la fila fresca."""
    if operacion not in {
        'completar_sesion', 'aplicar_cambio', 'cerrar_operacion', 'enviar_propuesta',
        'autorizar_cambio', 'rechazar_cambio', 'retirar_cambio',
        'solicitar_cambio', 'cancelar_propia',
        'asignar_responsable', 'anotar_reserva', 'solicitar_informacion',
        'rechazar_reserva', 'cancelar_reserva',
        'aprobar_reserva',
        'transicionar_reserva_operativa',
        'corregir_reserva',
    }:
        raise ValueError('Operacion de autoridad no definida.')
    mensaje = gettext('No tienes autorización para modificar esta reserva.')
    if unidad_esperada is not None and reserva.laboratorio_id != unidad_esperada:
        raise PermissionDenied(mensaje)
    if not actor or not actor.is_authenticated or not actor.pk:
        raise PermissionDenied(mensaje)
    vigente = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if vigente is None:
        raise PermissionDenied(mensaje)
    if operacion in {'enviar_propuesta', 'retirar_cambio', 'solicitar_cambio', 'cancelar_propia'}:
        permitida = reserva.usuario_id == vigente.pk
    elif operacion == 'completar_sesion':
        permitida = reserva.usuario_id == vigente.pk or puede_operar_modulo_unidad(
            vigente, reserva.laboratorio, 'practicas')
    else:
        permitida = puede_operar_reservas_unidad(vigente, reserva.laboratorio)
    if not permitida:
        raise PermissionDenied(mensaje)
    return vigente
