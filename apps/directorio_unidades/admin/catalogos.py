"""Registro administrativo del SLCID."""

from apps.core.presentation.administracion import AdministracionTraducida
from apps.core.presentation.tipologias import idioma_actual, tipologias_actuales

from django import forms
from django.contrib import admin
from django.db.models import Count

from apps.directorio_unidades.models.core import Categoria, TipoLaboratorio


class ClasificacionInstitucionalForm(forms.ModelForm):
    """Las tipologias se eligen del catalogo; vacio significa todas."""

    tipologias = forms.MultipleChoiceField(
        label='Tipologías', required=False, widget=forms.CheckboxSelectMultiple,
        help_text='Códigos de tipología donde se ofrece; vacío significa todas.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        idioma = idioma_actual()
        self.fields['tipologias'].choices = [
            (t.codigo, t.etiqueta(idioma, plural=True)) for t in tipologias_actuales()
        ]

    def clean_tipologias(self):
        return list(self.cleaned_data.get('tipologias') or [])


class ClasificacionInstitucionalAdmin(AdministracionTraducida):
    """Crear, editar, ordenar y archivar; eliminar solo sin unidades."""

    form = ClasificacionInstitucionalForm
    list_display = ['nombre', 'codigo', 'orden', 'activa', 'total_unidades']
    list_filter = ['activa']
    search_fields = ['nombre', 'codigo']
    ordering = ['orden', 'nombre']
    fields = ['nombre', 'codigo', 'descripcion', 'orden', 'activa', 'tipologias']
    actions = None

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(total_unidades=Count('unidades', distinct=True))

    @admin.display(description='Unidades', ordering='total_unidades')
    def total_unidades(self, obj):
        return obj.total_unidades

    def get_readonly_fields(self, request, obj=None):
        return ['codigo'] if obj else []

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.unidades.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Categoria)
class CategoriaAdmin(ClasificacionInstitucionalAdmin):
    pass


@admin.register(TipoLaboratorio)
class TipoLaboratorioAdmin(ClasificacionInstitucionalAdmin):
    pass
