"""Contrato ``lectura_dispositivo_v1``: validación y registro de un lote de lecturas.

Cada lectura es ``{"canal": "<clave>", "instante": "<ISO 8601 con zona>", "valor": <número>}``.
El lote se acepta por partes: las lecturas válidas se guardan y las demás se
devuelven con su posición y el motivo, para que el dispositivo no reenvíe todo.
"""
import math
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.conexiones.models import CanalMedicion, DispositivoConectado, LecturaCanal

MAX_LECTURAS_POR_LOTE = 500
# Un dispositivo sin conexión puede guardar lecturas y enviarlas después.
ANTIGUEDAD_MAXIMA = timedelta(days=30)
# Tolerancia para relojes adelantados.
ADELANTO_MAXIMO = timedelta(minutes=5)


class LoteInvalido(ValueError):
    """El cuerpo no tiene la forma del contrato; no se guardó nada."""


def _instante(valor, ahora):
    if not isinstance(valor, str) or len(valor) > 40:
        return None, 'instante ausente o con formato no admitido'
    try:
        instante = parse_datetime(valor)
    except ValueError:
        instante = None
    if instante is None:
        return None, 'instante ausente o con formato no admitido'
    if timezone.is_naive(instante):
        return None, 'el instante debe indicar su zona horaria'
    if instante > ahora + ADELANTO_MAXIMO:
        return None, 'instante en el futuro'
    if instante < ahora - ANTIGUEDAD_MAXIMA:
        return None, 'instante demasiado antiguo'
    return instante, ''


def registrar_lote(dispositivo, datos, ahora=None):
    """Guarda las lecturas válidas del lote y devuelve el resumen que recibe el dispositivo."""
    ahora = ahora or timezone.now()
    lecturas = datos.get('lecturas') if isinstance(datos, dict) else None
    if not isinstance(lecturas, list) or not lecturas:
        raise LoteInvalido('El cuerpo debe ser un objeto con la lista «lecturas».')
    if len(lecturas) > MAX_LECTURAS_POR_LOTE:
        raise LoteInvalido(f'Cada envío admite hasta {MAX_LECTURAS_POR_LOTE} lecturas.')

    canales = {canal.clave: canal for canal in CanalMedicion.objects.filter(dispositivo=dispositivo, activo=True)}
    rechazadas, validas = [], {}
    fuera_de_rango = 0
    for posicion, lectura in enumerate(lecturas):
        if not isinstance(lectura, dict):
            rechazadas.append({'posicion': posicion, 'motivo': 'cada lectura debe ser un objeto'})
            continue
        canal = canales.get(lectura.get('canal')) if isinstance(lectura.get('canal'), str) else None
        if canal is None:
            rechazadas.append({'posicion': posicion, 'motivo': 'canal desconocido o inactivo'})
            continue
        valor = lectura.get('valor')
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
            rechazadas.append({'posicion': posicion, 'motivo': 'el valor debe ser un número finito'})
            continue
        instante, motivo = _instante(lectura.get('instante'), ahora)
        if instante is None:
            rechazadas.append({'posicion': posicion, 'motivo': motivo})
            continue
        # Dentro del mismo lote prevalece la última lectura de un canal e instante.
        validas[(canal.pk, instante)] = LecturaCanal(canal=canal, instante=instante, valor=float(valor))
        fuera_de_rango += canal.fuera_de_rango(valor)

    por_canal = {}
    for canal_id, instante in validas:
        por_canal.setdefault(canal_id, []).append(instante)
    with transaction.atomic():
        # Solo se consultan los instantes del lote: el índice único los resuelve sin recorrer la serie.
        repetidas = sum(
            LecturaCanal.objects.filter(canal_id=canal_id, instante__in=instantes).count()
            for canal_id, instantes in por_canal.items()
        )
        if validas:
            LecturaCanal.objects.bulk_create(validas.values(), ignore_conflicts=True)
        DispositivoConectado.objects.filter(pk=dispositivo.pk).update(ultima_senal=ahora)
    return {
        'aceptadas': len(validas) - repetidas,
        'repetidas': repetidas,
        'fuera_de_rango': fuera_de_rango,
        'rechazadas': rechazadas,
    }
