"""Los cursos y capacitaciones que ofrece una unidad: su ficha de presentación y publicidad, y cada edición en que se
dicta. El contenido del curso se escribe una vez; cada edición (2026-I, 2026-II…) tiene sus fechas, su cupo y su
lugar, de modo que se sabe qué cursos se dictan cada año sin duplicar nada."""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.identificadores import youtube_id
from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.formacion.models.cursos_certificacion import CATEGORIAS_EVENTO, TIPOS_CERTIFICADO
from apps.formacion.models.enlaces_formacion import validar_enlace_formacion


def _lineas(texto):
    return [linea.strip() for linea in (texto or '').splitlines() if linea.strip()]


def _validar_curso_de_actividad(instancia):
    """Las lecciones compartidas por grupos siguen perteneciendo a un solo curso."""
    if (instancia.inscripcion_id and instancia.leccion_id and
            instancia.inscripcion.edicion.curso_id != instancia.leccion.modulo.curso_id):
        raise ValidationError({'leccion': 'La lección y la matrícula deben pertenecer al mismo curso.'})


class Curso(models.Model):
    CLASIFICACIONES = [
        ('corto', 'Curso corto'),
        ('largo', 'Curso largo'),
        ('taller', 'Taller'),
        ('capacitacion', 'Capacitación'),
        ('induccion', 'Inducción'),
        ('entrenamiento', 'Entrenamiento técnico'),
        ('webinar', 'Webinar'),
        ('seminario', 'Seminario'),
        ('conferencia', 'Conferencia'),
        ('congreso', 'Congreso'),
        ('jornada', 'Jornada'),
        ('encuentro', 'Encuentro'),
    ]
    MODALIDADES = [
        ('autoguiado', 'Autoguiado: a su ritmo, con textos, videos y materiales'),
        ('en_vivo', 'En vivo: con clases presenciales o virtuales'),
        ('mixto', 'Mixto: contenidos guiados y clases en vivo'),
    ]
    INSCRIPCIONES = [
        ('abierta', 'Abierta: quien se inscribe entra al momento, hasta llenar el cupo'),
        ('aprobacion', 'Con aprobación: la unidad revisa cada inscripción'),
    ]
    ORIGENES = [('nativo', 'En esta plataforma'), ('externo', 'Plataforma externa')]
    PARTICIPACIONES = [('organizador', 'Organizador'), ('coorganizador', 'Coorganizador'),
                      ('colaborador', 'Colaborador'), ('difusor', 'Difusión académica')]

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name='cursos', verbose_name='Unidad')
    codigo = models.CharField('Código', max_length=40, unique=True)
    nombre = models.CharField('Nombre del curso', max_length=160)
    lema = models.CharField('Frase de presentación', max_length=200, blank=True,
                            help_text='Una frase que invite a inscribirse; va bajo el nombre, en la portada.')
    clasificacion = models.CharField('Clasificación', max_length=16, choices=CLASIFICACIONES, default='corto')
    origen = models.CharField('Dónde se realiza', max_length=10, choices=ORIGENES, default='nativo')
    url_externa = models.URLField('Enlace de la actividad externa', max_length=1000, blank=True,
                                 validators=[validar_enlace_formacion])
    entidad_organizadora = models.CharField('Institución organizadora', max_length=200, blank=True)
    participacion_unidad = models.CharField('Participación de la unidad', max_length=14,
                                           choices=PARTICIPACIONES, default='organizador')
    modalidad = models.CharField('Modalidad', max_length=12, choices=MODALIDADES, default='autoguiado')
    descripcion = models.TextField('De qué trata', blank=True)
    aprendizajes = models.TextField('Qué aprenderás', blank=True, help_text='Un aprendizaje por línea.')
    dirigido_a = models.TextField('A quién va dirigido', blank=True)
    requisitos = models.TextField('Requisitos', blank=True, help_text='Un requisito por línea.')
    instructores = models.TextField('Instructores', blank=True,
                                    help_text='Uno por línea: «Nombre | lo que enseña o su cargo».')
    duracion_horas = models.PositiveSmallIntegerField('Duración (horas)', null=True, blank=True,
                                                      validators=[MinValueValidator(1), MaxValueValidator(2000)])
    imagen = models.ImageField('Imagen de portada', upload_to='cursos/', blank=True)
    video_url = models.URLField('Video promocional', blank=True, help_text='Enlace de YouTube.')
    costo = models.DecimalField('Costo (USD)', max_digits=8, decimal_places=2, null=True, blank=True,
                                validators=[MinValueValidator(0)], help_text='Vacío o 0: gratuito.')
    pago_transferencia = models.BooleanField('Acepta transferencia o depósito', default=True)
    pago_ventanilla = models.BooleanField('Acepta pago en ventanilla', default=False)
    pago_enlace = models.BooleanField('Acepta pago en línea', default=False)
    enlace_pago = models.URLField('Enlace de pago en línea', blank=True,
                                  help_text='La página de la pasarela o del botón de pago de la institución.')
    datos_pago = models.TextField('Datos para pagar', blank=True,
                                  help_text='Cuenta bancaria, beneficiario, ventanilla u otras instrucciones.')
    inscripcion = models.CharField('Inscripción', max_length=12, choices=INSCRIPCIONES, default='abierta')
    emite_certificado = models.BooleanField('Emite certificado', default=True,
                                            help_text='Al aprobar el curso se entrega un certificado verificable.')
    firma_nombre = models.CharField('Firma del certificado', max_length=160, blank=True,
                                    help_text='Quien firma. Vacío: la coordinación de la unidad.')
    firma_cargo = models.CharField('Cargo de quien firma', max_length=200, blank=True,
                                   help_text='Vacío: «Coordinación de» y el nombre de la unidad.')
    actividad_catalogo = models.ForeignKey(
        CatalogoActividadReserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos',
        verbose_name='Actividad del catálogo de reservas',
        help_text='La actividad con que se reservan sus clases en vivo; sus sesiones se muestran en el curso.')
    publicado = models.BooleanField('Publicado', default=False,
                                    help_text='Mientras no se publica, solo lo ve quien gestiona la unidad.')
    activo = models.BooleanField('Activo', default=True,
                                help_text='Desactiva la oferta sin borrar contenidos ni el historial de sus participantes.')
    orden = models.PositiveIntegerField('Orden', default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_curso'
        ordering = ('orden', 'nombre')
        verbose_name = 'Curso o capacitación'
        verbose_name_plural = 'Cursos y capacitaciones'
        indexes = [
            models.Index(fields=('unidad', 'publicado', 'activo', 'orden', 'nombre'),
                         name='curso_unidad_oferta_orden_idx'),
            models.Index(fields=('unidad', 'orden', 'nombre'), name='curso_unidad_orden_nombre_idx'),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.actividad_catalogo_id and self.actividad_catalogo.unidad_id not in (None, self.unidad_id):
            raise ValidationError({'actividad_catalogo': 'La actividad debe ser de la misma unidad.'})
        if self.es_externo:
            validar_enlace_formacion(self.url_externa)
            if self.publicado and (not self.url_externa or not self.entidad_organizadora.strip()):
                raise ValidationError('Para publicar una actividad externa indica su enlace y la institución organizadora.')
            self.validar_cambio_origen()

    @property
    def es_externo(self):
        return self.origen == 'externo'

    @property
    def url_externa_segura(self):
        """No expone un href inseguro aunque un importador omita full_clean()."""
        try:
            validar_enlace_formacion(self.url_externa)
        except ValidationError:
            return ''
        return self.url_externa

    def tiene_historial(self):
        """Incluye matrículas retiradas e invitaciones canceladas: también son evidencia."""
        if not self.pk:
            return False
        return (self.ediciones.filter(models.Q(inscripciones__isnull=False)
                | models.Q(participantes_evento__isnull=False)
                | models.Q(invitaciones__isnull=False)).exists()
                or self.modulos.filter(lecciones__comentarios__isnull=False).exists())

    def validar_cambio_origen(self):
        if (self.pk and self.es_externo
                and type(self).objects.filter(pk=self.pk, origen='nativo').exists()
                and self.tiene_historial()):
            raise ValidationError('Esta actividad tiene historial académico local. Conserva su origen y crea otra ficha para la oferta externa.')

    def validar_eliminacion(self):
        if self.tiene_historial():
            raise ValidationError('Esta actividad tiene participantes o evidencias. Desactívala para conservar su historial.')

    def save(self, *args, **kwargs):
        if (self.pk and self.es_externo
                and (kwargs.get('update_fields') is None or 'origen' in kwargs['update_fields'])):
            with transaction.atomic(using=kwargs.get('using') or self._state.db):
                type(self).objects.select_for_update().only('pk').get(pk=self.pk)
                self.validar_cambio_origen()
                list(self.ediciones.select_for_update().order_by('pk').values_list('pk', flat=True))
                self.validar_cambio_origen()
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic(using=kwargs.get('using') or self._state.db):
            type(self).objects.select_for_update().only('pk').get(pk=self.pk)
            self.validar_eliminacion()
            # La matrícula también bloquea la edición: no se comprueba el
            # historial mientras otra operación está incorporando participantes.
            list(self.ediciones.select_for_update().order_by('pk').values_list('pk', flat=True))
            self.validar_eliminacion()
            return super().delete(*args, **kwargs)

    @property
    def gratuito(self):
        return not self.costo

    @property
    def video_id(self):
        return youtube_id(self.video_url)

    @property
    def lista_aprendizajes(self):
        return _lineas(self.aprendizajes)

    @property
    def lista_requisitos(self):
        return _lineas(self.requisitos)

    @property
    def lista_instructores(self):
        return [{'nombre': nombre.strip(), 'rol': rol.strip()}
                for nombre, _, rol in (linea.partition('|') for linea in _lineas(self.instructores))]

    def edicion_vigente(self, hoy=None):
        """La edición que hoy importa: la que tiene inscripciones abiertas, si no la próxima, si no la que está en
        curso; si todas terminaron, la última."""
        hoy = hoy or timezone.localdate()
        ediciones = [edicion for edicion in self.ediciones.all() if edicion.activa]
        por_estado = {}
        for edicion in ediciones:
            por_estado.setdefault(edicion.estado(hoy)[0], []).append(edicion)
        fecha = lambda edicion: (edicion.inicio or date(edicion.anio, 1, 1), edicion.pk)  # noqa: E731
        if por_estado.get('inscripciones'):
            return min(por_estado['inscripciones'], key=fecha)
        if por_estado.get('proxima'):
            return min(por_estado['proxima'], key=fecha)
        if por_estado.get('en_curso'):
            return max(por_estado['en_curso'], key=fecha)
        return max(ediciones, key=lambda edicion: (edicion.fin or edicion.inicio or date(edicion.anio, 12, 31), edicion.pk),
                   default=None)


class EdicionCurso(models.Model):
    TIPOS_GRUPO = [('periodica', 'Por período o convocatoria'), ('a_medida', 'A medida para una organización')]

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='ediciones', verbose_name='Curso')
    nombre = models.CharField('Edición', max_length=60, help_text='Por ejemplo: «2026-I» o «Cohorte de verano 2026».')
    anio = models.PositiveSmallIntegerField('Año', validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    inicio = models.DateField('Empieza', null=True, blank=True)
    fin = models.DateField('Termina', null=True, blank=True)
    horas_certificadas = models.DecimalField('Horas reales que se certifican', max_digits=6, decimal_places=2,
                                            null=True, blank=True, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(2000)],
                                            help_text='Vacío: horas generales del certificado o duración del curso.')
    inscripciones_desde = models.DateField('Inscripciones desde', null=True, blank=True)
    inscripciones_hasta = models.DateField('Inscripciones hasta', null=True, blank=True,
                                           help_text='Vacío: hasta el día en que empieza.')
    cupo = models.PositiveSmallIntegerField('Cupo', null=True, blank=True, help_text='Vacío: sin límite.')
    horario = models.CharField('Horario', max_length=200, blank=True, help_text='Por ejemplo: «Martes y jueves, 15:00 a 17:00».')
    lugar = models.CharField('Lugar', max_length=200, blank=True, help_text='Un área de la unidad, un aula o «Virtual».')
    tipo_grupo = models.CharField('Tipo de grupo', max_length=12, choices=TIPOS_GRUPO, default='periodica')
    destinatario = models.CharField('Organización o destinatario', max_length=160, blank=True)
    activa = models.BooleanField('Se ofrece', default=True)

    class Meta:
        db_table = 'webcitt_edicioncurso'
        ordering = ('-anio', 'inicio', 'pk')
        verbose_name = 'Edición del curso'
        verbose_name_plural = 'Ediciones del curso'
        constraints = [models.UniqueConstraint(fields=('curso', 'nombre'), name='edicion_curso_unica')]

    def __str__(self):
        return f'{self.curso} · {self.nombre}'

    def clean(self):
        if self.curso_id and self.curso.es_externo:
            raise ValidationError('Las convocatorias de esta actividad se administran en la plataforma organizadora.')
        errores = {}
        if self.inicio and self.fin and self.fin < self.inicio:
            errores['fin'] = 'Termina antes de empezar.'
        if self.inscripciones_desde and self.inscripciones_hasta and self.inscripciones_hasta < self.inscripciones_desde:
            errores['inscripciones_hasta'] = 'Las inscripciones cierran antes de abrirse.'
        if self.inicio and self.anio and self.inicio.year != self.anio:
            errores['anio'] = f'Empieza en {self.inicio.year}: el año de la edición debe coincidir.'
        if errores:
            raise ValidationError(errores)

    def delete(self, *args, **kwargs):
        with transaction.atomic(using=kwargs.get('using') or self._state.db):
            Curso.objects.select_for_update().only('pk').get(pk=self.curso_id)
            self.validar_eliminacion()
            type(self).objects.select_for_update().only('pk').get(pk=self.pk)
            self.validar_eliminacion()
            return super().delete(*args, **kwargs)

    def validar_eliminacion(self):
        if (self.inscripciones.exists() or self.participantes_evento.exists()
                or self.invitaciones.exists()):
            raise ValidationError('Este grupo tiene participantes o invitaciones registradas. Desactívalo para conservar el historial.')

    def estado(self, hoy=None):
        """En qué momento está: (clave, texto). Las inscripciones cierran, si no se dice otra cosa, el día en que empieza
        (inclusive); con «Inscripciones hasta» posterior al inicio se aceptan inscripciones tardías. Una edición de un
        año ya pasado que no dice cuándo termina se da por finalizada."""
        hoy = hoy or timezone.localdate()
        if not self.activa:
            return 'suspendida', 'No se ofrece'
        if (self.fin and self.fin < hoy) or (not self.fin and self.anio < hoy.year):
            return 'finalizada', 'Finalizada'
        cierre = self.inscripciones_hasta or self.inicio
        if (not self.inscripciones_desde or self.inscripciones_desde <= hoy) and (not cierre or hoy <= cierre):
            return 'inscripciones', 'Inscripciones abiertas'
        if self.inicio and self.inicio <= hoy:
            return 'en_curso', 'En curso'
        if self.inscripciones_desde and hoy < self.inscripciones_desde:
            return 'proxima', f'Inscripciones desde el {self.inscripciones_desde:%d/%m/%Y}'
        return 'proxima', 'Por empezar'


# Lo que se sube como material de estudio: documentos, presentaciones, hojas, imágenes, audio, video y comprimidos.
EXTENSIONES_DE_MATERIAL = ('pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'odp', 'ods', 'txt', 'csv',
                           'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp3', 'mp4', 'webm', 'zip', 'stl', 'step', 'svg', 'dxf')
# Las direcciones de las reuniones de Microsoft Teams (cuentas institucionales y personales).
TEAMS = ('teams.microsoft.com', 'teams.live.com')


def ruta_material(instancia, nombre_original):
    """Fuera del alias público: el material solo se entrega desde el aula, a quien está inscrito."""
    curso = instancia.modulo.curso
    nombre = f'{slugify(instancia.titulo)[:60] or "material"}{Path(nombre_original).suffix.lower()}'
    return f'cursos/materiales/{curso.codigo}/{nombre}'


class ModuloCurso(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos', verbose_name='Curso')
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    titulo = models.CharField('Título del módulo', max_length=160)
    descripcion = models.TextField('Qué se ve en este módulo', blank=True)

    class Meta:
        db_table = 'webcitt_modulocurso'
        ordering = ('orden', 'pk')
        verbose_name = 'Módulo del curso'
        verbose_name_plural = 'Módulos del curso'

    def __str__(self):
        return f'{self.orden}. {self.titulo}'


class LeccionCurso(models.Model):
    TIPOS = [
        ('texto', 'Lectura: texto para leer'),
        ('video', 'Video'),
        ('material', 'Material de estudio: archivo o enlace'),
        ('en_vivo', 'Clase en vivo: presencial o virtual'),
        ('evaluacion', 'Evaluación: preguntas que se califican solas'),
        ('deber', 'Deber: una entrega que califica el instructor'),
    ]
    CALIFICADAS = ('evaluacion', 'deber')
    SALAS = [
        ('plataforma', 'Sala de la plataforma (videollamada dentro del aula)'),
        ('teams', 'Microsoft Teams transmitido por YouTube Live'),
        ('youtube', 'Transmisión por YouTube Live'),
        ('externa', 'Enlace externo: Zoom, Meet, Teams u otro'),
        ('presencial', 'Solo presencial'),
    ]

    modulo = models.ForeignKey(ModuloCurso, on_delete=models.CASCADE, related_name='lecciones', verbose_name='Módulo')
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    titulo = models.CharField('Título de la lección', max_length=160)
    tipo = models.CharField('Tipo', max_length=10, choices=TIPOS, default='texto')
    contenido = models.TextField('Contenido o explicación', blank=True)
    video_url = models.URLField('Video', blank=True, help_text='Enlace de YouTube.')
    archivo = models.FileField('Archivo', upload_to=ruta_material, blank=True,
                               validators=[FileExtensionValidator(EXTENSIONES_DE_MATERIAL)],
                               help_text='PDF, documentos, presentaciones, imágenes, audio, video o ZIP.')
    enlace = models.URLField('Enlace', blank=True,
                             help_text='Un material en línea o, en una clase virtual, el enlace de la reunión.')
    fecha_hora = models.DateTimeField('Fecha y hora de la clase', null=True, blank=True)
    lugar = models.CharField('Lugar de la clase', max_length=200, blank=True)
    sala = models.CharField(
        'Sala de la clase', max_length=12, choices=SALAS, default='plataforma', blank=True,
        help_text='En una clase en vivo: dónde se conecta cada persona. La sala de la plataforma se abre dentro del '
                  'aula; YouTube Live y el enlace externo usan el campo Enlace; Teams usa el enlace de la reunión y, en '
                  'Enlace, el de la transmisión de YouTube Live que se ve dentro del aula.')
    reunion_url = models.URLField('Reunión de Microsoft Teams', blank=True,
                                  help_text='En una clase por Teams: el enlace de la reunión, para quien quiera hablar o '
                                            'compartir pantalla con su cuenta institucional.')
    grabacion_id = models.CharField('Grabación en Digital Samba', max_length=64, blank=True, editable=False,
                                    help_text='La plataforma la trae al registrar la asistencia y la reproduce en la '
                                              'lección.')
    grabacion_url = models.URLField('Grabación de la clase', blank=True,
                                    help_text='BigBlueButton la completa sola. Con YouTube Live, la transmisión queda '
                                              'como grabación sin hacer nada; para usar la de Teams, pegue el enlace de '
                                              'Stream de «Compartir › Insertar».')
    duracion_min = models.PositiveSmallIntegerField('Duración (minutos)', null=True, blank=True,
                                                    validators=[MinValueValidator(1), MaxValueValidator(1440)])
    nota_minima = models.PositiveSmallIntegerField(
        'Nota mínima para aprobar (%)', default=70, validators=[MaxValueValidator(100)],
        help_text='En evaluaciones y deberes: el porcentaje que hay que alcanzar.')
    intentos = models.PositiveSmallIntegerField('Intentos permitidos', default=3,
                                                validators=[MinValueValidator(1), MaxValueValidator(20)],
                                                help_text='En evaluaciones: cuántas veces se puede rendir.')
    fecha_limite = models.DateTimeField('Fecha límite', null=True, blank=True,
                                        help_text='En evaluaciones y deberes; vacío, sin plazo.')
    obligatoria = models.BooleanField('Obligatoria para aprobar', default=True)
    publicada = models.BooleanField('Publicada', default=True,
                                    help_text='Sin publicar, los inscritos no la ven todavía.')

    class Meta:
        db_table = 'webcitt_leccioncurso'
        ordering = ('orden', 'pk')
        verbose_name = 'Lección del curso'
        verbose_name_plural = 'Lecciones del curso'

    def __str__(self):
        return self.titulo

    def clean(self):
        if self.tipo == 'video' and not self.video_id and not self.archivo:
            raise ValidationError({'video_url': 'Pegue el enlace de YouTube del video o suba el archivo.'})
        if self.tipo == 'material' and not self.archivo and not self.enlace:
            raise ValidationError({'archivo': 'Suba el archivo o escriba el enlace del material.'})
        # Sin sala elegida, la clase va en la sala de la plataforma.
        self.sala = self.sala or 'plataforma'
        if self.tipo == 'en_vivo' and self.sala in ('youtube', 'teams') and not youtube_id(self.enlace):
            raise ValidationError({'enlace': 'Pegue el enlace de la transmisión de YouTube Live.'})
        if self.tipo == 'en_vivo' and self.sala == 'teams' and urlparse(self.reunion_url).hostname not in TEAMS:
            raise ValidationError({'reunion_url': 'Pegue el enlace de la reunión de Microsoft Teams.'})
        if self.tipo == 'en_vivo' and self.sala == 'externa' and not self.enlace:
            raise ValidationError({'enlace': 'Escriba el enlace de la reunión (Zoom, Meet, Teams u otro).'})

    @property
    def video_id(self):
        return youtube_id(self.video_url)

    @property
    def transmision_id(self):
        """El identificador de la transmisión cuando la clase va por YouTube Live (sola o desde Teams)."""
        return youtube_id(self.enlace) if self.sala in ('youtube', 'teams') else ''

    @property
    def terminada(self):
        """La clase ya pasó: su hora más la duración prevista (dos horas si no se indicó)."""
        if not self.fecha_hora:
            return False
        return timezone.now() > self.fecha_hora + timedelta(minutes=self.duracion_min or 120)

    @property
    def grabacion_embebida(self):
        """La grabación que se ve dentro de la lección: un video de YouTube o una de Teams insertada desde Stream."""
        if youtube_id(self.grabacion_url):
            return f'https://www.youtube-nocookie.com/embed/{youtube_id(self.grabacion_url)}?rel=0'
        partes = urlparse(self.grabacion_url)
        if (partes.scheme == 'https' and (partes.hostname or '').endswith('.sharepoint.com')
                and partes.path.endswith('/embed.aspx')):
            return self.grabacion_url
        return ''

    @property
    def en_vivo(self):
        """Una clase en vivo se completa cuando la unidad registra la asistencia, no con un clic del inscrito."""
        return self.tipo == 'en_vivo'

    @property
    def calificada(self):
        """Una evaluación o un deber se completan al aprobarlos, no con un clic."""
        return self.tipo in self.CALIFICADAS

    def vencida(self, ahora=None):
        return bool(self.fecha_limite and (ahora or timezone.now()) > self.fecha_limite)


class InscripcionCurso(models.Model):
    ESTADOS = [
        ('pendiente', 'En revisión'),
        ('aceptada', 'Inscrito'),
        ('rechazada', 'No aceptada'),
        ('retirada', 'Retirado'),
    ]

    edicion = models.ForeignKey(EdicionCurso, on_delete=models.PROTECT, related_name='inscripciones',
                                verbose_name='Edición')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='inscripciones_curso',
                                verbose_name='Persona')
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS, default='pendiente')
    nombres_completos = models.CharField('Nombres completos de la matrícula', max_length=200, blank=True)
    documento = models.CharField('Cédula o documento de la matrícula', max_length=30, blank=True)
    fecha_inscripcion = models.DateTimeField('Se inscribió', auto_now_add=True)
    fecha_respuesta = models.DateTimeField('Respuesta de la unidad', null=True, blank=True)
    observacion = models.CharField('Observación', max_length=300, blank=True)

    class Meta:
        db_table = 'webcitt_inscripcioncurso'
        ordering = ('-fecha_inscripcion',)
        verbose_name = 'Inscripción a un curso'
        verbose_name_plural = 'Inscripciones a cursos'
        indexes = [models.Index(fields=('edicion', 'estado'), name='curso_insc_edicion_estado_idx')]
        constraints = [
            models.UniqueConstraint(fields=('edicion', 'usuario'), name='inscripcion_curso_unica'),
            models.UniqueConstraint(fields=('edicion', 'documento'), condition=~models.Q(documento=''),
                                    name='documento_unico_por_grupo_curso'),
        ]

    def __str__(self):
        return f'{self.usuario} · {self.edicion}'


