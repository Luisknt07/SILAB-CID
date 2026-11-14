from django import template

from apps.core.panel_trabajo import PREFIJOS_TRABAJO

register = template.Library()


@register.simple_tag
def rutas_panel_trabajo():
    return list(PREFIJOS_TRABAJO)
