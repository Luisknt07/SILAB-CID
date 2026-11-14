
from apps.core.presentation.catalogos import tipos_usuario
from apps.core.presentation.niveles import niveles

from apps.core.presentation.catalogos import carreras, facultades

import re
from pathlib import Path
from datetime import datetime

from django.db import models, router, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico
from apps.reservas.workflows.reservas import RESERVA_ESTADO_CHOICES, validar_accion_reserva
# Import lazy para evitar imports circulares


PROPOSITO_INSTITUCIONAL_CHOICES = [
    ('docencia_practica', 'Docencia y práctica curricular'),
    ('investigacion_innovacion', 'Investigación, desarrollo e innovación'),
    ('vinculacion', 'Vinculación con la sociedad'),
    ('capacitacion', 'Capacitación y educación continua'),
    ('servicio_cientifico_tecnologico', 'Servicio científico-tecnológico'),
    ('titulacion', 'Trabajo de titulación'),
    ('otro', 'Otro propósito institucional'),
]

SUBTIPO_ACTIVIDAD_CHOICES = [
    ('practica_curricular', 'Práctica curricular de laboratorio'),
    ('simulacion_demostracion', 'Clase demostrativa o simulación académica'),
    ('practica_evaluativa', 'Práctica evaluativa o examen práctico'),
    ('proyecto_asignatura', 'Proyecto integrador de asignatura'),
    ('taller_docente', 'Taller práctico de asignatura'),
    ('investigacion_formativa', 'Investigación formativa o semillero'),
    ('entrenamiento_tecnico', 'Entrenamiento técnico o desarrollo de competencias'),
    ('proyecto_investigacion', 'Proyecto de investigación'),
    ('desarrollo_experimental', 'Desarrollo experimental'),
    ('innovacion_prototipado', 'Innovación o prototipado'),
    ('proyecto_centro', 'Actividad de un centro o grupo de investigación'),
    ('proyecto_vinculacion', 'Proyecto o programa de vinculación'),
    ('transferencia_conocimiento', 'Transferencia de conocimiento o tecnología'),
    ('curso', 'Curso de educación continua'),
    ('taller', 'Taller o capacitación práctica'),
    ('induccion', 'Inducción o actualización técnica'),
    ('servicio_autorizado', 'Servicio técnico o científico autorizado'),
    ('trabajo_titulacion', 'Trabajo de titulación registrado'),
    ('otro', 'Otro subtipo'),
]

SUBTIPOS_POR_PROPOSITO = {
    # Toda actividad docente exige guia de practica (FT04); por eso el
    # semillero pasa a investigacion y el entrenamiento tecnico a capacitacion.
    'docencia_practica': {
        'practica_curricular', 'simulacion_demostracion', 'practica_evaluativa',
        'proyecto_asignatura', 'taller_docente',
    },
    'investigacion_innovacion': {
        'proyecto_investigacion', 'desarrollo_experimental',
        'innovacion_prototipado', 'proyecto_centro', 'investigacion_formativa',
    },
    'vinculacion': {'proyecto_vinculacion', 'transferencia_conocimiento'},
    'capacitacion': {'curso', 'taller', 'induccion', 'entrenamiento_tecnico'},
    'servicio_cientifico_tecnologico': {'servicio_autorizado'},
    'titulacion': {'trabajo_titulacion'},
    'otro': {'otro'},
}

SUBTIPO_PREDETERMINADO = {
    'docencia_practica': 'practica_curricular',
    'investigacion_innovacion': 'proyecto_investigacion',
    'vinculacion': 'proyecto_vinculacion',
    'capacitacion': 'curso',
    'servicio_cientifico_tecnologico': 'servicio_autorizado',
    'titulacion': 'trabajo_titulacion',
    'otro': 'otro',
}

ALCANCE_BENEFICIARIO_CHOICES = [
    ('perfil_solicitante', 'Carrera o dependencia del solicitante'),
    ('otra_carrera', 'Otra carrera de la institución'),
    ('dependencia_upec', 'Otra dependencia de la institución'),
    ('proyecto_centro', 'Proyecto, grupo o centro de investigación'),
    ('externo', 'Institución o comunidad externa'),
]

ORIGEN_PROGRAMACION_CHOICES = [
    ('programada', 'Actividad programada en planificación académica'),
    ('adicional', 'Actividad adicional o extraordinaria'),
    ('no_aplica', 'No aplica'),
]

VINCULACION_ACTIVIDAD_CHOICES = [
    ('catalogo', 'Actividad registrada en el catálogo institucional'),
    ('clonada', 'Guía institucional clonada para adaptar'),
    ('manual', 'Actividad formal informada por el solicitante'),
    ('independiente', 'Uso autónomo sin actividad formal vinculada'),
    ('no_aplica', 'No aplica'),
]


class EjemploSolicitudUnidad(models.Model):
    """Ejemplo de redacción con el que una unidad enseña a describir su solicitud.

    El asistente pide un texto de varias decenas de palabras y ofrece un
    ejemplo para arrancar. Ese ejemplo tiene que sonar al laboratorio que se
    está reservando: un taller habla de piezas y tolerancias y un observatorio
    de series de datos. La unidad que no publique el suyo muestra el ejemplo
    neutro del asistente, que enseña la forma sin inventarle una disciplina.
    """

    FORMA_SERVICIO = 'servicio'
    FORMAS_CHOICES = [
        (FORMA_SERVICIO, 'Servicio encargado por el solicitante'),
    ] + PROPOSITO_INSTITUCIONAL_CHOICES

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='ejemplos_solicitud',
    )
    proposito_codigo = models.CharField(
        'Propósito o forma de atención',
        max_length=50,
        choices=FORMAS_CHOICES,
        help_text=(
            'Momento del asistente en el que se ofrece este ejemplo. '
            '«Servicio encargado» cubre cualquier propósito de esa vía.'
        ),
    )
    ejemplo = models.TextField(
        'Ejemplo de redacción',
        help_text=(
            'Descripción modelo, escrita como la escribiría quien reserva. '
            'Se ofrece con el botón «Usar el ejemplo redactado».'
        ),
    )
    checklist = models.JSONField(
        'Qué incluir',
        default=list,
        blank=True,
        help_text=(
            'Puntos que la unidad quiere que la descripción cubra, uno por '
            'línea. Vacío deja la lista general del asistente.'
        ),
    )
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_ejemplosolicitudunidad'
        verbose_name = 'Ejemplo de redacción de la unidad'
        verbose_name_plural = 'Ejemplos de redacción de las unidades'
        unique_together = ('unidad', 'proposito_codigo')
        ordering = ['unidad__nombre', 'proposito_codigo']

    def __str__(self):
        return f'{self.unidad} · {self.get_proposito_codigo_display()}'

    def clean(self):
        super().clean()
        if not isinstance(self.checklist, list):
            raise ValidationError({'checklist': 'Escribe los puntos como una lista.'})
        self.checklist = [str(punto).strip() for punto in self.checklist if str(punto).strip()]
        if len(self.checklist) > 8:
            raise ValidationError({'checklist': 'Ocho puntos son suficientes para una lista.'})

    @classmethod
    def publicados(cls, unidad):
        """Los ejemplos que el asistente de esta unidad debe ofrecer."""
        return {
            fila.proposito_codigo: {
                'ejemplo': fila.ejemplo,
                'checklist': fila.checklist or [],
            }
            for fila in cls.objects.filter(unidad=unidad, activo=True)
        }


