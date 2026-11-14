"""Registro de desechos peligrosos y especiales por unidad."""

from django.contrib import admin

from apps.core.presentation.administracion import AdministracionTraducida

from apps.recursos.models.desechos import RegistroDesecho


@admin.register(RegistroDesecho)
class RegistroDesechoAdmin(AdministracionTraducida):
    list_display = (
        'fecha_generacion', 'unidad', 'nombre', 'clase', 'clave_listado', 'cantidad_con_unidad',
        'etapa', 'gestor_autorizado', 'manifiesto',
    )
    # La unidad primero y solo las que el queryset contiene: cada tipo de unidad
    # lista las suyas.
    list_filter = (('unidad', admin.RelatedOnlyFieldListFilter), 'clase', 'etapa', 'estado_fisico',
                   'fecha_generacion')
    search_fields = ('nombre', 'clave_listado', 'origen', 'gestor_autorizado', 'manifiesto')
    date_hierarchy = 'fecha_generacion'
    autocomplete_fields = ()
    readonly_fields = ('registrado_por', 'creado_en', 'actualizado_en')
    fieldsets = (
        ('Qué se generó', {
            'fields': ('unidad', 'fecha_generacion', 'nombre', 'clase', 'clave_listado', 'origen',
                       'estado_fisico', ('cantidad', 'unidad_medida')),
        }),
        ('Envase y almacenamiento', {
            'fields': ('envase', 'etiquetado', 'almacenamiento', 'etapa'),
        }),
        ('Entrega al gestor autorizado', {
            'fields': ('fecha_entrega', 'gestor_autorizado', 'licencia_gestor', 'manifiesto', 'documento'),
            'description': 'Para registrar una entrega se requieren fecha, gestor, licencia o autorización, '
                           'número de manifiesto, archivo de respaldo y responsable. La unidad verifica '
                           'que la autorización corresponda al tipo de desecho entregado.',
        }),
        ('Responsables y notas', {
            'fields': ('responsable', 'observaciones', 'registrado_por', 'creado_en', 'actualizado_en'),
        }),
    )

    @admin.display(description='Cantidad', ordering='cantidad')
    def cantidad_con_unidad(self, obj):
        return f'{obj.cantidad:g} {obj.get_unidad_medida_display()}'

    def save_model(self, request, obj, form, change):
        if not obj.registrado_por_id:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
