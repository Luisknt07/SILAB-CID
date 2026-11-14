from django.core.exceptions import ValidationError


from django.db import models


class PerfilOperativoBase(models.Model):
    """Campos comunes de la configuración especializada de una unidad."""

    activo = models.BooleanField(default=True)
    descripcion_operativa = models.TextField(
        "Descripción operativa",
        blank=True,
        help_text="Alcance, condiciones y forma de operación de esta capacidad.",
    )
    requisitos_acceso = models.TextField(
        "Requisitos de acceso",
        blank=True,
        help_text="Formación, documentos, permisos o condiciones previas.",
    )
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    clasificaciones_permitidas = set()

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if (
            self.unidad_id
            and self.unidad.clasificacion_funcional
            not in self.clasificaciones_permitidas
        ):
            permitidas = ", ".join(sorted(self.clasificaciones_permitidas))
            raise ValidationError(
                {
                    "unidad": (
                        "Este perfil no corresponde a la clasificación funcional de "
                        f"la unidad. Clasificaciones permitidas: {permitidas}."
                    ),
                }
            )
