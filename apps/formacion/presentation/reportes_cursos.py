"""Oferta de formación: catálogo actual y actividad local del período, sin datos personales.

Las lecciones se comparten entre ediciones del mismo curso. Cada curso se
atribuye una sola vez a su unidad propietaria; las reservas no se suman como
cursos ni las inscripciones se presentan como personas únicas.
"""
from datetime import datetime, time, timedelta

from django.core.exceptions import BadRequest
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso

NOTAS_FORMACION = (
    'Cursos y eventos: catálogo actual de la unidad, incluyendo oferta propia y colaboraciones externas. Se conserva el historial de actividades inactivas.',
    'Las actividades externas se identifican por plataforma y organizador; no se atribuyen a la UPEC matrículas, notas o certificados de otras plataformas.',
    'Ediciones iniciadas: fecha de inicio dentro del período; grupos sin inicio no se atribuyen a un día.',
    'Inscripciones: fecha de inscripción dentro del período y estado actual. Una persona puede tener varias.',
    'Certificados: emitidos dentro del período y vigentes ahora; incluye participantes externos de eventos.',
    'Las horas acreditadas suman horas de certificados, no horas lectivas ni personas únicas. Las reservas se informan por separado.',
)


def _ventana(desde, hasta):
    zona = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(desde, time.min), zona),
            timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), zona))


def indicadores_formacion(cursos, desde, hasta, *, por_curso=False):
    """Cuatro agregaciones independientes; evita multiplicar matrículas por certificados."""
    inicio, fin = _ventana(desde, hasta)
    dimension = 'pk' if por_curso else 'unidad_id'
    salida = {}
    for fila in cursos.order_by().values(dimension).annotate(
            cursos=Count('pk'), cursos_publicados=Count('pk', filter=Q(publicado=True, activo=True)),
            cursos_nativos=Count('pk', filter=Q(origen='nativo')),
            cursos_externos=Count('pk', filter=Q(origen='externo'))):
        clave = fila.pop(dimension)
        salida[clave] = {**dict.fromkeys(('ediciones', 'inscripciones', 'aceptadas', 'pendientes',
                                         'certificados', 'horas_acreditadas'), 0), **fila}
    ids = cursos.values('pk')
    grupo = 'curso_id' if por_curso else 'curso__unidad_id'
    for fila in EdicionCurso.objects.filter(curso_id__in=ids, inicio__range=(desde, hasta)).order_by().values(grupo).annotate(ediciones=Count('pk')):
        clave = fila.pop(grupo)
        salida[clave].update(fila)
    grupo = 'edicion__curso_id' if por_curso else 'edicion__curso__unidad_id'
    for fila in InscripcionCurso.objects.filter(edicion__curso_id__in=ids,
            fecha_inscripcion__gte=inicio, fecha_inscripcion__lt=fin).order_by().values(grupo).annotate(
                inscripciones=Count('pk'), aceptadas=Count('pk', filter=Q(estado='aceptada')),
                pendientes=Count('pk', filter=Q(estado='pendiente'))):
        clave = fila.pop(grupo)
        salida[clave].update(fila)
    dimension = Coalesce('inscripcion__edicion__curso_id', 'participante_evento__edicion__curso_id') if por_curso else Coalesce(
        'inscripcion__edicion__curso__unidad_id', 'participante_evento__edicion__curso__unidad_id')
    certificados = CertificadoCurso.objects.filter(
        Q(inscripcion__edicion__curso_id__in=ids) | Q(participante_evento__edicion__curso_id__in=ids),
        anulado=False, emitido_en__gte=inicio, emitido_en__lt=fin)
    for fila in certificados.annotate(agrupacion=dimension).order_by().values('agrupacion').annotate(
            certificados=Count('pk'), horas_acreditadas=Coalesce(Sum('horas'), 0, output_field=CertificadoCurso._meta.get_field('horas'))):
        clave = fila.pop('agrupacion')
        salida[clave].update(fila)
    return salida


def dataset_cursos(unidad, desde, hasta, estado='', buscar=''):
    cursos = Curso.objects.filter(unidad=unidad)
    estados = (('publicado', 'Publicados'), ('borrador', 'Borradores'), ('inactivo', 'Inactivos'))
    if estado == 'inactivo':
        cursos = cursos.filter(activo=False)
    elif estado in ('publicado', 'borrador'):
        cursos = cursos.filter(publicado=estado == 'publicado', activo=True)
    if buscar:
        cursos = cursos.filter(Q(nombre__icontains=buscar) | Q(codigo__icontains=buscar) | Q(entidad_organizadora__icontains=buscar))
    # No producir una descarga aparentemente completa con datos cortados.
    if cursos.count() > 5000:
        raise BadRequest('El reporte supera 5000 cursos. Refina la búsqueda o el estado.')
    indicadores = indicadores_formacion(cursos, desde, hasta, por_curso=True)
    campos = ('cursos', 'cursos_publicados', 'cursos_nativos', 'cursos_externos', 'ediciones', 'inscripciones', 'aceptadas', 'pendientes', 'certificados', 'horas_acreditadas')
    totales = {campo: sum(f.get(campo, 0) for f in indicadores.values()) for campo in campos}
    filas = []
    for curso in cursos.order_by('nombre', 'pk').iterator(chunk_size=200):
        cifras = indicadores[curso.pk]
        estado_actual = 'Inactivo' if not curso.activo else ('Publicado' if curso.publicado else 'Borrador')
        filas.append([curso.codigo, curso.nombre, estado_actual,
            cifras['ediciones'], cifras['inscripciones'], cifras['aceptadas'], cifras['pendientes'],
            cifras['certificados'], cifras['horas_acreditadas'],
            curso.get_origen_display(), curso.entidad_organizadora or unidad.nombre,
            curso.get_participacion_unidad_display()])
    headers = ['Código', 'Curso o evento', 'Estado actual', 'Ediciones iniciadas', 'Inscripciones',
               'Aceptadas', 'Pendientes', 'Certificados vigentes emitidos', 'Horas acreditadas',
               'Plataforma', 'Institución organizadora', 'Participación de la unidad']
    return {'headers': headers, 'rows': filas, 'cards': [
        ('Cursos y eventos', totales['cursos'],
         f"catálogo actual · {totales['cursos_nativos']} propios · {totales['cursos_externos']} externos"),
        ('Ediciones iniciadas', totales['ediciones'], 'inicio en el período'),
        ('Inscripciones', totales['inscripciones'], 'registradas en el período'),
        ('Certificados vigentes', totales['certificados'], 'emitidos en el período')],
        'state_choices': estados, 'column_count': len(headers), 'truncated': False,
        'matrix': False, 'matrix_kind': '', 'structured': False, 'records': [],
        'document_meta': {}, 'notes': NOTAS_FORMACION, 'tablas': []}
