"""Referencias editables para nuevas propuestas, sin alterar planes conservados."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


TIPOS = [('laboratorios', 'Laboratorio'), ('plantas_piloto', 'Planta piloto'),
         ('centro_experimental', 'Centro experimental'), ('observatorios', 'Observatorio')]
INDICADORES = [('PRACTICAS', 'Prácticas ejecutadas'), ('PRACTICAS-PLAN', 'Prácticas planificadas'),
    ('GUIAS', 'Guías vigentes'), ('INVENTARIO', 'Revisiones de inventario'),
    ('CAPACITACION', 'Capacitaciones del personal'), ('DIFUSION', 'Acciones de difusión'),
    ('PRODUCCION', 'Lotes o procesos'), ('ENSAYOS', 'Ciclos experimentales con seguimiento'),
    ('BOLETINES', 'Publicaciones del observatorio'), ('DATOS-ACTUALIZADOS', 'Series actualizadas'),
    ('EVENTOS', 'Socializaciones'), ('MANTENIMIENTO', 'Cobertura de mantenimiento crítico (%)'),
    ('PRACTICAS-SEMANA', 'Prácticas por semana y asignatura'),
    ('PRACTICAS-MINUTOS', 'Minutos previstos por práctica')]


class ReferenciaIndicadorUnidad(models.Model):
    tipo_unidad = models.CharField('Tipo de unidad', max_length=24, choices=TIPOS)
    codigo = models.CharField('Indicador', max_length=24, choices=INDICADORES)
    nivel_capacidad = models.CharField('Alcance de la referencia', max_length=12, blank=True, default='',
        choices=[('', 'Referencia base del plan'), ('inicial', 'Propuesta: capacidad inicial'),
                 ('limitada', 'Propuesta: capacidad limitada'), ('consolidada', 'Propuesta: capacidad consolidada')],
        help_text='Los niveles de capacidad sólo se usan para proponer cantidades de prácticas.')
    valor = models.PositiveSmallIntegerField('Valor de referencia', validators=[MinValueValidator(1), MaxValueValidator(10000)])
    fundamento = models.TextField('Fundamento de la referencia',
        help_text='Explica la programación, capacidad o decisión institucional que sustenta esta cantidad. No basta el número.')
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')

    class Meta:
        verbose_name = 'Referencia de indicadores por tipo de unidad'
        verbose_name_plural = 'Referencias de indicadores por tipo de unidad'
        ordering = ['tipo_unidad', 'codigo', 'nivel_capacidad']
        constraints = [models.UniqueConstraint(fields=['tipo_unidad', 'codigo', 'nivel_capacidad'],
            name='referencia_indicador_tipo_nivel_unico'),
            models.CheckConstraint(condition=models.Q(valor__gte=1, valor__lte=10000), name='referencia_indicador_rango')]

    def clean(self):
        super().clean()
        if not str(self.fundamento or '').strip():
            raise ValidationError({'fundamento': 'Explica el fundamento antes de cambiar la referencia.'})
        if self.nivel_capacidad and self.codigo not in ('PRACTICAS', 'PRACTICAS-PLAN'):
            raise ValidationError({'nivel_capacidad': 'El nivel de capacidad sólo corresponde a prácticas.'})
        if self.codigo == 'MANTENIMIENTO' and self.valor > 100:
            raise ValidationError({'valor': 'La cobertura debe estar entre 1 y 100 %.'})

    def __str__(self):
        return f'{self.get_tipo_unidad_display()} · {self.get_codigo_display()} · {self.valor}'
