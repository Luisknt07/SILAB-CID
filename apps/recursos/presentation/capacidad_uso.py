"""Agenda y capacidad precargadas para medir uso sin inventar jornadas ni aforo."""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Q

from apps.core.models.periodos import VersionCalendarioAcademico
from apps.core.presentation.calendario import ambitos_operacion
from apps.gestion_unidades.models.operaciones import (
    BloqueoAgendaUnidad, CapacidadOperativaUnidad, HorarioOperacionUnidad, HORA_ALMUERZO,
)
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import Reserva


def segundos(hora):
    return hora.hour * 3600 + hora.minute * 60 + hora.second


def unir(intervalos):
    salida = []
    for inicio, fin in sorted((a, b) for a, b in intervalos if b > a):
        if salida and inicio <= salida[-1][1]:
            salida[-1] = (salida[-1][0], max(fin, salida[-1][1]))
        else:
            salida.append((inicio, fin))
    return salida


def restar(intervalos, cierres):
    salida = unir(intervalos)
    for a, b in unir(cierres):
        partes = []
        for inicio, fin in salida:
            if b <= inicio or a >= fin:
                partes.append((inicio, fin))
            else:
                if inicio < a:
                    partes.append((inicio, a))
                if b < fin:
                    partes.append((b, fin))
        salida = partes
    return salida


def longitud(intervalos):
    return sum(fin - inicio for inicio, fin in unir(intervalos))


def precargar_uso_unidad(unidad, inicio, fin, *, periodo=None):
    """Número fijo de consultas, reutilizable en semanas y meses del mismo tramo."""
    horarios = list(HorarioOperacionUnidad.objects.filter(unidad=unidad, activo=True))
    capacidades = list(CapacidadOperativaUnidad.objects.filter(unidad=unidad, activo=True,
        vigente_desde__lte=fin).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=inicio)))
    bloqueos = list(BloqueoAgendaUnidad.objects.filter(unidad=unidad, activo=True,
        alcance='unidad_completa', fecha_inicio__lte=fin, fecha_fin__gte=inicio))
    calendarios = list(VersionCalendarioAcademico.objects.filter(vigente=True,
        periodo__estado__in=('publicado', 'cerrado'), periodo__ambito__in=ambitos_operacion(), fecha_inicio_clases__lte=fin,
        fecha_fin_periodo__gte=inicio).select_related('periodo').prefetch_related('semanas'))
    reservas = list(Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin)))
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad),
        activa=True, fecha_baja__isnull=True).distinct()
    estados = list(equipos.values_list('estado_unidad', flat=True))
    return dict(unit_id=unidad.pk, inicio=inicio, fin=fin, horarios=horarios,
        capacidades=capacidades, bloqueos=bloqueos, calendarios=calendarios,
        reservas=reservas, periodo=periodo, equipo_total=len(estados),
        equipo_disponible=sum(e == 'disponible' for e in estados))


def _semanas(calendario):
    valor = calendario.semanas
    return list(valor.all()) if hasattr(valor, 'all') else list(valor)


def jornada_del_dia(contexto, fecha):
    """La jornada específica sustituye a la general sólo dentro de su calendario."""
    vigentes = [c for c in contexto['calendarios']
        if c.fecha_inicio_clases <= fecha <= c.fecha_fin_periodo]
    periodo = contexto.get('periodo')
    if periodo is not None:
        vigentes = [c for c in vigentes if c.periodo_id == periodo.pk]
    periodos = {c.periodo_id for c in vigentes}
    especificos = [h for h in contexto['horarios'] if h.periodo_id in periodos]
    aplicables = especificos or [h for h in contexto['horarios'] if h.periodo_id is None]
    calendarios_aplicables = ([c for c in vigentes if c.periodo_id in {h.periodo_id for h in especificos}]
                              if especificos else vigentes)
    periodos_aplicables = {c.periodo_id for c in calendarios_aplicables}
    suspendida = any(not s.permite_reservas for c in calendarios_aplicables for s in _semanas(c)
        if s.fecha_inicio <= fecha <= s.fecha_fin)
    recursos, servicios = [], []
    for horario in aplicables:
        if horario.dia_semana != fecha.weekday():
            continue
        franja = [(segundos(horario.hora_inicio), segundos(horario.hora_fin))]
        if horario.permite_recursos:
            recursos.extend(restar(franja, [(HORA_ALMUERZO * 3600, (HORA_ALMUERZO + 1) * 3600)]))
        if horario.permite_servicios:
            servicios.extend(franja)
    recursos, servicios = unir(recursos), unir(servicios)
    antes = unir(recursos + servicios)
    cierres_recursos, cierres_servicios, ids_cierres = [], [], []
    for bloqueo in contexto['bloqueos']:
        if not bloqueo.fecha_inicio <= fecha <= bloqueo.fecha_fin:
            continue
        franja = (0, 86400) if bloqueo.dia_completo else (
            segundos(bloqueo.hora_inicio), segundos(bloqueo.hora_fin)) if (
                bloqueo.hora_inicio and bloqueo.hora_fin) else None
        if franja is None:
            continue
        ids_cierres.append(bloqueo.pk)
        if bloqueo.bloquea_recursos:
            cierres_recursos.append(franja)
        if bloqueo.bloquea_servicios:
            cierres_servicios.append(franja)
    recursos = [] if suspendida else restar(recursos, cierres_recursos)
    servicios = [] if suspendida else restar(servicios, cierres_servicios)
    disponibles = unir(recursos + servicios)
    return dict(intervalos=disponibles, recursos=recursos, servicios=servicios,
        conocida=bool(aplicables), suspendida=suspendida,
        descuento=longitud(antes) - longitud(disponibles),
        horarios=[h.pk for h in aplicables], bloqueos=ids_cierres,
        calendarios=[c.pk for c in calendarios_aplicables], periodos=periodos_aplicables,
        ambigua=len({h.periodo_id for h in especificos}) > 1)


def capacidad_del_dia(contexto, fecha, periodos=()):
    filas = [c for c in contexto['capacidades'] if c.vigente_desde <= fecha
        and (c.vigente_hasta is None or c.vigente_hasta >= fecha)
        and (c.periodo_id is None or c.periodo_id in periodos)]
    especificas = [c for c in filas if c.periodo_id in periodos and c.periodo_id is not None]
    candidatas = especificas or [c for c in filas if c.periodo_id is None]
    fila = max(candidatas, key=lambda c: (c.vigente_desde, c.pk or 0), default=None)
    valor = fila.capacidad_efectiva if fila else 0
    return dict(valor=max(0, valor), conocida=bool(fila), respaldada=bool(fila and fila.fuente.strip()),
        registro=fila.pk if fila else None, fuente=fila.fuente if fila else '',
        factor=fila.factor_limitante if fila else 'Capacidad operativa sin declarar')


def dias_del_tramo(inicio, fin):
    actual = inicio
    while actual <= fin:
        yield actual
        actual += timedelta(days=1)


def indexar_reservas(contexto):
    salida = defaultdict(list)
    for reserva in contexto['reservas']:
        salida[reserva.fecha].append(reserva)
    return salida
