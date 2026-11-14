from django.contrib import admin
from .models import Movimiento, Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "unidad", "existencia", "minimo"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["existencia"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "producto", "tipo", "cantidad", "usuario", "motivo"]
    readonly_fields = [
        "producto",
        "tipo",
        "cantidad",
        "motivo",
        "usuario",
        "fecha",
        "clave",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
