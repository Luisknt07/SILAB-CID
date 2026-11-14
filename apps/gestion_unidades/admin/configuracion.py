
from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida, BloqueTraducido

from apps.core.presentation.catalogos import tipos_usuario
import re

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Q, TextField
from django.forms.models import BaseInlineFormSet


from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, CapacidadOperativaUnidad, ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.gestion_unidades.models.presentacion import HitoUnidad, LineaAccionUnidad, PresentacionUnidad
from apps.gestion_unidades.models.interior import MedioInterior
from apps.gestion_unidades.models.novedades import NovedadUnidad
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.unidades import UnidadEquipo



from apps.directorio_unidades.presentation.contexto_editor import equipos_de_la_unidad, unidad_en_edicion


class ConfiguracionOperativaUnidadInline(BloqueTraducido):
    model = ConfiguracionOperativaUnidad
    extra = 0
    max_num = 1
    can_delete = False
    classes = ['collapse']
    readonly_fields = ('politica_economica',)

    @admin.display(description='Cobertura institucional')
    def politica_economica(self, obj):
        return (
            'La UPEC asume el 100 % de espacios, mobiliario, equipos, software y '
            'personal, incluidos diseño y guías. Solo se cobran materiales consumidos.'
        )

    fieldsets = (
        ('Flujo y atención', {
            'fields': ('solicitudes_servicio', 'seguimiento', 'indicadores_reportes')
        }),
        ('Orientación pública', {
            'fields': ('tutorial_recursos_url', 'tutorial_servicios_url'),
            'description': 'Solo dos videos genéricos: reservar recursos y encargar un servicio.',
        }),
        ('Reservas e inventario', {
            'fields': ('reservas_espacios', 'reservas_equipos', 'inventario_equipos', 'consumibles')
        }),
        ('Horario de atención al público', {
            'fields': ('hora_apertura_atencion', 'hora_cierre_atencion'),
            'description': (
                'Franja que ven quienes reservan, en horas en punto. Empieza en '
                '08:00–18:00 y cada unidad la ajusta: un laboratorio que abre a las '
                '07:00 o cierra a las 20:00 lo declara aquí y sus usuarios podrán '
                'reservar esas horas. La jornada operativa de cada día se define '
                'aparte, en los horarios de operación; la administración puede '
                'registrar dentro de ella aunque quede fuera de esta franja.'
            ),
        }),
        ('Equipos: mantenimiento y trazabilidad', {
            'fields': ('mantenimiento_equipos', 'incidencias_equipos', 'ciclo_vida_equipos')
        }),
        ('Operación especializada', {
            'fields': ('revision_tecnica', 'cotizacion_costos', 'ordenes_trabajo')
        }),
        ('Producción', {
            'fields': ('registra_produccion', 'tarifa_energia_kwh', 'costo_hora_persona'),
            'description': 'Con estas tarifas cada corrida calcula su energía y su mano de obra.',
        }),
        ('Política económica de reservas de recursos', {
            'fields': (
                'tarifa_referencial_hora_espacio',
                'tarifa_referencial_hora_equipo',
                'tarifa_referencial_hora_software',
                'tarifa_referencial_hora_acompanamiento',
                'politica_economica',
            ),
            'description': (
                'Valores comparables para transparentar el aporte de la Universidad. '
                'Los insumos se calculan de forma independiente según consumo.'
            ),
        }),
        ('Impuestos', {
            'fields': ('aplicar_iva', 'porcentaje_iva'),
            'description': (
                'El IVA se calcula sobre el valor a cargo del usuario y se muestra como '
                'una fila propia en estimaciones, comprobantes y liquidaciones.'
            ),
        }),
    )


class HorarioOperacionUnidadForm(forms.ModelForm):
    tipos_usuario_habilitados = forms.MultipleChoiceField(
        label='Tipos de usuario habilitados',
        choices=tipos_usuario,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Sin selección: todos los tipos de usuario.',
    )
    propositos_habilitados = forms.MultipleChoiceField(
        label='Propósitos institucionales habilitados',
        choices=Reserva.PROPOSITO_INSTITUCIONAL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Sin selección: todos los propósitos institucionales.',
    )

    class Meta:
        model = HorarioOperacionUnidad
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['tipos_usuario_habilitados'] = (
                self.instance.tipos_usuario_habilitados
            )
            self.initial['propositos_habilitados'] = (
                self.instance.propositos_habilitados
            )


