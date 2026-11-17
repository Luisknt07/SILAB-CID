"""Designaciones funcionales documentadas; no son cargos ni permisos técnicos."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AsignacionGobernanza(models.Model):
    ROLES = [
        ("seguimiento", "Seguimiento institucional de Laboratorios y Centros"),
        ("adscripcion", "Validación del consolidado de dependencia"),
        ("centro", "Responsabilidad de Centro"),
        ("investigacion", "Verificación de referencias científicas oficiales"),
    ]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    rol = models.CharField(max_length=20, choices=ROLES)
    referencia = models.CharField(
        max_length=160,
        blank=True,
        help_text="ID de dependencia o identificador público del Centro. Vacío para funciones institucionales.",
    )
    acto = models.CharField("Acto de asignación y alcance", max_length=500)
    desde = models.DateField()
    hasta = models.DateField(null=True, blank=True)
    dedicacion = models.CharField("Dedicación y cobertura autorizadas", max_length=200)
    activa = models.BooleanField(default=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="designaciones_registradas",
        editable=False,
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asignación funcional documentada"
        verbose_name_plural = "Asignaciones funcionales documentadas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hasta__isnull=True)
                | models.Q(hasta__gte=models.F("desde")),
                name="gobernanza_fechas_ordenadas",
            )
        ]

    def clean(self):
        super().clean()
        if not self.acto.strip() or not self.dedicacion.strip():
            raise ValidationError(
                "Registre el acto, su alcance y la dedicación autorizada."
            )
        if (self.rol in ("adscripcion", "centro")) != bool(self.referencia.strip()):
            raise ValidationError(
                "La dependencia y el Centro requieren un ámbito; las funciones institucionales no."
            )
        if self.rol == "adscripcion" and not self.referencia.isdigit():
            raise ValidationError(
                "La dependencia se identifica por su ID institucional."
            )
        if self.hasta and self.desde and self.hasta < self.desde:
            raise ValidationError("La vigencia final debe ser posterior a la inicial.")

    def __str__(self):
        return f"{self.usuario} · {self.get_rol_display()} · {self.referencia or 'institución'}"
