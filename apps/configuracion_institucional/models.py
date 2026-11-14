"""Revisiones publicas inmutables y un puntero a la publicacion vigente."""

from .niveles.models import PublicacionNivelesAcademicos as PublicacionNivelesAcademicos
from .niveles.models import RevisionNivelesAcademicos as RevisionNivelesAcademicos
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.identidad import validar_logo, validar_texto
from apps.core.paleta import validar_paleta
from apps.core.presentation.identidad import resolver_logo_estatico
from .imagenes import CAMPOS_IMAGENES, almacen_logos
from .versionado import HistorialInstitucionalQuerySet as HistorialPresentacionQuerySet
from .catalogos.models import PublicacionCatalogoAcademico as PublicacionCatalogoAcademico
from .catalogos.models import RevisionCatalogoAcademico as RevisionCatalogoAcademico
from .calendario.models import PublicacionPoliticaCalendario as PublicacionPoliticaCalendario
from .calendario.models import RevisionPoliticaCalendario as RevisionPoliticaCalendario
from .capacidades.models import EstadoCapacidad as EstadoCapacidad
from .capacidades.models import CambioCapacidad as CambioCapacidad
from .tipologias.models import TipologiaUnidad as TipologiaUnidad


CAMPOS_PRESENTACION = (
    'nombre_producto', 'nombre_corto_producto', 'nombre_institucion',
    'telefono', 'correo', 'ubicacion', 'logo', 'logo_secundario', 'paleta',
) + CAMPOS_IMAGENES


class RevisionPresentacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'borrador', _('Borrador')
        PUBLICADA = 'publicada', _('Publicada')

    institucion_codigo = models.CharField(max_length=200, editable=False)
    producto_codigo = models.CharField(max_length=250, editable=False)
    nombre_producto = models.CharField(_('Nombre del sistema'), max_length=250)
    nombre_corto_producto = models.CharField(_('Nombre corto del sistema'), max_length=250)
    nombre_institucion = models.CharField(_('Nombre de la institución'), max_length=250)
    telefono = models.CharField(_('Teléfono público'), max_length=250, blank=True)
    correo = models.CharField(_('Correo público'), max_length=250, blank=True)
    ubicacion = models.CharField(_('Ubicación pública'), max_length=250, blank=True)
    logo = models.CharField(_('Logo de respaldo instalado'), max_length=250, blank=True,
                            help_text=_('Solo si no subes ningún logotipo arriba: ruta de una imagen ya instalada en '
                                       'los archivos estáticos del despliegue, por ejemplo img/logo_upec.png. '
                                       'Vacío y sin logotipos subidos, se muestran las siglas.'))
    logo_secundario = models.CharField(_('Logo secundario de respaldo instalado'), max_length=250, blank=True,
                            help_text=_('Equivalente al anterior para la segunda marca de los documentos.'))
    paleta = models.JSONField(_('Paleta institucional'), default=dict, db_default={}, blank=True)
    logo_claro = models.ImageField(_('Logo principal sobre fondo claro'), storage=almacen_logos, blank=True, default='', db_default='',
        help_text=_('Es el logotipo que más se usa: comprobantes, guías y todos los PDF sobre papel blanco, y las '
                   'pantallas de fondo claro. Recomendado 600 × 180 px. PNG transparente, JPEG o WebP; máximo 2 MB. Opcional.'))
    logo_oscuro = models.ImageField(_('Logo principal sobre fondo oscuro'), storage=almacen_logos, blank=True, default='', db_default='',
        help_text=_('Versión clara de la marca para la cabecera del portal, las portadas de las páginas y la franja '
                   'oscura de los reportes. Recomendado 600 × 180 px. PNG transparente, JPEG o WebP; máximo 2 MB. Opcional.'))
    logo_movil_claro = models.ImageField(_('Logo compacto sobre fondo claro'), storage=almacen_logos, blank=True, default='', db_default='',
        help_text=_('Solo para pantallas de celular, donde el logotipo ancho no cabe. Si lo dejas vacío se usa el '
                   'logotipo principal. Recomendado 256 × 256 px. PNG transparente, JPEG o WebP; máximo 2 MB. Opcional.'))
    logo_movil_oscuro = models.ImageField(_('Logo compacto sobre fondo oscuro'), storage=almacen_logos, blank=True, default='', db_default='',
        help_text=_('El compacto para la cabecera del portal en celular. Si lo dejas vacío se usa el logotipo '
                   'principal. Recomendado 256 × 256 px. PNG transparente, JPEG o WebP; máximo 2 MB. Opcional.'))
    logo_secundario_subido = models.ImageField(_('Segunda marca para documentos'), storage=almacen_logos, blank=True, default='', db_default='',
        help_text=_('Marca acompañante —facultad, acreditación o programa— que se imprime junto a la principal en el '
                   'reporte de reservas. No aparece en el portal. Recomendado 600 × 180 px. PNG transparente, JPEG o WebP; máximo 2 MB. Opcional.'))
    estado = models.CharField(_('Estado'), max_length=10, choices=Estado.choices, editable=False)
    basada_en = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='+', editable=False, verbose_name=_('Publicación de base'))
    fuente = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                              related_name='+', editable=False, verbose_name=_('Revisión de origen'))
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name='+', editable=False, verbose_name=_('Responsable'))
    fecha = models.DateTimeField(_('Fecha'), auto_now_add=True)

    objects = HistorialPresentacionQuerySet.as_manager()

    class Meta:
        ordering = ('-pk',)
        verbose_name = _('Presentación institucional')
        verbose_name_plural = _('Presentaciones institucionales')
        permissions = (('publicar_presentacion', 'Publicar presentacion institucional'),)

    def __str__(self):
        return f'{self.nombre_corto_producto} · {self.get_estado_display()} #{self.pk or "—"}'

    def clean(self):
        errores = {}
        for campo in CAMPOS_PRESENTACION:
            try:
                if campo in CAMPOS_IMAGENES:
                    archivo = getattr(self, campo)
                    if archivo and archivo._committed:
                        from apps.core.identidad import validar_imagen_subida
                        validar_imagen_subida(archivo.name)
                        if not archivo.storage.exists(archivo.name):
                            errores[campo] = _('La imagen guardada no está disponible. Restáurala desde un respaldo o sube una nueva.')
                    continue
                if campo == 'paleta':
                    self.paleta = dict(validar_paleta(self.paleta))
                    continue
                validar_texto(getattr(self, campo), obligatorio=campo.startswith('nombre'))
                if campo.startswith('logo'):
                    validar_logo(getattr(self, campo))
                    if getattr(self, campo) and not resolver_logo_estatico(getattr(self, campo)):
                        errores[campo] = _('La imagen debe estar instalada en archivos estáticos antes de publicar.')
                if campo == 'correo' and self.correo:
                    validate_email(self.correo)
            except (ValueError, ValidationError) as exc:
                if campo == 'paleta':
                    errores[campo] = _(str(exc))
                    continue
                errores[campo] = _('Revisa el formato: texto simple, correo válido o imagen estática local.')
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        autorizado = kwargs.pop('_desde_editor', False)
        if not autorizado or not self._state.adding or self.pk is not None:
            raise ValidationError(_('Usa el editor; las revisiones guardadas no se pueden modificar.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('El historial de presentación no se puede modificar.'))


class PublicacionInstitucional(models.Model):
    """Una instalacion, un puntero; publicar no reescribe revisiones anteriores."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    revision = models.ForeignKey(RevisionPresentacion, null=True, blank=True,
                                 on_delete=models.PROTECT, related_name='+')
    objects = HistorialPresentacionQuerySet.as_manager()

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='institucion_publicacion_unica')]

    def save(self, *args, **kwargs):
        if not kwargs.pop('_desde_editor', False):
            raise ValidationError(_('Usa el editor de presentación institucional.'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(_('Usa el editor de presentación institucional.'))