class CatalogoActividadReserva(models.Model):
    """Referencia administrable para relacionar una reserva con una actividad formal."""

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('revision', 'Pendiente de revisión'),
        ('publicado', 'Publicado'),
        ('archivado', 'Archivado'),
    ]
    VISIBILIDAD_CHOICES = [
        ('privada', 'Solo quien la registró'),
        ('participantes', 'Solicitante y participantes'),
        ('unidad', 'Comunidad de la unidad'),
        ('institucional', 'Catálogo institucional'),
    ]

    proposito_codigo = models.CharField(
        max_length=50,
        choices=PROPOSITO_INSTITUCIONAL_CHOICES,
    )
    subtipo_actividad = models.CharField(
        max_length=50,
        choices=SUBTIPO_ACTIVIDAD_CHOICES,
    )
    nombre = models.CharField(max_length=220)
    codigo = models.CharField(max_length=80, blank=True)
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='actividades_reservables',
        help_text='Déjalo vacío para publicar la referencia en todas las unidades.',
    )
    facultad = models.CharField(
        max_length=50,
        choices=facultades,
        blank=True,
    )
    carrera = models.CharField(
        max_length=50,
        choices=carreras,
        blank=True,
    )
    periodo_academico = models.CharField(max_length=40, blank=True)
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='actividades_reserva',
        help_text='Período institucional aplicable; el código de texto se conserva como histórico.',
    )
    responsable = models.CharField(max_length=180, blank=True)
    descripcion = models.TextField(
        blank=True,
        help_text='Resumen de la actividad, práctica, asignatura o proyecto.',
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actividades_reserva_creadas',
    )
    participantes_autorizados = models.ManyToManyField(
        User, db_table='webcitt_catalogoactividadreserva_participantes_autorizados',
        blank=True,
        related_name='actividades_reserva_asignadas',
        help_text='Personas que pueden consultar la actividad y sus guías privadas.',
    )
    estado_publicacion = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='publicado',
        db_index=True,
    )
    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDAD_CHOICES,
        default='unidad',
        db_index=True,
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    actualizado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = 'webcitt_catalogoactividadreserva'
        ordering = ['proposito_codigo', 'orden', 'nombre']
        verbose_name = 'Actividad institucional para reservas'
        verbose_name_plural = 'Actividades institucionales para reservas'
        indexes = [
            models.Index(fields=['proposito_codigo', 'activo']),
            models.Index(fields=['unidad', 'activo']),
            models.Index(fields=['estado_publicacion', 'visibilidad']),
        ]

    def __str__(self):
        codigo = f'{self.codigo} · ' if self.codigo else ''
        return f'{codigo}{self.nombre}'

    def clean(self):
        errors = {}
        permitidos = SUBTIPOS_POR_PROPOSITO.get(self.proposito_codigo, set())
        if self.subtipo_actividad and self.subtipo_actividad not in permitidos:
            errors['subtipo_actividad'] = (
                'El subtipo seleccionado no corresponde al propósito institucional.'
            )
        if self.carrera:
            facultad_esperada = UserProfile.facultad_para_carrera(self.carrera)
            if facultad_esperada and self.facultad and self.facultad != facultad_esperada:
                errors['facultad'] = 'La facultad no corresponde a la carrera seleccionada.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.periodo_id:
            self.periodo_academico = self.periodo.codigo
        self.actualizado_en = timezone.now()
        super().save(*args, **kwargs)

def guia_actividad_upload_to(instance, filename):
    actividad_id = instance.actividad_id or 'temporal'
    return f'actividades/{actividad_id}/guias/{filename}'


def guia_firmada_upload_to(instance, filename):
    return f'actividades/{instance.actividad_id}/guias/{instance.pk}/firmada/{filename}'


class GuiaActividadReserva(models.Model):
    """Guía versionada de una actividad, estructurada o importada como PDF."""

    VISIBILIDAD_CHOICES = [
        ('participantes', 'Solo participantes de la actividad'),
        ('unidad', 'Comunidad de la unidad'),
        ('publica', 'Publicada en Recursos y prácticas'),
    ]
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('revision', 'Pendiente de revisión'),
        ('publicada', 'Aprobada y publicada'),
        ('rechazada', 'Devuelta con observaciones'),
        ('archivada', 'Archivada'),
    ]

    actividad = models.ForeignKey(
        CatalogoActividadReserva,
        on_delete=models.CASCADE,
        related_name='guias',
    )
    familia = models.ForeignKey(
        'plantas_operacion.FamiliaProducto',
        on_delete=models.PROTECT,
        related_name='guias_practica',
        null=True,
        blank=True,
        help_text='Familia del proceso que enseña la guía, cuando pertenece a una planta piloto.',
    )
    titulo = models.CharField(max_length=220)
    descripcion = models.TextField(blank=True)
    codigo_guia = models.CharField(max_length=80, blank=True)
    numero_version = models.PositiveSmallIntegerField(default=1)
    es_estructurada = models.BooleanField(
        default=False,
        db_index=True,
        help_text='La guía se genera desde el formulario institucional.',
    )
    ALCANCES = [
        ('sesion', 'Guía de la sesión'),
        ('periodo', 'Guía general del período'),
    ]
    # Una guía general planifica el período y no autoriza ninguna sesión por
    # sí sola; cada sesión programada tiene su propia guía.
    alcance = models.CharField(max_length=10, choices=ALCANCES, default='sesion')
    guia_general = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guias_de_sesion',
        help_text='La guía general del período a la que sirve esta guía de sesión.',
    )
    guia_origen = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adaptaciones',
        help_text='Versión institucional desde la que se clonó esta guía.',
    )
    sesion = models.ForeignKey(
        'formacion.PlanificacionPractica',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guias_de_la_sesion',
        help_text='La sesión programada a la que pertenece esta guía.',
    )
    es_vigente = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Identifica la versión aprobada que debe usarse en nuevas reservas.',
    )
    contenido = models.JSONField(
        default=dict,
        blank=True,
        help_text='Contenido normalizado del formato institucional de guía de práctica.',
    )
    archivo = models.FileField(
        upload_to=guia_actividad_upload_to,
        max_length=255,
        validators=[FileExtensionValidator(['pdf'])],
        blank=True,
    )
    nombre_original = models.CharField(max_length=255, blank=True)
    tamano = models.PositiveBigIntegerField(default=0)
    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDAD_CHOICES,
        default='participantes',
        db_index=True,
    )
    estado_publicacion = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='revision',
        db_index=True,
    )
    permite_descarga = models.BooleanField(
        default=False,
        help_text=(
            'Permite que los usuarios autorizados descarguen el PDF. '
            'Si se desactiva, la guía queda disponible únicamente para visualización.'
        ),
    )
    solicita_publicacion = models.BooleanField(
        default=False,
        help_text='Solicita que la guía aprobada sea visible para la comunidad de la unidad.',
    )
    observaciones_revision = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    subido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guias_actividad_subidas',
    )
    revisado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guias_actividad_revisadas',
    )
    revisado_en = models.DateTimeField(null=True, blank=True)
    aprobado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guias_actividad_aprobadas',
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)
    # Firma electronica certificada (FirmaEC): PDF aprobado firmado fuera de
    # la plataforma y cargado como version oficial descargable.
    archivo_firmado = models.FileField(
        upload_to=guia_firmada_upload_to,
        max_length=255,
        null=True,
        blank=True,
        help_text='PDF de la guía aprobada firmado con certificado electrónico (FirmaEC).',
    )
    firmado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='guias_firmadas',
    )
    firmado_en = models.DateTimeField(null=True, blank=True)
    firma_certificada_resumen = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_guiaactividadreserva'
        ordering = ['actividad', '-numero_version', '-creado_en', '-pk']
        verbose_name = 'Guía de práctica'
        verbose_name_plural = 'Guías de práctica'
        constraints = [
            models.UniqueConstraint(
                fields=['actividad', 'numero_version'],
                condition=models.Q(es_estructurada=True, sesion__isnull=True),
                name='guia_estructurada_version_unica',
            ),
            models.UniqueConstraint(
                fields=['actividad'],
                condition=models.Q(es_estructurada=True, es_vigente=True, sesion__isnull=True),
                name='guia_estructurada_vigente_unica',
            ),
            models.UniqueConstraint(
                fields=['sesion', 'numero_version'],
                condition=models.Q(es_estructurada=True, sesion__isnull=False),
                name='guia_de_sesion_version_unica',
            ),
            models.UniqueConstraint(
                fields=['sesion'],
                condition=models.Q(es_estructurada=True, es_vigente=True, sesion__isnull=False),
                name='guia_de_sesion_vigente_unica',
            ),
        ]

    def __str__(self):
        return f'{self.actividad}: {self.titulo}'

    def clean(self):
        errors = {}
        if self.familia_id and self.actividad_id and self.familia.unidad_id != self.actividad.unidad_id:
            errors['familia'] = 'La familia debe pertenecer a la misma planta que la actividad.'
        if self.es_estructurada and self.archivo:
            errors['archivo'] = (
                'Una guía estructurada se genera desde el sistema y no requiere un PDF cargado.'
            )
        if not self.es_estructurada and not self.archivo:
            errors['archivo'] = 'Carga el archivo PDF de la guía.'
        if self.archivo:
            if not self.archivo.name.lower().endswith('.pdf'):
                errors['archivo'] = 'Las guías de actividades deben cargarse en formato PDF.'
            if self.archivo.size > 20 * 1024 * 1024:
                errors['archivo'] = 'La guía PDF no puede superar 20 MB.'
        if errors:
            raise ValidationError(errors)

    @property
    def es_editable(self):
        """Se corrige mientras no este validada para publicar.

        La guia en revision todavia admite cambios: quien la escribio y el
        personal de la unidad pueden ajustarla hasta que se apruebe. La
        version firmada con certificado ya no se toca, porque el PDF firmado
        dejaria de corresponder con el contenido.
        """
        return (
            self.es_estructurada
            and self.estado_publicacion in {'borrador', 'revision', 'rechazada'}
            and not self.archivo_firmado
        )

    def secciones_faltantes(self):
        """Mínimo institucional antes de enviar la guía a revisión.

        Los apartados complementarios se conservan en el FT04, pero pueden
        quedar como ``No registrado`` o ``No aplica`` cuando la práctica no
        los necesite. Equipos, software e insumos proceden de la reserva y no
        son requisito universal (por ejemplo, una actividad puede usar solo
        un espacio o no generar residuos).
        """
        if not self.es_estructurada:
            return []
        etiquetas = {
            'asignatura': 'Asignatura o actividad formativa',
            'carrera_semestre': 'Carrera y semestre',
            'docente_responsable': 'Docente responsable',
            'laboratorio': 'Laboratorio o unidad',
            'categoria_uso': 'Categoría de uso',
            'duracion': 'Duración estimada',
            'maximo_estudiantes': 'Número máximo de estudiantes',
            'resultado_aprendizaje': 'Resultado de aprendizaje',
            'objetivos': 'Objetivos de la práctica',
            'procedimiento': 'Procedimiento',
        }
        contenido = self.contenido or {}
        if contenido.get('formato_contenido') == 'html':
            # Un apartado del editor visual puede contener solo etiquetas vacias.
            from apps.reservas.presentation.guia_html import esta_vacio

            def vacio(clave):
                valor = contenido.get(clave)
                return esta_vacio(valor) if isinstance(valor, str) else not valor
        else:
            def vacio(clave):
                return not contenido.get(clave)
        pendientes = [etiqueta for clave, etiqueta in etiquetas.items() if vacio(clave)]
        firmas = contenido.get('firmas')
        if isinstance(firmas, dict):
            from apps.reservas.presentation.guia_firmas import firmas_faltantes, normalizar_firmas

            pendientes.extend(f'Firma {item}' for item in firmas_faltantes(normalizar_firmas(firmas)))
        return pendientes

    def save(self, *args, **kwargs):
        if self.familia_id is None and self.sesion_id:
            reserva = Reserva.objects.filter(planificacion_practica=self.sesion).select_related('receta').first()
            if reserva and reserva.receta_id:
                self.familia = reserva.receta.familia
        if self.archivo:
            self.nombre_original = self.nombre_original or Path(self.archivo.name).name
            try:
                self.tamano = self.archivo.size
            except (AttributeError, OSError):
                pass
        super().save(*args, **kwargs)


