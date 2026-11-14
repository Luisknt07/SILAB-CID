from django.contrib import admin

from apps.core.presentation.administracion import AdministracionTraducida
from apps.documentos.models.referencias_indicadores import ReferenciaIndicadorUnidad


@admin.register(ReferenciaIndicadorUnidad)
class ReferenciaIndicadorUnidadAdmin(AdministracionTraducida):
    list_display = ('tipo_unidad', 'codigo', 'nivel_capacidad', 'valor', 'activo', 'actualizado_en', 'actualizado_por')
    list_filter = ('tipo_unidad', 'codigo', 'activo')
    search_fields = ('codigo', 'fundamento')
    fields = ('tipo_unidad', 'codigo', 'nivel_capacidad', 'valor', 'fundamento', 'activo',
              'alcance_del_cambio', 'actualizado_en', 'actualizado_por')
    readonly_fields = ('alcance_del_cambio', 'actualizado_en', 'actualizado_por')

    @admin.display(description='Aplicación del cambio')
    def alcance_del_cambio(self, obj):
        if obj and obj.codigo in ('PRACTICAS-SEMANA', 'PRACTICAS-MINUTOS'):
            return ('Referencia histórica: se conserva para las versiones anteriores. Los planes nuevos usan '
                    'las sesiones y los horarios concretos de la agenda y FT02; esta referencia no interviene en su cálculo.')
        return ('Dirección administra las metas; la unidad no edita los números desde la planificación. '
                'Las prácticas se obtienen de las sesiones concretas de la agenda y FT02, respetando la referencia mínima '
                'por unidad y período. Sus horarios determinan las horas de ocupación, sin imponer una frecuencia semanal '
                'a cada asignatura. El catálogo de asignaturas no constituye carga comprometida. '
                'Las reglas se conservan al guardar y las versiones firmadas mantienen sus metas. '
                'El 100 % de cobertura de seguridad, registro y trazabilidad conserva su definición.')

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    has_change_permission = has_add_permission = has_view_permission

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)