class HorarioOperacionUnidadInline(BloqueTraducido):
    model = HorarioOperacionUnidad
    form = HorarioOperacionUnidadForm
    extra = 0
    classes = ['collapse']
    fieldsets = (
        ('Jornada y vigencia', {
            'fields': (
                'periodo', 'nombre', 'dia_semana', 'hora_inicio', 'hora_fin', 'activo',
            ),
            'description': (
                'Sin período se aplica como horario general. Cuando una unidad tiene '
                'jornadas para un período, estas reemplazan el horario general durante '
                'todo ese calendario. S\u00e1bado y domingo son jornadas excepcionales: '
                'al activarlas aparecer\u00e1n en la agenda p\u00fablica, pero sus reservas '
                'solo podr\u00e1 registrarlas la administraci\u00f3n de la unidad.'
            ),
        }),
        ('Servicios y público habilitado', {
            'fields': (
                'permite_recursos', 'permite_servicios',
                'tipos_usuario_habilitados', 'propositos_habilitados',
                'observaciones',
            ),
        }),
    )


class CapacidadOperativaUnidadInline(TablaTraducida):
    model = CapacidadOperativaUnidad
    extra = 0
    classes = ['collapse']
    fields = (
        'periodo', 'vigente_desde', 'vigente_hasta', 'aforo_seguridad',
        'puestos_mobiliario', 'puestos_equipados', 'capacidad_personal',
        'fuente', 'activo',
    )


class BloqueoAgendaUnidadInline(TablaTraducida):
    model = BloqueoAgendaUnidad
    extra = 0
    classes = ['collapse']
    fields = (
        'tipo', 'titulo', 'fecha_inicio', 'fecha_fin', 'dia_completo',
        'hora_inicio', 'hora_fin', 'alcance', 'activo',
    )


class EspacioReservableInline(BloqueTraducido):
    model = EspacioReservable
    extra = 0
    fields = [
        'codigo', 'nombre', 'tipo', 'ubicacion', 'capacidad', 'imagen',
        'descripcion_publica', 'mobiliario_incluido', 'politica_reserva',
        'equipos_asociados', 'responsable',
        'caracteristicas', 'instrucciones_uso', 'reservable', 'activo', 'orden',
    ]
    filter_horizontal = ['equipos_asociados']
    classes = ['collapse']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'equipos_asociados':
            kwargs['queryset'] = equipos_de_la_unidad(request)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'responsable':
            kwargs['queryset'] = ResponsableUnidad.objects.filter(
                unidad_id=unidad_en_edicion(request), activo=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ResponsableUnidadFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if self.instance.dependencia != 'plantas_piloto' or any(self.errors):
            return
        responsables_publicos = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get('DELETE')
            and form.cleaned_data.get('activo')
            and form.cleaned_data.get('publico')
            and (form.cleaned_data.get('nombre') or form.cleaned_data.get('usuario'))
        ]
        if not responsables_publicos:
            raise ValidationError(
                'Una planta piloto debe conservar al menos un responsable activo y público.'
            )


class ResponsableUnidadInline(TablaTraducida):
    model = ResponsableUnidad
    formset = ResponsableUnidadFormSet
    extra = 0
    fields = [
        'usuario', 'nombre', 'rol', 'email', 'telefono', 'foto',
        'descripcion', 'horario_atencion', 'publico',
        'recibe_reservas', 'activo', 'orden',
    ]
    raw_id_fields = ['usuario']
    classes = ['collapse']

    def get_min_num(self, request, obj=None, **kwargs):
        return 1 if obj and obj.dependencia == 'plantas_piloto' else 0


