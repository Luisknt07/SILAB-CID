"""Reglas compartidas para validar el horario operativo de una unidad."""

from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
from apps.gestion_unidades.models.operaciones import HORA_ALMUERZO, ventana_atencion


def jornadas_habilitadas(
    unidad,
    *,
    periodo,
    fecha,
    tipo_solicitud,
    modalidad_servicio,
    tipo_usuario,
    proposito_codigo,
    es_administrador=False,
    horarios=None,
):
    """Devuelve las jornadas aplicables a fecha, perfil y proposito."""
    if horarios is None:
        horarios = list(HorarioOperacionUnidad.objects.filter(unidad=unidad, activo=True))
    horarios_periodo = [horario for horario in horarios if periodo and horario.periodo_id == periodo.pk]
    if horarios_periodo:
        horarios = horarios_periodo
        contexto = f"el período {periodo.codigo}"
    else:
        horarios = [horario for horario in horarios if horario.periodo_id is None]
        contexto = "el horario general de la unidad"

    jornadas = [
        jornada
        for jornada in horarios if jornada.dia_semana == fecha.weekday()
        if (
            jornada.admite(
                tipo_solicitud=tipo_solicitud,
                tipo_usuario=tipo_usuario,
                proposito_codigo=proposito_codigo,
            )
            or (
                es_administrador
                and (
                    jornada.permite_servicios
                    if tipo_solicitud == "servicio"
                    else jornada.permite_recursos
                )
            )
        )
        and not (
            tipo_solicitud == "servicio"
            and modalidad_servicio == "diseno_asistido"
            and not jornada.permite_recursos
        )
    ]
    return jornadas, contexto


def validar_horario_operativo(
    unidad,
    *,
    periodo,
    semana,
    fecha,
    hora_inicio,
    hora_fin,
    tipo_solicitud,
    modalidad_servicio,
    tipo_usuario,
    proposito_codigo,
    es_administrador=False,
    permitir_almuerzo=False,
    horarios=None,
):
    """Comprueba la jornada institucional aplicable a una reserva."""
    if semana and not semana.permite_reservas:
        raise ValueError(
            f"La semana {semana.numero} del período {periodo.codigo} no permite "
            "reservas según el calendario institucional."
        )

    if fecha.weekday() >= 5 and not es_administrador:
        raise ValueError(
            "Las reservas de sábado o domingo solo pueden ser registradas por la "
            "administración de la unidad, previa coordinación con el responsable."
        )

    jornadas, contexto = jornadas_habilitadas(
        unidad,
        periodo=periodo,
        fecha=fecha,
        tipo_solicitud=tipo_solicitud,
        modalidad_servicio=modalidad_servicio,
        tipo_usuario=tipo_usuario,
        proposito_codigo=proposito_codigo,
        es_administrador=es_administrador,
        horarios=horarios,
    )
    if not jornadas:
        modalidad = "servicios" if tipo_solicitud == "servicio" else "reservas de recursos"
        raise ValueError(
            f"La unidad no tiene {modalidad} habilitadas el "
            f'{fecha.strftime("%d/%m/%Y")} para tu perfil y propósito dentro de {contexto}.'
        )

    configuracion = getattr(unidad, "configuracion_operativa", None)
    apertura, cierre = ventana_atencion(configuracion, es_administrador)
    atencion = set(range(apertura, cierre))
    horas_habilitadas = {
        hora
        for jornada in jornadas
        for hora in range(jornada.hora_inicio.hour, jornada.hora_fin.hour)
    } & atencion
    horas_solicitadas = set(range(hora_inicio.hour, hora_fin.hour))
    fuera_de_atencion = horas_solicitadas - atencion
    if fuera_de_atencion and min(fuera_de_atencion) < apertura:
        raise ValueError(
            f"La atención de esta unidad empieza a las {apertura:02d}:00."
        )
    if fuera_de_atencion:
        raise ValueError(
            f"La atención de esta unidad termina a las {cierre:02d}:00. Fuera de ese "
            "horario solo registra la administración de la unidad, previa "
            "coordinación con el responsable."
        )
    if not horas_solicitadas.issubset(horas_habilitadas):
        rangos = ", ".join(
            f"{jornada.hora_inicio:%H:%M}–{jornada.hora_fin:%H:%M}"
            for jornada in jornadas
        )
        raise ValueError(
            f"El horario seleccionado está fuera de la jornada habilitada ({rangos}) "
            f"para {contexto}."
        )
    if (
        HORA_ALMUERZO in horas_solicitadas
        and tipo_solicitud != "servicio"
        and not permitir_almuerzo
    ):
        raise ValueError(
            f"El bloque de {HORA_ALMUERZO:02d}:00 a {HORA_ALMUERZO + 1:02d}:00 es la hora "
            "de almuerzo y no se reserva; elige otro horario."
        )


# Compatibilidad temporal para consumidores que todavia importan los nombres privados.
_jornadas_habilitadas = jornadas_habilitadas
_validar_horario_operativo = validar_horario_operativo
