from apps.directorio_unidades.models.core import Unidad


from django.db import models


from django.templatetags.static import static
from apps.recursos.models.medios import medios_publicos, validar_medios_referencia


class SoftwareDisponible(models.Model):
    """Software disponible en un laboratorio específico"""

    TIPO_RECURSO_CHOICES = [
        ("software", "Software instalado o de libre acceso"),
        ("licencia", "Licencia institucional"),
    ]
    TIPO_ACCESO_CHOICES = [
        ("instalacion", "Instalado en equipos del laboratorio"),
        ("licencia", "Licencia individual temporal"),
        ("red", "Licencia concurrente o de red"),
        ("remoto", "Acceso remoto"),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name="software_disponible",
        help_text="Laboratorio al que pertenece este software",
    )
    nombre = models.CharField(
        max_length=100, help_text="Nombre del software (ej: AutoCAD, MATLAB)"
    )
    codigo = models.CharField(
        max_length=40,
        blank=True,
        help_text="Código interno de la licencia o recurso de software.",
    )
    version = models.CharField(
        max_length=50, blank=True, help_text="Versión del software (ej: 2024, R2023a)"
    )
    logo = models.ImageField(
        upload_to="software/logos/",
        blank=True,
        null=True,
        help_text=(
            "Logo o icono visible en el catálogo de reservas. Se recomienda una "
            "imagen cuadrada con fondo transparente."
        ),
    )
    logo_catalogo = models.CharField(
        "Logo de catálogo",
        max_length=255,
        blank=True,
        help_text="Ruta estática del ícono oficial del programa, cuando la unidad no subió su logo.",
    )
    sitio_web = models.URLField(
        "Sitio oficial",
        max_length=500,
        blank=True,
        help_text="Página oficial del programa o de su documentación.",
    )
    medios_referencia = models.JSONField(
        default=dict, blank=True, validators=[validar_medios_referencia],
        help_text='Fuentes, créditos, guías y videos del producto identificado; no acredita instalaciones ni licencias.',
    )
    descripcion = models.TextField(
        blank=True, help_text="Descripción del software y su uso"
    )
    tipo_recurso = models.CharField(
        max_length=20,
        choices=TIPO_RECURSO_CHOICES,
        default="software",
        help_text="Diferencia el programa disponible de una licencia institucional limitada.",
    )
    tipo_acceso = models.CharField(
        max_length=20,
        choices=TIPO_ACCESO_CHOICES,
        default="instalacion",
    )
    equipos_instalados = models.ManyToManyField(
        "recursos.UnidadEquipo",
        db_table="webcitt_softwaredisponible_equipos_instalados",
        blank=True,
        related_name="software_instalado",
        limit_choices_to={"activa": True},
        help_text=(
            "Equipos físicos de esta unidad donde está instalado o habilitado el "
            "software. Para acceso por instalación debe seleccionarse al menos uno."
        ),
    )
    USO_EN_EQUIPO_CHOICES = (
        ("opcional", "Opcional: la persona elige si lo usa"),
        ("obligatorio", "Propio del equipo: se usa siempre que se reserva el equipo"),
    )
    uso_en_equipo = models.CharField(
        max_length=12,
        choices=USO_EN_EQUIPO_CHOICES,
        default="opcional",
        help_text=(
            "Propio del equipo: el programa con el que opera el equipo (por "
            "ejemplo, el laminador de una impresora 3D); al reservar el equipo "
            "queda incluido y no puede desmarcarse. Opcional: uno de los "
            "programas disponibles en un puesto, como una computadora, que la "
            "persona marca solo si lo necesita."
        ),
    )
    licencias_totales = models.PositiveIntegerField(default=1)
    licencias_disponibles = models.PositiveIntegerField(default=1)
    requiere_reserva = models.BooleanField(
        default=True,
        help_text="Permite solicitar esta licencia desde el asistente público.",
    )
    instrucciones_acceso = models.TextField(
        blank=True,
        help_text="Condiciones, ubicación o requisitos para utilizar el software.",
    )
    activo = models.BooleanField(
        default=True, help_text="Si el software está disponible y activo"
    )

    class Meta:
        db_table = "webcitt_softwaredisponible"
        verbose_name = "Software Disponible"
        verbose_name_plural = "Software Disponible"
        unique_together = ("unidad", "nombre")  # Evita duplicados por unidad
        ordering = ["nombre", "version"]

    def clean(self):
        super().clean()
        from apps.recursos.models.adquisiciones import validar_habilitacion
        validar_habilitacion(self)

    def __str__(self):
        version_str = f" {self.version}" if self.version else ""
        return f"{self.nombre}{version_str}"

    @property
    def logo_publico_url(self):
        if self.logo:
            try:
                return self.logo.url
            except ValueError:
                pass
        if self.medios_publicos.get('medios_por_revisar'):
            return static('img/software/software-generico.svg')
        if self.logo_catalogo:
            return static(self.logo_catalogo)
        if self.medios_publicos.get('estado') == 'identidad_pendiente':
            return static('img/software/software-generico.svg')
        name = (self.nombre or "").lower()
        fallbacks = (
            (("autocad",), "img/software/autocad.svg"),
            (("fusion", "autodesk"), "img/software/autodesk-fusion.svg"),
            (("solidworks",), "img/software/solidworks.svg"),
            (("blender",), "img/software/blender.svg"),
            (("cura", "ultimaker"), "img/software/cura.svg"),
            (("meshlab",), "img/software/meshlab.svg"),
        )
        for keywords, asset in fallbacks:
            if any(keyword in name for keyword in keywords):
                return static(asset)
        return static("img/software/software-generico.svg")

    @property
    def medios_publicos(self):
        return medios_publicos(self.medios_referencia)

    @property
    def equipos_instalados_ids_csv(self):
        return ",".join(str(equipo.pk) for equipo in self.equipos_instalados.all())

    @property
    def equipos_instalados_resumen(self):
        return ", ".join(
            f"{equipo.equipo.nombre} · {equipo.codigo_unidad}"
            for equipo in self.equipos_instalados.all()
        )