class ProgramacionReserva(models.Model):
    """Agrupa las sesiones creadas por una reserva semanal de período."""

    FRECUENCIA_CHOICES = [
        ('unica', 'Una sola sesión'),
        ('semanal_rango', 'Semanal hasta una fecha definida'),
        ('semanal_periodo', 'Semanal durante el período académico'),
    ]
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('cancelada', 'Cancelada'),
        ('finalizada', 'Finalizada'),
    ]

    laboratorio = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='programaciones_reserva',
    )
    actividad = models.ForeignKey(
        CatalogoActividadReserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programaciones_reserva',
    )
    solicitante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='programaciones_reserva',
    )
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='programaciones_reserva',
    )
    asignatura = models.ForeignKey(
        'formacion.Asignatura',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programaciones',
        help_text='La asignatura cuyo sílabo programa estas sesiones.',
    )
    frecuencia = models.CharField(
        max_length=20,
        choices=FRECUENCIA_CHOICES,
        default='unica',
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    dia_semana = models.PositiveSmallIntegerField(
        help_text='Día ISO/Python de la sesión recurrente: lunes=0, domingo=6.',
    )
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    horas_seleccionadas = models.JSONField(default=list, blank=True)
    fechas_omitidas = models.JSONField(default=list, blank=True)
    total_sesiones = models.PositiveSmallIntegerField(default=1)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activa')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_programacionreserva'
        ordering = ['-creado_en']
        verbose_name = 'Programación de reserva'
        verbose_name_plural = 'Programaciones de reservas'

    def __str__(self):
        return f'{self.laboratorio} · {self.get_frecuencia_display()} · {self.fecha_inicio}'


class Reserva(models.Model):
    """Modelo para gestionar reservas de equipos y laboratorios"""

    TIPO_SOLICITUD_CHOICES = [
        ('recursos', 'Reserva de recursos'),
        ('equipo', 'Reserva de equipos'),
        ('espacio', 'Reserva de espacios'),
        ('software', 'Reserva de software o licencias'),
        ('servicio', 'Solicitud de servicio'),
    ]
    MODALIDAD_SERVICIO_CHOICES = [
        ('modelo_listo', 'Entrego el modelo o archivo listo'),
        ('diseno_asistido', 'Diseñaré en el laboratorio con asesoría'),
        ('diseno_completo', 'El laboratorio realizará el diseño completo'),
    ]
    URGENCIA_SERVICIO_CHOICES = [
        ('normal', 'Atención normal según la cola de trabajo'),
        ('urgente', 'Urgente: 1 a 2 días laborables'),
    ]
    METODO_PAGO_CHOICES = [
        ('por_definir', 'Definir después de la revisión técnica'),
        ('transferencia', 'Transferencia o depósito'),
        ('ventanilla', 'Pago físico en ventanilla universitaria'),
        ('tarjeta', 'Tarjeta en punto de pago'),
    ]
    PROVISION_CONSUMIBLES_CHOICES = [
        ('ninguno', 'No requiere insumos ni materiales'),
        ('unidad', 'Solicitar insumos o materiales de la unidad'),
        ('propios', 'Utilizará materiales propios'),
        ('revision', 'Requiere orientación o revisión técnica'),
    ]
    ALCANCE_ESPACIO_CHOICES = [
        ('sin_espacio', 'No requiere espacio físico'),
        ('areas', 'Una o varias áreas configuradas'),
        ('espacio_unico', 'Espacio único de la unidad'),
        ('unidad_completa', 'Unidad completa'),
    ]
    
    PROPOSITO_INSTITUCIONAL_CHOICES = PROPOSITO_INSTITUCIONAL_CHOICES
    SUBTIPO_ACTIVIDAD_CHOICES = SUBTIPO_ACTIVIDAD_CHOICES
    SUBTIPOS_POR_PROPOSITO = SUBTIPOS_POR_PROPOSITO
    SUBTIPO_PREDETERMINADO = SUBTIPO_PREDETERMINADO
    ALCANCE_BENEFICIARIO_CHOICES = ALCANCE_BENEFICIARIO_CHOICES
    ORIGEN_PROGRAMACION_CHOICES = ORIGEN_PROGRAMACION_CHOICES
    VINCULACION_ACTIVIDAD_CHOICES = VINCULACION_ACTIVIDAD_CHOICES

    ESTADO_CHOICES = RESERVA_ESTADO_CHOICES

    RESULTADO_CIERRE_CHOICES = [
        ('atendida', 'Atendida y completada'),
        ('no_presentado', 'El usuario no se presentó'),
        ('no_atendida', 'No atendida por la unidad'),
        ('vencida', 'Vencida sin aprobación'),
    ]
    
    # RELACIONES PRINCIPALES
    laboratorio = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE, 
        related_name='reservas',
        help_text="Laboratorio donde se realizará la reserva"
    )
    programacion = models.ForeignKey(
        ProgramacionReserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sesiones',
        help_text='Serie de la que proviene esta sesión, si es una reserva recurrente.',
    )
    # Una práctica por proceso: la planta marcó todo lo que el proceso exige y
    # el solicitante solo eligió la escala; al aprobarse nace su orden.
    receta = models.ForeignKey(
        'plantas_operacion.Receta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_por_proceso',
        help_text='El proceso que la práctica sigue, cuando se reservó por proceso.',
    )
    producto_solicitado = models.ForeignKey(
        'plantas_operacion.Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_solicitadas',
        help_text=(
            'Producto que se elaborará en la planta, incluso cuando su proceso '
            'técnico todavía no esté configurado.'
        ),
    )
    factor_proceso = models.DecimalField(
        'Corridas base del proceso',
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
    )
    materia_prima_cliente = models.BooleanField(
        'Materia prima del cliente',
        default=False,
        help_text='En un encargo por proceso, el cliente trae la materia prima de la corrida base.',
    )
    tipo_solicitud = models.CharField(
        max_length=20,
        choices=TIPO_SOLICITUD_CHOICES,
        default='equipo',
        help_text='Distingue el flujo solicitado dentro del mismo asistente.',
    )
    provision_consumibles = models.CharField(
        max_length=20,
        choices=PROVISION_CONSUMIBLES_CHOICES,
        default='ninguno',
        help_text='Indica cómo se cubrirán los insumos y materiales requeridos por la actividad.',
    )
    servicios_solicitados = models.ManyToManyField(
        'laboratorios_operacion.FablabService', db_table='webcitt_reserva_servicios_solicitados',
        blank=True,
        related_name='reservas_solicitantes',
        help_text='Servicios técnicos concretos seleccionados en la reserva.',
    )
    software_solicitado = models.ManyToManyField(
        'recursos.SoftwareDisponible', db_table='webcitt_reserva_software_solicitado',
        blank=True,
        related_name='reservas',
        help_text='Software o licencias solicitadas por el usuario.',
    )
    incluye_espacio = models.BooleanField(
        default=False,
        help_text=(
            'Indica que la solicitud requiere además el uso del espacio físico '
            'de la unidad.'
        ),
    )
    solicito_espacio = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            'El usuario marcó explícitamente espacio y mobiliario al iniciar; se '
            'distingue del espacio incorporado por la ubicación de un equipo.'
        ),
    )
    solicito_equipo = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            'El usuario marcó explícitamente equipo o instrumento; se distingue '
            'del puesto incorporado automáticamente por una licencia.'
        ),
    )
    solicito_software = models.BooleanField(
        default=False,
        db_index=True,
        help_text='El usuario marcó explícitamente software o licencia al iniciar.',
    )
    alcance_espacio = models.CharField(
        max_length=20,
        choices=ALCANCE_ESPACIO_CHOICES,
        default='sin_espacio',
        db_index=True,
        help_text=(
            'Conserva si la solicitud ocupa áreas concretas, el único espacio '
            'disponible o toda la unidad.'
        ),
    )
    espacios_solicitados = models.ManyToManyField(
        'gestion_unidades.EspacioReservable', db_table='webcitt_reserva_espacios_solicitados',
        blank=True,
        related_name='reservas',
        help_text='Áreas, estaciones o puestos concretos solicitados dentro de la unidad.',
    )
    responsable_asignado = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_asignadas',
        help_text='Responsable de la unidad encargado de atender esta solicitud.',
    )
    participantes = models.ManyToManyField(
        User, db_table='webcitt_reserva_participantes',
        blank=True,
        related_name='reservas_como_participante',
        help_text='Usuarios secundarios registrados que participarán en la actividad.',
    )
    
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='reservas_realizadas',
        help_text="Usuario que realiza la reserva (opcional para usuarios anónimos)"
    )
    
    # INFORMACIÓN TEMPORAL - ✅ COMPATIBLE
    fecha = models.DateField(help_text="Fecha de la reserva")
    hora_inicio = models.TimeField(help_text="Hora de inicio") 
    hora_fin = models.TimeField(help_text="Hora de finalización")
    
    # ✅ AGREGAR: Campo para almacenar horas seleccionadas del calendario
    horas_seleccionadas = models.TextField(
        blank=True, 
        null=True,
        help_text="JSON con las horas seleccionadas en el calendario"
    )
    
    # ✅ CORREGIR: Cambiar nombre del campo duracion
    duracion = models.IntegerField(
        default=1,
        help_text="Duración en horas (calculada automáticamente)"
    )
    
    # INFORMACIÓN DEL EQUIPO - ✅ COMPATIBLE
    equipo_codigo = models.CharField(
        # Guarda el código del recurso principal, que puede ser un equipo, un
        # espacio (60), un software (40) o un servicio. Con veinte caracteres,
        # un código de área algo largo rompía la creación de la reserva.
        max_length=60,
        help_text="Código del recurso principal de la reserva",
    )
    equipo_nombre = models.CharField(
        max_length=100,
        help_text="Nombre del equipo reservado"
    )
    
    # ✅ AGREGAR: Unidades seleccionadas
    unidades_seleccionadas = models.TextField(
        blank=True,
        null=True,
        help_text="JSON con las unidades específicas seleccionadas"
    )
    
    # INFORMACIÓN DEL SOLICITANTE - ✅ COMPATIBLE con formulario
    nombre_solicitante = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nombre completo del solicitante"
    )
    correo_solicitante = models.EmailField(
        blank=True,
        null=True,
        help_text="Correo del solicitante"
    )
    telefono_solicitante = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Teléfono del solicitante"
    )
    institucion = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Institución del solicitante"
    )
    tipo_usuario_solicitante = models.CharField(
        max_length=20,
        choices=tipos_usuario,
        blank=True,
        help_text='Clasificación del usuario conservada al momento de solicitar.',
    )
    facultad_solicitante = models.CharField(
        max_length=50,
        choices=facultades,
        blank=True,
        help_text='Facultad o dependencia conservada al momento de solicitar.',
    )
    carrera_solicitante = models.CharField(
        max_length=50,
        choices=carreras,
        blank=True,
        help_text='Carrera conservada al momento de solicitar.',
    )
    nivel_academico_solicitante = models.CharField(
        max_length=30,
        choices=niveles,
        blank=True,
        help_text='Nivel académico conservado al momento de solicitar.',
    )
    
    TIPO_USO_CHOICES = [
        ('experimentacion', 'Experimentación/Investigación'),
        ('individual', 'Uso individual'),
        ('practica', 'Práctica de Laboratorio'),
    ]
    tipo_uso = models.CharField(
        max_length=20,
        choices=TIPO_USO_CHOICES,
        default='experimentacion',
        help_text="Tipo de uso de la reserva"
    )

        
    # ✅ AGREGAR: Campos del formulario de reserva
    proposito = models.TextField(
        default='No especificado',  # ✅ AGREGAR default
        help_text="Propósito/Objetivo de la reserva"
    )
    proposito_codigo = models.CharField(
        max_length=50,
        choices=PROPOSITO_INSTITUCIONAL_CHOICES,
        blank=True,
        db_index=True,
        help_text='Código institucional estable utilizado para indicadores y filtros.',
    )
    subtipo_actividad = models.CharField(
        max_length=50,
        choices=SUBTIPO_ACTIVIDAD_CHOICES,
        blank=True,
        db_index=True,
    )
    alcance_beneficiario = models.CharField(
        max_length=40,
        choices=ALCANCE_BENEFICIARIO_CHOICES,
        default='perfil_solicitante',
        db_index=True,
        help_text=(
            'Identifica para quién se realiza la actividad, independientemente '
            'del perfil solicitante.'
        ),
    )
    facultad_beneficiaria = models.CharField(
        max_length=50,
        choices=facultades,
        blank=True,
        db_index=True,
    )
    carrera_beneficiaria = models.CharField(
        max_length=50,
        choices=carreras,
        blank=True,
        db_index=True,
    )
    entidad_beneficiaria = models.CharField(max_length=220, blank=True)
    vinculacion_actividad = models.CharField(
        max_length=20,
        choices=VINCULACION_ACTIVIDAD_CHOICES,
        default='no_aplica',
        db_index=True,
        help_text=(
            'Distingue una referencia seleccionada del catálogo, una referencia '
            'manual y un uso autónomo sin actividad formal.'
        ),
    )
    actividad_catalogo = models.ForeignKey(
        CatalogoActividadReserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas',
    )
    referencia_actividad = models.CharField(
        max_length=220,
        blank=True,
        help_text=(
            'Asignatura, práctica, proyecto, trabajo de titulación o '
            'capacitación vinculada.'
        ),
    )
    codigo_referencia_actividad = models.CharField(max_length=80, blank=True)
    periodo_academico = models.CharField(max_length=40, blank=True)
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservas',
        help_text='Período académico institucional determinado para la fecha de la reserva.',
    )
    version_calendario = models.ForeignKey(
        VersionCalendarioAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservas',
        help_text='Versión vigente del calendario utilizada al registrar la solicitud.',
    )
    semana_academica = models.ForeignKey(
        SemanaAcademica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas',
    )
    semana_academica_numero = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Número de semana conservado para reportes históricos.',
    )
    responsable_actividad = models.CharField(max_length=180, blank=True)
    origen_programacion = models.CharField(
        max_length=20,
        choices=ORIGEN_PROGRAMACION_CHOICES,
        default='no_aplica',
    )
    detalle_otro_proposito = models.TextField(blank=True)
    descripcion_proyecto = models.TextField(
        default='Sin descripción especificada',  # ✅ AGREGAR default
        help_text="Descripción detallada del proyecto/actividad"
    )
    requisitos_especiales = models.TextField(
        blank=True, 
        null=True,
        help_text="Requisitos especiales o materiales adicionales"
    )
    titulo_solicitud = models.CharField(
        max_length=255,
        blank=True,
        help_text='Título generado automáticamente a partir del tipo, recurso y propósito.',
    )
    modalidad_servicio = models.CharField(
        max_length=30,
        choices=MODALIDAD_SERVICIO_CHOICES,
        blank=True,
    )
    desglose_cotizacion = models.JSONField(default=dict, blank=True)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    descuento_aplicado = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    desglose_liquidacion = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Foto contable del cierre: recursos y consumos reales, aporte '
            'institucional, desperdicio y variación frente a la estimación.'
        ),
    )
    costo_real = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Costo operativo total del cierre, incluido el desperdicio.',
    )
    aporte_institucional_real = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor real asumido institucionalmente en el cierre.',
    )
    valor_final_usuario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor resultante para el usuario después del aporte institucional.',
    )
    cotizacion_aceptada = models.BooleanField(default=False)
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        blank=True,
    )
    # Trabajo encargado en una solicitud de servicio.
    urgencia_servicio = models.CharField(
        max_length=10,
        choices=URGENCIA_SERVICIO_CHOICES,
        blank=True,
    )
    cantidad_piezas = models.PositiveIntegerField(
        default=1,
        help_text='Número de piezas o ejemplares del trabajo solicitado.',
    )
    detalle_trabajo = models.TextField(
        blank=True,
        help_text='Dimensiones, acabado u otras precisiones del trabajo.',
    )
    fecha_entrega_prevista = models.DateField(
        null=True,
        blank=True,
        help_text='Entrega propuesta por el sistema según la cola de trabajo; la unidad puede ajustarla.',
    )
    intencion_solicitud = models.TextField(
        blank=True,
        help_text=(
            'Lo que la persona pretende realizar (50 a 200 palabras): orienta la revisión '
            'y las sugerencias de la guía sin publicarse en ella.'
        ),
    )




    numero_participantes = models.PositiveIntegerField(
        default=1,
        help_text="Número de participantes en la sesión"
    )
    
    # ✅ SIMPLIFICAR: Usar el campo motivo para descripción completa





    # DETALLES DE LA RESERVA
    motivo = models.TextField(
        blank=True,
        null=True,
        help_text="Campo combinado con propósito y descripción (generado automáticamente)"
    )
     
    # ESTADO Y CONTROL
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='pendiente',
        help_text="Estado actual de la reserva"
    )
    
    # ✅ CORREGIR: Nombre del campo de fecha de creación
    fecha_reserva = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora cuando se creó la reserva"
    )
    # <-- Nuevo campo para el código público de la reserva
    codigo_reserva = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        unique=True,
        editable=False,
        help_text="Código público de la reserva, p.e. LAB001-000123"
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text="Última actualización de la reserva"
    )
    
    # CONTROL DE NOTIFICACIONES
    notificacion_enviada = models.BooleanField(
        default=False,
        help_text="Si se envió notificación al solicitante"
    )
    encargado_notificado = models.BooleanField(
        default=False,
        help_text="Si se notificó al encargado del laboratorio"
    )
    fecha_inicio_atencion = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    resultado_cierre = models.CharField(
        max_length=20,
        choices=RESULTADO_CIERRE_CHOICES,
        blank=True,
        db_index=True,
    )
    detalle_cierre = models.TextField(blank=True)
    detalle_ejecucion = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Registro estructurado de lo realmente ejecutado: asistencia, '
            'recursos, consumos, incidencias y costos.'
        ),
    )
    
    # VALIDACIÓN Y APROBACIÓN
    validada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_validadas',
        help_text="Usuario que validó/aprobó la reserva"
    )
    fecha_validacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de validación/aprobación"
    )
    observaciones_validacion = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones del validador"
    )

    # CANCELACIÓN TRAZABLE: la reserva cancelada no se elimina; sale de la
    # agenda pero conserva quién, cuándo y por qué la canceló.
    ORIGEN_CANCELACION_CHOICES = [
        ('solicitante', 'Solicitante'),
        ('laboratorio', 'Laboratorio'),
    ]
    cancelada_en = models.DateTimeField(null=True, blank=True)
    cancelada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_canceladas',
    )
    origen_cancelacion = models.CharField(
        max_length=20,
        choices=ORIGEN_CANCELACION_CHOICES,
        blank=True,
    )
    motivo_cancelacion = models.TextField(blank=True)
    
    class Meta:
        db_table = 'webcitt_reserva'
        ordering = ['-fecha_reserva', '-hora_inicio']  # ✅ CORREGIR ordenamiento
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        indexes = [
            models.Index(fields=['fecha', 'hora_inicio']),
            models.Index(fields=['equipo_codigo', 'fecha']),
            models.Index(fields=['laboratorio', 'fecha']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        solicitante = self.nombre_completo_solicitante
        return f"{self.laboratorio.nombre} - {self.equipo_nombre} - {self.fecha} ({solicitante})"
    
    # ✅ AGREGAR: Métodos para manejar JSON fields
    def get_horas_seleccionadas_list(self):
        """Retorna las horas seleccionadas como lista"""
        if self.horas_seleccionadas:
            import json
            try:
                return json.loads(self.horas_seleccionadas)
            except Exception:
                return []
        return []
    
    def get_unidades_seleccionadas_list(self):
        """Retorna las unidades seleccionadas como lista"""
        if self.unidades_seleccionadas:
            import json
            try:
                return json.loads(self.unidades_seleccionadas)
            except Exception:
                return []
        return []
    
    def clean(self):
        """Validaciones del modelo"""
        errors = {}

        if self.producto_solicitado_id and self.laboratorio_id:
            if self.producto_solicitado.unidad_id != self.laboratorio_id:
                errors['producto_solicitado'] = (
                    'El producto solicitado debe pertenecer a la unidad reservada.'
                )
        if self.receta_id and self.laboratorio_id:
            if self.receta.unidad_id != self.laboratorio_id:
                errors['receta'] = 'El proceso debe pertenecer a la unidad reservada.'
            if (
                self.producto_solicitado_id
                and self.receta.producto_id != self.producto_solicitado_id
            ):
                errors['producto_solicitado'] = (
                    'El producto solicitado no corresponde al proceso seleccionado.'
                )
        
        # Validar que la hora de fin sea posterior a la hora de inicio
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            errors['hora_fin'] = "La hora de fin debe ser posterior a la hora de inicio."
        
        # Validar que se proporcione información del solicitante
        if not self.usuario and not self.nombre_solicitante:
            errors['nombre_solicitante'] = "Debe proporcionar un usuario registrado o el nombre del solicitante."
        
        if not self.usuario and not self.correo_solicitante:
            errors['correo_solicitante'] = "Debe proporcionar el correo del solicitante."
        
        # Validar duración máxima (ej: 8 horas)
        if self.hora_inicio and self.hora_fin:
            duracion_calculada = self.calcular_duracion()
            if duracion_calculada > 8:
                errors['hora_fin'] = "La duración máxima de una reserva es de 8 horas."
            elif duracion_calculada <= 0:
                errors['hora_fin'] = "La duración debe ser mayor a 0 horas."
        
        # Validar que la fecha no sea en el pasado
        if self.fecha and self.fecha < timezone.localdate(timezone=timezone.get_default_timezone()):
            errors['fecha'] = "No se pueden crear reservas para fechas pasadas."

        if self.fecha and self.hora_inicio and self.hora_fin:
            from apps.core.presentation.regional import validar_intervalo_institucional
            try:
                validar_intervalo_institucional(
                    datetime.combine(self.fecha, self.hora_inicio),
                    datetime.combine(self.fecha, self.hora_fin),
                )
            except ValueError as error:
                errors['hora_inicio'] = str(error)
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save para calcular duración automáticamente"""
        campos = kwargs.get('update_fields')
        sincronizar_visita = bool(
            self.pk and self.costo_estimado is not None
            and (campos is None or 'costo_estimado' in campos)
        )
        if self.hora_inicio and self.hora_fin:
            self.duracion = self.calcular_duracion()
        if self.version_calendario_id and not self.periodo_id:
            self.periodo_id = self.version_calendario.periodo_id
        if self.semana_academica_id:
            self.version_calendario_id = self.semana_academica.version_calendario_id
            self.periodo_id = self.semana_academica.version_calendario.periodo_id
            self.semana_academica_numero = self.semana_academica.numero
        if self.periodo_id:
            self.periodo_academico = self.periodo.codigo
            if self.fecha and not self.semana_academica_id:
                semana = self.periodo.semana_para_fecha(self.fecha)
                if semana:
                    self.semana_academica = semana
                    self.semana_academica_numero = semana.numero
                    self.version_calendario_id = semana.version_calendario_id
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            if sincronizar_visita:
                # La reserva es el expediente económico canónico de la visita.
                self._meta.apps.get_model('reservas', 'SolicitudVisita').objects.using(using).filter(
                    reserva_id=self.pk,
                ).exclude(costo_estimado=self.costo_estimado).update(costo_estimado=self.costo_estimado)
    
    # PROPIEDADES DE INFORMACIÓN
    
    # Prefijos con los que el sistema arma `titulo_solicitud`: solo esos se
    # recortan para el nombre corto (un título escrito a mano se respeta).
    PREFIJOS_TITULO_GENERADO = (
        'Reserva de equipo: ',
        'Reserva de software: ',
        'Reserva de espacio: ',
        'Solicitud de servicio: ',
        'Solicitud de recursos: ',
    )
    ETIQUETAS_TIPO_USUARIO_CORTAS = {
        'estudiante': 'Estudiante',
        'docente': 'Docente',
        'investigador': 'Investigador',
        'administrativo': 'Administrativo',
        'egresado': 'Egresado',
        'externo': 'Externo',
    }
    ETIQUETAS_PROPOSITO_CORTAS = {
        'docencia_practica': 'Docencia',
        'investigacion_innovacion': 'Investigación',
        'vinculacion': 'Vinculación',
        'capacitacion': 'Capacitación',
        'servicio_cientifico_tecnologico': 'Servicio técnico',
        'titulacion': 'Titulación',
        'otro': 'Otro propósito',
    }

    @property
    def resumen_solicitud(self):
        """Nombre corto para las tarjetas de agenda: el recurso, sin prefijo,
        modalidad ni propósito (esos ya se muestran en su propia línea)."""
        titulo = (self.titulo_solicitud or '').strip()
        prefijo = next(
            (item for item in self.PREFIJOS_TITULO_GENERADO if titulo.startswith(item)),
            '',
        )
        if not prefijo:
            return titulo or self.equipo_nombre or self.get_tipo_solicitud_display()
        cuerpo = titulo[len(prefijo):].split(' · ')[0].strip()
        partes = [parte.strip() for parte in cuerpo.split(' + ') if parte.strip()]
        restantes = 0
        if partes and re.fullmatch(r'\d+ más', partes[-1]):
            restantes = int(partes[-1].split()[0])
            partes = partes[:-1]
        if len(partes) > 2:
            restantes += len(partes) - 2
            partes = partes[:2]
        nombre = ' + '.join(partes)
        if not nombre:
            return titulo
        return f'{nombre} +{restantes}' if restantes else nombre

    @property
    def url_seguimiento(self):
        """Enlace que abre esta solicitud en «Mis reservas» de su unidad.

        Vive en la reserva porque lo usan los avisos, la lista de guías y el
        perfil: si la forma del enlace cambia, cambia en un solo sitio.
        """
        return f'{self.laboratorio.get_absolute_url()}?reserva={self.pk}#mis-reservas'

    @property
    def tipo_usuario_solicitante_corto(self):
        """Quién reserva: estudiante, docente, investigador…"""
        return self.ETIQUETAS_TIPO_USUARIO_CORTAS.get(
            self.tipo_usuario_solicitante,
            'Usuario registrado',
        )

    @property
    def proposito_corto(self):
        """Categoría de uso en una palabra para las tarjetas de agenda."""
        return (
            self.ETIQUETAS_PROPOSITO_CORTAS.get(self.proposito_codigo)
            or (self.proposito or '').strip()
            or 'Uso del laboratorio'
        )

    @property
    def nombre_completo_solicitante(self):
        """Retorna el nombre completo del solicitante"""
        if self.usuario:
            return self.usuario.get_full_name() or self.usuario.username
        return self.nombre_solicitante or 'Sin nombre'

    @property
    def tipo_solicitud_reportado(self):
        """La visita conserva su reserva de espacio, pero se presenta como visita."""
        return 'Visita' if getattr(self, 'visita', None) else self.get_tipo_solicitud_display()
    
    @property
    def correo_contacto(self):
        """Retorna el correo de contacto del solicitante"""
        if self.usuario:
            return self.usuario.email
        return self.correo_solicitante
    
    @property
    def telefono_contacto(self):
        """Retorna el teléfono de contacto del solicitante"""
        if self.usuario and hasattr(self.usuario, 'profile'):
            return self.usuario.profile.telefono
        return self.telefono_solicitante
    
    @property
    def fecha_hora_inicio(self):
        if not self.fecha or not self.hora_inicio:
            return None
        valor = datetime.combine(self.fecha, self.hora_inicio)
        return timezone.make_aware(valor, timezone.get_default_timezone())

    @property
    def fecha_hora_fin(self):
        if not self.fecha or not self.hora_fin:
            return None
        valor = datetime.combine(self.fecha, self.hora_fin)
        return timezone.make_aware(valor, timezone.get_default_timezone())

    @property
    def requiere_cierre_operativo(self):
        fin = self.fecha_hora_fin
        return bool(
            fin
            and fin < timezone.now()
            and self.estado in {'confirmada', 'en_proceso'}
        )

    @property
    def es_efectiva(self):
        ejecucion = self.detalle_ejecucion if isinstance(self.detalle_ejecucion, dict) else {}
        return bool(
            self.estado == 'completada'
            and self.resultado_cierre == 'atendida'
            and ejecucion.get('registrada_en')
        )

    @property
    def requiere_regularizacion_operativa(self):
        """Detecta cierres heredados que no sustentan una atención efectiva."""
        return self.estado == 'completada' and not self.es_efectiva
    
    # MÉTODOS DE CÁLCULO
    
    def construir_codigo_reserva(self):
        """Codigo publico institucional de la solicitud.

        El formato vive unicamente aqui; la senal posterior al guardado y
        cualquier flujo que necesite el identificador deben usar este metodo
        en lugar de rearmar la cadena por su cuenta.
        """
        laboratorio_id = self.laboratorio_id or 0
        return f'RL{int(laboratorio_id):03d}-{int(self.id):06d}'

    def calcular_duracion(self):
        """Calcula la duración en horas de la reserva"""
        if not self.hora_inicio or not self.hora_fin:
            return 0
        
        from datetime import datetime, timedelta
        
        # Convertir a datetime para hacer la resta
        inicio = datetime.combine(self.fecha if self.fecha else timezone.localdate(timezone=timezone.get_default_timezone()), self.hora_inicio)
        fin = datetime.combine(self.fecha if self.fecha else timezone.localdate(timezone=timezone.get_default_timezone()), self.hora_fin)
        
        # Si la hora de fin es menor, asumir que es al día siguiente
        if fin <= inicio:
            fin += timedelta(days=1)
        
        duracion = fin - inicio
        return round(duracion.total_seconds() / 3600, 2)  # Convertir a horas
    
    def get_tipo_uso_display(self):
        """Retorna el nombre legible del tipo de uso"""
        return dict(self.TIPO_USO_CHOICES).get(self.tipo_uso, "No especificado")
    
    # MÉTODOS DE VALIDACIÓN Y CONFLICTOS
    
    # MÉTODOS DE GESTIÓN DE ESTADO
    
    def confirmar(self, validador=None, observaciones=""):
        """
        Confirma la reserva
        
        Args:
            validador: User - Usuario que confirma la reserva
            observaciones: str - Observaciones de la confirmación
        """
        from apps.formacion.presentation.practicas_integracion import validar_compuerta_documental

        validar_compuerta_documental(self, 'aprobar')
        self.estado = validar_accion_reserva(self.estado, 'aprobar')
        if validador:
            self.validada_por = validador
            self.fecha_validacion = timezone.now()
        if observaciones:
            self.observaciones_validacion = observaciones
        self.save()
    
    def cancelar(self, motivo=""):
        """
        Cancela la reserva
        
        Args:
            motivo: str - Motivo de la cancelación
        """
        self.estado = validar_accion_reserva(
            self.estado,
            'cancelar',
            motivo=motivo or 'Cancelación registrada',
        )
        if motivo:
            self.observaciones_validacion = f"Cancelada: {motivo}"
        self.save()
    
    def registrar_cancelacion(self, *, actor, origen, motivo=''):
        """Deja constancia de la cancelación sin borrar la reserva."""
        self.estado = 'cancelada'
        self.cancelada_en = timezone.now()
        self.cancelada_por = actor if getattr(actor, 'pk', None) else None
        self.origen_cancelacion = origen
        self.motivo_cancelacion = (motivo or '').strip()
        quien = 'el solicitante' if origen == 'solicitante' else 'el laboratorio'
        nota = f"Reserva cancelada por {quien}" + (
            f": {self.motivo_cancelacion}" if self.motivo_cancelacion else ''
        )
        anterior = (self.observaciones_validacion or '').strip()
        self.observaciones_validacion = '\n'.join(
            parte for parte in (anterior, nota) if parte
        )

    # MÉTODOS DE CONSULTA
    
class NotificacionReserva(models.Model):
    """Aviso interno y trazabilidad de la entrega por correo de una reserva."""

    TIPO_CHOICES = [
        ('confirmacion', 'Confirmación de solicitud'),
        ('estado', 'Cambio de estado'),
        ('informacion', 'Información solicitada'),
        ('recordatorio_24h', 'Recordatorio 24 horas'),
        ('recordatorio_2h', 'Recordatorio 2 horas'),
        ('cierre_pendiente', 'Cierre operativo pendiente'),
        ('guia_sesion_pendiente', 'Guía de sesión pendiente'),
        ('vencimiento', 'Solicitud vencida'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificaciones_reservas',
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, db_index=True)
    titulo = models.CharField(max_length=180)
    mensaje = models.TextField()
    url = models.CharField(max_length=500, blank=True)
    clave = models.CharField(max_length=180, unique=True)
    leida = models.BooleanField(default=False, db_index=True)
    enviada_email = models.BooleanField(default=False)
    fecha_email = models.DateTimeField(null=True, blank=True)
    intentos_email = models.PositiveSmallIntegerField(default=0)
    ultimo_intento_email = models.DateTimeField(null=True, blank=True)
    error_email = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'webcitt_notificacionreserva'
        ordering = ['-creada_en', '-pk']
        verbose_name = 'Notificación de reserva'
        verbose_name_plural = 'Notificaciones de reservas'

    def __str__(self):
        return f'{self.usuario} · {self.titulo}'


class RegistroParticipanteReserva(models.Model):
    """Fotografía institucional de cada persona prevista en una reserva."""

    ROL_CHOICES = [
        ('solicitante', 'Solicitante principal'),
        ('participante', 'Participante secundario'),
    ]
    ASISTENCIA_CHOICES = [
        ('prevista', 'Participación prevista'),
        ('asistio', 'Asistió'),
        ('no_asistio', 'No asistió'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='registros_participantes',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_participacion_reservas',
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    nombre = models.CharField(max_length=180)
    correo = models.EmailField(blank=True)
    tipo_usuario = models.CharField(
        max_length=20,
        choices=tipos_usuario,
        blank=True,
        db_index=True,
    )
    facultad = models.CharField(
        max_length=50,
        choices=facultades,
        blank=True,
        db_index=True,
    )
    carrera = models.CharField(
        max_length=50,
        choices=carreras,
        blank=True,
        db_index=True,
    )
    nivel_academico = models.CharField(
        max_length=30,
        choices=niveles,
        blank=True,
    )
    institucion = models.CharField(max_length=200, blank=True)
    asistencia = models.CharField(
        max_length=20,
        choices=ASISTENCIA_CHOICES,
        default='prevista',
        db_index=True,
    )

    class Meta:
        db_table = 'webcitt_registroparticipantereserva'
        ordering = ['reserva_id', 'rol', 'nombre']
        verbose_name = 'Participante registrado en reserva'
        verbose_name_plural = 'Participantes registrados en reservas'
        constraints = [
            models.UniqueConstraint(
                fields=['reserva', 'usuario'],
                condition=models.Q(usuario__isnull=False),
                name='participante_usuario_unico_por_reserva',
            ),
        ]

    def __str__(self):
        return f'{self.reserva.codigo_reserva or self.reserva_id} · {self.nombre}'


class ReservaConsumible(models.Model):
    """Cantidad de un material o consumible solicitada con una reserva."""

    METODO_ESTIMACION_CHOICES = [
        ('simulacion', 'Calculada con laminador, simulación o software técnico'),
        ('estimacion', 'Estimación proporcionada por el solicitante'),
        ('revision', 'Cantidad por calcular durante la revisión técnica'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='consumibles_solicitados',
    )
    consumible = models.ForeignKey(
        'recursos.Consumible',
        on_delete=models.PROTECT,
        related_name='reservas_solicitantes',
    )
    cantidad_solicitada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    metodo_estimacion = models.CharField(
        max_length=20,
        choices=METODO_ESTIMACION_CHOICES,
        default='estimacion',
    )
    cantidad_aprobada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    cantidad_consumida = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    cantidad_desperdiciada = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text='Cantidad adicional retirada por falla, calidad o proceso.',
    )

    class Meta:
        db_table = 'webcitt_reservaconsumible'
        verbose_name = 'Consumible solicitado en reserva'
        verbose_name_plural = 'Consumibles solicitados en reservas'
        constraints = [
            models.UniqueConstraint(
                fields=['reserva', 'consumible'],
                name='reserva_consumible_unico',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(cantidad_solicitada__gt=0)
                    | models.Q(
                        cantidad_solicitada__isnull=True,
                        metodo_estimacion='revision',
                    )
                ),
                name='reserva_consumible_cantidad_o_revision',
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_consumida__gte=0),
                name='reserva_consumible_consumo_no_negativo',
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_desperdiciada__gte=0),
                name='reserva_consumible_desperdicio_no_negativo',
            ),
        ]

    def __str__(self):
        unidad = self.consumible.unidad_medida or 'unidades'
        if self.cantidad_solicitada is None:
            return f'{self.consumible.nombre}: cantidad por revisión técnica'
        return f'{self.consumible.nombre}: {self.cantidad_solicitada} {unidad}'

    def clean(self):
        errors = {}
        if self.consumible_id and self.reserva_id:
            unidad_id = self.consumible.unidad_id
            if unidad_id and unidad_id != self.reserva.laboratorio_id:
                errors['consumible'] = 'El consumible pertenece a otra unidad.'
        if self.cantidad_solicitada is None and self.metodo_estimacion != 'revision':
            errors['cantidad_solicitada'] = (
                'Indica una cantidad o marca que debe calcularla el laboratorista.'
            )
        limite = self.cantidad_aprobada or self.cantidad_solicitada
        if limite is not None and self.cantidad_consumida > limite:
            errors['cantidad_consumida'] = 'El consumo no puede superar la cantidad autorizada.'
        if self.cantidad_desperdiciada < 0:
            errors['cantidad_desperdiciada'] = 'El desperdicio no puede ser negativo.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RevisionReserva(models.Model):
    """Fotografía inmutable del expediente de una reserva.

    Las revisiones no sustituyen el registro operativo: permiten demostrar qué
    se solicitó originalmente y qué quedó vigente después de cada cambio
    autorizado.
    """

    TIPO_CHOICES = [
        ('inicial', 'Registro inicial'),
        ('cambio_aprobado', 'Cambio solicitado y aprobado'),
        ('correccion_admin', 'Corrección administrativa'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='revisiones',
    )
    numero = models.PositiveIntegerField()
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    estado_reserva = models.CharField(max_length=20, choices=Reserva.ESTADO_CHOICES)
    datos = models.JSONField(default=dict)
    motivo = models.TextField(blank=True)
    creada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revisiones_reserva_creadas',
    )
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'webcitt_revisionreserva'
        ordering = ['reserva_id', 'numero']
        verbose_name = 'Revisión de reserva'
        verbose_name_plural = 'Revisiones de reservas'
        constraints = [
            models.UniqueConstraint(
                fields=['reserva', 'numero'],
                name='revision_numero_unico_por_reserva',
            ),
        ]

    def __str__(self):
        codigo = self.reserva.codigo_reserva or f'RES-{self.reserva_id:06d}'
        return f'{codigo} · revisión {self.numero}'

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                'Una revisión de reserva es inmutable; crea una nueva revisión.'
            )
        return super().save(*args, **kwargs)


class SolicitudCambioReserva(models.Model):
    """Propuesta del titular que permanece separada de la reserva vigente."""

    ESTADO_CHOICES = [
        ('solicitada', 'Pendiente de autorización'),
        ('autorizada', 'Edición autorizada'),
        ('enviada', 'Propuesta enviada'),
        ('aprobada', 'Cambio aprobado y aplicado'),
        ('rechazada', 'Cambio rechazado'),
        ('vencida', 'Autorización vencida'),
        ('cancelada', 'Solicitud cancelada'),
    ]
    ESTADOS_ACTIVOS = ('solicitada', 'autorizada', 'enviada')
    CAMPOS_CHOICES = [
        ('fecha_horario', 'Fecha y horario'),
        ('actividad', 'Título, motivo y descripción'),
        ('participantes', 'Participantes'),
        ('equipos', 'Equipos'),
        ('software', 'Software'),
        ('espacios', 'Espacios'),
        ('servicios', 'Servicios'),
        ('insumos', 'Insumos y cantidades solicitadas'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='solicitudes_cambio',
    )
    solicitada_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='solicitudes_cambio_reserva',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='solicitada',
        db_index=True,
    )
    motivo_solicitud = models.TextField()
    datos_base = models.JSONField(default=dict)
    campos_autorizados = models.JSONField(default=list, blank=True)
    propuesta = models.JSONField(default=dict, blank=True)
    autorizada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_cambio_autorizadas',
    )
    autorizada_en = models.DateTimeField(null=True, blank=True)
    autorizacion_vence_en = models.DateTimeField(null=True, blank=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    revisada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_cambio_revisadas',
    )
    revisada_en = models.DateTimeField(null=True, blank=True)
    observacion_revision = models.TextField(blank=True)
    revision_aplicada = models.OneToOneField(
        RevisionReserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitud_cambio',
    )
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webcitt_solicitudcambioreserva'
        ordering = ['-creada_en', '-pk']
        verbose_name = 'Solicitud de cambio de reserva'
        verbose_name_plural = 'Solicitudes de cambio de reservas'
        constraints = [
            models.UniqueConstraint(
                fields=['reserva'],
                condition=models.Q(estado__in=('solicitada', 'autorizada', 'enviada')),
                name='una_solicitud_cambio_activa_por_reserva',
            ),
        ]

    def __str__(self):
        codigo = self.reserva.codigo_reserva or f'RES-{self.reserva_id:06d}'
        return f'{codigo} · {self.get_estado_display()}'

    @property
    def autorizacion_vencida(self):
        return bool(
            self.estado == 'autorizada'
            and self.autorizacion_vence_en
            and self.autorizacion_vence_en <= timezone.now()
        )

    @property
    def puede_editar(self):
        return self.estado == 'autorizada' and not self.autorizacion_vencida

    @property
    def campos_autorizados_display(self):
        etiquetas = dict(self.CAMPOS_CHOICES)
        return [
            etiquetas.get(campo, campo)
            for campo in (self.campos_autorizados or [])
        ]


def reserva_adjunto_upload_to(instance, filename):
    reserva_id = instance.reserva_id or 'temporal'
    return f'reservas/{reserva_id}/archivos_tecnicos/{filename}'


class ReservaAdjunto(models.Model):
    """Archivo técnico entregado para la revisión y trazabilidad de una reserva."""

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='archivos_tecnicos',
    )
    archivo = models.FileField(upload_to=reserva_adjunto_upload_to, max_length=255)
    nombre_original = models.CharField(max_length=255)
    extension = models.CharField(max_length=20, blank=True)
    tipo_contenido = models.CharField(max_length=120, blank=True)
    tamano = models.PositiveBigIntegerField(default=0)
    descripcion = models.CharField(max_length=255, blank=True)
    indicaciones_visualizacion = models.TextField(
        blank=True,
        verbose_name='Indicaciones para abrir o visualizar',
        help_text=(
            'Versión del software, programa recomendado, unidades, escala, perfiles '
            'o cualquier consideración necesaria para revisar el archivo.'
        ),
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_reservaadjunto'
        ordering = ['fecha_carga', 'pk']
        verbose_name = 'Archivo técnico de reserva'
        verbose_name_plural = 'Archivos técnicos de reservas'

    def __str__(self):
        return f'{self.reserva}: {self.nombre_original}'


def imagen_guia_upload_to(instance, filename):
    if instance.guia_id is None:
        # Cargada desde el editor antes de que exista la guia (borrador).
        return f'guias/borradores/{instance.borrador_token or "sin-token"}/{filename}'
    return f'actividades/{instance.guia.actividad_id}/guias/{instance.guia_id}/figuras/{filename}'


class ImagenGuiaActividad(models.Model):
    """Figura citada en el fundamento o el procedimiento de una guía estructurada.

    El formato anterior la referencia por posición (``![Figura 2: título](figura:2)``);
    el editor visual, por su identificador estable (``data-figura``). En ambos
    casos el contenido no depende de rutas de archivo. Una figura puede
    cargarse antes de que exista la guía (``guia`` vacía y ``borrador_token``):
    se asocia al guardar la solicitud.
    """

    guia = models.ForeignKey(
        GuiaActividadReserva,
        on_delete=models.CASCADE,
        related_name='imagenes',
        null=True,
        blank=True,
    )
    borrador_token = models.CharField(max_length=40, blank=True, db_index=True)
    subido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='figuras_guia_subidas',
    )
    imagen = models.ImageField(
        upload_to=imagen_guia_upload_to,
        max_length=255,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])],
    )
    titulo = models.CharField(max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(default=1)
    tamano = models.PositiveBigIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webcitt_imagenguiaactividad'
        ordering = ['orden', 'pk']
        verbose_name = 'Figura de guía de práctica'
        verbose_name_plural = 'Figuras de guías de práctica'

    def __str__(self):
        if self.guia_id is None:
            return f'Figura en borrador {self.borrador_token}'
        return f'{self.guia}: figura {self.orden}'


# SIGNALS



@receiver(pre_save, sender=Reserva)
def calcular_duracion_reserva(sender, instance, **kwargs):
    """Signal para calcular automáticamente la duración antes de guardar"""
    if instance.hora_inicio and instance.hora_fin:
        instance.duracion = instance.calcular_duracion()

@receiver(post_save, sender=Reserva)
def asignar_codigo_reserva(sender, instance, created, **kwargs):
    """Codigo faltante: servicio con savepoint; fallo observable no bloqueante."""
    if kwargs.get('raw') or instance.codigo_reserva:
        return
    from apps.reservas.services.codigos_reserva import EVENTO_ASIGNACION_FALLIDA, asegurar_codigo_reserva, logger
    try:
        asegurar_codigo_reserva(instance, using=kwargs.get('using'))
    except Exception:
        # No registrar mensaje/traceback, IDs, codigo, usuario, SQL o argumentos.
        logger.warning(EVENTO_ASIGNACION_FALLIDA)
