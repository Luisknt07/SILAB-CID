"""Seguimiento del mantenimiento de los equipos de una unidad.

Responde, con los registros que ya existen, a las preguntas que hace la
auditoría: qué equipo está al día y cuál no, cada cuánto se le hace
mantenimiento y cuándo le toca, cuál se hizo y cuál falta, quién lo hizo y
cuánto costó, qué repuestos llevó, cuánta vida útil le queda, cuál está
obsoleto y qué pasó con los que se dieron de baja.

Todo se resume en un semáforo por equipo —crítico, atención, al día— y en
series por mes para los gráficos del panel, de modo que el seguimiento se lea
de un vistazo.
"""

from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta
from decimal import Decimal
from itertools import groupby
from math import ceil

from django.db.models import Count, DecimalField, F, Q, Sum
from django.utils import timezone

from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo, RepuestoMantenimiento
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.areas_recursos import asignaciones_por_area, grupos_de_filas
from apps.recursos.presentation.inventario_gestion import preparar_recursos_de_equipos, vinculos_del_modelo

MESES_CORTOS = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MESES_SERIE = 12
# Un equipo con la vida útil por encima de este porcentaje entra en renovación.
VIDA_UTIL_ALERTA = 80
ESTADOS_FUERA_DE_SERVICIO = ('dañado', 'mantenimiento', 'no_disponible')

SEMAFOROS = {
    'baja': ('Dado de baja', 'baja'),
    'critico': ('Requiere intervención', 'critico'),
    'atencion': ('Requiere atención', 'atencion'),
    'al_dia': ('Al día', 'al_dia'),
}
# La tabla ya dice la criticidad de cada equipo; en una columna cabe la
# palabra, no la definición completa.
CRITICIDAD_CORTA = {'critico': 'Crítico', 'importante': 'Importante', 'normal': 'Normal'}

# Lo que viene, por urgencia. Las ventanas se cuentan desde hoy.
VENTANAS_AGENDA = (
    ('vencido', 'Vencidos', 'critico', None, -1),
    ('semana', 'Esta semana', 'atencion', 0, 7),
    ('mes', 'Este mes', 'atencion', 8, 30),
    ('despues', 'Más adelante', 'al_dia', 31, None),
)


def agenda_de_mantenimiento(unidad, hoy=None, limite=24):
    """Qué toca y cuándo, agrupado por urgencia.

    El listado de planes repetía lo que la tabla ya dice equipo por equipo. Lo
    que falta al operar no es el plan otra vez, sino en qué orden atenderlo:
    primero lo vencido, después esta semana y el resto del mes.
    """
    hoy = hoy or timezone.localdate()
    planes = (PlanMantenimientoEquipo.objects
              .filter(equipo__in=equipos_de(unidad, incluir_bajas=False), activo=True)
              .select_related('equipo', 'equipo__equipo', 'responsable')
              .order_by('proxima_ejecucion')[:limite])
    grupos = {clave: [] for clave, *_ in VENTANAS_AGENDA}
    for plan in planes:
        dias = (plan.proxima_ejecucion - hoy).days
        for clave, _etiqueta, _tono, desde, hasta in VENTANAS_AGENDA:
            if (desde is None or dias >= desde) and (hasta is None or dias <= hasta):
                grupos[clave].append({'plan': plan, 'dias': dias})
                break
    return [
        {'clave': clave, 'etiqueta': etiqueta, 'tono': tono, 'items': grupos[clave]}
        for clave, etiqueta, tono, _desde, _hasta in VENTANAS_AGENDA if grupos[clave]
    ]


def equipos_de(unidad, incluir_bajas=True):
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()
    if not incluir_bajas:
        equipos = equipos.filter(activa=True, fecha_baja__isnull=True)
    else:
        equipos = equipos.filter(Q(activa=True) | Q(fecha_baja__isnull=False))
    return equipos.select_related('equipo')


def _meses_recientes(hoy, cantidad=MESES_SERIE):
    """[(anio, mes, 'Abr 26')] terminando en el mes actual."""
    serie = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        serie.append((anio, mes, f'{MESES_CORTOS[mes]} {str(anio)[-2:]}'))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(serie))


def _fecha_local(valor):
    """La misma fecha institucional utilizada por los filtros SQL __date."""
    if isinstance(valor, datetime):
        return timezone.localtime(valor).date() if timezone.is_aware(valor) else valor.date()
    return valor


def _ejecutada_al_corte(estado, fin, hoy):
    return estado == 'completado' and fin is not None and _fecha_local(fin) <= hoy


