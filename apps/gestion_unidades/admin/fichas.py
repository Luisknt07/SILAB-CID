"""Administración del gobierno editorial común de las fichas."""

from apps.core.presentation.administracion import AdministracionTraducida

from django.contrib import admin
from django.utils import timezone

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, unidades_gestionables

from apps.gestion_unidades.models.fichas import FichaContenido


@admin.register(FichaContenido)
class FichaContenidoAdmin(AdministracionTraducida):
    list_display = (
        'codigo', 'titulo', 'unidad', 'familia', 'tipo', 'estado', 'estado_validacion',
        'version', 'visibilidad', 'completitud', 'decision_editorial_manual',
    )
    list_filter = (
        'unidad', 'familia', 'tipo', 'estado', 'estado_validacion', 'visibilidad',
        'decision_editorial_manual',
    )
    search_fields = ('codigo', 'titulo', 'descripcion')
    autocomplete_fields = ('unidad', 'familia', 'relacionadas')
    filter_horizontal = ('relacionadas',)
    readonly_fields = (
        'completitud', 'validado_por', 'validado_en', 'decision_editorial_manual',
        'decision_editorial_por', 'decision_editorial_en', 'creado_en', 'actualizado_en',
    )
    list_editable = ('estado', 'visibilidad', 'version')
    actions = (
        'publicar', 'enviar_a_revision', 'restringir', 'hacer_internas', 'archivar',
        'enviar_a_validacion', 'validar_institucionalmente', 'bloquear_validacion',
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(unidad__in=unidades_gestionables(request.user))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            gestionables = unidades_gestionables(request.user)
            if db_field.name == 'unidad':
                kwargs['queryset'] = db_field.remote_field.model.objects.filter(pk__in=gestionables)
            elif db_field.name == 'familia':
                kwargs['queryset'] = db_field.remote_field.model.objects.filter(unidad__in=gestionables)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _administra_objeto(self, request, obj):
        return bool(
            request.user.is_superuser
            or obj is None
            or puede_gestionar_unidad(request.user, obj.unidad)
        )

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._administra_objeto(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._administra_objeto(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._administra_objeto(request, obj)

    def _actualizar_decision(self, request, queryset, **cambios):
        return queryset.update(
            decision_editorial_manual=True,
            decision_editorial_por=request.user,
            decision_editorial_en=timezone.now(),
            **cambios,
        )

    def save_model(self, request, obj, form, change):
        campos_gobierno = {
            'estado', 'visibilidad', 'version', 'estado_validacion', 'observacion_validacion',
        }
        if not change or campos_gobierno.intersection(form.changed_data):
            obj.decision_editorial_manual = True
            obj.decision_editorial_por = request.user
            obj.decision_editorial_en = timezone.now()
        if 'estado_validacion' in form.changed_data:
            if obj.estado_validacion == 'validada':
                obj.validado_por = request.user
                obj.validado_en = timezone.now()
            else:
                obj.validado_por = None
                obj.validado_en = None
        super().save_model(request, obj, form, change)

    @admin.action(description='Publicar con acceso público')
    def publicar(self, request, queryset):
        self._actualizar_decision(request, queryset, estado='publicada', visibilidad='publica')

    @admin.action(description='Enviar a revisión')
    def enviar_a_revision(self, request, queryset):
        self._actualizar_decision(request, queryset, estado='en_revision')

    @admin.action(description='Publicar para la comunidad universitaria')
    def restringir(self, request, queryset):
        self._actualizar_decision(request, queryset, estado='publicada', visibilidad='restringida')

    @admin.action(description='Hacer internas')
    def hacer_internas(self, request, queryset):
        self._actualizar_decision(request, queryset, visibilidad='interna')

    @admin.action(description='Archivar')
    def archivar(self, request, queryset):
        self._actualizar_decision(request, queryset, estado='archivada', visibilidad='interna')

    @admin.action(description='Enviar a validación institucional')
    def enviar_a_validacion(self, request, queryset):
        self._actualizar_decision(
            request,
            queryset,
            estado_validacion='en_revision',
            validado_por=None,
            validado_en=None,
        )

    @admin.action(description='Marcar como validadas por la institución')
    def validar_institucionalmente(self, request, queryset):
        ahora = timezone.now()
        queryset.update(
            estado_validacion='validada',
            validado_por=request.user,
            validado_en=ahora,
            decision_editorial_manual=True,
            decision_editorial_por=request.user,
            decision_editorial_en=ahora,
        )

    @admin.action(description='Bloquear por información institucional faltante')
    def bloquear_validacion(self, request, queryset):
        self._actualizar_decision(
            request,
            queryset,
            estado_validacion='bloqueada',
            observacion_validacion='Requiere completar o comprobar información institucional.',
            validado_por=None,
            validado_en=None,
        )
