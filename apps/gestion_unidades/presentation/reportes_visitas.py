"""Visitas en los mismos listados, métricas y formatos de las reservas."""

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.reservas.models.reservas import Reserva
from apps.reservas.models.visitas import AsistenteVisita, SolicitudVisita


TIPOS_REPORTE = (*Reserva.TIPO_SOLICITUD_CHOICES, ('visita', 'Visita'))


def reservas_con_visitas(queryset):
    presentes = AsistenteVisita.objects.filter(visita__reserva_id=OuterRef('pk'), asistio=True).order_by().values(
        'visita_id',
    ).annotate(total=Count('pk')).values('total')
    return queryset.select_related('visita').annotate(
        reporte_asistentes_visita=Coalesce(Subquery(presentes, output_field=IntegerField()), Value(0)),
    )


def filtrar_tipo_reporte(queryset, tipo):
    if tipo == 'visita':
        return queryset.filter(visita__isnull=False)
    return queryset.filter(tipo_solicitud=tipo, visita__isnull=True) if tipo else queryset


def reporte_visitas(unidad, inicio, fin, estado='', buscar='', efectividad=''):
    from apps.gestion_unidades.presentation.reportes_alcance import notas_del_reporte
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas, participantes

    consulta = SolicitudVisita.objects.filter(unidad=unidad, reserva__fecha__range=(inicio, fin)).select_related(
        'reserva__usuario', 'guia',
    ).annotate(presentes_reportados=Count('asistentes', filter=Q(asistentes__asistio=True), distinct=True)).prefetch_related(
        'recorrido',
    ).order_by('reserva__fecha', 'reserva__hora_inicio', 'pk')
    if estado in dict(Reserva.ESTADO_CHOICES):
        consulta = consulta.filter(reserva__estado=estado)
    if buscar:
        consulta = consulta.filter(
            Q(institucion__icontains=buscar) | Q(reserva__codigo_reserva__icontains=buscar)
            | Q(reserva__nombre_solicitante__icontains=buscar) | Q(reserva__correo_solicitante__icontains=buscar)
            | Q(reserva__titulo_solicitud__icontains=buscar) | Q(recorrido__nombre__icontains=buscar)
            | Q(guia__first_name__icontains=buscar) | Q(guia__last_name__icontains=buscar)
        ).distinct()
    filas = []
    total = efectivas = previstos = presentes = atendidos = internas = externas = 0
    horas = 0.0
    for visita in consulta.iterator(chunk_size=200):
        reserva = visita.reserva
        efectiva = reserva.es_efectiva
        if (efectividad == 'efectivas' and not efectiva) or (efectividad == 'no_efectivas' and efectiva):
            continue
        reserva.reporte_asistentes_visita = visita.presentes_reportados
        total += 1
        efectivas += int(efectiva)
        previstos += visita.personas
        presentes += visita.presentes_reportados
        internas += int(visita.categoria == 'interna')
        externas += int(visita.categoria == 'externa')
        horas_fila = horas_efectivas(reserva) if efectiva else 0.0
        horas += horas_fila
        atendidos += participantes(reserva) if efectiva else 0
        if len(filas) < 500:
            filas.append([
                reserva.codigo_reserva, f'{reserva.fecha:%d/%m/%Y} · {reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}',
                visita.get_categoria_display(), visita.institucion, reserva.nombre_completo_solicitante,
                visita.get_proposito_display(), ', '.join(area.nombre for area in visita.recorrido.all()) or 'Por coordinar',
                f"{visita.guias_necesarios} requerido{'s' if visita.guias_necesarios != 1 else ''} · " + ((visita.guia.get_full_name() or visita.guia.username) if visita.guia else 'Por asignar'),
                visita.personas, visita.presentes_reportados, reserva.get_estado_display(), round(horas_fila, 1),
            ])
    return {
        'headers': ['Código', 'Fecha y horario', 'Tipo de visita', 'Institución / grupo', 'Responsable', 'Propósito',
                    'Recorrido solicitado', 'Guías', 'Visitantes previstos', 'Presentes registrados', 'Estado', 'Horas efectivas'],
        'rows': filas, 'state_choices': Reserva.ESTADO_CHOICES,
        'cards': [('Solicitudes de visita', total), ('Visitas atendidas', efectivas), ('Horas efectivas', round(horas, 1)),
                  ('Visitantes atendidos', atendidos), ('Visitantes previstos', previstos), ('Presentes registrados', presentes),
                  ('Visitas internas', internas), ('Visitas externas', externas)],
        'truncated': total > len(filas), 'notes': notas_del_reporte('visitas'),
    }
