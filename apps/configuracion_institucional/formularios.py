"""Campos comunes del editor institucional, independientes de cada contrato."""
import json
from django import forms
from django.utils.translation import gettext_lazy as _
from apps.core.identidad import validar_texto


class JsonRevisionField(forms.CharField):
    def prepare_value(self, value):
        return json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return None
        try:
            if len(value) > self.max_length:
                raise ValueError
            return self.serializar(self.validar(self.cargar({self.clave_entorno: value})))
        except (ValueError, TypeError, RecursionError):
            raise forms.ValidationError(self.mensaje_error) from None


class TituloRevisionForm(forms.Form):
    titulo = forms.CharField(label=_('Nombre de la revisión'), max_length=100)

    def clean_titulo(self):
        titulo = self.cleaned_data['titulo']
        try:
            validar_texto(titulo, obligatorio=True)
        except ValueError:
            raise forms.ValidationError(_('Usa un nombre de revisión en texto simple.')) from None
        return titulo
