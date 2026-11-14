"""Sesiones versionadas: separadas de los parámetros de las plantas piloto.

El estado es privado y calculado en servidor. Los eventos permiten reconstruir
las decisiones sin reinterpretar una partida antigua con un motor nuevo.
"""

import secrets
import uuid

from django.conf import settings
from django.db import models


def codigo_partida():
    return secrets.token_hex(6).upper()


class PartidaSimulador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unidad = models.ForeignKey(
        'directorio_unidades.Unidad', on_delete=models.PROTECT, related_name="partidas_simulador"
    )
    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partidas_simulador",
    )
    simulador = models.CharField(
        max_length=24,
        choices=[
            ("cerveza", "Cadena de suministro"),
            ("operaciones", "Operaciones 3D"),
        ],
    )
    caso = models.CharField(max_length=64)
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(
        max_length=12, unique=True, default=codigo_partida, editable=False
    )
    version_motor = models.CharField(max_length=24)
    version_caso = models.CharField(max_length=24, default="1.0.0")
    semilla = models.PositiveIntegerField(default=42)
    fase = models.CharField(
        max_length=12,
        default="sala",
        choices=[
            ("sala", "Sala"),
            ("activa", "Activa"),
            ("terminada", "Terminada"),
            ("cerrada", "Archivada"),
        ],
    )
    revision = models.PositiveIntegerField(default=0)
    estado = models.JSONField(default=dict, editable=False)
    observaciones = models.JSONField(
        default=dict,
        editable=False,
        help_text="Vistas por rol calculadas por el motor de esta versión; permiten consultar partidas históricas.",
    )
    resultado = models.JSONField(default=dict, editable=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_partidasimulador'
        ordering = ("-actualizada_en", "-pk")
        indexes = [
            models.Index(
                fields=["propietario", "unidad", "-actualizada_en"],
                name="partida_autor_unidad_fecha",
            ),
            models.Index(
                fields=["unidad", "simulador", "fase"], name="partida_unidad_motor_fase"
            ),
        ]
        verbose_name = "Partida de simulador"
        verbose_name_plural = "Partidas de simuladores"

    def __str__(self):
        return self.nombre


class ParticipantePartida(models.Model):
    partida = models.ForeignKey(
        PartidaSimulador, on_delete=models.CASCADE, related_name="participantes"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="participaciones_simulador",
    )
    rol = models.CharField(max_length=16)
    pedido = models.PositiveIntegerField(null=True, blank=True, editable=False)
    unido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_participantepartida'
        constraints = [
            models.UniqueConstraint(
                fields=["partida", "rol"], name="partida_rol_unico"
            ),
            models.UniqueConstraint(
                fields=["partida", "usuario"], name="partida_usuario_unico"
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "partida"], name="partida_usuario_acceso")
        ]
        verbose_name = "Participante de partida"


class EventoPartida(models.Model):
    partida = models.ForeignKey(
        PartidaSimulador, on_delete=models.CASCADE, related_name="eventos"
    )
    revision = models.PositiveIntegerField()
    tipo = models.CharField(max_length=24)
    datos = models.JSONField(default=dict, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_eventopartida'
        ordering = ("revision",)
        constraints = [
            models.UniqueConstraint(
                fields=["partida", "revision"], name="partida_evento_revision_unica"
            )
        ]
        verbose_name = "Evento de partida"
