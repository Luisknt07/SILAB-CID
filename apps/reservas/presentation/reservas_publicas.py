"""Catálogo y agenda públicos de una unidad, sin duplicar el motor de reservas."""

from collections import OrderedDict
from datetime import date, time, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, HorarioOperacionUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.reservas.models.reservas import Reserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.operaciones import ventana_atencion

from apps.reservas.presentation.gestion_agenda import _horarios_aplicables_en_fecha
from apps.reservas.presentation.availability import ACTIVE_RESERVATION_STATUSES


def catalogo_servicios_publico(unidad):
    """Servicios visibles agrupados; el asistente continúa siendo la fuente de solicitud."""
    servicios = list(
        FablabService.objects.filter(
            unidad=unidad,
            activo=True,
            publico=True,
        )
        .exclude(tipo_servicio='visita')
        .select_related('responsable', 'responsable__usuario')
        .order_by('familia', 'tipo_servicio', 'code', 'nombre')
    )
    responsable_general = (
        ResponsableUnidad.objects.filter(unidad=unidad, activo=True, publico=True)
        .select_related('usuario')
        .order_by('-recibe_reservas', 'orden', 'id')
        .first()
    )
    familias = OrderedDict()
    for servicio in servicios:
        servicio.responsable_publico = servicio.responsable or responsable_general
        familias.setdefault(servicio.familia_catalogo, []).append(servicio)
    return [
        {'nombre': nombre, 'servicios': elementos}
        for nombre, elementos in familias.items()
    ]


def _hora_superior(valor):
    return valor.hour + bool(valor.minute or valor.second)


def _horas_de(inicio, fin):
    return range(inicio.hour, _hora_superior(fin))


def _se_superponen(inicio_a, fin_a, inicio_b, fin_b):
    return inicio_a < fin_b and fin_a > inicio_b


def agenda_publica(unidad, desde=None, dias=14):
    """Disponibilidad agregada: solo libre o comprometido, sin identidad ni motivo."""
    desde = desde or timezone.localdate()
    hasta = desde + timedelta(days=dias - 1)
    horarios = list(
        HorarioOperacionUnidad.objects.filter(unidad=unidad, activo=True)
        .select_related('periodo')
        .order_by('dia_semana', 'hora_inicio')
    )
    reservas = list(
        Reserva.objects.filter(
            laboratorio=unidad,
            fecha__range=(desde, hasta),
            estado__in=ACTIVE_RESERVATION_STATUSES,
        ).only('fecha', 'hora_inicio', 'hora_fin')
    )
    bloqueos = list(
        BloqueoAgendaUnidad.objects.filter(
            unidad=unidad,
            activo=True,
            fecha_inicio__lte=hasta,
            fecha_fin__gte=desde,
        ).only('fecha_inicio', 'fecha_fin', 'dia_completo', 'hora_inicio', 'hora_fin')
    )
    por_fecha = {}
    for reserva in reservas:
        por_fecha.setdefault(reserva.fecha, []).append(
            (reserva.hora_inicio, reserva.hora_fin)
        )

    configuracion = None
    try:
        configuracion = unidad.configuracion_operativa
    except ObjectDoesNotExist:
        pass
    hora_apertura, hora_cierre = ventana_atencion(configuracion)
    apertura = time(hora_apertura)
    cierre = time(hora_cierre)

    resultado = []
    for desplazamiento in range(dias):
        fecha = desde + timedelta(days=desplazamiento)
        aplicables = _horarios_aplicables_en_fecha(horarios, fecha)
        intervalos = [
            (horario.hora_inicio, horario.hora_fin)
            for horario in aplicables
            if horario.permite_recursos or horario.permite_servicios
        ]
        if not horarios and fecha.weekday() < 5:
            intervalos = [(apertura, cierre)]

        slots_por_hora = OrderedDict()
        for inicio, fin in intervalos:
            for hora in _horas_de(inicio, fin):
                hora_inicio = time(hora)
                hora_fin = time(min(hora + 1, 23), 59, 59) if hora == 23 else time(hora + 1)
                comprometido = any(
                    _se_superponen(hora_inicio, hora_fin, reserva_inicio, reserva_fin)
                    for reserva_inicio, reserva_fin in por_fecha.get(fecha, [])
                )
                if not comprometido:
                    comprometido = any(
                        bloqueo.fecha_inicio <= fecha <= bloqueo.fecha_fin
                        and (
                            bloqueo.dia_completo
                            or _se_superponen(
                                hora_inicio,
                                hora_fin,
                                bloqueo.hora_inicio,
                                bloqueo.hora_fin,
                            )
                        )
                        for bloqueo in bloqueos
                    )
                slots_por_hora[hora] = {
                    'inicio': hora_inicio,
                    'fin': hora_fin,
                    'estado': 'comprometido' if comprometido else 'disponible',
                }
        slots = list(slots_por_hora.values())
        resultado.append({
            'fecha': fecha,
            'slots': slots,
            'habilitado': bool(slots),
            'disponibles': sum(slot['estado'] == 'disponible' for slot in slots),
            'comprometidos': sum(slot['estado'] == 'comprometido' for slot in slots),
        })
    return resultado


def _desde_solicitado(request):
    valor = (request.GET.get('desde') or '').strip()
    try:
        return date.fromisoformat(valor) if valor else timezone.localdate()
    except ValueError:
        return timezone.localdate()


def _contexto_base(unidad):
    return {
        'unidad': unidad,
        'volver_url': f'{unidad.get_absolute_url()}#reservas-servicios',
        'generado_en': timezone.localtime(),
    }


def _numero_de(unidad, clave):
    """El número de la sección en la ficha de esta unidad; vacío si su tipo no tiene mapa."""
    from apps.plantas_piloto.operacion.presentation.secciones_plantas import mapa_de
    mapa = mapa_de(unidad)
    return mapa.numero(clave) if mapa else ''


@xframe_options_sameorigin
def catalogo_servicios_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    familias = catalogo_servicios_publico(unidad)
    return render(request, 'portal/pages/unidades/aula/servicios.html', {
        **_contexto_base(unidad),
        'seccion': _numero_de(unidad, 'servicios'),
        'familias': familias,
        'total_servicios': sum(len(familia['servicios']) for familia in familias),
    })


@xframe_options_sameorigin
def agenda_disponibilidad_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    desde = _desde_solicitado(request)
    agenda = agenda_publica(unidad, desde=desde)
    return render(request, 'portal/pages/unidades/aula/agenda.html', {
        **_contexto_base(unidad),
        'seccion': _numero_de(unidad, 'agenda'),
        'agenda': agenda,
        'desde': desde,
        'hasta': desde + timedelta(days=13),
        'anterior': desde - timedelta(days=14),
        'siguiente': desde + timedelta(days=14),
        'hoy': timezone.localdate(),
        'reservar_url': unidad.get_absolute_url() + '#reservas-servicios',
    })
