"""Alertas de uso de equipos y traspasos entre unidades, en el administrador.

La lectura no modifica alertas. El cierre de actividad o la tarea de revisión actualiza el seguimiento. Un traspaso se solicita
aquí o desde la ficha del equipo (llega con la unidad, el equipo y la alerta ya puestos); la Dirección lo aprueba,
lo rechaza o lo ejecuta con las acciones de la lista, y el acta se abre desde el propio traspaso.
"""
from apps.core.presentation.administracion import AdministracionTraducida
from datetime import timedelta
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils.html import format_html

from apps.recursos.presentation.traspasos import detectar_equipos_sin_uso, ejecutar_traspaso, marcar_en_reasignacion, puede_aprobar, resolver_traspaso
from apps.recursos.models.redistribucion import AlertaUsoEquipo, EquipoEnTraspaso, PoliticaUsoEquipo, TraspasoEquipo
from apps.recursos.presentation.uso_equipos import politica_uso
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, unidades_gestionables


@admin.register(PoliticaUsoEquipo)
class PoliticaUsoEquipoAdmin(AdministracionTraducida):
    fields = ['dias_sin_uso', 'horas_minimas_anuales', 'dias_atencion', 'fundamento', 'actualizada', 'actualizada_por']
    readonly_fields = ['actualizada', 'actualizada_por']
    list_display = ['__str__', 'dias_sin_uso', 'horas_minimas_anuales', 'dias_atencion', 'actualizada']

    def has_add_permission(self, request):
        return puede_aprobar(request.user) and not PoliticaUsoEquipo.objects.exists()

    def has_change_permission(self, request, obj=None):
        return puede_aprobar(request.user)

    def has_view_permission(self, request, obj=None):
        return puede_aprobar(request.user)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.actualizada_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AlertaUsoEquipo)
class AlertaUsoEquipoAdmin(AdministracionTraducida):
    list_display = ['equipo', 'unidad', 'motivo', 'horas_anuales', 'ultimo_uso', 'detectada', 'estado',
                    'revisar_desde', 'ultima_revision', 'trasladar']
    list_filter = ['estado', 'motivo', 'unidad']
    search_fields = ['equipo__codigo_unidad', 'equipo__codigo_bien', 'equipo__equipo__nombre', 'unidad__nombre']
    readonly_fields = ['equipo', 'unidad', 'motivo', 'horas_anuales', 'ultimo_uso', 'detectada', 'atendida_por',
                       'actualizada', 'ultima_revision', 'evidencia']
    fields = ['equipo', 'unidad', 'motivo', 'horas_anuales', 'ultimo_uso', 'detectada', 'estado', 'justificacion',
              'plan_uso', 'notificada_en', 'revisar_desde', 'ultima_revision', 'evidencia', 'atendida_por', 'actualizada']
    actions = ['pasar_a_estudio', 'detectar_ahora']

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if puede_aprobar(request.user):
            return consulta
        ids = [u.pk for u in unidades_gestionables(request.user)
               if puede_operar_modulo_unidad(request.user, u, 'recursos')]
        return consulta.filter(unidad_id__in=ids)

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if not puede_aprobar(request.user):
            campos += ['estado', 'notificada_en', 'revisar_desde']
        return campos

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        politica = politica_uso()
        if (puede_aprobar(request.user) and obj.notificada_en and not obj.revisar_desde
                and obj.plan_uso.strip() and politica['dias_atencion'] is not None):
            obj.revisar_desde = obj.notificada_en + timedelta(days=politica['dias_atencion'])
        obj.atendida_por = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Traslado')
    def trasladar(self, obj):
        if not obj.vigente or obj.estado == 'reasignacion':
            return '—'
        url = (f"{reverse('admin:recursos_traspasoequipo_add')}?unidad_origen={obj.unidad_id or ''}"
               f"&equipo={obj.equipo_id}&alerta={obj.pk}&motivo=subutilizado")
        return format_html('<a href="{}">Solicitar traslado</a>', url)

    @admin.action(description='Pasar a estudio de la Dirección')
    def pasar_a_estudio(self, request, queryset):
        if not puede_aprobar(request.user):
            raise PermissionDenied('La Dirección establece el estudio y el plazo de revisión.')
        cambiadas = queryset.filter(estado='abierta').update(estado='en_estudio', atendida_por=request.user)
        self.message_user(request, f'{cambiadas} alertas pasaron a estudio.')

    @admin.action(description='Revisar ahora el uso de todos los equipos')
    def detectar_ahora(self, request, queryset):
        if not puede_aprobar(request.user):
            raise PermissionDenied('La Dirección revisa el uso de todos los equipos.')
        resultado = detectar_equipos_sin_uso()
        self.message_user(request, f"{resultado['revisados']} equipos revisados: {resultado['nuevas']} alertas nuevas, "
                                   f"{resultado['cerradas']} cerradas porque volvieron a usarse.")


class EquipoEnTraspasoInline(admin.TabularInline):
    model = EquipoEnTraspaso
    extra = 1
    autocomplete_fields = ['equipo']
    fields = ['equipo', 'codigo_bien', 'codigo_anterior', 'codigo_nuevo', 'custodio_anterior']
    readonly_fields = ['codigo_bien', 'codigo_anterior', 'codigo_nuevo', 'custodio_anterior']

    def has_change_permission(self, request, obj=None):
        return obj is None or obj.en_curso

    def has_add_permission(self, request, obj=None):
        return obj is None or obj.estado == 'solicitado'

    def has_delete_permission(self, request, obj=None):
        return obj is None or obj.estado == 'solicitado'


