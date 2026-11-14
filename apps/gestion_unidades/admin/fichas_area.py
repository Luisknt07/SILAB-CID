"""Fichas explicativas de las áreas: qué es, cómo funciona y con qué se trabaja."""
from django import forms
from django.contrib import admin
from django.db.models import TextField

from apps.core.presentation.administracion import AdministracionTraducida, BloqueTraducido

from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.models.unidades import UnidadEquipo


class ElementoFichaAreaInline(BloqueTraducido):
    model = ElementoFichaArea
    extra = 0
    classes = ['collapse']
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 3})}}
    fieldsets = (
        (None, {'fields': (('tipo', 'nivel', 'orden'), ('nombre', 'icono'), 'para_que', ('ejemplo', 'cantidad'), 'solo_referencia')}),
        ('Ficha técnica del equipo', {'fields': ('especificaciones', 'consumibles', 'cuidados', ('foto', 'registrado'))}),
        ('Software y documentación', {'fields': (('licencia', 'url'),)}),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Solo los equipos de la unidad dueña del área.
        if db_field.name == 'registrado':
            ficha_id = request.resolver_match.kwargs.get('object_id') if request.resolver_match else None
            ficha = FichaArea.objects.filter(pk=ficha_id).select_related('espacio').first()
            kwargs['queryset'] = (UnidadEquipo.objects.filter(laboratorio_id=ficha.espacio.unidad_id)
                                  if ficha else UnidadEquipo.objects.none())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(FichaArea)
class FichaAreaAdmin(AdministracionTraducida):
    list_display = ('espacio', 'unidad', 'publicada', 'actualizado_en')
    list_filter = ('publicada', 'espacio__unidad')
    search_fields = ('espacio__nombre', 'espacio__codigo', 'que_es')
    list_editable = ('publicada',)
    autocomplete_fields = ('espacio',)
    inlines = (ElementoFichaAreaInline,)
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 4})}}
    fieldsets = (
        (None, {'fields': ('espacio', 'publicada')}),
        ('La tecnología', {'fields': ('que_es', 'como_funciona', 'principio', 'aplicaciones')}),
        ('El área', {'fields': ('distribucion', 'conexiones', 'seguridad', 'fuente')}),
    )

    @admin.display(description='Unidad', ordering='espacio__unidad__nombre')
    def unidad(self, ficha):
        return ficha.espacio.unidad
