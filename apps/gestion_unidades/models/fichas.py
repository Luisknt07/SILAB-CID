"""Gobierno común de las fichas publicables del núcleo de plantas piloto."""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.directorio_unidades.models.core import Unidad
from apps.plantas_piloto.operacion.models.produccion import FamiliaProducto


class FichaContenido(models.Model):
    """Estado editorial y relaciones de una ficha generada desde un objeto del núcleo."""

    ESTADOS = [
        ('borrador', 'Borrador'),
        ('en_revision', 'En revisión'),
        ('publicada', 'Publicada'),
        ('archivada', 'Archivada'),
    ]
    VISIBILIDADES = [
        ('publica', 'Pública'),
        ('interna', 'Interna'),
        ('restringida', 'Restringida'),
    ]
    ESTADOS_VALIDACION = [
        ('pendiente', 'Pendiente de validación institucional'),
        ('en_revision', 'En validación institucional'),
        ('validada', 'Validada por la institución'),
        ('bloqueada', 'Bloqueada por información faltante'),
    ]
    TIPOS = [
        ('equipo', 'Equipo'),
        ('producto', 'Producto'),
        ('proceso', 'Proceso'),
        ('pcc', 'Punto crítico de control'),
        ('especificacion', 'Especificación'),
        ('guia', 'Guía'),
        ('simulador', 'Simulador'),
        ('documento', 'Documento'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='fichas_contenido')
    familia = models.ForeignKey(
        FamiliaProducto,
        on_delete=models.PROTECT,
        related_name='fichas',
        null=True,
        blank=True,
    )
    codigo = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    titulo = models.CharField(max_length=220)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador', db_index=True)
    version = models.PositiveSmallIntegerField(default=1)
    visibilidad = models.CharField(max_length=20, choices=VISIBILIDADES, default='interna', db_index=True)
    estado_validacion = models.CharField(
        max_length=20,
        choices=ESTADOS_VALIDACION,
        default='pendiente',
        db_index=True,
    )
    observacion_validacion = models.TextField(
        blank=True,
        help_text='Explica el dato o evidencia que falta cuando la ficha queda bloqueada.',
    )
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        editable=False,
    )
    validado_en = models.DateTimeField(null=True, blank=True, editable=False)
    decision_editorial_manual = models.BooleanField(default=False, db_index=True, editable=False)
    decision_editorial_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        editable=False,
    )
    decision_editorial_en = models.DateTimeField(null=True, blank=True, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    objeto = GenericForeignKey('content_type', 'object_id')
    relacionadas = models.ManyToManyField('self', db_table='webcitt_fichacontenido_relacionadas', blank=True, symmetrical=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_fichacontenido'
        ordering = ('unidad', 'tipo', 'codigo')
        verbose_name = 'Ficha de contenido'
        verbose_name_plural = 'Fichas de contenido'
        constraints = [
            models.UniqueConstraint(
                fields=('content_type', 'object_id'),
                condition=models.Q(content_type__isnull=False, object_id__isnull=False),
                name='ficha_unica_por_objeto',
            ),
        ]

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    def clean(self):
        super().clean()
        errores = {}
        if self.familia_id and self.unidad_id and self.familia.unidad_id != self.unidad_id:
            errores['familia'] = 'La familia debe pertenecer a la misma planta.'
        if bool(self.content_type_id) != bool(self.object_id):
            errores['object_id'] = 'El tipo de contenido y el objeto deben declararse juntos.'
        if errores:
            raise ValidationError(errores)

    @property
    def completitud(self):
        """Porcentaje calculado de los metadatos mínimos de publicación."""
        if self.tipo == 'equipo' and self.content_type_id and self.object_id:
            objeto = self.objeto
            if objeto is not None and hasattr(objeto, 'completitud_ficha'):
                return objeto.completitud_ficha
        valores = (self.codigo, self.tipo, self.titulo, self.descripcion, self.estado, self.version, self.visibilidad)
        return round(sum(bool(valor) for valor in valores) * 100 / len(valores))
