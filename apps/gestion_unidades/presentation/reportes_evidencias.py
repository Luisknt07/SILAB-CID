"""Reportes de evidencia que salen de lo que la unidad ya registra.

Guías de práctica, seguridad y acceso, transferencia y servicios, préstamos
de equipos y la disponibilidad de cada equipo en el período. Ninguno crea datos: leen las
tablas que el resto de la consola ya llena y las devuelven con la forma del
Centro de reportes (cabeceras, filas, tarjetas y estados filtrables).
"""

from collections import defaultdict
from datetime import datetime, time, timedelta
from heapq import nsmallest

from django.db.models import Count, Prefetch, Q, Sum
from django.utils import timezone

from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.recursos.models.desechos import RegistroDesecho
from apps.laboratorios.operacion.models.fablab import SolicitudFabricacion
from apps.recursos.models.unidades import UnidadEquipo
from apps.directorio_unidades.models.core import Unidad

# Estados de un activo en los que no está para usarse.
ESTADOS_FUERA_DE_SERVICIO = ('mantenimiento', 'dañado', 'no_disponible', 'obsoleto', 'no_localizado')

# Propósitos de una reserva que cuentan como transferencia hacia afuera de la
# docencia: servicios, vinculación y capacitación.
PROPOSITOS_TRANSFERENCIA = ('servicio_cientifico_tecnologico', 'vinculacion', 'capacitacion')
# Y los que cuentan como investigación aplicada, desarrollo y titulación.
PROPOSITOS_INVESTIGACION = ('investigacion_innovacion', 'titulacion')


def _nombre(usuario):
    if not usuario:
        return '—'
    return usuario.get_full_name() or usuario.get_username()


# -- Guías de práctica --------------------------------------------------------

def guias_del_periodo(unidades, start_date, end_date):
    return GuiaActividadReserva.objects.filter(actividad__unidad__in=unidades, activo=True).filter(
        Q(actualizado_en__date__range=(start_date, end_date)) | Q(es_vigente=True))


def reporte_guias(unit, start_date, end_date, state='', search=''):
    """Cada guía con su versión vigente, su estado y la asignatura a la que responde.

    Se toman las guías actualizadas en el período; las vigentes se listan
    aunque no cambiaran, porque la evidencia pide las aprobadas, no las nuevas.
    """
    state_choices = GuiaActividadReserva._meta.get_field('estado_publicacion').choices
    queryset = (
        guias_del_periodo([unit], start_date, end_date)
        .select_related('actividad', 'aprobado_por', 'revisado_por', 'familia')
        .prefetch_related('planificaciones_practica__tema_asignatura__asignatura')
        .order_by('actividad__nombre', 'titulo', '-numero_version')
    )
    if state in dict(state_choices):
        queryset = queryset.filter(estado_publicacion=state)
    if search:
        queryset = queryset.filter(
            Q(titulo__icontains=search) | Q(codigo_guia__icontains=search)
            | Q(actividad__nombre__icontains=search)
            | Q(planificaciones_practica__tema_asignatura__asignatura__nombre__icontains=search)
        ).distinct()
    headers = ['Código', 'Guía', 'Versión', 'Actividad', 'Asignatura / tema (syllabus)',
               'Estado', 'Aprobada por', 'Descarga pública']
    rows = []
    for guia in queryset[:501]:
        temas = {
            f'{plan.tema_asignatura.asignatura.nombre} · {plan.tema_asignatura.nombre}'
            for plan in guia.planificaciones_practica.all() if plan.tema_asignatura_id
        }
        rows.append([
            guia.codigo_guia or '—', guia.titulo,
            f'v{guia.numero_version}' + (' (vigente)' if guia.es_vigente else ''),
            guia.actividad.nombre,
            '; '.join(sorted(temas)) or 'Sin vincular',
            guia.get_estado_publicacion_display(),
            _nombre(guia.aprobado_por) if guia.aprobado_por_id else '—',
            'Sí' if guia.permite_descarga else 'No',
        ])
    cards = [
        ('Guías', queryset.count()),
        ('Publicadas', queryset.filter(estado_publicacion='publicada').count()),
        ('En revisión', queryset.filter(estado_publicacion='revision').count()),
        ('Vinculadas al syllabus',
         queryset.filter(planificaciones_practica__tema_asignatura__isnull=False).distinct().count()),
    ]
    return headers, rows, cards, state_choices


