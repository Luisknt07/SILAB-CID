"""Ajustes de una unidad sobre las secciones comunes de su ficha: nombre propio o sección oculta.

Las secciones numeradas son la estructura que comparten las unidades de un mismo
tipo (33 en las plantas, 24 en los laboratorios) y su contenido lo arma la
plataforma; cada unidad solo puede renombrarlas u ocultarlas. Las carpetas
propias que se cuelgan de ellas son `CarpetaRecurso`.
"""

from django.db import models

from apps.plantas_piloto.operacion.presentation.secciones_plantas import NUMEROS_DE_SECCION


class AjusteSeccionPlanta(models.Model):
    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='ajustes_seccion')
    # El título depende del mapa de la unidad; aquí solo se guarda el número.
    numero = models.CharField('Sección', max_length=5, choices=[(numero, numero) for numero in NUMEROS_DE_SECCION])
    titulo = models.CharField('Nombre propio', max_length=120, blank=True,
                              help_text='Vacío, conserva el nombre común de la sección.')
    oculta = models.BooleanField('Oculta', default=False,
                                 help_text='No se muestra en la ficha, con sus carpetas propias.')
    grupos = models.JSONField('Subcarpetas automáticas', default=dict, blank=True,
                              help_text='Por subcarpeta automática (cada área en las fichas de equipo, el escáner…): '
                                        'nombre propio, orden y si está oculta.')
    elementos_ocultos = models.JSONField('Elementos ocultos', default=list, blank=True,
                                         help_text='Los elementos automáticos que la unidad retiró del menú; '
                                                   'el registro se conserva.')

    class Meta:
        db_table = 'webcitt_ajusteseccionplanta'
        ordering = ('unidad', 'numero')
        constraints = [models.UniqueConstraint(fields=('unidad', 'numero'), name='ajuste_seccion_unico_por_unidad')]
        verbose_name = 'Ajuste de sección de la ficha'
        verbose_name_plural = 'Ajustes de secciones de la ficha'

    def __str__(self):
        return f'{self.unidad} · {self.numero}'
