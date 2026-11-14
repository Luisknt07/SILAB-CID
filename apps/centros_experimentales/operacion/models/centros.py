"""Los centros experimentales trabajan por ejes productivos: ganadería de leche, cultivos andinos, café, frutales…

Un eje es lo que en un laboratorio es un área y en un observatorio un eje temático: dice qué produce, cómo trabaja
paso a paso, en qué temporada, con qué áreas del centro, a dónde va lo que produce (una planta piloto, la venta,
la semilla, las prácticas), para quién sirve, qué prácticas atiende y qué le falta para producir más. Sus ciclos
(una campaña, el hato, un lote de animales) y los registros diarios forman la gestión productiva, al final del módulo.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable


def _lineas_de(texto):
    return [linea.strip(' -•\t') for linea in (texto or '').splitlines() if linea.strip(' -•\t')]


def _pares_de(texto):
    """Las líneas «título | explicación» como pares; una línea sin barra queda sin explicación."""
    return [tuple(parte.strip() for parte in (linea.split('|', 1) + [''])[:2]) for linea in _lineas_de(texto)]


def _solo_centros(unidad):
    if unidad is not None and unidad.dependencia != 'centro_experimental':
        raise ValidationError({'unidad': 'Solo los centros experimentales organizan su producción por ejes.'})


class EjeProductivo(models.Model):
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='ejes_productivos',
                               verbose_name='Centro experimental')
    codigo = models.SlugField('Código', max_length=40)
    titulo = models.CharField('Eje productivo', max_length=120)
    icono = models.CharField('Ícono', max_length=40, default='fas fa-seedling',
                             help_text='Ícono de Font Awesome, por ejemplo «fas fa-tint».')
    resumen = models.CharField('En una frase', max_length=255)
    que_produce = models.TextField('Qué produce y para qué')
    rubros = models.TextField('Rubros', blank=True, help_text='Uno por línea: cultivo, especie o producto.')
    como_trabaja = models.TextField('Cómo trabaja, paso a paso', blank=True,
                                    help_text='Un paso por línea, con el formato «Paso | explicación».')
    calendario = models.TextField('Calendario', blank=True,
                                  help_text='Una temporada por línea, «Meses | qué se hace».')
    destino = models.TextField('A dónde va lo que produce', blank=True,
                               help_text='Uno por línea, «Destino | qué recibe» (una planta piloto, la venta, la semilla…).')
    para_quien = models.TextField('Para quién sirve', blank=True,
                                  help_text='Uno por línea, «Público | para qué le sirve».')
    practicas = models.TextField('Prácticas y asignaturas que atiende', blank=True, help_text='Una por línea.')
    temas_investigacion = models.TextField('Temas de investigación abiertos', blank=True, help_text='Uno por línea.')
    para_producir_mas = models.TextField('Qué le falta para producir más', blank=True,
                                         help_text='Una necesidad por línea, «Necesidad | qué permitiría».')
    videos = models.TextField('Videos', blank=True,
                              help_text='Uno por línea, «ID de YouTube | título | canal | qué muestra».')
    espacios = models.ManyToManyField(EspacioReservable, db_table='webcitt_ejeproductivo_espacios', blank=True, related_name='ejes_productivos',
                                      verbose_name='Áreas del centro que lo componen')
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    publicado = models.BooleanField('Publicado', default=True)

    class Meta:
        db_table = 'webcitt_ejeproductivo'
        ordering = ('unidad', 'orden', 'titulo')
        verbose_name = 'Eje productivo del centro'
        verbose_name_plural = 'Ejes productivos de los centros'
        constraints = [models.UniqueConstraint(fields=('unidad', 'codigo'), name='eje_codigo_por_centro')]

    def __str__(self):
        return self.titulo

    def clean(self):
        _solo_centros(getattr(self, 'unidad', None))

    lista_rubros = property(lambda self: _lineas_de(self.rubros))
    lista_practicas = property(lambda self: _lineas_de(self.practicas))
    lista_temas = property(lambda self: _lineas_de(self.temas_investigacion))
    pasos = property(lambda self: _pares_de(self.como_trabaja))
    temporadas = property(lambda self: _pares_de(self.calendario))
    destinos = property(lambda self: _pares_de(self.destino))
    publicos = property(lambda self: _pares_de(self.para_quien))
    necesidades = property(lambda self: _pares_de(self.para_producir_mas))

    @property
    def lista_videos(self):
        videos = []
        for linea in _lineas_de(self.videos):
            identificador, titulo, canal, descripcion = (linea.split('|') + ['', '', ''])[:4]
            if identificador.strip():
                videos.append({'id': identificador.strip(), 'titulo': titulo.strip(), 'canal': canal.strip(),
                               'descripcion': descripcion.strip()})
        return videos


class ImagenEje(models.Model):
    """Una foto del eje con su crédito y su licencia: la primera es la portada de la página del eje."""
    eje = models.ForeignKey(EjeProductivo, on_delete=models.CASCADE, related_name='imagenes', verbose_name='Eje')
    imagen = models.ImageField('Imagen', upload_to='centros/ejes/')
    titulo = models.CharField('Qué muestra', max_length=160)
    credito = models.CharField('Autor y licencia', max_length=200, blank=True)
    fuente = models.URLField('Página de origen', blank=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)

    class Meta:
        db_table = 'webcitt_imageneje'
        ordering = ('eje', 'orden', 'pk')
        verbose_name = 'Foto del eje productivo'
        verbose_name_plural = 'Fotos de los ejes productivos'

    def __str__(self):
        return self.titulo


# --------------------------------------------------------------------- la gestión productiva
# Un centro deja de producir solo en temporada de prácticas cuando cada eje planifica sus ciclos (una campaña de papa,
# el hato en un año, un lote de ponedoras) con una meta, y registra el mismo día lo que pasa: cosechas, ordeños,
# posturas, pesajes, labores, sanidad, insumos y entregas. Con eso se compara lo producido con lo planificado.

UNIDADES_DE_MEDIDA = [
    ('kg', 'kilogramos'), ('t', 'toneladas'), ('L', 'litros'), ('huevos', 'huevos'), ('animales', 'animales'),
    ('plantas', 'plantas'), ('qq', 'quintales'), ('unidades', 'unidades'),
]


class CicloProductivo(models.Model):
    TIPOS = [
        ('cultivo', 'Campaña de cultivo'),
        ('hato', 'Hato o plantel en producción'),
        ('lote', 'Lote de animales'),
        ('vivero', 'Producción de plántulas'),
        ('proceso', 'Proceso del centro (compost, beneficio…)'),
    ]
    ESTADOS = [('planificado', 'Planificado'), ('en_curso', 'En curso'), ('cerrado', 'Cerrado')]

    eje = models.ForeignKey(EjeProductivo, on_delete=models.CASCADE, related_name='ciclos', verbose_name='Eje productivo')
    nombre = models.CharField('Ciclo', max_length=120, help_text='Por ejemplo «Papa Superchola, bloque 7, 2026-B».')
    tipo = models.CharField('Tipo', max_length=10, choices=TIPOS, default='cultivo')
    rubro = models.CharField('Rubro', max_length=80, help_text='El cultivo, la especie o el producto.')
    lugar = models.ForeignKey(EspacioReservable, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='ciclos_productivos', verbose_name='Área o lote del centro')
    inicio = models.DateField('Inicio')
    fin_previsto = models.DateField('Fin previsto')
    fin = models.DateField('Fin real', null=True, blank=True)
    superficie_ha = models.DecimalField('Superficie (ha)', max_digits=7, decimal_places=2, null=True, blank=True)
    animales = models.PositiveIntegerField('Animales', null=True, blank=True)
    meta = models.DecimalField('Meta de producción', max_digits=12, decimal_places=2,
                               help_text='Lo que el ciclo debe producir en total, en la unidad de medida.')
    unidad_medida = models.CharField('Unidad de medida', max_length=10, choices=UNIDADES_DE_MEDIDA, default='kg')
    referencia = models.CharField('De dónde sale la meta', max_length=200, blank=True,
                                  help_text='Por ejemplo «14 t/ha, INIAP» o «7,9 L/vaca/día, promedio de la Sierra 2024».')
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS, default='planificado')
    notas = models.TextField('Notas', blank=True)

    class Meta:
        db_table = 'webcitt_cicloproductivo'
        ordering = ('-inicio', 'nombre')
        verbose_name = 'Ciclo productivo'
        verbose_name_plural = 'Ciclos productivos'

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.inicio and self.fin_previsto and self.fin_previsto < self.inicio:
            raise ValidationError({'fin_previsto': 'El ciclo debe terminar después de empezar.'})
        if self.fin and self.inicio and self.fin < self.inicio:
            raise ValidationError({'fin': 'El ciclo debe terminar después de empezar.'})
        if self.lugar_id and self.eje_id and self.lugar.unidad_id != self.eje.unidad_id:
            raise ValidationError({'lugar': 'El área debe ser del mismo centro del eje.'})
        if self.estado == 'cerrado' and not self.fin:
            raise ValidationError({'fin': 'Para cerrar el ciclo, registra su fecha de fin.'})

    @property
    def producido(self):
        """Lo producido según los registros de cosecha, ordeño, postura o salida, en la unidad del ciclo."""
        total = self.registros.filter(tipo__in=RegistroProduccion.PRODUCCION, unidad_medida=self.unidad_medida) \
            .aggregate(total=models.Sum('cantidad'))['total']
        return total or 0

    @property
    def cumplimiento(self):
        """El porcentaje de la meta que ya se produjo; None sin meta."""
        return round(float(self.producido) * 100 / float(self.meta)) if self.meta else None


class RegistroProduccion(models.Model):
    TIPOS = [
        ('cosecha', 'Cosecha'),
        ('ordeno', 'Ordeño'),
        ('postura', 'Postura (huevos)'),
        ('salida', 'Salida de animales o producto'),
        ('pesaje', 'Pesaje o conteo'),
        ('labor', 'Labor (siembra, poda, riego, deshierbe…)'),
        ('sanidad', 'Sanidad (vacuna, tratamiento, control de plagas)'),
        ('insumo', 'Insumo aplicado'),
        ('entrega', 'Entrega a un destino'),
        ('novedad', 'Novedad o pérdida'),
    ]
    # Lo que suma a la producción del ciclo.
    PRODUCCION = ('cosecha', 'ordeno', 'postura', 'salida')
    DESTINOS = [
        ('', '—'), ('planta', 'Planta piloto'), ('venta', 'Venta'), ('practicas', 'Prácticas'), ('semilla', 'Semilla'),
        ('consumo', 'Consumo del centro (alimento, abono)'), ('perdida', 'Pérdida'),
    ]

    ciclo = models.ForeignKey(CicloProductivo, on_delete=models.CASCADE, related_name='registros', verbose_name='Ciclo')
    fecha = models.DateField('Fecha')
    tipo = models.CharField('Qué se registra', max_length=10, choices=TIPOS)
    cantidad = models.DecimalField('Cantidad', max_digits=12, decimal_places=2, null=True, blank=True)
    unidad_medida = models.CharField('Unidad de medida', max_length=10, choices=UNIDADES_DE_MEDIDA, blank=True)
    destino = models.CharField('Destino', max_length=10, choices=DESTINOS, blank=True)
    detalle = models.CharField('Detalle', max_length=255, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='registros_produccion', verbose_name='Registrado por')
    creado = models.DateTimeField('Registrado', auto_now_add=True)

    class Meta:
        db_table = 'webcitt_registroproduccion'
        ordering = ('-fecha', '-pk')
        verbose_name = 'Registro de producción'
        verbose_name_plural = 'Registros de producción'

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.fecha:%d/%m/%Y}'

    def clean(self):
        if self.tipo in self.PRODUCCION + ('entrega',) and self.cantidad is None:
            raise ValidationError({'cantidad': 'Una cosecha, un ordeño, una postura, una salida o una entrega lleva cantidad.'})
        if self.cantidad is not None and not self.unidad_medida:
            raise ValidationError({'unidad_medida': 'Indica en qué se mide la cantidad.'})
        if self.tipo == 'entrega' and not self.destino:
            raise ValidationError({'destino': 'Una entrega dice a dónde fue.'})
        ciclo = getattr(self, 'ciclo', None)
        if ciclo is not None and self.fecha and self.fecha < ciclo.inicio:
            raise ValidationError({'fecha': 'El registro no puede ser anterior al inicio del ciclo.'})