# -- Seguridad y acceso -------------------------------------------------------

def reporte_seguridad(unit, start_date, end_date, state='', search=''):
    """Ingresos con y sin protección, rechazos, habilitaciones vigentes y vencidas."""
    state_choices = (('ingreso', 'Ingresó'), ('rechazo', 'No ingresó'))
    ingresos = (
        RegistroIngreso.objects.filter(
            reserva__laboratorio=unit, reserva__fecha__range=(start_date, end_date),
        )
        .select_related('reserva', 'usuario', 'registrado_por')
        .order_by('reserva__fecha', 'hora_ingreso', 'pk')
    )
    if state == 'ingreso':
        ingresos = ingresos.filter(ingresa=True)
    elif state == 'rechazo':
        ingresos = ingresos.filter(ingresa=False)
    if search:
        ingresos = ingresos.filter(
            Q(nombre__icontains=search) | Q(motivo__icontains=search)
            | Q(reserva__codigo_reserva__icontains=search)
            | Q(usuario__username__icontains=search)
        )
    headers = ['Fecha', 'Reserva', 'Persona', 'Categoría', 'Ingresó', 'Protección verificada',
               'Restricciones verificadas', 'Pendientes', 'Motivo', 'Registró']
    rows = []
    for registro in ingresos[:501]:
        rows.append([
            registro.reserva.fecha.strftime('%d/%m/%Y')
            + (f' {registro.hora_ingreso:%H:%M}' if registro.hora_ingreso else ''),
            registro.reserva.codigo_reserva or '—',
            registro.nombre or _nombre(registro.usuario),
            registro.get_categoria_display(),
            'Sí' if registro.ingresa else 'No',
            'Sí' if registro.proteccion_verificada else 'No',
            'Sí' if registro.restricciones_verificadas else 'No',
            ', '.join(registro.pendientes) if isinstance(registro.pendientes, list) else (registro.pendientes or '—'),
            registro.motivo or '—',
            _nombre(registro.registrado_por),
        ])
    requisitos = RequisitoAcceso.objects.filter(unidad=unit, activo=True)
    habilitaciones = HabilitacionAcceso.objects.filter(requisito__unidad=unit, activa=True)
    hoy = end_date
    vigentes = habilitaciones.filter(fecha__lte=hoy).filter(
        Q(vence__isnull=True) | Q(vence__gte=hoy)
    ).count()
    cards = [
        ('Ingresos registrados', ingresos.filter(ingresa=True).count()),
        ('No ingresaron', ingresos.filter(ingresa=False).count()),
        ('Requisitos activos', requisitos.count()),
        ('Habilitaciones vigentes', vigentes, f'de {habilitaciones.count()} otorgadas'),
    ]
    return headers, rows, cards, state_choices


# -- Transferencia y servicios ------------------------------------------------

def reporte_transferencia(unit, start_date, end_date, state='', search=''):
    """Servicios prestados y reservas con propósito de transferencia, en una sola lectura."""
    state_choices = (
        ('servicios', 'Solicitudes de servicio'),
        ('reservas', 'Reservas de vinculación, capacitación o servicio'),
    )
    servicios = (
        SolicitudFabricacion.objects.filter(unidad=unit, fecha_solicitud__range=(start_date, end_date))
        .select_related('solicitante', 'responsable_asignado')
        .order_by('fecha_solicitud', 'pk')
    )
    reservas = (
        Reserva.objects.filter(
            laboratorio=unit, fecha__range=(start_date, end_date),
            proposito_codigo__in=PROPOSITOS_TRANSFERENCIA,
        )
        .select_related('usuario')
        .order_by('fecha', 'hora_inicio', 'pk')
    )
    if search:
        servicios = servicios.filter(
            Q(nombre_proyecto__icontains=search) | Q(departamento__icontains=search)
            | Q(solicitante__username__icontains=search) | Q(solicitante__first_name__icontains=search)
            | Q(solicitante__last_name__icontains=search)
        )
        reservas = reservas.filter(
            Q(titulo_solicitud__icontains=search) | Q(nombre_solicitante__icontains=search)
            | Q(institucion__icontains=search) | Q(codigo_reserva__icontains=search)
        )
    headers = ['Fecha', 'Tipo', 'Referencia', 'Beneficiario', 'Institución / departamento',
               'Propósito', 'Estado', 'Horas / tiempo']
    rows = []
    if state != 'reservas':
        for item in servicios[:501]:
            rows.append([
                item.fecha_solicitud.strftime('%d/%m/%Y'),
                'Servicio',
                item.nombre_proyecto or '—',
                _nombre(item.solicitante),
                item.departamento or '—',
                item.get_tipo_trabajo_display(),
                item.get_estado_display(),
                f'{item.tiempo_estimado_horas} h' if item.tiempo_estimado_horas else '—',
            ])
    if state != 'servicios':
        for reserva in reservas[:501]:
            rows.append([
                reserva.fecha.strftime('%d/%m/%Y'),
                'Reserva',
                reserva.codigo_reserva or reserva.titulo_solicitud,
                reserva.nombre_solicitante or _nombre(reserva.usuario),
                reserva.institucion or '—',
                reserva.get_proposito_codigo_display(),
                reserva.get_estado_display(),
                f'{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}',
            ])
    rows.sort(key=lambda fila: datetime.strptime(fila[0], '%d/%m/%Y'))
    # Cada fuente ya está ordenada por fecha: ninguna fila posterior a la 501
    # puede pertenecer a las primeras 501 de la combinación. Los conteos siguen
    # usando los querysets completos y el presentador advierte el límite500.
    rows = rows[:501]
    externos = reservas.filter(tipo_usuario_solicitante='externo').count()
    cards = [
        ('Servicios solicitados', servicios.count()),
        ('Servicios completados', servicios.filter(estado='completada').count()),
        ('Reservas de transferencia', reservas.count()),
        ('Beneficiarios externos', externos, 'solicitantes externos'),
    ]
    return headers, rows, cards, state_choices


