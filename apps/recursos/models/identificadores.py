"""Identificadores que los modelos necesitan validar sin depender de la capa de aplicación.

El código del bien de bodega llega con el prefijo institucional de la etiqueta («23300000000-37881242») y se
guarda sin él; un video de manejo se identifica por su id de YouTube. Los dominios (codigos_equipo,
plantillas_ficha) usan estas mismas funciones: una sola regla para los modelos y para las vistas.
"""
import re

from django.conf import settings

PREFIJO_INSTITUCIONAL = getattr(settings, 'PREFIJO_BIENES_INSTITUCION', '23300000000')
# Las etiquetas de bodega son «<prefijo de la Universidad>-<código del bien>»; otro prefijo no es un bien propio.
_CON_PREFIJO = re.compile(rf'^\s*({re.escape(PREFIJO_INSTITUCIONAL)})\s*-\s*([A-Za-z0-9]+)\s*$')
_YOUTUBE = re.compile(r'(?:youtu\.be/|v=|embed/|shorts/|live/)([A-Za-z0-9_-]{11})')


def limpiar_codigo_bien(texto):
    """El código del bien sin espacios ni prefijo institucional («23300000000-37881242» → «37881242»)."""
    texto = (texto or '').strip()
    coincidencia = _CON_PREFIJO.match(texto)
    # En mayúsculas: el índice único distingue mayúsculas y un código escrito en minúsculas sería otro.
    return (coincidencia.group(2) if coincidencia else texto).upper()


def youtube_id(url):
    """El id de un video de YouTube en cualquiera de sus direcciones; vacío si no es una."""
    coincidencia = _YOUTUBE.search(url or '')
    return coincidencia.group(1) if coincidencia else ''
