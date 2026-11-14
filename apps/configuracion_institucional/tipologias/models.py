"""Tipologias administrables; se desactivan, nunca se eliminan."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.tipologias import (
    CODIGOS_BASE,
    TIPOLOGIAS_BASE,
    Tipologia,
    validar_codigo,
    validar_icono,
    validar_tipologia,
)


def sembrar_bases(modelo):
    """Garantiza una fila por tipologia implementada; idempotente.

    Lo usan la migracion inicial y las pruebas: una base vaciada por un
    TransactionTestCase vuelve a tener las cuatro filas administrables.
    """
    for tipologia in TIPOLOGIAS_BASE:
        modelo.objects.get_or_create(
            codigo=tipologia.codigo,
            defaults={
                'nombre': tipologia.nombre,
                'nombre_plural': tipologia.nombre_plural,
                'nombre_en': tipologia.nombre_en,
                'nombre_plural_en': tipologia.nombre_plural_en,
                'icono': tipologia.icono,
                'orden': tipologia.orden,
                'base': tipologia.base,
                'activa': True,
            },
        )


def validar_codigo_modelo(valor):
    try:
        validar_codigo(valor)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None


def validar_icono_modelo(valor):
    try:
        validar_icono(valor)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None


class TipologiaUnidad(models.Model):
    codigo = models.CharField(
        _('Código'), max_length=50, unique=True, validators=[validar_codigo_modelo],
        help_text=_('Identificador estable en minúsculas; no cambia después de crear la tipología.'),
    )
    nombre = models.CharField(_('Nombre'), max_length=100)
    nombre_plural = models.CharField(_('Nombre en plural'), max_length=100)
    nombre_en = models.CharField(_('Nombre en inglés'), max_length=100, blank=True)
    nombre_plural_en = models.CharField(_('Nombre en plural en inglés'), max_length=100, blank=True)
    descripcion = models.TextField(_('Descripción'), blank=True)
    icono = models.CharField(
        _('Icono'), max_length=60, default='iconsminds-microscope',
        validators=[validar_icono_modelo],
        help_text=_('Clase del icono institucional, por ejemplo iconsminds-microscope.'),
    )
    orden = models.PositiveSmallIntegerField(_('Orden'), default=100)
    base = models.CharField(
        _('Base operativa'), max_length=50, default=CODIGOS_BASE[0],
        choices=tuple((t.codigo, t.nombre_plural) for t in TIPOLOGIAS_BASE),
        help_text=_('Implementación cuyo catálogo, detalle, módulos y reserva reutiliza esta tipología.'),
    )
    activa = models.BooleanField(
        _('Activa'), default=True,
        help_text=_('Una tipología inactiva sale del catálogo público y no se asigna a unidades nuevas; sus unidades conservan datos e historial.'),
    )

    class Meta:
        ordering = ('orden', 'codigo')
        verbose_name = _('Tipología de unidad')
        verbose_name_plural = _('Tipologías de unidad')

    def __str__(self):
        return f'{self.nombre_plural} ({self.codigo})'

    def como_tipologia(self):
        return Tipologia(
            codigo=self.codigo, nombre=self.nombre, nombre_plural=self.nombre_plural,
            base=self.base, icono=self.icono, orden=self.orden, activa=self.activa,
            nombre_en=self.nombre_en, nombre_plural_en=self.nombre_plural_en,
        )

    def clean(self):
        super().clean()
        try:
            validar_tipologia(self.como_tipologia())
        except ValueError as exc:
            raise ValidationError(str(exc)) from None

    def delete(self, *args, **kwargs):
        raise ValidationError(
            _('Una tipología se desactiva; no se elimina, para conservar sus unidades y su historial.')
        )