# -- Disponibilidad de equipos en el período ----------------------------------

def disponibilidad_por_equipo(unit, start_date, end_date):
    """Días disponible y fuera de servicio de cada activo, desde su ciclo de vida.

    Reconstruye el estado día a día con los cambios registrados: el estado al
    inicio es el anterior al primer cambio del período o, sin cambios, el
    actual. Devuelve {equipo_id: (porcentaje, dias_fuera)}.
    """
    return disponibilidad_de_unidades([unit], start_date, end_date)[unit.pk]


def disponibilidad_de_unidades(unidades, start_date, end_date):
    """El mismo cálculo para todo el consolidado, cargando activos y eventos una vez."""
    ids = {unidad.pk for unidad in unidades}
    if not ids:
        return {}
    zona = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(start_date, time.min), zona)
    fin = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), zona)
    total = (fin - inicio).total_seconds()
    if total <= 0:
        return {pk: {} for pk in ids}
    activos = list(UnidadEquipo.objects.filter(
        Q(laboratorio_id__in=ids) | Q(laboratorios__pk__in=ids)).distinct().prefetch_related(
            Prefetch('laboratorios', queryset=Unidad.objects.filter(pk__in=ids).only('pk'),
                     to_attr='unidades_del_reporte')))
    eventos = defaultdict(list)
    consulta = (
        EventoCicloVidaEquipo.objects.filter(equipo__in=activos, tipo='cambio_estado', fecha__lt=fin)
        .order_by('fecha', 'pk').values_list('equipo_id', 'fecha', 'estado_anterior', 'estado_nuevo')
    )
    for equipo_id, fecha, anterior, nuevo in consulta:
        eventos[equipo_id].append((fecha, anterior, nuevo))
    resultado = {}
    for activo in activos:
        cambios = eventos.get(activo.pk, [])
        previos = [c for c in cambios if c[0] < inicio]
        del_periodo = [c for c in cambios if c[0] >= inicio]
        if previos:
            estado = previos[-1][2]
        elif del_periodo:
            estado = del_periodo[0][1] or activo.estado_unidad
        else:
            estado = activo.estado_unidad
        cursor, fuera = inicio, 0.0
        for fecha, _anterior, nuevo in del_periodo:
            if estado in ESTADOS_FUERA_DE_SERVICIO:
                fuera += (fecha - cursor).total_seconds()
            cursor, estado = fecha, nuevo
        if estado in ESTADOS_FUERA_DE_SERVICIO:
            fuera += (fin - cursor).total_seconds()
        porcentaje = round(100 * (1 - fuera / total), 1)
        resultado[activo.pk] = (porcentaje, round(fuera / 86400, 1))
    por_unidad = {pk: {} for pk in ids}
    for activo in activos:
        compartidas = {unidad.pk for unidad in activo.unidades_del_reporte} | {activo.laboratorio_id}
        for unidad_id in compartidas & ids:
            por_unidad[unidad_id][activo.pk] = resultado[activo.pk]
    return por_unidad


