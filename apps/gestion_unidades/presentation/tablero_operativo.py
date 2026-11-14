"""Resumen operativo calculado para responsables de una unidad."""

from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.mantenimiento import IncidenciaEquipo, PlanMantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo


PRIORIDAD_ALERTA = {"critico": 0, "advertencia": 1, "informativo": 2}


def _capacidad_activa(configuracion, nombre):
    return bool(configuracion and getattr(configuracion, nombre, False))


def construir_tablero_operativo(unidad, configuracion):
    """Construye indicadores sin persistir ni duplicar información operativa."""
    hoy = timezone.localdate()
    limite = hoy + timedelta(days=30)
    equipos = UnidadEquipo.objects.filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad),
        activa=True,
    ).distinct()
    total_equipos = equipos.count()
    disponibles = equipos.filter(estado_unidad="disponible").count()
    fuera_servicio = equipos.filter(
        estado_unidad__in=("mantenimiento", "dañado", "no_disponible")
    ).count()

    mantenimiento_activo = _capacidad_activa(configuracion, "mantenimiento_equipos")
    incidencias_activas = _capacidad_activa(configuracion, "incidencias_equipos")
    consumibles_activos = _capacidad_activa(configuracion, "consumibles")

    planes = PlanMantenimientoEquipo.objects.filter(
        equipo__in=equipos,
        activo=True,
    )
    planes_vencidos = planes.filter(proxima_ejecucion__lt=hoy).count()
    planes_proximos = planes.filter(
        proxima_ejecucion__gte=hoy,
        proxima_ejecucion__lte=limite,
    ).count()
    equipos_planificados = planes.values("equipo_id").distinct().count()
    cobertura_mantenimiento = (
        round((equipos_planificados / total_equipos) * 100) if total_equipos else 0
    )

    incidencias = IncidenciaEquipo.objects.filter(
        Q(unidad=unidad) | Q(equipo__in=equipos)
    ).exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).distinct()
    incidencias_abiertas = incidencias.count()
    incidencias_criticas = incidencias.filter(
        prioridad__in=("alta", "critica")
    ).count()

    consumibles = Consumible.objects.filter(unidad=unidad, activo=True)
    consumibles_bajos = consumibles.filter(
        Q(stock_total__lte=0)
        | Q(minimo__gt=0, stock_total__lte=F("minimo"))
    ).count()
    consumibles_agotados = consumibles.filter(stock_total__lte=0).count()

    alertas = []
    if mantenimiento_activo and planes_vencidos:
        alertas.append({
            "tipo": "mantenimiento_vencido",
            "nivel": "critico",
            "icono": "fas fa-tools",
            "titulo": "Mantenimiento vencido",
            "detalle": "Equipos que superaron su fecha programada.",
            "cantidad": planes_vencidos,
        })
    if incidencias_activas and incidencias_criticas:
        alertas.append({
            "tipo": "incidencia_critica",
            "nivel": "critico",
            "icono": "fas fa-exclamation-triangle",
            "titulo": "Incidencias prioritarias",
            "detalle": "Reportes de prioridad alta o crítica que requieren atención.",
            "cantidad": incidencias_criticas,
        })
    if consumibles_activos and consumibles_agotados:
        alertas.append({
            "tipo": "consumible_agotado",
            "nivel": "critico",
            "icono": "fas fa-box-open",
            "titulo": "Consumibles agotados",
            "detalle": "Existencias que deben reponerse antes de nuevas actividades.",
            "cantidad": consumibles_agotados,
        })
    if mantenimiento_activo and planes_proximos:
        alertas.append({
            "tipo": "mantenimiento_proximo",
            "nivel": "advertencia",
            "icono": "fas fa-calendar-check",
            "titulo": "Mantenimiento próximo",
            "detalle": "Actividades programadas para los siguientes 30 días.",
            "cantidad": planes_proximos,
        })
    incidencias_no_criticas = max(incidencias_abiertas - incidencias_criticas, 0)
    if incidencias_activas and incidencias_no_criticas:
        alertas.append({
            "tipo": "incidencia_abierta",
            "nivel": "advertencia",
            "icono": "fas fa-clipboard-list",
            "titulo": "Incidencias abiertas",
            "detalle": "Reportes operativos pendientes de evaluación o cierre.",
            "cantidad": incidencias_no_criticas,
        })
    consumibles_solo_bajos = max(consumibles_bajos - consumibles_agotados, 0)
    if consumibles_activos and consumibles_solo_bajos:
        alertas.append({
            "tipo": "consumible_bajo",
            "nivel": "advertencia",
            "icono": "fas fa-boxes",
            "titulo": "Stock bajo",
            "detalle": "Consumibles que alcanzaron su umbral de reposición.",
            "cantidad": consumibles_solo_bajos,
        })
    alertas.sort(key=lambda alerta: PRIORIDAD_ALERTA[alerta["nivel"]])

    if any(alerta["nivel"] == "critico" for alerta in alertas):
        estado = {"tono": "critico", "etiqueta": "Requiere atención"}
    elif alertas or fuera_servicio:
        estado = {"tono": "advertencia", "etiqueta": "Con pendientes"}
    else:
        estado = {"tono": "estable", "etiqueta": "Operación estable"}

    metricas = [
        {
            "valor": total_equipos,
            "etiqueta": "Equipos activos",
            "detalle": f"{disponibles} disponibles",
            "icono": "fas fa-microscope",
            "tono": "estable",
        },
        {
            "valor": fuera_servicio,
            "etiqueta": "Fuera de servicio",
            "detalle": "Mantenimiento, daño o indisponibilidad",
            "icono": "fas fa-power-off",
            "tono": "critico" if fuera_servicio else "estable",
        },
        {
            "valor": incidencias_abiertas if incidencias_activas else "—",
            "etiqueta": "Incidencias abiertas",
            "detalle": f"{incidencias_criticas} prioritarias" if incidencias_activas else "Módulo desactivado",
            "icono": "fas fa-exclamation-circle",
            "tono": "critico" if incidencias_criticas else "estable",
        },
        {
            "valor": planes_vencidos if mantenimiento_activo else "—",
            "etiqueta": "Mantenimientos vencidos",
            "detalle": f"{planes_proximos} próximos" if mantenimiento_activo else "Módulo desactivado",
            "icono": "fas fa-tools",
            "tono": "critico" if planes_vencidos else "estable",
        },
        {
            "valor": consumibles_bajos if consumibles_activos else "—",
            "etiqueta": "Consumibles críticos",
            "detalle": f"{consumibles_agotados} agotados" if consumibles_activos else "Módulo desactivado",
            "icono": "fas fa-boxes",
            "tono": "critico" if consumibles_agotados else "estable",
        },
    ]

    return {
        "estado": estado,
        "metricas": metricas,
        "alertas": alertas,
        "cobertura_mantenimiento": cobertura_mantenimiento,
        "equipos_planificados": equipos_planificados,
        "total_equipos": total_equipos,
        "planes_proximos": planes_proximos,
        "incidencias_abiertas": incidencias_abiertas,
        "consumibles_bajos": consumibles_bajos,
    }
