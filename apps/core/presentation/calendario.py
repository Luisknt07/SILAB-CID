"""Proveedores Django del calendario; no consultan datos durante el arranque."""

from django.conf import settings

from apps.core.calendario import politica_calendario
from .calendario_institucional import calendario_en_contexto


def calendario_actual():
    return calendario_en_contexto() or calendario_de_despliegue()


def calendario_de_despliegue():
    return politica_calendario(settings.ACADEMIC_CALENDAR)


def ciclos():
    try:
        politica = calendario_actual()
    except (ValueError, AttributeError):
        return ()  # E004 diagnostica y bloquea el arranque normal.
    return tuple((c, etiqueta) for c, etiqueta, _ in politica.ciclos + politica.ciclos_historicos)


def ambitos():
    try:
        politica = calendario_actual()
    except (ValueError, AttributeError):
        return ()
    return politica.ambitos + politica.ambitos_historicos


def ambitos_operacion():
    return calendario_actual().ambitos_operacion


def ambito_predeterminado():
    return calendario_actual().ambito_predeterminado


def semanas_predeterminadas():
    return calendario_actual().semanas_predeterminadas
