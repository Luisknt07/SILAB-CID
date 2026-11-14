"""Expediente de calidad de cada unidad, por año de gestión.

La universidad pide la documentación de cada unidad organizada en cuatro
carpetas —Planeación, Ejecución, Evaluación y Mejora continua— y disponible
por período. Aquí viven dos cosas: el catálogo institucional de lo exigido
(qué documento, en qué carpeta, quién lo produce, cada cuánto y con qué plazo)
y el estado de cada documento en cada unidad y año: pendiente, generado por el
sistema, cargado firmado, validado u observado.

El archivo físico es un `Recurso` del módulo de contenidos de la unidad, que
ya versiona, calcula hash y controla el acceso; el expediente solo lo apunta.
"""

from datetime import date, datetime, time, timedelta
from contextvars import ContextVar
from functools import wraps

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

# Documentos que la unidad redacta con el editor guiado antes de firmarlos.
REDACTABLES = ('planificacion', 'informe', 'compras', 'protocolo')

CARPETAS = [
    ('planeacion', 'Planeación'),
    ('ejecucion', 'Ejecución'),
    ('evaluacion', 'Evaluación'),
    ('mejora', 'Mejora continua'),
]
NOMBRES_CARPETA = dict(CARPETAS)


class DocumentoExigido(models.Model):
    """Un documento que la institución exige a las unidades, tal como lo define el formato anual."""

    PERIODICIDADES = [
        ('unica', 'Una sola vez; se hereda cada año'),
        ('anual', 'Una vez por año de gestión'),
        ('semestral', 'Una vez por período académico'),
        ('mensual', 'Cada mes'),
    ]
    ORIGENES = [
        ('sistema', 'Lo genera el sistema con lo registrado'),
        ('unidad', 'Lo carga la unidad'),
        ('ambos', 'El sistema genera el borrador y la unidad carga la versión firmada'),
    ]
    PLAZOS = [
        ('inicio', 'Días después del inicio del año o período'),
        ('fin', 'Días antes del cierre del año o período'),
        ('cierre', 'Entrega después del cierre del semestre de gestión'),
        ('meses', 'Entre dos meses del año'),
        ('ninguno', 'Sin plazo'),
    ]

    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True, help_text='Qué se espera y qué indicador mínimo lo acompaña.')
    carpeta = models.CharField(max_length=12, choices=CARPETAS)
    periodicidad = models.CharField(max_length=10, choices=PERIODICIDADES, default='anual')
    origen = models.CharField(max_length=8, choices=ORIGENES, default='unidad')
    requiere_firma = models.BooleanField(
        'Requiere firma electrónica', default=False,
        help_text='La carga se acepta solo si el PDF trae firma electrónica (FirmaEC).',
    )
    plazo_regla = models.CharField(max_length=8, choices=PLAZOS, default='ninguno')
    apertura_dias = models.PositiveSmallIntegerField(
        'Días de ventana para entregarlo',
        default=15,
        help_text='Cuántos días antes del vencimiento se abre la entrega. La planificación se '
                  'entrega desde el primer día del período; el cierre, en los últimos días.',
    )
    plazo_dias = models.PositiveSmallIntegerField(default=0)
    hora_limite = models.TimeField(default=time(23, 59), verbose_name='Hora límite institucional')
    fecha_limite = models.DateField(null=True, blank=True, verbose_name='Fecha institucional específica',
                                   help_text='Opcional: sustituye la regla solo en el año de esta fecha.')
    # Con plazo «entre dos meses»: el plan anual de compras se presenta de mayo a agosto.
    abre_mes = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text='Con plazo «entre dos meses»: mes en que se abre la entrega.')
    vence_mes = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text='Con plazo «entre dos meses»: último mes para entregar.')
    fuente_reporte = models.CharField(
        max_length=30, blank=True,
        help_text='Categoría del Centro de reportes con la que el sistema genera el documento, o '
                  '«planificacion» / «informe» cuando se redacta con el editor guiado.',
    )
    condicional = models.BooleanField(
        'Solo cuando aplique', default=False,
        help_text='No todas las unidades hacen esto: la unidad puede marcarlo como «no aplica» con su '
                  'justificación y deja de contar en su cumplimiento.',
    )
    tipos_unidad = models.JSONField(
        default=list, blank=True,
        help_text='Códigos de tipo de unidad a los que aplica; vacío significa todos.',
    )
    orden = models.PositiveSmallIntegerField(default=100)
    activo = models.BooleanField(default=True)
    # La unidad firma dos documentos por período; todo lo que el sistema produce
    # viaja dentro de ellos como anexo y se valida con ellos. Un anexo no es una
    # obligación aparte: si lo fuera, quince clics de ceremonia no medirían calidad.
    anexo_de = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='anexos',
        verbose_name='Anexo de',
        help_text='Documento firmado que lleva a este como anexo. Se genera y se valida con él.',
    )

    class Meta:
        db_table = 'webcitt_documentoexigido'
        ordering = ['carpeta', 'orden', 'codigo']
        verbose_name = 'Documento exigido del expediente'
        verbose_name_plural = 'Documentos exigidos del expediente'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def nombre_para(self, unidad):
        from apps.documentos.presentation.perfil_laboratorios import nombre_para
        return nombre_para(self, unidad)

    def periodicidad_para(self, unidad):
        from apps.documentos.presentation.perfil_laboratorios import periodicidad_para
        return periodicidad_para(self, unidad)

    def aplica_a(self, dependencia, *, base=None):
        from apps.documentos.presentation.perfil_unidades import aplica_documento
        return aplica_documento(self, dependencia, base=base)

    @property
    def generable(self):
        return self.origen in ('sistema', 'ambos') and bool(self.fuente_reporte)

    @property
    def cargable(self):
        return self.origen in ('unidad', 'ambos')

    @property
    def redactable(self):
        """Se elabora con el editor guiado y luego se firma y se carga."""
        return self.fuente_reporte in REDACTABLES

    @property
    def automatico(self):
        """Lo produce el sistema con lo registrado: no es una entrega de la unidad."""
        return self.origen == 'sistema'

    @property
    def es_anexo(self):
        return self.anexo_de_id is not None

    @property
    def corte_del_anexo_anual(self):
        """Con qué período viaja un anexo anual: el de apertura si su documento abre el
        año (la planificación), el de cierre si lo cierra (el informe)."""
        if not self.es_anexo or self.periodicidad != 'anual':
            return ''
        return 'A' if self.anexo_de.plazo_regla == 'inicio' else 'B'

    def vence(self, inicio, fin):
        """Fecha de vencimiento para un tramo (inicio, fin), o None si no hay plazo."""
        if self.fecha_limite and self.fecha_limite.year == inicio.year:
            return self.fecha_limite
        if self.plazo_regla == 'inicio':
            return inicio + timedelta(days=self.plazo_dias)
        if self.plazo_regla == 'fin':
            return fin - timedelta(days=self.plazo_dias)
        if self.plazo_regla == 'cierre':
            return fin + timedelta(days=self.plazo_dias)
        if self.plazo_regla == 'meses' and self.vence_mes:
            siguiente = date(inicio.year + (self.vence_mes == 12), self.vence_mes % 12 + 1, 1)
            return siguiente - timedelta(days=1)
        return None

    def abre(self, inicio, fin):
        """Desde cuándo se puede entregar.

        Lo que abre el período se entrega desde el primer día; lo que lo cierra
        necesita que el período haya avanzado, así que su ventana empieza unos
        días antes del vencimiento. Sin esa ventana, un informe de cierre
        aparecería como pendiente desde enero.
        """
        if self.plazo_regla == 'meses' and self.abre_mes:
            return date(inicio.year, self.abre_mes, 1)
        if self.plazo_regla == 'cierre':
            return max(inicio, fin - timedelta(days=self.apertura_dias or 0))
        if self.plazo_regla != 'fin':
            return inicio
        vence = self.vence(inicio, fin)
        if vence is None:
            return inicio
        return max(inicio, vence - timedelta(days=self.apertura_dias or 0))