class ProgresoLeccion(models.Model):
    inscripcion = models.ForeignKey(InscripcionCurso, on_delete=models.CASCADE, related_name='progresos',
                                    verbose_name='Inscripción')
    leccion = models.ForeignKey(LeccionCurso, on_delete=models.CASCADE, related_name='progresos', verbose_name='Lección')
    completada_en = models.DateTimeField('Completada', auto_now_add=True)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='+', verbose_name='Asistencia registrada por')

    class Meta:
        db_table = 'webcitt_progresoleccion'
        verbose_name = 'Lección completada'
        verbose_name_plural = 'Lecciones completadas'
        constraints = [models.UniqueConstraint(fields=('inscripcion', 'leccion'), name='progreso_leccion_unico')]

    def clean(self):
        super().clean()
        _validar_curso_de_actividad(self)


def _sin_tildes(texto):
    import unicodedata
    plano = unicodedata.normalize('NFKD', texto or '')
    return ' '.join(''.join(letra for letra in plano if not unicodedata.combining(letra)).lower().split())


class PreguntaEvaluacion(models.Model):
    TIPOS = [
        ('unica', 'Una respuesta correcta'),
        ('multiple', 'Varias respuestas correctas'),
        ('corta', 'Respuesta corta escrita'),
    ]

    leccion = models.ForeignKey(LeccionCurso, on_delete=models.CASCADE, related_name='preguntas',
                                verbose_name='Evaluación')
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    enunciado = models.TextField('Pregunta')
    tipo = models.CharField('Tipo de pregunta', max_length=10, choices=TIPOS, default='unica')
    opciones = models.TextField('Opciones', blank=True,
                                help_text='Una por línea; marque las correctas con * al inicio. Verdadero o falso: '
                                          '«*Verdadero» y «Falso».')
    respuestas_aceptadas = models.TextField('Respuestas aceptadas', blank=True,
                                            help_text='En respuesta corta: una por línea; no importan mayúsculas ni tildes.')
    puntos = models.PositiveSmallIntegerField('Puntos', default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])
    explicacion = models.TextField('Explicación', blank=True, help_text='Se muestra después de responder.')

    class Meta:
        db_table = 'webcitt_preguntaevaluacion'
        ordering = ('orden', 'pk')
        verbose_name = 'Pregunta de evaluación'
        verbose_name_plural = 'Preguntas de evaluación'

    def __str__(self):
        return self.enunciado[:80]

    @property
    def lista_opciones(self):
        """[(texto, es correcta)] en el orden escrito."""
        return [(linea.lstrip('*').strip(), linea.startswith('*')) for linea in _lineas(self.opciones)]

    def clean(self):
        if self.tipo == 'corta':
            if not _lineas(self.respuestas_aceptadas):
                raise ValidationError({'respuestas_aceptadas': 'Escriba al menos una respuesta aceptada.'})
            return
        opciones = self.lista_opciones
        correctas = sum(1 for _texto, correcta in opciones if correcta)
        if len(opciones) < 2:
            raise ValidationError({'opciones': 'Escriba al menos dos opciones, una por línea.'})
        if correctas == 0:
            raise ValidationError({'opciones': 'Marque con * al inicio la opción correcta.'})
        if self.tipo == 'unica' and correctas > 1:
            raise ValidationError({'opciones': 'Con una respuesta correcta, marque solo una opción con *.'})

    def es_correcta(self, respuesta):
        """La respuesta del formulario: índices elegidos (texto) o lo escrito."""
        if self.tipo == 'corta':
            escrita = _sin_tildes(respuesta[0] if respuesta else '')
            return bool(escrita) and escrita in {_sin_tildes(linea) for linea in _lineas(self.respuestas_aceptadas)}
        correctas = {str(indice) for indice, (_texto, correcta) in enumerate(self.lista_opciones) if correcta}
        return set(respuesta or ()) == correctas