class MedioInteriorInline(TablaTraducida):
    """Fotos y videos de YouTube de «La planta por dentro», cada uno con su área."""
    model = MedioInterior
    extra = 0
    fields = ['tipo', 'espacio', 'titulo', 'descripcion', 'imagen', 'youtube_url', 'orden', 'publicado']
    verbose_name = 'Foto o video'
    verbose_name_plural = 'La planta por dentro: fotos y videos'
    classes = ['collapse']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'espacio':
            kwargs['queryset'] = EspacioReservable.objects.filter(unidad_id=unidad_en_edicion(request), activo=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PresentacionUnidadInline(BloqueTraducido):
    """«Conoce la unidad»: lo que la unidad cuenta de sí misma en su ficha."""
    model = PresentacionUnidad
    max_num = 1
    can_delete = False
    verbose_name = 'Presentación'
    verbose_name_plural = 'Conoce la unidad: presentación'
    classes = ['collapse']
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 3})}}
    fieldsets = (
        (None, {'fields': ('publicada', 'lema')}),
        ('Quién es', {'fields': ('que_es', 'que_hace', 'capacidades', 'areas_trabajo')}),
        ('Rumbo', {'fields': ('mision', 'vision', 'objetivos')}),
        ('Historia e impacto', {'fields': ('historia', 'beneficiarios', 'resultados')}),
        ('Video de presentación', {'fields': ('video_url', 'video_presenta')}),
    )


class LineaAccionUnidadInline(TablaTraducida):
    model = LineaAccionUnidad
    extra = 0
    fields = ['titulo', 'descripcion', 'icono', 'orden']
    verbose_name_plural = 'Conoce la unidad: líneas de acción'
    classes = ['collapse']


class HitoUnidadInline(TablaTraducida):
    model = HitoUnidad
    extra = 0
    fields = ['anio', 'mes', 'tipo', 'titulo', 'descripcion', 'enlace']
    verbose_name_plural = 'Conoce la unidad: hitos de la historia'
    classes = ['collapse']


class NovedadUnidadInline(BloqueTraducido):
    """Lo que pasa en la unidad: llega a su sección «Novedades» y a la página «Noticias» del portal."""
    model = NovedadUnidad
    extra = 0
    verbose_name_plural = 'Novedades: noticias, logros, eventos y convocatorias'
    classes = ['collapse']
    formfield_overrides = {TextField: {'widget': forms.Textarea(attrs={'rows': 5})}}
    fieldsets = (
        (None, {'fields': (('titulo', 'categoria'), 'resumen', 'cuerpo', ('imagen', 'enlace'))}),
        ('Publicación', {'fields': (('fecha_publicacion', 'publicada', 'destacada'),)}),
        ('Solo para eventos y convocatorias', {'fields': (('fecha_evento', 'lugar'), 'cierre')}),
    )


@admin.register(HorarioOperacionUnidad)
class HorarioOperacionUnidadAdmin(AdministracionTraducida):
    form = HorarioOperacionUnidadForm
    list_display = [
        'unidad', 'periodo', 'dia_semana', 'hora_inicio', 'hora_fin',
        'permite_recursos', 'permite_servicios', 'activo',
    ]
    list_filter = [
        'activo', 'dia_semana', 'permite_recursos', 'permite_servicios',
        'periodo', 'unidad',
    ]
    search_fields = ['unidad__nombre', 'periodo__codigo', 'nombre', 'observaciones']
    autocomplete_fields = ['unidad', 'periodo']
    ordering = ['unidad__nombre', 'periodo__codigo', 'dia_semana', 'hora_inicio']
    fieldsets = HorarioOperacionUnidadInline.fieldsets


@admin.register(BloqueoAgendaUnidad)
class BloqueoAgendaUnidadAdmin(AdministracionTraducida):
    list_display = [
        'titulo', 'unidad', 'tipo', 'fecha_inicio', 'fecha_fin',
        'horario_resumido', 'alcance', 'activo',
    ]
    list_filter = ['activo', 'tipo', 'alcance', 'dia_completo', 'unidad']
    search_fields = ['titulo', 'motivo', 'unidad__nombre']
    autocomplete_fields = ['unidad']
    filter_horizontal = ['espacios', 'equipos']
    readonly_fields = ['creado_por', 'creado_en', 'actualizado_en']
    fieldsets = (
        ('Motivo y vigencia', {
            'fields': ('unidad', 'tipo', 'titulo', 'motivo', 'activo', 'visible_en_agenda'),
        }),
        ('Fecha y horario', {
            'fields': ('fecha_inicio', 'fecha_fin', 'dia_completo', 'hora_inicio', 'hora_fin'),
            'description': 'Para feriados o cierres institucionales marca día completo. Para mantenimiento indica solo las horas afectadas.',
        }),
        ('Alcance del bloqueo', {
            'fields': ('alcance', 'espacios', 'equipos', 'bloquea_recursos', 'bloquea_servicios'),
            'description': 'Toda la unidad impide cualquier uso; por áreas o equipos conserva disponible el resto de la capacidad.',
        }),
        ('Auditoría', {'fields': ('creado_por', 'creado_en', 'actualizado_en')}),
    )

    @admin.display(description='Horario')
    def horario_resumido(self, obj):
        if obj.dia_completo:
            return 'Día completo'
        return f'{obj.hora_inicio:%H:%M}–{obj.hora_fin:%H:%M}'

    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(CapacidadOperativaUnidad)
