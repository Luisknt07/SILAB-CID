"""Administración de fabricación digital y servicios FabLab."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.templatetags.static import static
from django.utils.html import format_html

from apps.laboratorios.operacion.models.fablab import FablabService, FablabServiceConsumible, SolicitudConsumible, SolicitudFabricacion


class FablabServiceConsumibleInline(TablaTraducida):
    model = FablabServiceConsumible
    extra = 0
    verbose_name = 'Consumible por Servicio'
    verbose_name_plural = 'Consumibles por Servicio'


class FablabServiceAdminForm(forms.ModelForm):
    class Meta:
        model = FablabService
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        unidad = getattr(self.instance, 'unidad', None)
        if unidad:
            self.fields['responsable'].queryset = unidad.responsables_unidad.filter(
                activo=True,
            ).order_by('orden', 'nombre', 'id')

    def clean(self):
        datos = super().clean()
        if datos.get('activo') and datos.get('publico'):
            imagen = datos.get('imagen_referencial')
            ruta_demostrativa = (datos.get('imagen_catalogo') or '').strip()
            if not imagen and not ruta_demostrativa:
                self.add_error(
                    'imagen_referencial',
                    'Los servicios públicos deben tener una imagen referencial.',
                )
        return datos


@admin.register(FablabService)
class FablabServiceAdmin(AdministracionTraducida):
    form = FablabServiceAdminForm
    list_display = [
        'code', 'nombre', 'imagen_publicada', 'unidad', 'tipo_servicio', 'requiere_archivos',
        'requiere_cotizacion', 'tiempo_estimado_texto', 'tarifa_base',
        'activo', 'publico',
    ]
    list_filter = [
        'unidad', 'tipo_servicio', 'requiere_archivos', 'requiere_cotizacion',
        'permite_modelo_listo', 'permite_diseno_asistido',
        'permite_diseno_completo',
        'activo', 'publico',
    ]
    search_fields = [
        'code', 'nombre', 'descripcion', 'resultado_entregado',
        'cuando_elegirlo', 'unidad__nombre',
    ]
    inlines = [FablabServiceConsumibleInline]
    readonly_fields = ['vista_previa_imagen']
    fieldsets = (
        ('Servicio publicado', {
            'fields': (
                'code', 'nombre', 'descripcion', 'unidad', 'tipo_servicio',
                'resultado_entregado', 'cuando_elegirlo', 'tiempo_estimado_texto',
                'unidad_cobro', 'responsable',
                'activo', 'publico',
            )
        }),
        ('Imagen del servicio', {
            'description': (
                'Sube una imagen horizontal que ayude al usuario a reconocer el '
                'resultado o la capacidad técnica. La carga administrada tiene '
                'prioridad sobre la ruta demostrativa.'
            ),
            'fields': (
                'imagen_referencial', 'imagen_catalogo', 'vista_previa_imagen',
            ),
        }),
        ('Guía para el solicitante', {
            'fields': (
                'requiere_reserva', 'requiere_revision_tecnica', 'requiere_cotizacion',
                'requiere_archivos', 'requisitos_usuario', 'formatos_archivo',
            )
        }),
        ('Modalidades permitidas', {
            'description': (
                'Controla las alternativas que se ofrecerán al usuario para este '
                'servicio concreto.'
            ),
            'fields': (
                'permite_modelo_listo', 'permite_diseno_asistido',
                'permite_diseno_completo',
            ),
        }),
        ('Tarifas institucionales', {
            'description': (
                'La simulación suma tarifa base, equipo, mano de obra, insumos y '
                'diseño; luego aplica el descuento correspondiente al perfil del usuario.'
            ),
            'fields': (
                'tarifa_base', 'horas_equipo_estimadas', 'costo_hora_equipo',
                'horas_mano_obra_estimadas', 'costo_hora_mano_obra',
                'costo_diseno_asistido', 'costo_diseno_completo',
                'descuento_estudiante', 'descuento_personal', 'descuento_externo',
            )
        }),
    )

    @admin.display(description='Imagen', boolean=True)
    def imagen_publicada(self, obj):
        return bool(obj.imagen_referencial or obj.imagen_catalogo)

    @admin.display(description='Vista previa')
    def vista_previa_imagen(self, obj):
        if not obj:
            return 'La vista previa aparecerá después de guardar.'
        if obj.imagen_referencial:
            url = obj.imagen_referencial.url
        elif obj.imagen_catalogo:
            url = static(obj.imagen_catalogo)
        else:
            return 'Sin imagen referencial.'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" alt="Vista previa" '
            'style="width:240px;max-width:100%;aspect-ratio:4/3;object-fit:cover;'
            'border-radius:10px;border:1px solid #d8e2dc"></a>',
            url,
            url,
        )

class SolicitudConsumibleInline(TablaTraducida):
    model = SolicitudConsumible
    extra = 0


class SolicitudFabricacionAdminForm(forms.ModelForm):
    class Meta:
        model = SolicitudFabricacion
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        unidad = getattr(self.instance, 'unidad', None)
        if unidad:
            self.fields['servicios'].queryset = FablabService.objects.filter(
                Q(unidad=unidad) | Q(unidad__isnull=True),
                activo=True,
            ).order_by('code', 'nombre')

    def clean(self):
        datos = super().clean()
        unidad = datos.get('unidad')
        reserva = datos.get('reserva')
        servicios = datos.get('servicios')
        if unidad and reserva and reserva.laboratorio_id != unidad.pk:
            self.add_error('reserva', 'La reserva debe pertenecer a la unidad seleccionada.')
        if unidad and servicios is not None:
            incompatibles = servicios.exclude(unidad__isnull=True).exclude(unidad=unidad)
            if incompatibles.exists():
                self.add_error(
                    'servicios',
                    'Selecciona únicamente servicios generales o asociados a esta unidad.',
                )
        revision = datos.get('revision_laboratorista')
        if revision == 'aprobada' and (
            datos.get('costo_materiales_estimado') is None
            or datos.get('tiempo_estimado_horas') is None
        ):
            raise ValidationError(
                'Para aprobar la revisión debe registrar el costo y el tiempo estimados.'
            )
        if revision == 'rechazada' and not datos.get('observaciones_laboratorista'):
            raise ValidationError(
                'Para rechazar la solicitud debe registrar las observaciones del laboratorista.'
            )
        return datos


@admin.register(SolicitudFabricacion)
class SolicitudFabricacionAdmin(AdministracionTraducida):
    form = SolicitudFabricacionAdminForm
    list_display = [
        'numero_orden',
        '__str__',
        'unidad',
        'solicitante',
        'estado_visual',
        'prioridad',
        'responsable_asignado',
        'fecha_programada_inicio',
        'revision_laboratorista',
    ]
    search_fields = [
        'nombre_proyecto', 'solicitante__username', 'departamento',
        'unidad__nombre', 'unidad__codigo', 'responsable_asignado__username',
    ]
    list_filter = [
        'estado',
        'revision_laboratorista',
        'aprobada_decanato',
        'costo_amortizado_decanato',
        'tipo_trabajo',
        'unidad',
        'prioridad',
        'responsable_asignado',
    ]
    readonly_fields = [
        'fecha_revision_laboratorista',
        'fecha_aprobacion_decanato',
        'fecha_amortizacion_decanato',
        'fecha_actualizacion',
        'fecha_cierre',
        'modalidad_reserva',
        'cotizacion_reserva',
        'pago_reserva',
        'participantes_reserva',
    ]
    filter_horizontal = ['servicios', 'maquinas_requeridas']
    inlines = [SolicitudConsumibleInline]
    fieldsets = (
        ('Solicitud', {
            'fields': (
                'unidad', 'reserva', 'solicitante', 'departamento', 'fecha_solicitud', 'tipo_trabajo',
                'nombre_proyecto', 'descripcion_general', 'servicios',
                'materiales_principales', 'maquinas_requeridas',
            )
        }),
        ('Estimación y revisión técnica', {
            'fields': (
                'tiempo_estimado_horas', 'costo_materiales_estimado',
                'maquina_alto_costo', 'estado', 'revision_laboratorista',
                'fecha_revision_laboratorista', 'observaciones_laboratorista',
            )
        }),
        ('Datos recibidos desde la solicitud pública', {
            'fields': (
                'modalidad_reserva', 'cotizacion_reserva', 'pago_reserva',
                'participantes_reserva',
            )
        }),
        ('Decanato y pago', {
            'fields': (
                'aprobada_decanato', 'fecha_aprobacion_decanato',
                'observaciones_decanato', 'costo_amortizado_decanato',
                'fecha_amortizacion_decanato', 'comprobante_pago',
            )
        }),
        ('Gestión de la orden de trabajo', {
            'fields': (
                'prioridad', 'responsable_asignado',
                'fecha_programada_inicio', 'fecha_programada_fin',
                'notas_operativas', 'fecha_cierre',
            )
        }),
        ('Metadatos', {
            'fields': ('fecha_actualizacion',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Estado', ordering='estado')
    def estado_visual(self, obj):
        colores = {
            'pendiente': '#8a6116',
            'en_revision': '#1f5f91',
            'estimada': '#466f38',
            'en_fabricacion': '#5b4b9a',
            'completada': '#1f6d4d',
            'rechazada': '#a33a3a',
        }
        return format_html(
            '<strong style="color:{}">{}</strong>',
            colores.get(obj.estado, '#333'),
            obj.get_estado_display(),
        )

    @admin.display(description='Modalidad solicitada')
    def modalidad_reserva(self, obj):
        if not obj.reserva_id:
            return 'No registrada'
        return obj.reserva.get_modalidad_servicio_display() or 'No registrada'

    @admin.display(description='Cotización aceptada')
    def cotizacion_reserva(self, obj):
        if not obj.reserva_id or obj.reserva.costo_estimado is None:
            return 'Pendiente de estimación'
        return format_html(
            '<strong>${} USD</strong><br><small>Descuento: {}% · {}</small>',
            obj.reserva.costo_estimado,
            obj.reserva.descuento_aplicado,
            'Aceptada' if obj.reserva.cotizacion_aceptada else 'No aceptada',
        )

    @admin.display(description='Método de pago')
    def pago_reserva(self, obj):
        if not obj.reserva_id or not obj.reserva.metodo_pago:
            return 'No definido'
        return obj.reserva.get_metodo_pago_display()

    @admin.display(description='Usuarios participantes')
    def participantes_reserva(self, obj):
        if not obj.reserva_id:
            return 'No registrados'
        nombres = [obj.reserva.nombre_completo_solicitante]
        nombres.extend(
            participante.get_full_name() or participante.username
            for participante in obj.reserva.participantes.all()
        )
        return ', '.join(nombres)
