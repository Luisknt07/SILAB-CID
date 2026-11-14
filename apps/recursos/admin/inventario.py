"""Administración de insumos, materiales y movimientos de inventario."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from django import forms
from django.contrib import admin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, EntradaInventario, LoteConsumible


class EntradaInventarioInline(TablaTraducida):
    model = EntradaInventario
    extra = 0
    fields = [
        'tipo', 'motivo', 'cantidad', 'lote_inventario', 'equipo', 'fecha',
        'referencia', 'costo_unitario', 'responsable_costo', 'saldo_resultante',
        'usuario', 'nota',
    ]
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ConsumiblePorEquipoInline(TablaTraducida):
    model = ConsumiblePorEquipo
    extra = 0


class ConsumibleAdminForm(forms.ModelForm):
    ingreso = forms.DecimalField(
        label='Ingreso',
        required=False,
        max_digits=12,
        decimal_places=3,
        min_value=0,
        widget=forms.NumberInput(attrs={'step': '0.001', 'min': '0'}),
        help_text='Cantidad a registrar como entrada de inventario.',
    )
    consumo = forms.DecimalField(
        label='Consumo',
        required=False,
        max_digits=12,
        decimal_places=3,
        min_value=0,
        widget=forms.NumberInput(attrs={'step': '0.001', 'min': '0'}),
        help_text='Cantidad a registrar como salida de inventario.',
    )

    class Meta:
        model = Consumible
        fields = '__all__'


class MovimientoInventarioQuickForm(forms.Form):
    consumible = forms.ModelChoiceField(
        queryset=Consumible.objects.all(),
        label='Insumo o material',
    )
    tipo = forms.ChoiceField(choices=EntradaInventario.TIPO_CHOICES, label='Tipo')
    cantidad = forms.DecimalField(
        label='Cantidad',
        max_digits=12,
        decimal_places=3,
        min_value=0.001,
        widget=forms.NumberInput(attrs={'step': '0.001', 'min': '0.001'}),
    )
    fecha = forms.DateTimeField(
        label='Fecha',
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    nota = forms.CharField(
        label='Nota',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Opcional'}),
    )
    referencia = forms.CharField(
        label='Referencia',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Factura, entrega, orden...'}),
    )


@admin.register(Consumible)
class ConsumibleAdmin(AdministracionTraducida):
    change_list_template = 'admin/recursos/consumible/change_list.html'
    list_display = [
        'clasificacion', 'familia', 'nombre', 'variante', 'color', 'codigo', 'unidad',
        'stock_total', 'stock_seguridad', 'minimo', 'stock_objetivo', 'alerta_stock',
        'origen_abastecimiento', 'ubicacion', 'unidad_medida', 'visible_en_reservas', 'activo',
    ]
    list_filter = [
        'clasificacion', 'familia', 'color', 'origen_abastecimiento', 'unidad',
        'visible_en_reservas', 'activo', 'unidad_medida',
    ]
    search_fields = [
        'nombre', 'familia', 'variante', 'color', 'marca', 'codigo',
        'unidad__nombre', 'ubicacion', 'lote', 'proveedor_referencia',
    ]
    inlines = [EntradaInventarioInline, ConsumiblePorEquipoInline]
    readonly_fields = ['fecha_actualizacion', 'stock_total']
    form = ConsumibleAdminForm
    fieldsets = (
        ('Identificación', {
            'fields': (
                'unidad', 'codigo', 'nombre', 'descripcion',
            )
        }),
        ('Clasificación del inventario', {
            'description': (
                'Seleccione Insumo cuando se consume o transforma durante la actividad '
                '(PLA, resinas o reactivos). Seleccione Material para elementos de apoyo '
                'o reutilizables (probetas, tubos, accesorios o materiales planos). La '
                'familia organiza el catálogo dentro de cada tipo.'
            ),
            'fields': (
                'clasificacion', 'familia', 'variante', 'color', 'marca',
                'presentacion', 'cantidad_por_presentacion', 'unidad_medida',
                'especificacion_tecnica', 'instrucciones_solicitud', 'precio_unitario',
                'imagen', 'imagen_catalogo', 'ficha_tecnica',
            )
        }),
        ('Stock y plan de reposición', {
            'fields': (
                'stock_total', 'stock_seguridad', 'minimo', 'stock_objetivo',
                'plazo_reposicion_dias', 'origen_abastecimiento',
                'proveedor_referencia', 'ubicacion', 'lote', 'fecha_vencimiento',
                'visible_en_reservas', 'activo', 'ingreso', 'consumo',
            )
        }),
        ('Metadatos', {
            'fields': ('fecha_actualizacion',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Alerta', boolean=True)
    def alerta_stock(self, obj):
        return obj.bajo_minimo

    def changelist_view(self, request, extra_context=None):
        quick_form = MovimientoInventarioQuickForm(request.POST or None)

        if request.method == 'POST' and 'registrar_movimiento' in request.POST:
            if quick_form.is_valid():
                data = quick_form.cleaned_data
                EntradaInventario.objects.create(
                    consumible=data['consumible'],
                    tipo=data['tipo'],
                    cantidad=data['cantidad'],
                    fecha=data['fecha'] or timezone.now(),
                    usuario=request.user,
                    nota=data['nota'] or 'Movimiento registrado desde el inventario',
                    referencia=data['referencia'],
                )
                self.message_user(request, 'Movimiento registrado correctamente.')
                return HttpResponseRedirect(request.path)

        context = extra_context or {}
        context['quick_inventory_form'] = quick_form
        return super().changelist_view(request, extra_context=context)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, EntradaInventario) and not instance.usuario_id:
                instance.usuario = request.user
            instance.save()

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        ingreso = form.cleaned_data.get('ingreso') or 0
        consumo = form.cleaned_data.get('consumo') or 0

        super().save_model(request, obj, form, change)

        if not change and not ingreso and not consumo:
            return

        if ingreso:
            EntradaInventario.objects.create(
                consumible=obj,
                tipo='ingreso',
                cantidad=ingreso,
                usuario=request.user,
                nota='Ingreso registrado desde el administrador de inventario',
                unidad=obj.unidad,
                referencia='ADMIN',
            )

        if consumo:
            EntradaInventario.objects.create(
                consumible=obj,
                tipo='salida',
                cantidad=consumo,
                usuario=request.user,
                nota='Consumo registrado desde el administrador de inventario',
                unidad=obj.unidad,
                referencia='ADMIN',
            )


@admin.register(ConsumiblePorEquipo)
class ConsumiblePorEquipoAdmin(AdministracionTraducida):
    list_display = ['consumible', 'equipo', 'cantidad', 'minimo_alerta', 'ubicacion']
    search_fields = ['consumible__nombre', 'equipo__nombre']
    # La unidad primero: una lista de 220 filas de 21 unidades no dice de quien es cada una.
    list_filter = [('consumible__unidad', admin.RelatedOnlyFieldListFilter), 'equipo']


@admin.register(EntradaInventario)
class EntradaInventarioAdmin(AdministracionTraducida):
    list_display = [
        'consumible', 'unidad', 'tipo', 'motivo', 'cantidad', 'lote_inventario',
        'equipo', 'responsable_costo', 'saldo_resultante', 'referencia', 'fecha', 'usuario',
    ]
    search_fields = ['consumible__nombre', 'consumible__codigo', 'unidad__nombre', 'referencia']
    list_filter = ['unidad', 'tipo', 'motivo', 'responsable_costo', 'fecha']
    readonly_fields = ['saldo_resultante', 'usuario']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [
                'consumible', 'unidad', 'tipo', 'motivo', 'cantidad',
                'lote_inventario', 'equipo', 'reserva', 'incidencia',
                'costo_unitario', 'responsable_costo', 'fecha', 'usuario',
                'nota', 'referencia', 'saldo_resultante',
            ]
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
            if not obj.unidad_id and obj.consumible_id:
                obj.unidad = obj.consumible.unidad
        super().save_model(request, obj, form, change)


@admin.register(LoteConsumible)
class LoteConsumibleAdmin(AdministracionTraducida):
    list_display = [
        'codigo', 'consumible', 'estado', 'cantidad_actual', 'cantidad_inicial',
        'bodega', 'estanteria', 'posicion', 'equipo_en_uso', 'fecha_vencimiento',
        'actualizado_por',
    ]
    list_filter = ['estado', 'consumible__unidad', 'fecha_vencimiento']
    search_fields = [
        'codigo', 'consumible__codigo', 'consumible__nombre', 'bodega',
        'estanteria', 'posicion', 'documento_recepcion',
    ]
    readonly_fields = ['cantidad_inicial', 'cantidad_actual', 'creado_por', 'creado_en', 'actualizado_en']

    def has_add_permission(self, request):
        # Recibir un lote también debe generar el movimiento contable inicial;
        # ese flujo atómico se realiza desde Gestionar laboratorio.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id:
            obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)