def _dias_intervalos_ordenados(intervalos):
    """Une intervalos ya ordenados sin conservar el historial en memoria."""
    inicio_actual = fin_actual = None
    segundos = 0
    for inicio, fin in intervalos:
        if not inicio or not fin or fin <= inicio:
            continue
        if fin_actual is None:
            inicio_actual, fin_actual = inicio, fin
        elif inicio <= fin_actual:
            fin_actual = max(fin_actual, fin)
        else:
            segundos += (fin_actual - inicio_actual).total_seconds()
            inicio_actual, fin_actual = inicio, fin
    if fin_actual is not None:
        segundos += (fin_actual - inicio_actual).total_seconds()
    return ceil(segundos / 86400)


def _dias_fuera_de_servicio(mantenimientos):
    """Días detenido, sin duplicar órdenes simultáneas sobre el mismo activo."""
    intervalos = sorted((m.fecha_inicio, m.fecha_fin) for m in mantenimientos
                        if m.fecha_inicio and m.fecha_fin and m.fecha_fin > m.fecha_inicio)
    return _dias_intervalos_ordenados(intervalos)


def _resumen_de_ordenes(claves, unidad, hoy):
    """Escalares por equipo; el historial se recorre en lotes sin conservarlo."""
    resumenes = {}
    ordenes = (MantenimientoEquipo.objects.filter(equipo__in=claves)
               .order_by('-fecha_programada', '-pk')
               .values_list('equipo_id', 'estado', 'fecha_programada',
                            'fecha_inicio', 'fecha_fin', 'costo', 'unidad_id', 'equipo__laboratorio_id'))
    for equipo_id, estado, programada, inicio, fin, costo, unidad_id, adscripcion_id in ordenes.iterator(chunk_size=500):
        resumen = resumenes.get(equipo_id)
        if resumen is None:
            resumen = {
                'programados': 0, 'completados': 0, 'ultimo': None,
                'dias_detenido': 0, 'costo': Decimal(0),
            }
            resumenes[equipo_id] = resumen
        resumen['programados'] += 1
        if not _ejecutada_al_corte(estado, fin, hoy):
            continue
        # «Último» describe la intervención real, aunque una orden programada
        # antes haya terminado después de las más recientes.
        if resumen['ultimo'] is None or fin > resumen['ultimo']:
            resumen['ultimo'] = fin
        resumen['completados'] += 1
        # La condición e historia acompañan al activo; el gasto pertenece a la
        # unidad capturada en la orden, incluso si el activo está compartido.
        # Si falta, la adscripción primaria actual evita duplicar gasto legado;
        # ese respaldo no reconstruye quién financió históricamente la orden.
        if unidad_id == unidad.pk or (unidad_id is None and adscripcion_id == unidad.pk):
            resumen['costo'] += costo or Decimal(0)
    # Segundo recorrido pequeño y ordenado por inicio: permite unir los
    # intervalos de cada activo con memoria constante aunque haya miles.
    intervalos = (MantenimientoEquipo.objects.filter(equipo__in=claves, estado='completado',
                    fecha_inicio__isnull=False, fecha_fin__gt=F('fecha_inicio'), fecha_fin__date__lte=hoy)
                  .order_by('equipo_id', 'fecha_inicio', 'fecha_fin')
                  .values_list('equipo_id', 'fecha_inicio', 'fecha_fin').iterator(chunk_size=500))
    for equipo_id, registros in groupby(intervalos, key=lambda registro: registro[0]):
        resumenes[equipo_id]['dias_detenido'] = _dias_intervalos_ordenados((inicio, fin) for _, inicio, fin in registros)
    return resumenes


