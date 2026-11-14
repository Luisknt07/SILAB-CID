"""Campos de archivo con vista previa, sin alterar carga ni permisos."""
from django import forms


class LogoPreviewInput(forms.ClearableFileInput):
    template_name = 'configuracion_institucional/logo_widget.html'
