"""Historial inmutable, autoridad fresca y bloqueo de punteros de publicación."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, models, transaction
from django.utils.translation import gettext_lazy as _


class HistorialInstitucionalQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError(_('El historial institucional no se puede modificar.'))

    def delete(self):
        raise ValidationError(_('El historial institucional no se puede modificar.'))

    def bulk_create(self, objs, **kwargs):
        raise ValidationError(_('Usa el editor institucional.'))


def actor_con_permiso(usuario, permiso, *, lectura=None):
    if not usuario or not usuario.is_authenticated:
        raise PermissionDenied
    try:
        autor = get_user_model().objects.select_for_update().get(pk=usuario.pk)
    except get_user_model().DoesNotExist:
        raise PermissionDenied from None
    if (not autor.is_active or not autor.is_staff or not autor.has_perm(permiso)
            or (lectura and not autor.has_perm(lectura))):
        raise PermissionDenied
    return autor


def bloquear_publicacion(modelo):
    try:
        return modelo.objects.select_for_update().get(pk=1)
    except modelo.DoesNotExist:
        try:
            with transaction.atomic():
                modelo(pk=1).save(_desde_editor=True, force_insert=True)
        except IntegrityError:
            pass
    return modelo.objects.select_for_update().get(pk=1)
