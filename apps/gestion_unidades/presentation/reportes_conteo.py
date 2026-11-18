"""Cuánto hay detrás de cada documento que el Centro de reportes genera de los registros.

La tabla de anexos muestra, en la fila de cada respaldo o consulta, cuántos registros tiene en el período o,
si el documento describe el estado actual de la unidad, cuántos elementos hay. Cada lectura es un solo
``count()``; las consultas sin un conteo sencillo no consultan nada y se calculan al abrir el documento.
"""
from django.db.models import Q


def _capacitacion(unidad, desde, hasta):
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    from apps.gestion_unidades.presentation.reportes_auditoria import ACTIVIDADES
    return (EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo__in=[codigo for codigo, _ in ACTIVIDADES],
                                                  fecha__range=(desde, hasta)).exclude(estado='anulado').count())


def _simulacros(unidad, desde, hasta):
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    from apps.documentos.models.resultados_gestion import TIPO_SIMULACRO
    return (EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo=TIPO_SIMULACRO, fecha__range=(desde, hasta))
            .exclude(estado='anulado').count())


def _satisfaccion(unidad, desde, hasta):
    from apps.reservas.models.valoraciones import RESERVA_ATENDIDA, ValoracionReserva
    return ValoracionReserva.objects.filter(
        reserva__laboratorio=unidad, reserva__fecha__range=(desde, hasta),
        **{f'reserva__{campo}': valor for campo, valor in RESERVA_ATENDIDA.items()}).count()


def _calibracion(unidad, desde, hasta):
    from apps.documentos.models.funcionalidad import equipos_del_alcance
    return (equipos_del_alcance(unidad).filter(activa=True, fecha_baja__isnull=True)
            .filter(Q(equipo__fecha_ultima_calibracion__isnull=False) | Q(equipo__proxima_calibracion__isnull=False))
            .count())


def _personal(unidad, desde, hasta):
    from apps.gestion_unidades.models.espacios import ResponsableUnidad
    return ResponsableUnidad.objects.filter(unidad=unidad, activo=True).count()


def _sustancias(unidad, desde, hasta):
    from apps.recursos.models.consumibles import Consumible
    return Consumible.objects.filter(unidad=unidad, activo=True, sustancia_controlada=True).count()


def _desechos(unidad, desde, hasta):
    from apps.recursos.models.desechos import RegistroDesecho
    return RegistroDesecho.objects.filter(unidad=unidad, fecha_generacion__range=(desde, hasta)).count()


def _auditoria(unidad, desde, hasta):
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad
    return RegistroAuditoriaUnidad.objects.filter(unidad=unidad, creado_en__date__range=(desde, hasta)).count()


# {categoría: (lectura, singular, plural)}. Personal, sustancias y calibración son estado actual de la unidad.
CONTEOS = {
    'capacitacion': (_capacitacion, 'capacitación o difusión', 'capacitaciones y difusiones'),
    'simulacros': (_simulacros, 'simulacro', 'simulacros'),
    'satisfaccion': (_satisfaccion, 'valoración', 'valoraciones'),
    'calibracion': (_calibracion, 'equipo con calibración', 'equipos con calibración'),
    'personal': (_personal, 'persona', 'personas'),
    'sustancias': (_sustancias, 'sustancia', 'sustancias'),
    'desechos': (_desechos, 'registro de desechos', 'registros de desechos'),
    'auditoria': (_auditoria, 'movimiento registrado', 'movimientos registrados'),
}
SIN_CONTEO = 'Se genera al consultar'


def lo_registrado(codigo, unidad, desde, hasta):
    """(texto de «Registrado», hay registros): una consulta como máximo; ninguna si no hay conteo sencillo."""
    conteo = CONTEOS.get(codigo)
    if conteo is None:
        return SIN_CONTEO, None
    lectura, singular, plural = conteo
    cantidad = lectura(unidad, desde, hasta)
    return f'{cantidad} {singular if cantidad == 1 else plural}', cantidad > 0
