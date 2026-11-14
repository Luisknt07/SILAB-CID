"""Traduccion de etiquetas de presentacion; nunca transforma codigos ni valores."""

from django import template
from django.utils.translation import gettext


register = template.Library()


@register.filter
def ui(valor):
    return gettext(str(valor)) if valor is not None else ""
