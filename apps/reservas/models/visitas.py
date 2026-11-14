"""Visitas a la unidad: un papel en una solicitud, no un cuarto tipo de usuario.

Las visitas internas vinculan al organizador y los asistentes con sus cuentas.
Las externas admiten un responsable sin cuenta con nombre y contacto. La visita es una solicitud con su
propio formulario que se apoya en una reserva de las áreas del recorrido: la
agenda, el aforo, la aprobación, el comprobante y los avisos son los de
siempre. Lo propio de la visita: la institución, el grupo, el recorrido por
las áreas visitables, los guías que exige, la protección del inventario y la
lista de asistencia que se toma en la puerta.
"""

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import Reserva


class SolicitudVisita(models.Model):
    PROPOSITOS = [
        ('academica', 'Académica'),
        ('institucional', 'Institucional'),
        ('comercial', 'Comercial'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='solicitudes_visita')
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='visita')
    responsable = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='visitas_organizadas')
    categoria = models.CharField(max_length=10, choices=[('interna', 'Interna'), ('externa', 'Externa')], default='externa')
    institucion = models.CharField(max_length=180)
    proposito = models.CharField(max_length=20, choices=PROPOSITOS, default='academica')
    personas = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    rango_edades = models.CharField(max_length=60, blank=True)
    descripcion = models.TextField(blank=True)
    recorrido = models.ManyToManyField(EspacioReservable, db_table='webcitt_solicitudvisita_recorrido', related_name='visitas', blank=True)
    guia = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitas_guiadas',
    )
    guias_necesarios = models.PositiveSmallIntegerField(default=1)
    requisitos_aceptados = models.BooleanField(default=False)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_solicitudvisita'
        ordering = ('-pk',)
        verbose_name = 'Solicitud de visita'
        verbose_name_plural = 'Solicitudes de visita'

    def __str__(self):
        return f'Visita de {self.institucion} · {self.reserva.fecha:%d/%m/%Y}'

    @property
    def estado(self):
        return self.reserva.estado

    @property
    def valor_estimado_vigente(self):
        """Mismo importe que el expediente, incluso para copias históricas previas."""
        return self.reserva.costo_estimado

    @property
    def presentes(self):
        return self.asistentes.filter(asistio=True).count()


class AsistenteVisita(models.Model):
    ROLES = [
        ('estudiante', 'Estudiante'), ('docente', 'Profesor'),
        ('administrativo', 'Administrativo'), ('otro', 'Otro'),
    ]
    visita = models.ForeignKey(SolicitudVisita, on_delete=models.CASCADE, related_name='asistentes')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='asistencias_visita')
    nombre = models.CharField(max_length=150)
    documento = models.CharField(max_length=40, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, blank=True, default='')
    telefono = models.CharField('Celular', max_length=30, blank=True, default='')
    correo = models.EmailField(blank=True, default='')
    asistio = models.BooleanField(default=False)
    ingreso_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webcitt_asistentevisita'
        ordering = ('pk',)
        verbose_name = 'Asistente de visita'
        verbose_name_plural = 'Asistentes de visita'

    def __str__(self):
        return self.nombre