@admin.register(TraspasoEquipo)
class TraspasoEquipoAdmin(AdministracionTraducida):
    list_display = ['codigo', 'unidad_origen', 'unidad_destino', 'motivo', 'estado', 'fecha_solicitud', 'acta']
    list_filter = ['estado', 'motivo', 'unidad_origen', 'unidad_destino']
    search_fields = ['codigo', 'equipos__codigo_anterior', 'equipos__codigo_nuevo', 'equipos__codigo_bien',
                     'unidad_origen__nombre', 'unidad_destino__nombre']
    inlines = [EquipoEnTraspasoInline]
    autocomplete_fields = ['area_destino']
    readonly_fields = ['codigo', 'estado', 'solicitado_por', 'fecha_solicitud', 'aprobado_por', 'fecha_aprobacion',
                       'ejecutado_por', 'fecha_ejecucion', 'acta']
    fieldsets = (
        ('Traspaso', {'fields': ('codigo', 'estado', 'acta', ('unidad_origen', 'unidad_destino'), 'area_destino',
                                 'motivo', 'justificacion', 'alerta')}),
        ('Dirección', {'fields': (('aprobado_por', 'fecha_aprobacion'), 'observacion_direccion')}),
        ('Entrega y recepción (firmas del acta)', {
            'fields': (('entrega_nombre', 'recibe_nombre'), ('bodega_nombre', 'custodio_nuevo'), 'acta_firmada',
                       ('ejecutado_por', 'fecha_ejecucion')),
            'description': 'Se completa antes de ejecutar: el sistema asigna el nuevo código de laboratorio y conserva el de bodega.',
        }),
        ('Registro', {'fields': (('solicitado_por', 'fecha_solicitud'),)}),
    )
    actions = ['aprobar', 'rechazar', 'ejecutar']

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None and not obj.en_curso:
            campos += ['unidad_origen', 'unidad_destino', 'area_destino', 'motivo', 'justificacion', 'alerta',
                       'entrega_nombre', 'recibe_nombre', 'bodega_nombre', 'custodio_nuevo']
        if not puede_aprobar(request.user):
            campos += ['observacion_direccion']
        return campos

    def get_changeform_initial_data(self, request):
        """Desde la ficha del equipo o una alerta: la unidad, el motivo y la alerta ya vienen puestos."""
        inicial = super().get_changeform_initial_data(request)
        return {clave: valor for clave, valor in inicial.items() if clave in ('unidad_origen', 'unidad_destino', 'motivo', 'alerta')}

    def get_formset_kwargs(self, request, obj, inline, prefix):
        kwargs = super().get_formset_kwargs(request, obj, inline, prefix)
        if obj is None and request.method == 'GET' and isinstance(inline, EquipoEnTraspasoInline) and request.GET.get('equipo'):
            kwargs['initial'] = [{'equipo': request.GET['equipo']}]
        return kwargs

    def save_model(self, request, obj, form, change):
        if not change:
            obj.solicitado_por = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        for item in formset.save(commit=False):
            if not item.codigo_anterior:
                item.codigo_anterior = item.equipo.codigo_unidad
                item.codigo_bien = item.equipo.codigo_bien or ''
                item.custodio_anterior = item.equipo.custodio or ''
            item.save()
        for item in formset.deleted_objects:
            item.delete()
        if form.instance.estado == 'solicitado':
            marcar_en_reasignacion(form.instance)

    @admin.display(description='Acta')
    def acta(self, obj):
        if not obj.pk:
            return '—'
        url = reverse('acta_traspaso_equipos', args=[obj.codigo])
        return format_html(
            '<a href="{}?formato=pdf" data-ver-pdf data-pdf-titulo="Acta de traspaso {}" '
            'data-pdf-descarga="{}?formato=pdf&amp;descargar=1">Acta {}</a>',
            url, obj.codigo, url, obj.codigo,
        )

    def _aplicar(self, request, queryset, funcion, hecho):
        hechos = 0
        for traspaso in queryset:
            try:
                funcion(traspaso)
                hechos += 1
            except (PermissionDenied, ValidationError) as error:
                mensaje = error.messages[0] if isinstance(error, ValidationError) else str(error)
                self.message_user(request, f'{traspaso.codigo}: {mensaje}', messages.ERROR)
        if hechos:
            self.message_user(request, f'{hechos} traspasos {hecho}.')

    @admin.action(description='Aprobar (Dirección)')
    def aprobar(self, request, queryset):
        self._aplicar(request, queryset, lambda traspaso: resolver_traspaso(traspaso, request.user, True), 'aprobados')

    @admin.action(description='Rechazar (Dirección)')
    def rechazar(self, request, queryset):
        self._aplicar(request, queryset, lambda traspaso: resolver_traspaso(traspaso, request.user, False), 'rechazados')

    @admin.action(description='Ejecutar: trasladar y recodificar (Dirección)')
    def ejecutar(self, request, queryset):
        self._aplicar(request, queryset, lambda traspaso: ejecutar_traspaso(traspaso, request.user), 'ejecutados')
