"""Si una unidad tiene registros del módulo que alimenta una categoría del Centro de reportes.

Las consultas de gestión que no son anexos del expediente solo se ofrecen cuando la
unidad usa ese módulo: un informe de aula, visitas o finanzas sin un solo registro
no aporta nada a la Dirección. Cada lectura es un ``exists()`` sobre la unidad, sin
filtrar por fechas: basta con que el módulo tenga historia para que la consulta del
período tenga sentido. Las categorías que no figuran aquí se ofrecen siempre.
"""
from django.db.models import Q

# Se consultan siempre: la trazabilidad de la unidad y su capacidad declarada existen sin otros registros.
SIEMPRE = frozenset(('auditoria', 'uso-capacidad'))
# El respaldo para auditoría es una lista de comprobación: el documento se ofrece aunque no haya registros,
# porque «no se registraron simulacros en el período» también responde. La satisfacción conserva su lectura.
SIEMPRE |= frozenset(('capacitacion', 'calibracion', 'sustancias', 'personal', 'reglamento', 'simulacros'))


def _equipos(unidad):
    from apps.recursos.models.unidades import UnidadEquipo
    return UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))


def _asignaturas(unidad):
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.reservas.models.reservas import Reserva
    return (PlanificacionPractica.objects.filter(unidad=unidad, eliminado_en__isnull=True).exists()
            or Reserva.objects.filter(laboratorio=unidad, programacion__isnull=False).exists())


def _reservas(unidad):
    from apps.reservas.models.reservas import Reserva
    return Reserva.objects.filter(laboratorio=unidad).exists()


def _aula(unidad):
    from apps.formacion.models.aula import EjercicioAula
    return EjercicioAula.objects.filter(unidad=unidad).exists()


def _mantenimiento(unidad):
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    from apps.recursos.models.mantenimiento import MantenimientoEquipo, PlanMantenimientoEquipo
    equipos = _equipos(unidad).values('pk')
    return (MantenimientoEquipo.objects.filter(Q(unidad=unidad) | Q(equipo_id__in=equipos)).exists()
            or PlanMantenimientoEquipo.objects.filter(equipo_id__in=equipos).exists()
            or EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo__in=('PLAN-INFRA', 'EJECUCION-INFRA')).exists())


def _retiros(unidad):
    from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
    return (_equipos(unidad).filter(Q(fecha_baja__isnull=False) | Q(reemplazado_por__isnull=False)).exists()
            or EventoCicloVidaEquipo.objects.filter(unidad=unidad).filter(
                Q(tipo__in=('baja', 'disposicion'))
                | Q(tipo='actualizacion', descripcion__startswith='Retiro/sustitución: ')).exists())


def _inventario(unidad):
    from apps.recursos.models.consumibles import Consumible, EntradaInventario
    return (Consumible.objects.filter(unidad=unidad).exists()
            or EntradaInventario.objects.filter(Q(unidad=unidad) | Q(consumible__unidad=unidad)).exists())


def _prestamos(unidad):
    from apps.recursos.models.prestamos import PrestamoEquipo
    return PrestamoEquipo.objects.filter(Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad)).exists()


def _visitas(unidad):
    from apps.reservas.models.visitas import SolicitudVisita
    return SolicitudVisita.objects.filter(unidad=unidad).exists()


def _cursos(unidad):
    from apps.formacion.models.cursos import Curso
    return Curso.objects.filter(unidad=unidad).exists()


def _finanzas(unidad):
    from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
    from apps.reservas.models.reservas import Reserva
    return (MovimientoFinancieroUnidad.objects.filter(unidad=unidad).exists()
            or Reserva.objects.filter(laboratorio=unidad, costo_real__isnull=False, estado='completada').exists())


def _procesos(unidad):
    from apps.plantas_piloto.operacion.models.produccion import EtapaReceta
    return EtapaReceta.objects.filter(receta__unidad=unidad).exists()


def _calidad(unidad):
    from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad
    return (ControlCalidad.objects.reales().filter(unidad=unidad).exists()
            or NoConformidad.objects.reales().filter(unidad=unidad).exists())


def _produccion(unidad):
    from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
    return OrdenProduccion.objects.reales().filter(unidad=unidad).exists()


def _ejecuciones(unidad):
    from apps.formacion.models.practicas import EjecucionPractica
    return EjecucionPractica.objects.filter(planificacion__unidad=unidad).exists()


def _desechos(unidad):
    from apps.recursos.models.desechos import RegistroDesecho
    return RegistroDesecho.objects.filter(unidad=unidad).exists()


def _satisfaccion(unidad):
    from apps.reservas.models.valoraciones import ValoracionReserva
    return ValoracionReserva.objects.filter(reserva__laboratorio=unidad).exists()


# Ejecuciones y desechos son consultas de detalle desde documentos.0025: su evidencia va en los anexos de
# prácticas y de seguridad, y la consulta solo se ofrece si la unidad tiene registros.
LECTURAS = {
    'ejecuciones': _ejecuciones, 'desechos': _desechos,
    'asignaturas': _asignaturas, 'reservas': _reservas, 'aula': _aula, 'mantenimiento': _mantenimiento,
    'retiros': _retiros, 'inventario': _inventario, 'prestamos': _prestamos, 'visitas': _visitas,
    'cursos': _cursos, 'finanzas': _finanzas, 'procesos': _procesos, 'calidad': _calidad,
    'produccion': _produccion,
    'satisfaccion': _satisfaccion,
}


def tiene_registros(categoria, unidad):
    """Verdadero si la categoría se consulta siempre, no tiene lectura propia o la unidad registró algo en ella."""
    if categoria in SIEMPRE:
        return True
    lectura = LECTURAS.get(categoria)
    return True if lectura is None else bool(lectura(unidad))