def semaforo_equipo(equipo, hoy, *, planes, incidencias, vencidos, por_vencer, bloqueantes=0):
    """Estado del equipo y por qué: lo que la unidad debe atender primero.

    Un equipo de baja sale del semáforo operativo. Después pesa lo que detiene
    el servicio: incidencia bloqueante, mantenimiento vencido o un equipo
    crítico sin plan. La vida útil cumplida y las incidencias abiertas piden
    atención sin detener nada.
    """
    motivos = []
    if equipo.fecha_baja:
        motivo = equipo.get_motivo_baja_display() if equipo.motivo_baja else 'sin motivo declarado'
        return 'baja', [f'Baja del {equipo.fecha_baja:%d/%m/%Y}: {motivo}.']

    consumida = equipo.vida_util_consumida(hoy)
    if equipo.estado_unidad == 'dañado':
        motivos.append('Fuera de servicio por daño.')
    elif equipo.estado_unidad == 'no_localizado':
        motivos.append('Equipo no localizado: verificar existencia y custodia.')
    if bloqueantes:
        motivos.append(f'{bloqueantes} incidencia(s) abierta(s) impiden la operación.')
    if vencidos:
        motivos.append(f'{vencidos} plan(es) de mantenimiento vencido(s).')
    if equipo.criticidad == 'critico' and not planes:
        motivos.append('Equipo crítico sin plan de mantenimiento vigente.')
    if motivos:
        return 'critico', motivos

    if incidencias:
        motivos.append(f'{incidencias} incidencia(s) abierta(s).')
    if por_vencer:
        motivos.append(f'{por_vencer} mantenimiento(s) por vencer.')
    if consumida is not None and consumida >= 100:
        motivos.append('Vida útil cumplida: evaluar renovación o baja.')
    elif consumida is not None and consumida >= VIDA_UTIL_ALERTA:
        motivos.append(f'Vida útil al {consumida} %.')
    if equipo.estado_unidad == 'mantenimiento':
        motivos.append('En mantenimiento.')
    elif equipo.estado_unidad == 'no_disponible':
        motivos.append('No disponible en el inventario: revisar su condición antes de habilitarlo.')
    elif equipo.estado_unidad == 'obsoleto':
        motivos.append('Obsoleto en el inventario: evaluar continuidad, reparación o reposición.')
    if motivos:
        return 'atencion', motivos
    return 'al_dia', ['Con plan vigente y sin novedades.' if planes else 'Sin novedades registradas.']


def filas_de_equipos(unidad, hoy=None):
    """Una fila por equipo con su semáforo, su plan, su historial y su costo."""
    hoy = hoy or timezone.localdate()
    equipos = list(equipos_de(unidad).select_related('equipo__familia', 'reemplazado_por').prefetch_related(
        'equipo__categorias', 'espacios_asociados'))
    if not equipos:
        return []
    claves = [equipo.pk for equipo in equipos]

    planes = {}
    for plan in (PlanMantenimientoEquipo.objects.filter(equipo__in=claves, activo=True)
                 .select_related('responsable').order_by('proxima_ejecucion')):
        planes.setdefault(plan.equipo_id, []).append(plan)

    ordenes = _resumen_de_ordenes(claves, unidad, hoy)
    incidencias = {
        equipo_id: dict(total=total, bloqueantes=bloqueantes)
        for equipo_id, total, bloqueantes in (
        IncidenciaEquipo.objects.filter(equipo__in=claves)
        .exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS)
        .order_by().values('equipo_id').annotate(total=Count('pk'), bloqueantes=Count('pk', filter=Q(detiene_operacion=True)))
        .values_list('equipo_id', 'total', 'bloqueantes').iterator(chunk_size=500))
    }
    repuestos = {
        fila['mantenimiento__equipo']: fila['total']
        for fila in RepuestoMantenimiento.objects.filter(
            Q(mantenimiento__unidad=unidad) | Q(mantenimiento__unidad__isnull=True, mantenimiento__equipo__laboratorio=unidad),
            mantenimiento__equipo__in=claves, mantenimiento__estado='completado', mantenimiento__fecha_fin__date__lte=hoy)
        .values('mantenimiento__equipo')
        .annotate(total=Sum(F('cantidad') * F('costo_unitario'),
                            output_field=DecimalField(max_digits=14, decimal_places=2)))
    }

    asignacion = asignaciones_por_area(unidad, equipos)['por_equipo']
    filas = []
    for equipo in equipos:
        propios = planes.get(equipo.pk, [])
        historial = ordenes.get(equipo.pk, {})
        vencidos = [p for p in propios if p.proxima_ejecucion < hoy]
        por_vencer = [p for p in propios
                      if hoy <= p.proxima_ejecucion <= hoy + timedelta(days=p.anticipacion_dias)]
        proximo = min((p.proxima_ejecucion for p in propios), default=None)
        ultimo = historial.get('ultimo')
        costo = historial.get('costo', Decimal(0))
        estado, motivos = semaforo_equipo(
            equipo, hoy, planes=propios, incidencias=incidencias.get(equipo.pk, {}).get('total', 0),
            vencidos=len(vencidos), por_vencer=len(por_vencer),
            bloqueantes=incidencias.get(equipo.pk, {}).get('bloqueantes', 0),
        )
        filas.append({
            'equipo': equipo,
            **asignacion[equipo.pk],
            'semaforo': estado,
            'etiqueta': SEMAFOROS[estado][0],
            'motivos': motivos,
            'criticidad': equipo.get_criticidad_display(),
            'criticidad_corta': CRITICIDAD_CORTA.get(equipo.criticidad, equipo.criticidad),
            'planes': propios,
            'frecuencia': min((p.frecuencia_dias for p in propios), default=None),
            'proximo': proximo,
            'dias_para_proximo': (proximo - hoy).days if proximo else None,
            'ultimo': _fecha_local(ultimo),
            'completados': historial.get('completados', 0),
            'programados': historial.get('programados', 0),
            'incidencias_abiertas': incidencias.get(equipo.pk, {}).get('total', 0),
            'dias_detenido': historial.get('dias_detenido', 0),
            'costo': costo + Decimal(repuestos.get(equipo.pk, 0) or 0),
            'vida_util': equipo.vida_util_consumida(hoy),
            'fin_vida_util': equipo.fin_vida_util,
            'en_garantia': equipo.en_garantia(hoy),
        })
    orden_semaforo = {'critico': 0, 'atencion': 1, 'al_dia': 2, 'baja': 3}
    return sorted(filas, key=lambda f: (orden_semaforo[f['semaforo']], f['equipo'].codigo_unidad))


