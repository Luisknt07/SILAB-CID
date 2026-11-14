"""Resolucion vigente de personal operativo asociado a una unidad."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext

from apps.gestion_unidades.models.espacios import ResponsableUnidad


def resolver_responsable_operativo(reserva, responsable_id):
    """Bloquea y devuelve una asignacion activa de la unidad de la reserva."""
    try:
        responsable_pk = int(responsable_id)
    except (TypeError, ValueError):
        responsable_pk = None
    responsable = (
        ResponsableUnidad.objects.select_for_update(of=("self",))
        .filter(
            pk=responsable_pk,
            unidad_id=reserva.laboratorio_id,
            usuario__isnull=False,
            usuario__is_active=True,
            activo=True,
            recibe_reservas=True,
        )
        .first()
    )
    if responsable is None:
        raise ValidationError(
            gettext("El responsable seleccionado no atiende esta unidad."),
            code="responsable_invalido",
        )
    return responsable
