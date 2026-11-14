"""Revisión explícita: nunca deduce pertenencia del correo o nombre visible."""

from secrets import compare_digest

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.pertenencia import huella_revision, identidad_revisable
from apps.core.presentation.identidad import identidad_actual
from apps.core.presentation.catalogos import tipos_usuario
from apps.core.presentation.catalogo_institucional import con_catalogo_institucional
from apps.core.presentation.niveles_institucionales import con_niveles_institucionales
from apps.core.models.usuarios_base import UserProfile
from apps.core.models.verificaciones import VerificacionInstitucional


PERMISO_REVISION = 'core.revisar_pertenencia_institucional'


def puede_revisar(revisor, perfil=None):
    return bool(
        revisor and revisor.is_authenticated and revisor.pk
        and revisor.is_active and revisor.is_staff
        and revisor.has_perm(PERMISO_REVISION)
        and (revisor.has_perm('core.view_userprofile')
             or revisor.has_perm('core.change_userprofile'))
        and (perfil is None or revisor.pk != perfil.user_id)
    )


def identidad_del_perfil(perfil):
    return identidad_revisable(identidad_actual()[1].siglas, {
        'usuario_id': perfil.user_id,
        'nombre': perfil.user.first_name, 'apellidos': perfil.user.last_name,
        'correo': perfil.user.email, 'tipo_usuario': perfil.tipo_usuario,
        'institucion': perfil.institucion, 'facultad': perfil.facultad,
        'carrera': perfil.carrera, 'documento': perfil.cedula,
    })


@con_catalogo_institucional()
@con_niveles_institucionales()
def estado_verificacion(perfil):
    """La última decisión manda; una aprobación previa no revive al rechazar."""
    ultima = perfil.verificaciones_institucionales.first()
    identidad = identidad_del_perfil(perfil)
    estado = ultima.decision if ultima else 'pendiente'
    if estado not in VerificacionInstitucional.Decision.values:
        estado = 'pendiente'
    if ultima and estado == 'aprobada':
        if ultima.identidad_revisada != identidad:
            estado = 'datos_modificados'
        elif not perfil.perfil_reserva_completo or perfil.tipo_usuario not in dict(tipos_usuario()):
            estado = 'datos_modificados'
        elif ultima.vigente_hasta and ultima.vigente_hasta < timezone.localdate():
            estado = 'vencida'
        elif not perfil.user.is_active:
            estado = 'cuenta_inactiva'
    etiquetas = {
        'pendiente': _('Pendiente de revisión institucional'),
        'aprobada': _('Pertenencia y tipo de usuario verificados'),
        'rechazada': _('Verificación rechazada'),
        'revocada': _('Verificación revocada'),
        'datos_modificados': _('Datos modificados: requiere nueva revisión'),
        'vencida': _('Verificación vencida'),
        'cuenta_inactiva': _('Cuenta inactiva'),
    }
    return {
        'codigo': estado, 'etiqueta': etiquetas[estado],
        'verificada': estado == 'aprobada', 'ultima': ultima,
        'huella': huella_revision(identidad, ultima.pk if ultima else None),
    }


@con_catalogo_institucional()
@con_niveles_institucionales()
@transaction.atomic
def registrar_revision(*, perfil_id, revisor, decision, fundamento, referencia,
                       huella, vigente_hasta=None):
    """Bloquea la identidad y rechaza formularios abiertos antes de otro cambio."""
    if not puede_revisar(revisor):
        raise PermissionDenied
    revisor = get_user_model().objects.get(pk=revisor.pk)
    if not puede_revisar(revisor):
        raise PermissionDenied
    user_id = UserProfile.objects.values_list('user_id', flat=True).get(pk=perfil_id)
    usuario = get_user_model().objects.select_for_update().get(pk=user_id)
    perfil = UserProfile.objects.select_for_update().get(pk=perfil_id)
    perfil.user = usuario
    if not puede_revisar(revisor, perfil):
        raise PermissionDenied
    estado = estado_verificacion(perfil)
    if (not isinstance(huella, str) or not huella.isascii()
            or not compare_digest(estado['huella'], huella)):
        raise ValidationError(_('Los datos o la revisión cambiaron. Recarga antes de decidir.'))
    if decision not in VerificacionInstitucional.Decision.values:
        raise ValidationError(_('Selecciona una decisión válida.'))
    if (not isinstance(fundamento, str) or not isinstance(referencia, str)
            or not fundamento.strip() or not referencia.strip()):
        raise ValidationError(_('Indica el fundamento y la referencia de la evidencia.'))
    if decision == 'aprobada':
        if not usuario.is_active or not perfil.perfil_reserva_completo:
            raise ValidationError(_('Solo se pueden aprobar cuentas activas con datos completos.'))
        perfil.full_clean()
        if perfil.tipo_usuario != 'externo' and perfil.institucion != identidad_actual()[1].siglas:
            raise ValidationError(_('La procedencia interna debe coincidir con la institución configurada.'))
        if vigente_hasta and vigente_hasta < timezone.localdate():
            raise ValidationError(_('La vigencia no puede terminar en el pasado.'))
    else:
        vigente_hasta = None
    if decision == 'revocada' and not perfil.verificaciones_institucionales.filter(
        decision='aprobada', identidad_revisada__institucion_codigo=identidad_actual()[1].siglas,
    ).exists():
        raise ValidationError(_('No existe una aprobación que se pueda revocar.'))
    revision = VerificacionInstitucional(
        perfil=perfil, revisor=revisor, decision=decision,
        identidad_revisada=identidad_del_perfil(perfil),
        fundamento=fundamento.strip(), referencia=referencia.strip(),
        vigente_hasta=vigente_hasta,
    )
    revision.full_clean()
    revision.save(_desde_revision=True)
    return revision
