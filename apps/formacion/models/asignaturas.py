"""Asignaturas y sus temas: el sílabo práctico que se programa en la unidad.

Una asignatura del período tiene temas por semana; cada tema puede apuntar
a un proceso de la unidad y a los simuladores o software que se usarán. Al
programar el período, el cronograma de la guía general y las guías por
sesión nacen de estos temas. Sirve igual para una planta y un laboratorio.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad


class Asignatura(models.Model):
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='asignaturas')
    periodo = models.ForeignKey(
        'core.PeriodoAcademico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaturas',
        help_text='El período en que se dicta; vacío cuando sirve a cualquier período.',
    )
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=180)
    carrera = models.CharField(max_length=180, blank=True)
    semestre = models.CharField(max_length=60, blank=True)
    docente = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaturas_dictadas',
        help_text='Quien la dicta; vacío es cualquier docente que la elija al programar.',
    )
    estudiantes = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_asignatura'
        ordering = ('nombre', 'pk')
        constraints = [
            models.UniqueConstraint(fields=('unidad', 'codigo'), name='asignatura_unica_por_unidad'),
        ]
        verbose_name = 'Asignatura'
        verbose_name_plural = 'Asignaturas'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def temas_ordenados(self):
        return list(self.temas.select_related('receta').prefetch_related('software').order_by('orden', 'pk'))


class TemaAsignatura(models.Model):
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='temas')
    orden = models.PositiveSmallIntegerField(default=1, help_text='La semana o el orden en que se dicta.')
    nombre = models.CharField(max_length=240)
    receta = models.ForeignKey(
        'plantas_operacion.Receta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temas_asignatura',
        help_text='El proceso de la unidad que se practica en este tema.',
    )
    software = models.ManyToManyField(
        SoftwareDisponible, db_table='webcitt_temaasignatura_software',
        blank=True,
        related_name='temas_asignatura',
        help_text='Simuladores y software del aula que se usan en el tema.',
    )
    ejercicios = models.TextField(blank=True, help_text='Ejercicios del aula previstos para el tema.')
    resultado_aprendizaje = models.TextField(blank=True)

    class Meta:
        db_table = 'webcitt_temaasignatura'
        ordering = ('asignatura', 'orden', 'pk')
        constraints = [
            models.UniqueConstraint(fields=('asignatura', 'orden'), name='tema_unico_por_orden'),
        ]
        verbose_name = 'Tema de asignatura'
        verbose_name_plural = 'Temas de asignatura'

    def __str__(self):
        return f'{self.orden}. {self.nombre}'

    def clean(self):
        super().clean()
        if self.receta_id and self.asignatura_id and self.receta.unidad_id != self.asignatura.unidad_id:
            raise ValidationError({'receta': 'El proceso debe pertenecer a la unidad de la asignatura.'})
