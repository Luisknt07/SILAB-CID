from django.contrib import admin
from django.core.exceptions import PermissionDenied
from apps.core.models.gobernanza import AsignacionGobernanza
from apps.core.presentation.administracion import AdministracionTraducida


@admin.register(AsignacionGobernanza)
class AsignacionGobernanzaAdmin(AdministracionTraducida):
    list_display = ("usuario", "rol", "referencia", "desde", "hasta", "activa")
    list_filter = ("rol", "activa")
    search_fields = ("usuario__username", "acto", "referencia")
    readonly_fields = ("registrado_por", "actualizado_en")

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        if not obj.pk:
            obj.registrado_por = request.user
        obj.full_clean()
        super().save_model(request, obj, form, change)