class IntentoEvaluacion(models.Model):
    inscripcion = models.ForeignKey(InscripcionCurso, on_delete=models.CASCADE, related_name='intentos',
                                    verbose_name='Inscripción')
    leccion = models.ForeignKey(LeccionCurso, on_delete=models.CASCADE, related_name='intentos_rendidos',
                                verbose_name='Evaluación')
    respuestas = models.JSONField('Respuestas', default=dict)
    aciertos = models.JSONField('Aciertos por pregunta', default=dict)
    nota = models.DecimalField('Nota (%)', max_digits=5, decimal_places=2)
    aprobado = models.BooleanField('Aprobado', default=False)
    entregado_en = models.DateTimeField('Entregado', auto_now_add=True)

    class Meta:
        db_table = 'webcitt_intentoevaluacion'
        ordering = ('-entregado_en',)
        verbose_name = 'Intento de evaluación'
        verbose_name_plural = 'Intentos de evaluación'

    def __str__(self):
        return f'{self.inscripcion} · {self.leccion} · {self.nota}'

    def clean(self):
        super().clean()
        _validar_curso_de_actividad(self)


EXTENSIONES_DE_ENTREGA = EXTENSIONES_DE_MATERIAL + ('py', 'ino', 'c', 'cpp', 'json', 'gcode', '3mf', 'obj', 'fcstd',
                                                    'skp', 'blend', 'rar', '7z')


