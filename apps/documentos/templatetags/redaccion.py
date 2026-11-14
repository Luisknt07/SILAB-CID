"""Filtros del editor guiado del expediente."""

from django import template

register = template.Library()


@register.filter
def get_item(valor, clave):
    """Acceso por clave a diccionarios en la plantilla (`{{ fila|get_item:col }}`)."""
    if isinstance(valor, dict):
        resultado = valor.get(clave)
        return '' if resultado is None else resultado
    return ''