# -- Desechos peligrosos y especiales -----------------------------------------

def reporte_desechos(unit, start_date, end_date, state='', search=''):
    """Cada generación o entrega de desecho con su clase, clave, cantidad y manifiesto."""
    state_choices = RegistroDesecho.ETAPAS
    queryset = (
        RegistroDesecho.objects.filter(unidad=unit, fecha_generacion__range=(start_date, end_date))
        .select_related('responsable')
        .order_by('fecha_generacion', 'pk')
    )
    if state in dict(state_choices):
        queryset = queryset.filter(etapa=state)
    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search) | Q(clave_listado__icontains=search) | Q(origen__icontains=search)
            | Q(gestor_autorizado__icontains=search) | Q(manifiesto__icontains=search)
        )
    headers = ['Fecha', 'Desecho', 'Clase', 'Clave del listado', 'Origen', 'Estado físico', 'Cantidad',
               'Envase', 'Etiquetado', 'Etapa', 'Fecha de entrega', 'Gestor autorizado', 'Manifiesto',
               'Responsable']
    rows = []
    for item in queryset[:501]:
        rows.append([
            item.fecha_generacion.strftime('%d/%m/%Y'), item.nombre, item.get_clase_display(),
            item.clave_listado or '—', item.origen or '—', item.get_estado_fisico_display(),
            f'{item.cantidad:g} {item.get_unidad_medida_display()}', item.envase or '—',
            'Sí' if item.etiquetado else 'No', item.get_etapa_display(),
            item.fecha_entrega.strftime('%d/%m/%Y') if item.fecha_entrega else '—',
            item.gestor_autorizado or '—', item.manifiesto or '—', _nombre(item.responsable),
        ])
    totales = queryset.aggregate(
        total=Count('pk'), entregados=Count('pk', filter=Q(etapa='entregado')),
        almacenados=Count('pk', filter=Q(etapa='almacenado')),
        kilos=Sum('cantidad', filter=Q(unidad_medida='kg')),
    )
    kilos = totales['kilos'] or 0
    cards = [
        ('Registros', totales['total']),
        ('Entregados a gestor', totales['entregados']),
        ('Almacenados sin entregar', totales['almacenados']),
        ('Kilogramos registrados', f'{kilos:g}', 'solo lo medido en kg'),
    ]
    return headers, rows, cards, state_choices


# -- Equipamiento: disponibilidad y funcionalidad -----------------------------

def reporte_equipamiento(unit, start_date, end_date, state='', search=''):
    """Cada equipo con su estado, su disponibilidad en el período y lo que le pasó."""
    state_choices = UnidadEquipo._meta.get_field('estado_unidad').choices
    # Una referencia (inactiva y sin baja) no existe: no se reporta ni suma disponibilidad.
    equipos = (
        UnidadEquipo.objects.filter(Q(laboratorio=unit) | Q(laboratorios=unit))
        .exclude(activa=False, fecha_baja__isnull=True)
        .select_related('equipo').distinct().order_by('codigo_unidad')
    )
    if state in dict(state_choices):
        equipos = equipos.filter(estado_unidad=state)
    if search:
        equipos = equipos.filter(
            Q(codigo_unidad__icontains=search) | Q(equipo__nombre__icontains=search)
            | Q(ubicacion_especifica__icontains=search)
        )
    disponibilidad = disponibilidad_por_equipo(unit, start_date, end_date)
    mantenimientos = MantenimientoEquipo.objects.filter(
        equipo__in=equipos, fecha_programada__date__range=(start_date, end_date))
    incidencias = IncidenciaEquipo.objects.filter(
        equipo__in=equipos, fecha_reporte__date__range=(start_date, end_date))
    detalle_equipos = list(equipos[:501])
    por_equipo_mant = {
        fila['equipo_id']: (fila['total'], fila['completados'])
        for fila in mantenimientos.filter(equipo__in=detalle_equipos).order_by().values('equipo_id').annotate(
            total=Count('pk'), completados=Count('pk', filter=Q(estado='completado')))
    }
    por_equipo_inc = {
        fila['equipo_id']: fila['total']
        for fila in incidencias.filter(equipo__in=detalle_equipos).order_by().values('equipo_id').annotate(total=Count('pk'))
    }
    headers = ['Código', 'Equipo', 'Ubicación', 'Estado actual', 'Disponible en el período',
               'Días fuera de servicio', 'Mantenimientos (completados)', 'Incidencias',
               'Próximo mantenimiento']
    rows = []
    for item in detalle_equipos:
        porcentaje, dias_fuera = disponibilidad.get(item.pk, (100.0, 0.0))
        programados, completados = por_equipo_mant.get(item.pk, (0, 0))
        rows.append([
            item.codigo_unidad, item.equipo.nombre, item.ubicacion_especifica or '—',
            item.get_estado_unidad_display(), f'{porcentaje:.1f} %', f'{dias_fuera:.1f}',
            f'{programados} ({completados})', por_equipo_inc.get(item.pk, 0),
            item.proximo_mantenimiento.strftime('%d/%m/%Y') if item.proximo_mantenimiento else '—',
        ])
    cantidad_equipos = equipos.count()
    suma_porcentajes = sum(
        disponibilidad.get(pk, (100.0, 0.0))[0]
        for pk in equipos.values_list('pk', flat=True).iterator(chunk_size=200)
    )
    media = round(suma_porcentajes / cantidad_equipos, 1) if cantidad_equipos else None
    cards = [
        ('Equipos', cantidad_equipos),
        ('Disponibilidad media', f'{media:.1f} %' if media is not None else 'Sin medición',
         'del período' if media is not None else 'sin equipos en la selección'),
        ('Fuera de servicio hoy', equipos.filter(estado_unidad__in=ESTADOS_FUERA_DE_SERVICIO).count()),
        ('Incidencias en el período', incidencias.count()),
    ]
    return headers, rows, cards, state_choices


