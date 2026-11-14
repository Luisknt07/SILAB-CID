"""Las sesiones del ERP de una planta: dónde ocurre cada operación.

La producción real no lleva sesión: es la única que mueve el inventario, las
finanzas, los indicadores y los reportes. Cada práctica trabaja en su sesión,
con sus planes, pedidos, órdenes y lotes, que no se ven desde otra ni cuentan
como reales. Las existencias de una sesión parten de una foto del inventario al
abrirla y cambian con lo que se recibe y se consume dentro de ella.
"""
import secrets

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible
from apps.directorio_unidades.models.core import Unidad

# Sin letras ni cifras que se confundan al dictarlas en clase (0/O, 1/I/L).
ALFABETO_CLAVE = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def _clave_nueva():
    return ''.join(secrets.choice(ALFABETO_CLAVE) for _ in range(6))


class SesionERP(models.Model):
    TIPOS = [
        ('practica', 'Sesión de práctica'),
        ('individual', 'Sesión individual'),
        ('demostrativa', 'Sesión demostrativa'),
    ]
    ESTADOS = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='sesiones_erp')
    codigo = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    nombre = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='practica', db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierta', db_index=True)
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sesiones_erp_a_cargo',
        help_text='El docente de la práctica o el estudiante de su sesión individual.',
    )
    miembros = models.ManyToManyField(User, db_table='webcitt_sesionerp_miembros', blank=True, related_name='sesiones_erp')
    reserva = models.ForeignKey(
        'reservas.Reserva', on_delete=models.SET_NULL, null=True, blank=True, related_name='sesiones_erp',
        help_text='La práctica aprobada que la originó, si la hay.',
    )
    clave_acceso = models.CharField(
        'Clave para unirse', max_length=6, unique=True, default=_clave_nueva, editable=False,
        help_text='La dicta el docente: con ella los estudiantes entran a la sesión.',
    )
    observaciones = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    cerrada_en = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        db_table = 'webcitt_sesionerp'
        ordering = ('-creada_en', '-pk')
        verbose_name = 'Sesión del ERP'
        verbose_name_plural = 'Sesiones del ERP'

    def __str__(self):
        return f'{self.codigo or self.pk} · {self.nombre}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f'SE{self.unidad_id:03d}-{self.pk:05d}'
            super().save(update_fields=['codigo'])

    @property
    def abierta(self):
        return self.estado == 'abierta'

    def participa(self, usuario):
        return bool(usuario and usuario.is_authenticated) and (
            usuario.pk == self.responsable_id or self.miembros.filter(pk=usuario.pk).exists()
        )

    def tomar_foto_del_inventario(self):
        """Las existencias de la sesión parten de las reales al abrirla."""
        self.existencias.all().delete()
        ExistenciaSesion.objects.bulk_create([
            ExistenciaSesion(sesion=self, consumible=consumible, cantidad=consumible.stock_total or 0)
            for consumible in Consumible.objects.filter(unidad=self.unidad, activo=True)
        ])

    @classmethod
    def demostrativa_de(cls, unidad):
        """La sesión donde viven las corridas de ejemplo de la planta: una sola por planta."""
        sesion, _ = cls.objects.get_or_create(
            unidad=unidad, tipo='demostrativa', defaults={'nombre': 'Corridas demostrativas'},
        )
        return sesion

    def cerrar(self):
        self.estado = 'cerrada'
        self.cerrada_en = timezone.now()
        self.save(update_fields=['estado', 'cerrada_en'])


class ExistenciaSesion(models.Model):
    """Lo que hay de cada insumo dentro de una sesión: el inventario real no se toca."""

    sesion = models.ForeignKey(SesionERP, on_delete=models.CASCADE, related_name='existencias')
    consumible = models.ForeignKey(Consumible, on_delete=models.CASCADE, related_name='existencias_sesion')
    cantidad = models.DecimalField(max_digits=14, decimal_places=3, default=0, validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'webcitt_existenciasesion'
        ordering = ('consumible__nombre',)
        verbose_name = 'Existencia en una sesión'
        verbose_name_plural = 'Existencias en las sesiones'
        constraints = [
            models.UniqueConstraint(fields=('sesion', 'consumible'), name='existencia_unica_por_sesion'),
        ]

    def __str__(self):
        return f'{self.sesion.codigo} · {self.consumible.nombre}: {self.cantidad}'
