from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.utils.translation import gettext

from apps.core.roles import validar_delegacion

from apps.directorio_unidades.models.core import Unidad


class EspacioReservable(models.Model):
    """Área, estación o puesto concreto que puede reservarse dentro de una unidad."""

    TIPO_CHOICES = [
        ('area', 'Área de trabajo'),
        ('estacion', 'Estación de trabajo'),
        ('sala', 'Sala'),
        ('puesto', 'Puesto individual'),
        ('cabina', 'Cabina o espacio especializado'),
        ('taller', 'Taller'),
        # Plantas piloto y centros experimentales.
        ('linea', 'Línea de proceso'),
        ('camara', 'Cámara de frío o almacén'),
        ('parcela', 'Parcela o lote de campo'),
        ('invernadero', 'Invernadero'),
        ('establo', 'Establo o corral'),
        ('otro', 'Otro espacio'),
    ]
    POLITICA_RESERVA_CHOICES = [
        (
            'general',
            'Uso general: puede reservarse solo con mobiliario',
        ),
        (
            'mixto',
            'Uso mixto: espacio solo o con recursos técnicos',
        ),
        (
            'tecnico',
            'Uso técnico: exige equipo o software asociado',
        ),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='espacios_reservables',
    )
    codigo = models.CharField(
        'Código',
        max_length=60,
        help_text='Código único dentro de la unidad, por ejemplo FAB-AREA-IMP3D.',
    )
    nombre = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='area')
    descripcion_publica = models.TextField(
        'Descripción pública',
        blank=True,
        help_text='Explica al solicitante qué puede realizar en este espacio.',
    )
    ubicacion = models.CharField(
        max_length=255,
        blank=True,
        help_text='Referencia física dentro de la unidad.',
    )
    superficie_m2 = models.DecimalField(
        'Superficie (m²)', max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Superficie útil del espacio; en parcelas e invernaderos, el área cultivable.',
    )
    capacidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Número máximo recomendado de usuarios simultáneos.',
    )
    imagen = models.ImageField(
        upload_to='espacios_reservables/',
        blank=True,
        null=True,
        help_text='Imagen pública opcional del área o estación.',
    )
    caracteristicas = models.TextField(
        blank=True,
        help_text='Equipamiento, dimensiones o condiciones relevantes para elegir el espacio.',
    )
    mobiliario_incluido = models.TextField(
        'Mobiliario e infraestructura incluidos',
        blank=True,
        help_text=(
            'Mesas, sillas, tomas eléctricas, red, proyector u otros elementos que '
            'se incluyen automáticamente al reservar el espacio y no se seleccionan '
            'como equipos técnicos.'
        ),
    )
    politica_reserva = models.CharField(
        'Política de reserva',
        max_length=20,
        choices=POLITICA_RESERVA_CHOICES,
        default='mixto',
        help_text=(
            'Define si el espacio puede reservarse únicamente con su mobiliario, '
            'si admite ambos usos o si siempre exige un equipo o software asociado.'
        ),
    )
    equipos_asociados = models.ManyToManyField(
        'recursos.UnidadEquipo', db_table='webcitt_espacioreservable_equipos_asociados',
        blank=True,
        related_name='espacios_asociados',
        help_text=(
            'Equipos técnicos ubicados o disponibles en este espacio. La política '
            'de reserva determina si su selección es obligatoria u opcional.'
        ),
    )
    instrucciones_uso = models.TextField(
        'Instrucciones de uso',
        blank=True,
        help_text='Preparación, seguridad y forma de uso visible para el solicitante.',
    )
    activo = models.BooleanField(default=True)
    desactivados_con_el_area = models.JSONField(
        'Desactivados junto con el área', default=dict, blank=True, editable=False,
        help_text='Equipos, software e insumos que se desactivaron con el área y vuelven con ella al reactivarla.',
    )
    integrada_en = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='areas_integradas',
        verbose_name='Integrada en',
        help_text='El área que recibió sus equipos, su ficha y sus reservas al fusionarse; la página vieja lleva a ella.',
    )
    reservable = models.BooleanField(
        default=True,
        help_text='Permite seleccionar este espacio en una nueva solicitud.',
    )
    visitable = models.BooleanField(
        default=False,
        help_text='Forma parte del recorrido que se ofrece a las visitas guiadas.',
    )
    orden = models.PositiveIntegerField(default=0)
    responsable = models.ForeignKey(
        'gestion_unidades.ResponsableUnidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='areas_a_cargo',
        help_text='Quién coordina el área y responde por ella; se elige entre el personal de la unidad.',
    )

    class Meta:
        db_table = 'webcitt_espacioreservable'
        verbose_name = 'Espacio reservable'
        verbose_name_plural = 'Espacios reservables'
        ordering = ['orden', 'nombre', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['unidad', 'codigo'],
                name='espacio_codigo_unico_por_unidad',
            ),
        ]

    def __str__(self):
        return f'{self.nombre} · {self.unidad.nombre}'

    def clean(self):
        super().clean()
        if self.responsable_id and self.responsable.unidad_id != self.unidad_id:
            raise ValidationError({'responsable': 'El responsable debe ser personal de la misma unidad.'})

    @property
    def imagen_publica_url(self):
        """Usa la foto administrada y conserva una muestra visual en datos demo."""
        return self.imagen_propia_url or static('img/generated/home-hero/hero-fabricacion-avanzada.png')

    @property
    def imagen_propia_url(self):
        """La foto del área, o la de su tipo de trabajo en datos demo; vacía si no hay ninguna que la represente."""
        if self.imagen:
            try:
                return self.imagen.url
            except ValueError:
                pass
        reference = f'{self.codigo} {self.nombre}'.lower()
        fallbacks = (
            (('laser', 'láser'), 'img/catalogo/fablab/equipos/cortadora-laser.png'),
            (('cnc', 'fresado', 'mecanizado'), 'img/catalogo/fablab/equipos/fresadora-cnc.png'),
            (('scan', 'escaneo', 'digitalizacion', 'digitalización'), 'img/catalogo/fablab/equipos/escaner-3d.png'),
            (('resina', 'sla'), 'img/catalogo/fablab/equipos/impresora-3d-resina.png'),
            (('imp3d', 'impresión', 'impresion', 'fdm'), 'img/catalogo/fablab/equipos/impresora-3d-fdm.png'),
        )
        for keywords, asset in fallbacks:
            if any(keyword in reference for keyword in keywords):
                return static(asset)
        return ''

    @property
    def equipos_asociados_ids_csv(self):
        """Todos los equipos asociados, también las referencias: lo usa el formulario de gestión del área."""
        return ','.join(str(equipo.pk) for equipo in self.equipos_asociados.all())

    @property
    def equipos_existentes(self):
        """Los equipos asociados que existen: activos y sin baja. Una referencia no se muestra ni se ofrece."""
        return [equipo for equipo in self.equipos_asociados.all() if equipo.activa and not equipo.fecha_baja]

    @property
    def equipos_existentes_ids_csv(self):
        return ','.join(str(equipo.pk) for equipo in self.equipos_existentes)

    @property
    def equipos_asociados_resumen(self):
        return ', '.join(
            f'{equipo.equipo.nombre} · {equipo.codigo_unidad}'
            for equipo in self.equipos_existentes
        )

    @property
    def software_asociado_resumen(self):
        nombres = {
            software.nombre
            for equipo in self.equipos_existentes
            for software in equipo.software_instalado.all()
            if software.activo and software.requiere_reserva
        }
        return ', '.join(sorted(nombres))

    @property
    def requiere_recurso_tecnico(self):
        return self.politica_reserva == 'tecnico'

