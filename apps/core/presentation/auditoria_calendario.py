"""Auditoria local de compatibilidad: conteos sin escribir ni exponer usuarios."""

from django.apps import apps
from django.db.models import F, Q

from .calendario import calendario_actual


def auditar_calendario(*, database="default", politica_propuesta=None):
    politica = politica_propuesta if politica_propuesta is not None else calendario_actual()
    periodos = apps.get_model('core', "PeriodoAcademico").objects.using(database)
    semanas = apps.get_model('core', "SemanaAcademica").objects.using(database)
    compatibles = Q(pk__in=[])
    for ciclo, _, tipo in politica.ciclos + politica.ciclos_historicos:
        compatibles |= Q(ciclo=ciclo, tipo=tipo)
    return {
        "periodos": periodos.count(), "semanas": semanas.count(),
        "ciclos_desconocidos": periodos.exclude(ciclo__in=[c for c, _, _ in politica.ciclos + politica.ciclos_historicos]).count(),
        "ambitos_desconocidos": periodos.exclude(ambito__in=dict(politica.ambitos + politica.ambitos_historicos)).count(),
        "ciclos_tipos_incompatibles": periodos.exclude(compatibles).count(),
        "periodos_fuera_de_limites": periodos.exclude(
            semanas_planificadas__range=(politica.semanas_minimas, politica.semanas_maximas)).count(),
        "semanas_fuera_de_plan": semanas.filter(
            Q(numero__lt=1) | Q(numero__gt=F("version_calendario__periodo__semanas_planificadas"))).count(),
        "semanas_fuera_de_fechas": semanas.filter(
            Q(fecha_fin__lt=F("fecha_inicio"))
            | Q(fecha_inicio__lt=F("version_calendario__fecha_inicio_clases"))
            | Q(fecha_fin__gt=F("version_calendario__fecha_fin_periodo"))).count(),
    }
