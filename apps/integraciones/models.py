"""Seguimiento común: referencias y constancias, sin copiar los dominios de origen."""

from django.conf import settings
from django.db import models


class ConsolidadoSeguimiento(models.Model):
    AMBITOS = [
        ("dependencia", "Dependencia de adscripción"),
        ("centro", "Centro de Investigación y Desarrollo"),
    ]
    ambito = models.CharField(max_length=15, choices=AMBITOS)
    referencia = models.CharField(max_length=160)
    inicio = models.DateField()
    fin = models.DateField()
    version = models.PositiveIntegerField(default=1)
    fuentes = models.JSONField()
    sha256 = models.CharField(max_length=64)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="consolidados_validados",
    )
    validado_en = models.DateTimeField(null=True)
    estado = models.CharField(
        max_length=15,
        default="preparado",
        choices=[
            ("preparado", "Preparado"),
            ("validado", "Validado por adscripción"),
            ("observado", "Observado institucionalmente"),
            ("revisado", "Revisado institucionalmente"),
        ],
    )

    class Meta:
        ordering = ("-fin", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("ambito", "referencia", "inicio", "fin", "version"),
                name="consolidado_version_unica",
            ),
            models.CheckConstraint(
                condition=models.Q(fin__gte=models.F("inicio")),
                name="consolidado_periodo_ordenado",
            ),
        ]


class EvidenciaSeguimiento(models.Model):
    """Cada corrección agrega una versión; el archivo conserva su repositorio de origen."""

    centro = models.SlugField(max_length=160)
    codigo = models.SlugField(max_length=100)
    inicio = models.DateField()
    fin = models.DateField()
    version = models.PositiveIntegerField()
    titulo = models.CharField(max_length=240)
    fuente = models.URLField(max_length=1000)
    huella_archivo = models.CharField(max_length=64, blank=True)
    documento_centro_id = models.PositiveBigIntegerField(null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("centro", "codigo", "inicio", "fin", "version"),
                name="evidencia_centro_version_unica",
            )
        ]


class EventoSeguimiento(models.Model):
    consolidado = models.ForeignKey(
        ConsolidadoSeguimiento, on_delete=models.PROTECT, related_name="eventos"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    accion = models.CharField(max_length=30)
    observacion = models.TextField(blank=True)
    sha256 = models.CharField(max_length=64)
    creado_en = models.DateTimeField(auto_now_add=True)


class CompromisoSeguimiento(models.Model):
    consolidado = models.ForeignKey(
        ConsolidadoSeguimiento, on_delete=models.PROTECT, related_name="compromisos"
    )
    descripcion = models.TextField()
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    plazo = models.DateField()
    abierto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    evidencia = models.URLField(max_length=1000, blank=True)
    respuesta = models.TextField(blank=True)
    estado = models.CharField(
        max_length=15,
        default="abierto",
        choices=[
            ("abierto", "Abierto"),
            ("respondido", "Respondido"),
            ("verificado", "Cumplimiento verificado"),
        ],
    )
    verificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    verificado_en = models.DateTimeField(null=True)


class ReferenciaOficialInvestigacion(models.Model):
    centro = models.SlugField(max_length=160)
    tipo = models.CharField(
        max_length=12, choices=[("proyecto", "Proyecto"), ("resultado", "Resultado")]
    )
    objeto_id = models.PositiveBigIntegerField()
    sistema = models.CharField(max_length=150)
    identificador = models.CharField(max_length=200)
    fuente = models.URLField(max_length=1000)
    estado_oficial = models.CharField(max_length=120)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    registrado_en = models.DateTimeField(auto_now_add=True)
    verificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    verificado_en = models.DateTimeField(null=True)


class IdentidadActivoCompartido(models.Model):
    """Un código patrimonial, una agenda operativa de origen; otros usos son vínculos."""

    codigo_institucional = models.CharField(max_length=80, unique=True)
    origen = models.CharField(
        max_length=12,
        choices=[
            ("directorio", "Inventario de laboratorio"),
            ("centro", "Inventario de Centro"),
        ],
    )
    objeto_id = models.PositiveBigIntegerField()
    fuente = models.URLField(max_length=1000)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("origen", "objeto_id"), name="activo_origen_unico"
            )
        ]