def ruta_entrega(instancia, nombre_original):
    """Fuera del alias público: solo la ven quien entrega y quien califica."""
    leccion = instancia.leccion
    persona = slugify(instancia.inscripcion.usuario.get_username())[:40] or 'persona'
    return (f'cursos/entregas/{leccion.modulo.curso.codigo}/{leccion.pk}/'
            f'{persona}-{timezone.now():%Y%m%d%H%M%S}{Path(nombre_original).suffix.lower()}')


class EntregaDeber(models.Model):
    ESTADOS = [
        ('entregada', 'Por revisar'),
        ('aprobada', 'Aprobada'),
        ('devuelta', 'Devuelta para corregir'),
    ]

    inscripcion = models.ForeignKey(InscripcionCurso, on_delete=models.CASCADE, related_name='entregas',
                                    verbose_name='Inscripción')
    leccion = models.ForeignKey(LeccionCurso, on_delete=models.CASCADE, related_name='entregas', verbose_name='Deber')
    archivo = models.FileField('Archivo', upload_to=ruta_entrega, blank=True,
                               validators=[FileExtensionValidator(EXTENSIONES_DE_ENTREGA)])
    enlace = models.URLField('Enlace', blank=True, help_text='Si el trabajo está en línea.')
    comentario = models.TextField('Comentario para el instructor', blank=True)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS, default='entregada')
    entregada_en = models.DateTimeField('Entregada', default=timezone.now)
    nota = models.DecimalField('Nota (%)', max_digits=5, decimal_places=2, null=True, blank=True,
                               validators=[MinValueValidator(0), MaxValueValidator(100)])
    retroalimentacion = models.TextField('Retroalimentación', blank=True)
    calificada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='+', verbose_name='Calificada por')
    calificada_en = models.DateTimeField('Calificada', null=True, blank=True)

    class Meta:
        db_table = 'webcitt_entregadeber'
        ordering = ('entregada_en',)
        verbose_name = 'Entrega de deber'
        verbose_name_plural = 'Entregas de deberes'
        constraints = [models.UniqueConstraint(fields=('inscripcion', 'leccion'), name='entrega_deber_unica')]

    def __str__(self):
        return f'{self.inscripcion} · {self.leccion}'

    def clean(self):
        super().clean()
        _validar_curso_de_actividad(self)

    @property
    def tardia(self):
        return bool(self.leccion.fecha_limite and self.entregada_en > self.leccion.fecha_limite)


