"""Politicas declaradas por despliegue; solo capacidades con controles completos.

No instala codigo ni ofrece configuracion comercial editable por la institucion.
La habilitacion institucional persistente se integrara en su propio bloque.
"""
from dataclasses import replace
import json

from apps.core.capacidades import ControlCapacidad
from config.modulos import registro_de_despliegue


CAPACIDADES_CONTROLADAS = (
    ('portal', 'portada_inicio'),
    ('reservas', 'reservas_operativas'),
)


def controles_de_despliegue(configuracion):
    if not isinstance(configuracion, dict):
        raise ValueError('La politica de capacidades requiere un objeto de controles.')
    registro = registro_de_despliegue()
    controles = {}
    for modulo, capacidad in CAPACIDADES_CONTROLADAS:
        if modulo not in registro.manifiestos or capacidad not in registro.manifiestos[modulo].capacidades:
            raise ValueError('La capacidad controlada no pertenece al registro de despliegue.')
        controles[f'{modulo}.{capacidad}'] = ControlCapacidad(modulo, capacidad)
    if set(configuracion) - set(controles):
        raise ValueError('La politica incluye capacidades sin controles de servidor implementados.')
    for identificador, valores in configuracion.items():
        if (not isinstance(valores, dict) or set(valores) - {'disponible', 'habilitada', 'derecho'}
                or any(type(v) is not bool for v in valores.values())):
            raise ValueError('Los controles solo admiten disponibilidad, habilitacion y derecho booleanos.')
        controles[identificador] = replace(controles[identificador], **valores)
    return controles


def configuracion_capacidades(valor):
    def sin_duplicados(pares):
        resultado = {}
        for clave, dato in pares:
            if clave in resultado:
                raise ValueError('La politica no admite claves duplicadas.')
            resultado[clave] = dato
        return resultado

    try:
        if not isinstance(valor, str) or len(valor) > 4096:
            raise ValueError
        datos = json.loads(valor, object_pairs_hook=sin_duplicados)
    except (TypeError, ValueError):
        raise ValueError('La politica de capacidades debe ser JSON valido.') from None
    controles_de_despliegue(datos)
    return datos
