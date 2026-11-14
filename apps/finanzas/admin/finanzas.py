"""Administración de consulta para el libro financiero de las unidades."""

from apps.core.presentation.administracion import AdministracionTraducida

from django.contrib import admin

from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad


@admin.register(MovimientoFinancieroUnidad)
class MovimientoFinancieroUnidadAdmin(AdministracionTraducida):
    list_display = (
        "numero_movimiento", "fecha_movimiento", "unidad", "tipo", "categoria",
        "fuente_fondos", "monto", "estado", "creado_por",
    )
    list_filter = (
        "unidad", "tipo", "categoria", "fuente_fondos", "estado", "fecha_movimiento",
    )
    search_fields = (
        "referencia", "descripcion", "reserva__codigo_reserva",
        "equipo__codigo_unidad", "mantenimiento__codigo", "referencia_autorizacion",
        "creado_por__username", "creado_por__first_name", "creado_por__last_name",
    )
    readonly_fields = (
        "creado_por", "creado_en", "actualizado_por", "actualizado_en",
        "anulado_por", "anulado_en",
    )
    fieldsets = (
        ("Movimiento", {
            "fields": (
                "unidad", "tipo", "categoria", "fuente_fondos", "estado",
                "fecha_movimiento", "monto", "metodo", "referencia", "descripcion",
            )
        }),
        ("Vínculos y soporte", {
            "fields": (
                "reserva", "movimiento_inventario", "equipo", "mantenimiento", "comprobante", "observaciones",
            )
        }),
        ("Revisión administrativa documentada del egreso", {
            "description": "Registra decisiones y respaldos ya emitidos. El sistema no autoriza gastos ni define excepciones por autogestión.",
            "fields": (
                "procedimiento_solicitado", "procedimiento_verificado", "referencia_autorizacion",
                "certificacion_presupuestaria", "fundamento_procedimiento",
            ),
        }),
        ("Trazabilidad", {
            "fields": (
                "creado_por", "creado_en", "actualizado_por", "actualizado_en",
                "motivo_anulacion", "anulado_por", "anulado_en",
            )
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.estado in {"confirmado", "anulado"}:
            fields.extend(
                field.name
                for field in self.model._meta.fields
                if field.name not in {"estado", "motivo_anulacion"}
            )
        if obj and obj.estado == "anulado":
            fields.extend(("estado", "motivo_anulacion"))
        return tuple(dict.fromkeys(fields))

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        obj.actualizado_por = request.user
        if obj.estado == "anulado" and not obj.anulado_por_id:
            obj.anulado_por = request.user
        super().save_model(request, obj, form, change)
