"""Traduccion de etiquetas de presentacion; nunca transforma codigos ni valores."""

from django import template
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.utils.translation import gettext

from apps.core.estaticos import nombre_catalogo_js


register = template.Library()


@register.simple_tag
def catalogo_javascript_url(idioma):
    """Dirección del catálogo de traducciones para JavaScript.

    En producción es un estático con huella que se genera al recopilar; en
    desarrollo y en pruebas, la vista que lo calcula en cada petición.
    """
    idioma = str(idioma or settings.LANGUAGE_CODE).split('-')[0]
    nombre = nombre_catalogo_js(idioma)
    publicados = getattr(staticfiles_storage, 'hashed_files', None)
    if not settings.DEBUG and publicados and staticfiles_storage.hash_key(nombre) in publicados:
        return staticfiles_storage.url(nombre)
    return reverse('javascript_catalog') + '?language=' + idioma


@register.filter
def ui(valor):
    return gettext(str(valor)) if valor is not None else ""