# Valores por omisión de la política institucional. El mínimo no es un detalle
# del código: es el indicador con el que se mide a todas las unidades, así que
# vive en una fila que la Dirección cambia sin tocar nada más.
MINIMO_CUMPLIMIENTO = 70
PENALIZACION_TARDIA = 20

# Una operación de lectura comparte una política. La siguiente vuelve a leer
# la base, incluso cuando otro proceso fue quien guardó el cambio.
_POLITICA = ContextVar('politica_calidad_lectura', default=None)


def olvidar_politica():
    """Vuelve a leer la política de la base en la próxima consulta."""
    _POLITICA.set(None)


def politica_consistente(funcion):
    """Una lectura coherente por operación, sin caché permanente por proceso."""
    @wraps(funcion)
    def leer(*args, **kwargs):
        if _POLITICA.get() is not None:
            return funcion(*args, **kwargs)
        token = _POLITICA.set(PoliticaDeCalidad.objects.order_by('pk').first() or PoliticaDeCalidad())
        try:
            return funcion(*args, **kwargs)
        finally:
            _POLITICA.reset(token)
    return leer


class PoliticaDeCalidad(models.Model):
    """Con qué se mide el cumplimiento de todas las unidades: una sola fila.

    El mínimo institucional decide quién cumple y quién pasa a mejora continua,
    y la penalización dice cuánto cuesta entregar fuera de plazo: entregar tarde
    no exime de entregar, pero tampoco vale lo mismo que entregar a tiempo.
    """

    minimo_cumplimiento = models.PositiveSmallIntegerField(
        'Mínimo de cumplimiento (%)', default=MINIMO_CUMPLIMIENTO, validators=[MaxValueValidator(100)],
        help_text='Por debajo de este porcentaje la unidad no cumple y pasa a mejora continua.')
    penalizacion_entrega_tardia = models.PositiveSmallIntegerField(
        'Penalización por entregar fuera de plazo (puntos)', default=PENALIZACION_TARDIA,
        validators=[MaxValueValidator(100)],
        help_text='Se descuenta de la calificación de la entrega que la Dirección recibió vencido el plazo.')
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'webcitt_politicadecalidad'
        verbose_name = 'Política de calidad del expediente'
        verbose_name_plural = 'Política de calidad del expediente'
        constraints = [
            models.CheckConstraint(condition=models.Q(minimo_cumplimiento__lte=100),
                                   name='calidad_minimo_porcentaje'),
            models.CheckConstraint(condition=models.Q(penalizacion_entrega_tardia__lte=100),
                                   name='calidad_penalizacion_porcentaje'),
        ]

    def __str__(self):
        return (f'Mínimo {self.minimo_cumplimiento} % · entregar fuera de plazo cuesta '
                f'{self.penalizacion_entrega_tardia} puntos')

    def save(self, *args, **kwargs):
        """Una política, una fila: guardar dos veces no crea dos mínimos."""
        self.pk = 1
        super().save(*args, **kwargs)
        olvidar_politica()

    def delete(self, *args, **kwargs):
        resultado = super().delete(*args, **kwargs)
        olvidar_politica()
        return resultado

    @classmethod
    def vigente(cls):
        """La política guardada o, mientras nadie la escriba, la de por omisión."""
        return _POLITICA.get() or cls.objects.order_by('pk').first() or cls()


