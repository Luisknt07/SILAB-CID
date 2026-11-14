"""Administración del repositorio y de los modelos externos."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, unidades_gestionables

from apps.gestion_unidades.models.repositorio import Adjunto, ArtefactoExterno, ResultadoArtefacto
from apps.recursos.admin.contenido import SolicitudMicroproyectoAdminMixin


class _RepositorioPorUnidadMixin:
    ruta_unidad = 'unidad'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(**{f'{self.ruta_unidad}__in': unidades_gestionables(request.user)})

    def _unidad_objeto(self, obj):
        if obj is None:
            return None
        return obj.unidad if self.ruta_unidad == 'unidad' else obj.artefacto.unidad

    def _administra_objeto(self, request, obj):
        unidad = self._unidad_objeto(obj)
        return bool(
            request.user.is_superuser
            or obj is None
            or (unidad and puede_gestionar_unidad(request.user, unidad))
        )

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._administra_objeto(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._administra_objeto(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._administra_objeto(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            unidades = unidades_gestionables(request.user)
            filtros = {
                'unidad': Q(pk__in=unidades),
                'ficha': Q(unidad__in=unidades),
                'carpeta': Q(unidad__in=unidades),
                'familia': Q(unidad__in=unidades),
                'receta': Q(unidad__in=unidades),
                'equipo': Q(laboratorio__in=unidades) | Q(laboratorios__in=unidades),
                'area': Q(unidad__in=unidades),
                'evidencia_validacion': Q(unidad__in=unidades),
                'reemplaza_a': Q(unidad__in=unidades),
                'artefacto': Q(unidad__in=unidades),
            }
            if db_field.name in filtros:
                kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                    filtros[db_field.name],
                ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Adjunto)
class AdjuntoAdmin(SolicitudMicroproyectoAdminMixin, _RepositorioPorUnidadMixin, AdministracionTraducida):
    list_display = (
        'nombre', 'tipo_adjunto', 'unidad', 'ficha', 'carpeta', 'version',
        'estado', 'visibilidad', 'seguridad_verificada', 'tamano_bytes',
    )
    list_filter = (
        'tipo_adjunto', 'estado', 'visibilidad', 'seguridad_verificada',
        'fuente', 'licencia_uso', 'unidad',
    )
    search_fields = ('nombre', 'descripcion', 'autor', 'palabras_clave', 'hash_sha256')
    autocomplete_fields = ('unidad', 'ficha', 'carpeta', 'reemplaza_a')
    readonly_fields = (
        'nombre_original', 'formato', 'tamano_bytes', 'hash_sha256',
        'fecha_subida', 'subido_por', 'veces_descargado',
    )
    fieldsets = (
        ('Vínculo obligatorio', {'fields': ('unidad', 'ficha', 'carpeta')}),
        ('Descripción', {'fields': ('nombre', 'descripcion', 'tipo_adjunto', 'palabras_clave')}),
        ('Archivo o enlace', {'fields': ('archivo', 'url', 'descargar', 'autorizacion_tamano')}),
        ('Autoría y uso', {'fields': ('autor', 'fecha_documento', 'fuente', 'licencia_uso')}),
        ('Publicación y versión', {
            'fields': (
                'version', 'reemplaza_a', 'estado', 'activo', 'visibilidad',
                'seguridad_verificada', 'orden',
            ),
        }),
        ('Metadatos calculados', {
            'fields': (
                'nombre_original', 'formato', 'tamano_bytes', 'hash_sha256',
                'fecha_subida', 'subido_por', 'veces_descargado',
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.subido_por_id:
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)


class ResultadoArtefactoInline(TablaTraducida):
    model = ResultadoArtefacto
    extra = 0
    fields = ('archivo', 'resumen', 'importado_por', 'importado_en')
    readonly_fields = ('importado_por', 'importado_en')


@admin.register(ArtefactoExterno)
class ArtefactoExternoAdmin(_RepositorioPorUnidadMixin, AdministracionTraducida):
    list_display = (
        'codigo', 'nombre', 'unidad', 'tipo', 'nivel_integracion', 'estado',
        'estado_validacion', 'estado_vigencia', 'posiblemente_desactualizado', 'version',
    )
    list_filter = (
        'unidad', 'tipo', 'nivel_integracion', 'estado', 'visibilidad',
        'estado_verificacion', 'estado_validacion', 'posiblemente_desactualizado',
    )
    search_fields = ('codigo', 'nombre', 'descripcion', 'autor', 'software_requerido')
    autocomplete_fields = (
        'unidad', 'familia', 'receta', 'equipo', 'area', 'evidencia_validacion', 'reemplaza_a',
    )
    filter_horizontal = ('archivos',)
    readonly_fields = (
        'responsable_validacion', 'validado_en', 'estado_vigencia',
        'posiblemente_desactualizado', 'motivo_desactualizacion',
        'sincronizado_en', 'veces_descargado', 'ultima_ejecucion',
        'creado_en', 'actualizado_en', 'cita',
    )
    inlines = (ResultadoArtefactoInline,)
    actions = ('confirmar_sincronizacion',)
    fieldsets = (
        ('Identidad y vínculo', {'fields': (
            'codigo', 'nombre', 'descripcion', 'tipo', 'nivel_integracion',
            'unidad', 'familia', 'receta', 'equipo', 'area',
        )}),
        ('Ejecución externa', {'fields': (
            'software_requerido', 'version_software', 'licencia_software',
            'requisitos_tecnicos', 'instrucciones_uso', 'archivos',
        )}),
        ('Contrato de datos', {'fields': (
            'entradas_esperadas', 'salidas_devueltas', 'formato_intercambio', 'esquema',
        )}),
        ('Verificación y validación', {'fields': (
            'que_representa', 'supuestos_simplificaciones', 'estado_verificacion',
            'estado_validacion', 'evidencia_validacion', 'fuente_referencia',
            'responsable_validacion', 'validado_en', 'limitaciones_conocidas',
        )}),
        ('Gobierno', {'fields': (
            'autor', 'institucion', 'contacto', 'licencia_uso', 'cita_requerida',
            'version', 'reemplaza_a', 'estado', 'visibilidad',
        )}),
        ('Vigencia', {'fields': (
            'vigente_desde', 'vigente_hasta', 'estado_vigencia',
            'posiblemente_desactualizado', 'motivo_desactualizacion', 'sincronizado_en',
            'veces_descargado', 'ultima_ejecucion', 'creado_en', 'actualizado_en', 'cita',
        )}),
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'archivos' and not request.user.is_superuser:
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                unidad__in=unidades_gestionables(request.user),
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.estado_validacion != 'sin_validar' and (
            not change or 'estado_validacion' in form.changed_data or not obj.responsable_validacion_id
        ):
            obj.responsable_validacion = request.user
            obj.validado_en = timezone.now()
        elif obj.estado_validacion == 'sin_validar' and 'estado_validacion' in form.changed_data:
            obj.responsable_validacion = None
            obj.validado_en = None
        super().save_model(request, obj, form, change)

    @admin.action(description='Confirmar sincronización y vigencia técnica')
    def confirmar_sincronizacion(self, request, queryset):
        ahora = timezone.now()
        queryset.exclude(estado_validacion='sin_validar').update(
            posiblemente_desactualizado=False,
            motivo_desactualizacion='',
            sincronizado_en=ahora,
            responsable_validacion=request.user,
            validado_en=ahora,
        )

    def save_formset(self, request, form, formset, change):
        objetos = formset.save(commit=False)
        for objeto in objetos:
            if isinstance(objeto, ResultadoArtefacto) and not objeto.importado_por_id:
                objeto.importado_por = request.user
            objeto.save()
        formset.save_m2m()


@admin.register(ResultadoArtefacto)
class ResultadoArtefactoAdmin(_RepositorioPorUnidadMixin, AdministracionTraducida):
    ruta_unidad = 'artefacto__unidad'
    list_display = ('artefacto', 'importado_por', 'importado_en')
    list_filter = ('artefacto__unidad', 'artefacto', 'importado_en')
    search_fields = ('artefacto__codigo', 'artefacto__nombre')
    autocomplete_fields = ('artefacto',)
    readonly_fields = ('importado_por', 'importado_en')

    def save_model(self, request, obj, form, change):
        if not obj.importado_por_id:
            obj.importado_por = request.user
        super().save_model(request, obj, form, change)