class ParticipanteEvento(models.Model):
    """Identidad acreditada en una edición de evento, sin crear una cuenta de acceso."""
    edicion = models.ForeignKey(EdicionCurso, on_delete=models.PROTECT, related_name='participantes_evento')
    documento = models.CharField('Cédula o documento de identidad', max_length=30)
    nombres_completos = models.CharField('Nombres y apellidos completos', max_length=200)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_participanteevento'
        ordering = ('nombres_completos', 'pk')
        constraints = [models.UniqueConstraint(fields=('edicion', 'documento'), name='participante_evento_documento_unico')]

    def clean(self):
        from apps.core.models.datos_matricula import validar_datos_matricula
        datos = validar_datos_matricula(documento=self.documento, nombres_completos=self.nombres_completos)
        self.documento, self.nombres_completos = datos['documento'], datos['nombres_completos']

    def __str__(self):
        return self.nombres_completos


class CertificadoCurso(models.Model):
    """Lo que certifica, guardado tal como era el día de la emisión: el PDF se rehace igual cada vez. Una inscripción
    tiene a lo sumo un certificado vigente; si la unidad anula uno, puede emitir otro corregido."""
    TIPOS = TIPOS_CERTIFICADO

    inscripcion = models.ForeignKey(InscripcionCurso, on_delete=models.PROTECT, related_name='certificados', null=True, blank=True,
                                    verbose_name='Inscripción')
    participante_evento = models.ForeignKey(ParticipanteEvento, on_delete=models.PROTECT, related_name='certificados',
                                            null=True, blank=True, verbose_name='Participante externo del evento')
    codigo = models.CharField('Código de verificación', max_length=20, unique=True)
    tipo = models.CharField('Tipo', max_length=14, choices=TIPOS, default='aprobacion')
    nombre = models.CharField('Otorgado a', max_length=200)
    documento = models.CharField('Documento de identidad', max_length=30, blank=True)
    curso_nombre = models.CharField('Curso', max_length=160)
    clasificacion = models.CharField('Clasificación', max_length=60)
    horas = models.DecimalField('Horas', max_digits=6, decimal_places=2, null=True, blank=True,
                               validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(2000)])
    categoria_evento = models.CharField('Tipo de actividad al emitir', max_length=24, choices=CATEGORIAS_EVENTO, blank=True)
    fecha_inicio = models.DateField('Inicio de la actividad', null=True, blank=True)
    fecha_fin = models.DateField('Fin de la actividad', null=True, blank=True)
    emision_manual = models.BooleanField('Acreditación manual', default=False)
    emitido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='+', verbose_name='Emisión autorizada por')
    motivo_emision = models.CharField('Constancia de la acreditación manual', max_length=300, blank=True)
    edicion = models.CharField('Edición', max_length=60)
    unidad_nombre = models.CharField('Unidad', max_length=200)
    nota_final = models.DecimalField('Calificación final (%)', max_digits=5, decimal_places=2, null=True, blank=True)
    firma_nombre = models.CharField('Firma', max_length=160, blank=True)
    firma_cargo = models.CharField('Cargo de quien firma', max_length=200, blank=True)
    diseno_certificado = models.JSONField('Diseño y contenido al emitir', default=dict, blank=True)
    emitido_en = models.DateTimeField('Emitido', default=timezone.now)
    anulado = models.BooleanField('Anulado', default=False)
    motivo_anulacion = models.CharField('Motivo de la anulación', max_length=300, blank=True)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+', verbose_name='Anulado por')
    anulado_en = models.DateTimeField('Anulado', null=True, blank=True)

    class Meta:
        db_table = 'webcitt_certificadocurso'
        ordering = ('-emitido_en',)
        verbose_name = 'Certificado de curso'
        verbose_name_plural = 'Certificados de cursos'
        constraints = [models.UniqueConstraint(fields=('inscripcion',), condition=models.Q(anulado=False),
                                               name='un_certificado_vigente_por_inscripcion'),
                       models.UniqueConstraint(fields=('participante_evento',), condition=models.Q(anulado=False),
                                               name='certificado_vigente_por_externo'),
                       models.CheckConstraint(condition=(
                           models.Q(inscripcion__isnull=False, participante_evento__isnull=True) |
                           models.Q(inscripcion__isnull=True, participante_evento__isnull=False)),
                           name='certificado_exactamente_una_identidad')]

    @property
    def edicion_origen(self):
        persona = self.inscripcion if self.inscripcion_id else self.participante_evento
        return persona.edicion if persona else None

    @property
    def curso_origen(self):
        edicion = self.edicion_origen
        return edicion.curso if edicion else None

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'


