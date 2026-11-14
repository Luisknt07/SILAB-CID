"""Aprobacion integral de una reserva vigente."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext

from apps.reservas.models.reservas import Reserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.reservas.workflows.reservas import validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.plantas_piloto.operacion.presentation.gestion_produccion import orden_de_practica
from apps.formacion.presentation.practicas_integracion import sincronizar_planificacion_reserva, validar_compuerta_documental
from apps.reservas.presentation.seguridad import validar_aforo
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.elegibilidad import validar_elegibilidad_reserva
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.reservas.presentation.responsables import resolver_responsable_operativo
from apps.reservas.presentation.trazabilidad import agregar_observacion, instantanea_reserva_para_auditoria, registrar_accion_reserva


ETIQUETA_APROBACION = "Reserva aprobada"


def _normalizar_observacion(observacion):
    if not isinstance(observacion, str):
        raise ValidationError(
            gettext("La observación debe ser texto."), code="observacion_invalida"
        )
    observacion = observacion.strip()
    if len(observacion) > 1200:
        raise ValidationError(
            gettext("La observación no puede superar 1200 caracteres."),
            code="observacion_invalida",
        )
    return observacion


def _responsable_automatico(reserva):
    """Bloquea candidatos y equilibra su carga activa dentro de la unidad."""
    candidatos_base = ResponsableUnidad.objects.filter(
        unidad_id=reserva.laboratorio_id,
        usuario__isnull=False,
        usuario__is_active=True,
        activo=True,
        recibe_reservas=True,
    )
    candidatos_ids = list(
        candidatos_base.select_for_update(of=("self",))
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    if not candidatos_ids:
        return None
    candidatos = list(
        ResponsableUnidad.objects.filter(pk__in=candidatos_ids).annotate(
            carga_activa=Count(
                "reservas_asignadas",
                filter=Q(
                    reservas_asignadas__laboratorio_id=reserva.laboratorio_id,
                    reservas_asignadas__estado__in={
                        "pendiente",
                        "confirmada",
                        "en_proceso",
                    },
                    reservas_asignadas__fecha__gte=timezone.localdate(),
                ),
                distinct=True,
            )
        )
    )
    actual_id = reserva.responsable_asignado_id
    if actual_id in candidatos_ids:
        return next(item for item in candidatos if item.pk == actual_id)
    prioridad_rol = {
        "responsable_tecnico": 0,
        "laboratorista": 1,
        "tecnico": 2,
        "soporte": 3,
        "coordinacion": 4,
        "otro": 5,
    }
    return min(
        candidatos,
        key=lambda candidato: (
            candidato.carga_activa,
            prioridad_rol.get(candidato.rol, 9),
            candidato.orden,
            candidato.pk,
        ),
    )


@operacion_reservas
@transaction.atomic
def aprobar_reserva(
    reserva,
    *,
    actor,
    responsable_id=None,
    observacion="",
    request=None,
    unidad_esperada=None,
):
    """Aprueba y genera sus efectos como una sola operacion autorizada."""
    if reserva._state.db not in {None, "default"}:
        raise ValidationError(
            gettext(
                "Las aprobaciones de reserva requieren la base de datos principal."
            ),
            code="no_disponible",
        )
    observacion = _normalizar_observacion(observacion)
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada

    # Serializa aprobaciones de una misma unidad antes de bloquear expedientes.
    # Asi la carga para asignacion y la agenda se leen despues del commit previo.
    Unidad.objects.select_for_update(of=("self",)).filter(pk=alcance).first()
    reserva = (
        Reserva.objects.select_for_update(of=("self",))
        .select_related("laboratorio", "responsable_asignado")
        .filter(pk=reserva.pk)
        .first()
    )
    if reserva is None:
        raise ValidationError(
            gettext("La reserva ya no está disponible."), code="no_disponible"
        )
    actor = exigir_autoridad_reserva(
        reserva,
        actor,
        operacion="aprobar_reserva",
        unidad_esperada=alcance,
    )
    validar_compuerta_documental(reserva, "aprobar")
    responsable = (
        resolver_responsable_operativo(reserva, responsable_id)
        if responsable_id not in {None, ""}
        else _responsable_automatico(reserva)
    )
    validar_accion_reserva(reserva.estado, "aprobar", motivo=observacion)
    if responsable is None:
        raise ValidationError(
            gettext(
                "No hay responsables activos disponibles para esta unidad. "
                "Configura uno que reciba reservas antes de continuar."
            ),
            code="responsable_no_disponible",
        )

    validar_aforo(reserva)
    validar_elegibilidad_reserva(reserva)

    estado_anterior = reserva.estado
    datos_anteriores = instantanea_reserva_para_auditoria(reserva)
    reserva.responsable_asignado = responsable
    reserva.estado = "confirmada"
    reserva.validada_por = actor
    reserva.fecha_validacion = timezone.now()
    agregar_observacion(reserva, ETIQUETA_APROBACION, observacion)
    reserva.save(
        update_fields=[
            "responsable_asignado",
            "estado",
            "validada_por",
            "fecha_validacion",
            "observaciones_validacion",
            "fecha_actualizacion",
        ]
    )

    if reserva.receta_id:
        orden_de_practica(reserva, actor)
    plan, creado, cambiado = sincronizar_planificacion_reserva(reserva, actor=actor)
    if plan and cambiado:
        registrar_auditoria(
            request,
            unidad=reserva.laboratorio,
            accion="crear" if creado else "actualizar",
            objeto=plan,
            descripcion=(
                f"Planificación {plan.codigo} generada desde la reserva "
                f"{reserva.codigo_reserva}."
                if creado
                else f"Planificación {plan.codigo} sincronizada con la reserva."
            ),
            nuevos={
                "reserva_id": reserva.pk,
                "fecha": reserva.fecha.isoformat(),
                "hora_inicio": reserva.hora_inicio.isoformat(),
                "hora_fin": reserva.hora_fin.isoformat(),
                "participantes": reserva.numero_participantes,
            },
            usuario=actor,
        )
    reserva.notificaciones.filter(
        leida=False, clave__contains=":sin_responsable"
    ).update(leida=True)
    notificar_cambio_reserva(reserva, "aprobar", observacion)
    registrar_accion_reserva(
        actor, reserva, ETIQUETA_APROBACION, estado_anterior, observacion
    )
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="aprobar",
        objeto=reserva,
        descripcion=(
            f"{ETIQUETA_APROBACION}: {observacion}"
            if observacion
            else ETIQUETA_APROBACION
        ),
        anteriores=datos_anteriores,
        nuevos=instantanea_reserva_para_auditoria(reserva),
        usuario=actor,
    )
    return reserva
