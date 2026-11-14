"""Resolución del calendario académico aplicable a una reserva."""

from apps.core.presentation.calendario_institucional import con_calendario_institucional

from apps.core.models.periodos import PeriodoAcademico


@con_calendario_institucional()
def resolver_periodo_reserva(fecha, contexto_actividad, proposito_codigo):
    """Determina PAO, versión y semana desde la fecha y el contexto declarado."""
    actividad = contexto_actividad.get("actividad_catalogo")
    periodo = getattr(actividad, "periodo", None) if actividad else None
    codigo_solicitado = (
        contexto_actividad.get("periodo_academico") or ""
    ).strip().upper()
    if periodo is None and codigo_solicitado:
        periodo = PeriodoAcademico.objects.filter(codigo=codigo_solicitado).first()
    if periodo is None:
        periodo = (
            PeriodoAcademico.objects.para_fecha(fecha)
            .operativos()
            .prefetch_related("versiones__semanas")
            .first()
        )

    version = periodo.version_vigente if periodo else None
    if periodo and version and not (
        version.fecha_inicio_clases <= fecha <= version.fecha_fin_periodo
    ):
        raise ValueError(
            f"La fecha seleccionada no corresponde al período {periodo.codigo}. "
            "Selecciona una fecha de su calendario vigente."
        )
    semana = periodo.semana_para_fecha(fecha) if periodo else None
    codigo = periodo.codigo if periodo else codigo_solicitado
    calendario_institucional_activo = (
        PeriodoAcademico.objects.publicados().operativos().exists()
    )
    if (
        proposito_codigo == "docencia_practica"
        and not codigo
        and calendario_institucional_activo
    ):
        raise ValueError(
            "No existe un período académico configurado para la fecha seleccionada. "
            "Solicita al administrador publicar el calendario institucional."
        )
    return {
        "periodo": periodo,
        "periodo_academico": codigo,
        "version_calendario": version,
        "semana_academica": semana,
        "semana_academica_numero": semana.numero if semana else None,
    }
