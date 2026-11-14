"""Identidad institucional y asistencia de participantes de una reserva."""

import json

from django.contrib.auth import get_user_model

from apps.reservas.models.reservas import RegistroParticipanteReserva
from apps.core.models.periodos import VinculacionUsuarioPeriodo


def datos_usuario_para_periodo(usuario, periodo):
    """Proyecta la vinculacion historica aplicable sin alterar el perfil actual."""
    perfil = getattr(usuario, "profile", None)
    vinculacion = None
    if periodo:
        vinculacion = VinculacionUsuarioPeriodo.objects.filter(
            usuario=usuario,
            periodo=periodo,
            estado="activa",
        ).first()
    fuente = vinculacion or perfil
    return {
        "tipo_usuario": getattr(fuente, "tipo_usuario", "") or "",
        "facultad": getattr(fuente, "facultad", "") or "",
        "carrera": getattr(fuente, "carrera", "") or "",
        "nivel_academico": getattr(fuente, "nivel_academico", "") or "",
        "institucion": getattr(fuente, "institucion", "") or "",
    }


def registrar_participantes(reserva, solicitante, participantes):
    """Conserva la clasificacion institucional usada por los indicadores."""
    filas = []
    for usuario, rol in [(solicitante, "solicitante")] + [
        (participante, "participante") for participante in participantes
    ]:
        datos_periodo = datos_usuario_para_periodo(usuario, reserva.periodo)
        filas.append(
            RegistroParticipanteReserva(
                reserva=reserva,
                usuario=usuario,
                rol=rol,
                nombre=usuario.get_full_name() or usuario.username,
                correo=usuario.email or "",
                tipo_usuario=datos_periodo["tipo_usuario"],
                facultad=datos_periodo["facultad"],
                carrera=datos_periodo["carrera"],
                nivel_academico=datos_periodo["nivel_academico"],
                institucion=datos_periodo["institucion"],
            )
        )
    RegistroParticipanteReserva.objects.bulk_create(filas)


def validar_participantes(valor_json, solicitante):
    """Resuelve una lista JSON de cuentas activas con perfil completo."""
    try:
        ids = json.loads(valor_json or "[]")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("El formato de participantes no es válido") from error
    if not isinstance(ids, list):
        raise ValueError("El formato de participantes no es válido")
    try:
        ids = [int(value) for value in ids]
    except (TypeError, ValueError) as error:
        raise ValueError("Uno de los participantes no es válido") from error
    ids = [value for value in ids if value != solicitante.pk]
    if len(ids) != len(set(ids)):
        raise ValueError("No se puede seleccionar dos veces al mismo participante")
    participantes = list(
        get_user_model()
        .objects.filter(pk__in=ids, is_active=True)
        .select_related("profile")
    )
    if len(participantes) != len(ids):
        raise ValueError(
            "Uno de los participantes no está registrado o ya no está activo"
        )
    incompletos = []
    for participante in participantes:
        perfil = getattr(participante, "profile", None)
        if not perfil or perfil.campos_faltantes_reserva():
            incompletos.append(participante.get_full_name() or participante.username)
    if incompletos:
        raise ValueError(
            "Estos participantes deben completar su perfil antes de ser agregados: "
            + ", ".join(incompletos)
        )
    return participantes


def actualizar_participantes_reserva(reserva, datos):
    """Sincroniza identidades y asistencia desde una entrada tipo QueryDict."""
    if "participantes_seleccionados" not in datos:
        return False
    if not reserva.usuario_id:
        raise ValueError(
            "Una solicitud sin cuenta institucional no permite editar participantes."
        )
    try:
        filas = json.loads(datos.get("participantes_seleccionados") or "[]")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "La lista de participantes no tiene un formato válido."
        ) from error
    if not isinstance(filas, list):
        raise ValueError("La lista de participantes no tiene un formato válido.")

    ids = []
    asistencias = {}
    opciones_asistencia = dict(RegistroParticipanteReserva.ASISTENCIA_CHOICES)
    for fila in filas:
        if isinstance(fila, dict):
            participante_id = fila.get("id")
            asistencia = fila.get("asistencia") or "prevista"
        else:
            participante_id = fila
            asistencia = "prevista"
        try:
            participante_id = int(participante_id)
        except (TypeError, ValueError) as error:
            raise ValueError("Uno de los participantes no es válido.") from error
        if asistencia not in opciones_asistencia:
            raise ValueError("Uno de los estados de asistencia no es válido.")
        ids.append(participante_id)
        asistencias[participante_id] = asistencia

    participantes = validar_participantes(json.dumps(ids), reserva.usuario)
    asistencia_solicitante = (
        datos.get("asistencia_solicitante") or "prevista"
    ).strip()
    if asistencia_solicitante not in opciones_asistencia:
        raise ValueError("El estado de asistencia del solicitante no es válido.")

    reserva.participantes.set(participantes)
    reserva.registros_participantes.all().delete()
    registrar_participantes(reserva, reserva.usuario, participantes)
    RegistroParticipanteReserva.objects.filter(
        reserva=reserva,
        usuario=reserva.usuario,
    ).update(asistencia=asistencia_solicitante)
    for participante_id, asistencia in asistencias.items():
        RegistroParticipanteReserva.objects.filter(
            reserva=reserva,
            usuario_id=participante_id,
        ).update(asistencia=asistencia)
    reserva.numero_participantes = 1 + len(participantes)
    return True
