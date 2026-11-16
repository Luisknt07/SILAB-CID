"""Administración de reservas y generación de reportes."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from apps.core.presentation.catalogos import tipos_usuario
from apps.core.presentation.calendario import calendario_actual

from apps.core.presentation.catalogos import facultades, carreras

import base64
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from apps.gestion_unidades.presentation.reportes_filtros import PeriodoReporte, entero_pedido
from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf, reporte_listado_reservas
from apps.gestion_unidades.presentation.reportes_dimensiones import DIMENSIONES, agrupar, es_multiple, horas_efectivas

from apps.reservas.models.reservas import CatalogoActividadReserva, EjemploSolicitudUnidad, GuiaActividadReserva, ImagenGuiaActividad, NotificacionReserva, ProgramacionReserva, RegistroParticipanteReserva, Reserva, ReservaAdjunto, ReservaConsumible, RevisionReserva, SolicitudCambioReserva
from apps.core.models.periodos import PeriodoAcademico
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.presentation.utilizacion import calculate_unit_utilization


def criterios_del_listado(listado):
    """Los filtros que el administrador dejo puestos, con las etiquetas que ve.

    Se leen del propio ChangeList para que el reporte y la pantalla no puedan
    discrepar: si el listado muestra veinte solicitudes de una unidad, eso dice
    la cabecera del documento.
    """
    criterios = []
    for filtro in listado.filter_specs:
        if not getattr(filtro, 'used_parameters', None):
            continue
        elegidos = [
            str(opcion['display'])
            for opcion in filtro.choices(listado)
            if opcion.get('selected')
        ]
        if elegidos:
            criterios.append((str(filtro.title).capitalize(), ' · '.join(elegidos)))
    if listado.query:
        criterios.append(('Búsqueda', listado.query))
    if not criterios:
        criterios.append(('Selección', 'Listado completo, sin filtros aplicados'))
    criterios.append(('Registros', listado.result_count))
    return criterios


class _ExpedienteSoloLecturaAdmin(AdministracionTraducida):
    """Evita que el administrador de Django eluda el flujo versionado."""

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RevisionReserva)
class RevisionReservaAdmin(_ExpedienteSoloLecturaAdmin):
    list_display = [
        'reserva', 'numero', 'tipo', 'estado_reserva', 'creada_por', 'creada_en'
    ]
    list_filter = [('reserva__laboratorio', admin.RelatedOnlyFieldListFilter),
                   'tipo', 'estado_reserva', 'creada_en']
    search_fields = [
        'reserva__codigo_reserva', 'reserva__titulo_solicitud',
        'creada_por__username', 'motivo',
    ]
    ordering = ['-creada_en', '-pk']


@admin.register(SolicitudCambioReserva)
class SolicitudCambioReservaAdmin(_ExpedienteSoloLecturaAdmin):
    list_display = [
        'reserva', 'estado', 'solicitada_por', 'autorizada_por',
        'revisada_por', 'creada_en',
    ]
    list_filter = [('reserva__laboratorio', admin.RelatedOnlyFieldListFilter),
                   'estado', 'creada_en', 'autorizada_en', 'revisada_en']
    search_fields = [
        'reserva__codigo_reserva', 'reserva__titulo_solicitud',
        'solicitada_por__username', 'motivo_solicitud',
    ]
    ordering = ['-creada_en', '-pk']


@admin.register(NotificacionReserva)
class NotificacionReservaAdmin(AdministracionTraducida):
    list_display = ['titulo', 'usuario', 'reserva', 'tipo', 'leida', 'enviada_email', 'creada_en']
    list_filter = [('reserva__laboratorio', admin.RelatedOnlyFieldListFilter),
                   'tipo', 'leida', 'enviada_email', 'creada_en']
    search_fields = ['titulo', 'mensaje', 'usuario__username', 'usuario__email', 'reserva__codigo_reserva']
    readonly_fields = [
        'reserva', 'usuario', 'tipo', 'titulo', 'mensaje', 'url', 'clave',
        'enviada_email', 'fecha_email', 'intentos_email',
        'ultimo_intento_email', 'error_email', 'creada_en',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Campos que decide el ciclo documental (enviar, aprobar, rechazar, versionar,
# archivar) y que el administrador no debe reescribir a mano.
GUIA_CAMPOS_DEL_CICLO = [
    'numero_version', 'es_estructurada', 'es_vigente', 'visibilidad',
    'estado_publicacion', 'solicita_publicacion', 'observaciones_revision',
    'activo', 'contenido', 'subido_por', 'revisado_por', 'revisado_en',
    'aprobado_por', 'aprobado_en', 'archivo_firmado', 'firmado_por', 'firmado_en',
    'firma_certificada_resumen',
]


class GuiaActividadReservaInline(TablaTraducida):
    model = GuiaActividadReserva
    extra = 0
    fields = [
        'titulo', 'numero_version', 'es_estructurada', 'es_vigente', 'archivo',
        'visibilidad', 'estado_publicacion', 'permite_descarga', 'activo',
        'orden', 'subido_por', 'creado_en',
    ]
    readonly_fields = [
        'numero_version', 'es_estructurada', 'es_vigente', 'visibilidad',
        'estado_publicacion', 'activo', 'subido_por', 'creado_en',
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Las versiones nacen del asistente o de "Crear nueva version".
        return False


@admin.register(EjemploSolicitudUnidad)
class EjemploSolicitudUnidadAdmin(AdministracionTraducida):
    """Lo que cada unidad quiere que se escriba al pedirle algo."""

    list_display = ['unidad', 'proposito_codigo', 'activo', 'actualizado_en']
    list_filter = ['proposito_codigo', 'activo', 'unidad']
    search_fields = ['unidad__nombre', 'ejemplo']
    autocomplete_fields = ['unidad']
    ordering = ['unidad__nombre', 'proposito_codigo']


@admin.register(CatalogoActividadReserva)
class CatalogoActividadReservaAdmin(AdministracionTraducida):
    list_display = [
        'nombre', 'codigo', 'proposito_codigo', 'subtipo_actividad', 'unidad',
        'facultad', 'carrera', 'periodo', 'estado_publicacion', 'visibilidad',
        'creado_por', 'activo', 'orden',
    ]
    list_filter = [
        'proposito_codigo', 'subtipo_actividad', 'activo', 'unidad',
        'facultad', 'carrera', 'periodo', 'periodo_academico',
        'estado_publicacion', 'visibilidad',
    ]
    search_fields = [
        'nombre', 'codigo', 'responsable', 'unidad__nombre',
        'creado_por__username', 'creado_por__email',
    ]
    autocomplete_fields = ['unidad', 'periodo', 'creado_por']
    filter_horizontal = ['participantes_autorizados']
    ordering = ['proposito_codigo', 'orden', 'nombre']
    inlines = [GuiaActividadReservaInline]


class ImagenGuiaActividadInline(TablaTraducida):
    """Figuras de la guía: se cargan desde el asistente o el editor; aquí se consultan."""

    model = ImagenGuiaActividad
    extra = 0
    can_delete = False
    fields = ['orden', 'titulo', 'imagen', 'tamano', 'creado_en']
    readonly_fields = ['orden', 'titulo', 'imagen', 'tamano', 'creado_en']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GuiaActividadReserva)
class GuiaActividadReservaAdmin(AdministracionTraducida):
    inlines = [ImagenGuiaActividadInline]
    list_display = [
        'titulo', 'actividad', 'numero_version', 'es_estructurada', 'es_vigente',
        'visibilidad', 'estado_publicacion', 'permite_descarga', 'activo',
        'subido_por', 'actualizado_en', 'abrir_pdf',
    ]
    list_filter = [
        'estado_publicacion', 'es_estructurada', 'es_vigente', 'visibilidad',
        'permite_descarga', 'activo', 'actividad__unidad',
        'creado_en',
    ]
    search_fields = [
        'titulo', 'nombre_original', 'actividad__nombre', 'actividad__codigo',
        'subido_por__username',
    ]
    autocomplete_fields = ['actividad']
    readonly_fields = [
        'actividad', 'nombre_original', 'tamano', 'creado_en', 'actualizado_en',
        'abrir_pdf', *GUIA_CAMPOS_DEL_CICLO,
    ]

    def has_add_permission(self, request):
        # Una guia se crea desde la solicitud o desde "Crear nueva version".
        return False

    def has_delete_permission(self, request, obj=None):
        """Las guías se archivan para conservar su historial documental."""
        return False

    @admin.display(description='Visualizar o descargar')
    def abrir_pdf(self, obj):
        if not obj:
            return 'Sin guía'
        url_visor = reverse('ver_guia_actividad', args=[obj.pk])
        if obj.es_estructurada:
            return format_html(
                '<a class="button" href="{}">Ver guía HTML</a>',
                url_visor,
            )
        if not obj.archivo:
            return 'Sin archivo'
        if not obj.permite_descarga:
            return format_html(
                '<a class="button" href="{}" data-ver-pdf data-pdf-titulo="{}" data-pdf-sin-descarga>Ver PDF</a> '
                '<span style="margin-left:8px;color:#765b16;">Solo visualización</span>',
                url_visor,
                obj.titulo,
            )
        return format_html(
            '<a class="button" href="{}" data-ver-pdf data-pdf-titulo="{}" data-pdf-descarga="{}">Ver PDF</a> '
            '<a class="button" href="{}" download>Descargar</a>',
            url_visor,
            obj.titulo,
            f'{url_visor}?download=1',
            f'{url_visor}?download=1',
        )


@admin.register(ProgramacionReserva)
class ProgramacionReservaAdmin(_ExpedienteSoloLecturaAdmin):
    """Cronograma de consulta; sus sesiones cambian desde el flujo de reservas."""

    list_display = [
        'id', 'laboratorio', 'actividad', 'solicitante', 'frecuencia',
        'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin',
        'total_sesiones', 'estado',
    ]
    list_filter = ['frecuencia', 'estado', 'laboratorio', 'periodo', 'dia_semana']
    search_fields = [
        'actividad__nombre', 'actividad__codigo', 'solicitante__username',
        'solicitante__email', 'laboratorio__nombre',
    ]
    autocomplete_fields = ['laboratorio', 'actividad', 'solicitante', 'periodo']
    readonly_fields = ['creado_en', 'total_sesiones']


class _InlineSoloLectura(TablaTraducida):
    """Inline de consulta: la operacion se hace en Gestionar laboratorio."""

    extra = 0
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


class RegistroParticipanteReservaInline(_InlineSoloLectura):
    model = RegistroParticipanteReserva
    fields = [
        'usuario', 'rol', 'nombre', 'tipo_usuario', 'facultad', 'carrera',
        'nivel_academico', 'institucion', 'asistencia',
    ]
    readonly_fields = [
        'usuario', 'rol', 'nombre', 'tipo_usuario', 'facultad', 'carrera',
        'nivel_academico', 'institucion',
    ]


@admin.register(RegistroParticipanteReserva)
class RegistroParticipanteReservaAdmin(_ExpedienteSoloLecturaAdmin):
    """Fotografía de consulta; asistencia y participantes se sincronizan en el flujo."""

    list_display = [
        'reserva', 'nombre', 'rol', 'tipo_usuario', 'facultad', 'carrera',
        'asistencia',
    ]
    list_filter = [
        'rol', 'tipo_usuario', 'facultad', 'carrera', 'asistencia',
        'reserva__laboratorio',
    ]
    search_fields = [
        'nombre', 'correo', 'reserva__codigo_reserva',
        'reserva__titulo_solicitud',
    ]
    raw_id_fields = ['reserva', 'usuario']


class ReservaConsumibleInline(_InlineSoloLectura):
    model = ReservaConsumible
    autocomplete_fields = ['consumible']
    fields = [
        'consumible', 'metodo_estimacion', 'cantidad_solicitada', 'cantidad_aprobada',
        'cantidad_consumida',
    ]


class ReservaAdjuntoVisualMixin:
    @admin.display(description='Archivo')
    def descargar_archivo(self, obj):
        if not obj or not obj.archivo:
            return 'Sin archivo'
        return format_html(
            '<a class="button" href="{}" download>Descargar {}</a>',
            obj.archivo.url,
            obj.nombre_original,
        )

    @admin.display(description='Tamaño')
    def tamano_legible(self, obj):
        if not obj:
            return '—'
        if obj.tamano < 1024:
            return f'{obj.tamano} B'
        if obj.tamano < 1024 * 1024:
            return f'{obj.tamano / 1024:.1f} KB'
        return f'{obj.tamano / (1024 * 1024):.2f} MB'


class ReservaAdjuntoInline(ReservaAdjuntoVisualMixin, TablaTraducida):
    model = ReservaAdjunto
    extra = 0
    fields = [
        'descargar_archivo', 'nombre_original', 'extension', 'tipo_contenido',
        'tamano_legible', 'indicaciones_visualizacion', 'fecha_carga',
    ]
    readonly_fields = fields
    can_delete = False


@admin.register(ReservaAdjunto)
class ReservaAdjuntoAdmin(ReservaAdjuntoVisualMixin, AdministracionTraducida):
    list_display = [
        'nombre_original', 'reserva', 'extension', 'tamano_legible',
        'fecha_carga', 'descargar_archivo',
    ]
    list_filter = ['extension', 'fecha_carga', 'reserva__laboratorio']
    search_fields = [
        'nombre_original', 'reserva__codigo_reserva',
        'reserva__titulo_solicitud', 'indicaciones_visualizacion',
    ]
    raw_id_fields = ['reserva']
    fields = [
        'reserva', 'descargar_archivo', 'nombre_original', 'extension',
        'tipo_contenido', 'tamano_legible', 'indicaciones_visualizacion',
        'fecha_carga',
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Reserva)
class ReservaAdmin(_ExpedienteSoloLecturaAdmin):
    """Expediente de consulta. La operacion vive en Gestionar laboratorio.

    Cambiar aqui el estado, el horario, los recursos o la cotizacion se
    saltaba la maquina de estados, la compuerta documental, las revisiones,
    la sincronizacion de la planificacion, las notificaciones y la auditoria que si aplica
    el panel. El administrador conserva busqueda, filtros y reportes.
    """

    change_list_template = "admin/reservas_changelist.html"
    list_display = [
        'id', 'codigo_reserva', 'titulo_solicitud', 'producto_solicitado', 'tipo_solicitud', 'provision_consumibles', 'laboratorio', 'responsable_asignado', 'equipo_nombre', 'nombre_completo_solicitante',
        'fecha', 'hora_inicio', 'hora_fin', 'estado', 'fecha_reserva'
    ]
    list_filter = [
        'tipo_solicitud', 'tipo_usuario_solicitante', 'facultad_solicitante',
        'carrera_solicitante', 'proposito_codigo', 'subtipo_actividad',
        'alcance_beneficiario', 'vinculacion_actividad',
        'origen_programacion', 'producto_solicitado__familia',
        'facultad_beneficiaria', 'carrera_beneficiaria',
        'provision_consumibles', 'incluye_espacio', 'solicito_espacio',
        'solicito_equipo', 'solicito_software', 'estado', 'fecha',
        'laboratorio', 'responsable_asignado', 'periodo',
        'programacion',
        'semana_academica_numero', 'fecha_reserva'
    ]
    search_fields = [
        'codigo_reserva', 'titulo_solicitud', 'equipo_codigo', 'equipo_nombre', 'nombre_solicitante',
        'correo_solicitante', 'motivo', 'producto_solicitado__nombre',
        'producto_solicitado__codigo', 'receta__nombre', 'receta__codigo'
    ]
    readonly_fields = [
        'fecha_reserva', 'fecha_actualizacion', 'duracion', 'codigo_reserva',
        'desglose_liquidacion', 'costo_real', 'aporte_institucional_real',
        'valor_final_usuario',
    ]
    raw_id_fields = [
        'laboratorio', 'usuario', 'responsable_asignado', 'programacion', 'periodo',
        'version_calendario', 'semana_academica', 'producto_solicitado', 'receta',
    ]
    filter_horizontal = [
        'servicios_solicitados', 'software_solicitado', 'espacios_solicitados',
        'participantes',
    ]
    inlines = [
        RegistroParticipanteReservaInline,
        ReservaConsumibleInline,
        ReservaAdjuntoInline,
    ]

    fieldsets = (
        ('Información Básica', {
            'fields': (
                'panel_de_gestion', 'laboratorio', 'codigo_reserva', 'titulo_solicitud',
                'tipo_solicitud', 'incluye_espacio', 'alcance_espacio',
                'solicito_espacio', 'solicito_equipo', 'solicito_software',
                'provision_consumibles', 'producto_solicitado', 'receta',
                'factor_proceso', 'materia_prima_cliente',
                'usuario', 'responsable_asignado', 'programacion', 'estado',
            )
        }),
        ('Equipo Reservado', {
            'fields': (
                'equipo_codigo', 'equipo_nombre', 'software_solicitado',
                'servicios_solicitados', 'espacios_solicitados',
            )
        }),
        ('Unidades Seleccionadas', {
            'fields': ('unidades_seleccionadas',),
            'description': 'JSON con las unidades específicas seleccionadas'
        }),
        ('Fecha y Horario', {
            'fields': ('fecha', 'hora_inicio', 'hora_fin', 'horas_seleccionadas', 'duracion')
        }),
        ('Solicitante', {
            'fields': (
                'nombre_solicitante', 'correo_solicitante', 'telefono_solicitante',
                'institucion', 'tipo_usuario_solicitante', 'facultad_solicitante',
                'carrera_solicitante', 'nivel_academico_solicitante',
                'participantes', 'numero_participantes',
            )
        }),
        ('Propósito y contexto institucional', {
            'fields': (
                'proposito_codigo', 'proposito', 'subtipo_actividad',
                'alcance_beneficiario', 'facultad_beneficiaria',
                'carrera_beneficiaria', 'entidad_beneficiaria',
                'vinculacion_actividad', 'actividad_catalogo', 'referencia_actividad',
                'codigo_referencia_actividad', 'periodo', 'periodo_academico',
                'version_calendario', 'semana_academica',
                'semana_academica_numero',
                'responsable_actividad', 'origen_programacion',
                'detalle_otro_proposito',
            )
        }),
        ('Detalles de la Reserva', {
            'fields': ('descripcion_proyecto', 'requisitos_especiales', 'motivo')
        }),
        ('Servicio, cotización y pago', {
            'fields': (
                'modalidad_servicio', 'urgencia_servicio', 'cantidad_piezas',
                'detalle_trabajo', 'fecha_entrega_prevista',
                'desglose_cotizacion', 'costo_estimado',
                'descuento_aplicado', 'cotizacion_aceptada', 'metodo_pago',
                'desglose_liquidacion', 'costo_real',
                'aporte_institucional_real', 'valor_final_usuario',
            )
        }),
        ('Control y Validación', {
            'fields': ('validada_por', 'fecha_validacion', 'observaciones_validacion')
        }),
        ('Metadatos', {
            'fields': ('fecha_reserva', 'fecha_actualizacion', 'notificacion_enviada', 'encargado_notificado'),
            'classes': ('collapse',)
        })
    )


    def get_readonly_fields(self, request, obj=None):
        campos = [field.name for field in self.model._meta.fields]
        campos += [field.name for field in self.model._meta.many_to_many]
        return campos + ['panel_de_gestion']

    @admin.display(description='Operar esta solicitud')
    def panel_de_gestion(self, obj):
        if not obj or not obj.pk or not obj.laboratorio_id:
            return '-'
        url = reverse('gestion_unidad', args=[obj.laboratorio.slug])
        return format_html(
            '<a href="{}?reserva={}" target="_blank" rel="noopener">Abrir en Gestionar laboratorio</a>',
            url,
            obj.pk,
        )

    def nombre_completo_solicitante(self, obj):
        return obj.nombre_completo_solicitante
    nombre_completo_solicitante.short_description = 'Solicitante'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('estadisticas/', self.admin_site.admin_view(self.estadisticas_view), name='reservas-estadisticas'),
            path('reporte-uso/', self.admin_site.admin_view(self.reporte_uso_view), name='reservas-reporte-uso'),
            path('descargar_pdf/', self.admin_site.admin_view(self.descargar_pdf), name='reservas-descargar-pdf'),
            path('reporte-listado/', self.admin_site.admin_view(self.reporte_listado_view), name='reservas-reporte-listado'),
        ]
        return custom_urls + urls

    def reporte_listado_view(self, request):
        """El listado filtrado: primero se ve como queda, luego se descarga.

        Con «formato=pdf» devuelve el mismo documento en PDF institucional; sin
        el parametro, la vista previa con la que se comprueba antes de bajarlo.
        """
        if not self.has_view_permission(request):
            raise PermissionDenied
        consulta = request.GET.copy()
        formato = consulta.pop('formato', [''])[0]
        # El reporte se arma con los filtros del listado; «formato» es nuestro y
        # el ChangeList lo tomaria por un filtro que no existe.
        request.GET = consulta
        try:
            listado = self.get_changelist_instance(request)
        except IncorrectLookupParameters:
            return redirect('admin:reservas_reserva_changelist')
        reporte = reporte_listado_reservas(listado.queryset, criterios_del_listado(listado))
        if formato == 'pdf':
            respuesta = HttpResponse(
                render_unit_report_pdf(reporte), content_type='application/pdf'
            )
            nombre = f"reservas-{reporte['generated_at']:%Y%m%d-%H%M}.pdf"
            respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
            return respuesta
        contexto = {
            **self.admin_site.each_context(request),
            'title': 'Reporte del listado de reservas',
            'reporte_gestion': reporte,
            'consulta': consulta.urlencode(),
            'url_listado': reverse(f'{self.admin_site.name}:{self.opts.app_label}_{self.opts.model_name}_changelist'),
        }
        return TemplateResponse(request, 'admin/reservas_reporte_listado.html', contexto)

    def reporte_uso_view(self, request):
        """Consolida las dimensiones guardadas al momento de cada solicitud."""

        if not self.has_view_permission(request):
            raise PermissionDenied
        queryset = self.get_queryset(request)
        periodos = PeriodoAcademico.objects.all()
        unidades = Unidad.objects.filter(activo=True).order_by('nombre')
        if getattr(self, '_local', lambda r: False)(request):
            unidades = unidades.filter(pk__in=self._unidades(request))
        if getattr(self, 'codigos', None):
            unidades = unidades.filter(dependencia__in=self.codigos())
        unidad_id = entero_pedido(request.GET.get('unidad'), 'Unidad', defecto='')
        periodo_id = entero_pedido(request.GET.get('periodo'), 'Período', defecto='')
        semana_numero = entero_pedido(request.GET.get('semana'), 'Semana', defecto='', maximo=32767)
        tramo = PeriodoReporte.pedido(request.GET, claves=('fecha_desde', 'fecha_hasta'), maximo_dias=730)
        fecha_desde, fecha_hasta = tramo.parametros().values()
        agrupacion = request.GET.get('agrupacion') or 'semana_academica'

        periodo_seleccionado = periodos.filter(pk=periodo_id).first() if periodo_id else None
        unidad_seleccionada = unidades.filter(pk=unidad_id).first() if unidad_id else None
        if unidad_id and unidad_seleccionada is None:
            raise BadRequest('Unidad fuera del alcance del reporte.')
        if periodo_id and periodo_seleccionado is None:
            raise BadRequest('Período inexistente.')
        if unidad_seleccionada:
            queryset = queryset.filter(laboratorio=unidad_seleccionada)
        if periodo_seleccionado:
            queryset = queryset.filter(periodo=periodo_seleccionado)
        if semana_numero:
            queryset = queryset.filter(semana_academica_numero=semana_numero)
        if tramo.desde:
            queryset = queryset.filter(fecha__gte=tramo.desde)
        if tramo.hasta:
            queryset = queryset.filter(fecha__lte=tramo.hasta)

        # Claves del catalogo compartido: las etiquetas y la forma de medir
        # son las mismas que ve el responsable en el panel de su unidad.
        dimensiones = (
            'unidad', 'facultad', 'carrera', 'tipo_solicitud',
            'proposito', 'subtipo', 'alcance', 'vinculacion', 'recurso',
        )
        reportes = []

        # Los cortes de tiempo son dimensiones del mismo catalogo; ya no se
        # reimplementan con funciones de base de datos.
        CORTES_TIEMPO = {
            'periodo': 'periodo',
            'mes': 'mes',
            'trimestre': 'trimestre',
            'anio': 'anio',
            'tipo_jornada': 'jornada',
            'semana_calendario': 'semana_calendario',
            'semana_academica': 'semana_academica',
        }
        clave_tiempo = CORTES_TIEMPO.get(agrupacion, 'semana_academica')


        # Se materializa una sola vez y se reutiliza para cada dimension: el
        # calculo de horas y asistencia usa la ejecucion real, que vive en un
        # JSONField y no puede agregarse en la base de datos.
        from apps.gestion_unidades.presentation.reportes_visitas import reservas_con_visitas
        reservas_del_reporte = list(reservas_con_visitas(queryset).select_related(
            'laboratorio', 'periodo', 'responsable_asignado',
        ).prefetch_related('espacios_solicitados', 'software_solicitado', 'servicios_solicitados'))

        reportes.append({
            'titulo': f'Uso por {DIMENSIONES[clave_tiempo].etiqueta.lower()}',
            'filas': [
                {
                    'nombre': fila['label'],
                    'total': fila['total'],
                    'efectivas': fila['effective'],
                    'horas': round(fila['hours'], 1),
                    'participantes': fila['participants'],
                }
                for fila in agrupar(reservas_del_reporte, clave_tiempo)
            ],
            'metrica': 'Solicitudes',
            'horas_label': 'Horas efectivas',
            'cuenta_varias_veces': False,
        })
        for clave in dimensiones:
            reportes.append({
                'titulo': f'Uso por {DIMENSIONES[clave].etiqueta.lower()}',
                'filas': [
                    {
                        'nombre': fila['label'],
                        'total': fila['total'],
                        'efectivas': fila['effective'],
                        'horas': round(fila['hours'], 1),
                        'participantes': fila['participants'],
                    }
                    for fila in agrupar(reservas_del_reporte, clave)
                ],
                'metrica': 'Solicitudes',
                'horas_label': 'Horas efectivas',
                'cuenta_varias_veces': es_multiple(clave),
            })

        participantes = RegistroParticipanteReserva.objects.filter(
            reserva__in=queryset,
        )
        dimensiones_participantes = [
            ('tipo_usuario', 'Participaciones por tipo de usuario', dict(tipos_usuario())),
            ('facultad', 'Participaciones por facultad de origen', dict(facultades())),
            ('carrera', 'Participaciones por carrera de origen', dict(carreras())),
        ]
        # Una participacion cuenta como efectiva cuando su reserva lo es. El
        # criterio se toma de las reservas ya materializadas para no repetir
        # aqui una definicion distinta de atencion efectiva.
        ids_efectivas = {
            reserva.pk for reserva in reservas_del_reporte if reserva.es_efectiva
        }
        horas_por_reserva = {
            reserva.pk: horas_efectivas(reserva)
            for reserva in reservas_del_reporte
            if reserva.pk in ids_efectivas
        }
        for campo, titulo, etiquetas in dimensiones_participantes:
            acumulado = {}
            for registro in participantes.values('id', campo, 'reserva_id'):
                valor = registro[campo] or ''
                nombre = etiquetas.get(valor, valor) or 'Sin clasificar'
                fila = acumulado.setdefault(
                    nombre,
                    {'nombre': nombre, 'total': 0, 'efectivas': 0, 'horas': 0.0,
                     'participantes': 0},
                )
                fila['total'] += 1
                if registro['reserva_id'] in ids_efectivas:
                    fila['efectivas'] += 1
                    fila['participantes'] += 1
                    fila['horas'] += horas_por_reserva.get(registro['reserva_id'], 0.0)
            filas = sorted(
                ({**fila, 'horas': round(fila['horas'], 1)} for fila in acumulado.values()),
                key=lambda item: (-item['total'], item['nombre']),
            )
            reportes.append({
                'titulo': titulo,
                'filas': filas,
                'metrica': 'Participaciones',
                'horas_label': 'Horas-persona efectivas',
                'cuenta_varias_veces': False,
            })
        indicator_start = date.today() - timedelta(days=30)
        indicator_end = date.today()
        if periodo_seleccionado and periodo_seleccionado.version_vigente:
            version = periodo_seleccionado.version_vigente
            indicator_start = version.fecha_inicio_clases
            indicator_end = version.fecha_fin_periodo
        try:
            if fecha_desde:
                indicator_start = date.fromisoformat(fecha_desde)
            if fecha_hasta:
                indicator_end = date.fromisoformat(fecha_hasta)
        except ValueError:
            pass
        indicator_units = [unidad_seleccionada] if unidad_seleccionada else list(unidades)
        indicadores_utilizacion = [
            calculate_unit_utilization(
                unidad,
                indicator_start,
                indicator_end,
                period=periodo_seleccionado,
            )
            for unidad in indicator_units
            if unidad is not None
        ]

        context = {
            **self.admin_site.each_context(request),
            'title': 'Reporte de uso por carreras y usuarios',
            'reportes': reportes,
            'total_solicitudes': queryset.count(),
            'total_participaciones': participantes.count(),
            'periodos': periodos,
            'unidades': unidades,
            'unidad_seleccionada': unidad_seleccionada,
            'unidad_id': unidad_id,
            'periodo_seleccionado': periodo_seleccionado,
            'semana_numero': str(semana_numero),
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'agrupacion': agrupacion,
            'semanas_disponibles': range(
                1,
                (periodo_seleccionado.semanas_planificadas if periodo_seleccionado else calendario_actual().semanas_maximas) + 1,
            ),
            'indicadores_utilizacion': indicadores_utilizacion,
            'indicator_start': indicator_start,
            'indicator_end': indicator_end,
        }
        return TemplateResponse(request, 'admin/reservas_reporte_uso.html', context)

    def _datos_estadisticos(self, request):
        from apps.gestion_unidades.presentation.reportes_filtros import anio_pedido
        from apps.gestion_unidades.presentation.reportes_estadisticas import estadisticas_reservas

        if not self.has_view_permission(request):
            raise PermissionDenied
        anio = anio_pedido(request.GET.get('year'), None)
        por_unidad = bool(request.GET.get('por_laboratorio'))
        original = request.GET
        parametros = original.copy()
        parametros.pop('year', None)
        parametros.pop('por_laboratorio', None)
        request.GET = parametros
        try:
            listado = self.get_changelist_instance(request)
        except IncorrectLookupParameters:
            raise BadRequest('Los filtros de reservas no son válidos.') from None
        finally:
            request.GET = original
        datos = estadisticas_reservas(
            listado.queryset, anio=anio, por_unidad=por_unidad,
            alcance=str(self.opts.app_config.verbose_name))
        criterios = criterios_del_listado(listado)
        datos['filter_summary'].extend((nombre, valor) for nombre, valor in criterios if nombre != 'Registros')
        datos['filter_summary'].append(('Registros', sum(f[1] + f[2] for f in datos['filas'])))
        return datos, parametros, anio, por_unidad

    def _contexto_estadisticas(self, request, datos, anio, por_unidad):
        from apps.gestion_unidades.presentation.reportes_estadisticas import grafica_estadisticas

        consulta = request.GET.copy()
        if anio:
            consulta['year'] = str(anio)
        alterna = consulta.copy()
        sin_anio = consulta.copy()
        sin_anio.pop('year', None)
        if por_unidad:
            alterna.pop('por_laboratorio', None)
        else:
            alterna['por_laboratorio'] = '1'
        prefijo = 'admin:reservas' if self.opts.app_label == 'reservas' else f'admin:{self.opts.app_label}-reservas'
        return {
            **datos,
            'grafico': base64.b64encode(grafica_estadisticas(
                datos['filas'], datos['titulo_estadisticas'], por_unidad=por_unidad)).decode('ascii'),
            'por_laboratorio': por_unidad, 'selected_year': str(anio) if anio else '',
            'toggle_url': request.path + '?' + alterna.urlencode(),
            'url_sin_anio': request.path + '?' + sin_anio.urlencode(),
            'url_pdf': reverse(prefijo + '-descargar-pdf') + '?' + consulta.urlencode(),
            'url_estadisticas': reverse(prefijo + '-estadisticas') + '?' + consulta.urlencode(),
            'url_reporte_uso': reverse(prefijo + '-reporte-uso'),
            'url_reporte_listado': reverse(prefijo + '-reporte-listado'),
            'url_listado': reverse(f'admin:{self.opts.app_label}_{self.opts.model_name}_changelist'),
        }

    def changelist_view(self, request, extra_context=None):
        datos, parametros, anio, por_unidad = self._datos_estadisticos(request)
        contexto = {**(extra_context or {}), **self._contexto_estadisticas(request, datos, anio, por_unidad)}
        original = request.GET
        request.GET = parametros
        try:
            return super().changelist_view(request, extra_context=contexto)
        finally:
            request.GET = original

    def estadisticas_view(self, request):
        datos, _, anio, por_unidad = self._datos_estadisticos(request)
        contexto = {**self.admin_site.each_context(request),
                    **self._contexto_estadisticas(request, datos, anio, por_unidad),
                    'title': datos['titulo_estadisticas']}
        return TemplateResponse(request, 'admin/reservas_estadisticas.html', contexto)

    def descargar_pdf(self, request):
        from apps.gestion_unidades.presentation.reportes_estadisticas import grafica_estadisticas

        datos, _, _, por_unidad = self._datos_estadisticos(request)
        datos['dataset']['grafica'] = grafica_estadisticas(
            datos['filas'], datos['titulo_estadisticas'], por_unidad=por_unidad)
        respuesta = HttpResponse(render_unit_report_pdf(datos), content_type='application/pdf')
        respuesta['Content-Disposition'] = 'attachment; filename="reporte_reservas.pdf"'
        return respuesta