def series_por_mes(unidad, hoy=None, cantidad=MESES_SERIE):
    """Programados, completados y costo de cada mes, para el gráfico de cumplimiento."""
    hoy = hoy or timezone.localdate()
    meses = _meses_recientes(hoy, cantidad)
    inicio = date(meses[0][0], meses[0][1], 1)
    ordenes = MantenimientoEquipo.objects.filter(
        Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad),
        fecha_programada__date__gte=inicio,
    ).distinct()
    programados, completados, costos = Counter(), Counter(), Counter()
    for orden in ordenes.only('fecha_programada', 'fecha_fin', 'estado', 'costo').iterator(chunk_size=500):
        programada = _fecha_local(orden.fecha_programada)
        clave = (programada.year, programada.month)
        programados[clave] += 1
        if _ejecutada_al_corte(orden.estado, orden.fecha_fin, hoy):
            cierre = _fecha_local(orden.fecha_fin)
            completados[(cierre.year, cierre.month)] += 1
            costos[(cierre.year, cierre.month)] += float(orden.costo or 0)
    for fin, programada, cantidad_repuesto, costo_unitario in RepuestoMantenimiento.objects.filter(
            mantenimiento__in=ordenes.filter(estado='completado', fecha_fin__date__lte=hoy)).values_list(
                'mantenimiento__fecha_fin', 'mantenimiento__fecha_programada', 'cantidad', 'costo_unitario').iterator(chunk_size=500):
        cierre = _fecha_local(fin)
        costos[(cierre.year, cierre.month)] += float(cantidad_repuesto * costo_unitario)
    return [{
        'etiqueta': etiqueta,
        'programados': programados.get((anio, mes), 0),
        'completados': completados.get((anio, mes), 0),
        'costo': round(costos.get((anio, mes), 0.0), 2),
    } for anio, mes, etiqueta in meses]


def _reparto_vida_util(filas):
    reparto = Counter()
    for fila in filas:
        if fila['semaforo'] == 'baja':
            continue
        consumida = fila['vida_util']
        if consumida is None:
            reparto['sin_definir'] += 1
        elif consumida >= 100:
            reparto['cumplida'] += 1
        elif consumida >= VIDA_UTIL_ALERTA:
            reparto['por_renovar'] += 1
        else:
            reparto['vigente'] += 1
    return reparto


def _costo_acumulado_unidad(unidad, hoy):
    """Gasto ejecutado propio, conservado aunque el activo haya sido trasladado."""
    ordenes = MantenimientoEquipo.objects.filter(
        Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad),
        estado='completado', fecha_fin__date__lte=hoy,
    )
    servicio = ordenes.aggregate(total=Sum('costo'))['total'] or Decimal(0)
    repuestos = RepuestoMantenimiento.objects.filter(mantenimiento__in=ordenes).aggregate(
        total=Sum(F('cantidad') * F('costo_unitario'), output_field=DecimalField(max_digits=14, decimal_places=2)),
    )['total'] or Decimal(0)
    return servicio + repuestos


