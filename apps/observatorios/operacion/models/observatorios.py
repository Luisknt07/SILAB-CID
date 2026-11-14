"""Lo propio de un observatorio: indicadores con ficha metodológica, sus valores en el tiempo, publicaciones con
calendario, encuestas propias, aliados y solicitudes de datos.

Un observatorio produce información para decidir. Cada indicador declara qué mide, cómo se calcula, de dónde sale
el dato y cada cuánto se actualiza (los campos de la ficha de metadatos de la Guía de Datos Abiertos del Ecuador),
y puede fijar umbrales: cuando su último valor los cruza, la ficha pública muestra una alerta. Las publicaciones
se planifican con fecha y se marcan al publicarse, para medir el cumplimiento del calendario. Las solicitudes de
datos solo las hacen personas con cuenta: el observatorio no recoge datos personales de visitantes anónimos.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad

ORIGENES_VALOR = [('cargador', 'Carga inicial verificada en su fuente'), ('manual', 'Registro en la página'),
                  ('csv', 'Plantilla CSV'), ('api', 'Sincronización automática')]

PERIODICIDADES = [
    ('diaria', 'Diaria'), ('semanal', 'Semanal'), ('mensual', 'Mensual'), ('trimestral', 'Trimestral'),
    ('cuatrimestral', 'Cuatrimestral'), ('semestral', 'Semestral'), ('anual', 'Anual'),
    ('quinquenal', 'Cada cinco años o más'), ('eventual', 'Eventual'),
]


def numero_legible(valor):
    """Un Decimal legible en español, sin ceros sobrantes."""
    if valor is None:
        return '—'
    signo = '-' if valor < 0 else ''
    texto = format(abs(valor).normalize() if valor != 0 else Decimal(0), 'f')
    entero, _, decimales = texto.partition('.')
    # Miles con espacio fino (172 828), como en las publicaciones del INEC; la coma separa los decimales.
    entero = f'{int(entero):,}'.replace(',', ' ')
    return f'{signo}{entero},{decimales}' if decimales else f'{signo}{entero}'


def _solo_observatorios(unidad):
    if unidad is not None and unidad.dependencia != 'observatorios':
        raise ValidationError({'unidad': 'Solo los observatorios registran indicadores, publicaciones y encuestas.'})


def _lineas_de(texto):
    return [linea.strip(' -•\t') for linea in (texto or '').splitlines() if linea.strip(' -•\t')]


def _pares_de(texto):
    """Las líneas «título | explicación» como pares; una línea sin barra queda sin explicación."""
    return [tuple(parte.strip() for parte in (linea.split('|', 1) + [''])[:2]) for linea in _lineas_de(texto)]


class LineaObservatorio(models.Model):
    """Un eje temático: el sector que el observatorio sigue con sus indicadores, tableros, visores y fuentes.

    Es lo que en un laboratorio es un área. Su página explica qué estudia, qué aporta al Carchi, qué preguntas
    responde, cómo trabaja paso a paso, qué produce, quién usa sus datos, qué carreras aportan y sus videos.
    """
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='lineas_observatorio',
                               verbose_name='Observatorio')
    codigo = models.SlugField('Código', max_length=40)
    titulo = models.CharField('Eje temático', max_length=120)
    icono = models.CharField('Ícono', max_length=40, default='fas fa-layer-group',
                             help_text='Ícono de Font Awesome, por ejemplo «fas fa-truck».')
    resumen = models.CharField('En una frase', max_length=255)
    que_estudia = models.TextField('Qué estudia')
    por_que_importa = models.TextField('Qué aporta al Carchi')
    preguntas = models.TextField('Qué preguntas responde', blank=True, help_text='Una por línea.')
    como_trabaja = models.TextField('Cómo trabaja, paso a paso', blank=True,
                                    help_text='Un paso por línea, con el formato «Paso | explicación».')
    productos = models.TextField('Qué produce', blank=True, help_text='Un producto por línea.')
    usuarios = models.TextField('Para quién sirve', blank=True,
                                help_text='Uno por línea, «Público | para qué le sirve» (docentes, estudiantes, empresas…).')
    carreras = models.TextField('Carreras y laboratorios que aportan', blank=True, help_text='Uno por línea.')
    temas_investigacion = models.TextField('Temas de investigación abiertos', blank=True,
                                           help_text='Preguntas para tesis, prácticas o proyectos; una por línea.')
    pendiente = models.TextField('Qué falta y por qué', blank=True,
                                 help_text='Lo que la línea aún no puede medir con datos verificables, y qué se espera.')
    videos = models.TextField('Videos', blank=True,
                              help_text='Uno por línea, «ID de YouTube | título | canal | qué muestra».')
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    publicada = models.BooleanField('Publicada', default=True)

    class Meta:
        db_table = 'webcitt_lineaobservatorio'
        ordering = ('unidad', 'orden', 'titulo')
        verbose_name = 'Eje temático del observatorio'
        verbose_name_plural = 'Ejes temáticos de los observatorios'
        constraints = [models.UniqueConstraint(fields=('unidad', 'codigo'), name='linea_codigo_por_observatorio')]

    def __str__(self):
        return self.titulo

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))

    lista_preguntas = property(lambda self: _lineas_de(self.preguntas))
    lista_productos = property(lambda self: _lineas_de(self.productos))
    para_quien = property(lambda self: _pares_de(self.usuarios))
    lista_carreras = property(lambda self: _lineas_de(self.carreras))
    lista_temas = property(lambda self: _lineas_de(self.temas_investigacion))

    pasos = property(lambda self: _pares_de(self.como_trabaja))

    @property
    def lista_videos(self):
        videos = []
        for linea in _lineas_de(self.videos):
            identificador, titulo, canal, descripcion = (linea.split('|') + ['', '', ''])[:4]
            identificador = identificador.strip()
            if identificador:
                videos.append({'id': identificador, 'titulo': titulo.strip(), 'canal': canal.strip(),
                               'descripcion': descripcion.strip(),
                               'url': f'https://www.youtube.com/watch?v={identificador}'})
        return videos


def ruta_imagen_area(instancia, nombre):
    return f'observatorios/{instancia.linea.unidad.slug}/areas/{instancia.linea.codigo}-{nombre}'


class ImagenLinea(models.Model):
    """Una foto de un eje temático, con su crédito: la primera es la portada y las demás, la galería."""
    linea = models.ForeignKey(LineaObservatorio, on_delete=models.CASCADE, related_name='imagenes',
                              verbose_name='Eje temático')
    imagen = models.ImageField('Imagen', upload_to=ruta_imagen_area)
    titulo = models.CharField('Qué muestra', max_length=200)
    credito = models.CharField('Crédito', max_length=255, blank=True,
                               help_text='Autor y licencia, por ejemplo «Diego Delso · CC BY-SA 4.0».')
    fuente = models.URLField('Página de la imagen', max_length=500, blank=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)

    class Meta:
        db_table = 'webcitt_imagenlinea'
        ordering = ('linea', 'orden', 'pk')
        verbose_name = 'Imagen de un eje temático'
        verbose_name_plural = 'Imágenes de los ejes temáticos'

    def __str__(self):
        return self.titulo


class FuenteDatos(models.Model):
    """Una base o fuente de la que salen los datos: quién la produce, cómo se obtiene y con qué nivel de acceso.

    El catálogo es común a todos los observatorios: el INEC o el Banco Central alimentan a varios. Dice si los datos
    se consultan solos por una API, se descargan, se toman de una publicación, se piden formalmente o se levantan,
    y si son abiertos, por solicitud, por convenio o con costo.
    """
    METODOS = [('api', 'API: el observatorio la consulta solo'), ('descarga', 'Descarga de archivo (CSV o Excel)'),
               ('pagina', 'Publicación o página web'), ('solicitud', 'Solicitud formal a la institución'),
               ('propia', 'Levantamiento propio del observatorio')]
    ACCESOS = [('abierto', 'Abierto y gratuito'), ('solicitud', 'Por solicitud (LOTAIP)'),
               ('convenio', 'Por convenio'), ('pago', 'Con costo')]

    nombre = models.CharField('Fuente', max_length=160, unique=True)
    institucion = models.CharField('Institución', max_length=160)
    descripcion = models.TextField('Qué contiene', blank=True)
    url = models.URLField('Dónde está', max_length=500, blank=True)
    documentacion = models.URLField('Documentación de la API o del archivo', max_length=500, blank=True)
    metodo = models.CharField('Cómo se obtiene', max_length=10, choices=METODOS, default='pagina')
    acceso = models.CharField('Nivel de acceso', max_length=10, choices=ACCESOS, default='abierto')
    licencia = models.CharField('Licencia o condiciones de uso', max_length=160, blank=True)
    periodicidad = models.CharField('Cada cuánto publica', max_length=80, blank=True)
    requiere_clave = models.BooleanField('La API exige clave', default=False)

    class Meta:
        db_table = 'webcitt_fuentedatos'
        ordering = ('institucion', 'nombre')
        verbose_name = 'Fuente o base de datos'
        verbose_name_plural = 'Fuentes y bases de datos de los observatorios'

    def __str__(self):
        return self.nombre


class IndicadorObservatorio(models.Model):
    """Un indicador con su ficha metodológica. Su valor vive en ValorIndicador, por periodo y territorio."""
    TIPOS_FUENTE = [
        ('registro', 'Registro administrativo o estadística oficial'),
        ('encuesta', 'Encuesta propia del observatorio'),
        ('estacion', 'Estación o sensor de monitoreo'),
        ('laboratorio', 'Análisis de un laboratorio de la universidad'),
        ('otra', 'Otra fuente'),
    ]
    SENTIDOS = [
        ('subir', 'Conviene que suba'), ('bajar', 'Conviene que baje'), ('estable', 'Conviene que se mantenga'),
        ('neutro', 'Sin valoración'),
    ]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='indicadores_observatorio',
                               verbose_name='Observatorio')
    codigo = models.SlugField('Código', max_length=40, help_text='Corto y estable, por ejemplo «precio-leche».')
    nombre = models.CharField('Indicador', max_length=160)
    pregunta = models.CharField('Qué pregunta responde', max_length=255, blank=True)
    definicion = models.TextField('Definición')
    formula = models.CharField('Fórmula o método de cálculo', max_length=255, blank=True)
    unidad_medida = models.CharField('Unidad de medida', max_length=60, help_text='Por ejemplo «%», «USD/litro», «t».')
    fuente = models.CharField('Fuente', max_length=255, help_text='Institución y operación de donde sale el dato.')
    tipo_fuente = models.CharField('Tipo de fuente', max_length=12, choices=TIPOS_FUENTE, default='registro')
    url_fuente = models.URLField('Enlace a la fuente', max_length=500, blank=True)
    periodicidad = models.CharField('Periodicidad', max_length=14, choices=PERIODICIDADES, default='anual')
    desagregacion = models.CharField('Desagregación', max_length=200, blank=True,
                                     help_text='Por ejemplo «provincia y cantón», «por sexo».')
    limitaciones = models.TextField('Limitaciones y advertencias', blank=True)
    sentido = models.CharField('Sentido deseado', max_length=8, choices=SENTIDOS, default='neutro')
    umbral_bajo = models.DecimalField('Alerta si baja de', max_digits=16, decimal_places=4, null=True, blank=True)
    umbral_alto = models.DecimalField('Alerta si sube de', max_digits=16, decimal_places=4, null=True, blank=True)
    alerta_variacion = models.DecimalField(
        'Alerta si empeora más de (%)', max_digits=6, decimal_places=2, null=True, blank=True,
        help_text='Criterio del observatorio: avisa cuando el último valor empeora más que este porcentaje frente al '
                  'periodo anterior, según el sentido deseado del indicador.')
    mensaje_alerta = models.CharField('Qué significa la alerta', max_length=255, blank=True)
    territorio_principal = models.CharField('Territorio principal', max_length=80, default='Carchi',
                                            help_text='El territorio cuyo último valor se resume en la ficha.')
    linea = models.ForeignKey(LineaObservatorio, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='indicadores', verbose_name='Eje temático')
    fuente_datos = models.ForeignKey(FuenteDatos, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='indicadores', verbose_name='Base o fuente de datos')
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    publicado = models.BooleanField('Publicado', default=True)
    actualizado = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        db_table = 'webcitt_indicadorobservatorio'
        ordering = ('unidad', 'orden', 'nombre')
        verbose_name = 'Indicador del observatorio'
        verbose_name_plural = 'Indicadores del observatorio'
        constraints = [models.UniqueConstraint(fields=('unidad', 'codigo'), name='indicador_codigo_por_observatorio')]

    def __str__(self):
        return self.nombre

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))
        if self.umbral_bajo is not None and self.umbral_alto is not None and self.umbral_bajo >= self.umbral_alto:
            raise ValidationError({'umbral_alto': 'El umbral alto debe ser mayor que el bajo.'})

    def serie(self, territorio=None):
        """Los valores del territorio principal (u otro), del más antiguo al más reciente."""
        return self.valores.filter(territorio=territorio or self.territorio_principal).order_by('fecha')

    def ultimos(self):
        """El último valor y el anterior del territorio principal, para la tendencia."""
        valores = list(self.valores.filter(territorio=self.territorio_principal).order_by('-fecha')[:2])
        return (valores + [None, None])[:2]

    @property
    def vigilado(self):
        """Si el indicador tiene algún criterio de alerta: umbral bajo, umbral alto o variación."""
        return any(criterio is not None for criterio in (self.umbral_bajo, self.umbral_alto, self.alerta_variacion))

    def variacion(self, valor, anterior):
        """El cambio porcentual del último valor frente al anterior, o None si no se puede calcular."""
        if valor is None or anterior is None or not anterior.valor:
            return None
        return (valor.valor - anterior.valor) / abs(anterior.valor) * 100

    def alerta(self, valor=None, anterior=None):
        """'bajo' o 'alto' si el último valor cruzó un umbral; 'variacion' si empeoró más de lo admitido frente al
        periodo anterior; '' si no hay alerta."""
        if valor is None:
            valor, anterior = self.ultimos()
        if valor is None:
            return ''
        if self.umbral_bajo is not None and valor.valor < self.umbral_bajo:
            return 'bajo'
        if self.umbral_alto is not None and valor.valor > self.umbral_alto:
            return 'alto'
        cambio = self.variacion(valor, anterior)
        if self.alerta_variacion is not None and cambio is not None and self.sentido in ('subir', 'bajar'):
            empeora = -cambio if self.sentido == 'subir' else cambio
            if empeora > self.alerta_variacion:
                return 'variacion'
        return ''


class ValorIndicador(models.Model):
    """El valor de un indicador en un periodo y un territorio."""
    indicador = models.ForeignKey(IndicadorObservatorio, on_delete=models.CASCADE, related_name='valores',
                                  verbose_name='Indicador')
    periodo = models.CharField('Periodo', max_length=20, help_text='Como se publica: «2024», «2025-T4», «2026-02».')
    fecha = models.DateField('Fecha de referencia', help_text='El primer día del periodo, para ordenar la serie.')
    territorio = models.CharField('Territorio', max_length=80, default='Carchi')
    valor = models.DecimalField('Valor', max_digits=16, decimal_places=4)
    provisional = models.BooleanField('Provisional', default=False)
    nota = models.CharField('Nota', max_length=255, blank=True, help_text='Fuente específica u observación del dato.')
    origen = models.CharField('Cómo entró', max_length=10, choices=ORIGENES_VALOR, default='manual')
    registrado = models.DateTimeField('Registrado', default=timezone.now)
    modificado = models.DateTimeField('Última modificación', auto_now=True)

    class Meta:
        db_table = 'webcitt_valorindicador'
        ordering = ('indicador', 'fecha', 'territorio')
        verbose_name = 'Valor de indicador'
        verbose_name_plural = 'Valores de indicadores'
        constraints = [models.UniqueConstraint(fields=('indicador', 'fecha', 'territorio'),
                                               name='un_valor_por_periodo_y_territorio')]

    def __str__(self):
        return f'{self.indicador} · {self.periodo} · {self.territorio}: {self.valor}'

    @property
    def valor_legible(self):
        """El valor sin ceros sobrantes y con sus miles: 33.4000 → 33,4; 16600 → 16 600."""
        return numero_legible(self.valor)

    def save(self, *args, **kwargs):
        """Si el valor cambia, la corrección queda en el historial: lo publicado antes no se pierde."""
        anterior = None
        if self.pk:
            anterior = ValorIndicador.objects.filter(pk=self.pk).values_list('valor', flat=True).first()
        super().save(*args, **kwargs)
        if anterior is not None and Decimal(anterior) != Decimal(self.valor):
            RevisionValor.objects.create(valor=self, anterior=anterior, nuevo=self.valor, origen=self.origen)


class RevisionValor(models.Model):
    """Una corrección de un valor ya publicado: qué decía, qué dice ahora, cuándo y por qué vía."""
    valor = models.ForeignKey(ValorIndicador, on_delete=models.CASCADE, related_name='revisiones',
                              verbose_name='Valor')
    fecha = models.DateTimeField('Fecha', auto_now_add=True)
    anterior = models.DecimalField('Valor anterior', max_digits=16, decimal_places=4)
    nuevo = models.DecimalField('Valor nuevo', max_digits=16, decimal_places=4)
    origen = models.CharField('Cómo entró', max_length=10, choices=ORIGENES_VALOR, default='manual')

    class Meta:
        db_table = 'webcitt_revisionvalor'
        ordering = ('-fecha',)
        verbose_name = 'Revisión de un valor'
        verbose_name_plural = 'Historial de revisiones de valores'

    def __str__(self):
        return f'{self.valor}: {self.anterior} → {self.nuevo}'


class ConectorIndicador(models.Model):
    """La consulta automática que mantiene al día un indicador desde una API pública.

    Cada conector sabe qué pedir (parámetros), cada cuánto (horas) y deja constancia de su última ejecución. Los
    valores que trae entran con origen «api» y, si corrigen uno anterior, la corrección queda en el historial.
    """
    TIPOS = [('socrata', 'Datos abiertos Socrata (datos.gov.co)'), ('csv', 'Archivo CSV publicado en la web'),
             ('firms', 'Focos de calor por satélite (NASA FIRMS), recortados al Carchi')]
    ESTADOS = [('pendiente', 'Sin ejecutar todavía'), ('ok', 'Al día'), ('error', 'Con error')]

    indicador = models.OneToOneField(IndicadorObservatorio, on_delete=models.CASCADE, related_name='conector',
                                     verbose_name='Indicador')
    tipo = models.CharField('Tipo de conexión', max_length=10, choices=TIPOS)
    parametros = models.JSONField('Parámetros de la consulta', default=dict, blank=True)
    frecuencia_horas = models.PositiveIntegerField('Cada cuántas horas', default=24)
    activo = models.BooleanField('Activo', default=True)
    ultima_ejecucion = models.DateTimeField('Última ejecución', null=True, blank=True)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS, default='pendiente')
    mensaje = models.CharField('Resultado', max_length=500, blank=True)
    nuevos = models.PositiveIntegerField('Valores nuevos en la última ejecución', default=0)
    actualizados = models.PositiveIntegerField('Valores corregidos en la última ejecución', default=0)

    class Meta:
        db_table = 'webcitt_conectorindicador'
        ordering = ('indicador__unidad', 'indicador__orden')
        verbose_name = 'Conexión automática de un indicador'
        verbose_name_plural = 'Conexiones automáticas de los indicadores'

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.indicador}'

    def vencido(self, ahora=None):
        if not self.activo:
            return False
        if self.ultima_ejecucion is None:
            return True
        return (ahora or timezone.now()) - self.ultima_ejecucion >= timezone.timedelta(hours=self.frecuencia_horas)

    @property
    def proxima_ejecucion(self):
        if self.ultima_ejecucion is None or not self.activo:
            return None
        return self.ultima_ejecucion + timezone.timedelta(hours=self.frecuencia_horas)


def ruta_publicacion(instancia, nombre):
    return f'observatorios/{instancia.unidad.slug}/publicaciones/{nombre}'


class PublicacionObservatorio(models.Model):
    """Un boletín, informe o nota de política, planificado en el calendario y marcado al publicarse."""
    TIPOS = [('boletin', 'Boletín'), ('informe', 'Informe'), ('nota_politica', 'Nota de política pública'),
             ('perfil', 'Perfil o ficha temática')]
    ESTADOS = [('planificada', 'Planificada'), ('publicada', 'Publicada'), ('cancelada', 'Cancelada')]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='publicaciones_observatorio',
                               verbose_name='Observatorio')
    tipo = models.CharField('Tipo', max_length=14, choices=TIPOS, default='boletin')
    titulo = models.CharField('Título', max_length=200)
    periodo = models.CharField('Periodo que cubre', max_length=40, blank=True)
    resumen = models.TextField('Resumen', blank=True)
    fecha_planificada = models.DateField('Fecha planificada')
    fecha_publicada = models.DateField('Fecha de publicación', null=True, blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS, default='planificada')
    archivo = models.FileField('Archivo', upload_to=ruta_publicacion, blank=True,
                               validators=[FileExtensionValidator(['pdf', 'docx', 'xlsx', 'csv', 'zip'])])
    enlace = models.URLField('Enlace', max_length=500, blank=True)
    indicadores = models.ManyToManyField(IndicadorObservatorio, db_table='webcitt_publicacionobservatorio_indicadores', blank=True, related_name='publicaciones',
                                         verbose_name='Indicadores en que se basa')

    class Meta:
        db_table = 'webcitt_publicacionobservatorio'
        ordering = ('-fecha_planificada', 'titulo')
        verbose_name = 'Publicación del observatorio'
        verbose_name_plural = 'Publicaciones del observatorio'

    def __str__(self):
        return self.titulo

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))
        if self.estado == 'publicada':
            if not self.fecha_publicada:
                self.fecha_publicada = timezone.localdate()
            if not self.archivo and not self.enlace:
                raise ValidationError({'archivo': 'Una publicación publicada necesita su archivo o su enlace.'})

    @property
    def a_tiempo(self):
        """Publicada en su fecha o antes; None si todavía no se publica."""
        if self.estado != 'publicada' or not self.fecha_publicada:
            return None
        return self.fecha_publicada <= self.fecha_planificada

    @property
    def atrasada(self):
        return self.estado == 'planificada' and self.fecha_planificada < timezone.localdate()


class EncuestaObservatorio(models.Model):
    """Una encuesta propia con su metodología pública."""
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='encuestas_observatorio',
                               verbose_name='Observatorio')
    nombre = models.CharField('Encuesta', max_length=160)
    objetivo = models.TextField('Objetivo')
    poblacion = models.CharField('Población objetivo', max_length=255)
    muestra = models.CharField('Muestra y diseño muestral', max_length=255, blank=True)
    periodicidad = models.CharField('Periodicidad', max_length=14, choices=PERIODICIDADES, default='semestral')
    ultimo_levantamiento = models.CharField('Último levantamiento', max_length=60, blank=True)
    etapa = models.CharField('Etapa', max_length=10, default='periodica',
                             choices=[('periodica', 'Se levanta periódicamente'),
                                      ('diseno', 'En diseño: primer levantamiento previsto')])
    proximo_levantamiento = models.CharField('Próximo levantamiento', max_length=60, blank=True)
    linea = models.ForeignKey(LineaObservatorio, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='encuestas', verbose_name='Eje temático')
    instrumento = models.URLField('Cuestionario o instrumento', max_length=500, blank=True)
    proteccion_datos = models.TextField(
        'Protección de datos personales', blank=True,
        default='Consentimiento informado de cada persona encuestada y anonimización antes de publicar, conforme a '
                'la Ley Orgánica de Protección de Datos Personales.')
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        db_table = 'webcitt_encuestaobservatorio'
        ordering = ('unidad', 'orden', 'nombre')
        verbose_name = 'Encuesta del observatorio'
        verbose_name_plural = 'Encuestas del observatorio'

    def __str__(self):
        return self.nombre

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))


class AliadoObservatorio(models.Model):
    """Una institución que aporta datos, usa los resultados o integra el comité del observatorio."""
    TIPOS = [('gobierno', 'Gobierno nacional o local'), ('gremio', 'Gremio o sector productivo'),
             ('academia', 'Universidad o centro de investigación'), ('organismo', 'Organismo internacional'),
             ('sociedad', 'Sociedad civil')]
    ROLES = [('fuente', 'Aporta datos'), ('usuario', 'Usa los resultados'), ('comite', 'Integra el comité'),
             ('socio', 'Socio en estudios')]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='aliados_observatorio',
                               verbose_name='Observatorio')
    nombre = models.CharField('Institución', max_length=160)
    tipo = models.CharField('Tipo', max_length=10, choices=TIPOS)
    rol = models.CharField('Rol', max_length=8, choices=ROLES, default='usuario')
    aporte = models.CharField('Qué aporta o cómo usa los datos', max_length=255, blank=True)
    convenio = models.CharField('Convenio', max_length=120, blank=True, help_text='Número o nombre del convenio, si existe.')
    enlace = models.URLField('Sitio web', max_length=300, blank=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        db_table = 'webcitt_aliadoobservatorio'
        ordering = ('unidad', 'orden', 'nombre')
        verbose_name = 'Aliado del observatorio'
        verbose_name_plural = 'Aliados del observatorio'

    def __str__(self):
        return self.nombre

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))


class SolicitudDatos(models.Model):
    """Una persona con cuenta pide datos, un análisis o una asesoría al observatorio."""
    TIPOS = [('datos', 'Datos o series'), ('analisis', 'Análisis o estudio'), ('asesoria', 'Asesoría metodológica'),
             ('sala', 'Uso de la sala de análisis'), ('capacitacion', 'Capacitación o curso')]
    ESTADOS = [('recibida', 'Recibida'), ('en_proceso', 'En proceso'), ('atendida', 'Atendida'),
               ('rechazada', 'No procede')]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='solicitudes_datos',
                               verbose_name='Observatorio')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitudes_datos',
                                verbose_name='Solicitante')
    tipo = models.CharField('Qué necesita', max_length=12, choices=TIPOS, default='datos')
    institucion = models.CharField('Institución', max_length=160, blank=True)
    descripcion = models.TextField('Qué necesita, de qué periodo y territorio')
    finalidad = models.CharField('Para qué lo usará', max_length=255)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS, default='recibida')
    respuesta = models.TextField('Respuesta del observatorio', blank=True)
    creada = models.DateTimeField('Recibida', auto_now_add=True)
    atendida = models.DateTimeField('Atendida', null=True, blank=True)

    class Meta:
        db_table = 'webcitt_solicituddatos'
        ordering = ('-creada',)
        verbose_name = 'Solicitud de datos'
        verbose_name_plural = 'Solicitudes de datos'

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.unidad}'

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))


VISTAS_TABLERO = [
    ('series', 'Series en el tiempo: último valor, cambio y gráfico de cada indicador'),
    ('semaforo', 'Semáforo: cada indicador frente a su umbral o su meta'),
    ('comparacion', 'Comparación entre cantones o territorios'),
    ('mapa', 'Mapa de los cantones del Carchi'),
]


class TableroObservatorio(models.Model):
    """Un tablero nativo: un grupo de indicadores que se leen juntos, con sus gráficos, desde la propia base."""
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='tableros_observatorio',
                               verbose_name='Observatorio')
    titulo = models.CharField('Tablero', max_length=160)
    descripcion = models.TextField('Qué permite ver', blank=True)
    indicadores = models.ManyToManyField(IndicadorObservatorio, db_table='webcitt_tableroobservatorio_indicadores', related_name='tableros', verbose_name='Indicadores')
    linea = models.ForeignKey(LineaObservatorio, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='tableros', verbose_name='Eje temático')
    vista = models.CharField('Cómo se dibuja', max_length=12, default='series', choices=VISTAS_TABLERO)
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    publicado = models.BooleanField('Publicado', default=True)

    class Meta:
        db_table = 'webcitt_tableroobservatorio'
        ordering = ('unidad', 'orden', 'titulo')
        verbose_name = 'Tablero del observatorio'
        verbose_name_plural = 'Tableros del observatorio'

    def __str__(self):
        return self.titulo

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))


class VisorExterno(models.Model):
    """Un tablero o mapa hecho en otra herramienta (Power BI, Looker Studio, ArcGIS…) que se muestra en la ficha.

    Es un complemento: la fuente oficial son los datos del observatorio. Por eso se registra con qué datos se
    alimenta, quién lo mantiene (una cuenta institucional, no personal) y su fecha de corte.
    """
    PLATAFORMAS = [('powerbi', 'Power BI'), ('looker', 'Looker Studio'), ('arcgis', 'ArcGIS'),
                   ('superset', 'Apache Superset'), ('metabase', 'Metabase'), ('tableau', 'Tableau Public'),
                   ('flourish', 'Flourish'), ('mymaps', 'Google My Maps'), ('otra', 'Otra')]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='visores_observatorio',
                               verbose_name='Observatorio')
    titulo = models.CharField('Visor', max_length=160)
    descripcion = models.TextField('Qué muestra', blank=True)
    plataforma = models.CharField('Plataforma', max_length=10, choices=PLATAFORMAS, default='powerbi')
    url = models.URLField('Dirección para insertar', max_length=600,
                          help_text='La dirección pública del visor (en Power BI, la de «Publicar en la web»).')
    url_datos = models.URLField('Datos que lo alimentan', max_length=600, blank=True,
                                help_text='El CSV o la API del observatorio que usa el visor; se ofrece para descargar.')
    responsable = models.CharField('Quién lo mantiene', max_length=160, blank=True,
                                   help_text='Una cuenta o un cargo institucional, no una cuenta personal.')
    fecha_corte = models.DateField('Fecha de corte de los datos', null=True, blank=True)
    linea = models.ForeignKey(LineaObservatorio, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='visores', verbose_name='Eje temático')
    institucion = models.CharField('Institución que lo publica', max_length=160, blank=True)
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    publicado = models.BooleanField('Publicado', default=True)

    class Meta:
        db_table = 'webcitt_visorexterno'
        ordering = ('unidad', 'orden', 'titulo')
        verbose_name = 'Visor externo del observatorio'
        verbose_name_plural = 'Visores externos del observatorio'

    def __str__(self):
        return self.titulo

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))
        if self.url and not self.url.startswith('https://'):
            raise ValidationError({'url': 'El visor debe servirse por https.'})


class PoliticaDatosObservatorio(models.Model):
    """Qué datos son abiertos, cuáles se entregan por solicitud o convenio, cuáles nunca, y qué servicios se cobran.

    Los textos por defecto siguen la LOTAIP (gratuidad y datos abiertos), la LOPDP (datos personales) y el Código
    Ingenios (bases de datos de investigación con fondos públicos en acceso abierto); cada observatorio los ajusta.
    """
    unidad = models.OneToOneField(Unidad, on_delete=models.CASCADE, related_name='politica_datos',
                                  verbose_name='Observatorio')
    licencia = models.CharField('Licencia de los datos abiertos', max_length=60, default='CC BY 4.0')
    abiertos = models.TextField('Datos abiertos (gratuitos)', default=(
        'Indicadores, series agregadas, boletines, fichas metodológicas y microdatos de encuestas propias ya '
        'anonimizados. Se descargan en CSV y JSON sin registro.'))
    por_solicitud = models.TextField('Por solicitud (gratuitos)', default=(
        'Desagregaciones o compilaciones que ya existen y no están publicadas. Se entregan en formato abierto en el '
        'plazo de la LOTAIP (10 días, prorrogables 5); solo se cobra el material si se piden impresas.'))
    por_convenio = models.TextField('Por convenio', default=(
        'Microdatos con riesgo de reidentificación y registros administrativos de otras instituciones, bajo las '
        'condiciones del convenio. No se cobra por el dato.'))
    reservados = models.TextField('Reservados', default=(
        'Datos personales identificables, respuestas con identificadores y consentimientos: no se entregan '
        '(Ley Orgánica de Protección de Datos Personales).'))
    servicios_pagados = models.TextField('Servicios con tarifa', default=(
        'Estudios a medida, levantamientos encargados, procesamientos que crean información nueva y capacitaciones, '
        'con la tarifa aprobada por la universidad. Si los contrata una entidad pública, el resultado se publica.'))
    cita = models.CharField('Cómo citar', max_length=300, blank=True,
                            help_text='Vacío: «Nombre del observatorio, Universidad Politécnica Estatal del Carchi».')
    actualizada = models.DateField('Actualizada', auto_now=True)

    class Meta:
        db_table = 'webcitt_politicadatosobservatorio'
        verbose_name = 'Política de datos del observatorio'
        verbose_name_plural = 'Políticas de datos de los observatorios'

    def __str__(self):
        return f'Política de datos · {self.unidad}'

    def clean(self):
        _solo_observatorios(getattr(self, 'unidad', None))


class DescargaDatos(models.Model):
    """Cuántas veces se descargó cada conjunto por día y formato: mide el uso sin guardar quién descargó."""
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='descargas_datos',
                               verbose_name='Observatorio')
    fecha = models.DateField('Fecha')
    formato = models.CharField('Formato', max_length=8)
    conjunto = models.CharField('Conjunto', max_length=60, blank=True, help_text='Código del indicador; vacío: todo.')
    veces = models.PositiveIntegerField('Descargas', default=0)

    class Meta:
        db_table = 'webcitt_descargadatos'
        ordering = ('-fecha',)
        verbose_name = 'Descarga de datos'
        verbose_name_plural = 'Descargas de datos'
        constraints = [models.UniqueConstraint(fields=('unidad', 'fecha', 'formato', 'conjunto'),
                                               name='una_cuenta_por_dia_formato_y_conjunto')]

    @classmethod
    def registrar(cls, unidad, formato, conjunto=''):
        from django.db.models import F
        fila, _ = cls.objects.get_or_create(unidad=unidad, fecha=timezone.localdate(), formato=formato,
                                            conjunto=conjunto)
        cls.objects.filter(pk=fila.pk).update(veces=F('veces') + 1)