# -- Investigación aplicada y desarrollo tecnológico --------------------------

def reporte_investigacion(unit, start_date, end_date, state='', search=''):
    """Uso de la unidad con fines de investigación, desarrollo y titulación.

    Los resultados (prototipos, publicaciones, informes técnicos) no tienen
    registro todavía; lo que sí se demuestra es qué se hizo, quién y cuánto.
    """
    state_choices = Reserva.ESTADO_CHOICES
    reservas = (
        Reserva.objects.filter(
            laboratorio=unit, fecha__range=(start_date, end_date),
            proposito_codigo__in=PROPOSITOS_INVESTIGACION,
        )
        .select_related('usuario', 'actividad_catalogo')
        .order_by('fecha', 'hora_inicio', 'pk')
    )
    if state in dict(state_choices):
        reservas = reservas.filter(estado=state)
    servicios = SolicitudFabricacion.objects.filter(
        unidad=unit, tipo_trabajo='investigacion', fecha_solicitud__range=(start_date, end_date),
    ).select_related('solicitante').order_by('-fecha_solicitud', 'pk')
    if search:
        reservas = reservas.filter(
            Q(titulo_solicitud__icontains=search) | Q(nombre_solicitante__icontains=search)
            | Q(codigo_reserva__icontains=search) | Q(carrera_solicitante__icontains=search)
            | Q(actividad_catalogo__nombre__icontains=search)
        )
        servicios = servicios.filter(Q(nombre_proyecto__icontains=search) | Q(departamento__icontains=search))
    headers = ['Fecha', 'Tipo', 'Referencia', 'Propósito', 'Investigador o estudiante', 'Carrera / programa',
               'Estado', 'Horas']
    rows = []
    for reserva in reservas[:501]:
        rows.append([
            reserva.fecha.strftime('%d/%m/%Y'), 'Reserva', reserva.codigo_reserva or reserva.titulo_solicitud,
            reserva.get_proposito_codigo_display(), reserva.nombre_solicitante or _nombre(reserva.usuario),
            reserva.carrera_solicitante or reserva.facultad_solicitante or '—', reserva.get_estado_display(),
            f'{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}',
        ])
    if state == '':
        def filas_servicios():
            for item in servicios.iterator(chunk_size=200):
                yield [
                    item.fecha_solicitud.strftime('%d/%m/%Y'), 'Servicio de fabricación', item.nombre_proyecto or '—',
                    item.get_tipo_trabajo_display(), _nombre(item.solicitante), item.departamento or '—',
                    item.get_estado_display(), f'{item.tiempo_estimado_horas} h' if item.tiempo_estimado_horas else '—',
                ]
        # La fuente histórica tiene orden descendente; conservar sus empates al
        # ordenar por fecha requiere recorrerla, pero no retener todas las filas.
        rows.extend(nsmallest(501, filas_servicios(), key=lambda fila: datetime.strptime(fila[0], '%d/%m/%Y')))
    rows.sort(key=lambda fila: datetime.strptime(fila[0], '%d/%m/%Y'))
    rows = rows[:501]
    cards = [
        ('Reservas de investigación', reservas.filter(proposito_codigo='investigacion_innovacion').count()),
        ('Reservas de titulación', reservas.filter(proposito_codigo='titulacion').count()),
        ('Servicios para investigación', servicios.count()),
        ('Investigadores distintos', reservas.values('usuario_id').distinct().count()),
    ]
    return headers, rows, cards, state_choices


