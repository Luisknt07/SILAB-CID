"""Adaptadores de formularios; datos, claves y opciones conservan sus valores."""

from django.utils.translation import gettext
from django.forms.models import ModelChoiceField


def _opciones(opciones):
    return [(valor, _opciones(etiqueta) if isinstance(etiqueta, (list, tuple))
             else gettext(str(etiqueta))) for valor, etiqueta in opciones]


class FormularioTraducidoMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        traducir_campos(self)


def traducir_campos(formulario):
    for campo in formulario.fields.values():
        if campo.label:
            campo.label = gettext(str(campo.label))
        if campo.help_text:
            campo.help_text = gettext(str(campo.help_text))
        for atributo in ("placeholder", "title", "aria-label"):
            if atributo in campo.widget.attrs:
                campo.widget.attrs[atributo] = gettext(str(campo.widget.attrs[atributo]))
        campo.error_messages = {codigo: gettext(str(mensaje)) for codigo, mensaje in campo.error_messages.items()}
        if hasattr(campo, "choices"):
            # No materializar ModelChoiceIterator: sus etiquetas son datos del usuario.
            if not isinstance(campo, ModelChoiceField):
                campo.choices = _opciones(campo.choices)
    return formulario