class ResponsableUnidad(models.Model):
    """Persona o punto de contacto que puede asumir solicitudes de una unidad."""

    ROL_CHOICES = [
        ('coordinacion', 'Coordinación de la unidad'),
        ('responsable_tecnico', 'Responsable técnico'),
        ('laboratorista', 'Laboratorista'),
        ('tecnico', 'Técnico especialista'),
        ('soporte', 'Soporte operativo'),
        ('otro', 'Otro rol'),
    ]

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.CASCADE,
        related_name='responsables_unidad',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responsabilidades_en_unidades',
        help_text='Cuenta institucional opcional vinculada al responsable.',
    )
    nombre = models.CharField(
        max_length=160,
        blank=True,
        help_text='Nombre público o denominación del punto de contacto.',
    )
    rol = models.CharField(max_length=30, choices=ROL_CHOICES, default='laboratorista')
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=60, blank=True)
    foto = models.ImageField(
        upload_to='unidades/responsables/',
        blank=True,
        null=True,
        help_text='Fotografía pública del responsable. Si se omite, se usa el avatar de su perfil institucional.',
    )
    foto_referencial = models.CharField(
        max_length=255,
        blank=True,
        help_text='Ruta de una imagen estática usada únicamente para datos demostrativos.',
    )
    descripcion = models.CharField(
        max_length=240,
        blank=True,
        help_text='Breve descripción de su función o especialidad visible al solicitante.',
    )
    horario_atencion = models.CharField(
        max_length=120,
        blank=True,
        help_text='Horario o modalidad habitual de contacto.',
    )
    formacion = models.CharField(
        'Título o formación',
        max_length=200,
        blank=True,
        help_text='Título profesional o formación que respalda su función en la unidad.',
    )
    acto_designacion = models.CharField(
        'Acto de designación',
        max_length=200,
        blank=True,
        help_text='Documento con que fue designado: tipo y número (resolución, memorando, acción de personal).',
    )
    fecha_designacion = models.DateField(
        'Fecha de designación',
        null=True,
        blank=True,
        help_text='Fecha del acto de designación.',
    )
    publico = models.BooleanField(
        default=True,
        help_text='Muestra sus datos de contacto en la información pública de la unidad.',
    )
    recibe_reservas = models.BooleanField(
        default=False,
        help_text=(
            'Permite asignarle solicitudes desde la gestión interna. Requiere '
            'una cuenta institucional vinculada.'
        ),
    )
    permisos_operativos = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Permisos granulares del panel de gestión. Un valor ausente conserva '
            'la configuración recomendada para el rol.'
        ),
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'webcitt_responsableunidad'
        verbose_name = 'Responsable de unidad'
        verbose_name_plural = 'Responsables de unidad'
        ordering = ['orden', 'nombre', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['unidad', 'usuario'],
                condition=models.Q(usuario__isnull=False),
                name='uniq_responsable_usuario_por_unidad',
            ),
        ]

    def __str__(self):
        return f'{self.nombre_publico} · {self.get_rol_display()}'

    @property
    def nombre_publico(self):
        if self.nombre:
            return self.nombre
        if self.usuario_id:
            return self.usuario.get_full_name() or self.usuario.get_username()
        return 'Responsable sin identificar'

    @property
    def email_publico(self):
        if self.email:
            return self.email
        if self.usuario_id:
            return self.usuario.email
        return ''

    @property
    def telefono_publico(self):
        if self.telefono:
            return self.telefono
        if self.usuario_id:
            perfil = getattr(self.usuario, 'profile', None)
            if perfil:
                return perfil.telefono or ''
        return ''

    @property
    def foto_publica_url(self):
        if self.foto:
            try:
                return self.foto.url
            except ValueError:
                pass
        if self.usuario_id:
            perfil = getattr(self.usuario, 'profile', None)
            if perfil and perfil.avatar:
                try:
                    return perfil.avatar.url
                except ValueError:
                    pass
        if self.foto_referencial:
            return static(self.foto_referencial)
        return ''

    @property
    def descripcion_publica(self):
        """Qué hace la persona en la unidad.

        Manda lo que declaró la unidad; si no lo declaró, se aprovecha lo que
        la propia persona escribió en su perfil, que para eso se le pide.
        """
        if self.descripcion:
            return self.descripcion
        if self.usuario_id:
            perfil = getattr(self.usuario, 'profile', None)
            if perfil:
                return (perfil.cargo or perfil.biografia or '')[:240]
        return ''

    @property
    def iniciales(self):
        partes = [parte for parte in self.nombre_publico.replace('.', ' ').split() if parte]
        if not partes:
            return 'RU'
        return ''.join(parte[0] for parte in partes[:2]).upper()

    @property
    def es_administrador_principal(self):
        """La fuente única del responsable principal es Unidad.administrador."""
        return bool(
            self.usuario_id
            and self.unidad_id
            and self.unidad.administrador_id == self.usuario_id
        )

    def clean(self):
        errors = {}
        if not self.usuario_id and not (self.nombre or '').strip():
            errors['nombre'] = 'Registra un usuario institucional o el nombre del responsable.'
        if not self.usuario_id and not (
            (self.email or '').strip() or (self.telefono or '').strip()
        ):
            errors['email'] = 'Registra un correo o teléfono cuando no existe un usuario vinculado.'
        if not self.usuario_id and self.recibe_reservas:
            errors['recibe_reservas'] = (
                'Vincula una cuenta institucional antes de habilitar la asignación de reservas.'
            )
        try:
            validar_delegacion(self.permisos_operativos)
        except ValueError as exc:
            errors['permisos_operativos'] = gettext(str(exc))
        else:
            if not self.usuario_id and any(self.permisos_operativos.values()):
                errors['permisos_operativos'] = (
                    'Los permisos del panel requieren una cuenta institucional vinculada.'
                )
        if errors:
            raise ValidationError(errors)