# -- Préstamos: quién retira el equipo y cuándo lo devuelve --------------------

def reporte_prestamos(unit, start_date, end_date, state='', search=''):
    """Cada salida del equipo con su responsable, su plazo y su retorno.

    Es una consulta de gestión: el préstamo no tiene meta y ya no viaja como
    anexo del informe. Sale de lo que la unidad registra al entregar y al recibir.
    """
    state_choices = PrestamoEquipo.ESTADOS
    queryset = (
        PrestamoEquipo.objects.filter(unidad=unit, fecha_salida__date__range=(start_date, end_date))
        .select_related('equipo', 'equipo__equipo', 'solicitante', 'entregado_por', 'recibido_por')
        .order_by('fecha_salida', 'pk')
    )
    if state in dict(state_choices):
        queryset = queryset.filter(estado=state)
    if search:
        queryset = queryset.filter(
            Q(codigo__icontains=search) | Q(equipo__codigo_unidad__icontains=search)
            | Q(equipo__equipo__nombre__icontains=search) | Q(nombre_solicitante__icontains=search)
            | Q(institucion__icontains=search) | Q(proposito__icontains=search)
        )
    headers = ['Código', 'Equipo', 'Tipo', 'Quién retira', 'Institución o área', 'Autoriza',
               'Propósito', 'Salida', 'Retorno previsto', 'Retorno real', 'Días fuera',
               'Condición de salida', 'Condición de retorno', 'Acta', 'Estado']
    rows = []
    for item in queryset[:501]:
        rows.append([
            item.codigo,
            f'{item.equipo.codigo_unidad} · {item.equipo.equipo.nombre}',
            item.get_tipo_display().split(':')[0],
            item.quien_retira,
            item.institucion or '—',
            item.autorizado_por or '—',
            item.proposito,
            timezone.localtime(item.fecha_salida).strftime('%d/%m/%Y %H:%M'),
            timezone.localtime(item.fecha_retorno_previsto).strftime('%d/%m/%Y'),
            timezone.localtime(item.fecha_retorno_real).strftime('%d/%m/%Y') if item.fecha_retorno_real else '—',
            item.dias_fuera,
            item.get_condicion_salida_display(),
            item.get_condicion_retorno_display() if item.condicion_retorno else '—',
            'Sí' if item.acta else 'No',
            'Vencido sin devolver' if item.vencido else item.get_estado_display(),
        ])
    afuera = Q(estado__in=PrestamoEquipo.ESTADOS_FUERA)
    totales = queryset.aggregate(
        total=Count('pk'), externos=Count('pk', filter=Q(tipo='externo')),
        afuera=Count('pk', filter=afuera),
        vencidos=Count('pk', filter=afuera & Q(fecha_retorno_previsto__lt=timezone.now())),
        sin_acta=Count('pk', filter=Q(tipo='externo') & (Q(acta='') | Q(acta__isnull=True))),
        devueltos=Count('pk', filter=Q(estado='devuelto')),
        con_novedad=Count('pk', filter=Q(estado='devuelto', condicion_retorno__in={'observado', 'danado'})),
    )
    cards = [
        ('Préstamos del período', totales['total'], f'{totales["externos"]} externos'),
        ('Equipos fuera ahora', totales['afuera'],
         f'{totales["vencidos"]} vencidos sin devolver' if totales['vencidos'] else 'ninguno vencido'),
        ('Externos sin acta', totales['sin_acta'], 'la salida exige respaldo firmado'),
        ('Devueltos con novedad', totales['con_novedad'], f'sobre {totales["devueltos"]} devueltos'),
    ]
    return headers, rows, cards, state_choices
