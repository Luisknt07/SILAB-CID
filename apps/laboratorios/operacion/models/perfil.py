from apps.gestion_unidades.models.perfiles_unidad import PerfilOperativoBase


from django.db import models


from apps.directorio_unidades.models.core import Unidad


class PerfilLaboratorio(PerfilOperativoBase):
    clasificaciones_permitidas = {
        "laboratorio_academico",
        "laboratorio_id",
        "laboratorio_mixto",
    }

    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name="perfil_laboratorio",
    )
    gestiona_practicas = models.BooleanField(default=True)
    gestiona_muestras = models.BooleanField(default=False)
    requiere_protocolo = models.BooleanField(default=False)
    requiere_supervision = models.BooleanField(default=True)
    acreditacion_referencia = models.CharField(
        "Acreditación o norma de referencia",
        max_length=180,
        blank=True,
    )

    class Meta:
        db_table = "webcitt_perfillaboratorio"
        verbose_name = "Perfil operativo de laboratorio"
        verbose_name_plural = "Perfiles operativos de laboratorios"

    def __str__(self):
        return f"Laboratorio: {self.unidad.nombre}"


class PerfilPlataformaTecnologica(PerfilOperativoBase):
    clasificaciones_permitidas = {"plataforma_tecnologica"}

    unidad = models.OneToOneField(
        Unidad,
        on_delete=models.CASCADE,
        related_name="perfil_plataforma_tecnologica",
    )
    permite_recursos_combinados = models.BooleanField(default=True)
    acepta_archivos_tecnicos = models.BooleanField(default=True)
    gestiona_cotizaciones = models.BooleanField(default=True)
    gestiona_ordenes_servicio = models.BooleanField(default=True)
    ofrece_asesoria = models.BooleanField(default=True)

    class Meta:
        db_table = "webcitt_perfilplataformatecnologica"
        verbose_name = "Perfil operativo de plataforma tecnológica"
        verbose_name_plural = "Perfiles operativos de plataformas tecnológicas"

    def __str__(self):
        return f"Plataforma tecnológica: {self.unidad.nombre}"
