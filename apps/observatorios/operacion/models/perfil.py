from apps.gestion_unidades.models.perfiles_unidad import PerfilOperativoBase


from django.db import models


from apps.directorio_unidades.models.core import Unidad


class PerfilObservatorio(PerfilOperativoBase):
    clasificaciones_permitidas = {"observatorio"}

    NIVEL_ACCESO_CHOICES = [
        ("publico", "Datos públicos"),
        ("mixto", "Datos públicos y restringidos"),
        ("restringido", "Acceso controlado"),
    ]

    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name="perfil_observatorio",
    )
    nivel_acceso_datos = models.CharField(
        max_length=20,
        choices=NIVEL_ACCESO_CHOICES,
        default="mixto",
    )
    gestiona_fuentes = models.BooleanField(default=True)
    gestiona_versiones = models.BooleanField(default=True)
    publica_metodologia = models.BooleanField(default=True)
    ofrece_api = models.BooleanField(default=False)
    ofrece_analisis_solicitud = models.BooleanField(
        "Ofrece análisis bajo solicitud",
        default=True,
    )
    periodicidad_actualizacion = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "webcitt_perfilobservatorio"
        verbose_name = "Perfil operativo de observatorio"
        verbose_name_plural = "Perfiles operativos de observatorios"

    def __str__(self):
        return f"Observatorio: {self.unidad.nombre}"
