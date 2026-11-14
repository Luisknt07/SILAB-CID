"""Administración de la producción: productos, recetas, calidad, órdenes, lotes y salidas."""

from apps.core.presentation.administracion import AdministracionTraducida, TablaTraducida

from django.contrib import admin

from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, InsumoReceta, LoteProducto, MovimientoProducto, OrdenProduccion, Producto, Receta, SalidaReceta
from apps.plantas_piloto.operacion.models.calidad import ParametroCalidad, PlanCalidad


@admin.register(FamiliaProducto)
class FamiliaProductoAdmin(AdministracionTraducida):
    list_display = ('codigo', 'nombre', 'unidad', 'orden', 'activa')
    list_filter = ('unidad', 'activa')
    search_fields = ('codigo', 'nombre', 'descripcion')
    ordering = ('unidad', 'orden')
    list_editable = ('orden', 'activa')


class EtapaRecetaInline(TablaTraducida):
    model = EtapaReceta
    extra = 0
    fields = (
        'orden', 'nombre', 'tipo', 'equipo', 'espacio', 'duracion_min', 'espera_min',
        'personas', 'rendimiento_pct', 'distancia_m', 'punto_critico', 'punto_control', 'parametro', 'limite',
    )


class InsumoRecetaInline(TablaTraducida):
    model = InsumoReceta
    extra = 0
    autocomplete_fields = ('consumible',)


class SalidaRecetaInline(TablaTraducida):
    model = SalidaReceta
    extra = 0


class LoteProductoInline(TablaTraducida):
    model = LoteProducto
    extra = 0
    fields = (
        'codigo', 'producto', 'cantidad_inicial', 'cantidad_disponible',
        'fecha_produccion', 'fecha_vencimiento', 'estado', 'control_calidad',
    )
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class MovimientoProductoInline(TablaTraducida):
    model = MovimientoProducto
    extra = 0
    fields = ('fecha', 'tipo', 'cantidad', 'destino', 'valor_total', 'referencia', 'registrado_por')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Producto)
class ProductoAdmin(AdministracionTraducida):
    list_display = ('codigo', 'nombre', 'unidad', 'familia', 'tipo', 'unidad_medida', 'precio_venta', 'vida_util_dias', 'activo')
    list_filter = ('unidad', 'familia', 'tipo', 'activo', 'publico', 'requiere_frio')
    search_fields = ('codigo', 'nombre', 'descripcion')
    ordering = ('unidad', 'tipo', 'nombre')
    list_editable = ('activo',)
    autocomplete_fields = ('unidad', 'familia')


@admin.register(Receta)
class RecetaAdmin(AdministracionTraducida):
    list_display = ('codigo', 'nombre', 'unidad', 'familia', 'producto', 'cantidad_base', 'unidad_base', 'rendimiento_esperado', 'origen', 'activa')
    list_filter = ('unidad', 'familia', 'origen', 'activa')
    search_fields = ('codigo', 'nombre', 'producto__nombre')
    inlines = (EtapaRecetaInline, InsumoRecetaInline, SalidaRecetaInline)
    list_editable = ('activa',)
    autocomplete_fields = ('unidad', 'familia', 'producto', 'derivado_de')


class ParametroCalidadInline(TablaTraducida):
    model = ParametroCalidad
    extra = 0
    fields = ('orden', 'nombre', 'tipo', 'unidad_medida', 'minimo', 'maximo', 'valor_esperado', 'metodo',
              'etapa', 'critico', 'activo')


@admin.register(PlanCalidad)
class PlanCalidadAdmin(AdministracionTraducida):
    """Lo que publican 5.1 (protocolos), 5.3 (HACCP) y 5.4 (control de calidad) de cada planta."""
    list_display = ('codigo', 'nombre', 'unidad', 'familia', 'momento', 'aplica_a', 'activo')
    list_filter = ('unidad', 'familia', 'momento', 'activo')
    search_fields = ('codigo', 'nombre', 'descripcion')
    list_editable = ('activo',)
    autocomplete_fields = ('unidad', 'familia', 'producto')
    inlines = (ParametroCalidadInline,)


@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(AdministracionTraducida):
    list_display = (
        'codigo', 'unidad', 'producto', 'origen', 'demostrativa', 'fecha_inicio', 'fecha_fin',
        'cantidad_planificada', 'cantidad_obtenida', 'merma', 'estado',
    )
    list_filter = ('unidad', 'estado', 'origen', 'demostrativa')
    search_fields = ('codigo', 'producto__nombre', 'receta__nombre', 'observaciones')
    date_hierarchy = 'fecha_inicio'
    readonly_fields = (
        'codigo', 'producto', 'cantidad_planificada', 'cantidad_obtenida', 'merma',
        'rendimiento_real_pct', 'detalle_cierre', 'bloqueo', 'creada_en', 'cerrada_en',
    )
    filter_horizontal = ('equipos',)
    inlines = (LoteProductoInline,)


@admin.register(LoteProducto)
class LoteProductoAdmin(AdministracionTraducida):
    list_display = (
        'codigo', 'unidad', 'producto', 'fecha_produccion', 'fecha_vencimiento',
        'cantidad_disponible', 'cantidad_inicial', 'estado', 'control_calidad', 'demostrativo',
    )
    list_filter = ('unidad', 'estado', 'control_calidad', 'producto__tipo', 'demostrativo')
    search_fields = ('codigo', 'producto__nombre', 'orden__codigo')
    date_hierarchy = 'fecha_produccion'
    readonly_fields = ('cantidad_disponible', 'creado_en', 'actualizado_en')
    inlines = (MovimientoProductoInline,)


@admin.register(MovimientoProducto)
class MovimientoProductoAdmin(AdministracionTraducida):
    list_display = ('fecha', 'unidad', 'lote', 'tipo', 'cantidad', 'destino', 'valor_total')
    list_filter = ('unidad', 'tipo')
    search_fields = ('lote__codigo', 'lote__producto__nombre', 'destino', 'referencia')
    date_hierarchy = 'fecha'
    readonly_fields = ('valor_total', 'movimiento_financiero', 'entrada_destino', 'creado_en')

    def has_change_permission(self, request, obj=None):
        # Una salida registrada no se corrige: el lote conserva su historia.
        return obj is None and super().has_change_permission(request, obj)
