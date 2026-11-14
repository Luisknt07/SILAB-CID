"""Uso efectivo frente a jornadas y capacidad histórica declaradas de la unidad."""
from collections import defaultdict
import hashlib
import json

from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_time

from apps.recursos.presentation.capacidad_uso import (
    capacidad_del_dia, dias_del_tramo, indexar_reservas, jornada_del_dia,
    longitud, precargar_uso_unidad, segundos,
)


APPROVED_STATUSES = ('completada',)


def _percentage(numerator, denominator):
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def utilization_level(value):
    """Descripción de la ocupación; nunca es una nota de cumplimiento."""
    if value <= 40:
        return dict(code='low', label='Uso bajo', color='#7b8580')
    if value <= 70:
        return dict(code='moderate', label='Uso moderado', color='#c89421')
    if value <= 90:
        return dict(code='adequate', label='Uso adecuado', color='#2f7653')
    return dict(code='saturation', label='Uso muy alto · revisar', color='#6d4c91')


def _execution_values(reservation):
    """Sólo horario y asistencia capturados; lo solicitado no prueba ejecución."""
    execution = reservation.detalle_ejecucion
    if not isinstance(execution, dict):
        return None
    schedule = execution.get('horario_real')
    if not isinstance(schedule, dict):
        return None
    try:
        start, end = (parse_time(str(schedule.get(c) or '')) for c in ('inicio', 'fin'))
        raw = execution.get('asistentes_total')
        if isinstance(raw, bool) or raw is None or str(raw).strip() != str(int(raw)):
            return None
        people = int(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if not start or not end or end <= start or people < 0:
        return None
    return segundos(start), segundos(end), people


def _registrada_al_corte(reserva, hoy):
    try:
        instante = parse_datetime(str((reserva.detalle_ejecucion or {}).get('registrada_en') or ''))
        if instante is None:
            return False
        fecha = timezone.localtime(instante).date() if timezone.is_aware(instante) else instante.date()
        return fecha <= hoy
    except (TypeError, ValueError, OverflowError):
        return False


def _dentro(inicio, fin, intervalos):
    return any(a <= inicio and fin <= b for a, b in intervalos)


def _identidades(reserva, personas):
    registros = (reserva.detalle_ejecucion or {}).get('participantes')
    if not isinstance(registros, list):
        return None
    ids = [p.get('usuario_id') for p in registros if isinstance(p, dict)
        and p.get('asistencia_codigo') == 'asistio']
    if len(ids) != personas or any(type(pk) is not int or pk <= 0 for pk in ids) or len(set(ids)) != personas:
        return None
    return set(ids)


def _huella(valor):
    return hashlib.sha256(json.dumps(valor, sort_keys=True, ensure_ascii=True,
        separators=(',', ':')).encode()).hexdigest()


def fuente_uso_valida(fuente):
    """Comprobación del contrato JSON archivado, sin aceptar objetos de modelo."""
    if (not isinstance(fuente, dict) or fuente.get('metodo') != 'uso-capacidad-1'
            or type(fuente.get('unidad')) is not int or fuente['unidad'] <= 0
            or any(not isinstance(fuente.get(k), list) for k in (
                'horarios', 'capacidades', 'bloqueos', 'calendarios', 'atenciones', 'alertas'))):
        return False
    try:
        return fuente.get('huella_sha256') == _huella({k: v for k, v in fuente.items() if k != 'huella_sha256'})
    except (ValueError, TypeError, OverflowError):
        return False


def _fuentes_medicion(unit, inicio, fin, corte, context, referencias, alertas):
    """Conserva valores utilizados, no sólo IDs ni referencias mutables."""
    def iso(valor):
        return valor.isoformat() if valor is not None else None
    fuente = dict(metodo='uso-capacidad-1', unidad=unit.pk, inicio=inicio.isoformat(),
        fin=fin.isoformat(), corte=corte.isoformat(), apertura=iso(getattr(unit, 'fecha_inicio', None)),
        horarios=[dict(id=h.pk, periodo=h.periodo_id, dia=h.dia_semana,
            inicio=iso(h.hora_inicio), fin=iso(h.hora_fin), recursos=h.permite_recursos,
            servicios=h.permite_servicios) for h in context['horarios'] if h.pk in referencias['horarios']],
        capacidades=[dict(id=c.pk, periodo=c.periodo_id, desde=iso(c.vigente_desde),
            hasta=iso(c.vigente_hasta), capacidad=c.capacidad_efectiva, fuente=c.fuente,
            factor=c.factor_limitante,
            aforo=getattr(c, 'aforo_seguridad', None), mobiliario=getattr(c, 'puestos_mobiliario', None),
            puestos=getattr(c, 'puestos_equipados', None), personal=getattr(c, 'capacidad_personal', None))
            for c in context['capacidades'] if c.pk in referencias['capacidades']],
        bloqueos=[dict(id=b.pk, desde=iso(b.fecha_inicio), hasta=iso(b.fecha_fin),
            dia_completo=b.dia_completo, inicio=iso(b.hora_inicio), fin=iso(b.hora_fin),
            recursos=b.bloquea_recursos, servicios=b.bloquea_servicios)
            for b in context['bloqueos'] if b.pk in referencias['bloqueos']],
        calendarios=[], atenciones=[dict(id=r.pk, fecha=iso(r.fecha), estado=r.estado,
            tipo=getattr(r, 'tipo_solicitud', ''), detalle_sha256=_huella(r.detalle_ejecucion))
            for r in context['reservas'] if r.pk in referencias['atenciones']], alertas=alertas)
    for calendario in context['calendarios']:
        if calendario.pk not in referencias['calendarios']:
            continue
        semanas = calendario.semanas.all() if hasattr(calendario.semanas, 'all') else calendario.semanas
        fuente['calendarios'].append(dict(id=calendario.pk, periodo=calendario.periodo_id,
            desde=iso(calendario.fecha_inicio_clases), hasta=iso(calendario.fecha_fin_periodo),
            semanas=[dict(desde=iso(s.fecha_inicio), hasta=iso(s.fecha_fin), permite=s.permite_reservas)
                     for s in semanas]))
    for clave in ('horarios', 'capacidades', 'bloqueos', 'calendarios', 'atenciones'):
        fuente[clave].sort(key=lambda r: r['id'])
    fuente['huella_sha256'] = _huella(fuente)
    return fuente


def calculate_unit_utilization(unit, start_date, end_date, *, period=None, context=None, hoy=None):
    """Tiempo real exacto; los porcentajes incompletos llevan ``pending``.

    Frecuencia = tiempo efectivo / tiempo abierto. Ocupación = horas-persona /
    capacidad durante el uso. Utilización = horas-persona / capacidad abierta.
    Una reserva o dato solicitado nunca acredita utilización efectiva.
    """
    hoy = hoy or timezone.localdate()
    if end_date < start_date:
        raise ValueError('La fecha final no puede preceder a la inicial.')
    context = context or precargar_uso_unidad(unit, start_date, end_date, periodo=period)
    if (context.get('unit_id') != unit.pk or context['inicio'] > start_date or context['fin'] < end_date):
        raise ValueError('La precarga debe corresponder a la unidad y cubrir el tramo solicitado.')
    cutoff = min(end_date, hoy)
    apertura = getattr(unit, 'fecha_inicio', None)
    inicio = max(start_date, apertura) if apertura else start_date
    por_fecha = indexar_reservas(context)
    incidencias = defaultdict(lambda: dict(cantidad=0, registros=set()))
    def avisar(codigo, cantidad=1, registro=None):
        incidencias[codigo]['cantidad'] += cantidad
        if registro is not None:
            incidencias[codigo]['registros'].add(registro)
    diarios, fuentes = [], dict(horarios=set(), capacidades=set(), bloqueos=set(), calendarios=set(), atenciones=set())
    for dia in dias_del_tramo(inicio, end_date):
        jornada = jornada_del_dia(context, dia)
        capacidad = capacidad_del_dia(context, dia, jornada['periodos'])
        abierta = jornada['intervalos']
        fuentes['horarios'].update(jornada['horarios'])
        fuentes['bloqueos'].update(jornada['bloqueos'])
        fuentes['calendarios'].update(jornada['calendarios'])
        if capacidad['registro'] is not None:
            fuentes['capacidades'].add(capacidad['registro'])
        medido = dia <= cutoff
        if medido and not jornada['conocida']:
            avisar('sin_jornada')
        if medido and abierta and not capacidad['conocida']:
            avisar('sin_capacidad')
        elif medido and abierta and not capacidad['respaldada']:
            avisar('capacidad_sin_fuente', registro=capacidad['registro'])
        if medido and jornada['ambigua']:
            avisar('calendarios_solapados')
        efectivos, demanda = [], []
        cierres_pendientes = 0
        for reserva in por_fecha.get(dia, []):
            if reserva.estado in ('confirmada', 'en_proceso'):
                if reserva.hora_inicio and reserva.hora_fin:
                    demanda.append((segundos(reserva.hora_inicio), segundos(reserva.hora_fin)))
            if not medido:
                continue
            if not reserva.es_efectiva:
                ahora = timezone.localtime()
                vencida = dia < hoy or (dia == ahora.date() and reserva.hora_fin and reserva.hora_fin < ahora.time())
                if reserva.estado == 'completada' or reserva.estado in ('confirmada', 'en_proceso') and vencida:
                    avisar('sin_cierre', registro=reserva.pk)
                    cierres_pendientes += 1
                continue
            valores = _execution_values(reserva)
            if valores is None or not _registrada_al_corte(reserva, hoy):
                avisar('cierre_incompleto', registro=reserva.pk)
                continue
            a, b, personas = valores
            if personas == 0:
                avisar('sin_asistencia', registro=reserva.pk)
                continue
            efectivos.append((a, b, personas, reserva))
            fuentes['atenciones'].add(reserva.pk)
        puntos = sorted({p for a, b in abierta + jornada['recursos'] + jornada['servicios'] for p in (a, b)} |
                        {p for a, b, _, _ in efectivos for p in (a, b)})
        uso = personas_s = personas_s_brutas = fuera_s = exceso_s = solapado_s = 0
        capacidad_durante_uso = 0
        for a, b in zip(puntos, puntos[1:]):
            activos = [(n, r) for x, y, n, r in efectivos if x <= a and b <= y]
            if not activos:
                continue
            personas, duracion = sum(n for n, _ in activos), b - a
            personas_s_brutas += personas * duracion
            if len(activos) > 1:
                solapado_s += duracion
                identidades = [_identidades(r, n) for n, r in activos]
                if any(ids is None for ids in identidades):
                    avisar('simultaneidad_sin_identidad', duracion / 3600)
                elif len(set().union(*identidades)) != sum(len(ids) for ids in identidades):
                    avisar('personas_duplicadas', duracion / 3600)
            autorizados, fuera = [], False
            for numero, reserva in activos:
                canal = jornada['servicios'] if getattr(reserva, 'tipo_solicitud', '') == 'servicio' else jornada['recursos']
                if not _dentro(a, b, canal):
                    avisar('fuera_jornada', duracion / 3600, reserva.pk)
                    fuera = True
                else:
                    autorizados.append((numero, reserva))
            if fuera:
                fuera_s += duracion
            if autorizados and _dentro(a, b, abierta):
                personas = sum(n for n, _ in autorizados)
                uso += duracion
                if capacidad['conocida']:
                    personas_s += min(capacidad['valor'], personas) * duracion
                    capacidad_durante_uso += capacidad['valor'] * duracion
                    if personas > capacidad['valor']:
                        exceso_s += duracion
                        for _, reserva in activos:
                            avisar('sobrecupo', duracion / 3600, reserva.pk)
                else:
                    personas_s += personas * duracion
        if solapado_s:
            avisar('atenciones_simultaneas', solapado_s / 3600)
        diarios.append(dict(fecha=dia, medido=medido, jornada_conocida=jornada['conocida'],
            capacidad_conocida=capacidad['conocida'], capacidad_respaldada=capacidad['respaldada'],
            capacidad=capacidad['valor'], fuente_capacidad=capacidad['fuente'],
            registro_capacidad=capacidad['registro'], factor_limitante=capacidad['factor'],
            disponible_segundos=longitud(abierta), capacidad_segundos=longitud(abierta) * capacidad['valor'],
            uso_segundos=uso, persona_segundos=personas_s, persona_segundos_brutos=personas_s_brutas,
            capacidad_durante_uso=capacidad_durante_uso,
            fuera_jornada_segundos=fuera_s, sobrecupo_segundos=exceso_s,
            simultaneidad_segundos=solapado_s, bloqueo_segundos=jornada['descuento'],
            demanda_segundos=longitud(demanda), atenciones=len(efectivos),
            cierres_pendientes=cierres_pendientes))
    medidos = [d for d in diarios if d['medido']]
    abiertos = [d for d in medidos if d['disponible_segundos']]
    theoretical_seconds = sum(d['disponible_segundos'] for d in medidos)
    occupied_seconds = sum(d['uso_segundos'] for d in medidos)
    theoretical_person_seconds = sum(d['capacidad_segundos'] for d in medidos)
    person_seconds = sum(d['persona_segundos'] for d in medidos)
    capacity_during_use = sum(d['capacidad_durante_uso'] for d in medidos)
    horarios_conocidos = bool(medidos) and all(d['jornada_conocida'] for d in medidos)
    capacidades_conocidas = bool(abiertos) and all(d['capacidad_conocida'] and d['capacidad_respaldada'] for d in abiertos)
    pendientes_ejecucion = any(c in incidencias for c in ('sin_cierre', 'cierre_incompleto', 'sin_asistencia',
        'fuera_jornada', 'sobrecupo', 'simultaneidad_sin_identidad', 'personas_duplicadas', 'calendarios_solapados'))
    frequency_pending = not horarios_conocidos or not theoretical_seconds or pendientes_ejecucion
    utilization_pending = frequency_pending or not capacidades_conocidas or not theoretical_person_seconds
    mensajes = {
        'sin_jornada': 'Falta declarar la jornada operativa; no se inventa un horario disponible.',
        'sin_capacidad': 'Falta una capacidad operativa histórica aplicable a las jornadas del tramo.',
        'capacidad_sin_fuente': 'La capacidad declarada no indica su acta o fundamento técnico; el porcentaje es informativo.',
        'calendarios_solapados': 'Hay jornadas de varios períodos aplicables a la misma fecha; revisa su alcance.',
        'sin_cierre': 'Hay atenciones vencidas sin cierre efectivo; no acreditan uso.',
        'cierre_incompleto': 'El cierre no conserva horario real, asistencia válida o fecha de registro al corte.',
        'sin_asistencia': 'El cierre declara cero asistentes; no demuestra tiempo de atención efectiva.',
        'fuera_jornada': 'Se registró actividad fuera de la jornada o durante un bloqueo aplicable; requiere revisión.',
        'sobrecupo': 'La asistencia simultánea supera la capacidad declarada; el exceso no infla la utilización.',
        'atenciones_simultaneas': 'Hubo atenciones simultáneas; la franja se cuenta una vez y debe comprobarse que las personas no se duplican.',
        'simultaneidad_sin_identidad': 'La asistencia simultánea no está completamente identificada; revisa las listas antes de acreditar el cumplimiento.',
        'personas_duplicadas': 'Una misma persona figura en atenciones simultáneas; requiere conciliar sus registros.',
    }
    alertas = [dict(codigo=c, mensaje=mensajes[c], cantidad=round(v['cantidad'], 4),
                    registros=sorted(v['registros'])) for c, v in sorted(incidencias.items())]
    utilization = min(100.0, _percentage(person_seconds, theoretical_person_seconds)) if theoretical_person_seconds else 0.0
    ultimo = medidos[-1] if medidos else None
    snapshot_id = ultimo['registro_capacidad'] if ultimo else None
    snapshot = next((c for c in context['capacidades'] if c.pk == snapshot_id), None)
    return dict(unit=unit, start_date=start_date, end_date=end_date, measured_until=cutoff,
        snapshot=snapshot, capacity=ultimo['capacidad'] if ultimo else 0,
        limiting_factor=ultimo['factor_limitante'] if ultimo else 'Sin tramo medido',
        theoretical_hours=round(theoretical_seconds / 3600, 4), occupied_hours=round(occupied_seconds / 3600, 4),
        theoretical_person_hours=round(theoretical_person_seconds / 3600, 4),
        actual_person_hours=round(person_seconds / 3600, 4),
        actual_person_hours_raw=round(sum(d['persona_segundos_brutos'] for d in medidos) / 3600, 4),
        frequency=_percentage(occupied_seconds, theoretical_seconds),
        occupancy=_percentage(person_seconds, capacity_during_use), utilization=utilization,
        level=utilization_level(utilization), equipment_total=context['equipo_total'],
        equipment_available=context['equipo_disponible'],
        equipment_availability=_percentage(context['equipo_disponible'], context['equipo_total']),
        administrative_block_hours=round(sum(d['bloqueo_segundos'] for d in medidos) / 3600, 4),
        available_hours_period=round(sum(d['disponible_segundos'] for d in diarios) / 3600, 4),
        planned_hours=round(sum(d['demanda_segundos'] for d in diarios) / 3600, 4),
        effective_attentions=sum(d['atenciones'] for d in medidos),
        pending=utilization_pending, frequency_pending=frequency_pending,
        utilization_pending=utilization_pending, denominator_known=horarios_conocidos and capacidades_conocidas,
        quality='pendiente' if utilization_pending else 'con_observaciones' if alertas else 'comprobable',
        calidad='pendiente' if utilization_pending else 'con_observaciones' if alertas else 'comprobable',
        fuera_jornada_horas=round(sum(d['fuera_jornada_segundos'] for d in medidos) / 3600, 4),
        sobrecupo_horas=round(sum(d['sobrecupo_segundos'] for d in medidos) / 3600, 4),
        daily=diarios, fuentes={k: sorted(v) for k, v in fuentes.items()}, alertas=alertas,
        fuentes_medicion=_fuentes_medicion(unit, start_date, end_date, cutoff, context, fuentes, alertas))
