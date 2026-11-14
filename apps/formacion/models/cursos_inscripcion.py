"""Cómo se entra a un curso: gratis, pagando (con un código de descuento si se tiene) o por matrícula de la unidad.

Un curso con costo recibe el pago por los medios que la unidad habilita (transferencia o depósito, pago en ventanilla
o un enlace de pago en línea) y la unidad lo verifica con el comprobante; al verificarlo, la persona entra al curso.
Un código de descuento rebaja el costo y, al 100 %, lo exonera. La unidad también matricula directamente a una persona
o a un grupo, por usuario o por correo; a quien todavía no tiene cuenta le queda una invitación que se activa cuando
entra a la plataforma con ese correo.
"""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.text import slugify

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso

MEDIOS_DE_PAGO = [
    ('transferencia', 'Transferencia o depósito bancario'),
    ('ventanilla', 'Pago en ventanilla o recaudación de la institución'),
    ('enlace', 'Pago en línea (tarjeta)'),
]


class CodigoDescuento(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='codigos_descuento', verbose_name='Curso')
    codigo = models.CharField('Código', max_length=30, help_text='Lo que la persona escribe al inscribirse, por ejemplo «BECA2026».')
    descripcion = models.CharField('Para quién es', max_length=160, blank=True)
    porcentaje = models.PositiveSmallIntegerField('Descuento (%)', validators=[MinValueValidator(1), MaxValueValidator(100)],
                                                  help_text='100 %: el curso queda gratis para quien lo use.')
    usos_maximos = models.PositiveIntegerField('Usos permitidos', null=True, blank=True, help_text='Vacío: sin límite.')
    vigente_hasta = models.DateField('Válido hasta', null=True, blank=True)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        db_table = 'webcitt_codigodescuento'
        ordering = ('codigo',)
        verbose_name = 'Código de descuento'
        verbose_name_plural = 'Códigos de descuento'
        constraints = [models.UniqueConstraint(fields=('curso', 'codigo'), name='codigo_descuento_unico_por_curso')]

    def __str__(self):
        return f'{self.codigo} · {self.porcentaje} %'

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or '').strip().upper()
        super().save(*args, **kwargs)

    @property
    def usos(self):
        """Los usos que cuentan: los de inscripciones que siguen en pie (no las rechazadas ni retiradas)."""
        return (self.pagos.exclude(estado='rechazado')
                .exclude(inscripcion__estado__in=('rechazada', 'retirada')).count())

    def motivo_invalido(self, hoy=None):
        """Por qué no se puede usar ahora, o '' si se puede."""
        hoy = hoy or timezone.localdate()
        if not self.activo:
            return 'Ese código ya no está activo.'
        if self.vigente_hasta and hoy > self.vigente_hasta:
            return 'Ese código venció.'
        if self.usos_maximos is not None and self.usos >= self.usos_maximos:
            return 'Ese código ya se usó todas las veces permitidas.'
        return ''


def ruta_comprobante(instancia, nombre_original):
    """Fuera del alias público: el comprobante solo lo ven quien pagó y quien verifica."""
    curso = instancia.inscripcion.edicion.curso
    persona = slugify(instancia.inscripcion.usuario.get_username())[:40] or 'persona'
    return f'cursos/comprobantes/{curso.codigo}/{persona}-{timezone.now():%Y%m%d%H%M%S}{Path(nombre_original).suffix.lower()}'


class PagoInscripcion(models.Model):
    ESTADOS = [('pendiente', 'Por verificar'), ('verificado', 'Verificado'), ('rechazado', 'Rechazado'),
               ('exonerado', 'Sin costo')]

    inscripcion = models.OneToOneField(InscripcionCurso, on_delete=models.CASCADE, related_name='pago',
                                       verbose_name='Inscripción')
    monto_original = models.DecimalField('Costo del curso (USD)', max_digits=8, decimal_places=2)
    codigo = models.ForeignKey(CodigoDescuento, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos',
                               verbose_name='Código de descuento')
    descuento = models.PositiveSmallIntegerField('Descuento (%)', default=0)
    monto = models.DecimalField('A pagar (USD)', max_digits=8, decimal_places=2)
    medio = models.CharField('Medio de pago', max_length=14, choices=MEDIOS_DE_PAGO, blank=True)
    referencia = models.CharField('Número de comprobante o transacción', max_length=80, blank=True)
    comprobante = models.FileField('Comprobante', upload_to=ruta_comprobante, blank=True,
                                   validators=[FileExtensionValidator(('pdf', 'png', 'jpg', 'jpeg', 'webp'))])
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS, default='pendiente')
    registrado = models.DateTimeField('Registrado', auto_now_add=True)
    verificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='+', verbose_name='Verificado por')
    verificado_en = models.DateTimeField('Verificado', null=True, blank=True)
    observacion = models.CharField('Observación', max_length=300, blank=True)

    class Meta:
        db_table = 'webcitt_pagoinscripcion'
        verbose_name = 'Pago de inscripción'
        verbose_name_plural = 'Pagos de inscripciones'

    def __str__(self):
        return f'{self.inscripcion} · {self.monto} USD · {self.get_estado_display()}'

    def clean(self):
        super().clean()
        if self.codigo_id and self.inscripcion_id and self.codigo.curso_id != self.inscripcion.edicion.curso_id:
            raise ValidationError({'codigo': 'El código de descuento y la matrícula deben pertenecer al mismo curso.'})
        if self.monto and self.estado == 'pendiente' and not (self.comprobante or self.referencia):
            raise ValidationError('Adjunte el comprobante o escriba el número de la transacción.')


