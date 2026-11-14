
"""Expediente de calidad: el catalogo de lo exigido y la validacion de lo entregado."""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.formats import date_format
from datetime import date

from apps.core.presentation.administracion import AdministracionTraducida

from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente, PoliticaDeCalidad
from apps.documentos.models.mejora import InformeMejora


@admin.register(InformeMejora)
class InformeMejoraAdmin(AdministracionTraducida):
    """Bandeja de consulta; las transiciones usan los servicios del expediente."""
    list_display = ('unidad', 'anio', 'corte', 'estado', 'dependencia', 'abrir_expediente')
    list_filter = ('anio', 'corte', ('unidad', admin.RelatedOnlyFieldListFilter),
                   ('dependencia', admin.RelatedOnlyFieldListFilter))
    search_fields = ('unidad__nombre',)
    actions = None

    def get_queryset(self, request):
        from django.db.models import F, Q
        from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, unidades_gestionables

        consulta = super().get_queryset(request).select_related('unidad', 'dependencia', 'recurso')
        if not request.user.is_active:
            return consulta.none()
        if request.user.is_superuser:
            return consulta
        return consulta.filter(
            Q(unidad_id__in=[u.pk for u in unidades_gestionables(request.user)
                             if puede_operar_modulo_unidad(request.user, u, 'reportes')])
            | Q(remitido_en__isnull=False, dependencia__activa=True,
                dependencia__receptores=request.user, unidad__adscrita_a_id=F('dependencia_id'),
                destinatarios__contains=[{'id': request.user.pk}])).distinct()

    def has_module_permission(self, request):
        return request.user.is_active and request.user.has_perm('documentos.view_documentoexpediente')

    def has_view_permission(self, request, obj=None):
        from apps.documentos.presentation.mejora_seguimiento import puede_leer_mejora
        return self.has_module_permission(request) and (obj is None or puede_leer_mejora(request.user, obj))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)

    def get_fields(self, request, obj=None):
        return tuple(f.name for f in self.model._meta.fields if f.name != 'recurso') + (
            'archivo_informe', 'abrir_expediente')

    @admin.display(description='Archivo del informe')
    def archivo_informe(self, obj):
        if not obj.recurso.activo:
            return f'Versión {obj.recurso.version} sustituida antes de la remisión'
        url = reverse('recurso_unidad', args=[obj.recurso_id])
        return format_html(
            '<a href="{}" data-ver-pdf data-pdf-titulo="Informe de mejora v{}" '
            'data-pdf-descarga="{}?download=1">Ver informe v{}</a>',
            url, obj.recurso.version, url, obj.recurso.version)

    @admin.display(description='Trámite')
    def abrir_expediente(self, obj):
        return format_html('<a href="{}?anio={}&amp;corte={}">Abrir expediente</a>',
                           reverse('gestion_expediente_unidad', args=[obj.unidad.slug]), obj.anio, obj.corte)






