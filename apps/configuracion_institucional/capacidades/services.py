"""Cambios auditados con autoridad fresca y control optimista de version."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.persistence.publicacion import actor_con_permiso
from .models import CambioCapacidad
from .selectors import bloquear_habilitacion


@transaction.atomic
def cambiar_habilitacion(modulo, capacidad, habilitada, usuario, *, version_esperada, motivo):
    autor = actor_con_permiso(usuario, 'configuracion_institucional.administrar_capacidades',
                             lectura='configuracion_institucional.view_estadocapacidad')
    if type(habilitada) is not bool or type(version_esperada) is not int or version_esperada < 0:
        raise ValidationError(_('Revisa el estado y la versión de la capacidad.'))
    estado = bloquear_habilitacion(modulo, capacidad)
    if estado.version != version_esperada:
        raise ValidationError(_('La habilitación cambió. Recarga antes de confirmar.'))
    if estado.habilitada == habilitada:
        raise ValidationError(_('La capacidad ya tiene ese estado.'))
    cambio = CambioCapacidad(estado=estado, habilitada_anterior=estado.habilitada,
                             habilitada_nueva=habilitada, version=estado.version + 1,
                             motivo=motivo, autor=autor)
    cambio.full_clean()
    cambio.save(_desde_control=True)
    estado.habilitada = habilitada
    estado.version = cambio.version
    estado.save(_desde_control=True, update_fields=('habilitada', 'version'))
    return cambio
