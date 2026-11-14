"""Expediente de calidad: el catalogo de lo exigido y la validacion de lo entregado."""

from django.contrib import admin

from apps.core.presentation.administracion import AdministracionTraducida

from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad





class UnidadAdscritaInline(admin.TabularInline):
    """Las unidades de la dependencia: aquí el decanato designa quién las coordina.

    El coordinador designado es quien valida y envía lo que la unidad entrega,
    y responde por que esa información sea verídica; quien dice si la unidad
    cumple es la Dirección. Las carreras que atiende la unidad se registran
    aquí mismo, porque las define el mismo decanato.
    """

    model = Unidad
    fk_name = 'adscrita_a'
    extra = 0
    can_delete = False
    fields = ('nombre', 'dependencia', 'administrador', 'carreras', 'activo')
    readonly_fields = ('nombre', 'dependencia', 'activo')
    autocomplete_fields = ('administrador',)
    verbose_name = 'Unidad adscrita'
    verbose_name_plural = 'Unidades adscritas: coordinador designado y carreras'

    def has_add_permission(self, request, obj=None):
        return False

    def _designa(self, request, obj):
        """Quién designa aquí. Django pregunta también sin objeto —para armar el
        listado—, y ahí basta con recibir el informe de alguna dependencia: cuál
        se ve lo acota el queryset del administrador."""
        if request.user.is_superuser:
            return True
        if obj is not None:
            return obj.recibe_informe(request.user)
        return request.user.dependencias_que_recibe.filter(activa=True).exists()

    def has_view_permission(self, request, obj=None):
        return self._designa(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._designa(request, obj)


@admin.register(DependenciaAcademica)
class DependenciaAcademicaAdmin(AdministracionTraducida):
    """Los decanatos que designan a los responsables de sus unidades y reciben su informe."""

    list_display = ('nombre', 'tipo', 'centro_costo', 'activa', 'cuantas_unidades', 'quienes_reciben')
    list_filter = ('tipo', 'activa')
    search_fields = ('nombre',)
    filter_horizontal = ('receptores',)
    inlines = (UnidadAdscritaInline,)

    def get_queryset(self, request):
        """Cada quien ve la suya: quien recibe el informe de una dependencia no gobierna las demás."""
        consulta = super().get_queryset(request)
        if request.user.is_superuser:
            return consulta
        return consulta.filter(receptores=request.user, activa=True)

    def get_readonly_fields(self, request, obj=None):
        """Quién recibe el informe de la dependencia lo nombra la Dirección, no la dependencia."""
        if request.user.is_superuser:
            return super().get_readonly_fields(request, obj)
        return tuple(super().get_readonly_fields(request, obj)) + ('nombre', 'tipo', 'activa', 'receptores')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description='Unidades adscritas')
    def cuantas_unidades(self, obj):
        return obj.unidades.count()

    @admin.display(description='Reciben el informe')
    def quienes_reciben(self, obj):
        return ', '.join(u.get_full_name() or u.username for u in obj.receptores.all()) or '—'
