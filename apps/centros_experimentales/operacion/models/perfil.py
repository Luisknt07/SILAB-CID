from apps.gestion_unidades.models.perfiles_unidad import PerfilOperativoBase


from django.db import models


from apps.directorio_unidades.models.core import Unidad


class PerfilCentroExperimental(PerfilOperativoBase):
    clasificaciones_permitidas = {"centro_experimental"}

    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name="perfil_centro_experimental",
    )
    gestiona_areas_georreferenciadas = models.BooleanField(default=True)
    gestiona_ciclos = models.BooleanField(default=True)
    requiere_material_biologico = models.BooleanField(default=False)
    requiere_protocolo_campo = models.BooleanField(default=True)
    requiere_bioseguridad = models.BooleanField(default=True)
    variables_ambientales = models.TextField(
        blank=True,
        help_text="Variables climáticas, productivas o ambientales registradas.",
    )

    class Meta:
        db_table = "webcitt_perfilcentroexperimental"
        verbose_name = "Perfil operativo de centro experimental"
        verbose_name_plural = "Perfiles operativos de centros experimentales"

    def __str__(self):
        return f"Centro experimental: {self.unidad.nombre}"
