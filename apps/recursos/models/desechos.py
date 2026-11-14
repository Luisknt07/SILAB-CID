"""Registro de desechos peligrosos y especiales de cada unidad.

Cada fila es una generación o entrega de desecho con lo que la normativa
ambiental pide poder demostrar: qué es y a qué clase y clave del listado
nacional corresponde, cuánto, en qué envase y dónde se almacenó, y a qué
gestor autorizado se entregó con qué manifiesto. La clave del listado y la
licencia del gestor se escriben tal como los expide la autoridad: el sistema
no fija la norma, la registra.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def documento_desecho_upload_to(instance, filename):
    return f"desechos/{instance.unidad_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class RegistroDesecho(models.Model):
    CLASES = [
        ("peligroso", "Peligroso"),
        ("especial", "Especial"),
    ]
    ESTADOS_FISICOS = [
        ("solido", "Sólido"),
        ("liquido", "Líquido"),
        ("lodo", "Lodo o pasta"),
        ("gaseoso", "Gaseoso"),
    ]
    UNIDADES = [
        ("kg", "kg"),
        ("l", "L"),
        ("unidad", "unidades"),
    ]
    ETAPAS = [
        ("almacenado", "Almacenado temporalmente en la unidad"),
        ("entregado", "Entregado a gestor autorizado"),
        ("tratado", "Tratado o neutralizado en la unidad"),
    ]

    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.PROTECT, related_name="desechos")
    fecha_generacion = models.DateField("Fecha de generación")
    clase = models.CharField(max_length=12, choices=CLASES)
    clave_listado = models.CharField(
        "Clave del listado nacional", max_length=40, blank=True,
        help_text="Código del desecho en el listado nacional de desechos peligrosos o especiales vigente.",
    )
    nombre = models.CharField("Desecho", max_length=160)
    origen = models.CharField(
        "Proceso o práctica que lo genera", max_length=200, blank=True,
    )
    estado_fisico = models.CharField(max_length=10, choices=ESTADOS_FISICOS, default="solido")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad_medida = models.CharField(max_length=8, choices=UNIDADES, default="kg")
    envase = models.CharField(
        "Envase o contenedor", max_length=120, blank=True,
        help_text="Tipo y capacidad del envase; el etiquetado se marca aparte.",
    )
    etiquetado = models.BooleanField("Envase etiquetado", default=False)
    almacenamiento = models.CharField("Lugar de almacenamiento temporal", max_length=160, blank=True)
    etapa = models.CharField(max_length=12, choices=ETAPAS, default="almacenado")
    fecha_entrega = models.DateField("Fecha de entrega al gestor", null=True, blank=True)
    gestor_autorizado = models.CharField("Gestor ambiental autorizado", max_length=160, blank=True)
    licencia_gestor = models.CharField("Licencia o registro del gestor", max_length=80, blank=True)
    manifiesto = models.CharField("Número de manifiesto de entrega", max_length=80, blank=True)
    documento = models.FileField(
        "Manifiesto o acta escaneada", upload_to=documento_desecho_upload_to, max_length=255,
        blank=True, null=True,
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="desechos_a_cargo", verbose_name="Responsable en la unidad",
    )
    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="desechos_registrados", editable=False,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_registrodesecho'
        ordering = ["-fecha_generacion", "-pk"]
        verbose_name = "Registro de desecho"
        verbose_name_plural = "Registros de desechos peligrosos y especiales"
        indexes = [models.Index(fields=["unidad", "fecha_generacion"])]

    def __str__(self):
        return f"{self.nombre} · {self.cantidad} {self.get_unidad_medida_display()} · {self.fecha_generacion:%d/%m/%Y}"

    def clean(self):
        super().clean()
        errores = {}
        if self.cantidad is not None and self.cantidad <= 0:
            errores["cantidad"] = "La cantidad debe ser mayor que cero."
        if self.etapa == "entregado":
            # Una entrega sin gestor ni manifiesto no se puede demostrar.
            if not self.gestor_autorizado.strip():
                errores["gestor_autorizado"] = "Indica a qué gestor autorizado se entregó."
            if not self.manifiesto.strip():
                errores["manifiesto"] = "La entrega se demuestra con el número de manifiesto."
            if not self.fecha_entrega:
                errores["fecha_entrega"] = "Registra la fecha de la entrega."
            if not self.licencia_gestor.strip():
                errores["licencia_gestor"] = "Registra la licencia o autorización del gestor que recibió el desecho."
            if not self.documento:
                errores["documento"] = "Adjunta el manifiesto o acta que respalda la entrega."
            if not self.responsable_id:
                errores["responsable"] = "Asigna al responsable de la entrega en la unidad."
        if self.fecha_entrega and self.fecha_generacion and self.fecha_entrega < self.fecha_generacion:
            errores["fecha_entrega"] = "La entrega no puede ser anterior a la generación."
        if errores:
            raise ValidationError(errores)