@admin.register(PoliticaDeCalidad)
class PoliticaDeCalidadAdmin(AdministracionTraducida):
    """El mínimo con el que se mide a todas las unidades, en un solo lugar.

    Es el indicador institucional del expediente: cambiarlo aquí cambia quién
    cumple y quién pasa a mejora continua en todos los tableros, sin que nadie
    tenga que tocar el código.
    """

    list_display = ('minimo_cumplimiento', 'penalizacion_entrega_tardia', 'actualizado_en', 'actualizado_por')
    fields = ('minimo_cumplimiento', 'penalizacion_entrega_tardia', 'actualizado_en', 'actualizado_por')
    readonly_fields = ('actualizado_en', 'actualizado_por')

    def has_add_permission(self, request):
        """Una sola política: si ya está escrita, se cambia; no se crea otra."""
        return request.user.is_superuser and not PoliticaDeCalidad.objects.exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Sin política no hay con qué medir: se cambia, no se borra."""
        return False

    def save_model(self, request, obj, form, change):
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentoExigido)
class DocumentoExigidoAdmin(AdministracionTraducida):
    readonly_fields = ('alcance_laboratorios',)
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.fecha_limite:
            DocumentoExpediente.objects.filter(exigido=obj, anio=obj.fecha_limite.year,
                                               estado='pendiente').update(vence_el=obj.fecha_limite)

    list_display = ('orden', 'codigo', 'nombre', 'carpeta', 'periodicidad', 'origen', 'requiere_firma',
                    'condicional', 'plazo', 'fuente_reporte', 'activo')
    list_display_links = ('codigo', 'nombre')
    list_filter = ('carpeta', 'periodicidad', 'origen', 'requiere_firma', 'condicional', 'activo')
    search_fields = ('codigo', 'nombre', 'descripcion')
    ordering = ('carpeta', 'orden', 'codigo')
    fieldsets = (
        (None, {'fields': ('codigo', 'nombre', 'descripcion', 'carpeta', 'orden', 'activo')}),
        ('Cuándo y quién', {'fields': ('periodicidad', 'origen', 'requiere_firma', 'condicional',
                                       ('plazo_regla', 'plazo_dias'), 'apertura_dias', ('abre_mes', 'vence_mes'), ('fecha_limite', 'hora_limite')),
                            'description': 'La regla define el vencimiento; la ventana define cuándo puede presentarse. '
                                           'La entrega posterior al cierre no amplía el período de las actividades reportadas.'}),
        ('Alcance', {'fields': ('fuente_reporte', 'tipos_unidad', 'anexo_de', 'alcance_laboratorios'),
                     'description': 'La fuente es la categoría del Centro de reportes que lo genera; los tipos '
                                    'acotan a qué unidades se exige (vacío: a todas).'}),
    )

    @admin.display(description='Aplicación en laboratorios')
    def alcance_laboratorios(self, obj):
        from types import SimpleNamespace
        unidad = SimpleNamespace(dependencia='laboratorios')
        frecuencia = dict(obj.PERIODICIDADES)[obj.periodicidad_para(unidad)]
        return f'{obj.nombre_para(unidad)}. Frecuencia: {frecuencia}. Los otros tipos conservan su catálogo.'

    @admin.display(description='Plazo')
    def plazo(self, obj):
        hora = obj.hora_limite.strftime('%H:%M')
        if obj.fecha_limite:
            return f'{date_format(obj.fecha_limite, "d/m/Y")} · {hora}'
        if obj.plazo_regla == 'ninguno':
            return 'Sin fecha asignada'
        if obj.plazo_regla == 'meses':
            if not obj.abre_mes or not obj.vence_mes:
                return 'Completa los meses de apertura y cierre'
            inicio = date_format(date(2000, obj.abre_mes, 1), 'F')
            fin = date_format(date(2000, obj.vence_mes, 1), 'F')
            return f'De {inicio} a {fin} · {hora}'
        referencia = {'inicio': 'después del inicio', 'fin': 'antes del cierre',
                      'cierre': 'después del cierre del semestre de gestión'}.get(obj.plazo_regla)
        if referencia is None:
            return f'Regla de plazo por revisar · {hora}'
        return f'{obj.plazo_dias} días {referencia} · {hora}'


@admin.register(DocumentoExpediente)
class DocumentoExpedienteAdmin(AdministracionTraducida):
    """Las filas las crea el sistema; aquí se validan u observan."""

    list_display = ('unidad', 'nombre_por_alcance', 'etiqueta_corte', 'carpeta', 'estado', 'vence_el', 'version',
                    'archivo', 'validado_por')
    list_filter = (('unidad', admin.RelatedOnlyFieldListFilter), 'estado', 'exigido__carpeta', 'anio',
                   'exigido__periodicidad')
    search_fields = ('exigido__nombre', 'exigido__codigo', 'unidad__nombre', 'observacion')
    list_select_related = ('unidad', 'exigido', 'recurso', 'validado_por')
    readonly_fields = ('unidad', 'exigido', 'anio', 'corte', 'mes', 'estado', 'recurso', 'version', 'vence_el',
                       'generado_en', 'cargado_en', 'cargado_por', 'validado_en', 'validado_por', 'correccion_hasta',
                       'observacion', 'abrir_observaciones')
    fields = readonly_fields
    actions = ('validar_documentos',)

    @admin.display(description='Documento', ordering='exigido__nombre')
    def nombre_por_alcance(self, obj):
        return f'{obj.exigido.codigo} · {obj.nombre_documental}'

    @admin.display(description='Observaciones y justificaciones')
    def abrir_observaciones(self, obj):
        from urllib.parse import urlencode
        consulta = urlencode(dict(unidad=obj.unidad.slug, anio=obj.anio, corte=obj.corte,
                                  revisar=obj.pk, vista='observaciones'))
        return format_html('<a href="{}?{}#evaluacion">Consultar y corregir observaciones</a>',
                           reverse('admin:reportes-cumplimiento-expediente'), consulta)

    def get_queryset(self, request):
        from apps.gestion_unidades.presentation.permisos import unidades_del_expediente

        return super().get_queryset(request).filter(unidad__in=unidades_del_expediente(request.user))

    def has_change_permission(self, request, obj=None):
        # La lista conserva las acciones de Dirección; cada ficha es de consulta.
        # Los cambios del documento pasan por sus comandos auditados.
        return obj is None and request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    @admin.display(description='Carpeta', ordering='exigido__carpeta')
    def carpeta(self, obj):
        return obj.exigido.get_carpeta_display()

    @admin.display(description='Archivo')
    def archivo(self, obj):
        if not obj.recurso_id:
            return '—'
        url = reverse('recurso_unidad', args=[obj.recurso_id])
        return format_html(
            '<a href="{}" data-ver-pdf data-pdf-titulo="{}" '
            'data-pdf-descarga="{}?download=1">Ver documento</a>',
            url, obj.nombre_documental, url)

    @admin.action(description='Validar los documentos seleccionados', permissions=['change'])
    def validar_documentos(self, request, queryset):
        from apps.documentos.presentation.expediente import validar_documento

        validados, omitidos = 0, 0
        for documento in queryset.select_related('exigido'):
            try:
                validar_documento(documento, request.user, request=request)
                validados += 1
            except ValidationError:
                omitidos += 1
        self.message_user(request, f'{validados} validado(s); {omitidos} sin archivo que validar.',
                          messages.SUCCESS if validados else messages.WARNING)



@admin.register(DocumentoElaborado)
class DocumentoElaboradoAdmin(AdministracionTraducida):
    """Lo que la unidad escribió en el editor guiado; se lee, no se edita desde aquí."""

    list_display = ('documento', 'porcentaje', 'version', 'actualizado_por', 'actualizado_en', 'generado_en')
    list_filter = (('documento__unidad', admin.RelatedOnlyFieldListFilter), 'documento__exigido__fuente_reporte',
                   'documento__anio')
    search_fields = ('documento__unidad__nombre', 'documento__exigido__nombre')
    list_select_related = ('documento', 'documento__unidad', 'documento__exigido', 'actualizado_por')
    readonly_fields = ('documento', 'version', 'actualizado_por', 'actualizado_en', 'generado_en', 'contenido')
    fields = readonly_fields

    def get_queryset(self, request):
        from apps.gestion_unidades.presentation.permisos import unidades_del_expediente

        return super().get_queryset(request).filter(
            documento__unidad__in=unidades_del_expediente(request.user))

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Avance')
    def porcentaje(self, obj):
        from apps.documentos.presentation.expediente_redaccion import avance

        return f"{avance(obj.documento.exigido.fuente_reporte, obj.contenido or {})['porcentaje']} %"
