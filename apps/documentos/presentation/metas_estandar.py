"""Metas centrales y carga de sesiones concretas, conservadas con cada plan.

El catálogo de asignaturas y el número de semanas no son compromisos de uso.
Los horarios de la agenda y las planificaciones vigentes aportan las sesiones y sus horas.
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal


def _horas(segundos):
    return f'{(Decimal(segundos) / 3600).quantize(Decimal("0.01")).normalize():f}'


def _ocupacion(intervalos):
    """Horas de unidad: las sesiones simultáneas ocupan un mismo intervalo una vez."""
    total, final = 0, None
    for inicio, fin in sorted(intervalos):
        total += max(0, fin - max(inicio, final if final is not None else inicio))
        final = max(fin, final if final is not None else fin)
    return total


def carga_docente(unidad, inicio, fin, calendario, referencias):
    from django.db.models import Exists, OuterRef, Q, Subquery
    from apps.formacion.models.asignaturas import Asignatura
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.reservas.models.reservas import Reserva

    # Una reserva con planificación cuenta por la planificación vigente, nunca por ambas. Los
    # horarios únicos y recurrentes ya están materializados por la agenda.
    vigentes = PlanificacionPractica.objects.filter(unidad=unidad,
        eliminado_en__isnull=True, es_version_vigente=True).exclude(estado='archivada')
    anteriores = PlanificacionPractica.objects.filter(unidad=unidad,
        grupo_version=OuterRef('grupo_version'), reserva__laboratorio=unidad).order_by('-numero_version')
    planes = vigentes.filter(fecha__range=(inicio, fin), categoria_uso__in=('docencia', 'posgrado')).annotate(
        _reserva_serie=Subquery(anteriores.values('reserva_id')[:1])).exclude(
        reserva__estado__in=('cancelada', 'rechazada', 'vencida')).filter(
        Q(reserva__isnull=True) | Q(reserva__laboratorio=unidad)).select_related(
            'tema_asignatura__asignatura', 'reserva__programacion__asignatura')
    familia_vigente = PlanificacionPractica.objects.filter(unidad=unidad, reserva_id=OuterRef('pk')).annotate(
        _vigente=Exists(vigentes.filter(grupo_version=OuterRef('grupo_version')))).filter(_vigente=True)
    reservas = Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin)).filter(
        Q(proposito_codigo='docencia_practica') | Q(programacion__asignatura__unidad=unidad)
    ).exclude(estado__in=('cancelada', 'rechazada', 'vencida')).annotate(
        _tiene_plan=Exists(familia_vigente)
    ).filter(_tiene_plan=False).select_related('programacion__asignatura')
    sesiones, pendientes, asignaturas, temas = [], [], {}, set()
    guias_por_practica = defaultdict(set)
    intervalos, por_mes = defaultdict(list), defaultdict(int)
    avisos = []

    def agregar(plan=None, reserva=None):
        registro = plan or reserva
        if registro.hora_fin <= registro.hora_inicio:
            avisos.append('Hay sesiones con horario inválido; completa su programación para confirmar la carga.')
            return
        programa = reserva.programacion if reserva and reserva.programacion_id else None
        tema = plan.tema_asignatura if plan and plan.tema_asignatura_id else None
        asignatura = (tema.asignatura if tema and tema.asignatura.unidad_id == unidad.pk else
            programa.asignatura if programa and programa.asignatura_id
                and programa.asignatura.unidad_id == unidad.pk else None)
        nombre = asignatura.nombre if asignatura else (
            plan.asignatura if plan else reserva.referencia_actividad or reserva.titulo_solicitud or 'Por vincular')
        segundos = int((datetime.combine(registro.fecha, registro.hora_fin)
                        - datetime.combine(registro.fecha, registro.hora_inicio)).total_seconds())
        if not asignatura:
            # El texto libre puede ser una solicitud, una demostración o una
            # actividad no curricular. Se conserva visible para revisión; no
            # convierte automáticamente el uso general en una cuota docente.
            pendientes.append(dict(origen='FT02' if plan else 'agenda', id=registro.pk,
                nombre=nombre, fecha=registro.fecha.isoformat(), segundos=segundos))
            return
        clave = f'id:{asignatura.pk}'
        curso = asignaturas.setdefault(clave, dict(id=asignatura.pk if asignatura else None,
            codigo=asignatura.codigo if asignatura else '', nombre=nombre, sesiones=0, segundos=0,
            desde=registro.fecha.isoformat(), hasta=registro.fecha.isoformat()))
        curso['sesiones'] += 1
        curso['segundos'] += segundos
        curso['desde'] = min(curso['desde'], registro.fecha.isoformat())
        curso['hasta'] = max(curso['hasta'], registro.fecha.isoformat())
        if plan and plan.requiere_guia:
            # Una guía puede respaldar varias sesiones de la misma práctica.
            practica = f'tema:{tema.pk}' if tema else f'practica:{clave}:{plan.tema.strip().casefold()}'
            guias_por_practica[practica].update([plan.guia_id] if plan.guia_id else [])
        if tema:
            temas.add(tema.pk)
        minuto = registro.hora_inicio.hour * 3600 + registro.hora_inicio.minute * 60 + registro.hora_inicio.second
        intervalos[registro.fecha].append((minuto, minuto + segundos))
        sesiones.append(dict(origen='FT02' if plan else 'agenda', id=registro.pk,
            reserva=reserva.pk if reserva else None, programacion=programa.pk if programa else None,
            fecha=registro.fecha.isoformat(), inicio=registro.hora_inicio.isoformat(),
            fin=registro.hora_fin.isoformat(), segundos=segundos, asignatura=clave,
            tema=tema.pk if tema else None, guia=plan.guia_id if plan else None,
            estado=registro.estado, version=plan.numero_version if plan else None))

    planes = list(planes.order_by('fecha', 'hora_inicio', 'pk'))
    reservas_anteriores = {r.pk: r for r in Reserva.objects.filter(laboratorio=unidad,
        pk__in={p._reserva_serie for p in planes if not p.reserva_id and p._reserva_serie}
    ).select_related('programacion__asignatura')}
    for plan in planes:
        reserva = plan.reserva if plan.reserva_id else reservas_anteriores.get(plan._reserva_serie)
        if reserva and (reserva.estado in ('cancelada', 'rechazada', 'vencida')
                        or reserva.programacion_id and reserva.programacion.estado == 'cancelada'):
            continue
        agregar(plan, reserva)
    for reserva in reservas.order_by('fecha', 'hora_inicio', 'pk'):
        if reserva.programacion_id and reserva.programacion.estado == 'cancelada':
            continue
        agregar(reserva=reserva)
    for fecha, tramos in intervalos.items():
        por_mes[str(fecha.month)] += _ocupacion(tramos)
    for curso in asignaturas.values():
        curso['horas'] = _horas(curso.pop('segundos'))
    if not sesiones:
        avisos.append('Falta programar la ocupación del semestre: registra las sesiones y sus horarios en la agenda '
                      'o en la planificación de la práctica. '
                      'La referencia mínima no sustituye esa programación.')
    if pendientes:
        avisos.append(f'{len(pendientes)} sesiones están pendientes de vincular a una asignatura del semestre. '
            'Se conservan en la agenda y sus reportes; revisa su relación académica antes de incorporarlas a la meta docente.')
    if not calendario.get('calendario_disponible'):
        avisos.append('Falta el calendario docente para contrastar las fechas de las sesiones.')
    guias = set().union(*guias_por_practica.values()) if guias_por_practica else set()
    guias_necesarias = len(guias) + sum(not ids for ids in guias_por_practica.values())
    return dict(aplica=True, sesiones=sesiones, sesiones_programadas=len(sesiones),
        asignaturas=list(asignaturas.values()), asignaturas_total=len(asignaturas),
        asignaturas_catalogo_total=Asignatura.objects.filter(unidad=unidad, activa=True).count(),
        sesiones_sin_vinculo=pendientes, horas_sin_vinculo=_horas(sum(s['segundos'] for s in pendientes)),
        temas=len(temas), guias=guias_necesarias, practicas=len(sesiones),
        horas_sesiones=_horas(sum(s['segundos'] for s in sesiones)),
        horas_requeridas=_horas(sum(por_mes.values())),
        horas_por_mes={m: _horas(s) for m, s in sorted(por_mes.items(), key=lambda par: int(par[0]))},
        avisos=list(dict.fromkeys(avisos)),
        formula=f'{len(sesiones)} sesiones concretas vinculadas a asignaturas en la agenda y las planificaciones '
                'vigentes del tramo; '
                'cada sesión cuenta una vez, con su fecha y duración reales. '
                'El catálogo de asignaturas y las semanas no multiplican la meta.')


def calcular_metas(unidad, inicio, fin, actividades, capacidad, calendario):
    from .metas_plan import regla_minimo
    actividades = list(actividades)
    referencias = [r for r in capacidad.get('referencias_indicadores') or []
                   if r['codigo'] not in ('PRACTICAS-SEMANA', 'PRACTICAS-MINUTOS')]
    docente = any(a.codigo in ('PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS') for a in actividades)
    carga = (carga_docente(unidad, inicio, fin, calendario, referencias) if docente else
        dict(aplica=False, asignaturas=[], asignaturas_total=0, temas=0, practicas=0, guias=0,
            sesiones=[], sesiones_programadas=0, horas_sesiones='0', horas_requeridas='0', horas_por_mes={},
            avisos=[], formula='Esta tipología utiliza sus indicadores propios.'))
    pisos = [int(regla_minimo(a)['valor']) for a in actividades
             if a.codigo in ('PRACTICAS', 'PRACTICAS-PLAN') and regla_minimo(a)]
    carga['piso_central'] = max(pisos, default=0)
    carga['practicas'] = max([carga['practicas'], *pisos])
    if docente:
        carga['formula'] += (f' Meta: el mayor valor entre las sesiones programadas y la referencia mínima '
            f'de Dirección ({carga["piso_central"]} por unidad y período). '
            'Es una referencia interna, no una cuota por asignatura o por semana.')
        if carga['sesiones_sin_vinculo']:
            carga['formula'] += (f' Hay {len(carga["sesiones_sin_vinculo"])} sesiones pendientes de vinculación académica; '
                'no se convierten automáticamente en una cuota docente.')
        if 0 < carga['sesiones_programadas'] < carga['piso_central']:
            carga['avisos'].append('La programación todavía no cubre la referencia mínima. Completa las sesiones '
                'o presenta la limitación a Dirección; no se inventan fechas ni horas para cubrirla.')
    from apps.recursos.presentation.utilizacion import calculate_unit_utilization
    medida = (calculate_unit_utilization(unidad, inicio, fin, hoy=fin) if docente else
              dict(available_hours_period=0, daily=[]))
    carga['horas_disponibles'] = str(medida['available_hours_period'])
    jornadas = medida['daily']
    carga['capacidad_confirmada'] = bool(jornadas) and all(d['jornada_conocida'] for d in jornadas) and all(
        d['capacidad_conocida'] and d['capacidad_respaldada'] for d in jornadas if d['disponible_segundos'])
    if docente and not carga['capacidad_confirmada']:
        carga['avisos'].append('La jornada y la capacidad operativa requieren confirmación; las metas no se reducen automáticamente.')
    if Decimal(carga['horas_requeridas']) > Decimal(str(carga['horas_disponibles'])):
        carga['avisos'].append('Las horas programadas superan la disponibilidad: Dirección debe revisar recursos y horarios.')
    metas, origenes = {}, {}
    for actividad in actividades:
        regla = regla_minimo(actividad)
        if not regla:
            metas[actividad.codigo] = actividad.minimo
            origenes[actividad.codigo] = 'Según programación de esta función; no se inventa una cuota de demanda.'
            continue
        valor = regla['valor']
        if actividad.codigo in ('PRACTICAS', 'PRACTICAS-PLAN'):
            valor = max(valor, Decimal(carga['practicas']))
            origenes[actividad.codigo] = carga['formula']
        elif actividad.codigo == 'GUIAS':
            valor = max(valor, Decimal(carga['guias']))
            origenes[actividad.codigo] = (f'{carga["guias"]} guías o prácticas distintas que requieren guía en las '
                f'planificaciones programadas; mínimo central {regla["valor"]}. Una misma guía puede utilizarse en varias sesiones. '
                'Los temas sin programación en el catálogo no aumentan la meta.')
        else:
            origenes[actividad.codigo] = ('Cobertura de los registros exigibles del indicador.' if regla['porcentaje'] else
                'Referencia central por tipo de unidad, conservada al guardar el plan.')
        metas[actividad.codigo] = f'{valor.normalize():f}' + (' %' if regla['porcentaje'] else '')
    return dict(version=2, inicio=inicio.isoformat(), fin=fin.isoformat(), metas=metas,
        origenes=origenes, referencias=referencias, carga_docente=carga,
        descripcion='Sesiones y horas según la programación real del semestre; referencias mínimas administradas por Dirección. '
            'La unidad programa fechas y horarios, sin editar directamente las metas calculadas.')


def aplicar_metas(plan, politica):
    from copy import deepcopy
    plan = deepcopy(plan)
    for codigo, fila in (plan.get('catalogo') or {}).items():
        if codigo in politica['metas']:
            fila['meta'] = politica['metas'][codigo]
    plan['metas_estandar'] = politica
    return plan
