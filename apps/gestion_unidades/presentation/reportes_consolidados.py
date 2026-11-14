"""Consolidado de evidencias por tipo de unidad para el administrador.

Suma, unidad por unidad, lo que cada Centro de reportes ya calcula. No hay
una segunda definición de nada: disponibilidad, guías o desechos salen de
las mismas funciones que usa la consola de la unidad.
"""

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.recursos.models.desechos import RegistroDesecho
from apps.reservas.models.seguridad import RegistroIngreso
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.directorio_unidades.models.core import Unidad

from apps.gestion_unidades.presentation.reportes_evidencias import disponibilidad_de_unidades, guias_del_periodo
from apps.gestion_unidades.presentation.reportes_filtros import PeriodoReporte

CAMPOS_SUMABLES = (
    'planificaciones', 'planificaciones_con_tema', 'ejecuciones', 'ejecuciones_con_evidencia',
    'guias_publicadas', 'ingresos', 'ingresos_protegidos', 'servicios_completados',
    'desechos_entregados', 'desechos_almacenados', 'prestamos', 'prestamos_vencidos',
)


def _informes(unidad, desde, hasta):
    """La dirección del informe de la unidad, categoría por categoría.

    Desde el consolidado se abre el detalle exacto, no la pestaña de reportes
    para volver a buscarlo.
    """
    base = reverse('admin:reportes-documento-evidencia', args=[unidad.slug]) + '?' + PeriodoReporte(desde, hasta).query() + '&categoria_reporte='
    return {clave: base + clave for clave in (
        'planificaciones', 'ejecuciones', 'guias', 'seguridad', 'transferencia', 'desechos',
        'prestamos', 'equipamiento', 'mantenimiento', 'recursos', 'inventario', 'investigacion',
    )}


def _conteos(consulta, campo, **metricas):
    return {fila.pop(campo): fila for fila in consulta.order_by().values(campo).annotate(**metricas)}


def evidencias_por_unidad(codigos_tipo, desde, hasta, usuario):
    """Filas por unidad activa del tipo y la fila de totales.

    Quien no es superusuario ve solo las unidades que administra: la misma
    regla que el reporte operativo del administrador.
    """
    unidades = Unidad.objects.filter(dependencia__in=codigos_tipo, activo=True).order_by('nombre')
    if not usuario.is_superuser:
        from apps.gestion_unidades.presentation.permisos import unidades_del_expediente
        unidades = unidades.filter(pk__in=unidades_del_expediente(usuario))
    unidades = list(unidades)
    ids = [unidad.pk for unidad in unidades]
    tablas = []
    if ids:
        tablas = [
            _conteos(PlanificacionPractica.objects.filter(
                unidad_id__in=ids, fecha__range=(desde, hasta), eliminado_en__isnull=True), 'unidad_id',
                planificaciones=Count('pk'),
                planificaciones_con_tema=Count('pk', filter=Q(tema_asignatura__isnull=False))),
            _conteos(EjecucionPractica.objects.filter(
                planificacion__unidad_id__in=ids, fecha_ejecucion__range=(desde, hasta),
                eliminado_en__isnull=True), 'planificacion__unidad_id',
                ejecuciones=Count('pk', distinct=True),
                ejecuciones_con_evidencia=Count('pk', filter=Q(evidencias__isnull=False), distinct=True)),
            _conteos(guias_del_periodo(unidades, desde, hasta).filter(estado_publicacion='publicada'),
                     'actividad__unidad_id', guias_publicadas=Count('pk')),
            _conteos(RegistroIngreso.objects.filter(
                reserva__laboratorio_id__in=ids, reserva__fecha__range=(desde, hasta)), 'reserva__laboratorio_id',
                ingresos=Count('pk', filter=Q(ingresa=True)),
                ingresos_protegidos=Count('pk', filter=Q(ingresa=True, proteccion_verificada=True))),
            _conteos(SolicitudFabricacion.objects.filter(
                unidad_id__in=ids, estado='completada', fecha_solicitud__range=(desde, hasta)),
                'unidad_id', servicios_completados=Count('pk')),
            _conteos(RegistroDesecho.objects.filter(
                unidad_id__in=ids, fecha_generacion__range=(desde, hasta)), 'unidad_id',
                desechos_entregados=Count('pk', filter=Q(etapa='entregado')),
                desechos_almacenados=Count('pk', filter=Q(etapa='almacenado'))),
            _conteos(PrestamoEquipo.objects.filter(
                unidad_id__in=ids, fecha_salida__date__range=(desde, hasta)), 'unidad_id',
                prestamos=Count('pk'), prestamos_vencidos=Count('pk', filter=Q(
                    estado__in=PrestamoEquipo.ESTADOS_FUERA, fecha_retorno_previsto__lt=timezone.now()))),
        ]
    disponibilidad = disponibilidad_de_unidades(unidades, desde, hasta)
    filas = []
    for unidad in unidades:
        fila = dict.fromkeys(CAMPOS_SUMABLES, 0)
        for tabla in tablas:
            fila.update(tabla.get(unidad.pk, {}))
        porcentajes = [valor[0] for valor in disponibilidad[unidad.pk].values()]
        fila.update({
            'unidad': unidad,
            'disponibilidad': round(sum(porcentajes) / len(porcentajes), 1) if porcentajes else 100.0,
            'url': reverse('admin:reportes-cumplimiento-expediente') + '?' + PeriodoReporte(desde, hasta).query(
                unidad=unidad.slug, anio=hasta.year, corte=''),
            'informes': _informes(unidad, desde, hasta),
        })
        filas.append(fila)
    totales = {campo: sum(fila[campo] for fila in filas) for campo in CAMPOS_SUMABLES}
    totales['disponibilidad'] = (
        round(sum(fila['disponibilidad'] for fila in filas) / len(filas), 1) if filas else 100.0)
    return filas, totales
