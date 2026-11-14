"""Validacion persistente de conflictos de agenda y recursos."""

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.reservas.models.reservas import Reserva

from apps.reservas.presentation.availability import ACTIVE_RESERVATION_STATUSES, evaluate_administrative_block_conflicts, evaluate_selection_conflicts


def validar_conflictos_recursos(
    unidad,
    fecha,
    hora_inicio,
    hora_fin,
    recursos,
    software,
    espacios,
    *,
    incluye_espacio,
    alcance_espacio,
    tipo_solicitud,
    modalidad_servicio,
    proposito_codigo,
    numero_participantes,
    bloquear_existentes=False,
    excluir_reserva_id=None,
):
    """Valida bloqueos, solapamientos y capacidad con una regla compartida."""
    usa_recursos = (
        tipo_solicitud != "servicio" or modalidad_servicio == "diseno_asistido"
    )
    unidades_ids = {
        int(recurso["id"])
        for recurso in recursos
        if isinstance(recurso, dict) and recurso.get("id") is not None
    }
    bloqueos = list(
        BloqueoAgendaUnidad.objects.filter(
            unidad=unidad,
            activo=True,
            fecha_inicio__lte=fecha,
            fecha_fin__gte=fecha,
        ).prefetch_related("espacios", "equipos")
    )
    conflictos_administrativos = evaluate_administrative_block_conflicts(
        bloqueos,
        selected_unit_ids=unidades_ids,
        selected_space_ids={espacio.pk for espacio in espacios},
        includes_space=incluye_espacio,
        space_scope=alcance_espacio,
        request_kind="servicio" if tipo_solicitud == "servicio" else "recursos",
    )
    hora_final = hora_fin.hour + (1 if hora_fin.minute else 0)
    motivos_administrativos = []
    for hora in range(hora_inicio.hour, hora_final):
        motivos_administrativos.extend(
            conflictos_administrativos.get((fecha.isoformat(), hora), ())
        )
    if motivos_administrativos:
        raise ValueError(" ".join(dict.fromkeys(motivos_administrativos)))
    if not usa_recursos:
        return

    queryset = Reserva.objects.filter(
        laboratorio=unidad,
        fecha=fecha,
        estado__in=ACTIVE_RESERVATION_STATUSES,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    )
    if excluir_reserva_id is not None:
        queryset = queryset.exclude(pk=excluir_reserva_id)
    if bloquear_existentes:
        queryset = queryset.order_by("pk").select_for_update(of=("self",))
    solapadas = list(
        queryset.prefetch_related("software_solicitado", "espacios_solicitados")
    )
    conflictos = evaluate_selection_conflicts(
        solapadas,
        selected_unit_ids=unidades_ids,
        selected_spaces=espacios,
        includes_space=incluye_espacio,
        space_scope=alcance_espacio,
        selected_software=software,
        purpose=proposito_codigo,
        participant_count=numero_participantes,
        unit_capacity=unidad.capacidad_personas,
    )
    motivos_relevantes = []
    for hora in range(hora_inicio.hour, hora_final):
        motivos_relevantes.extend(conflictos.get((fecha.isoformat(), hora), ()))
    if motivos_relevantes:
        raise ValueError(" ".join(dict.fromkeys(motivos_relevantes)))
