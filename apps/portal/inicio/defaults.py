"""Respaldo editorial que conserva la portada existente antes de publicar."""
from dataclasses import asdict
from django.utils.translation import gettext as _, override
from .contracts import PortadaInicio


def portada_base():
    return PortadaInicio(
        lema=_('Ciencia que transforma el futuro'), titulo='',
        resumen=_('Impulsamos investigacion, innovacion, transferencia de conocimiento y tecnologia para el desarrollo sostenible de nuestra region y del pais.'),
        boton_centros=_('Explorar Centros I+D'),
        boton_unidades=_('Explorar Laboratorios y Unidades'),
        mensaje_marca=_('Conocimiento que transforma el territorio'),
    )


def contenido_base():
    datos = {}
    for idioma in ('es', 'en'):
        with override(idioma):
            datos[idioma] = asdict(portada_base())
    return datos
