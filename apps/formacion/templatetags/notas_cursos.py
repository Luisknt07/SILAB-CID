"""Presentación de notas del curso sobre diez; el almacenamiento sigue sobre cien."""
from django import template

from apps.formacion.presentation.notas_cursos import nota_sobre_diez

register = template.Library()


@register.filter
def sobre_diez(valor):
    return nota_sobre_diez(valor)
