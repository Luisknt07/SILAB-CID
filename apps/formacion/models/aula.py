"""El aula: ejercicios sobre los simuladores, uno por estudiante, con nota.

Un ejercicio toma un proceso real y uno de los tres simuladores de la unidad,
y le da a cada estudiante su propia escala: nadie resuelve el mismo número que
su compañero. Las preguntas se corrigen contra el mismo motor que la planta usa
para producir, con la tolerancia que el docente fije, de modo que la nota sale
de la ingeniería y no de una respuesta guardada a mano.

Aquí vive también la simulación que alguien guarda por su cuenta, sin que se la
manden: la ensaya, le pone nombre y vuelve a ella para cambiarla, borrarla o
descargarla.
"""

from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.asignaturas import TemaAsignatura
from apps.plantas_piloto.operacion.models.produccion import FamiliaProducto, Receta
from apps.reservas.models.reservas import Reserva

SIMULADORES_EJERCICIO = [
    ('balance', 'Balance de materia y energía'),
    ('linea', 'Balance de línea'),
    ('materiales', 'Requerimiento de materiales'),
]


class EjercicioAula(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('abierto', 'Abierto'),
        ('cerrado', 'Cerrado'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='ejercicios_aula')
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    nombre = models.CharField(max_length=160)
    simulador = models.CharField(max_length=20, choices=SIMULADORES_EJERCICIO, default='balance', db_index=True)
    receta = models.ForeignKey(Receta, on_delete=models.PROTECT, related_name='ejercicios')
    reserva = models.ForeignKey(
        Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='ejercicios_aula',
        help_text='La sesión cuyos participantes reciben el ejercicio.',
    )
    tema = models.ForeignKey(
        TemaAsignatura, on_delete=models.SET_NULL, null=True, blank=True, related_name='ejercicios_aula',
    )
    consigna = models.TextField(help_text='Qué tiene que hacer el estudiante y con qué criterio se lo califica.')
    factor_base = models.DecimalField(
        max_digits=8, decimal_places=3, default=Decimal('1'), validators=[MinValueValidator(Decimal('0.001'))],
        help_text='La escala del primer estudiante, en corridas base de la receta.',
    )
    paso = models.DecimalField(
        max_digits=8, decimal_places=3, default=Decimal('0.5'), validators=[MinValueValidator(Decimal('0'))],
        help_text='Cuánto crece la escala de un estudiante al siguiente; cero da a todos la misma.',
    )
    parametros = models.JSONField(
        default=dict, blank=True,
        help_text='Los datos del simulador que son iguales para todos: temperaturas, jornada, corridas.',
    )
    tolerancia_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('2'),
        help_text='Cuánto puede apartarse la respuesta del valor del motor y seguir siendo correcta.',
    )
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10'))
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador', db_index=True)
    fecha_limite = models.DateField(null=True, blank=True)
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ejercicios_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_ejercicioaula'
        ordering = ('-creado_en', '-pk')
        verbose_name = 'Ejercicio del aula'
        verbose_name_plural = 'Ejercicios del aula'

    def __str__(self):
        return f'{self.codigo or self.pk} · {self.nombre}'

    @property
    def abierto(self):
        return self.estado == 'abierto'

    @property
    def vencido(self):
        return bool(self.fecha_limite and self.fecha_limite < timezone.localdate())

    def clean(self):
        super().clean()
        errores = {}
        if self.unidad_id and self.receta_id and self.receta.unidad_id != self.unidad_id:
            errores['receta'] = 'El proceso es de otra unidad.'
        if self.reserva_id and self.unidad_id and self.reserva.laboratorio_id != self.unidad_id:
            errores['reserva'] = 'La sesión es de otra unidad.'
        if self.tolerancia_pct is not None and not (Decimal('0') <= self.tolerancia_pct <= Decimal('50')):
            errores['tolerancia_pct'] = 'La tolerancia va de 0 a 50 por ciento.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'EJ{self.unidad_id:03d}-{self.pk:06d}'
            super().save(update_fields=['codigo'])

    def factor_para(self, indice):
        """La escala del estudiante que ocupa ese lugar en la lista."""
        return (Decimal(self.factor_base) + Decimal(self.paso) * indice).quantize(Decimal('0.001'))


