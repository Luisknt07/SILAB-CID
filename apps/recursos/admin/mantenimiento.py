"""Administración de mantenimiento, incidencias y ciclo de vida de activos."""

from apps.core.presentation.administracion import AdministracionTraducida

from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, unidades_gestionables

from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo, EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo, RepuestoMantenimiento, ServicioReparacionEquipo
from apps.recursos.models.prestamos import PrestamoEquipo


def _alcance_por_unidad(modelo, unidades):
    if any(campo.name == 'unidad' for campo in modelo._meta.fields):
        # Los registros anteriores sin unidad siguen la adscripción primaria;
        # compartir el activo no transfiere la gestión de su historial.
        return Q(unidad__in=unidades) | Q(unidad__isnull=True, equipo__laboratorio__in=unidades)
    return Q(equipo__laboratorio__in=unidades)


class _AdminPorUnidadMixin:
    """Limita a cada gestor a los activos de las unidades que administra."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(_alcance_por_unidad(self.model, unidades_gestionables(request.user)))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            unidades = unidades_gestionables(request.user)
            if db_field.name == 'equipo':
                filtro = Q(laboratorio__in=unidades)
                resolucion = getattr(request, 'resolver_match', None)
                objeto_id = resolucion.kwargs.get('object_id') if resolucion else None
                if objeto_id and str(objeto_id).isdecimal():
                    # Permitir conservar el equipo de un registro propio aunque
                    # hoy tenga otra sede; no habilitar activos ajenos al crear.
                    actual = self.get_queryset(request).filter(pk=objeto_id).values('equipo_id')
                    filtro |= Q(pk__in=actual)
                kwargs['queryset'] = db_field.remote_field.model.objects.filter(filtro)
            elif db_field.name in {'incidencia', 'mantenimiento'}:
                modelo = db_field.remote_field.model
                kwargs['queryset'] = modelo.objects.filter(_alcance_por_unidad(modelo, unidades))
            elif db_field.name == 'unidad':
                kwargs['queryset'] = db_field.remote_field.model.objects.filter(pk__in=unidades)
            elif db_field.name == 'espacio':
                kwargs['queryset'] = db_field.remote_field.model.objects.filter(unidad__in=unidades)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _administra_objeto(self, request, obj):
        if request.user.is_superuser or obj is None:
            return True
        unidad = getattr(obj, 'unidad', None) or getattr(obj.equipo, 'laboratorio', None)
        return bool(unidad and puede_gestionar_unidad(request.user, unidad))

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._administra_objeto(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._administra_objeto(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._administra_objeto(request, obj)


@admin.register(PlanMantenimientoEquipo)
class PlanMantenimientoEquipoAdmin(_AdminPorUnidadMixin, AdministracionTraducida):
    list_display = [
        "nombre", "equipo", "unidad_responsable", "tipo", "ejecutor", "proxima_ejecucion",
        "estado_programacion", "responsable", "activo",
    ]
    list_filter = ["activo", "tipo", "ejecutor", "proxima_ejecucion", "equipo__laboratorio"]
    search_fields = [
        "nombre", "equipo__codigo_unidad", "equipo__equipo__nombre",
        "equipo__laboratorio__nombre", "proveedor",
    ]
    autocomplete_fields = ["equipo", "responsable"]
    readonly_fields = ["creado_en", "actualizado_en"]
    date_hierarchy = "proxima_ejecucion"

    @admin.display(description="Unidad", ordering="equipo__laboratorio__nombre")
    def unidad_responsable(self, obj):
        return obj.equipo.laboratorio

    @admin.display(description="Programación")
    def estado_programacion(self, obj):
        if obj.esta_vencido:
            return "Vencido"
        if obj.requiere_programacion:
            return "Próximo"
        return "Al día"


@admin.register(IncidenciaEquipo)
class IncidenciaEquipoAdmin(_AdminPorUnidadMixin, AdministracionTraducida):
    list_display = [
        "titulo", "equipo", "unidad", "tipo", "prioridad", "estado",
        "detiene_operacion", "fecha_reporte", "asignada_a",
    ]
    list_filter = [
        "estado", "prioridad", "tipo", "detiene_operacion", "unidad", "fecha_reporte",
    ]
    search_fields = [
        "titulo", "descripcion", "solucion", "equipo__codigo_unidad",
        "equipo__equipo__nombre", "unidad__nombre",
    ]
    autocomplete_fields = ["equipo", "reportada_por", "asignada_a"]
    readonly_fields = [
        "unidad", "estado_equipo_previo", "fecha_reporte", "fecha_resolucion",
    ]
    date_hierarchy = "fecha_reporte"
    fieldsets = (
        ("Reporte", {
            "fields": (
                "equipo", "espacio", "unidad", "titulo", "tipo", "prioridad", "fecha_hecho", "descripcion",
                "detiene_operacion", "estado_equipo_previo", "evidencia",
            )
        }),
        ("Atención", {
            "fields": ("estado", "asignada_a", "solucion", "fecha_resolucion")
        }),
        ("Trazabilidad", {
            "fields": ("reportada_por", "fecha_reporte"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.reportada_por_id:
            obj.reportada_por = request.user
        super().save_model(request, obj, form, change)


class RepuestoMantenimientoInline(admin.TabularInline):
    """Lo que se cambió en la orden: sin esto no se sabe cuánto cuesta sostener el equipo."""

    model = RepuestoMantenimiento
    extra = 0
    autocomplete_fields = ["consumible", "pieza"]
    fields = ["descripcion", "pieza", "consumible", "cantidad", "costo_unitario", "procedencia",
              "referencia_adquisicion", "observacion"]


@admin.register(MantenimientoEquipo)
class MantenimientoEquipoAdmin(_AdminPorUnidadMixin, AdministracionTraducida):
    list_display = [
        "codigo", "titulo", "equipo", "unidad", "tipo", "ejecutor", "estado",
        "fecha_programada", "responsable", "costo",
    ]
    list_filter = ["estado", "tipo", "ejecutor", "unidad", "fecha_programada"]
    search_fields = [
        "codigo", "titulo", "descripcion", "resultado", "equipo__codigo_unidad",
        "equipo__equipo__nombre", "unidad__nombre", "proveedor",
    ]
    autocomplete_fields = ["equipo", "plan", "incidencia", "responsable"]
    readonly_fields = [
        "codigo", "unidad", "estado_equipo_previo", "creado_en", "actualizado_en",
    ]
    date_hierarchy = "fecha_programada"
    inlines = [RepuestoMantenimientoInline]
    fieldsets = (
        ("Orden de mantenimiento", {
            "fields": (
                "codigo", "equipo", "unidad", "plan", "incidencia", "tipo", "estado",
                "titulo", "descripcion",
            )
        }),
        ("Programación", {
            "fields": (
                "fecha_programada", "fecha_inicio", "fecha_fin", "ejecutor", "responsable",
                "proveedor", "estado_equipo_previo",
            ),
            "description": (
                "Quién lo hace decide el costo y el plazo: el laboratorista de la unidad "
                "atiende solo trabajos para los que sea competente. Consulta la cobertura de garantía "
                "y las capacidades declaradas del servicio interno; registra la derivación especializada cuando proceda."
            ),
        }),
        ("Cierre", {
            "fields": ("resultado", "prueba_funcionamiento", "resultado_operativo", "costo", "proximo_mantenimiento", "informe")
        }),
        ("Metadatos", {
            "fields": ("creado_en", "actualizado_en"),
            "classes": ("collapse",),
        }),
    )


@admin.register(ServicioReparacionEquipo)
class ServicioReparacionEquipoAdmin(AdministracionTraducida):
    list_display = ['nombre', 'activo', 'capacidad_mensual', 'casos_pendientes', 'contacto']
    search_fields = ['nombre', 'alcance', 'contacto']
    filter_horizontal = ['familias']
    readonly_fields = ['actualizado_en']

    @admin.display(description='Casos pendientes')
    def casos_pendientes(self, obj):
        return obj.diagnosticos.exclude(incidencia__estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).count()

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser


@admin.register(DiagnosticoIncidenciaEquipo)
class DiagnosticoIncidenciaEquipoAdmin(AdministracionTraducida):
    list_display = ['incidencia', 'fecha_evaluacion', 'decision', 'ruta', 'servicio', 'respuesta_prevista', 'evaluada_por']
    list_filter = ['incidencia__unidad', 'decision', 'ruta', 'garantia_revision', 'fuente_financiamiento']
    search_fields = ['incidencia__equipo__codigo_unidad', 'incidencia__titulo', 'causa', 'componente', 'justificacion_decision']
    autocomplete_fields = ['incidencia', 'pieza', 'servicio']
    readonly_fields = ['evaluada_por', 'actualizado_en']
    fieldsets = (
        ('Evaluación del equipo', {'fields': ('incidencia', 'fecha_evaluacion', 'causa', 'impacto', 'evidencia')}),
        ('Revisión previa de garantía', {'fields': ('garantia_revision', 'garantia_respaldo')}),
        ('Pieza o accesorio afectado', {'fields': ('pieza', 'componente', 'cantidad_componente', 'especificacion_componente')}),
        ('Atención y respuesta', {'fields': ('ruta', 'servicio', 'proveedor_externo', 'fecha_derivacion', 'respuesta_prevista', 'respuesta', 'costo_estimado', 'plazo_estimado_dias')}),
        ('Decisión técnica y respaldo administrativo', {'fields': ('decision', 'justificacion_decision', 'fuente_financiamiento', 'revision_adquisicion', 'autorizacion_referencia'), 'description': 'El diagnóstico no autoriza gasto. La autogestión es una fuente de financiación y no exime del procedimiento aplicable.'}),
        ('Trazabilidad', {'fields': ('evaluada_por', 'actualizado_en')}),
    )

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if not request.user.is_superuser:
            consulta = consulta.filter(incidencia__unidad__in=unidades_gestionables(request.user))
        return consulta

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'incidencia' and not request.user.is_superuser:
            kwargs['queryset'] = IncidenciaEquipo.objects.filter(unidad__in=unidades_gestionables(request.user))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or request.user.is_superuser or puede_gestionar_unidad(request.user, obj.incidencia.unidad))

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and (obj is None or request.user.is_superuser or puede_gestionar_unidad(request.user, obj.incidencia.unidad))

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.evaluada_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventoCicloVidaEquipo)
class EventoCicloVidaEquipoAdmin(_AdminPorUnidadMixin, AdministracionTraducida):
    list_display = ["equipo", "unidad", "tipo", "fecha", "usuario"]
    list_filter = ["tipo", "unidad", "fecha"]
    search_fields = [
        "equipo__codigo_unidad", "equipo__equipo__nombre", "unidad__nombre", "descripcion",
    ]
    autocomplete_fields = ["equipo", "usuario", "incidencia", "mantenimiento"]
    readonly_fields = ["fecha"]
    date_hierarchy = "fecha"

    def save_model(self, request, obj, form, change):
        if not obj.usuario_id:
            obj.usuario = request.user
        if not obj.fecha:
            obj.fecha = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(PrestamoEquipo)
class PrestamoEquipoAdmin(_AdminPorUnidadMixin, AdministracionTraducida):
    """El acta del préstamo: quién se llevó el equipo y cuándo lo devuelve."""

    list_display = ["codigo", "equipo", "tipo", "quien_retira", "institucion",
                    "fecha_salida", "fecha_retorno_previsto", "estado", "vencido"]
    list_filter = ["estado", "tipo", "condicion_retorno", "unidad", "fecha_salida"]
    search_fields = [
        "codigo", "equipo__codigo_unidad", "equipo__equipo__nombre", "nombre_solicitante",
        "institucion", "proposito", "autorizado_por",
    ]
    autocomplete_fields = ["equipo", "solicitante", "entregado_por", "recibido_por"]
    readonly_fields = ["codigo", "unidad", "estado_equipo_previo", "creado_en", "actualizado_en"]
    date_hierarchy = "fecha_salida"
    fieldsets = (
        ("Salida", {
            "fields": (
                "codigo", "equipo", "unidad", "tipo", "estado", "proposito",
                "fecha_salida", "fecha_retorno_previsto", "condicion_salida",
                "observaciones_salida", "entregado_por",
            ),
            "description": (
                "El préstamo externo saca el activo de la custodia de la unidad: exige "
                "institución receptora y quien autoriza la salida. En laboratorios, al entregar exige "
                "también acta legible y responsable de entrega; la devolución requiere responsable de recepción. "
                "Una solicitud puede prepararse antes de adjuntar el acta."
            ),
        }),
        ("Quién retira", {
            "fields": (
                "solicitante", "nombre_solicitante", "documento_solicitante", "contacto",
                "institucion", "autorizado_por", "acta",
            )
        }),
        ("Retorno", {
            "fields": (
                "fecha_retorno_real", "condicion_retorno", "observaciones_retorno", "recibido_por",
            )
        }),
        ("Calendario", {
            "fields": ("bloquea_agenda", "estado_equipo_previo"),
            "classes": ("collapse",),
        }),
        ("Metadatos", {
            "fields": ("creado_en", "actualizado_en"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Quién retira")
    def quien_retira(self, obj):
        return obj.quien_retira

    @admin.display(description="Vencido", boolean=True)
    def vencido(self, obj):
        return obj.vencido
