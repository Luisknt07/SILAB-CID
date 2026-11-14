"""Lectura fresca y bloqueos coordinados para operacion y habilitacion."""
import hashlib

from django.db import IntegrityError, transaction
from django.db import connection

from apps.core.presentation.identidad import identidad_de_despliegue
from .models import EstadoCapacidad


def identificacion(modulo, capacidad):
    from config.capacidades import CAPACIDADES_CONTROLADAS

    if (modulo, capacidad) not in CAPACIDADES_CONTROLADAS:
        raise ValueError('La capacidad no tiene controles de servidor implementados.')
    producto, institucion = identidad_de_despliegue()
    return {'producto_codigo': producto.codigo, 'institucion_codigo': institucion.siglas,
            'modulo': modulo, 'capacidad': capacidad}


def estado_actual(modulo, capacidad):
    estado = EstadoCapacidad.objects.filter(**identificacion(modulo, capacidad)).first()
    return (estado.habilitada, estado.version) if estado else (True, 0)


def habilitacion_actual(modulo, capacidad):
    return estado_actual(modulo, capacidad)[0]


def _clave_bloqueo(datos):
    texto = '|'.join((
        datos['producto_codigo'],
        datos['institucion_codigo'],
        datos['modulo'],
        datos['capacidad'],
    ))
    return int.from_bytes(hashlib.sha256(texto.encode()).digest()[:8], 'big', signed=True)


def _bloquear_advisory(datos, *, compartido):
    if connection.vendor != 'postgresql':
        return False
    funcion = 'pg_advisory_xact_lock_shared' if compartido else 'pg_advisory_xact_lock'
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT {funcion}(%s)', [_clave_bloqueo(datos)])
    return True


def bloquear_operacion(modulo, capacidad):
    """Permite escritores concurrentes y los coordina con la suspension."""
    datos = identificacion(modulo, capacidad)
    if not _bloquear_advisory(datos, compartido=True):
        return bloquear_habilitacion(modulo, capacidad)
    estado = EstadoCapacidad.objects.filter(**datos).first()
    return estado or EstadoCapacidad(**datos)


def bloquear_habilitacion(modulo, capacidad):
    datos = identificacion(modulo, capacidad)
    _bloquear_advisory(datos, compartido=False)
    try:
        return EstadoCapacidad.objects.select_for_update().get(**datos)
    except EstadoCapacidad.DoesNotExist:
        try:
            with transaction.atomic():
                EstadoCapacidad(**datos).save(_desde_control=True)
        except IntegrityError:
            pass  # Otro escritor materializo el estado inicial con la misma clave.
        return EstadoCapacidad.objects.select_for_update().get(**datos)
