"""Presentación de escenarios operativos solicitados para desarrollo local."""
from django.conf import settings


def escenario_activo(centro):
    return bool(settings.DEBUG and centro.slug in getattr(settings, 'CENTROS_ID_ESCENARIOS_OPERATIVOS', ()))


def filtro_contenido(centro):
    return {} if escenario_activo(centro) else {'es_muestra': False}


def contenido_admitido(objeto):
    return not objeto.es_muestra or escenario_activo(objeto.centro)