class CapacidadOperativaUnidadAdmin(AdministracionTraducida):
    list_display = [
        'unidad', 'periodo', 'vigente_desde', 'vigente_hasta',
        'capacidad_efectiva_admin', 'factor_limitante', 'activo',
    ]
    list_filter = ['activo', 'periodo', 'unidad']
    search_fields = ['unidad__nombre', 'fuente', 'observaciones']
    autocomplete_fields = ['unidad', 'periodo']
    readonly_fields = ['capacidad_efectiva_admin', 'factor_limitante', 'creado_por', 'creado_en']
    fieldsets = (
        ('Vigencia', {'fields': ('unidad', 'periodo', 'vigente_desde', 'vigente_hasta', 'activo')}),
        ('Límites simultáneos', {
            'fields': (
                'aforo_seguridad', 'puestos_mobiliario', 'puestos_equipados',
                'capacidad_personal', 'capacidad_efectiva_admin', 'factor_limitante',
            ),
            'description': 'La capacidad efectiva es el menor valor: así no se sobredimensiona el laboratorio.',
        }),
        ('Respaldo', {'fields': ('fuente', 'observaciones', 'creado_por', 'creado_en')}),
    )

    @admin.display(description='Capacidad efectiva')
    def capacidad_efectiva_admin(self, obj):
        return obj.capacidad_efectiva if obj else '—'

    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(EspacioReservable)
class EspacioReservableAdmin(AdministracionTraducida):
    list_display = [
        'codigo', 'nombre', 'unidad', 'tipo', 'ubicacion', 'capacidad',
        'politica_reserva', 'reservable', 'activo', 'orden',
    ]
    list_filter = ['tipo', 'politica_reserva', 'reservable', 'activo', 'unidad']
    search_fields = ['codigo', 'nombre', 'unidad__nombre', 'ubicacion']
    list_editable = ['reservable', 'activo', 'orden']
    raw_id_fields = ['unidad']
    filter_horizontal = ['equipos_asociados']
    ordering = ['unidad__nombre', 'orden', 'nombre']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'equipos_asociados':
            match = re.search(r'/espacioreservable/(\d+)/change/', request.path)
            espacio = (
                EspacioReservable.objects.filter(pk=match.group(1)).first()
                if match else None
            )
            if espacio:
                kwargs['queryset'] = UnidadEquipo.objects.filter(
                    Q(laboratorio=espacio.unidad) | Q(laboratorios=espacio.unidad),
                    activa=True,
                ).select_related('equipo').distinct()
            else:
                kwargs['queryset'] = UnidadEquipo.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(ResponsableUnidad)
class ResponsableUnidadAdmin(AdministracionTraducida):
    list_display = [
        'nombre_publico', 'rol', 'unidad', 'administrador_principal', 'email_publico', 'telefono',
        'publico', 'recibe_reservas', 'activo', 'orden',
    ]
    list_filter = ['rol', 'publico', 'recibe_reservas', 'activo', 'unidad']
    search_fields = [
        'nombre', 'email', 'telefono', 'usuario__username',
        'usuario__first_name', 'usuario__last_name', 'unidad__nombre',
    ]
    list_editable = ['publico', 'recibe_reservas', 'activo', 'orden']
    raw_id_fields = ['unidad', 'usuario']
    fields = [
        'unidad', 'usuario', 'nombre', 'rol', 'foto', 'email', 'telefono',
        'descripcion', 'horario_atencion', 'publico', 'recibe_reservas',
        'permisos_operativos', 'activo', 'orden',
    ]
    ordering = ['unidad__nombre', 'orden', 'nombre']

    @admin.display(description='Principal', boolean=True)
    def administrador_principal(self, obj):
        return obj.es_administrador_principal
