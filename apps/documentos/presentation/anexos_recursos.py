"""Anexos de uso, mantenimiento, inventario y fichas técnicas.

Tablas y columnas: docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.1 a 4.4. Cada
función recibe un :class:`~apps.documentos.presentation.anexos_evidencia.Contexto` y devuelve
la lista de :class:`~apps.documentos.presentation.anexos_evidencia.Registro` del anexo, en el
orden de la especificación. El motor numera las tablas («1.1», «1.2»…) y dibuja el PDF.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from .anexos_evidencia import (
    Grupo, Registro, cifra, enlace, enlace_archivo, enlace_recurso, evidencias_de_gestion, fecha, nombre_de, par,
    plural, si_no, texto, verificacion,
)

# Cómo se escribe en una celda lo que el modelo guarda con una frase larga.
CRITICIDADES = {'critico': 'Crítico', 'importante': 'Importante', 'normal': 'Normal'}
EJECUTORES = {'interno': 'Interno', 'externo': 'Externo', 'garantia': 'Garantía'}
RESULTADOS_OPERATIVOS = {'pendiente': 'Por verificar', 'apto': 'Apto', 'parcial': 'Parcial', 'no_apto': 'No apto'}
RESULTADOS_FUNCIONALES = {'operativo': 'Operativo', 'observado': 'Con observaciones',
                          'no_operativo': 'No operativo'}
ORIGENES_DE_ADQUISICION = {
    'asignacion_institucional': 'Asignación institucional', 'compra_publica': 'Compra pública',
    'proyecto': 'Proyecto', 'donacion': 'Donación', 'transferencia': 'Transferencia',
    'prestamo': 'Préstamo o comodato', 'otro': 'Otro origen',
}
ORIGENES_DE_ABASTECIMIENTO = {
    'compra_publica': 'Compra pública', 'recursos_autogestion': 'Autogestión', 'proyecto': 'Proyecto',
    'donacion': 'Donación', 'transferencia': 'Transferencia', 'otro': 'Otro origen',
}
TIPOS_DE_SOFTWARE = {'software': 'Software', 'licencia': 'Licencia', 'simulador': 'Simulador'}
ACCESOS_A_SOFTWARE = {'instalacion': 'Instalado', 'licencia': 'Licencia individual', 'red': 'Red',
                      'remoto': 'Remoto'}
USOS_EN_EQUIPO = {'opcional': 'Opcional', 'obligatorio': 'Obligatorio'}
# Los estados de un equipo que la tabla de estado presenta siempre; los demás, solo si hay equipos en ellos.
ESTADOS_DE_EQUIPO = ('disponible', 'en_uso', 'mantenimiento', 'dañado', 'prestado', 'no_disponible', 'no_localizado')
# Clasificaciones del inventario que van en la tabla de reactivos; las demás son insumos y materiales.
CLASES_DE_REACTIVO = ('reactivo', 'agroquimico', 'veterinario')
DIAS_PARA_VENCER = 90
DIAS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


def _hora(valor):
    return f'{valor:%H:%M}' if valor else '—'


def _horario_real(reserva):
    """El horario real registrado al cerrar la atención, o '' si no se registró."""
    ejecucion = reserva.detalle_ejecucion if isinstance(reserva.detalle_ejecucion, dict) else {}
    real = ejecucion.get('horario_real') if isinstance(ejecucion.get('horario_real'), dict) else {}
    inicio, fin = str(real.get('inicio') or '')[:5], str(real.get('fin') or '')[:5]
    return f'real {inicio}–{fin}' if inicio and fin else ''


def _recursos_de(reserva):
    """Espacios, equipo y software de la sesión, por su código o nombre."""
    partes = [e.codigo or e.nombre for e in reserva.espacios_solicitados.all()]
    if reserva.equipo_codigo or reserva.equipo_nombre:
        partes.append(reserva.equipo_codigo or reserva.equipo_nombre)
    partes += [s.codigo or s.nombre for s in reserva.software_solicitado.all()]
    return texto(', '.join(dict.fromkeys(p for p in partes if p)), 90)


def _actividad_de(reserva, base):
    """La asignatura si la sesión es una práctica planificada; si no, la actividad."""
    plan = getattr(reserva, 'planificacion_practica', None)
    actividad = (plan.asignatura if plan and plan.asignatura else '') or (
        reserva.actividad_catalogo.nombre if reserva.actividad_catalogo_id else '') or reserva.resumen_solicitud
    proceso = ''
    if base == 'plantas_piloto':
        proceso = str(reserva.producto_solicitado or reserva.receta or '') if (
            reserva.producto_solicitado_id or reserva.receta_id) else ''
    return par(texto(actividad, 80), texto(proceso, 60) if proceso else '')


def _solicitante_de(reserva):
    nombre = nombre_de(reserva.usuario) if reserva.usuario_id else texto(reserva.nombre_solicitante)
    perfil = ' · '.join(p for p in (
        reserva.get_tipo_usuario_solicitante_display() if reserva.tipo_usuario_solicitante else '',
        reserva.get_carrera_solicitante_display() if reserva.carrera_solicitante else '',
        reserva.get_nivel_academico_solicitante_display() if reserva.nivel_academico_solicitante else '',
    ) if p)
    return par(texto(nombre, 50), texto(perfil, 80) if perfil else '')


def uso(contexto):
    """Anexo de registros de uso (sección 4.1): sesiones, totales por propósito y por mes, y visitas."""
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas, participantes
    from apps.reservas.models.reservas import Reserva
    from apps.reservas.models.visitas import SolicitudVisita
    from .anexos_evidencia import mes
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    todas = Reserva.objects.filter(laboratorio=contexto.unidad, fecha__range=(contexto.inicio, contexto.fin))
    descartadas = todas.filter(estado__in=ESTADOS_RESERVA_DESCARTADOS).count()
    reservas = list(todas.exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS)
                    .select_related('usuario', 'actividad_catalogo', 'planificacion_practica', 'receta',
                                    'producto_solicitado')
                    .prefetch_related('espacios_solicitados', 'software_solicitado')
                    .order_by('fecha', 'hora_inicio', 'pk'))
    sesiones = []
    por_proposito = defaultdict(lambda: [0, 0, 0.0, 0])  # registradas, atendidas, horas, participantes
    por_mes = defaultdict(lambda: [0, 0, 0.0, 0])
    for reserva in reservas:
        proposito = reserva.get_proposito_codigo_display() or 'Sin propósito'
        atendida = reserva.es_efectiva
        horas = horas_efectivas(reserva) if atendida else 0.0
        asistieron = (participantes(reserva) or 0) if atendida else 0
        for grupo in (por_proposito[proposito], por_mes[f'{reserva.fecha:%Y-%m}']):
            grupo[0] += 1
            grupo[1] += atendida
            grupo[2] += horas
            grupo[3] += asistieron
        previsto = f'previsto {_hora(reserva.hora_inicio)}–{_hora(reserva.hora_fin)}'
        cierre = reserva.get_resultado_cierre_display() if reserva.resultado_cierre else ''
        sesiones.append([
            texto(reserva.codigo_reserva),
            par(fecha(reserva.fecha), ' · '.join(p for p in (previsto, _horario_real(reserva)) if p)),
            _recursos_de(reserva),
            texto(proposito),
            _actividad_de(reserva, contexto.base),
            _solicitante_de(reserva),
            par(cifra(reserva.numero_participantes), f'asistieron {cifra(asistieron)}' if atendida else ''),
            par(reserva.get_estado_display(), cierre),
            cifra(round(horas, 2)) if atendida else '—',
        ])
    atendidas = sum(v[1] for v in por_proposito.values())
    horas_totales = round(sum(v[2] for v in por_proposito.values()), 1)
    asistentes = sum(v[3] for v in por_proposito.values())
    pie = (f'Total: {plural(len(sesiones), "sesión", "sesiones")} · atendidas: {cifra(atendidas)} · '
           f'horas efectivas: {cifra(horas_totales)} · participantes: {cifra(asistentes)}')
    if descartadas:
        pie += f' · canceladas, rechazadas o vencidas, que no se listan: {cifra(descartadas)}'

    def resumen(grupos, clave, sin_cierre=True):
        filas = [[clave(k), cifra(v[0]), cifra(v[1]), *([cifra(v[0] - v[1])] if sin_cierre else []),
                  cifra(round(v[2], 1)), cifra(v[3])] for k, v in grupos]
        suma = ['Total', cifra(len(sesiones)), cifra(atendidas),
                *([cifra(len(sesiones) - atendidas)] if sin_cierre else []), cifra(horas_totales), cifra(asistentes)]
        return filas, (suma if filas else None)

    filas_proposito, suma_proposito = resumen(sorted(por_proposito.items(), key=lambda x: -x[1][0]), str)
    filas_mes, suma_mes = resumen(sorted(por_mes.items()), mes, sin_cierre=False)

    visitas = []
    for visita in (SolicitudVisita.objects.filter(unidad=contexto.unidad,
                                                  reserva__fecha__range=(contexto.inicio, contexto.fin))
                   .exclude(reserva__estado__in=ESTADOS_RESERVA_DESCARTADOS)
                   .select_related('reserva', 'responsable', 'guia').prefetch_related('recorrido')
                   .order_by('reserva__fecha', 'pk')):
        visitas.append([
            par(fecha(visita.reserva.fecha), texto(visita.reserva.codigo_reserva)),
            texto(visita.institucion, 70),
            par(visita.get_categoria_display(), visita.get_proposito_display()),
            par(cifra(visita.personas), texto(visita.rango_edades, 30) if visita.rango_edades else ''),
            texto(', '.join(e.codigo or e.nombre for e in visita.recorrido.all()), 80),
            par(nombre_de(visita.guia), f'guías necesarios: {cifra(visita.guias_necesarios)}'),
            nombre_de(visita.responsable),
        ])
    return [
        Registro('Sesiones del período',
                 ('Código', 'Fecha / horario', 'Espacio o recurso', 'Propósito', 'Actividad o asignatura',
                  'Solicitante / perfil', 'Participantes', 'Cierre', 'Horas efectivas'),
                 sesiones, pesos=(10, 14, 12, 10, 16, 15, 9, 9, 5), total=pie,
                 vacio='No hay sesiones registradas en el período.'),
        Registro('Sesiones por propósito',
                 ('Propósito', 'Registradas', 'Atendidas', 'Sin cierre', 'Horas efectivas', 'Participantes'),
                 filas_proposito, pesos=(40, 12, 12, 12, 12, 12), suma=suma_proposito,
                 vacio='No hay sesiones registradas en el período.'),
        Registro('Sesiones por mes',
                 ('Mes', 'Registradas', 'Atendidas', 'Horas efectivas', 'Participantes'),
                 filas_mes, pesos=(40, 15, 15, 15, 15), suma=suma_mes,
                 vacio='No hay sesiones registradas en el período.'),
        Registro('Visitas',
                 ('Fecha / sesión', 'Institución o grupo', 'Categoría / propósito', 'Personas / edades',
                  'Recorrido', 'Guía de la visita', 'Responsable'),
                 visitas, pesos=(12, 20, 14, 10, 18, 13, 13), vacio='No hubo visitas en el período.'),
    ]


# -- ayudas comunes de equipos, inventario y fichas ---------------------------------------

def _corto(nombres, valor):
    """El nombre corto de una opción del modelo; si no está previsto, el propio valor."""
    return nombres.get(valor) or str(valor or '—').replace('_', ' ').capitalize()


def _cantidad(valor, unidad=''):
    """Cantidad con su unidad de medida y sin ceros de relleno: «2,5 kg»."""
    if valor is None:
        return '—'
    numero = Decimal(str(valor)).normalize()
    decimales = max(0, min(3, -numero.as_tuple().exponent))
    return f'{cifra(numero, decimales)} {unidad or ""}'.strip()


def _dinero(valor):
    return '—' if valor is None else f'USD {cifra(valor, 2)}'


def _codigo_y_nombre(codigo, nombre, largo=70):
    """Celda «código / nombre»; sin código queda solo el nombre."""
    return par(texto(codigo), texto(nombre, largo)) if codigo else texto(nombre, largo)


def _equipo(equipo):
    return _codigo_y_nombre(equipo.codigo_unidad, equipo.equipo.nombre)


def _codigos(equipos):
    """Cuántos equipos y, debajo, sus códigos (los del anexo de inventario).

    Los códigos que solo cambian en el número final se juntan: «FAB-IMP-01-01 a 04».
    """
    grupos = defaultdict(list)
    for codigo in sorted(equipo.codigo_unidad for equipo in equipos):
        raiz, _guion, numero = codigo.rpartition('-')
        seriado = bool(raiz) and numero.isdigit()
        grupos[raiz if seriado else codigo].append(numero if seriado else None)
    partes = []
    for raiz, numeros in grupos.items():
        numeros = [n for n in numeros if n is not None]
        seguidos = len(numeros) > 2 and all(int(b) - int(a) == 1 for a, b in zip(numeros, numeros[1:]))
        if not numeros:
            partes.append(raiz)
        elif seguidos:
            partes.append(f'{raiz}-{numeros[0]} a {numeros[-1]}')
        else:
            partes.append(f'{raiz}-' + '/'.join(numeros))
    cuantos = sum(len(numeros) or 1 for numeros in grupos.values())
    return par(plural(cuantos, 'equipo', 'equipos'), texto(', '.join(partes))) if partes else '—'


def _respaldo(evidencia):
    """El archivo de la evidencia en el gestor documental o, si no lo tiene, su enlace; debajo, su verificación."""
    archivo = enlace_recurso(evidencia.recurso) if evidencia.recurso_id else enlace(evidencia.enlace)
    return par(archivo, verificacion(evidencia))


def _equipos_activos(unidad, corte):
    """Los equipos del alcance de la unidad activos al corte, por código.

    Un equipo dado de baja después del corte todavía estaba en el inventario de ese corte.
    """
    from django.db.models import Q
    from apps.documentos.models.funcionalidad import equipos_del_alcance
    return (equipos_del_alcance(unidad)
            .filter(Q(activa=True, fecha_baja__isnull=True) | Q(fecha_baja__gt=corte))
            .select_related('equipo', 'existencia_verificada_por').order_by('codigo_unidad', 'pk'))


def _de_la_unidad(unidad):
    """Filtro de las órdenes e incidencias de la unidad: las suyas y las de sus equipos sin unidad anotada."""
    from django.db.models import Q
    from apps.documentos.models.funcionalidad import equipos_del_alcance
    return Q(unidad=unidad) | Q(unidad__isnull=True, equipo__in=equipos_del_alcance(unidad).values('pk'))


def _dia(valor):
    """El día local de una fecha con hora."""
    from django.utils import timezone
    return timezone.localtime(valor).date() if valor else None


# -- mantenimiento y equipamiento (sección 4.2) -------------------------------------------

def _plan_vigente(equipos, corte):
    from apps.recursos.models.mantenimiento import PlanMantenimientoEquipo

    planes = list(PlanMantenimientoEquipo.objects.filter(equipo__in=[e.pk for e in equipos], activo=True)
                  .select_related('equipo__equipo', 'responsable')
                  .order_by('equipo__codigo_unidad', 'nombre', 'pk'))
    filas = [[
        _equipo(plan.equipo),
        _corto(CRITICIDADES, plan.equipo.criticidad),
        texto(plan.nombre, 90),
        plan.get_tipo_display(),
        f'Cada {plural(plan.frecuencia_dias, "día", "días")}',
        par(fecha(plan.equipo.fecha_ultimo_mantenimiento), fecha(plan.proxima_ejecucion)),
        par(_corto(EJECUTORES, plan.ejecutor), texto(plan.proveedor, 60) if plan.proveedor.strip() else ''),
        nombre_de(plan.responsable),
    ] for plan in planes]
    con_plan = {plan.equipo_id for plan in planes if plan.fecha_inicio <= corte}
    criticos_sin_plan = sum(e.criticidad == 'critico' and e.pk not in con_plan for e in equipos)
    return Registro(
        'Plan de mantenimiento vigente',
        ('Equipo', 'Criticidad', 'Plan', 'Tipo', 'Frecuencia', 'Última / próxima', 'Ejecutor / proveedor',
         'Responsable'),
        filas, pesos=(20, 9, 20, 10, 9, 10, 11, 11),
        total=(f'Total: {plural(len(planes), "plan vigente", "planes vigentes")} · equipos con plan: '
               f'{cifra(len({plan.equipo_id for plan in planes}))} · equipos críticos sin plan: '
               f'{cifra(criticos_sin_plan)}'),
        vacio=f'No hay planes de mantenimiento vigentes. Equipos críticos sin plan: {cifra(criticos_sin_plan)}.')


def _ejecucion_real(orden):
    """Inicio y fin reales de una orden, o '' si todavía no empieza."""
    desde, hasta = fecha(orden.fecha_inicio), fecha(orden.fecha_fin)
    if orden.fecha_inicio and orden.fecha_fin:
        return f'real {desde}' if desde == hasta else f'real {desde}–{hasta}'
    if orden.fecha_inicio:
        return f'inicio {desde}'
    return f'fin {hasta}' if orden.fecha_fin else ''


def _mantenimientos(unidad, inicio, fin):
    from django.db.models import Q
    from apps.recursos.models.mantenimiento import MantenimientoEquipo

    periodo = (inicio, fin)
    ordenes = list(MantenimientoEquipo.objects.filter(_de_la_unidad(unidad))
                   .filter(Q(fecha_programada__date__range=periodo) | Q(fecha_inicio__date__range=periodo)
                           | Q(fecha_fin__date__range=periodo))
                   .select_related('equipo__equipo', 'plan', 'incidencia').order_by('fecha_programada', 'pk'))
    filas = []
    for orden in ordenes:
        origen = ' · '.join(p for p in (
            f'Plan: {orden.plan.nombre}' if orden.plan_id else '',
            f'Incidencia del {fecha(orden.incidencia.fecha_reporte)}' if orden.incidencia_id else '') if p)
        ejecutor = ' · '.join(p for p in (_corto(EJECUTORES, orden.ejecutor), orden.proveedor.strip()) if p)
        con_resultado = orden.estado == 'completado' or orden.resultado_operativo != 'pendiente'
        filas.append([
            texto(orden.codigo),
            _equipo(orden.equipo),
            par(orden.get_tipo_display(), texto(origen, 80) if origen else ''),
            par(fecha(orden.fecha_programada), _ejecucion_real(orden)),
            orden.get_estado_display(),
            par(texto(ejecutor, 50), _dinero(orden.costo) if orden.costo is not None else ''),
            par(texto(orden.resultado, 180),
                'Prueba: ' + texto(orden.prueba_funcionamiento, 140) if orden.prueba_funcionamiento.strip() else ''),
            _corto(RESULTADOS_OPERATIVOS, orden.resultado_operativo) if con_resultado else '—',
            enlace_archivo(orden.informe),
        ])
    tipos = Counter(orden.tipo for orden in ordenes)
    otros = len(ordenes) - tipos['preventivo'] - tipos['correctivo']
    costo = sum((o.costo for o in ordenes if o.costo is not None and o.estado != 'cancelado'), Decimal('0'))
    pie = (f'Total: {plural(len(ordenes), "orden", "órdenes")} · completadas: '
           f'{cifra(sum(o.estado == "completado" for o in ordenes))} · preventivas: {cifra(tipos["preventivo"])} · '
           f'correctivas: {cifra(tipos["correctivo"])}' + (f' · de otro tipo: {cifra(otros)}' if otros else '')
           + f' · costo total: {_dinero(costo)}')
    return Registro(
        'Mantenimientos del período',
        ('Orden', 'Equipo', 'Tipo / origen', 'Programada / ejecutada', 'Estado', 'Ejecutor / costo', 'Resultado',
         'Resultado operativo', 'Informe'),
        filas, pesos=(11, 15, 12, 11, 8, 12, 19, 7, 5), total=pie,
        vacio='No hay órdenes de mantenimiento en el período.')


def _situacion_del_plan(tiene_plan, exigibles, respaldadas, futuras):
    if not tiene_plan:
        return 'Sin plan'
    if exigibles > respaldadas:
        return 'Atrasado'
    return 'Al día' if exigibles or futuras else 'Sin órdenes programadas en el año'


def _cumplimiento_critico(contexto, equipos):
    """Las órdenes del programa anual de cada equipo crítico que ya son exigibles al corte.

    Cuenta lo mismo que la meta de mantenimiento del informe (que da el porcentaje frente al 80 %):
    con la medición activa, una orden está ejecutada con respaldo si la medición la acredita; sin
    ella, si está completada al corte y tiene informe.
    """
    from apps.recursos.models.mantenimiento import MantenimientoEquipo, PlanMantenimientoEquipo

    titulo = 'Cumplimiento del plan en equipos críticos'
    cabecera = ('Equipo crítico', 'Programadas exigibles', 'Ejecutadas con respaldo', 'Pendientes', 'Situación')
    criticos = [e for e in equipos if e.criticidad == 'critico']
    if not criticos:
        return Registro(titulo, cabecera, [], vacio='La unidad no tiene equipos críticos identificados.')
    claves = [e.pk for e in criticos]
    corte, anio = contexto.corte, contexto.inicio.year
    con_plan = set(PlanMantenimientoEquipo.objects.filter(equipo_id__in=claves, activo=True, fecha_inicio__lte=corte)
                   .values_list('equipo_id', flat=True))
    medida = ((contexto.registros.get('mediciones_porcentuales') or {}).get('MANTENIMIENTO') or {}).get('equipos')
    acreditadas = set(medida.get('ordenes_acreditadas') or ()) if medida else None
    cuentas = defaultdict(lambda: [0, 0, 0])  # exigibles, ejecutadas con respaldo, programadas después del corte
    for orden in MantenimientoEquipo.objects.filter(
            _de_la_unidad(contexto.unidad), equipo_id__in=claves,
            fecha_programada__date__range=(date(anio, 1, 1), date(anio, 12, 31))):
        cuenta = cuentas[orden.equipo_id]
        if _dia(orden.fecha_programada) > corte:
            cuenta[2] += 1
            continue
        cuenta[0] += 1
        if acreditadas is not None:
            cuenta[1] += orden.codigo in acreditadas
        else:
            cuenta[1] += bool(orden.estado == 'completado' and orden.informe and orden.fecha_fin
                              and _dia(orden.fecha_fin) <= corte)
    filas = []
    for equipo in criticos:
        exigibles, respaldadas, futuras = cuentas[equipo.pk]
        filas.append([_equipo(equipo), cifra(exigibles), cifra(respaldadas), cifra(exigibles - respaldadas),
                      _situacion_del_plan(equipo.pk in con_plan, exigibles, respaldadas, futuras)])
    exigibles = sum(cuenta[0] for cuenta in cuentas.values())
    respaldadas = sum(cuenta[1] for cuenta in cuentas.values())
    return Registro(titulo, cabecera, filas, pesos=(40, 14, 14, 12, 20),
                    suma=['Total', cifra(exigibles), cifra(respaldadas), cifra(exigibles - respaldadas),
                          f'Programa anual {anio}, al {fecha(corte)}'])


def _dias_fuera_de_servicio(incidencia, limite):
    """Días del reporte a la resolución o al corte, si la incidencia detuvo la operación."""
    if not incidencia.detiene_operacion:
        return None
    hasta = min(incidencia.fecha_resolucion or limite, limite)
    return round(max((hasta - incidencia.fecha_reporte).total_seconds(), 0) / 86400, 1)


def _incidencias(unidad, inicio, fin, corte):
    from django.db.models import Q
    from django.utils import timezone
    from apps.recursos.models.mantenimiento import IncidenciaEquipo

    # Las reportadas en el período y las anteriores que seguían abiertas al empezar: también restan disponibilidad.
    anteriores = Q(fecha_reporte__date__lt=inicio) & (Q(fecha_resolucion__isnull=True)
                                                    | Q(fecha_resolucion__date__gte=inicio))
    incidencias = list(IncidenciaEquipo.objects.filter(_de_la_unidad(unidad)).exclude(tipo='seguridad')
                       .filter(Q(fecha_reporte__date__range=(inicio, fin)) | anteriores)
                       .select_related('equipo__equipo', 'reportada_por').prefetch_related('mantenimientos')
                       .order_by('fecha_reporte', 'pk'))
    limite = min(timezone.now(), timezone.make_aware(datetime.combine(corte + timedelta(days=1), time.min)))
    tipos, prioridades = dict(IncidenciaEquipo.TIPOS), dict(IncidenciaEquipo.PRIORIDADES)
    filas, dias_totales = [], 0.0
    for incidencia in incidencias:
        dias = _dias_fuera_de_servicio(incidencia, limite)
        dias_totales += dias or 0
        filas.append([
            par(fecha(incidencia.fecha_reporte), nombre_de(incidencia.reportada_por)),
            _equipo(incidencia.equipo),
            par(_corto(tipos, incidencia.tipo), _corto(prioridades, incidencia.prioridad)),
            par(texto(incidencia.titulo, 90),
                texto(incidencia.descripcion, 160) if incidencia.descripcion.strip() else ''),
            si_no(incidencia.detiene_operacion),
            cifra(dias) if dias is not None else '—',
            par(texto(incidencia.solucion, 160), ', '.join(m.codigo for m in incidencia.mantenimientos.all())),
            incidencia.get_estado_display(),
        ])
    desde_antes = sum(_dia(i.fecha_reporte) < inicio for i in incidencias)
    pie = (f'Total: {plural(len(incidencias), "incidencia", "incidencias")} · detuvieron la operación: '
           f'{cifra(sum(i.detiene_operacion for i in incidencias))} · días fuera de servicio: '
           f'{cifra(round(dias_totales, 1))}')
    if desde_antes:
        pie += f' · abiertas desde antes del período: {cifra(desde_antes)}'
    return Registro(
        'Disponibilidad: fallas e incidencias técnicas',
        ('Reporte', 'Equipo', 'Tipo / prioridad', 'Descripción', 'Detuvo la operación', 'Días fuera de servicio',
         'Solución', 'Estado'),
        filas, pesos=(11, 15, 12, 22, 8, 8, 16, 8), total=pie,
        vacio='No hay fallas ni incidencias técnicas en el período.')


def _pruebas_funcionales(unidad, inicio, fin, equipos):
    activos = {equipo.pk: equipo for equipo in equipos}
    filas, ultimo = [], {}
    for prueba in evidencias_de_gestion(unidad, 'FUNCIONALIDAD', inicio, fin):
        detalle = prueba.detalle if isinstance(prueba.detalle, dict) else {}
        foto = detalle.get('equipo_snapshot') if isinstance(detalle.get('equipo_snapshot'), dict) else {}
        clave = detalle.get('equipo_id') if type(detalle.get('equipo_id')) is int else None
        resultado = detalle.get('resultado_funcional') if isinstance(detalle.get('resultado_funcional'), str) else ''
        if clave in activos:
            ultimo[clave] = resultado  # Vienen por fecha: queda la última prueba de cada equipo.
        filas.append([
            fecha(prueba.fecha),
            _equipo(activos[clave]) if clave in activos else _codigo_y_nombre(foto.get('codigo'), foto.get('nombre')),
            texto(detalle.get('procedimiento'), 200),
            texto(detalle.get('criterio'), 160),
            _corto(RESULTADOS_FUNCIONALES, resultado) if resultado else '—',
            texto(detalle.get('hallazgos_funcionales'), 180),
            nombre_de(prueba.responsable),
            _respaldo(prueba),
        ])
    resultados = Counter(ultimo.values())
    pie = (f'Total: {plural(len(filas), "prueba", "pruebas")} · equipos probados: {cifra(len(ultimo))} de '
           f'{cifra(len(equipos))} activos · operativos: {cifra(resultados["operativo"])} · con observaciones: '
           f'{cifra(resultados["observado"])} · no operativos: {cifra(resultados["no_operativo"])}')
    return Registro(
        'Funcionalidad: pruebas funcionales',
        ('Fecha', 'Equipo', 'Procedimiento', 'Criterio de aceptación', 'Resultado', 'Hallazgos', 'Responsable',
         'Respaldo'),
        filas, pesos=(8, 15, 19, 15, 10, 14, 10, 9), total=pie,
        vacio=f'No hay pruebas funcionales registradas en el período. Equipos activos sin prueba: '
              f'{cifra(len(equipos))}.')


def _estado_de_equipos(equipos):
    from apps.recursos.models.unidades import UnidadEquipo

    nombres = dict(UnidadEquipo.ESTADO_UNIDAD_CHOICES)
    todos = Counter(equipo.estado_unidad for equipo in equipos)
    criticos = Counter(equipo.estado_unidad for equipo in equipos if equipo.criticidad == 'critico')
    estados = [*ESTADOS_DE_EQUIPO, *sorted(set(todos) - set(ESTADOS_DE_EQUIPO))] if equipos else []
    return Registro(
        'Estado de los equipos al corte', ('Estado', 'Equipos', 'De ellos, críticos'),
        [[_corto(nombres, estado).capitalize(), cifra(todos[estado]), cifra(criticos[estado])] for estado in estados],
        pesos=(50, 25, 25), suma=['Total', cifra(len(equipos)), cifra(sum(criticos.values()))],
        vacio='La unidad no tiene equipos activos al corte.')


def _infraestructura(contexto):
    """Cada intervención de infraestructura programada para el período, con su ejecución si la tiene."""
    from apps.documentos.models.infraestructura import fecha_detalle
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from .infraestructura_laboratorios import fechas_programadas

    unidad, inicio, fin, corte = contexto.unidad, contexto.inicio, contexto.fin, contexto.corte
    planes = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo='PLAN-INFRA', fecha__lte=corte)
                  .exclude(estado='anulado').select_related('responsable', 'recurso').order_by('fecha', 'pk'))
    ejecuciones = evidencias_de_gestion(unidad, 'EJECUCION-INFRA', inicio, fin)
    espacios = {e.pk: e for e in EspacioReservable.objects.filter(unidad=unidad)} if planes or ejecuciones else {}

    def detalle_de(evidencia):
        return evidencia.detalle if isinstance(evidencia.detalle, dict) else {}

    def lugar(detalle):
        espacio = espacios.get(detalle.get('espacio_id')) if type(detalle.get('espacio_id')) is int else None
        if espacio:
            return _codigo_y_nombre(espacio.codigo, espacio.nombre, 60)
        return texto(detalle.get('ubicacion') or ('Toda la unidad' if detalle.get('alcance_todo_laboratorio') else ''),
                     80)

    def ejecutada(detalle):
        desde, hasta = fecha(fecha_detalle(detalle, 'fecha_inicio')), fecha(fecha_detalle(detalle, 'fecha_fin'))
        return f'ejecutada {hasta}' if desde in ('—', hasta) else f'ejecutada {desde}–{hasta}'

    def fila(plan, prevista, ejecucion):
        origen, cierre = detalle_de(plan) if plan else {}, detalle_de(ejecucion) if ejecucion else {}
        intervencion = origen.get('intervencion') or (f"Plan {cierre.get('plan_codigo')}" if cierre.get('plan_codigo')
                                                     else '')
        estado = 'Ejecutada' if ejecucion else 'Programada' if prevista and prevista > corte else 'Pendiente'
        evidencia = ejecucion or plan
        return [
            lugar(origen if plan else cierre),
            par(texto(intervencion, 140), texto(cierre.get('resultado'), 140) if cierre.get('resultado') else ''),
            par(fecha(prevista), ejecutada(cierre) if ejecucion else ''),
            nombre_de(evidencia.responsable),
            estado,
            _respaldo(evidencia),
        ]

    cierres = {}
    for ejecucion in ejecuciones:
        detalle = detalle_de(ejecucion)
        cierres.setdefault((detalle.get('plan_id'), str(detalle.get('fecha_programada') or '')), ejecucion)
    por_clave = {plan.pk: plan for plan in planes}
    ordenadas, presentadas = [], set()
    for plan in planes:
        detalle = detalle_de(plan)
        if detalle.get('alcance_infraestructura') == 'no_aplica':
            # La declaración anual de que la unidad no tiene infraestructura que mantener.
            if inicio.year <= plan.fecha.year <= fin.year:
                ordenadas.append((plan.fecha, plan.pk, [
                    'Toda la unidad', texto('No aplica: ' + str(detalle.get('justificacion_alcance') or ''), 200),
                    fecha(plan.fecha), nombre_de(plan.responsable), 'No aplica', _respaldo(plan)]))
            continue
        for prevista in fechas_programadas(detalle, inicio, fin):
            ejecucion = cierres.get((plan.pk, prevista.isoformat()))
            if ejecucion:
                presentadas.add(ejecucion.pk)
            ordenadas.append((prevista, plan.pk, fila(plan, prevista, ejecucion)))
    for ejecucion in ejecuciones:
        # Ejecutadas en el período que estaban programadas para otra fecha.
        if ejecucion.pk not in presentadas:
            detalle = detalle_de(ejecucion)
            prevista = fecha_detalle(detalle, 'fecha_programada')
            ordenadas.append((prevista or ejecucion.fecha, ejecucion.pk,
                              fila(por_clave.get(detalle.get('plan_id')), prevista, ejecucion)))
    filas = [f for _fecha, _clave, f in sorted(ordenadas, key=lambda orden: orden[:2])]
    estados = Counter(f[4] for f in filas)
    pie = (f'Total: {plural(len(filas), "intervención", "intervenciones")} · ejecutadas: '
           f'{cifra(estados["Ejecutada"])} · pendientes: {cifra(estados["Pendiente"])} · programadas: '
           f'{cifra(estados["Programada"])}')
    alcance = {'centro_experimental': ' (riego, invernaderos, establos y cercas)',
               'observatorios': ' (red, servidores y respaldos de la sala)'}.get(contexto.base, '')
    return Registro(
        'Mantenimiento de infraestructura y espacios',
        ('Espacio o instalación', 'Intervención', 'Programada / ejecutada', 'Responsable', 'Estado', 'Respaldo'),
        filas, pesos=(20, 32, 14, 14, 9, 11), total=pie,
        vacio=f'No hay intervenciones de infraestructura{alcance} programadas ni ejecutadas en el período.')


def mantenimiento(contexto):
    """Anexo de mantenimiento y equipamiento (sección 4.2).

    Plan vigente, órdenes del período, cumplimiento en equipos críticos, fallas, pruebas funcionales,
    estado de los equipos al corte e infraestructura. Los incidentes de seguridad son del anexo de seguridad.
    """
    unidad, inicio, fin, corte = contexto.unidad, contexto.inicio, contexto.fin, contexto.corte
    equipos = list(_equipos_activos(unidad, corte))
    return [
        _plan_vigente(equipos, corte),
        _mantenimientos(unidad, inicio, fin),
        _cumplimiento_critico(contexto, equipos),
        _incidencias(unidad, inicio, fin, corte),
        _pruebas_funcionales(unidad, inicio, fin, equipos),
        _estado_de_equipos(equipos),
        _infraestructura(contexto),
    ]


# -- inventario (sección 4.3) -------------------------------------------------------------

def _actas_de_inventario(unidad, inicio, fin):
    actas = evidencias_de_gestion(unidad, 'INVENTARIO', inicio, fin)
    filas = [[
        texto(acta.codigo),
        fecha(acta.fecha),
        texto(', '.join(str(a) for a in acta.alcance).capitalize() if isinstance(acta.alcance, list) else ''),
        nombre_de(acta.responsable),
        texto(acta.descripcion, 220),
        _respaldo(acta),
    ] for acta in actas]
    verificadas = sum(acta.estado == 'validado' and not acta.demostracion for acta in actas)
    return Registro(
        'Acta de revisión física del período',
        ('Código', 'Fecha', 'Alcance', 'Responsable', 'Observaciones', 'Respaldo'),
        filas, pesos=(15, 9, 17, 15, 32, 12),
        total=f'Total: {plural(len(actas), "acta", "actas")} · verificadas: {cifra(verificadas)}',
        vacio='No hay acta de revisión física registrada en el período.')


def _verificacion_fisica(equipo):
    if not equipo.existencia_verificada:
        return 'Sin verificar'
    cuando = fecha(equipo.existencia_verificada_en) if equipo.existencia_verificada_en else 'Verificada'
    quien = nombre_de(equipo.existencia_verificada_por) if equipo.existencia_verificada_por_id else ''
    return ' · '.join(p for p in (cuando, quien) if p)


def _equipos_del_inventario(unidad, equipos, titulo):
    from apps.documentos.models.funcionalidad import equipos_del_alcance
    from apps.recursos.models.unidades import UnidadEquipo

    estados = dict(UnidadEquipo.ESTADO_UNIDAD_CHOICES)
    filas = []
    for equipo in equipos:
        modelo = equipo.equipo
        ubicacion = (equipo.ubicacion_especifica or equipo.ubicacion_bodega or '').strip()
        adquisicion = ' · '.join(p for p in (
            _corto(ORIGENES_DE_ADQUISICION, equipo.origen_adquisicion),
            fecha(equipo.fecha_adquisicion) if equipo.fecha_adquisicion else '') if p)
        garantia = equipo.fin_garantia
        filas.append([
            _equipo(equipo),
            par(texto(modelo.marca, 40), texto(modelo.modelo, 40) if modelo.modelo else ''),
            texto(equipo.numero_serie, 40),
            par(texto(equipo.codigo_bien),
                ' · '.join(p for p in (equipo.tipo_bien, texto(equipo.clase_bien, 60) if equipo.clase_bien else '')
                           if p)),
            par(texto(equipo.custodio, 50), texto(ubicacion, 70) if ubicacion else ''),
            par(_corto(estados, equipo.estado_unidad).capitalize(), _corto(CRITICIDADES, equipo.criticidad)),
            par(adquisicion, _dinero(equipo.valor_contable) if equipo.valor_contable is not None else ''),
            par(_verificacion_fisica(equipo), f'garantía hasta {fecha(garantia)}' if garantia else ''),
            enlace_archivo(modelo.ficha_tecnica),
        ])
    valor = sum((e.valor_contable for e in equipos if e.valor_contable is not None), Decimal('0'))
    sin_listar = equipos_del_alcance(unidad).count() - len(equipos)
    pie = (f'Total: {plural(len(equipos), "equipo activo", "equipos activos")} · verificados: '
           f'{cifra(sum(e.existencia_verificada for e in equipos))} · críticos: '
           f'{cifra(sum(e.criticidad == "critico" for e in equipos))} · valor contable total: {_dinero(valor)}')
    if sin_listar > 0:
        pie += f' · inactivos o dados de baja, que no se listan: {cifra(sin_listar)}'
    return Registro(
        titulo,
        ('Código / nombre', 'Marca / modelo', 'Serie', 'Código del bien / clase', 'Custodio / ubicación',
         'Estado / criticidad', 'Adquisición', 'Verificación física', 'Ficha técnica'),
        filas, pesos=(16, 10, 8, 11, 21, 8, 12, 9, 5), total=pie,
        vacio='La unidad no tiene equipos activos al corte.'
              + (f' Inactivos o dados de baja, que no se listan: {cifra(sin_listar)}.' if sin_listar > 0 else ''))


def _bajas_y_traspasos(unidad, inicio, fin):
    from django.db.models import Q
    from apps.documentos.models.funcionalidad import equipos_del_alcance
    from apps.recursos.models.redistribucion import EquipoEnTraspaso

    periodo = (inicio, fin)
    ordenadas = []
    for equipo in (equipos_del_alcance(unidad).filter(fecha_baja__range=periodo)
                   .select_related('equipo', 'reemplazado_por').order_by('fecha_baja', 'codigo_unidad')):
        ordenadas.append((equipo.fecha_baja, [
            _equipo(equipo),
            'Baja',
            fecha(equipo.fecha_baja),
            equipo.get_motivo_baja_display() or '—',
            f'Reemplazado por {equipo.reemplazado_por.codigo_unidad}' if equipo.reemplazado_por_id else '—',
            texto(equipo.observacion_baja, 140),
        ]))
    # Un traspaso ejecutado cuenta en la fecha en que se ejecutó; los demás, en la de su solicitud.
    traspasos = (EquipoEnTraspaso.objects
                 .filter(Q(traspaso__unidad_origen=unidad) | Q(traspaso__unidad_destino=unidad))
                 .exclude(traspaso__estado='anulado')
                 .filter(Q(traspaso__estado='ejecutado', traspaso__fecha_ejecucion__date__range=periodo)
                         | Q(~Q(traspaso__estado='ejecutado'), traspaso__fecha_solicitud__date__range=periodo))
                 .select_related('traspaso__unidad_origen', 'traspaso__unidad_destino', 'equipo__equipo')
                 .order_by('traspaso__codigo', 'codigo_anterior', 'pk'))
    for item in traspasos:
        traspaso = item.traspaso
        cuando = _dia(traspaso.fecha_ejecucion if traspaso.estado == 'ejecutado' else traspaso.fecha_solicitud)
        nombre = item.equipo.equipo.nombre + (
            f' · ahora {item.codigo_nuevo}' if item.codigo_nuevo and item.codigo_nuevo != item.codigo_anterior else '')
        entrega = traspaso.unidad_origen_id == unidad.pk
        ordenadas.append((cuando, [
            _codigo_y_nombre(item.codigo_anterior or item.equipo.codigo_unidad, nombre, 90),
            par('Traspaso entregado' if entrega else 'Traspaso recibido', traspaso.get_estado_display()),
            fecha(cuando),
            traspaso.get_motivo_display(),
            texto(traspaso.unidad_destino.nombre, 80) if entrega
            else par(texto(unidad.nombre, 80), 'recibido de ' + texto(traspaso.unidad_origen.nombre, 80)),
            par(texto(traspaso.codigo), enlace_archivo(traspaso.acta_firmada)),
        ]))
    filas = [f for _fecha, f in sorted(ordenadas, key=lambda orden: orden[0])]
    bajas = sum(f[1] == 'Baja' for f in filas)
    return Registro(
        'Bajas y traspasos del período',
        ('Equipo', 'Movimiento', 'Fecha', 'Motivo', 'Destino / reemplazo', 'Acta'),
        filas, pesos=(24, 14, 9, 19, 20, 14),
        total=(f'Total: {plural(len(filas), "movimiento", "movimientos")} · bajas: {cifra(bajas)} · traspasos: '
               f'{cifra(len(filas) - bajas)}'),
        vacio='No hubo bajas ni traspasos de equipos en el período.')


def _reactivos(unidad, inicio, corte, base):
    """Un lote por fila: los que tienen saldo al corte y los que se cerraron o ingresaron en el período."""
    from django.db.models import Q
    from apps.recursos.models.consumibles import Consumible, LoteConsumible

    articulos = list(Consumible.objects.filter(unidad=unidad, activo=True, clasificacion__in=CLASES_DE_REACTIVO)
                     .order_by('codigo'))
    lotes = defaultdict(list)
    for lote in (LoteConsumible.objects.filter(consumible__in=articulos)
                 .filter(Q(cantidad_actual__gt=0) | Q(fecha_ingreso__gte=inicio) | Q(actualizado_en__date__gte=inicio))
                 .select_related('equipo_en_uso').order_by('fecha_vencimiento', 'codigo')):
        lotes[lote.consumible_id].append(lote)
    en_centro = base == 'centro_experimental'
    clases = [clase for clase in CLASES_DE_REACTIVO if any(a.clasificacion == clase for a in articulos)]
    filas, total_lotes, vencidos, por_vencer = [], 0, 0, 0
    for clase in clases:
        if len(clases) > 1:
            filas.append(Grupo(Consumible.CLASIFICACION_DETALLE[clase][0]))
        for articulo in (a for a in articulos if a.clasificacion == clase):
            comunes = [_codigo_y_nombre(articulo.codigo, articulo.nombre),
                       par(texto(articulo.presentacion, 50), texto(articulo.marca, 40) if articulo.marca else '')]
            ficha = enlace_archivo(articulo.ficha_tecnica)
            if not lotes[articulo.pk]:
                filas.append([*comunes, 'Sin lote registrado', _cantidad(articulo.stock_total, articulo.unidad_medida),
                              fecha(articulo.fecha_vencimiento), texto(articulo.ubicacion, 70), '—', ficha])
            for lote in lotes[articulo.pk]:
                con_saldo = lote.cantidad_actual > 0
                vencido = bool(con_saldo and lote.fecha_vencimiento and lote.fecha_vencimiento < corte)
                total_lotes += 1
                vencidos += vencido
                por_vencer += bool(con_saldo and lote.fecha_vencimiento and not vencido
                                   and lote.fecha_vencimiento <= corte + timedelta(days=DIAS_PARA_VENCER))
                filas.append([
                    *comunes,
                    texto(lote.codigo),
                    _cantidad(lote.cantidad_actual, articulo.unidad_medida),
                    par(fecha(lote.fecha_vencimiento), 'vencido' if vencido else ''),
                    texto(lote.ubicacion_completa, 80),
                    lote.get_estado_display(),
                    ficha,
                ])
    sustantivo = ('artículo', 'artículos') if en_centro else ('reactivo', 'reactivos')
    return Registro(
        'Reactivos, agroquímicos y medicamentos veterinarios' if en_centro else 'Reactivos',
        ('Código / nombre', 'Presentación / marca', 'Lote', 'Cantidad', 'Vencimiento', 'Ubicación',
         'Estado del lote', 'Ficha de seguridad'),
        filas, pesos=(22, 14, 15, 9, 9, 16, 8, 7),
        total=(f'Total: {plural(len(articulos), *sustantivo)} · lotes: {cifra(total_lotes)} · vencidos con saldo: '
               f'{cifra(vencidos)} · vencen en {DIAS_PARA_VENCER} días: {cifra(por_vencer)}'),
        vacio='La unidad no tiene reactivos, agroquímicos ni medicamentos veterinarios activos en su inventario.')


def _insumos(unidad, base):
    from apps.recursos.models.consumibles import Consumible, LoteConsumible

    articulos = list(Consumible.objects.filter(unidad=unidad, activo=True)
                     .exclude(clasificacion__in=CLASES_DE_REACTIVO).order_by('codigo'))
    lotes = defaultdict(lambda: [0, 0, None])  # con saldo, del cliente, vencimiento más próximo
    for articulo, vence, del_cliente in (LoteConsumible.objects.filter(consumible__in=articulos, cantidad_actual__gt=0)
                                         .values_list('consumible_id', 'fecha_vencimiento', 'material_cliente')):
        cuenta = lotes[articulo]
        cuenta[0] += 1
        cuenta[1] += del_cliente
        if vence and (cuenta[2] is None or vence < cuenta[2]):
            cuenta[2] = vence
    en_planta = base == 'plantas_piloto'
    filas = []
    for articulo in articulos:
        con_saldo, del_cliente, vence = lotes[articulo.pk]
        medida = articulo.unidad_medida
        filas.append([
            _codigo_y_nombre(articulo.codigo, articulo.nombre),
            articulo.get_clasificacion_display(),
            _cantidad(articulo.stock_total, medida),
            par(_cantidad(articulo.minimo, medida) if articulo.minimo else '—',
                _cantidad(articulo.stock_objetivo, medida) if articulo.stock_objetivo else ''),
            par(cifra(con_saldo), f'del cliente: {cifra(del_cliente)}' if en_planta and del_cliente else ''),
            fecha(vence or articulo.fecha_vencimiento),
            texto(articulo.ubicacion, 70),
            _corto(ORIGENES_DE_ABASTECIMIENTO, articulo.origen_abastecimiento),
        ])
    sin_lotes = sum(a.stock_total > 0 and not lotes[a.pk][0] for a in articulos)
    return Registro(
        'Insumos y materiales',
        ('Código / nombre', 'Tipo', 'Existencia', 'Mínimo / objetivo', 'Lotes vigentes', 'Próximo vencimiento',
         'Ubicación', 'Origen'),
        filas, pesos=(26, 10, 10, 10, 8, 10, 15, 11),
        total=(f'Total: {plural(len(articulos), "artículo", "artículos")} · bajo el mínimo: '
               f'{cifra(sum(a.bajo_minimo for a in articulos))} · sin lotes localizables: {cifra(sin_lotes)}'),
        vacio='La unidad no tiene insumos ni materiales activos en su inventario.')


def _movimientos(unidad, inicio, fin, base):
    from django.db.models import Q
    from apps.recursos.models.consumibles import EntradaInventario

    movimientos = list(EntradaInventario.objects
                       .filter(Q(unidad=unidad) | Q(consumible__unidad=unidad), fecha__date__range=(inicio, fin))
                       .select_related('consumible', 'lote_inventario', 'reserva__planificacion_practica', 'usuario')
                       .order_by('fecha', 'pk'))
    # En la planta piloto, los consumos de producción se presentan en el anexo de producción.
    aparte = 'consumo_produccion' if base == 'plantas_piloto' else None
    listados = [m for m in movimientos if m.motivo != aparte]
    filas = []
    for movimiento in listados:
        articulo, reserva = movimiento.consumible, movimiento.reserva
        practica = getattr(reserva, 'planificacion_practica', None) if reserva else None
        filas.append([
            fecha(movimiento.fecha),
            _codigo_y_nombre(articulo.codigo, articulo.nombre, 60),
            par(movimiento.get_tipo_display(), movimiento.get_motivo_display() if movimiento.motivo else ''),
            _cantidad(movimiento.cantidad, articulo.unidad_medida),
            _cantidad(movimiento.saldo_resultante, articulo.unidad_medida),
            texto(movimiento.lote_inventario.codigo if movimiento.lote_inventario_id else ''),
            par(texto(reserva.codigo_reserva), texto(practica.codigo) if practica else '') if reserva
            else texto(movimiento.referencia, 60),
            nombre_de(movimiento.usuario) if movimiento.usuario_id else 'Sistema',
        ])
    motivos = Counter(m.get_motivo_display().lower() if m.motivo else 'sin motivo' for m in listados)
    pie = (f'Total: {plural(len(listados), "movimiento", "movimientos")} · ingresos: '
           f'{cifra(sum(m.tipo == "ingreso" for m in listados))} · salidas: '
           f'{cifra(sum(m.tipo == "salida" for m in listados))}')
    if motivos:
        pie += ' · por motivo: ' + ', '.join(f'{motivo} {cifra(n)}' for motivo, n in motivos.most_common())
    produccion = len(movimientos) - len(listados)
    if aparte:
        pie += f' · consumos de producción, que se presentan en el anexo de producción: {cifra(produccion)}'
    return Registro(
        'Movimientos del período',
        ('Fecha', 'Artículo', 'Movimiento / motivo', 'Cantidad', 'Saldo', 'Lote', 'Referencia', 'Responsable'),
        filas, pesos=(8, 20, 17, 8, 8, 15, 14, 10), total=pie,
        vacio='No hay movimientos de reactivos ni insumos en el período.'
              + (f' Consumos de producción, que se presentan en el anexo de producción: {cifra(produccion)}.'
                 if aparte else ''))


def _programas(unidad):
    """El software de la unidad con los equipos donde está instalado, por nombre."""
    from apps.recursos.models.software import SoftwareDisponible
    return list(SoftwareDisponible.objects.filter(unidad=unidad).prefetch_related('equipos_instalados')
                .order_by('nombre', 'version', 'pk'))


def _licencias(programa):
    return par(cifra(programa.licencias_totales), f'disponibles: {cifra(programa.licencias_disponibles)}')


def _software_y_licencias(unidad):
    programas = [p for p in _programas(unidad) if p.activo]
    filas = [[
        _codigo_y_nombre(programa.codigo, programa.nombre),
        texto(programa.version),
        par(_corto(TIPOS_DE_SOFTWARE, programa.tipo_recurso), _corto(ACCESOS_A_SOFTWARE, programa.tipo_acceso)),
        _licencias(programa),
        _codigos(programa.equipos_existentes),
    ] for programa in programas]
    return Registro(
        'Software y licencias', ('Código / nombre', 'Versión', 'Tipo / acceso', 'Licencias', 'Instalado en'),
        filas, pesos=(32, 12, 16, 12, 28),
        total=f'Total: {plural(len(programas), "programa", "programas")}',
        vacio='La unidad no tiene software ni licencias activos.')


def _espacios_del_observatorio(unidad):
    from apps.gestion_unidades.models.espacios import EspacioReservable

    espacios = list(EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('codigo', 'pk'))
    filas = [[
        _codigo_y_nombre(espacio.codigo, espacio.nombre),
        espacio.get_tipo_display(),
        plural(espacio.capacidad, 'persona', 'personas'),
        texto(espacio.ubicacion, 120),
    ] for espacio in espacios]
    return Registro(
        'Espacios', ('Código / nombre', 'Tipo', 'Capacidad', 'Ubicación'), filas, pesos=(36, 16, 12, 36),
        total=f'Total: {plural(len(espacios), "espacio", "espacios")}',
        vacio='La unidad no tiene espacios activos.')


def inventario(contexto):
    """Anexo de inventario (sección 4.3): acta, equipos, bajas y traspasos, reactivos, insumos y movimientos.

    El observatorio lleva la versión reducida: acta, equipos informáticos, bajas y traspasos, software y
    licencias, y espacios.
    """
    unidad, inicio, fin, corte, base = contexto.unidad, contexto.inicio, contexto.fin, contexto.corte, contexto.base
    en_observatorio = base == 'observatorios'
    equipos = list(_equipos_activos(unidad, corte))
    registros = [
        _actas_de_inventario(unidad, inicio, fin),
        _equipos_del_inventario(unidad, equipos, 'Equipos informáticos' if en_observatorio else 'Equipos'),
        _bajas_y_traspasos(unidad, inicio, fin),
    ]
    if en_observatorio:
        return [*registros, _software_y_licencias(unidad), _espacios_del_observatorio(unidad)]
    return [*registros, _reactivos(unidad, inicio, corte, base), _insumos(unidad, base),
            _movimientos(unidad, inicio, fin, base)]


# -- fichas técnicas (sección 4.4) --------------------------------------------------------

def _jornadas(por_dia):
    """Junta los días seguidos con el mismo horario: «Lunes a viernes 08:00–12:00 y 14:00–18:00»."""
    bloques = []
    for dia in sorted(por_dia):
        horas = ' y '.join(por_dia[dia])
        if bloques and bloques[-1][1] == dia - 1 and bloques[-1][2] == horas:
            bloques[-1][1] = dia
        else:
            bloques.append([dia, dia, horas])
    return '; '.join((DIAS[a] if a == b else f'{DIAS[a]} a {DIAS[b].lower()}') + f' {horas}' for a, b, horas in bloques)


def _horario_de_operacion(unidad, inicio, fin):
    """El horario general y, si lo hay, el propio de cada período académico que toca el tramo."""
    from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad

    jornadas = defaultdict(lambda: defaultdict(list))
    for horario in (HorarioOperacionUnidad.objects.filter(unidad=unidad, activo=True).select_related('periodo')
                    .prefetch_related('periodo__versiones').order_by('dia_semana', 'hora_inicio')):
        periodo = ''
        if horario.periodo_id:
            version = horario.periodo.version_vigente
            if not version or version.fecha_fin_periodo < inicio or version.fecha_inicio_clases > fin:
                continue
            periodo = horario.periodo.codigo
        jornadas[periodo][horario.dia_semana].append(f'{horario.hora_inicio:%H:%M}–{horario.hora_fin:%H:%M}')
    partes = [(f'Período {periodo}: ' if periodo else '') + _jornadas(jornadas[periodo]) for periodo in sorted(jornadas)]
    return ' · '.join(partes) or texto(unidad.horario_atencion)


def _ficha_de_la_unidad(contexto):
    from django.db.models import Q
    from apps.formacion.models.asignaturas import Asignatura
    from apps.gestion_unidades.models.espacios import ResponsableUnidad
    from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad
    from .anexos_evidencia import TIPOS_DE_UNIDAD

    unidad, corte = contexto.unidad, contexto.corte
    personal = [f'{nombre_de(unidad.administrador)} (responsable de la unidad)'] if unidad.administrador_id else []
    personal += [f'{r.nombre_publico} ({r.get_rol_display()})'
                 for r in (ResponsableUnidad.objects.filter(unidad=unidad, activo=True).select_related('usuario')
                           .order_by('orden', 'nombre', 'pk'))
                 if not (r.usuario_id and r.usuario_id == unidad.administrador_id)]
    capacidad = (CapacidadOperativaUnidad.objects.filter(unidad=unidad, activo=True, vigente_desde__lte=corte)
                 .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=corte)).order_by('-vigente_desde').first())
    sin_capacidad = 'Sin capacidad operativa registrada'
    carreras = sorted({c.strip() for c in Asignatura.objects.filter(unidad=unidad, activa=True)
                       .values_list('carrera', flat=True) if c and c.strip()})
    filas = [
        ['Nombre y tipo', f'{unidad.nombre} · {TIPOS_DE_UNIDAD.get(contexto.base, "—")}'],
        ['Ubicación', texto(' · '.join(p for p in (unidad.ubicacion, unidad.direccion) if p))],
        ['Responsable', texto('; '.join(personal))],
        ['Horario de operación', texto(_horario_de_operacion(unidad, contexto.inicio, contexto.fin))],
        ['Aforo de seguridad', plural(capacidad.aforo_seguridad, 'persona', 'personas') if capacidad
         else sin_capacidad],
        ['Puestos con mobiliario / equipados',
         f'{cifra(capacidad.puestos_mobiliario)} / {cifra(capacidad.puestos_equipados)}' if capacidad
         else sin_capacidad],
        ['Personal', f'Atiende a {plural(capacidad.capacidad_personal, "persona", "personas")} a la vez' if capacidad
         else sin_capacidad],
        ['Carreras que atiende', texto('; '.join(carreras) or unidad.carreras)],
    ]
    return Registro('Ficha de la unidad', ('Dato', 'Valor'), filas, ficha=True)


def _uso_del_periodo(unidad, inicio, fin):
    """Cuántas prácticas y sesiones del período usaron cada espacio y cada software.

    Devuelve dos diccionarios {clave: (prácticas, sesiones)}. Una sesión cancelada, rechazada o vencida
    no cuenta; una práctica cuenta por la sesión que la atiende y, en el software, también por su tema.
    """
    from apps.formacion.models.asignaturas import TemaAsignatura
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    sesiones = (Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin))
                .exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS))
    practicas = list(PlanificacionPractica.objects.filter(
        unidad=unidad, fecha__range=(inicio, fin), es_version_vigente=True, eliminado_en__isnull=True,
    ).values_list('pk', 'reserva_id', 'tema_asignatura_id'))
    practica_de = {reserva: clave for clave, reserva, _tema in practicas if reserva}
    usos = []
    for relacion, campo in ((Reserva.espacios_solicitados.through, 'espacioreservable_id'),
                            (Reserva.software_solicitado.through, 'softwaredisponible_id')):
        uso_de = defaultdict(lambda: (set(), set()))
        for recurso, reserva in relacion.objects.filter(reserva__in=sesiones).values_list(campo, 'reserva_id'):
            uso_de[recurso][1].add(reserva)
            if reserva in practica_de:
                uso_de[recurso][0].add(practica_de[reserva])
        usos.append(uso_de)
    del_tema = defaultdict(set)
    for clave, _reserva, tema in practicas:
        if tema:
            del_tema[tema].add(clave)
    if del_tema:
        for tema, programa in (TemaAsignatura.software.through.objects.filter(temaasignatura_id__in=list(del_tema))
                               .values_list('temaasignatura_id', 'softwaredisponible_id')):
            usos[1][programa][0].update(del_tema[tema])
    return tuple({clave: (len(p), len(s)) for clave, (p, s) in uso_de.items()} for uso_de in usos)


def _celda_de_uso(uso):
    practicas, sesiones = uso
    return par(plural(practicas, 'práctica', 'prácticas'), plural(sesiones, 'sesión', 'sesiones'))


def _ejes_y_ciclos(unidad):
    """Por espacio del centro experimental: sus ejes productivos y sus ciclos o ensayos en curso."""
    from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo

    ejes, ciclos = defaultdict(list), defaultdict(list)
    for espacio, titulo in (EjeProductivo.espacios.through.objects.filter(ejeproductivo__unidad=unidad)
                            .order_by('ejeproductivo__orden', 'ejeproductivo__titulo')
                            .values_list('espacioreservable_id', 'ejeproductivo__titulo')):
        ejes[espacio].append(titulo)
    for ciclo in (CicloProductivo.objects.filter(eje__unidad=unidad, lugar__isnull=False, estado='en_curso')
                  .order_by('inicio', 'pk')):
        ciclos[ciclo.lugar_id].append(('Ensayo en curso: ' if ciclo.es_ensayo else 'Ciclo en curso: ') + ciclo.nombre)
    return ejes, ciclos


def _espacios(contexto, usos):
    """Los espacios activos y, además, los inactivos que se usaron en el período."""
    from apps.gestion_unidades.models.espacios import EspacioReservable

    en_centro = contexto.base == 'centro_experimental'
    ejes, ciclos = _ejes_y_ciclos(contexto.unidad) if en_centro else ({}, {})
    filas, reservables, visitables = [], 0, 0
    for espacio in (EspacioReservable.objects.filter(unidad=contexto.unidad).select_related('responsable__usuario')
                    .prefetch_related('equipos_asociados').order_by('codigo', 'pk')):
        uso = usos.get(espacio.pk, (0, 0))
        if not espacio.activo and not any(uso):
            continue
        reservables += espacio.reservable
        visitables += espacio.visitable
        dotacion = ' · '.join(p for p in (espacio.mobiliario_incluido.strip(), espacio.caracteristicas.strip()) if p)
        if en_centro:
            # En el centro experimental la columna lleva el eje productivo y el ciclo en curso.
            eje = 'Eje: ' + ', '.join(ejes[espacio.pk]) if ejes.get(espacio.pk) else ''
            dotacion = par(texto(' · '.join(p for p in (eje, dotacion) if p), 200),
                           texto('; '.join(ciclos[espacio.pk]), 160) if ciclos.get(espacio.pk) else '')
        else:
            dotacion = texto(dotacion, 220)
        filas.append([
            _codigo_y_nombre(espacio.codigo, espacio.nombre),
            par(espacio.get_tipo_display(), '' if espacio.activo else 'inactivo'),
            texto(espacio.ubicacion, 90),
            par(plural(espacio.capacidad, 'persona', 'personas'),
                f'{_cantidad(espacio.superficie_m2)} m²' if espacio.superficie_m2 is not None else ''),
            dotacion,
            _codigos(espacio.equipos_existentes),
            espacio.responsable.nombre_publico if espacio.responsable_id else '—',
            par(si_no(espacio.reservable), f'visitable: {si_no(espacio.visitable).lower()}'),
            _celda_de_uso(uso),
        ])
    return Registro(
        'Espacios y talleres',
        ('Código / nombre', 'Tipo', 'Ubicación', 'Capacidad', 'Mobiliario e infraestructura', 'Equipos asociados',
         'Responsable', 'Reservable / visitable', 'Uso en el período'),
        filas, pesos=(16, 9, 11, 9, 19, 13, 9, 7, 7),
        total=(f'Total: {plural(len(filas), "espacio", "espacios")} · reservables: {cifra(reservables)} · '
               f'visitables: {cifra(visitables)}'),
        vacio='La unidad no tiene espacios registrados.')


def _software_y_simuladores(unidad, usos):
    """El software activo y, además, el inactivo que se usó en el período."""
    filas, tipos = [], Counter()
    for programa in _programas(unidad):
        uso = usos.get(programa.pk, (0, 0))
        if not programa.activo and not any(uso):
            continue
        tipos[programa.tipo_recurso] += 1
        filas.append([
            _codigo_y_nombre(programa.codigo, programa.nombre),
            texto(programa.version),
            par(_corto(TIPOS_DE_SOFTWARE, programa.tipo_recurso), '' if programa.activo else 'inactivo'),
            _corto(ACCESOS_A_SOFTWARE, programa.tipo_acceso),
            _licencias(programa),
            _codigos(programa.equipos_existentes),
            _corto(USOS_EN_EQUIPO, programa.uso_en_equipo),
            _celda_de_uso(uso),
        ])
    return Registro(
        'Software y simuladores',
        ('Código / nombre', 'Versión', 'Tipo', 'Acceso', 'Licencias', 'Instalado en', 'Uso en equipo',
         'Uso en el período'),
        filas, pesos=(24, 10, 9, 11, 10, 18, 9, 9),
        total=(f'Total: {plural(len(filas), "programa", "programas")} · software: {cifra(tipos["software"])} · '
               f'licencias: {cifra(tipos["licencia"])} · simuladores: {cifra(tipos["simulador"])}'),
        vacio='La unidad no tiene software ni simuladores registrados.')


def fichas(contexto):
    """Anexo de fichas técnicas (sección 4.4): ficha de la unidad, espacios y talleres, y software y simuladores.

    Los equipos son del anexo de inventario: aquí se citan por su código.
    """
    por_espacio, por_software = _uso_del_periodo(contexto.unidad, contexto.inicio, contexto.fin)
    return [
        _ficha_de_la_unidad(contexto),
        _espacios(contexto, por_espacio),
        _software_y_simuladores(contexto.unidad, por_software),
    ]