def panel_mantenimiento(unidad, hoy=None):
    """Todo lo que el panel necesita: semáforo, cifras, series y bajas del período."""
    hoy = hoy or timezone.localdate()
    filas = filas_de_equipos(unidad, hoy)
    activos = [f for f in filas if f['semaforo'] != 'baja']
    con_plan = [f for f in activos if f['planes']]
    criticos_sin_plan = [f for f in activos if f['equipo'].criticidad == 'critico' and not f['planes']]
    series = series_por_mes(unidad, hoy)
    programados = sum(fila['programados'] for fila in series)
    completados = sum(fila['completados'] for fila in series)
    reparto = _reparto_vida_util(filas)
    bajas = [f for f in filas if f['semaforo'] == 'baja']
    areas = grupos_de_filas(unidad, activos)
    if areas:
        preparar_recursos_de_equipos([fila['equipo'] for fila in activos])
    for area in areas:
        area['intervencion'] = area['atencion'] = area['incidencias'] = 0
        for categoria in area['categorias']:
            modelos = OrderedDict()
            for fila in categoria['filas']:
                tipo = fila['equipo'].equipo
                modelos.setdefault(tipo.pk, dict(tipo=tipo, filas=[]))['filas'].append(fila)
            for modelo in modelos.values():
                modelo['total'] = len(modelo['filas'])
                modelo['intervencion'] = sum(f['semaforo'] == 'critico' for f in modelo['filas'])
                modelo['atencion'] = sum(f['semaforo'] == 'atencion' for f in modelo['filas'])
                modelo['incidencias'] = sum(f['incidencias_abiertas'] for f in modelo['filas'])
                modelo['vinculos'] = vinculos_del_modelo(unidad, [f['equipo'] for f in modelo['filas']])
            categoria['modelos'] = list(modelos.values())
            categoria['intervencion'] = sum(f['semaforo'] == 'critico' for f in categoria['filas'])
            categoria['atencion'] = sum(f['semaforo'] == 'atencion' for f in categoria['filas'])
            categoria['incidencias'] = sum(f['incidencias_abiertas'] for f in categoria['filas'])
            for clave in ('intervencion', 'atencion', 'incidencias'):
                area[clave] += categoria[clave]
    return {
        'hoy': hoy,
        'filas': filas,
        'areas': areas,
        # Sin equipos no hay nada que mantener: se dice, en vez de dibujar
        # ceros y barras vacías que parecen un incumplimiento.
        'sin_equipos': not filas,
        'agenda': agenda_de_mantenimiento(unidad, hoy),
        'bajas': bajas,
        'series': series,
        'maximo_serie': max([max(f['programados'], f['completados']) for f in series] + [1]),
        'vida_util': [
            ('Vigente', reparto['vigente'], 'al_dia'),
            ('Por renovar', reparto['por_renovar'], 'atencion'),
            ('Vida útil cumplida', reparto['cumplida'], 'critico'),
            ('Sin vida útil definida', reparto['sin_definir'], 'neutro'),
        ],
        'semaforo': [
            ('Requieren intervención', sum(1 for f in activos if f['semaforo'] == 'critico'), 'critico'),
            ('Requieren atención', sum(1 for f in activos if f['semaforo'] == 'atencion'), 'atencion'),
            ('Al día', sum(1 for f in activos if f['semaforo'] == 'al_dia'), 'al_dia'),
        ],
        'cifras': {
            'equipos': len(activos),
            'con_plan': len(con_plan),
            'cobertura': round(100 * len(con_plan) / len(activos)) if activos else 0,
            'criticos_sin_plan': len(criticos_sin_plan),
            'vencidos': sum(1 for f in activos if any(p.proxima_ejecucion < hoy for p in f['planes'])),
            'por_vencer': sum(1 for f in activos if f['dias_para_proximo'] is not None
                              and 0 <= f['dias_para_proximo'] <= 30),
            'incidencias': sum(f['incidencias_abiertas'] for f in activos),
            'fuera_de_servicio': sum(1 for f in activos if not f['equipo'].es_publico),
            'programados': programados,
            'completados': completados,
            'cumplimiento': round(100 * completados / programados) if programados else None,
            'costo': _costo_acumulado_unidad(unidad, hoy),
            'bajas': len(bajas),
        },
    }


def historial_equipo(equipo, limite=40):
    """El ciclo de vida del activo: registro, cambios, incidencias, órdenes y baja."""
    return list(
        EventoCicloVidaEquipo.objects.filter(equipo=equipo)
        .select_related('usuario', 'incidencia', 'mantenimiento')
        .order_by('-fecha')[:limite]
    )
