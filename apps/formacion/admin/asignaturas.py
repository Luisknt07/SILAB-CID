"""Administración del sílabo práctico que cada unidad lleva a reservas."""

from apps.core.presentation.administracion import AdministracionTraducida, BloqueTraducido

from django.contrib import admin

from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura


class TemaAsignaturaInline(BloqueTraducido):
    model = TemaAsignatura
    extra = 0
    autocomplete_fields = ('receta',)
    filter_horizontal = ('software',)
    fields = ('orden', 'nombre', 'receta', 'software', 'ejercicios', 'resultado_aprendizaje')
    classes = ('collapse',)


@admin.register(Asignatura)
class AsignaturaAdmin(AdministracionTraducida):
    list_display = ('codigo', 'nombre', 'unidad', 'carrera', 'semestre', 'periodo', 'docente', 'activa')
    list_filter = ('activa', 'unidad', 'carrera', 'semestre', 'periodo')
    search_fields = ('codigo', 'nombre', 'carrera', 'descripcion')
    autocomplete_fields = ('unidad', 'periodo', 'docente')
    list_editable = ('activa',)
    ordering = ('unidad', 'nombre', 'pk')
    inlines = (TemaAsignaturaInline,)


@admin.register(TemaAsignatura)
class TemaAsignaturaAdmin(AdministracionTraducida):
    list_display = ('nombre', 'asignatura', 'orden', 'receta')
    list_filter = ('asignatura__unidad', 'asignatura')
    search_fields = ('nombre', 'asignatura__nombre', 'asignatura__codigo', 'resultado_aprendizaje')
    autocomplete_fields = ('asignatura', 'receta')
    filter_horizontal = ('software',)
    ordering = ('asignatura', 'orden', 'pk')
