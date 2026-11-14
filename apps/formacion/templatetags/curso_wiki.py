"""Filtros del aula para el renderer opt-in; el parser compartido vive en el dominio."""

from django import template
from django.utils.safestring import mark_safe

from apps.formacion.presentation.wiki_curso import es_wiki as contenido_es_wiki, html_wiki

register = template.Library()


@register.filter
def es_wiki(contenido):
    return contenido_es_wiki(contenido)


@register.filter
def curso_wiki(contenido):
    """Sólo se marca el HTML que construye y escapa nuestro renderer."""
    return mark_safe(html_wiki(contenido))


@register.filter
def video_bienvenida_wiki(leccion, curso):
    """Recursos accesibles sólo para el video propio identificado, sin alterar otros cursos."""
    return bool(
        getattr(curso, 'nombre', '') == 'Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial'
        and getattr(leccion, 'titulo', '') == 'Bienvenida: tu ruta para crear una aplicación logística'
        and getattr(leccion, 'tipo', '') == 'video'
        and getattr(leccion, 'archivo', None)
        and not getattr(leccion, 'video_id', None)
    )
