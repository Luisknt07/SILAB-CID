"""Los campos describen datos; las operaciones de stock viven en services.py."""

from decimal import Decimal
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


def texto_plano(value):
    if any(ord(char) < 32 for char in value) or "<" in value or ">" in value:
        raise ValidationError(
            "Utilice texto simple, sin etiquetas ni caracteres de control."
        )


class Producto(models.Model):
    codigo = models.CharField(
        max_length=24,
        unique=True,
        validators=[
            RegexValidator(
                r"^[A-Z0-9][A-Z0-9_-]{1,23}$",
                "Use 2 a 24 letras mayúsculas, números, guion o guion bajo.",
            )
        ],
    )
    nombre = models.CharField(max_length=120, validators=[texto_plano])
    unidad = models.CharField(
        max_length=8,
        choices=[("UN", "Unidad"), ("KG", "Kilogramo"), ("LT", "Litro")],
        default="UN",
    )
    minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )
    existencia = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), editable=False
    )

    class Meta:
        ordering = ["codigo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(existencia__gte=0), name="existencia_no_negativa"
            ),
            models.CheckConstraint(
                condition=models.Q(minimo__gte=0), name="minimo_no_negativo"
            ),
        ]

    def clean(self):
        self.codigo = self.codigo.strip().upper()
        self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "Indique un nombre."})

    @property
    def bajo_minimo(self):
        return self.existencia < self.minimo

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Movimiento(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="movimientos"
    )
    tipo = models.CharField(max_length=1, choices=[("E", "Entrada"), ("S", "Salida")])
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    motivo = models.CharField(max_length=160, validators=[texto_plano])
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    fecha = models.DateTimeField(auto_now_add=True)
    clave = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="cantidad_positiva"
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad} de {self.producto.codigo}"
