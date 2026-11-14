"""Administración del calendario académico y sus cortes históricos."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from datetime import timedelta

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from apps.core.presentation.calendario_institucional import con_calendario_institucional

from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico, VinculacionUsuarioPeriodo


class VersionCalendarioInline(TablaTraducida):
    model = VersionCalendarioAcademico
    extra = 0
    fields = [
        "numero",
        "nombre",
        "fecha_inicio_clases",
        "fecha_fin_clases",
        "fecha_fin_periodo",
        "resolucion",
        "vigente",
    ]
    show_change_link = True


@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(AdministracionTraducida):
    list_display = [
        "codigo",
        "nombre",
        "anio_referencia",
        "ciclo",
        "tipo",
        "ambito",
        "semanas_planificadas",
        "estado",
        "calendario_vigente",
    ]
    list_filter = ["estado", "tipo", "ciclo", "ambito", "anio_referencia"]
    search_fields = ["codigo", "nombre", "versiones__resolucion"]
    ordering = ["-anio_referencia", "-ciclo"]
    inlines = [VersionCalendarioInline]

    @admin.display(description="Calendario vigente")
    def calendario_vigente(self, obj):
        version = obj.version_vigente
        if not version:
            return "Sin publicar"
        return f"{version.fecha_inicio_clases:%d/%m/%Y} – {version.fecha_fin_periodo:%d/%m/%Y}"


@admin.register(VersionCalendarioAcademico)
class VersionCalendarioAcademicoAdmin(AdministracionTraducida):
    list_display = [
        "periodo",
        "numero",
        "nombre",
        "fecha_inicio_clases",
        "fecha_fin_periodo",
        "resolucion",
        "vigente",
        "total_semanas",
    ]
    list_filter = ["vigente", "periodo__estado", "periodo__anio_referencia", "periodo__ambito"]
    search_fields = ["periodo__codigo", "nombre", "resolucion"]
    autocomplete_fields = ["periodo"]
    readonly_fields = ["creado_por", "creado_en"]
    actions = ["generar_semanas_faltantes"]

    @admin.display(description="Semanas")
    def total_semanas(self, obj):
        return obj.semanas.count()

    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Generar semanas académicas faltantes")
    @con_calendario_institucional()
    def generar_semanas_faltantes(self, request, queryset):
        creadas = 0
        omitidas = 0
        for version in queryset.select_related("periodo"):
            try:
                version.periodo.full_clean()
                version.full_clean()
            except ValidationError:
                self.message_user(request, f"No se generaron semanas para {version.periodo.codigo}: revisa el periodo y su calendario.", messages.ERROR)
                continue
            tipo_semana = (
                "operacion_interperiodo"
                if version.periodo.tipo == "interperiodo"
                else "clases"
            )
            for numero in range(1, version.periodo.semanas_planificadas + 1):
                fecha_inicio = version.fecha_inicio_clases + timedelta(days=(numero - 1) * 7)
                if fecha_inicio > version.fecha_fin_periodo:
                    break
                fecha_fin = min(fecha_inicio + timedelta(days=6), version.fecha_fin_periodo)
                _, creada = SemanaAcademica.objects.get_or_create(
                    version_calendario=version,
                    numero=numero,
                    defaults={
                        "fecha_inicio": fecha_inicio,
                        "fecha_fin": fecha_fin,
                        "tipo": tipo_semana,
                    },
                )
                creadas += int(creada)
                omitidas += int(not creada)
        self.message_user(
            request,
            f"Se generaron {creadas} semanas; {omitidas} ya existían y se conservaron.",
            messages.SUCCESS,
        )


@admin.register(SemanaAcademica)
class SemanaAcademicaAdmin(AdministracionTraducida):
    list_display = [
        "version_calendario",
        "numero",
        "fecha_inicio",
        "fecha_fin",
        "tipo",
        "parcial",
        "reportable",
        "permite_reservas",
    ]
    list_filter = [
        "tipo",
        "reportable",
        "permite_reservas",
        "version_calendario__periodo__anio_referencia",
        "version_calendario__periodo",
    ]
    search_fields = ["version_calendario__periodo__codigo", "observaciones"]
    autocomplete_fields = ["version_calendario"]
    ordering = ["-version_calendario__periodo__anio_referencia", "numero"]


@admin.register(VinculacionUsuarioPeriodo)
class VinculacionUsuarioPeriodoAdmin(AdministracionTraducida):
    list_display = [
        "usuario",
        "periodo",
        "tipo_usuario",
        "facultad",
        "carrera",
        "nivel_academico",
        "paralelo",
        "estado",
        "fuente",
        "validada",
    ]
    list_filter = [
        "periodo",
        "tipo_usuario",
        "facultad",
        "carrera",
        "nivel_academico",
        "estado",
        "fuente",
        "validada",
    ]
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "usuario__email",
        "institucion",
    ]
    autocomplete_fields = ["usuario", "periodo"]