def minimo_vigente():
    """El porcentaje que hay que alcanzar para cumplir."""
    return PoliticaDeCalidad.vigente().minimo_cumplimiento


def penalizacion_vigente():
    """Cuántos puntos cuesta que la entrega llegue fuera de plazo."""
    return PoliticaDeCalidad.vigente().penalizacion_entrega_tardia


NOMBRES_ETAPA = {
    'planeacion': 'Planeación', 'ejecucion': 'Ejecución', 'evaluacion': 'Evaluación',
    'mejora': 'Mejora continua',
}


class DocumentoExpediente(models.Model):
    """El estado de un documento exigido en una unidad, un año y un corte."""

    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('generado', 'Generado por el sistema'),
        ('cargado', 'Cargado, por validar'),
        ('validado', 'Validado'),
        ('observado', 'Observado'),
        ('no_aplica', 'No aplica a la unidad'),
    ]
    CORTES = [('', 'Anual'), ('A', 'Período A'), ('B', 'Período B')]

    unidad = models.ForeignKey('directorio_unidades.Unidad', on_delete=models.CASCADE, related_name='expediente')
    exigido = models.ForeignKey(DocumentoExigido, on_delete=models.PROTECT, related_name='documentos')
    anio = models.PositiveSmallIntegerField('Año de gestión', db_index=True)
    corte = models.CharField(max_length=1, choices=CORTES, blank=True, default='')
    mes = models.PositiveSmallIntegerField(null=True, blank=True)
    tramo_inicio = models.DateField(null=True, blank=True, editable=False)
    tramo_fin = models.DateField(null=True, blank=True, editable=False)
    marco_periodo = models.CharField(max_length=32, default='gestion_v1', editable=False,
        help_text='Marco y fechas conservados del documento; no se recalculan al cambiar el calendario académico.')
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente', db_index=True)
    recurso = models.ForeignKey(
        'recursos.Recurso', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_expediente',
    )
    version = models.PositiveSmallIntegerField(default=0)
    firma_verificada = models.BooleanField(
        default=False, help_text='La versión actual pasó la validación de carga de PDF firmado.')
    verificacion_qr = models.UUIDField(null=True, blank=True, editable=False)
    entregado_en = models.DateTimeField(null=True, blank=True)
    evaluacion_version = models.PositiveSmallIntegerField(null=True, blank=True)
    abre_el = models.DateField(null=True, blank=True)
    vence_el = models.DateField(null=True, blank=True)
    prorroga_hasta = models.DateTimeField(null=True, blank=True)
    correccion_hasta = models.DateTimeField(
        'Corregir y reenviar hasta', null=True, blank=True,
        help_text='Fecha fijada por Dirección al devolver una entrega con observaciones.')
    ultimatum_hasta = models.DateTimeField(null=True, blank=True)
    incumplimiento_procesado_hasta = models.DateTimeField(null=True, blank=True)
    generado_en = models.DateTimeField(null=True, blank=True)
    cargado_en = models.DateTimeField(null=True, blank=True)
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_expediente_cargados',
    )
    validado_en = models.DateTimeField(null=True, blank=True)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_expediente_validados',
    )
    observacion = models.TextField(blank=True, help_text='Motivo de la observación; la unidad lo ve y corrige.')
    # La evaluación de la Dirección sobre lo enviado: un porcentaje de cumplimiento
    # y su motivo. Por debajo del mínimo, el documento pasa a mejora continua.
    evaluacion = models.PositiveSmallIntegerField(
        'Cumplimiento evaluado (%)', null=True, blank=True,
        help_text='De 0 a 100. Lo decide la Dirección sobre el documento enviado.')
    evaluacion_observacion = models.TextField(
        'Observación de la evaluación', blank=True,
        help_text='Lo que la Dirección vio: obligatoria cuando no alcanza el mínimo.')
    # Una nota sola dice si cumplió; esto dice dónde está la unidad y qué debe
    # atender en el siguiente período. Su próxima planificación lo responde.
    evaluacion_fortalezas = models.TextField(
        'Fortalezas', blank=True, help_text='Lo que la unidad hace bien y debe sostener.')
    evaluacion_debilidades = models.TextField(
        'Debilidades', blank=True, help_text='Lo que falta o falla; de aquí sale la mejora continua.')
    evaluacion_recomendaciones = models.TextField(
        'Recomendaciones para el siguiente período', blank=True,
        help_text='Lo que la unidad debe atender en el siguiente período; su planificación lo responde.')
    evaluado_en = models.DateTimeField(null=True, blank=True)
    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_expediente_evaluados',
    )
    # La Dirección es quien recibe. Cuando la unidad archivó su documento y no
    # alcanzó a validarlo, el director lo da por recibido y lo califica desde
    # su tablero: antes esperaba la firma de un tercero que no decidía nada.
    recibido_en = models.DateTimeField(null=True, blank=True)
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_expediente_recibidos',
    )
    # Entregar tarde no exime de entregar: vencido el plazo, la unidad pide a la
    # Dirección que lo habilite, el documento se recibe y queda marcado. La
    # marca descuenta puntos; el expediente no queda incompleto por eso.
    entregado_tarde = models.BooleanField('Entregado fuera de plazo', default=False)
    tardanza_motivo = models.TextField(
        'Motivo para entregar fuera de plazo', blank=True,
        help_text='Lo que expone el responsable de la unidad para entregar vencido el plazo.')
    tardanza_pedida_en = models.DateTimeField(null=True, blank=True)
    tardanza_habilitada_en = models.DateTimeField(null=True, blank=True)
    tardanza_habilitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_expediente_habilitados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_documentoexpediente'
        ordering = ['-anio', 'exigido__carpeta', 'exigido__orden', 'corte', 'mes']
        constraints = [
            models.UniqueConstraint(fields=['unidad', 'exigido', 'anio', 'corte', 'mes'],
                                    nulls_distinct=False, name='expediente_tramo_unico'),
        ]
        verbose_name = 'Documento del expediente'
        verbose_name_plural = 'Documentos del expediente de calidad'

    def __str__(self):
        return f'{self.nombre_documental} · {self.unidad.nombre} · {self.etiqueta_corte}'

    @property
    def nombre_documental(self):
        return self.exigido.nombre_para(self.unidad)

    @property
    def periodicidad_documental(self):
        return self.exigido.periodicidad_para(self.unidad)

    @property
    def requisitos_documentales(self):
        from apps.documentos.presentation.perfil_laboratorios import requisitos_para
        return requisitos_para(self)

    @property
    def etiqueta_corte(self):
        if self.mes:
            return f'{self.mes:02d}/{self.anio}'
        if self.corte:
            return f'Período {self.anio}-{self.corte}'
        return f'Año {self.anio}'

    @property
    def etiqueta_gestion(self):
        if self.exigido.codigo == 'PLAN-COMPRAS-ANUAL':
            return f'Necesidades {self.anio + 1} · preparación {self.anio}'
        return self.etiqueta_corte

    @property
    def exigible(self):
        """Cuenta en el cumplimiento de la unidad.

        Cuenta lo que la unidad entrega firmado y lo que se le pide una sola
        vez. Los anexos que el sistema produce viajan dentro del documento
        firmado y se validan con él: no son obligaciones aparte. Y queda fuera
        lo que la unidad declaró que no le aplica.
        """
        return self.estado != 'no_aplica' and not self.exigido.anexo_de_id

    @property
    def abierto(self):
        """Ya se puede entregar: su ventana empezó."""
        hoy = timezone.localdate()
        return self.abre_el is None or hoy >= self.abre_el

    @property
    def vencido(self):
        """Su plazo pasó."""
        return bool(self.plazo_original and timezone.now() > self.plazo_original)

    @property
    def plazo_original(self):
        if not self.vence_el:
            return None
        return timezone.make_aware(datetime.combine(self.vence_el, self.exigido.hora_limite))

    @property
    def plazo_entrega(self):
        return self.prorroga_hasta or self.correccion_hasta or self.ultimatum_hasta or self.plazo_original

    @property
    def correccion_activa(self):
        return bool(self.correccion_hasta and timezone.now() <= self.correccion_hasta)

    @property
    def correccion_abierta(self):
        return bool(self.correccion_hasta and self.plazo_entrega >= timezone.now())

    @property
    def ultimatum_activo(self):
        return bool(self.ultimatum_hasta and timezone.now() <= self.ultimatum_hasta)

    @property
    def reapertura_activa(self):
        return bool(self.tardanza_habilitada_en and self.prorroga_hasta
                    and timezone.now() <= self.prorroga_hasta)

    @property
    def prorroga_activa(self):
        return self.ultimatum_activo or self.reapertura_activa

    @property
    def solicitud_reapertura_pendiente(self):
        return bool(self.tardanza_pedida_en and (not self.tardanza_habilitada_en
                    or self.tardanza_pedida_en > self.tardanza_habilitada_en))

    @property
    def entrega_abierta(self):
        """Hoy se puede entregar: la ventana abrió y, si venció, la Dirección lo habilitó."""
        if self.correccion_hasta:
            return self.correccion_abierta
        return self.abierto and (not self.vencido or self.prorroga_activa)

    @property
    def nota(self):
        """La calificación que cuenta: la evaluada, menos lo que cuesta entregar tarde.

        Es lo que se promedia para saber si la unidad cumple. La nota de la
        Dirección mide el documento; la penalización mide la puntualidad, y las
        dos cosas pesan en el mismo indicador.
        """
        from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
        if es_permanente(self):
            # Crédito documental binario, sin transformar la decisión histórica en otra nota.
            return 100 if aprobacion_vigente(self) else None
        if (self.evaluacion is None or (self.estado != 'validado' and self.evaluacion != 0)
                or self.evaluacion_version != self.version):
            if self.evaluacion is not None and self.evaluacion_version == self.version:
                return None
            from apps.documentos.presentation.automatizacion_documental import nota_automatica
            return nota_automatica(self)
        if not self.entregado_tarde:
            return self.evaluacion
        return max(0, self.evaluacion - penalizacion_vigente())

    @property
    def firma_pendiente(self):
        return self.exigido.requiere_firma and not (self.firma_verificada or self.verificacion_qr)

    @property
    def aprobacion_en_linea_disponible(self):
        from apps.documentos.presentation.aprobacion_en_linea import admite_aprobacion_en_linea
        return (self.estado != 'cargado' and
                (not self.recurso_id or self.estado == 'generado' or bool(self.verificacion_qr)) and
                admite_aprobacion_en_linea(self))

    @property
    def cumple(self):
        """Alcanza el mínimo institucional; None si la Dirección todavía no lo calificó."""
        nota = self.nota
        if nota is None:
            return None
        return nota >= minimo_vigente()

    def etapa(self, hoy=None):
        """En qué carpeta está hoy el documento: planeacion · ejecucion · evaluacion · mejora.

        Es un solo archivo que recorre las cuatro carpetas del expediente, no
        cuatro copias. Se planea lo que aún no se produjo; está en ejecución
        mientras se produce o se corrige; pasa a evaluación cuando la unidad lo
        envía y la Dirección lo califica; y cae en mejora continua si no
        alcanza el mínimo o si no se entregó dentro del plazo.
        """
        hoy = hoy or timezone.localdate()
        if self.estado == 'validado':
            return 'mejora' if self.cumple is False else 'evaluacion'
        if self.recurso_id or self.estado == 'observado':
            return 'ejecucion'
        if self.vence_el and hoy > self.vence_el:
            return 'mejora'
        return 'planeacion'

    def semaforo(self, hoy=None):
        """validado · observado · por_validar · no_aplica · vencido · por_vencer · a_tiempo · no_abierto · sin_plazo.

        El documento ya archivado queda «por validar» aunque lo haya producido
        el sistema: archivarlo no es entregarlo, alguien tiene que darlo por
        bueno. Y mientras su ventana no se abre no se le reclama a nadie.
        """
        hoy = hoy or timezone.localdate()
        if self.estado == 'validado':
            return 'validado'
        if self.estado == 'observado':
            return 'observado'
        if self.estado == 'no_aplica':
            return 'no_aplica'
        if self.estado in ('cargado', 'generado') and self.recurso_id:
            return 'por_validar'
        if self.vence_el is None:
            return 'sin_plazo'
        if hoy > self.vence_el:
            return 'vencido'
        if self.abre_el and hoy < self.abre_el:
            return 'no_abierto'
        if (self.vence_el - hoy).days <= 7:
            return 'por_vencer'
        return 'a_tiempo'


class DocumentoElaborado(models.Model):
    """Lo que la unidad redacta con el editor guiado para un documento del expediente.

    El contenido es un diccionario por campo; lo que el sistema ya sabe (datos
    de la unidad, inventario, registros del período) no se guarda aquí: se lee
    al mostrar y al generar el PDF, para que nunca quede desactualizado.
    """

    documento = models.OneToOneField(DocumentoExpediente, on_delete=models.CASCADE, related_name='redaccion')
    contenido = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=0, help_text='Sube con cada guardado; evita pisar cambios ajenos.')
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_elaborados',
    )
    actualizado_en = models.DateTimeField(auto_now=True)
    generado_en = models.DateTimeField(null=True, blank=True)
    generado_version = models.PositiveIntegerField(null=True, blank=True, editable=False)

    class Meta:
        db_table = 'webcitt_documentoelaborado'
        verbose_name = 'Documento redactado con el editor'
        verbose_name_plural = 'Documentos redactados con el editor'

    def __str__(self):
        return f'Redacción de {self.documento}'

    @property
    def tipo(self):
        return self.documento.exigido.fuente_reporte
