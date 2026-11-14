"""Compatibilidad del editor institucional con las guardas neutrales del nucleo."""
from apps.core.persistence.publicacion import (
    HistorialInstitucionalQuerySet as HistorialInstitucionalQuerySet,
    actor_con_permiso as actor_con_permiso,
    bloquear_publicacion as bloquear_publicacion,
)
