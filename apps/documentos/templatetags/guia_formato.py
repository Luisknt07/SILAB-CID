"""Presentación segura del contenido estructurado escrito en las guías.

El análisis del texto vive en ``guia_contenido``; aquí solo se enlaza con las
plantillas para que la vista HTML muestre exactamente lo mismo que el PDF y
la vista previa del asistente.
"""

from django import template
from django.utils.safestring import mark_safe

from apps.reservas.presentation.guia_contenido import bloques_enriquecidos, html_bloques, html_procedimiento
from apps.reservas.presentation.guia_firmas import ROLES_FIRMA


register = template.Library()


@register.filter
def guia_richtext(value, figuras=None):
    """Subtítulos, listas, tablas e imágenes sin admitir HTML del usuario."""
    html = html_bloques(bloques_enriquecidos(value), figuras)
    return mark_safe(html or "<p>No registrado</p>")


@register.filter
def guia_procedimiento(contenido):
    """Procedimiento con su formato y los adjuntos de cada paso."""
    contenido = contenido or {}
    return mark_safe(html_procedimiento(
        contenido.get("procedimiento"),
        contenido.get("formato_procedimiento", "numerado"),
        contenido.get("figuras"),
    ))


@register.simple_tag
def firmas_documento(contenido=None):
    """Bloques de firma del FT04; en el asistente (sin guía) solo firma quien elabora."""
    if isinstance(contenido, dict) and contenido.get('firmas_lista'):
        return contenido['firmas_lista']
    estados = {
        'elaborado': 'Aceptación electrónica interna al enviar a revisión',
        'revisado': 'Pendiente de revisión',
        'aprobado': 'Pendiente de aprobación',
    }
    cargos = {'elaborado': 'Docente responsable', 'revisado': '', 'aprobado': ''}
    return [
        {
            'rol': rol,
            'etiqueta': etiqueta,
            'activo': rol == 'elaborado',
            'nombre': '',
            'cargo': cargos[rol],
            'fecha': '',
            'nombre_vista': 'Usuario autenticado',
            'cargo_vista': cargos[rol],
            'estado_vista': estados[rol],
            'fecha_vista': 'Se registra al firmar',
            'verificacion': '',
        }
        for rol, etiqueta in ROLES_FIRMA
    ]
