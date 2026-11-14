"""Configuración del certificado; sus cambios solo afectan emisiones futuras."""
import re
from decimal import Decimal
from string import Formatter
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

DISENOS_CERTIFICADO = [('clasico', 'Clásico institucional'), ('sobrio', 'Sobrio'),
                       ('tecnologico', 'Tecnológico'), ('geometrico', 'Geométrico'),
                       ('elegante', 'Elegante'), ('congreso', 'Congreso'),
                       ('industrial', 'Industrial · laboratorio'), ('circuitos', 'Circuitos · innovación'),
                       ('horizonte', 'Horizonte · fotografía'), ('editorial', 'Editorial · contenidos'),
                       ('academico', 'Académico · reconocimiento'), ('inmersivo', 'Inmersivo · tecnología'),
                       ('ia_particulas', 'Inteligencia artificial · partículas'), ('red_cientifica', 'Red científica · conexiones'),
                       ('poligonos_digitales', 'Polígonos digitales'), ('ondas_tecnologicas', 'Ondas tecnológicas'),
                       ('formacion_lateral', 'Formación lateral · competencias')]
CATEGORIAS_EVENTO = [('curso', 'Curso'), ('taller', 'Taller'), ('webinar', 'Webinar'),
                     ('seminario', 'Seminario'), ('congreso', 'Congreso'),
                     ('evento_cientifico', 'Evento científico'), ('jornada', 'Jornada'),
                     ('capacitacion', 'Capacitación'), ('induccion', 'Inducción'),
                     ('entrenamiento', 'Entrenamiento técnico')]
TIPOS_CERTIFICADO = [('aprobacion', 'Certificado de aprobación'),
                     ('participacion', 'Certificado de participación'),
                     ('asistencia', 'Participación por asistencia'),
                     ('ponente', 'Participación como ponente'),
                     ('organizador', 'Participación en la organización')]
POSICIONES_LOGO = [('auto', 'Automática'), ('izquierda', 'Izquierda'),
                    ('centro', 'Centro'), ('derecha', 'Derecha')]
CONTRASTES_LOGO = [('auto', 'Automático según el fondo'), ('original', 'Conservar original'),
                    ('oscuro', 'Oscuro para fondo claro'), ('claro', 'Claro para fondo oscuro')]
VARIABLES_CERTIFICADO = ('nombre', 'curso', 'horas', 'edicion', 'unidad', 'fecha', 'tipo',
                         'fecha_inicio', 'fecha_fin', 'categoria_evento', 'rol', 'periodo', 'fecha_emision', 'emisor', 'organizadores')
TEXTO_APROBACION = ('Aprobó satisfactoriamente «{curso}» ({tipo}), con una duración de {horas} horas. '
                    'La actividad se desarrolló {periodo}, bajo la organización de {organizadores}.')
TEXTO_PARTICIPACION = ('Participó y completó «{curso}» ({tipo}), con una duración de {horas} horas. '
                       'La actividad se desarrolló {periodo}, bajo la organización de {organizadores}.')
TEXTO_ASISTENCIA = ('Asistió a «{curso}» ({tipo}), con una duración acreditada de {horas} horas. '
                    'La actividad se desarrolló {periodo}, bajo la organización de {organizadores}.')
TEXTO_PONENTE = ('Participó en calidad de ponente en «{curso}» ({tipo}), con una duración acreditada de {horas} horas. '
                 'La actividad se desarrolló {periodo}, bajo la organización de {organizadores}.')
TEXTO_ORGANIZADOR = ('Participó en la organización de «{curso}» ({tipo}), con una duración acreditada de {horas} horas. '
                      'La actividad se desarrolló {periodo}, bajo la organización de {organizadores}.')
IMAGENES_CERTIFICADO = ('firma_imagen', 'segunda_firma_imagen', 'tercera_firma_imagen',
                         'logo_1_imagen', 'logo_2_imagen', 'logo_3_imagen', 'logo_4_imagen', 'foto_alusiva', 'imagen_fondo')


