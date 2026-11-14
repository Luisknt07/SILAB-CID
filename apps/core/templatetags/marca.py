from django import template
from apps.core.presentation.identidad import fuentes_logo
from apps.core.paleta import componentes_paleta

register = template.Library()

register.filter('componentes_paleta', componentes_paleta)


@register.inclusion_tag('portal/components/marca_institucional.html')
def marca_institucional(institucion, fondo='claro'):
    return {'institucion': institucion, **fuentes_logo(institucion, fondo=fondo)}


@register.inclusion_tag('portal/components/marca_institucional.html')
def marca_secundaria(institucion):
    return {'institucion': institucion, **fuentes_logo(institucion, secundario=True)}


@register.simple_tag
def url_marca_institucional(institucion, fondo='claro'):
    return fuentes_logo(institucion, fondo=fondo)['escritorio']
