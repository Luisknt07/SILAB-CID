from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

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
                    'las sesiones y los horarios concretos de la agenda y de la planificación de prácticas; esta referencia '
                    'no interviene en su cálculo.')
        return ('Dirección administra las metas; la unidad no edita los números desde la planificación. '
                'Las prácticas se obtienen de las sesiones concretas de la agenda y de la planificación de prácticas, '
                'respetando la referencia mínima '
                'por unidad y período. Sus horarios determinan las horas de ocupación, sin imponer una frecuencia semanal '
                'a cada asignatura. El catálogo de asignaturas no constituye carga comprometida. '
                'Las reglas se conservan al guardar y las versiones firmadas mantienen sus metas. '
                'Las coberturas de seguridad, registro y trazabilidad parten de 100 % y Dirección puede ajustarlas '
                'con su fundamento en «Metas del período».')

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

    def get_urls(self):
        return [path('metas/', self.admin_site.admin_view(self.metas_del_periodo),
                     name='metas-del-periodo')] + super().get_urls()

    def metas_del_periodo(self, request):
        """Todas las metas en una tabla: un indicador por fila y un tipo de unidad por columna."""
        from apps.documentos.presentation.metas_administracion import guardar_metas, tabla_de_metas

        if not self.has_change_permission(request):
            raise PermissionDenied
        errores = []
        if request.method == 'POST':
            try:
                cambios = guardar_metas(request.POST, request.user)
            except ValidationError as error:
                errores = error.messages
            else:
                if cambios:
                    messages.success(request, f'Se guardaron {len(cambios)} cambios: ' + '; '.join(cambios) + '.')
                else:
                    messages.info(request, 'No hubo cambios que guardar.')
                return redirect('admin:metas-del-periodo')
        contexto = {
            **self.admin_site.each_context(request),
            'title': 'Metas del período',
            'tabla': tabla_de_metas(request.POST if errores else None),
            'errores': errores,
            'fundamento': request.POST.get('fundamento', '') if errores else '',
        }
        return TemplateResponse(request, 'admin/documentos/referenciaindicadorunidad/metas.html', contexto)
