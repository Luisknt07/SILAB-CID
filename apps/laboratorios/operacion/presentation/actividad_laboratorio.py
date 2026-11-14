"""Lo que el laboratorio hace con sus reservas y su catálogo: proyectos, colaboración, vinculación y cursos.

Las secciones 6.1, 6.2 y 6.4 del mapa de laboratorio se arman con las reservas aprobadas o
realizadas, agrupadas por la actividad del catálogo a la que pertenecen; la 4.3, con las
actividades de capacitación publicadas. Lo que el solicitante escribió como propósito no se
publica: la ficha muestra el nombre de la actividad, su tipo, la carrera, las sesiones y las
horas, y el responsable solo si la actividad está abierta a la comunidad.
"""
from datetime import datetime

from django.utils import timezone
from django.db.models import Count, F, Window
from django.db.models.functions import RowNumber

from apps.reservas.models.reservas import CatalogoActividadReserva, Reserva
from apps.reservas.workflows.reservas import ESTADOS_APROBADOS

# Clave de sección → (título de la página, propósitos, subtipos). Se clasifica en este orden:
# lo que hace un centro o grupo de investigación primero, luego la vinculación y al final lo formativo.
GRUPOS = {
    'colaboracion_centros': ('Colaboración con centros de I+D', set(),
                             {'proyecto_centro', 'proyecto_investigacion'}),
    'vinculacion': ('Vinculación con la sociedad', {'vinculacion'},
                    {'proyecto_vinculacion', 'transferencia_conocimiento'}),
    'proyectos_formativos': ('Proyectos formativos', {'titulacion'},
                             {'investigacion_formativa', 'trabajo_titulacion', 'proyecto_asignatura',
                              'innovacion_prototipado', 'desarrollo_experimental'}),
}
VISIBILIDADES_ABIERTAS = ('unidad', 'institucional')


def grupo_de(reserva):
    """La sección a la que pertenece una reserva, o '' si es docencia, servicio u otra cosa."""
    for clave, (_titulo, propositos, subtipos) in GRUPOS.items():
        if reserva.subtipo_actividad in subtipos or (reserva.proposito_codigo in propositos and (
                not reserva.subtipo_actividad or clave == 'proyectos_formativos')):
            return clave
    return ''


def _horas(reserva):
    inicio = datetime.combine(reserva.fecha, reserva.hora_inicio)
    fin = datetime.combine(reserva.fecha, reserva.hora_fin)
    return max((fin - inicio).total_seconds() / 3600, 0)


def actividades_de(unidad):
    """Las actividades de la unidad por sección (6.1, 6.2, 6.4), con sesiones y horas, más recientes primero."""
    hoy = timezone.localdate()
    reservas = (
        Reserva.objects.filter(laboratorio=unidad, estado__in=ESTADOS_APROBADOS)
        .select_related('actividad_catalogo')
        .order_by('fecha', 'hora_inicio')
    )
    por_grupo = {clave: {} for clave in GRUPOS}
    for reserva in reservas:
        clave = grupo_de(reserva)
        if not clave:
            continue
        actividad = reserva.actividad_catalogo
        llave = ('actividad', actividad.pk) if actividad else ('tipo', reserva.subtipo_actividad, reserva.carrera_beneficiaria)
        fila = por_grupo[clave].get(llave)
        if fila is None:
            tipo = reserva.get_subtipo_actividad_display() if reserva.subtipo_actividad else (
                reserva.get_proposito_codigo_display())
            abierta = actividad is not None and actividad.visibilidad in VISIBILIDADES_ABIERTAS
            fila = por_grupo[clave][llave] = {
                'nombre': actividad.nombre if abierta else tipo,
                'tipo': tipo,
                'carrera': (actividad.get_carrera_display() if actividad and actividad.carrera
                            else reserva.get_carrera_beneficiaria_display() if reserva.carrera_beneficiaria else ''),
                'responsable': actividad.responsable if abierta else '',
                'sesiones': 0, 'horas': 0.0, 'desde': reserva.fecha, 'hasta': reserva.fecha, 'en_curso': False,
            }
        fila['sesiones'] += 1
        fila['horas'] += _horas(reserva)
        fila['hasta'] = reserva.fecha
        fila['en_curso'] = fila['en_curso'] or reserva.fecha >= hoy
    return {
        clave: sorted(filas.values(), key=lambda fila: fila['hasta'], reverse=True)
        for clave, filas in por_grupo.items()
    }


def consulta_cursos_de(unidad):
    """Consulta pública reutilizable antes de contar o paginar las actividades."""
    return CatalogoActividadReserva.objects.filter(
        unidad=unidad, proposito_codigo='capacitacion', estado_publicacion='publicado',
        visibilidad__in=VISIBILIDADES_ABIERTAS, activo=True,
    ).order_by('nombre', 'pk')


def completar_cursos_de(cursos):
    """Dos consultas de resumen para una página, sin una consulta por tarjeta."""
    cursos = list(cursos)
    if not cursos:
        return cursos
    hoy = timezone.localdate()
    ids = [curso.pk for curso in cursos]
    proximas = (Reserva.objects.filter(actividad_catalogo_id__in=ids, estado__in=ESTADOS_APROBADOS, fecha__gte=hoy)
                .annotate(_siguiente=Window(RowNumber(), partition_by=[F('actividad_catalogo_id')],
                                           order_by=['fecha', 'hora_inicio', 'pk']))
                .filter(_siguiente=1).order_by())
    siguientes = {reserva.actividad_catalogo_id: reserva for reserva in proximas}
    realizadas = dict(Reserva.objects.filter(actividad_catalogo_id__in=ids, estado='completada')
                      .order_by().values('actividad_catalogo_id').annotate(total=Count('pk'))
                      .values_list('actividad_catalogo_id', 'total'))
    for curso in cursos:
        curso.proxima_sesion = siguientes.get(curso.pk)
        curso.sesiones_realizadas = realizadas.get(curso.pk, 0)
    return cursos


def cursos_de(unidad):
    """Compatibilidad: catálogo completo cuando una superficie necesita todos sus recursos."""
    return completar_cursos_de(consulta_cursos_de(unidad))
