"""Autorización funcional revocable, consultada sin caché de sesión."""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from apps.core.models.gobernanza import AsignacionGobernanza


def asignaciones_vigentes(usuario):
    vacias = AsignacionGobernanza.objects.none()
    if not getattr(usuario, "is_authenticated", False) or not getattr(
        usuario, "pk", None
    ):
        return vacias
    if not get_user_model().objects.filter(pk=usuario.pk, is_active=True).exists():
        return vacias
    hoy = timezone.localdate()
    return AsignacionGobernanza.objects.filter(
        usuario_id=usuario.pk, activa=True, desde__lte=hoy
    ).filter(Q(hasta__isnull=True) | Q(hasta__gte=hoy))


def tiene_funcion(usuario, rol, referencia=""):
    return (
        asignaciones_vigentes(usuario)
        .filter(rol=rol, referencia=str(referencia))
        .exists()
    )


def es_revisor_institucional(usuario):
    return tiene_funcion(usuario, "seguimiento")
