"""Cómo se relacionan las unidades entre sí: un centro aloja plantas y les provee materia prima, un laboratorio
analiza las muestras de un centro o una planta, un observatorio sigue con datos su producción.

Cada relación se registra una vez, desde quien la ejerce, y se lee desde las dos puntas: en el centro dice «Aloja
a la Planta de Lácteos» y en la planta «Funciona en el Centro Experimental San Francisco», cada una con su enlace.
"""
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.presentation.tipologias import nombre_tipologia

from apps.directorio_unidades.models.core import Unidad

# tipo: (lo que dice la unidad de origen, lo que dice la de destino, quién puede ejercerla)
TIPOS_RELACION = {
    'aloja': ('Aloja a', 'Funciona en', {'centro_experimental'}),
    'abastece': ('Provee materia prima a', 'Recibe materia prima de', {'centro_experimental', 'plantas_piloto'}),
    'analiza': ('Analiza muestras de', 'Analiza sus muestras', {'laboratorios'}),
    'sigue': ('Da seguimiento con datos a', 'Sus datos los sigue', {'observatorios'}),
    'apoya': ('Apoya con equipos o personal a', 'Recibe apoyo de', None),
}


class RelacionUnidad(models.Model):
    TIPOS = [(clave, directa) for clave, (directa, _inversa, _origenes) in TIPOS_RELACION.items()]

    origen = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='relaciones_salientes',
                               verbose_name='Unidad que la ejerce')
    tipo = models.CharField('Relación', max_length=12, choices=TIPOS)
    destino = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='relaciones_entrantes',
                                verbose_name='Unidad relacionada')
    que_fluye = models.CharField('Qué pasa de una a otra', max_length=200, blank=True,
                                 help_text='Por ejemplo «Leche cruda del hato» o «Muestras de suelo y agua de riego».')
    descripcion = models.CharField('Para qué', max_length=255, blank=True)
    activa = models.BooleanField('Vigente', default=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)

    class Meta:
        db_table = 'webcitt_relacionunidad'
        ordering = ('orden', 'tipo', 'destino__nombre')
        verbose_name = 'Relación entre unidades'
        verbose_name_plural = 'Relaciones entre unidades'
        constraints = [models.UniqueConstraint(fields=('origen', 'tipo', 'destino'), name='relacion_unidad_unica')]

    def __str__(self):
        return f'{self.origen} · {self.get_tipo_display().lower()} · {self.destino}'

    @property
    def etiqueta_inversa(self):
        return TIPOS_RELACION[self.tipo][1]

    def clean(self):
        if self.origen_id and self.origen_id == self.destino_id:
            raise ValidationError({'destino': 'Una unidad no se relaciona consigo misma.'})
        origenes = TIPOS_RELACION.get(self.tipo, (None, None, None))[2]
        if self.origen_id and origenes and self.origen.dependencia not in origenes:
            permitidas = ', '.join(sorted(nombre_tipologia(clave) for clave in origenes))
            raise ValidationError({'tipo': f'Esta relación la ejerce: {permitidas}.'})
        if self.tipo == 'aloja' and self.destino_id and self.destino.dependencia == 'centro_experimental':
            raise ValidationError({'destino': 'Un centro no aloja a otro centro.'})