def validar_texto_certificado(valor):
    if any(ord(c) < 32 and c not in '\r\n\t' for c in valor) or '<' in valor or '>' in valor:
        raise ValidationError('Use texto normal, sin HTML ni caracteres de control.')
    try:
        for _, campo, formato, conversion in Formatter().parse(valor):
            if campo is not None and (campo not in VARIABLES_CERTIFICADO or formato or conversion):
                raise ValueError
    except ValueError:
        raise ValidationError('Variable no permitida o llaves incompletas. Use: ' +
                              ', '.join('{' + nombre + '}' for nombre in VARIABLES_CERTIFICADO) + '.')


def ruta_firma_certificado(instance, nombre):
    # Medios privados: solo se dibujan dentro del PDF autorizado.
    return f'cursos/materiales/firmas_certificados/{uuid4().hex}.png'


def ruta_logo_certificado(instance, nombre):
    return f'cursos/materiales/logos_certificados/{uuid4().hex}.png'


def ruta_foto_certificado(instance, nombre):
    return f'cursos/materiales/fotos_certificados/{uuid4().hex}.png'


def ruta_fondo_certificado(instance, nombre):
    return f'cursos/materiales/fondos_certificados/{uuid4().hex}.png'


class ConfiguracionCertificadoCurso(models.Model):
    curso = models.OneToOneField('formacion.Curso', on_delete=models.CASCADE,
                                related_name='configuracion_certificado')
    emisor = models.CharField('Organizador o unidad emisora', max_length=200, blank=True,
                              help_text='Laboratorio u organizador responsable. Se prellena desde la unidad; no supone un aval externo.')
    mostrar_facultad = models.BooleanField('Incluir facultad', default=False)
    facultad_nombre = models.CharField('Nombre de la facultad', max_length=220, blank=True,
                                       help_text='Se sugiere la facultad registrada en la unidad. Confirme el nombre real antes de incluirla.')
    mostrar_carrera = models.BooleanField('Incluir carrera', default=False)
    carrera_nombre = models.CharField('Nombre de la carrera', max_length=220, blank=True,
                                      help_text='Se sugiere sólo si la unidad tiene una carrera inequívoca; no se atribuye una carrera automáticamente.')
    entradilla = models.CharField('Frase de otorgamiento', max_length=160, default='Otorga el presente certificado a',
                                  validators=[validar_texto_certificado])
    categoria_evento = models.CharField('Tipo de actividad', max_length=24, choices=CATEGORIAS_EVENTO, default='curso')
    tipo_certificado = models.CharField('Certificado al completar', max_length=14, default='auto',
                                       choices=[('auto', 'Automático según los requisitos')] + TIPOS_CERTIFICADO[:3],
                                       help_text='Aprobación exige evaluaciones o trabajos aprobados. Ponentes y organizadores se acreditan manualmente.')
    fecha_inicio = models.DateField('Fecha inicial general', null=True, blank=True,
                                   help_text='Se usa si el grupo no tiene fecha de inicio.')
    fecha_fin = models.DateField('Fecha final general', null=True, blank=True,
                                help_text='Se usa si el grupo no tiene fecha final.')
    horas_certificadas = models.DecimalField('Horas generales que se certifican', max_digits=6, decimal_places=2,
                                            null=True, blank=True, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(2000)],
                                            help_text='Prevalecen las horas del grupo; vacío: duración del curso.')
    titulo_aprobacion = models.CharField('Título de aprobación', max_length=96,
                                        default='CERTIFICADO DE APROBACIÓN', validators=[validar_texto_certificado])
    titulo_participacion = models.CharField('Título de participación', max_length=96,
                                           default='CERTIFICADO DE PARTICIPACIÓN', validators=[validar_texto_certificado])
    titulo_asistencia = models.CharField('Título por asistencia', max_length=96,
                                        default='CERTIFICADO DE PARTICIPACIÓN', validators=[validar_texto_certificado])
    titulo_ponente = models.CharField('Título para ponentes', max_length=96,
                                     default='CERTIFICADO DE PARTICIPACIÓN', validators=[validar_texto_certificado])
    titulo_organizador = models.CharField('Título para organizadores', max_length=96,
                                         default='CERTIFICADO DE PARTICIPACIÓN', validators=[validar_texto_certificado])
    texto_aprobacion = models.TextField('Texto de aprobación', max_length=700, default=TEXTO_APROBACION,
                                       validators=[validar_texto_certificado])
    texto_participacion = models.TextField('Texto de participación', max_length=700, default=TEXTO_PARTICIPACION,
                                          validators=[validar_texto_certificado])
    texto_asistencia = models.TextField('Texto por asistencia', max_length=700, default=TEXTO_ASISTENCIA,
                                       validators=[validar_texto_certificado])
    texto_ponente = models.TextField('Texto para ponentes', max_length=700, default=TEXTO_PONENTE,
                                    validators=[validar_texto_certificado])
    texto_organizador = models.TextField('Texto para organizadores', max_length=700, default=TEXTO_ORGANIZADOR,
                                        validators=[validar_texto_certificado])
    diseno = models.CharField('Diseño', max_length=20, default='clasico', choices=DISENOS_CERTIFICADO)
    tema_fondo = models.CharField('Tema visual del fondo', max_length=16, default='auto',
                                  choices=[('auto', 'Automático según la actividad'), ('ia_datos', 'Inteligencia artificial y datos'),
                                           ('robotica', 'Robótica y fabricación'), ('redes', 'Redes y conexiones'),
                                           ('investigacion', 'Investigación científica'), ('sostenibilidad', 'Sostenibilidad')])
    modo_fondo = models.CharField('Apariencia del fondo', max_length=8, default='auto',
                                  choices=[('auto', 'Automática según el diseño'), ('claro', 'Claro'), ('oscuro', 'Oscuro')])
    intensidad_fondo = models.CharField('Intensidad de la decoración', max_length=8, default='media',
                                        choices=[('discreta', 'Discreta'), ('media', 'Media'), ('alta', 'Alta')],
                                        help_text='Las zonas de lectura conservan contraste incluso con intensidad alta.')
    imagen_fondo = models.ImageField('Imagen propia de fondo', upload_to=ruta_fondo_certificado, blank=True,
                                     help_text='Imagen propia o autorizada. PNG o JPEG, hasta 2 MB; se protege el texto y las firmas.')
    encuadre_fondo = models.CharField('Encuadre de la imagen de fondo', max_length=12, default='centro',
                                      choices=[('centro', 'Centrado'), ('superior', 'Parte superior'), ('inferior', 'Parte inferior'),
                                               ('izquierda', 'Lado izquierdo'), ('derecha', 'Lado derecho')])
    alineacion_contenido = models.CharField('Alineación del contenido', max_length=12, default='centro',
                                          choices=[('centro', 'Centrado'), ('izquierda', 'A la izquierda')])
    formato_contenido = models.CharField('Organización del contenido', max_length=16, default='institucional',
                                        choices=[('breve', 'Texto breve'), ('institucional', 'Bloque institucional'),
                                                 ('competencias', 'Texto y competencias o logros')])
    subtitulo = models.CharField('Subtítulo opcional', max_length=180, blank=True, validators=[validar_texto_certificado])
    competencias = models.TextField('Competencias o logros', max_length=600, blank=True,
                                    validators=[validar_texto_certificado],
                                    help_text='Una competencia por línea, hasta seis. Sólo aparece en el formato de competencias.')
    foto_alusiva = models.ImageField('Fotografía alusiva', upload_to=ruta_foto_certificado, blank=True,
                                     help_text='Fotografía propia o autorizada del laboratorio. PNG o JPEG, hasta 2 MB.')
    usar_foto_unidad = models.BooleanField('Usar la fotografía de la unidad', default=True,
                                           help_text='Se usa cuando no carga una fotografía específica y la unidad tiene una imagen propia.')
    color_primario = models.CharField('Color principal', max_length=7, blank=True,
                                     validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Use un color como #1E5A3D.')],
                                     help_text='Vacío: color institucional.')
    color_acento = models.CharField('Color de acento', max_length=7, blank=True,
                                   validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Use un color como #E1B93F.')],
                                   help_text='Vacío: acento institucional.')
    color_texto = models.CharField('Color del texto', max_length=7, blank=True,
                                   validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Use un color como #263D33.')],
                                   help_text='Vacío: texto automático con contraste. Se aplica al contenido y las firmas.')
    color_titulos = models.CharField('Color de títulos y nombres', max_length=7, blank=True,
                                     validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Use un color como #006633.')],
                                     help_text='Vacío: color institucional o blanco sobre fondo oscuro.')
    tipografia = models.CharField('Tipografía del certificado', max_length=12, default='poppins',
                                  choices=[('poppins', 'Poppins · tecnológica'), ('nunito', 'Nunito · institucional'),
                                           ('clasica', 'Clásica · serif')])
    mostrar_pie_tecnologico = models.BooleanField('Incluir pie tecnológico', default=False)
    estilo_pie_tecnologico = models.CharField('Estilo del pie tecnológico', max_length=16, default='circuitos',
                                             choices=[('circuitos', 'Circuitos y conexiones'), ('fabricacion', 'Fabricación e innovación'),
                                                      ('calidad', 'Calidad y formación')],
                                             help_text='Ornamento opcional bajo las firmas, sin representar sellos de acreditación.')
    mostrar_nota = models.BooleanField('Mostrar calificación en diseños anteriores', default=False,
                                      help_text='Campo de compatibilidad. Los certificados nuevos no muestran calificaciones.')
    disposicion_logos = models.CharField('Distribución de logos', max_length=16, default='auto',
                                         choices=POSICIONES_LOGO + [('entre_extremos', 'Distribuidos entre extremos')])
    logo_1_nombre = models.CharField('Nombre de la institución aliada 1', max_length=160, blank=True,
                                       help_text='Nombre real del organizador o aliado. Puede incluirse sin logo.')
    logo_1_contraste = models.CharField('Contraste del logo aliado 1', max_length=8, default='auto', choices=CONTRASTES_LOGO)
    logo_1_imagen = models.ImageField('Logo de la institución aliada 1', upload_to=ruta_logo_certificado, blank=True)
    logo_1_posicion = models.CharField('Posición del primer logo', max_length=12, default='auto', choices=POSICIONES_LOGO)
    logo_2_nombre = models.CharField('Nombre de la institución aliada 2', max_length=160, blank=True,
                                       help_text='Nombre real del organizador o aliado. Puede incluirse sin logo.')
    logo_2_contraste = models.CharField('Contraste del logo aliado 2', max_length=8, default='auto', choices=CONTRASTES_LOGO)
    logo_2_imagen = models.ImageField('Logo de la institución aliada 2', upload_to=ruta_logo_certificado, blank=True)
    logo_2_posicion = models.CharField('Posición del segundo logo', max_length=12, default='auto', choices=POSICIONES_LOGO)
    logo_3_nombre = models.CharField('Nombre de la institución aliada 3', max_length=160, blank=True,
                                       help_text='Nombre real del organizador o aliado. Puede incluirse sin logo.')
    logo_3_contraste = models.CharField('Contraste del logo aliado 3', max_length=8, default='auto', choices=CONTRASTES_LOGO)
    logo_3_imagen = models.ImageField('Logo de la institución aliada 3', upload_to=ruta_logo_certificado, blank=True)
    logo_3_posicion = models.CharField('Posición del tercer logo', max_length=12, default='auto', choices=POSICIONES_LOGO)
    logo_4_nombre = models.CharField('Nombre de la institución aliada 4', max_length=160, blank=True,
                                       help_text='Nombre real del organizador o aliado. Puede incluirse sin logo.')
    logo_4_contraste = models.CharField('Contraste del logo aliado 4', max_length=8, default='auto', choices=CONTRASTES_LOGO)
    logo_4_imagen = models.ImageField('Logo de la institución aliada 4', upload_to=ruta_logo_certificado, blank=True)
    logo_4_posicion = models.CharField('Posición del cuarto logo', max_length=12, default='auto', choices=POSICIONES_LOGO)
    usar_firmante_curso = models.BooleanField('Usar el firmante del curso si el nombre está vacío', default=True,
                                              help_text='Desactívalo para dejar la firma pendiente sin heredar la coordinación.')
    firma_nombre = models.CharField('Primer firmante', max_length=160, blank=True,
                                   help_text='Nombre completo de la persona que firmará el certificado.')
    firma_cargo = models.CharField('Cargo del primer firmante', max_length=200, blank=True)
    firma_imagen = models.ImageField('Imagen de la primera firma', upload_to=ruta_firma_certificado, blank=True)
    segunda_firma_nombre = models.CharField('Segundo firmante', max_length=160, blank=True)
    segunda_firma_cargo = models.CharField('Cargo del segundo firmante', max_length=200, blank=True)
    segunda_firma_imagen = models.ImageField('Imagen de la segunda firma', upload_to=ruta_firma_certificado, blank=True)
    tercera_firma_nombre = models.CharField('Tercer firmante', max_length=160, blank=True)
    tercera_firma_cargo = models.CharField('Cargo del tercer firmante', max_length=200, blank=True)
    tercera_firma_imagen = models.ImageField('Imagen de la tercera firma', upload_to=ruta_firma_certificado, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'webcitt_configuracioncertificadocurso'
        verbose_name = 'Diseño de certificado de curso'
        verbose_name_plural = 'Diseños de certificados de cursos'

    def clean(self):
        super().clean()
        for campo in ('emisor', 'facultad_nombre', 'carrera_nombre', 'logo_1_nombre', 'logo_2_nombre',
                      'logo_3_nombre', 'logo_4_nombre', 'firma_nombre', 'firma_cargo', 'segunda_firma_nombre', 'segunda_firma_cargo',
                      'tercera_firma_nombre', 'tercera_firma_cargo'):
            valor = getattr(self, campo, '')
            if '<' in valor or '>' in valor or re.search(r'[\x00-\x08\x0b-\x1f]', valor):
                raise ValidationError({campo: 'Use texto normal, sin HTML ni caracteres de control.'})
        try:
            validar_texto_certificado(self.emisor)
        except ValidationError as exc:
            raise ValidationError({'emisor': exc.messages}) from exc
        for campo in ('facultad', 'carrera'):
            if getattr(self, 'mostrar_' + campo) and not getattr(self, campo + '_nombre').strip():
                raise ValidationError({campo + '_nombre': 'Escriba el nombre real o desactive esta opción.'})
        if len([linea for linea in self.competencias.splitlines() if linea.strip()]) > 6:
            raise ValidationError({'competencias': 'Incluya como máximo seis competencias o logros.'})
        if self.formato_contenido == 'competencias' and not self.competencias.strip():
            raise ValidationError({'competencias': 'Añada las competencias o elija otro formato de contenido.'})
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha final no puede ser anterior a la inicial.'})
        if re.fullmatch(r'#[0-9a-fA-F]{6}', self.color_primario or ''):
            componentes = [int(self.color_primario[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            lineales = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in componentes]
            luminancia = sum(c * peso for c, peso in zip(lineales, (.2126, .7152, .0722)))
            if 1.05 / (luminancia + .05) < 4.5:
                raise ValidationError({'color_primario': 'Elija un color principal más oscuro para que el texto y el logo sean legibles.'})
        if not self.usar_firmante_curso and (self.firma_cargo or self.firma_imagen) and not self.firma_nombre.strip():
            raise ValidationError({'firma_nombre': 'Escriba el nombre del primer firmante o deje la firma pendiente sin cargo ni imagen.'})
        for prefijo, ordinal in (('segunda_firma', 'segundo'), ('tercera_firma', 'tercer')):
            if (getattr(self, prefijo + '_cargo') or getattr(self, prefijo + '_imagen')) and not getattr(self, prefijo + '_nombre').strip():
                raise ValidationError({prefijo + '_nombre': f'Escriba el nombre del {ordinal} firmante.'})

    def __str__(self):
        return f'Certificado · {self.curso.nombre}'
