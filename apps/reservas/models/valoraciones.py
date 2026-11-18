"""Valoración de la atención: una por reserva atendida, registrada por quien la solicitó.

No guarda al autor aparte: es el solicitante de la reserva. La consulta de gestión
presenta promedios y comentarios sin ese vínculo.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.reservas.models.reservas import Reserva

ESCALA = (MinValueValidator(1), MaxValueValidator(5))
# Reserva que la unidad cerró como atendida: la única que se valora y la base de la tasa de respuesta.
RESERVA_ATENDIDA = {'estado': 'completada', 'resultado_cierre': 'atendida'}


def _en_escala(campo, *, opcional=False):
    condicion = models.Q(**{f'{campo}__gte': 1, f'{campo}__lte': 5})
    return condicion | models.Q(**{f'{campo}__isnull': True}) if opcional else condicion


class ValoracionReserva(models.Model):
    # Aspectos opcionales, en el orden en que se preguntan y se informan.
    ASPECTOS = (
        ('atencion_personal', 'Atención del personal'),
        ('estado_equipos', 'Estado de los equipos'),
        ('instalaciones', 'Instalaciones'),
    )

    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='valoracion')
    general = models.PositiveSmallIntegerField('Valoración general', validators=ESCALA)
    atencion_personal = models.PositiveSmallIntegerField(
        'Atención del personal', null=True, blank=True, validators=ESCALA)
    estado_equipos = models.PositiveSmallIntegerField(
        'Estado de los equipos', null=True, blank=True, validators=ESCALA)
    instalaciones = models.PositiveSmallIntegerField(
        'Instalaciones', null=True, blank=True, validators=ESCALA)
    comentario = models.CharField(max_length=500, blank=True)
    registrada_en = models.DateTimeField('Fecha de registro', auto_now_add=True)

    class Meta:
        ordering = ('-registrada_en', '-pk')
        verbose_name = 'Valoración de la atención'
        verbose_name_plural = 'Valoraciones de la atención'
        constraints = [
            models.CheckConstraint(
                condition=(_en_escala('general') & _en_escala('atencion_personal', opcional=True)
                           & _en_escala('estado_equipos', opcional=True)
                           & _en_escala('instalaciones', opcional=True)),
                name='valoracion_reserva_escala_1_a_5'),
        ]

    def __str__(self):
        return f'Valoración {self.general}/5 · reserva {self.reserva_id}'
