"""Reconciliaciones históricas de reservas acotadas a una unidad."""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Exists, OuterRef

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.formacion.presentation.practicas_integracion import sincronizar_planificacion_reserva
from apps.reservas.presentation.cambios import asegurar_revision_inicial
from apps.reservas.models.reservas import Reserva, RevisionReserva
from apps.directorio_unidades.models.core import Unidad

from apps.reservas.presentation.capacidad import operacion_reservas


@dataclass(frozen=True)
class ResultadoRevisiones:
    creadas: int = 0


@dataclass(frozen=True)
class ResultadoPlanificaciones:
    creadas: int = 0
    actualizadas: int = 0
    omitidas: int = 0


@operacion_reservas
@transaction.atomic
def inicializar_revisiones_unidad(*, unidad_slug, simular=False):
    """Crea las líneas base faltantes dentro de una sola unidad bloqueada."""
    unidad = Unidad.objects.select_for_update(of=("self",)).get(slug=unidad_slug)
    reservas = (
        Reserva.objects.select_for_update(of=("self",))
        .select_related("laboratorio")
        .filter(laboratorio_id=unidad.pk)
        .annotate(
            tiene_linea_base=Exists(
                RevisionReserva.objects.filter(
                    reserva_id=OuterRef("pk"),
                    numero=1,
                )
            )
        )
        .filter(tiene_linea_base=False)
        .order_by("pk")
    )

    creadas = 0
    for reserva in reservas.iterator(chunk_size=200):
        # La comprobación dentro del bloqueo cubre datos legados y reintentos.
        if reserva.revisiones.filter(numero=1).exists():
            continue
        asegurar_revision_inicial(
            reserva,
            actor=None,
            motivo=(
                "Línea base vigente al habilitar el control de versiones; "
                "los cambios históricos previos continúan en la auditoría."
            ),
        )
        creadas += 1

    if simular:
        transaction.set_rollback(True)
    return ResultadoRevisiones(creadas=creadas)


@operacion_reservas
@transaction.atomic
def sincronizar_planificaciones_unidad(*, unidad_slug, simular=False):
    """Reconcilia FT02 de una unidad y conserva una única transacción local."""
    unidad = Unidad.objects.select_for_update(of=("self",)).get(slug=unidad_slug)
    reservas = (
        Reserva.objects.select_for_update(of=("self",))
        .select_related(
            "laboratorio",
            "actividad_catalogo",
            "usuario",
            "responsable_asignado",
        )
        .filter(laboratorio_id=unidad.pk)
        .exclude(tipo_solicitud="servicio")
        .order_by("pk")
    )

    creadas = 0
    actualizadas = 0
    omitidas = 0
    for reserva in reservas.iterator(chunk_size=200):
        plan, creada, cambiada = sincronizar_planificacion_reserva(
            reserva,
            actor=reserva.usuario,
        )
        if not plan:
            omitidas += 1
            continue
        if creada:
            creadas += 1
        elif cambiada:
            actualizadas += 1
        else:
            omitidas += 1
            continue
        registrar_auditoria(
            unidad=unidad,
            usuario=reserva.usuario,
            accion="crear" if creada else "actualizar",
            objeto=plan,
            descripcion=(
                f"Planificación {plan.codigo} sincronizada desde la reserva "
                f"histórica {reserva.codigo_reserva or reserva.pk}."
            ),
            nuevos={
                "reserva_id": reserva.pk,
                "requiere_guia": plan.requiere_guia,
                "estado": plan.estado,
            },
        )

    if simular:
        transaction.set_rollback(True)
    return ResultadoPlanificaciones(
        creadas=creadas,
        actualizadas=actualizadas,
        omitidas=omitidas,
    )
