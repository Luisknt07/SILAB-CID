"""Movimientos financieros trazables de cada unidad operativa."""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad


class MovimientoFinancieroUnidad(models.Model):
    TIPO_CHOICES = (
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    )
    CATEGORIA_CHOICES = (
        ("servicio", "Cobro por servicio"),
        ("producto", "Venta de producto elaborado"),
        ("aporte_proyecto", "Aporte de proyecto"),
        ("otro_ingreso", "Otro ingreso documentado"),
        ("reposicion_insumos", "Reposición de insumos o materiales"),
        ("mantenimiento", "Mantenimiento o reparación"),
        ("equipo", "Adquisición de equipo"),
        ("software", "Software o licencias"),
        ("operacion", "Gasto operativo"),
        ("otro_egreso", "Otro egreso documentado"),
    )
    CATEGORIAS_INGRESO = {
        "servicio", "producto", "aporte_proyecto", "otro_ingreso"
    }
    CATEGORIAS_EGRESO = {
        "reposicion_insumos", "mantenimiento", "equipo", "software",
        "operacion", "otro_egreso",
    }
    FUENTE_CHOICES = (
        ("autogestion", "Recursos generados por servicios y ventas"),
        ("presupuesto_institucional", "Presupuesto institucional"),
        ("proyecto", "Proyecto de investigación o vinculación"),
        ("donacion", "Donación"),
        ("transferencia", "Transferencia entre unidades"),
        ("otro", "Otra fuente documentada"),
    )
    ESTADO_CHOICES = (
        ("pendiente", "Pendiente de confirmar"),
        ("confirmado", "Confirmado"),
        ("anulado", "Anulado"),
    )
    METODO_CHOICES = (
        ("no_aplica", "No aplica"),
        ("transferencia", "Transferencia o depósito"),
        ("ventanilla", "Ventanilla universitaria"),
        ("tarjeta", "Tarjeta en punto de pago"),
        ("asignacion", "Asignación presupuestaria"),
        ("otro", "Otro medio documentado"),
    )
    PROCEDIMIENTO_CHOICES = (
        ("pendiente", "Por revisar con el área competente"),
        ("publico", "Contratación institucional"),
        ("infima", "Ínfima cuantía"),
        ("catalogo", "Catálogo electrónico"),
        ("caja_chica", "Caja chica autorizada"),
        ("otro", "Otro procedimiento documentado"),
    )

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.PROTECT,
        related_name="movimientos_financieros",
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, db_index=True)
    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES,
        db_index=True,
    )
    fuente_fondos = models.CharField(
        max_length=30,
        choices=FUENTE_CHOICES,
        default="autogestion",
        db_index=True,
        help_text="Identifica el origen de los fondos. La autogestión no sustituye la revisión del procedimiento de compra.",
    )
    estado = models.CharField(
        max_length=12,
        choices=ESTADO_CHOICES,
        default="pendiente",
        db_index=True,
    )
    fecha_movimiento = models.DateField(default=timezone.localdate, db_index=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    metodo = models.CharField(
        max_length=20,
        choices=METODO_CHOICES,
        default="no_aplica",
    )
    referencia = models.CharField(
        max_length=120,
        blank=True,
        help_text="Factura, comprobante, orden de compra, depósito u otra referencia.",
    )
    descripcion = models.CharField(max_length=240)
    clave_idempotencia = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        unique=True,
        editable=False,
        help_text="Evita duplicar el ingreso generado por un mismo cierre operativo.",
    )
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
        help_text="Servicio o venta que originó el ingreso, cuando corresponda.",
    )
    movimiento_inventario = models.ForeignKey(
        'recursos.EntradaInventario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
        help_text="Ingreso físico de inventario financiado por este egreso, cuando corresponda.",
    )
    equipo = models.ForeignKey(
        'recursos.UnidadEquipo', on_delete=models.PROTECT, null=True, blank=True,
        related_name='movimientos_financieros',
        help_text='Activo al que corresponde el egreso; se conserva su vínculo histórico aunque se traspase.',
    )
    mantenimiento = models.ForeignKey(
        'recursos.MantenimientoEquipo', on_delete=models.PROTECT, null=True, blank=True,
        related_name='movimientos_financieros',
        help_text='Orden cuya intervención o repuestos se financian. Vincula también la incidencia y su diagnóstico.',
    )
    procedimiento_solicitado = models.CharField(
        'Procedimiento registrado', max_length=20, choices=PROCEDIMIENTO_CHOICES, default='pendiente',
        help_text='Se registra el procedimiento revisado por el área competente; este libro no autoriza contrataciones.',
    )
    procedimiento_verificado = models.BooleanField(
        'Consta una revisión administrativa emitida', default=False,
        help_text='Declara que existe un respaldo de revisión; no constituye una autorización emitida por el sistema.',
    )
    referencia_autorizacion = models.CharField(
        'Autorización y autoridad responsable', max_length=240, blank=True,
        help_text='Referencia del acto u oficio ya emitido e identificación de la autoridad o delegado.',
    )
    certificacion_presupuestaria = models.CharField(
        'Certificación o fondo autorizado', max_length=240, blank=True,
        help_text='Referencia de disponibilidad certificada o del fondo autorizado que respalda este egreso.',
    )
    fundamento_procedimiento = models.CharField(
        'Reglamento o fundamento aplicable', max_length=240, blank=True,
        help_text='Obligatorio para caja chica u otro procedimiento: referencia y vigencia confirmadas por el área competente.',
    )
    trazabilidad_version = models.PositiveSmallIntegerField(default=1, editable=False)
    comprobante = models.FileField(
        upload_to="finanzas/comprobantes/",
        null=True,
        blank=True,
    )
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos_financieros_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos_financieros_actualizados",
    )
    actualizado_en = models.DateTimeField(auto_now=True)
    motivo_anulacion = models.TextField(blank=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros_anulados",
    )
    anulado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webcitt_movimientofinancierounidad'
        ordering = ("-fecha_movimiento", "-pk")
        verbose_name = "Movimiento financiero de unidad"
        verbose_name_plural = "Movimientos financieros de unidades"
        constraints = (
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="mov_financiero_monto_positivo",
            ),
        )
        indexes = (
            models.Index(
                fields=("unidad", "fecha_movimiento", "estado"),
                name="mov_fin_unidad_fecha_estado",
            ),
        )

    def __str__(self):
        return f"{self.numero_movimiento} · {self.get_tipo_display()} · ${self.monto}"

    @property
    def numero_movimiento(self):
        codigo = self.unidad.codigo or "UPEC"
        return f"MF-{codigo}-{self.pk or 0:06d}"

    def clean(self):
        super().clean()
        errores = {}
        try:
            monto_valido = Decimal(str(self.monto))
            monto_valido = monto_valido.is_finite() and monto_valido > 0
        except (InvalidOperation, TypeError, ValueError):
            monto_valido = False
        if not monto_valido:
            errores["monto"] = "El monto debe ser mayor que cero."
        categorias_validas = (
            self.CATEGORIAS_INGRESO if self.tipo == "ingreso" else self.CATEGORIAS_EGRESO
        )
        if self.tipo in dict(self.TIPO_CHOICES) and self.categoria not in categorias_validas:
            errores["categoria"] = "La categoría no corresponde al tipo de movimiento."
        if self.reserva_id:
            if self.reserva.laboratorio_id != self.unidad_id:
                errores["reserva"] = "La reserva debe pertenecer a la misma unidad."
            elif self.categoria == "servicio" and self.reserva.tipo_solicitud != "servicio":
                errores["reserva"] = "El cobro por servicio debe vincular una solicitud de servicio."
        if self.movimiento_inventario_id:
            movimiento = self.movimiento_inventario
            unidad_movimiento = movimiento.unidad_id or movimiento.consumible.unidad_id
            if unidad_movimiento != self.unidad_id:
                errores["movimiento_inventario"] = (
                    "El movimiento de inventario debe pertenecer a la misma unidad."
                )
            elif self.tipo != "egreso" or movimiento.tipo != "ingreso":
                errores["movimiento_inventario"] = (
                    "Solo un egreso puede financiar un ingreso físico de inventario."
                )
        # Las capturas confirmadas conservan el equipo y la unidad de ese
        # momento. Un traspaso posterior no invalida su asiento ni su anulación.
        vinculos_historicos = bool(self.pk and type(self).objects.filter(
            pk=self.pk, estado__in=('confirmado', 'anulado'), unidad_id=self.unidad_id,
            equipo_id=self.equipo_id, mantenimiento_id=self.mantenimiento_id,
        ).exists()) if self.equipo_id or self.mantenimiento_id else False
        if self.mantenimiento_id:
            modelo_orden = self._meta.get_field('mantenimiento').remote_field.model
            orden = modelo_orden.objects.filter(pk=self.mantenimiento_id).values('equipo_id', 'unidad_id').first()
            if orden is None:
                errores['mantenimiento'] = 'Selecciona una orden de mantenimiento existente.'
            elif self.equipo_id and self.equipo_id != orden['equipo_id']:
                errores['mantenimiento'] = 'La orden de mantenimiento pertenece a otro equipo.'
            elif not self.equipo_id:
                self.equipo_id = orden['equipo_id']
            if orden and not vinculos_historicos and orden['unidad_id'] and orden['unidad_id'] != self.unidad_id:
                errores['mantenimiento'] = 'La orden de mantenimiento debe pertenecer a esta unidad.'
        if self.equipo_id or self.mantenimiento_id:
            modelo_equipo = self._meta.get_field('equipo').remote_field.model
            if self.tipo != 'egreso':
                errores['equipo'] = 'Los vínculos a equipos o mantenimiento corresponden a un egreso.'
            elif not vinculos_historicos and not modelo_equipo.objects.filter(pk=self.equipo_id).filter(
                Q(laboratorio_id=self.unidad_id) | Q(laboratorios__pk=self.unidad_id),
            ).exists():
                errores['equipo'] = 'El equipo debe estar asignado a esta unidad.'
        if self.equipo_id and self.movimiento_inventario_id:
            if self.movimiento_inventario.equipo_id and self.movimiento_inventario.equipo_id != self.equipo_id:
                errores['movimiento_inventario'] = 'El movimiento de inventario está vinculado a otro equipo.'
        if self.tipo == 'egreso' and self.estado == 'confirmado' and self.trazabilidad_version >= 1:
            if not self.referencia.strip():
                errores['referencia'] = 'Registra la referencia de la factura o del comprobante del egreso.'
            if not self.comprobante:
                errores['comprobante'] = 'Adjunta el comprobante antes de confirmar el egreso.'
            if self.procedimiento_solicitado == 'pendiente' or not self.procedimiento_verificado:
                errores['procedimiento_solicitado'] = (
                    'Registra la revisión ya emitida por el área competente y el procedimiento aplicable.'
                )
            if not self.referencia_autorizacion.strip():
                errores['referencia_autorizacion'] = 'Identifica el acto de autorización y su autoridad responsable.'
            if not self.certificacion_presupuestaria.strip():
                errores['certificacion_presupuestaria'] = 'Registra la certificación o el fondo autorizado que respalda el egreso.'
            if self.procedimiento_solicitado in {'caja_chica', 'otro'} and not self.fundamento_procedimiento.strip():
                errores['fundamento_procedimiento'] = 'Registra el reglamento o fundamento vigente revisado por el área competente.'
        if self.estado == "anulado" and not self.motivo_anulacion.strip():
            errores["motivo_anulacion"] = "Explica por qué se anula el movimiento."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        with transaction.atomic(using=kwargs.get('using')):
            return self._guardar_validado(*args, **kwargs)

    def _guardar_validado(self, *args, **kwargs):
        anterior = None
        if self.pk:
            anterior = type(self).objects.select_for_update().get(pk=self.pk)
            if anterior.estado == "anulado":
                raise ValidationError("Un movimiento anulado no puede modificarse.")
            if anterior.estado == "confirmado":
                campos_contables = (
                    "unidad_id", "tipo", "categoria", "fuente_fondos",
                    "fecha_movimiento", "monto", "metodo", "referencia",
                    "descripcion", "reserva_id", "movimiento_inventario_id",
                    "equipo_id", "mantenimiento_id", "comprobante",
                    "procedimiento_solicitado", "procedimiento_verificado",
                    "referencia_autorizacion", "certificacion_presupuestaria",
                    "fundamento_procedimiento", "trazabilidad_version",
                )
                if any(
                    getattr(anterior, campo) != getattr(self, campo)
                    for campo in campos_contables
                ):
                    raise ValidationError(
                        "Un movimiento confirmado no se edita; anúlalo y registra la corrección."
                    )
                if self.estado not in {"confirmado", "anulado"}:
                    raise ValidationError(
                        "Un movimiento confirmado solo puede conservarse o anularse."
                    )
        if anterior is None or anterior.estado == 'pendiente':
            self.trazabilidad_version = 1
            if kwargs.get('update_fields') is not None:
                campos_guardados = {'trazabilidad_version', 'equipo'}
                if self.estado == 'confirmado':
                    # No se puede validar el respaldo en memoria y guardar
                    # únicamente el cambio de estado, perdiendo ese respaldo.
                    campos_guardados.update({
                        'referencia', 'comprobante', 'procedimiento_solicitado', 'procedimiento_verificado',
                        'referencia_autorizacion', 'certificacion_presupuestaria',
                        'fundamento_procedimiento', 'mantenimiento',
                    })
                kwargs['update_fields'] = set(kwargs['update_fields']) | campos_guardados
        if self.estado == "anulado" and (not anterior or anterior.estado != "anulado"):
            self.anulado_en = self.anulado_en or timezone.now()
        self.full_clean()
        return super().save(*args, **kwargs)
