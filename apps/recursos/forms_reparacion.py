"""Formulario acotado al activo de la incidencia; los datos institucionales no se repiten."""
from django import forms

from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo, ServicioReparacionEquipo
from apps.recursos.models.equipos import PiezaEquipo


class DiagnosticoIncidenciaForm(forms.ModelForm):
    class Meta:
        model = DiagnosticoIncidenciaEquipo
        exclude = ('incidencia', 'evaluada_por', 'actualizado_en')

    def __init__(self, *args, incidencia, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.incidencia = incidencia
        self.fields['pieza'].queryset = PiezaEquipo.objects.filter(equipo=incidencia.equipo.equipo)
        self.fields['servicio'].queryset = ServicioReparacionEquipo.objects.filter(activo=True, familias=incidencia.equipo.equipo.familia_id).distinct()
