from apps.gestion_unidades.models.perfiles_unidad import PerfilOperativoBase


from django.db import models


from apps.directorio_unidades.models.core import Unidad


class PerfilPlantaPiloto(PerfilOperativoBase):
    clasificaciones_permitidas = {"planta_piloto"}

    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name="perfil_planta_piloto",
    )
    gestiona_campanias = models.BooleanField("Gestiona campañas", default=True)
    gestiona_lotes = models.BooleanField(default=True)
    duracion_minima_horas = models.PositiveSmallIntegerField(default=1)
    requiere_receta_proceso = models.BooleanField(default=True)
    requiere_control_calidad = models.BooleanField(default=True)
    requiere_plan_limpieza = models.BooleanField(default=True)
    gestiona_residuos = models.BooleanField(default=True)
    servicios_auxiliares = models.TextField(
        blank=True,
        help_text="Agua, vapor, frío, aire, energía u otras utilidades requeridas.",
    )

    class Meta:
        db_table = "webcitt_perfilplantapiloto"
        verbose_name = "Perfil operativo de planta piloto"
        verbose_name_plural = "Perfiles operativos de plantas piloto"

    def __str__(self):
        return f"Planta piloto: {self.unidad.nombre}"