def monto_con_descuento(costo, porcentaje):
    return (Decimal(costo) * (100 - porcentaje) / 100).quantize(Decimal('0.01'))


class InvitacionCurso(models.Model):
    """Una matrícula por correo para quien aún no tiene cuenta; se vuelve inscripción cuando entra con ese correo."""
    edicion = models.ForeignKey(EdicionCurso, on_delete=models.CASCADE, related_name='invitaciones', verbose_name='Edición')
    correo = models.EmailField('Correo')
    nombres_completos = models.CharField('Nombres y apellidos completos', max_length=200, blank=True)
    documento = models.CharField('Cédula o documento de identidad', max_length=30, blank=True)
    activa = models.BooleanField('Matrícula vigente', default=True)
    exonerar_matricula = models.BooleanField('Matrícula sin costo autorizada por la unidad', default=True)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+',
                                   verbose_name='Matriculado por')
    creada = models.DateTimeField('Creada', auto_now_add=True)
    inscripcion = models.OneToOneField(InscripcionCurso, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='invitacion', verbose_name='Inscripción creada')

    class Meta:
        db_table = 'webcitt_invitacioncurso'
        ordering = ('-creada',)
        verbose_name = 'Invitación a un curso'
        verbose_name_plural = 'Invitaciones a cursos'
        indexes = [models.Index(fields=('edicion', 'activa'), name='curso_invit_edicion_activa_idx')]
        constraints = [
            models.UniqueConstraint(Lower('correo'), 'edicion', name='invitacion_curso_correo_unico'),
            models.UniqueConstraint(fields=('edicion', 'documento'),
                                    condition=models.Q(activa=True) & ~models.Q(documento=''),
                                    name='invitacion_curso_documento_unico'),
        ]

    def __str__(self):
        return f'{self.correo} · {self.edicion}'

    def clean(self):
        from apps.core.models.datos_matricula import normalizar_correo, validar_datos_matricula
        super().clean()
        if self.inscripcion_id and self.edicion_id and self.inscripcion.edicion_id != self.edicion_id:
            raise ValidationError({'inscripcion': 'La invitación y su matrícula deben pertenecer al mismo grupo.'})
        self.correo = normalizar_correo(self.correo)
        if self.nombres_completos or self.documento:
            datos = validar_datos_matricula(nombres_completos=self.nombres_completos, documento=self.documento)
            self.nombres_completos, self.documento = datos['nombres_completos'], datos['documento']

    def save(self, *args, **kwargs):
        self.correo = (self.correo or '').strip().lower()
        super().save(*args, **kwargs)


class ClaseGrupoCurso(models.Model):
    """Grabación privada de una lección compartida, limitada a su grupo."""
    edicion = models.ForeignKey(EdicionCurso, on_delete=models.CASCADE, related_name="clases_en_vivo")
    leccion = models.ForeignKey('formacion.LeccionCurso', on_delete=models.CASCADE, related_name="clases_por_grupo")
    grabacion_url = models.URLField("Enlace de grabación", max_length=500, blank=True)
    grabacion_id = models.CharField("Identificador de grabación", max_length=100, blank=True)

    class Meta:
        db_table = 'webcitt_clasegrupocurso'
        constraints = [models.UniqueConstraint(fields=("edicion", "leccion"), name="clase_unica_por_grupo")]
        verbose_name = "Clase en vivo del grupo"
        verbose_name_plural = "Clases en vivo de los grupos"

    def clean(self):
        if self.edicion_id and self.leccion_id and self.edicion.curso_id != self.leccion.modulo.curso_id:
            raise ValidationError("La lección y el grupo deben pertenecer al mismo curso.")
