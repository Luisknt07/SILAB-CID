"""Proveedor local y fallo cerrado; no importa una app operativa al cargar."""
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from importlib import import_module

from django.conf import settings
from django.db import DatabaseError, transaction
from django.core.exceptions import PermissionDenied

from apps.core.capacidades import ControlCapacidad

logger = logging.getLogger(__name__)
_bloqueadas = ContextVar('capacidades_bloqueadas', default=None)


def proveedor_habilitacion():
    ruta = getattr(settings, 'CAPABILITY_STATE_PROVIDER', '')
    if not ruta:
        return None
    if ruta != 'apps.configuracion_institucional.capacidades.selectors':
        raise ValueError('El proveedor de habilitacion no esta registrado.')
    return import_module(ruta)


def control_actual(modulo, capacidad):
    from config.capacidades import controles_de_despliegue

    try:
        control = controles_de_despliegue(getattr(settings, 'CAPABILITY_CONTROLS', {}))[f'{modulo}.{capacidad}']
        if not control.autoriza(True):
            return control
        bloqueadas = _bloqueadas.get() or {}
        if (modulo, capacidad) in bloqueadas:
            habilitada = bloqueadas[modulo, capacidad]
        else:
            proveedor = proveedor_habilitacion()
            habilitada = proveedor.habilitacion_actual(modulo, capacidad) if proveedor else True
        if type(habilitada) is not bool:
            raise ValueError('El proveedor requiere un estado booleano.')
        return replace(control, habilitada=control.habilitada and habilitada)
    except (ValueError, KeyError, DatabaseError):
        logger.warning('Politica de capacidades invalida; se bloquea la operacion solicitada.')
        return ControlCapacidad(modulo, capacidad, disponible=False, habilitada=False, derecho=False)


@contextmanager
def con_capacidad_bloqueada(modulo, capacidad):
    existentes = _bloqueadas.get() or {}
    if (modulo, capacidad) in existentes:
        if not control_actual(modulo, capacidad).autoriza(True):
            raise PermissionDenied
        yield
        return
    try:
        proveedor = proveedor_habilitacion()
    except ValueError:
        raise PermissionDenied from None
    with transaction.atomic():
        try:
            if proveedor:
                bloquear = getattr(
                    proveedor,
                    'bloquear_operacion',
                    proveedor.bloquear_habilitacion,
                )
                estado = bloquear(modulo, capacidad)
            else:
                estado = None
            valor = estado.habilitada if estado else True
            if type(valor) is not bool:
                raise ValueError('El proveedor requiere un estado booleano.')
        except (ValueError, DatabaseError):
            logger.warning('Habilitacion institucional no disponible; se bloquea la escritura.')
            raise PermissionDenied from None
        token = _bloqueadas.set({**existentes, (modulo, capacidad): valor})
        try:
            if not control_actual(modulo, capacidad).autoriza(True):
                raise PermissionDenied
            yield
        finally:
            _bloqueadas.reset(token)
