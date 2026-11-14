"""Captura de una prueba funcional específica, con equipo y criterio verificables."""
from django import forms

from apps.documentos.models.funcionalidad import RESULTADOS_FUNCIONALES, equipos_del_alcance


def campos_funcionalidad(unidad):
    return dict(
        equipo_id=forms.ModelChoiceField(required=False,
            queryset=equipos_del_alcance(unidad).filter(activa=True, fecha_baja__isnull=True).select_related('equipo'),
            label='Equipo del laboratorio o compartido'),
        procedimiento=forms.CharField(required=False, max_length=3000, label='Prueba o procedimiento realizado',
            widget=forms.Textarea(attrs={'rows': 3})),
        criterio=forms.CharField(required=False, max_length=1500, label='Criterio de aceptación o referencia técnica',
            widget=forms.Textarea(attrs={'rows': 2}),
            help_text='Indica qué debía comprobarse, con su límite, especificación o referencia cuando corresponda.'),
        resultado_funcional=forms.ChoiceField(required=False, label='Resultado de la prueba funcional',
            choices=[('', 'Selecciona el resultado documentado')] + list(RESULTADOS_FUNCIONALES)),
        hallazgos_funcionales=forms.CharField(required=False, max_length=3000,
            label='Hallazgos, limitaciones o fallas', widget=forms.Textarea(attrs={'rows': 3}),
            help_text='Obligatorio cuando el equipo presenta observaciones o no está operativo.'))
