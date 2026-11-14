"""El reporte de mantenimiento: lo que hay que sustentar ante la auditoría.

Es el documento «Plan anual de mantenimiento preventivo y correctivo» del
expediente. Va equipo por equipo con su criticidad, su plan y frecuencia, lo
ejecutado frente a lo programado, los repuestos y el costo, la vida útil y, al
final, las bajas del período con su motivo y su reemplazo.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, RepuestoMantenimiento
from apps.recursos.models.equipos import PiezaEquipo
from apps.documentos.models.respaldo_medicion import corte_efectivo, es_laboratorio

from apps.recursos.presentation.mantenimiento_panel import SEMAFOROS, filas_de_equipos
from apps.recursos.presentation.areas_recursos import grupos_de_filas
from apps.recursos.presentation.ficha_equipo import registros_baja_y_sustitucion, resumen_baja_y_sustitucion

# Cuántas ejecuciones del plan se proyectan en la columna del cronograma.
PROXIMAS_PROYECTADAS = 2

# La columna «Estado» ya dice de qué habla: la etiqueta larga del semáforo se
# parte en tres líneas y no aporta nada frente a la palabra.
ESTADOS_CORTOS = {
    'critico': 'Intervención', 'atencion': 'Atención', 'al_dia': 'Al día', 'baja': 'De baja',
}


def _texto(usuario):
    if not usuario:
        return '—'
    return usuario.get_full_name() or usuario.get_username()


def _cronograma(planes, hoy):
    """Las próximas ejecuciones que proyecta cada plan con su frecuencia.

    La auditoría no pregunta solo cuándo toca la siguiente: pide el
    cronograma del período, y eso se deduce de la frecuencia declarada.
    """
    fechas = []
    for plan in planes:
        fecha = plan.proxima_ejecucion
        for _ in range(PROXIMAS_PROYECTADAS):
            fechas.append(fecha)
            fecha = fecha + timedelta(days=plan.frecuencia_dias)
    return '; '.join(f'{fecha:%d/%m/%Y}' for fecha in sorted(fechas)[:PROXIMAS_PROYECTADAS]) or '—'


def _garantia(equipo, hoy):
    fin = equipo.fin_garantia
    if not fin:
        return 'No registrada'
    if fin >= hoy:
        return f'Vigente hasta {fin:%d/%m/%Y}'
    return f'Vencida el {fin:%d/%m/%Y}'


def _piezas_criticas_sin_repuesto(filas):
    """Las piezas que paran el equipo y de las que la unidad no guarda repuesto."""
    tipos = {fila['equipo'].equipo_id for fila in filas}
    faltantes = {}
    for pieza in PiezaEquipo.objects.filter(
            equipo__in=tipos, critica=True, repuesto_disponible=False).select_related('equipo'):
        faltantes.setdefault(pieza.equipo_id, []).append(pieza.nombre)
    return faltantes


def _dias_de_intervencion(completadas, desde, hasta):
    """Duración real dentro del período, sin duplicar intervalos superpuestos."""
    zona = timezone.get_current_timezone()
    limite_inferior = timezone.make_aware(datetime.combine(desde, time.min), zona)
    limite_superior = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), zona)
    intervalos = {}
    for equipo_id, inicio, fin in completadas.values_list('equipo_id', 'fecha_inicio', 'fecha_fin').iterator():
        if inicio and fin and fin > inicio:
            inicio, fin = max(inicio, limite_inferior), min(fin, limite_superior)
            if fin > inicio:
                intervalos.setdefault(equipo_id, []).append((inicio, fin))
    dias = {}
    for equipo_id, propios in intervalos.items():
        unidos = []
        for inicio, fin in sorted(propios):
            if unidos and inicio <= unidos[-1][1]:
                unidos[-1] = (unidos[-1][0], max(unidos[-1][1], fin))
            else:
                unidos.append((inicio, fin))
        dias[equipo_id] = sum((fin - inicio).total_seconds() for inicio, fin in unidos) / 86400
    return dias


def reporte_mantenimiento(unit, start_date, end_date, state='', search=''):
    """(headers, rows, cards, state_choices) del seguimiento de mantenimiento."""
    hoy = timezone.localdate()
    corte = corte_efectivo(unit, end_date)
    filas = filas_de_equipos(unit, hoy)
    if search:
        aguja = search.lower()
        filas = [
            fila for fila in filas
            if aguja in fila['equipo'].codigo_unidad.lower()
            or aguja in (fila['equipo'].equipo.nombre or '').lower()
            or any(aguja in plan.nombre.lower() for plan in fila['planes'])
        ]
    if state in dict(SEMAFOROS_ESTADO):
        filas = [fila for fila in filas if fila['semaforo'] == state]
    grupos = grupos_de_filas(unit, filas)
    categorias = {fila['equipo'].pk: categoria['nombre']
                  for area in grupos for categoria in area['categorias'] for fila in categoria['filas']}
    filas = [fila for area in grupos for categoria in area['categorias'] for fila in categoria['filas']]

    claves = [fila['equipo'].pk for fila in filas]
    # La partida explícita conserva su unidad aunque el activo cambie. Sin
    # unidad capturada sólo se usa la adscripción primaria actual: la relación
    # múltiple no puede imputar el mismo gasto legado a varias unidades.
    alcance = Q(unidad=unit) | Q(unidad__isnull=True, equipo_id__in=claves)
    alcance_financiero = Q(unidad=unit) | Q(unidad__isnull=True, equipo__laboratorio=unit)
    ordenes = MantenimientoEquipo.objects.filter(
        alcance_financiero,
        fecha_programada__date__range=(start_date, end_date),
    ).distinct()
    if search or state in dict(SEMAFOROS_ESTADO):
        ordenes = ordenes.filter(equipo_id__in=claves)
    hecha_al_corte = Q(estado='completado', fecha_fin__date__lte=corte)
    completadas = ordenes.filter(hecha_al_corte)
    repuestos = RepuestoMantenimiento.objects.filter(mantenimiento__in=ordenes)
    incidencias = IncidenciaEquipo.objects.filter(
        alcance,
        fecha_reporte__date__range=(start_date, end_date),
    ).distinct()
    if search or state in dict(SEMAFOROS_ESTADO):
        incidencias = incidencias.filter(equipo_id__in=claves)

    # El panel operativo conserva el historial completo. El informe exportado
    # debe usar el mismo período en sus filas y sus totales.
    resumen_ordenes = {item['equipo_id']: item for item in ordenes.order_by().values('equipo_id').annotate(
        total=Count('pk'), hechos=Count('pk', filter=hecha_al_corte),
        costo=Sum('costo', filter=hecha_al_corte),
    )}
    # El costo es por cantidad de cada repuesto, no el producto de las sumas.
    resumen_repuestos = {}
    for equipo_id, cantidad, costo_unitario in repuestos.filter(
            mantenimiento__in=completadas).values_list(
                'mantenimiento__equipo_id', 'cantidad', 'costo_unitario').iterator():
        resumen_repuestos[equipo_id] = resumen_repuestos.get(equipo_id, Decimal(0)) + cantidad * costo_unitario
    resumen_incidencias = {item['equipo_id']: item['total'] for item in incidencias.exclude(
        estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).order_by().values('equipo_id').annotate(total=Count('pk'))}
    dias_periodo = _dias_de_intervencion(completadas, start_date, corte)

    sin_repuesto = _piezas_criticas_sin_repuesto(filas)
    # Encabezados cortos: dieciseis columnas no caben si cada titulo trae una
    # frase, y una palabra partida en tres lineas no se lee.
    headers = [
        'Equipo', 'Criticidad', 'Estado', 'Plan y frecuencia', 'Ejecuta',
        'Cronograma', 'Último', 'Próximo', 'Hechos',
        'Incidencias', 'Días fuera', 'Vida útil', 'Garantía',
        'Piezas sin repuesto', 'Costo USD', 'Situación',
    ]
    rows = []
    retiros = registros_baja_y_sustitucion(fila['equipo'] for fila in filas)
    for fila in filas:
        equipo = fila['equipo']
        retiro = retiros[equipo.pk]
        situacion = resumen_baja_y_sustitucion(retiro)
        if not retiro['fecha']:
            situacion = ' '.join((*fila['motivos'], situacion)).strip()
        periodo = resumen_ordenes.get(equipo.pk, {})
        planes = '; '.join(
            f'{plan.nombre} · {plan.get_tipo_display()} · cada {plan.frecuencia_dias} días'
            f' · {_texto(plan.responsable) if plan.responsable_id else (plan.proveedor or "sin responsable")}'
            for plan in fila['planes']
        ) or 'Sin plan registrado'
        ejecutores = '; '.join(dict.fromkeys(
            plan.get_ejecutor_display() for plan in fila['planes'])) or '—'
        vida = '—' if fila['vida_util'] is None else f"{fila['vida_util']} %"
        if fila['fin_vida_util']:
            vida += f" · hasta {fila['fin_vida_util']:%m/%Y}"
        rows.append([
            f"{equipo.codigo_unidad} · {equipo.equipo.nombre}\n"
            f"{fila['area_nombre']} · {categorias[equipo.pk]}",
            fila['criticidad_corta'],
            ESTADOS_CORTOS.get(fila['semaforo'], fila['etiqueta']),
            planes,
            ejecutores,
            _cronograma(fila['planes'], hoy),
            f"{fila['ultimo']:%d/%m/%Y}" if fila['ultimo'] else 'Sin registro',
            f"{fila['proximo']:%d/%m/%Y}" if fila['proximo'] else '—',
            f"{periodo.get('hechos', 0)}/{periodo.get('total', 0)}",
            resumen_incidencias.get(equipo.pk, 0),
            f"{dias_periodo.get(equipo.pk, 0):.2f}",
            vida,
            _garantia(equipo, hoy),
            ', '.join(sin_repuesto.get(equipo.equipo_id, [])) or '—',
            f"{(periodo.get('costo') or Decimal(0)) + resumen_repuestos.get(equipo.pk, Decimal(0)):.2f}",
            situacion,
        ])
    costo_servicio = completadas.aggregate(total=Sum('costo'))['total'] or Decimal(0)
    costo_repuestos = sum(resumen_repuestos.values(), Decimal(0))
    costo = costo_servicio + costo_repuestos
    programadas = ordenes.count()
    externas = completadas.exclude(ejecutor='interno').count()
    activos = [fila for fila in filas if fila['semaforo'] != 'baja']
    con_plan = [fila for fila in activos if fila['planes']]
    criticos_sin_plan = [
        fila for fila in activos
        if fila['equipo'].criticidad == 'critico' and not fila['planes']
    ]
    en_garantia = [fila for fila in activos if fila['en_garantia']]
    cards = [
        ('Equipos con seguimiento', len(filas), f'{len(activos)} activos vigentes'),
        ('Cobertura del plan', f'{round(100 * len(con_plan) / len(activos)) if activos else 0} %',
         f'{len(con_plan)} de {len(activos)} con plan vigente'
         + (f' · {len(criticos_sin_plan)} críticos sin plan' if criticos_sin_plan else '')),
        ('Órdenes del período', programadas, f'{completadas.count()} completadas'),
        ('Ejecución operativa de órdenes' if es_laboratorio(unit) else 'Cumplimiento',
         f'{round(100 * completadas.count() / programadas)} %' if programadas else 'Sin programación',
         'órdenes completadas al corte sobre programadas; no equivale a ejecución respaldada del plan crítico'
         if es_laboratorio(unit) else 'ejecutado sobre programado; sin órdenes no se presume cumplimiento'),
        ('Ejecutadas por terceros', externas, 'técnico externo o garantía'),
        ('Incidencias del período', incidencias.count(),
         f"{incidencias.exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).count()} abiertas"),
        ('Equipos en garantía', len(en_garantia), 'el proveedor responde por ellos'),
        ('Repuestos utilizados', repuestos.filter(mantenimiento__in=completadas).count(),
         'registros de órdenes completadas'),
        ('Completadas sin informe', completadas.filter(Q(informe='') | Q(informe__isnull=True)).count(),
         'falta el archivo de respaldo de la ejecución'),
        ('Órdenes sin responsable', ordenes.filter(responsable__isnull=True).count(),
         'asignación pendiente'),
        ('Costo del período (USD)', f'{costo:.2f}',
         f'{costo_servicio:.2f} de servicio · {costo_repuestos:.2f} de repuestos'),
    ]
    if es_laboratorio(unit):
        from apps.documentos.presentation.medicion_metas import medir_mantenimiento_integral
        integral = medir_mantenimiento_integral(unit, start_date, end_date)
        critica = integral['equipos']
        infra = integral['infraestructura']
        cards.extend([
            ('Universo anual de equipos críticos', critica['equipos_criticos'],
             f'{critica["equipos_sin_plan"]} sin plan · {critica["equipos_sin_programacion"]} sin órdenes anuales'),
            ('Ejecución crítica de equipos al corte', f'{critica["numerador"]}/{critica["denominador"]}',
             'Sin equipos críticos: revisión respaldada' if critica['no_aplica_verificado'] else
             critica['motivo'] or 'sólo intervenciones exigibles con informe, resultado y responsable'),
            ('Ejecución crítica de infraestructura', f'{infra["numerador"]}/{infra["denominador"]}',
             'Sin intervenciones críticas: alcance respaldado' if infra['no_aplica_verificado'] else
             infra['motivo'] or 'sólo intervenciones exigibles con plan e informe verificados'),
            ('Meta crítica integral (80 %)', 'No aplica: alcance verificado' if integral['no_aplica_verificado'] else
             f'{integral["numerador"]}/{integral["denominador"]}',
             integral['motivo'] or f'{integral["programadas_futuras"]} intervenciones futuras dentro de plazo'),
        ])
    return headers, rows, cards, SEMAFOROS_ESTADO


SEMAFOROS_ESTADO = tuple((clave, etiqueta) for clave, (etiqueta, _tono) in SEMAFOROS.items())
