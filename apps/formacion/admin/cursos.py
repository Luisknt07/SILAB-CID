"""Administración de los cursos y capacitaciones de cada unidad: ediciones por año, módulos, lecciones e inscritos."""

from apps.core.presentation.administracion import AdministracionTraducida, BloqueTraducido

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ParticipanteEvento
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso


class FormacionUnidadAdminMixin:
    """La autorización del modelo se intersecta con la unidad del personal."""
    unidad_lookup = 'curso__unidad'

    def _unidades_permitidas(self, request):
        from apps.gestion_unidades.presentation.permisos import unidades_gestionables, puede_operar_modulo_unidad
        return [unidad.pk for unidad in unidades_gestionables(request.user)
                if puede_operar_modulo_unidad(request.user, unidad, 'practicas')]

    def _unidad_objeto(self, obj):
        if isinstance(obj, CertificadoCurso):
            curso = obj.curso_origen
            return curso.unidad_id if curso else None
        for atributo in self.unidad_lookup.split('__'):
            obj = getattr(obj, atributo)
        return obj.pk

    def _alcance(self, request, obj=None):
        return (request.user.is_superuser or (self._unidad_objeto(obj) in self._unidades_permitidas(request)
                if obj else bool(self._unidades_permitidas(request))))

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if request.user.is_superuser:
            return consulta
        permitidas = self._unidades_permitidas(request)
        if self.model is CertificadoCurso:
            return consulta.filter(Q(inscripcion__edicion__curso__unidad_id__in=permitidas)
                | Q(participante_evento__edicion__curso__unidad_id__in=permitidas))
        return consulta.filter(**{self.unidad_lookup + '_id__in': permitidas})

    def has_add_permission(self, request):
        return super().has_add_permission(request) and self._alcance(request)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._alcance(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._alcance(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._alcance(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            permitidas = self._unidades_permitidas(request)
            if db_field.name == 'curso':
                kwargs['queryset'] = Curso.objects.filter(unidad_id__in=permitidas)
            elif db_field.name == 'edicion':
                kwargs['queryset'] = EdicionCurso.objects.filter(curso__unidad_id__in=permitidas)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class EdicionCursoInline(BloqueTraducido):
    model = EdicionCurso
    extra = 0
    fields = ('nombre', 'anio', 'inicio', 'fin', 'inscripciones_desde', 'inscripciones_hasta', 'cupo', 'horario',
              'lugar', 'horas_certificadas', 'activa')


class ModuloCursoInline(BloqueTraducido):
    model = ModuloCurso
    extra = 0
    fields = ('orden', 'titulo', 'descripcion')


class LeccionCursoInline(BloqueTraducido):
    model = LeccionCurso
    extra = 0
    fields = ('orden', 'titulo', 'tipo', 'video_url', 'archivo', 'sala', 'enlace', 'reunion_url', 'fecha_hora',
              'duracion_min', 'grabacion_url', 'obligatoria', 'publicada')


@admin.register(Curso)
class CursoAdmin(AdministracionTraducida):
    list_display = ('codigo', 'nombre', 'unidad', 'clasificacion', 'origen', 'duracion_horas', 'activo', 'publicado')
    list_filter = ('activo', 'publicado', 'origen', 'clasificacion', 'modalidad', 'unidad')
    search_fields = ('codigo', 'nombre', 'lema', 'descripcion')
    autocomplete_fields = ('unidad', 'actividad_catalogo')
    list_editable = ('activo', 'publicado')
    ordering = ('unidad', 'orden', 'nombre')
    inlines = (EdicionCursoInline, ModuloCursoInline)

    def _unidades_permitidas(self, request):
        from apps.gestion_unidades.presentation.permisos import unidades_gestionables, puede_operar_modulo_unidad
        return [unidad.pk for unidad in unidades_gestionables(request.user)
                if puede_operar_modulo_unidad(request.user, unidad, 'practicas')]

    def get_queryset(self, request):
        consulta = super().get_queryset(request).select_related('unidad')
        if request.user.is_superuser:
            return consulta
        return consulta.filter(unidad_id__in=self._unidades_permitidas(request))

    def _alcance(self, request, obj=None):
        return (request.user.is_superuser or (obj.unidad_id in self._unidades_permitidas(request)
                if obj else bool(self._unidades_permitidas(request))))

    def has_add_permission(self, request):
        return super().has_add_permission(request) and self._alcance(request)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._alcance(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._alcance(request, obj)

    def has_delete_permission(self, request, obj=None):
        return (super().has_delete_permission(request, obj) and self._alcance(request, obj)
                and (obj is None or not obj.tiene_historial()))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'unidad' and not request.user.is_superuser:
            from apps.directorio_unidades.models.core import Unidad
            kwargs['queryset'] = Unidad.objects.filter(pk__in=self._unidades_permitidas(request))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inlines(self, request, obj):
        return () if obj and obj.es_externo else super().get_inlines(request, obj)

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        return (*campos, 'unidad', 'codigo') if obj and obj.tiene_historial() else campos

    def get_deleted_objects(self, objs, request):
        eliminados, cantidades, permisos, protegidos = super().get_deleted_objects(objs, request)
        for curso in objs:
            if curso.tiene_historial():
                protegidos.append(f'{curso}: conserva participantes o evidencias; desactiva la actividad.')
        return eliminados, cantidades, permisos, protegidos

    def delete_queryset(self, request, queryset):
        # La eliminación masiva de Django no invoca Model.delete(). Se valida
        # toda la selección antes de borrar una sola ficha.
        with transaction.atomic():
            cursos = list(queryset.select_for_update().order_by('pk'))
            for curso in cursos:
                if not self.has_delete_permission(request, curso):
                    raise ValidationError('La selección contiene actividades con historial o fuera de tu alcance.')
                list(curso.ediciones.select_for_update().order_by('pk').values_list('pk', flat=True))
                curso.validar_eliminacion()
            for curso in cursos:
                curso.delete()

    def delete_view(self, request, object_id, extra_context=None):
        try:
            return super().delete_view(request, object_id, extra_context)
        except ValidationError as error:
            self.message_user(request, ' '.join(error.messages), level=messages.ERROR)
            return redirect('admin:formacion_curso_change', object_id)

    def response_action(self, request, queryset):
        try:
            # Django registra la eliminación antes de llamar delete_queryset.
            # Si la protección detecta actividad nueva, también se revierte
            # ese asiento para no registrar una eliminación que no ocurrió.
            with transaction.atomic():
                return super().response_action(request, queryset)
        except ValidationError as error:
            self.message_user(request, ' '.join(error.messages), level=messages.ERROR)
            return redirect('admin:formacion_curso_changelist')


@admin.register(ModuloCurso)
class ModuloCursoAdmin(FormacionUnidadAdminMixin, AdministracionTraducida):
    list_display = ('titulo', 'curso', 'orden')
    list_filter = ('curso__unidad',)
    search_fields = ('titulo', 'curso__nombre', 'curso__codigo')
    autocomplete_fields = ('curso',)
    ordering = ('curso', 'orden', 'pk')
    inlines = (LeccionCursoInline,)


@admin.register(InscripcionCurso)
class InscripcionCursoAdmin(FormacionUnidadAdminMixin, AdministracionTraducida):
    unidad_lookup = 'edicion__curso__unidad'
    list_display = ('usuario', 'edicion', 'estado', 'fecha_inscripcion', 'fecha_respuesta')
    list_filter = ('estado', 'edicion__curso__unidad', 'edicion__curso')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'edicion__curso__nombre')
    autocomplete_fields = ('usuario',)
    raw_id_fields = ('edicion',)
    ordering = ('-fecha_inscripcion',)

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)

        class FormularioMatriculaLocal(base):
            def clean(self):
                datos = super().clean()
                edicion = datos.get('edicion')
                if edicion and (edicion.curso.es_externo or (not obj and not edicion.curso.activo)):
                    raise ValidationError('Esta actividad no admite nuevas matrículas locales.')
                return datos

        return FormularioMatriculaLocal


@admin.register(ParticipanteEvento)
class ParticipanteEventoAdmin(FormacionUnidadAdminMixin, AdministracionTraducida):
    unidad_lookup = 'edicion__curso__unidad'
    """Las identidades de eventos se cargan y revisan desde la importación."""
    list_display = ('nombres_completos', 'edicion', 'creado_en', 'creado_por')
    list_filter = ('edicion__curso__unidad', 'edicion__curso')
    search_fields = ('nombres_completos', 'documento', 'edicion__curso__nombre')
    readonly_fields = tuple(campo.name for campo in ParticipanteEvento._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UnidadCertificadoFilter(admin.SimpleListFilter):
    title = 'Unidad'
    parameter_name = 'unidad_certificado'

    def lookups(self, request, model_admin):
        from apps.directorio_unidades.models.core import Unidad
        return Unidad.objects.filter(Q(cursos__ediciones__inscripciones__certificados__isnull=False) |
                                     Q(cursos__ediciones__participantes_evento__certificados__isnull=False)).distinct().values_list('pk', 'nombre')

    def queryset(self, request, queryset):
        valor = self.value()
        if valor:
            if not valor.isdecimal():
                return queryset.none()
            return queryset.filter(Q(inscripcion__edicion__curso__unidad_id=int(valor)) |
                                   Q(participante_evento__edicion__curso__unidad_id=int(valor)))
        return queryset


@admin.register(CertificadoCurso)
class CertificadoCursoAdmin(FormacionUnidadAdminMixin, AdministracionTraducida):
    """El registro emitido se consulta; las correcciones pasan por anular y reemitir."""
    list_display = ('codigo', 'nombre', 'curso_nombre', 'tipo', 'emitido_en', 'anulado')
    list_filter = ('tipo', 'emision_manual', 'anulado', UnidadCertificadoFilter)
    search_fields = ('codigo', 'nombre', 'curso_nombre')
    readonly_fields = tuple(campo.name for campo in CertificadoCurso._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracionCertificadoCurso)
class ConfiguracionCertificadoCursoAdmin(FormacionUnidadAdminMixin, AdministracionTraducida):
    """El diseño se cambia desde el editor con su PDF de revisión, no desde una edición incompleta."""
    list_display = ('curso', 'categoria_evento', 'tipo_certificado', 'diseno', 'actualizado_en')
    list_filter = ('categoria_evento', 'tipo_certificado', 'diseno', 'curso__unidad')
    search_fields = ('curso__nombre', 'curso__codigo')
    readonly_fields = tuple(campo.name for campo in ConfiguracionCertificadoCurso._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def consultas_formacion_de_unidad(request, unidad):
    """Registros canónicos de consulta, dentro de la unidad propietaria.

    No se crean proxies ni se conceden permisos nuevos. El flujo editable sigue
    en el curso; estas tarjetas conservan los permisos del ModelAdmin original.
    """
    from urllib.parse import urlencode
    from django.urls import reverse

    filas = []
    for modelo, filtro, parametro in (
        (ConfiguracionCertificadoCurso, Q(curso__unidad=unidad), 'curso__unidad__id__exact'),
        (ParticipanteEvento, Q(edicion__curso__unidad=unidad), 'edicion__curso__unidad__id__exact'),
        (CertificadoCurso, Q(inscripcion__edicion__curso__unidad=unidad)
         | Q(participante_evento__edicion__curso__unidad=unidad), 'unidad_certificado'),
    ):
        panel = admin.site._registry.get(modelo)
        if panel is None or not panel.has_view_or_change_permission(request):
            continue
        opciones = modelo._meta
        filas.append({
            'nombre': str(opciones.verbose_name_plural).capitalize(), 'icono': 'academic',
            'descripcion': {
                ConfiguracionCertificadoCurso: 'Diseños del certificado de cada curso; se editan desde su editor.',
                ParticipanteEvento: 'Identidades de participantes acreditadas en eventos de esta unidad.',
                CertificadoCurso: 'Certificados emitidos para matrículas y participantes externos de esta unidad.',
            }[modelo],
            'seccion': '', 'total': panel.get_queryset(request).filter(filtro).count(),
            'lista': reverse(f'admin:{opciones.app_label}_{opciones.model_name}_changelist')
                     + '?' + urlencode({parametro: unidad.pk}),
            'nuevo': '',
        })
    return filas