class ComentarioLeccion(models.Model):
    """Una pregunta o un aporte en una lección, y las respuestas que recibe, para quien está en el aula."""
    leccion = models.ForeignKey(LeccionCurso, on_delete=models.CASCADE, related_name='comentarios', verbose_name='Lección')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comentarios_curso',
                                verbose_name='Autor')
    respuesta_a = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='respuestas',
                                    verbose_name='Responde a')
    texto = models.TextField('Comentario', max_length=2000)
    creado = models.DateTimeField('Publicado', auto_now_add=True)
    oculto = models.BooleanField('Oculto por la unidad', default=False)

    class Meta:
        db_table = 'webcitt_comentarioleccion'
        ordering = ('creado',)
        verbose_name = 'Comentario de lección'
        verbose_name_plural = 'Comentarios de lecciones'

    def __str__(self):
        return f'{self.usuario} · {self.texto[:60]}'

    def clean(self):
        super().clean()
        if self.respuesta_a_id and self.leccion_id and self.respuesta_a.leccion_id != self.leccion_id:
            raise ValidationError({'respuesta_a': 'La respuesta y su comentario original deben pertenecer a la misma lección.'})


class VotoComentario(models.Model):
    """Un «Me gusta» a un comentario de lección: uno por persona; los más votados suben en la lista."""
    comentario = models.ForeignKey(ComentarioLeccion, on_delete=models.CASCADE, related_name='me_gusta',
                                   verbose_name='Comentario')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votos_comentario',
                                verbose_name='Quién vota')
    creado = models.DateTimeField('Votó', auto_now_add=True)

    class Meta:
        db_table = 'webcitt_votocomentario'
        verbose_name = 'Voto a un comentario'
        verbose_name_plural = 'Votos a comentarios'
        constraints = [
            models.UniqueConstraint(fields=('comentario', 'usuario'), name='un_voto_por_persona_y_comentario'),
        ]

    def __str__(self):
        return f'{self.usuario} · {self.comentario_id}'


