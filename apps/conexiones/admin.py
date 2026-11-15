"""Alta de dispositivos y canales. La credencial se muestra una sola vez, al generarla."""
from django.contrib import admin, messages
from django.urls import reverse

from apps.conexiones.models import CanalMedicion, DispositivoConectado


class SoloSuperusuario:
    """Registrar un dispositivo abre una entrada de datos al sistema: lo decide la administración general."""

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_module_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


class CanalMedicionInline(SoloSuperusuario, admin.TabularInline):
    model = CanalMedicion
    extra = 0
    fields = ('clave', 'nombre', 'magnitud', 'unidad_medida', 'minimo_esperado', 'maximo_esperado',
              'retencion_dias', 'activo')

    def has_add_permission(self, request, obj=None):
        return self.has_module_permission(request)


@admin.register(DispositivoConectado)
class DispositivoConectadoAdmin(SoloSuperusuario, admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'unidad', 'tipo', 'activo', 'tiene_clave', 'ultima_senal')
    list_filter = ('activo', 'tipo')
    search_fields = ('codigo', 'nombre', 'unidad__nombre')
    raw_id_fields = ('unidad', 'equipo')
    readonly_fields = ('clave_generada_en', 'ultima_senal', 'creado_por', 'fecha_creacion', 'fecha_actualizacion')
    inlines = (CanalMedicionInline,)
    actions = ('generar_clave',)

    @admin.display(boolean=True, description='Con clave')
    def tiene_clave(self, obj):
        return bool(obj.clave_hash)

    def view_on_site(self, obj):
        # «Ver en el sitio» abre el estado de los dispositivos de su unidad.
        return reverse('conexiones_estado_unidad', args=[obj.unidad.slug])

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Generar una clave nueva (la anterior deja de servir)')
    def generar_clave(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Selecciona un solo dispositivo para generar su clave.', messages.ERROR)
            return
        dispositivo = queryset.get()
        credencial = dispositivo.generar_clave()
        self.message_user(
            request,
            f'Credencial de {dispositivo.codigo}: {credencial} — cópiala ahora; no se vuelve a mostrar.',
            messages.WARNING,
        )
