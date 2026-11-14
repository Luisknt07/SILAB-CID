"""Vigencia del perfil institucional.

Una cuenta creada con el correo institucional solo trae el nombre y el correo;
el resto —tipo de usuario, facultad, carrera, semestre— identifica a quien usa
los laboratorios y sostiene los reportes. Aquí se decide cuándo esos datos
están completos y al día para el período académico en curso.

La clasificación de cada período se guarda en ``VinculacionUsuarioPeriodo``,
que es la que leen las reservas y los reportes. Cuando los datos no cambian de
un período a otro, esa vinculación se registra sola desde el perfil; solo se
detiene a la persona cuando hay algo que decidir: al estudiante se le propone
el semestre siguiente y debe confirmarlo o corregirlo, porque el irregular no
avanza como el resto.
"""

from django.utils import timezone
from apps.core.presentation.niveles import niveles_actuales
from apps.core.presentation.niveles_institucionales import con_niveles_institucionales
from apps.core.presentation.catalogo_institucional import con_catalogo_institucional
from apps.core.presentation.calendario_institucional import con_calendario_institucional

from apps.core.models.periodos import PeriodoAcademico, VinculacionUsuarioPeriodo
from apps.core.models.usuarios_base import UserProfile


TIPOS_CON_PERIODO = frozenset(
    {"estudiante", "docente", "investigador", "administrativo", "egresado"}
)


@con_calendario_institucional()
def periodo_vigente(fecha=None):
    """Período académico publicado que contiene la fecha, si lo hay."""
    fecha = fecha or timezone.localdate()
    return (
        PeriodoAcademico.objects.para_fecha(fecha)
        .operativos()
        .first()
    )


@con_niveles_institucionales()
def siguiente_nivel(nivel):
    """Propone el siguiente nivel de su ruta; nunca inventa un cambio de programa."""
    return niveles_actuales().siguiente(nivel)


def vinculacion_del_periodo(usuario, periodo):
    if not periodo:
        return None
    return VinculacionUsuarioPeriodo.objects.filter(
        usuario=usuario, periodo=periodo, estado="activa"
    ).first()


def _ultima_vinculacion(usuario, periodo, tipo_usuario):
    if not periodo:
        return None
    version = periodo.version_vigente
    if not version:
        return None
    consulta = VinculacionUsuarioPeriodo.objects.filter(
        usuario=usuario, estado="activa", tipo_usuario=tipo_usuario,
        periodo__ambito=periodo.ambito, periodo__estado__in=("publicado", "cerrado"),
        periodo__versiones__vigente=True,
        periodo__versiones__fecha_fin_periodo__lt=version.fecha_inicio_clases,
    )
    return (
        consulta.select_related("periodo")
        .order_by("-periodo__versiones__fecha_fin_periodo", "-pk")
        .first()
    )


@con_niveles_institucionales()
def propuesta_para(usuario, perfil, periodo):
    """Datos sugeridos para el período en curso.

    A quien ya cursó un período ordinario se le propone el semestre siguiente;
    sin período anterior se propone lo que ya dice su perfil.
    """
    datos = {
        "tipo_usuario": perfil.tipo_usuario or "",
        "facultad": perfil.facultad or "",
        "carrera": perfil.carrera or "",
        "nivel_academico": perfil.nivel_academico or "",
        "institucion": perfil.institucion or "",
        "avanzado": False,
        "periodo_anterior": None,
    }
    anterior = _ultima_vinculacion(usuario, periodo, perfil.tipo_usuario)
    if (
        anterior
        and periodo
        and perfil.tipo_usuario == "estudiante"
        and periodo.tipo == "ordinario"
        and anterior.periodo.tipo == "ordinario"
        and anterior.carrera == perfil.carrera
    ):
        propuesto = siguiente_nivel(anterior.nivel_academico)
        datos["nivel_academico"] = propuesto
        datos["avanzado"] = propuesto != anterior.nivel_academico
        datos["periodo_anterior"] = anterior.periodo
    return datos


@con_catalogo_institucional()
@con_niveles_institucionales()
def estado_perfil(usuario):
    """Resume si la persona puede usar la plataforma y qué le falta."""
    perfil = getattr(usuario, "profile", None)
    if perfil is None:
        perfil, _ = UserProfile.objects.get_or_create(user=usuario)
    faltantes = perfil.campos_faltantes_reserva()
    periodo = periodo_vigente()
    vinculacion = vinculacion_del_periodo(usuario, periodo)
    propuesta = propuesta_para(usuario, perfil, periodo) if periodo else {}
    # Solo se detiene a quien tiene algo que decidir: el estudiante que cambia
    # de semestre al empezar el período. Al resto se le registra la vinculación
    # con lo que ya declaró.
    requiere_confirmacion = bool(
        periodo
        and not vinculacion
        and not faltantes
        and propuesta.get("avanzado")
    )
    if (
        periodo
        and not vinculacion
        and not faltantes
        and not requiere_confirmacion
        and perfil.tipo_usuario in TIPOS_CON_PERIODO
    ):
        vinculacion = confirmar_periodo(usuario, perfil, periodo)
    return {
        "perfil": perfil,
        "completo": not faltantes,
        "faltantes": faltantes,
        "periodo": periodo,
        "vinculacion": vinculacion,
        "confirmado": bool(vinculacion),
        "requiere_confirmacion": requiere_confirmacion,
        "propuesta": propuesta,
        "vigente": not faltantes and not requiere_confirmacion,
    }


def perfil_vigente(usuario):
    """Atajo para la compuerta: ¿puede usar las funciones de la plataforma?"""
    if not usuario or not usuario.is_authenticated:
        return False
    return estado_perfil(usuario)["vigente"]


@con_catalogo_institucional()
@con_niveles_institucionales()
def confirmar_periodo(usuario, perfil=None, periodo=None):
    """Deja registrados los datos de la persona en el período en curso.

    La vinculación conserva la clasificación de cada período sin reescribir la
    historia del anterior: un reporte de 2026-A sigue diciendo lo que era
    verdad entonces.
    """
    perfil = perfil or getattr(usuario, "profile", None)
    periodo = periodo or periodo_vigente()
    if not perfil or not periodo or perfil.tipo_usuario not in TIPOS_CON_PERIODO:
        return None
    if perfil.campos_faltantes_reserva():
        return None
    vinculacion, _creada = VinculacionUsuarioPeriodo.objects.update_or_create(
        usuario=usuario,
        periodo=periodo,
        defaults={
            "tipo_usuario": perfil.tipo_usuario,
            "facultad": perfil.facultad or "",
            "carrera": perfil.carrera or "",
            "nivel_academico": perfil.nivel_academico or "",
            "institucion": perfil.institucion or "",
            "estado": "activa",
            "fuente": "perfil",
        },
    )
    return vinculacion
