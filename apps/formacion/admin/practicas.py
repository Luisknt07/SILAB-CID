
from apps.core.presentation.administracion import AdministracionTraducida
from django.contrib import admin

from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad


@admin.register(PlanificacionPractica)
class PlanificacionPracticaAdmin(AdministracionTraducida):
    list_display = ("codigo", "unidad", "actividad", "fecha", "requiere_guia", "estado", "numero_version", "es_version_vigente")
    list_filter = ("estado", "categoria_uso", "requiere_guia", "unidad", "es_version_vigente")
    search_fields = ("codigo", "tema", "asignatura", "docente_tutor")
    # El FT02 se genera y sincroniza desde la reserva; su estado, version
    # vigente, guia y vinculos los decide ese flujo y la revision del panel.
    readonly_fields = (
        "codigo", "grupo_version", "numero_version", "es_version_vigente",
        "actividad", "guia", "reserva", "requiere_guia", "estado",
        "observaciones_revision", "creado_por", "revisado_por", "revisado_en",
        "eliminado_en", "eliminado_por", "creado_en", "actualizado_en",
    )
    autocomplete_fields = ("responsable_tecnico",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EjecucionPractica)
class EjecucionPracticaAdmin(AdministracionTraducida):
    list_display = ("planificacion", "fecha_ejecucion", "resultado", "estado", "estudiantes_asistentes")
    list_filter = (("planificacion__unidad", admin.RelatedOnlyFieldListFilter),
                   "resultado", "estado", "fecha_ejecucion")
    search_fields = ("planificacion__codigo", "planificacion__tema")
    # La ejecucion se registra y valida desde el panel de practicas.
    readonly_fields = ("planificacion", "estado", "resultado", "creado_por", "validado_por")
    autocomplete_fields = ("incidencia", "responsable_tecnico")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RegistroAuditoriaUnidad)
class RegistroAuditoriaUnidadAdmin(AdministracionTraducida):
    list_display = ("creado_en", "nombre_unidad", "usuario", "accion", "entidad", "objeto_id", "descripcion")
    list_filter = ("accion", "entidad", "unidad")
    search_fields = ("descripcion", "objeto_id", "usuario__username", "unidad_nombre")
    readonly_fields = tuple(field.name for field in RegistroAuditoriaUnidad._meta.fields)

    @admin.display(description="Unidad", ordering="unidad_nombre")
    def nombre_unidad(self, registro):
        # El histórico de una unidad eliminada sigue diciendo de quién era.
        return registro.nombre_unidad

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