class IntentoEjercicio(models.Model):
    ESTADOS = [
        ('asignado', 'Asignado'),
        ('entregado', 'Entregado'),
        ('calificado', 'Calificado'),
    ]

    ejercicio = models.ForeignKey(EjercicioAula, on_delete=models.CASCADE, related_name='intentos')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intentos_ejercicio')
    factor = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal('1'))
    respuestas = models.JSONField(default=dict, blank=True)
    resultados = models.JSONField(default=list, blank=True)
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='asignado', db_index=True)
    entregado_en = models.DateTimeField(null=True, blank=True)
    calificado_en = models.DateTimeField(null=True, blank=True)
    comentario = models.TextField(blank=True, help_text='Lo que el docente le dice al estudiante.')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_intentoejercicio'
        unique_together = ('ejercicio', 'estudiante')
        ordering = ('ejercicio', 'estudiante__last_name', 'estudiante__username', 'pk')
        verbose_name = 'Intento de un ejercicio'
        verbose_name_plural = 'Intentos de los ejercicios'

    def __str__(self):
        return f'{self.ejercicio.codigo} · {self.estudiante.get_full_name() or self.estudiante.username}'

    @property
    def aciertos(self):
        return sum(1 for fila in self.resultados if fila.get('correcta'))

    @property
    def preguntas_totales(self):
        return len(self.resultados)

    @property
    def fuera_de_plazo(self):
        return bool(
            self.ejercicio.fecha_limite
            and self.entregado_en
            and timezone.localtime(self.entregado_en).date() > self.ejercicio.fecha_limite
        )


class SimulacionGuardada(models.Model):
    """Una simulación que alguien guardó para volver a ella, cambiarla o bajarla.

    No guarda resultados calculados sino las variables con que se corrió: la
    receta, la escala y los datos que el autor movió. Al abrirla se vuelve a
    calcular con el motor de la planta, así que una simulación de marzo abierta
    en junio muestra el proceso como está hoy y no una foto vieja. Lo que sí se
    guarda aparte es el resumen: cuatro cifras para reconocerla en la lista sin
    recalcular quince simulaciones para pintar una tabla.
    """

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='simulaciones_guardadas')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='simulaciones_guardadas')
    simulador = models.CharField(max_length=20, choices=SIMULADORES_EJERCICIO, db_index=True)
    receta = models.ForeignKey(
        Receta, on_delete=models.CASCADE, null=True, blank=True, related_name='simulaciones_guardadas',
        help_text='El proceso simulado. El requerimiento de materiales puede abarcar varios.',
    )
    familia = models.ForeignKey(
        FamiliaProducto,
        on_delete=models.PROTECT,
        related_name='simulaciones_guardadas',
        null=True,
        blank=True,
        help_text='Familia del proceso simulado; permite ordenar simulaciones sin leer sus parámetros.',
    )
    nombre = models.CharField(max_length=120)
    notas = models.TextField(blank=True, help_text='Para qué se hizo esta simulación y qué se concluyó.')
    parametros = models.JSONField(default=dict, blank=True, help_text='Lo que reproduce la simulación: escala y datos movidos.')
    resumen = models.JSONField(default=list, blank=True, help_text='Las cifras con que se reconoce en la lista.')
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_simulacionguardada'
        ordering = ('-actualizada_en', '-pk')
        verbose_name = 'Simulación guardada'
        verbose_name_plural = 'Simulaciones guardadas'
        indexes = [models.Index(fields=['autor', 'unidad', 'simulador'])]

    def __str__(self):
        return f'{self.nombre} · {self.get_simulador_display()}'

    def clean(self):
        if not (self.nombre or '').strip():
            raise ValidationError({'nombre': 'Ponle un nombre para reconocerla después.'})
        if self.receta_id and self.receta.unidad_id != self.unidad_id:
            raise ValidationError({'receta': 'El proceso pertenece a otra unidad.'})
        if self.familia_id and self.unidad_id and self.familia.unidad_id != self.unidad_id:
            raise ValidationError({'familia': 'La familia pertenece a otra planta.'})
        if self.receta_id and self.familia_id and self.receta.familia_id not in (None, self.familia_id):
            raise ValidationError({'familia': 'La familia debe coincidir con la del proceso simulado.'})

    @property
    def consulta(self):
        """Los parámetros como cadena de consulta, para reabrir el simulador."""
        return urlencode({clave: valor for clave, valor in (self.parametros or {}).items() if valor != ''})