class ServidorClasesEnVivo(models.Model):
    """El servicio donde se abren las clases en vivo dentro del aula: Digital Samba o Daily en la nube, sin instalar
    nada, o un servidor de BigBlueButton propio o contratado. Hay un solo registro para toda la plataforma."""
    PROVEEDORES = [
        ('samba', 'Digital Samba: videollamada en la nube, gratis y sin tarjeta'),
        ('daily', 'Daily: videollamada en la nube; pide registrar una tarjeta'),
        ('bbb', 'BigBlueButton: servidor propio o de un proveedor'),
    ]
    ALGORITMOS = [('sha256', 'SHA-256'), ('sha1', 'SHA-1')]

    proveedor = models.CharField('Servicio', max_length=10, choices=PROVEEDORES, default='samba')
    samba_equipo = models.CharField('Team ID de Digital Samba', max_length=64, blank=True)
    samba_clave = models.CharField('Developer key de Digital Samba', max_length=200, blank=True)
    samba_dominio = models.CharField('Dominio de Digital Samba', max_length=120, blank=True,
                                     help_text='Se completa solo al guardar (por ejemplo laboratorios.digitalsamba.com).')
    daily_api_key = models.CharField('Clave de la API de Daily', max_length=200, blank=True)
    daily_dominio = models.CharField('Dominio de Daily', max_length=120, blank=True,
                                     help_text='Se completa solo al guardar la clave (por ejemplo upec.daily.co).')
    bbb_url = models.URLField('Dirección de la API de BigBlueButton', blank=True)
    bbb_secreto = models.CharField('Secreto de BigBlueButton', max_length=200, blank=True)
    bbb_checksum = models.CharField('Firma de BigBlueButton', max_length=6, choices=ALGORITMOS, default='sha256')
    actualizado = models.DateTimeField('Actualizado', auto_now=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='+', verbose_name='Actualizado por')

    class Meta:
        db_table = 'webcitt_servidorclasesenvivo'
        verbose_name = 'Servidor de clases en vivo'
        verbose_name_plural = 'Servidor de clases en vivo'

    def __str__(self):
        return self.get_proveedor_display()

    @property
    def listo(self):
        """Tiene lo que su servicio necesita para abrir salas."""
        if self.proveedor == 'samba':
            return bool(self.samba_equipo and self.samba_clave)
        if self.proveedor == 'daily':
            return bool(self.daily_api_key)
        return bool(self.bbb_url and self.bbb_secreto)
