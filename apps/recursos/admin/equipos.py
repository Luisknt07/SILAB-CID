"""Administración de categorías y unidades físicas de equipamiento."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from django import forms
from django.contrib import admin
from django.db.models import Count, Q
from django.urls import NoReverseMatch, path, reverse
from django.utils.html import format_html, format_html_join

from apps.recursos.presentation.edicion_equipo import EspecificacionesMixin
from apps.gestion_unidades.presentation.plantillas_ficha import GENERAL, plantilla_de
from apps.recursos.presentation.verificacion_equipos import verificar_existencia
from apps.recursos.presentation.ciclo_vida_equipo import CAMPOS_CICLO, UnidadEquipoCicloVidaForm, guardar_ciclo_vida
from apps.recursos.models.equipos import FotoEquipo, VideoEquipo, CategoriaEquipo, EquiposServicios, FamiliaEquipo, PiezaEquipo
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo


class AliasCodigoUnidadEquipoInline(TablaTraducida):
    model = AliasCodigoUnidadEquipo
    extra = 0
    fields = ('codigo', 'creado_en')
    readonly_fields = ('creado_en',)


def insumos_asociados(obj, app_label='recursos'):
    """Los insumos compatibles del activo, con el enlace para administrarlos.

    Son los mismos que ofrece la reserva; el texto libre de antes solo se
    muestra si quedo de una carga anterior sin relacion registrada.
    """
    if not obj or not obj.pk:
        return format_html('<em>{}</em>', 'Se registran después de guardar el activo.')
    nombres = list(obj.insumos_compatibles().values_list('nombre', flat=True))
    try:
        url = reverse(f'admin:{app_label}_consumibleporequipo_changelist')
    except NoReverseMatch:
        url = reverse('admin:recursos_consumibleporequipo_changelist')
    enlace = format_html('<a href="{}?equipo__id__exact={}">{}</a>', url, obj.equipo_id,
                         'Administrar insumos compatibles')
    if nombres:
        lista = format_html_join('', '<li>{}</li>', ((nombre,) for nombre in nombres))
        return format_html('<ul class="citt-insumos-asociados">{}</ul>{}', lista, enlace)
    if obj.insumos_necesarios:
        return format_html('<p><em>Descripción heredada, sin insumos registrados:</em> {}</p>{}',
                           obj.insumos_necesarios, enlace)
    return format_html('<p><em>Sin insumos asociados.</em></p>{}', enlace)


class PiezaEquipoInline(TablaTraducida):
    """Las partes de la maquina, que no son insumos.

    El insumo se gasta en el trabajo y no cambia como opera el equipo; la
    pieza si: la boquilla, el extrusor o la cama deciden si imprime y con que
    calidad. Se registran aqui para saber con que repuestos cuenta la unidad.
    """

    model = PiezaEquipo
    extra = 0
    fields = ['clase', 'nombre', 'cantidad', 'descripcion', 'critica',
              'vida_util_horas', 'repuesto_disponible', 'recomendacion', 'orden']


class UnidadEquipoInline(TablaTraducida):
    model = UnidadEquipo
    extra = 0
    readonly_fields = ['estado_visual', 'disponibilidad_info', 'ubicacion_completa', 'insumos']
    fields = [
        'codigo_unidad', 'laboratorio', 'laboratorios', 'estado_unidad',
        'estado_visual', 'ubicacion_especifica', 'disponibilidad_info',
        'insumos',
    ]

    @admin.display(description='Insumos')
    def insumos(self, obj):
        return insumos_asociados(obj)

    @admin.display(description='Estado visual')
    def estado_visual(self, obj):
        if not obj.pk:
            return '-'
        colores = {
            'disponible': '#28a745', 'en_uso': '#dc3545',
            'mantenimiento': '#ffc107', 'dañado': '#6c757d',
            'prestado': '#17a2b8', 'no_disponible': '#6c757d',
        }
        iconos = {
            'disponible': '✅', 'en_uso': '🔴', 'mantenimiento': '🔧',
            'dañado': '❌', 'prestado': '📤', 'no_disponible': '⛔',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colores.get(obj.estado_unidad, '#6c757d'),
            iconos.get(obj.estado_unidad, '❓'),
            obj.get_estado_unidad_display(),
        )

    @admin.display(description='Disponibilidad')
    def disponibilidad_info(self, obj):
        if not obj.pk:
            return '-'
        if obj.disponible_para_reserva:
            return format_html('<span style="color: green;">🟢 Disponible</span>')
        return format_html('<span style="color: red;">🔴 No disponible</span>')


@admin.register(CategoriaEquipo)
class CategoriaEquipoAdmin(AdministracionTraducida):
    list_display = ['nombre', 'codigo', 'icono', 'color', 'activa', 'orden']
    list_filter = ['activa']
    search_fields = ['nombre', 'codigo']
    ordering = ['orden', 'nombre']


class FotoEquipoInline(admin.TabularInline):
    model = FotoEquipo
    extra = 0
    fields = ('imagen', 'imagen_catalogo', 'titulo', 'tipo', 'credito', 'fuente', 'orden')


class VideoEquipoInline(admin.TabularInline):
    model = VideoEquipo
    fk_name = 'equipo'
    extra = 0
    fields = ('url', 'titulo', 'canal', 'idioma', 'orden')
    verbose_name_plural = 'Videos de manejo del modelo (si no tiene, la ficha muestra los de su familia)'


class VideoFamiliaInline(VideoEquipoInline):
    fk_name = 'familia'
    verbose_name_plural = 'Videos de manejo de la familia (los ven todos sus modelos que no tengan propios)'


class FichaTecnicaForm(EspecificacionesMixin, forms.ModelForm):
    """Las especificaciones de la plantilla del grupo como campos y los accesorios como «Cantidad × Nombre | uso»."""

    class Meta:
        model = EquiposServicios
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iniciar_especificaciones(self.instance if self.instance.pk else None)

    def save(self, commit=True):
        tipo = super().save(commit=False)
        self.aplicar_especificaciones(tipo)
        if commit:
            tipo.save()
            self.save_m2m()
        return tipo


@admin.register(FamiliaEquipo)
class FamiliaEquipoAdmin(AdministracionTraducida):
    list_display = ['nombre', 'grupo', 'tipos_count', 'equipos_count', 'enlace_institucional']
    list_filter = ['grupo']
    search_fields = ['nombre', 'grupo', 'tipos__nombre']
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [VideoFamiliaInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            total_tipos=Count('tipos', distinct=True),
            total_equipos=Count('tipos__unidades', filter=Q(tipos__unidades__activa=True), distinct=True),
        )

    @admin.display(description='Tipos de equipo', ordering='total_tipos')
    def tipos_count(self, obj):
        return obj.total_tipos

    @admin.display(description='Equipos activos', ordering='total_equipos')
    def equipos_count(self, obj):
        return obj.total_equipos

    @admin.display(description='Distribución')
    def enlace_institucional(self, obj):
        return format_html('<a href="{}">Ver por unidad</a>', reverse('familia_equipo_institucional', args=[obj.slug]))


@admin.register(EquiposServicios)
class EquiposServiciosAdmin(AdministracionTraducida):
    list_display = [
        'codigo', 'nombre', 'familia', 'familia_tecnologica', 'estado', 'cantidad',
        'unidades_disponibles_count', 'unidades_en_uso_count',
        'porcentaje_disponibilidad_display', 'categorias_display',
        'accesorios_count_display',
    ]
    list_filter = ['rol', 'familia', 'familia_tecnologica', 'estado', 'origen_datos_tecnicos', 'categorias', 'fecha_creacion']
    search_fields = ['codigo', 'nombre', 'marca', 'modelo']
    filter_horizontal = ['categorias', 'apoya_a', 'plantas_con_acceso']
    readonly_fields = [
        'fecha_creacion', 'fecha_actualizacion', 'porcentaje_documentacion',
        'resumen_unidades', 'categorias_html_display',
        'accesorios_resumen_readonly',
    ]
    fieldsets = (
        ('Información básica', {
            'fields': ('codigo', 'nombre', 'descripcion', 'estado', 'rol', 'apoya_a'),
            'description': (
                'Un equipo principal se reserva por sí mismo; un auxiliar acompaña '
                'a los principales que indique y no se reserva aparte.'
            ),
        }),
        ('Catálogo público para reservas', {
            'fields': (
                'imagen_catalogo', 'caracteristicas_publicas', 'uso_publico',
                'instrucciones_publicas',
            ),
            'description': (
                'Información orientativa visible para usuarios; mantenimiento y '
                'observaciones de inventario permanecen en la administración.'
            ),
        }),
        ('Categorización', {
            'fields': ('familia', 'familia_tecnologica', 'categorias', 'categorias_html_display'),
        }),
        ('Información técnica', {
            'fields': (
                'marca', 'modelo', 'fecha_adquisicion', 'software',
                'admite_software_adicional',
            ),
            'classes': ('collapse',),
        }),
        ('Capacidad y operación', {
            'fields': (
                'origen_datos_tecnicos', 'modo_operacion', 'capacidad_nominal', 'unidad_capacidad',
                'capacidad_util_min', 'capacidad_util_max', 'tiempo_setup',
                'tiempo_limpieza',
            ),
            'description': (
                'La carga útil y los tiempos alimentan el cálculo de capacidad. Los valores de '
                'referencia sirven para validar la planta y se publican como «por verificar»; al '
                'registrar el levantamiento real, marca el origen como validado en planta.'
            ),
        }),
        ('Conexiones y consumos', {
            'fields': (
                'potencia_kw', 'potencia_hp', 'voltaje', 'fases', 'frecuencia',
                'corriente_nominal', 'grado_proteccion', 'consumo_vapor',
                'consumo_agua', 'consumo_aire',
            ),
            'classes': ('collapse',),
        }),
        ('Implantación y ergonomía', {
            'fields': (
                'largo_mm', 'ancho_mm', 'alto_mm', 'peso_kg', 'lados_de_acceso',
                'coordenada_x', 'coordenada_y', 'posicion_operario_x',
                'posicion_operario_y',
            ),
            'description': 'Las coordenadas habilitan el diagrama de recorrido.',
            'classes': ('collapse',),
        }),
        ('Confiabilidad, calibración y uso compartido', {
            'fields': (
                'mtbf', 'mttr', 'criticidad', 'fecha_ultima_calibracion',
                'proxima_calibracion', 'es_compartido', 'plantas_con_acceso',
            ),
            'classes': ('collapse',),
        }),
        ('Vida útil de referencia', {
            'fields': ('vida_util_referencia_anios', 'vida_util_horas'),
            'description': (
                'Lo que dura este tipo de equipo cuando el activo no declara su '
                'propia vida útil. Las horas sirven para el cierre por uso intensivo.'
            ),
            'classes': ('collapse',),
        }),
        ('Documentación', {
            'fields': (
                'manual_operacion', 'imagen', 'ficha_tecnica',
                'video_montaje_cuidados', 'explicacion_drivers',
                'porcentaje_documentacion',
            ),
            'classes': ('collapse',),
        }),
        ('Accesorios y complementos', {
            'fields': (
                'accesorios_incluidos', 'accesorios_opcionales',
                'accesorios_resumen_readonly',
            ),
            'description': 'Gestión de accesorios incluidos y opcionales del equipo',
        }),
        ('Inventario', {
            'fields': ('cantidad', 'resumen_unidades'),
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )
    form = FichaTecnicaForm
    inlines = [FotoEquipoInline, VideoEquipoInline, PiezaEquipoInline, UnidadEquipoInline]

    def get_fieldsets(self, request, obj=None):
        # Las especificaciones de la plantilla del grupo del equipo, justo después del catálogo público.
        fieldsets = [list(bloque) for bloque in super().get_fieldsets(request, obj)]
        grupo, plantilla = plantilla_de(obj) if obj is not None else ('Otros', GENERAL)
        especificaciones = (f'Especificaciones técnicas · plantilla «{grupo}»', {
            'fields': [f'espec_{indice}' for indice in range(len(plantilla))] + ['otras_especificaciones'],
            'description': ('Lo que la ficha pública muestra en «Especificaciones técnicas», en este orden. Lo vacío no '
                            'se publica; quien gestiona ve qué falta. Elige la familia para tener la plantilla de su grupo.'),
        })
        posicion = next(indice for indice, (titulo, _opciones) in enumerate(fieldsets) if titulo == 'Catálogo público para reservas')
        fieldsets.insert(posicion + 1, especificaciones)
        for titulo, opciones in fieldsets:
            if titulo == 'Accesorios y complementos':
                opciones['fields'] = ('accesorios_incluidos_texto', 'accesorios_opcionales_texto', 'accesorios_resumen_readonly', 'modos_uso')
        return fieldsets

    @admin.display(description='Disponibles')
    def unidades_disponibles_count(self, obj):
        count = obj.unidades_disponibles
        color = 'green' if count == obj.cantidad else ('orange' if count else 'red')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span>',
            color, count, obj.cantidad,
        )

    @admin.display(description='En uso')
    def unidades_en_uso_count(self, obj):
        color = 'red' if obj.unidades_en_uso else 'green'
        return format_html('<span style="color: {};">{}</span>', color, obj.unidades_en_uso)

    @admin.display(description='Disponibilidad')
    def porcentaje_disponibilidad_display(self, obj):
        try:
            porcentaje = float(obj.porcentaje_disponibilidad)
        except (ValueError, TypeError):
            porcentaje = 0
        color = '#28a745' if porcentaje >= 80 else ('#ffc107' if porcentaje >= 50 else '#dc3545')
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; height: 20px; background-color: {}; text-align: center; '
            'line-height: 20px; color: white; font-size: 12px;">{}%</div></div>',
            int(porcentaje), color, round(porcentaje),
        )

    @admin.display(description='Categorías')
    def categorias_display(self, obj):
        if not obj or not getattr(obj, 'pk', None) or not obj.categorias.exists():
            return format_html('<span style="color: #6c757d;">Sin categorías</span>')
        badges = [
            format_html(
                '<span style="background-color: {}; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 11px; margin-right: 3px;">{} {}</span>',
                categoria.color_seguro, categoria.icono, categoria.nombre,
            )
            for categoria in obj.categorias.all()[:2]
        ]
        if obj.categorias.count() > 2:
            badges.append('<span style="color: #6c757d;">...</span>')
        return format_html(''.join(str(badge) for badge in badges))

    @admin.display(description='Categorías asignadas')
    def categorias_html_display(self, obj):
        if not obj or not getattr(obj, 'pk', None):
            return format_html('<span style="color: #6c757d;">Sin categorías</span>')
        return obj.categorias_html

    @admin.display(description='Resumen de unidades')
    def resumen_unidades(self, obj):
        return format_html(
            '<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">'
            '<strong>Resumen de unidades:</strong><br>📊 Total: {}<br>'
            '✅ Disponibles: <span style="color: green;">{}</span><br>'
            '🔴 En uso: <span style="color: red;">{}</span><br>'
            '🔧 Mantenimiento: <span style="color: orange;">{}</span></div>',
            obj.cantidad, obj.unidades_disponibles, obj.unidades_en_uso,
            obj.unidades_mantenimiento,
        )

    @admin.display(description='Accesorios')
    def accesorios_count_display(self, obj):
        return obj.get_accesorios_count_display()

    @admin.display(description='Resumen de accesorios')
    def accesorios_resumen_readonly(self, obj):
        return obj.get_accesorios_resumen_readonly()


@admin.register(UnidadEquipo)
class UnidadEquipoAdmin(AdministracionTraducida):
    change_list_template = 'admin/recursos/unidadequipo/change_list.html'

    def get_urls(self):
        from apps.recursos.presentation.transparencia import transparencia_equipos_view

        return [path('transparencia/', self.admin_site.admin_view(transparencia_equipos_view),
                     name='recursos_unidadequipo_transparencia')] + super().get_urls()

    form = UnidadEquipoCicloVidaForm
    list_display = [
        'codigo_unidad', 'codigo_bien', 'equipo', 'laboratorio_nombre_display',
        'estado_visual_list', 'disponibilidad_status', 'ubicacion_completa',
        'requiere_atencion_display',
    ]
    list_filter = [
        'equipo', 'laboratorio', 'laboratorios', 'estado_unidad', 'activa',
        'criticidad', 'tipo_bien', 'existencia_verificada', ('codigo_bien', admin.EmptyFieldListFilter), ('fecha_baja', admin.EmptyFieldListFilter),
        ('garantia_hasta', admin.EmptyFieldListFilter),
    ]
    search_fields = [
        'codigo_unidad', 'codigo_bien', 'numero_serie', 'custodio', 'codigos_anteriores__codigo',
        'equipo__nombre', 'equipo__codigo',
        'laboratorio__nombre', 'laboratorios__nombre',
    ]
    # Buscador en vez de una lista con las 2.500 unidades físicas: cada opción consultaba su modelo (N+1).
    autocomplete_fields = ['reemplazado_por']
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo_unidad', 'equipo', 'laboratorio', 'laboratorios')
        }),
        ('Registro patrimonial (bodega)', {
            'fields': (
                ('codigo_bien', 'tipo_bien'), 'clase_bien', 'numero_serie', ('custodio', 'ubicacion_bodega'),
                ('color', 'material'), 'dimensiones', ('fecha_ingreso_bodega', 'valor_contable'),
            ),
            'description': (
                'Lo que lleva la bodega de la Universidad. El código del bien es el de la etiqueta de código de '
                'barras (sin el prefijo institucional) y no puede repetirse. El custodio y el valor no se publican.'
            ),
        }),
        ('Estado y ubicación', {
            'fields': ('estado_unidad', 'ubicacion_especifica', 'activa', ('version_sistema', 'sistema_actualizado'))
        }),
        ('Verificación de existencia', {
            'fields': (('existencia_verificada', 'existencia_verificada_en', 'existencia_verificada_por'), 'existencia_nota'),
            'description': 'Se registra con las acciones «Confirmar que existe» o «No se localizó» (de la lista o de la ficha).',
        }),
        ('Mantenimiento', {
            'fields': (
                'criticidad', 'fecha_ultimo_mantenimiento', 'proximo_mantenimiento',
                'observaciones',
            ),
            'description': 'La criticidad decide qué equipos exigen plan vigente en el seguimiento.',
            'classes': ('collapse',),
        }),
        ('Ciclo de vida', {
            'fields': (
                'vida_util_anios', 'ciclo_version',
                ('fecha_baja', 'motivo_baja'), 'observacion_baja', 'reemplazado_por',
                'respaldo_retiro', 'justificacion_rectificacion',
            ),
            'description': ('Vida útil prevista, retiro de operación y sustitución. Conserva el activo y sus eventos. '
                            'Este registro no constituye autorización administrativa ni patrimonial de baja.'),
            'classes': ('collapse',),
        }),
        ('Garantía del proveedor', {
            'fields': (
                ('garantia_meses', 'garantia_hasta'), 'garantia_cobertura',
                'garantia_contacto',
            ),
            'description': (
                'Cuánto responde el proveedor desde la adquisición y qué cubre. '
                'Un correctivo dentro de ese plazo se registra con ejecutor '
                '«cubierto por la garantía» y sin costo para la unidad.'
            ),
            'classes': ('collapse',),
        }),
        ('Insumos', {
            'fields': ('insumos',),
            'description': 'Los mismos que ofrece la reserva: se administran como insumos '
                           'compatibles, no como texto.',
        }),
        ('Metadatos', {
            'fields': ('fecha_ingreso', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['fecha_ingreso', 'fecha_actualizacion', 'insumos']
    actions = ['marcar_disponible', 'marcar_mantenimiento', 'marcar_no_disponible', 'confirmar_existencia', 'marcar_no_localizado']
    inlines = (AliasCodigoUnidadEquipoInline,)

    def get_form(self, request, obj=None, **kwargs):
        formulario = super().get_form(request, obj, **kwargs)

        class FormularioConAutor(formulario):
            def __init__(self, *args, **form_kwargs):
                form_kwargs['usuario'] = request.user
                super().__init__(*args, **form_kwargs)

        return FormularioConAutor

    def save_model(self, request, obj, form, change):
        campos = (*CAMPOS_CICLO[:3], 'reemplazado_por', 'respaldo_retiro')
        if any(campo in form.changed_data for campo in campos):
            guardar_ciclo_vida(
                obj, request.user, evidencia=form.cleaned_data.get('respaldo_retiro'),
                justificacion=form.cleaned_data.get('justificacion_rectificacion', ''),
                esperados=form.ciclo_inicial,
            )
        else:
            super().save_model(request, obj, form, change)

    @admin.display(description='Laboratorio')
    def laboratorio_nombre_display(self, obj):
        if obj.laboratorio:
            return format_html('🏢 {}', obj.laboratorio.nombre)
        return format_html('<span style="color: #6c757d;">🚫 Sin asignar</span>')

    @admin.display(description='Estado')
    def estado_visual_list(self, obj):
        colores = {
            'disponible': '#28a745',
            'en_uso': '#dc3545',
            'mantenimiento': '#ffc107',
            'dañado': '#6c757d',
            'prestado': '#17a2b8',
            'no_disponible': '#6c757d',
        }
        iconos = {
            'disponible': '✅',
            'en_uso': '🔴',
            'mantenimiento': '🔧',
            'dañado': '❌',
            'prestado': '📤',
            'no_disponible': '⛔',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colores.get(obj.estado_unidad, '#6c757d'),
            iconos.get(obj.estado_unidad, '❓'),
            obj.get_estado_unidad_display(),
        )

    @admin.display(description='Reservable')
    def disponibilidad_status(self, obj):
        if obj.disponible_para_reserva:
            return format_html(
                '<span style="color: green; font-weight: bold;">🟢 Disponible</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">🔴 No disponible</span>'
        )

    @admin.display(description='Insumos compatibles')
    def insumos(self, obj):
        return insumos_asociados(obj, self.opts.app_label)

    @admin.display(description='Atención')
    def requiere_atencion_display(self, obj):
        if not obj.requiere_atencion:
            return format_html('<span style="color: green;">✅ OK</span>')

        motivos = []
        if obj.requiere_insumos:
            motivos.append('Insumos')
        if obj.en_mantenimiento_preventivo:
            motivos.append('Mantenimiento')
        if obj.estado_unidad in ['mantenimiento', 'dañado']:
            motivos.append('Estado')
        return format_html(
            '<span style="color: red; font-weight: bold;">⚠️ {}</span>',
            ', '.join(motivos),
        )

    def get_readonly_fields(self, request, obj=None):
        return [*super().get_readonly_fields(request, obj),
                'existencia_verificada', 'existencia_verificada_en', 'existencia_verificada_por']

    @admin.action(description='Confirmar que existe (verificación)')
    def confirmar_existencia(self, request, queryset):
        for equipo in queryset:
            verificar_existencia(equipo, request.user, existe=True)
        self.message_user(request, f'{queryset.count()} equipos con su existencia confirmada.')

    @admin.action(description='No se localizó (verificación)')
    def marcar_no_localizado(self, request, queryset):
        for equipo in queryset:
            verificar_existencia(equipo, request.user, existe=False)
        self.message_user(request, f'{queryset.count()} equipos marcados como no localizados.')

    @admin.action(description='Marcar como disponible')
    def marcar_disponible(self, request, queryset):
        retirados = queryset.filter(fecha_baja__isnull=False).count()
        updated = queryset.filter(fecha_baja__isnull=True).update(estado_unidad='disponible')
        self.message_user(request, f'{updated} unidades marcadas como disponibles.')
        if retirados:
            self.message_user(request, f'{retirados} equipos retirados se conservaron fuera de operación.', level='warning')

    @admin.action(description='Marcar en mantenimiento')
    def marcar_mantenimiento(self, request, queryset):
        retirados = queryset.filter(fecha_baja__isnull=False).count()
        updated = queryset.filter(fecha_baja__isnull=True).update(estado_unidad='mantenimiento')
        self.message_user(request, f'{updated} unidades marcadas en mantenimiento.')
        if retirados:
            self.message_user(request, f'{retirados} equipos retirados se conservaron fuera de operación.', level='warning')

    @admin.action(description='Marcar como no disponible')
    def marcar_no_disponible(self, request, queryset):
        updated = queryset.update(estado_unidad='no_disponible')
        self.message_user(request, f'{updated} unidades marcadas como no disponibles.')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='LabAdministradores').exists():
            return queryset.filter(laboratorio__administrador=request.user)
        return queryset

    def _administra_unidad(self, request, obj):
        return bool(
            obj.laboratorio
            and obj.laboratorio.administrador == request.user
        )

    def has_change_permission(self, request, obj=None):
        if obj is not None and request.user.groups.filter(name='LabAdministradores').exists():
            return self._administra_unidad(request, obj)
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and request.user.groups.filter(name='LabAdministradores').exists():
            return self._administra_unidad(request, obj)
        return super().has_delete_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if obj is not None and request.user.groups.filter(name='LabAdministradores').exists():
            return self._administra_unidad(request, obj)
        return super().has_view_permission(request, obj)


@admin.register(PiezaEquipo)
class PiezaEquipoAdmin(AdministracionTraducida):
    """Catálogo de partes por tipo de equipo, para saber con qué repuestos se cuenta."""

    list_display = ['nombre', 'equipo', 'clase', 'cantidad', 'critica',
                    'vida_util_horas', 'repuesto_disponible']
    list_filter = ['clase', 'critica', 'repuesto_disponible', 'equipo__familia_tecnologica']
    search_fields = ['nombre', 'descripcion', 'equipo__nombre', 'equipo__codigo']
    autocomplete_fields = ['equipo']
    ordering = ['equipo', 'clase', 'orden', 'nombre']
    fieldsets = (
        ('Identificación', {
            'fields': ('equipo', 'clase', 'nombre', 'cantidad', 'descripcion', 'orden'),
            'description': (
                'Una pieza no es un insumo: el insumo se consume en el trabajo y la '
                'pieza decide si el equipo opera y con qué calidad.'
            ),
        }),
        ('Reposición y cuidado', {
            'fields': ('critica', 'vida_util_horas', 'repuesto_disponible', 'recomendacion'),
        }),
    )
