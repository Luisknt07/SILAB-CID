"""Seguimiento académico por inscripción: cada edición conserva su propio avance.

No crea certificados ni modifica notas. Los aprobados de intentos históricos se
respetan tal como se guardaron; cambiar hoy el mínimo no recalifica el pasado.
"""
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.formacion.models.cursos import Curso, InscripcionCurso
from apps.directorio_unidades.models.core import Unidad

from apps.formacion.presentation.aula_cursos import avance, lecciones_de, marcar_avance
from apps.formacion.presentation.notas_cursos import nota_sobre_diez
from apps.formacion.presentation.cursos import puede_crear_cursos


def nombre_inscrito(inscripcion):
    return (getattr(inscripcion, 'nombres_completos', '') or inscripcion.usuario.get_full_name()
            or inscripcion.usuario.get_username())


def url_del_grupo(nombre, curso, edicion_id, *extra):
    """Enlaces del aula conservan la cohorte; nunca sustituyen una por la vigente."""
    return reverse(nombre, args=[curso.unidad.slug, curso.codigo, *extra]) + '?' + urlencode({'edicion': edicion_id})


def seguimiento_de(inscripcion, modulos=None):
    """Resumen reutilizable de una inscripción, con notas /10 y cada intento.

    El llamador debe comprobar la propiedad o permiso de gestión. Para listados,
    precargue usuario, edicion__curso__unidad, progresos, intentos, entregas y
    certificados. Devuelve estado aprobado/reprobado/pendiente, actividades,
    módulos, avance y estado del certificado. Un deber devuelto permite corregir;
    sólo las evaluaciones agotadas o vencidas cierran oportunidades de aprobación.
    """
    curso = inscripcion.edicion.curso
    modulos = modulos if modulos is not None else lecciones_de(curso)
    hechas = {progreso.leccion_id for progreso in inscripcion.progresos.all()}
    progreso = avance(curso, inscripcion, modulos, hechas)
    marcar_avance(modulos, hechas)
    por_leccion = {}
    for intento in sorted(inscripcion.intentos.all(), key=lambda propio: (propio.entregado_en, propio.pk)):
        por_leccion.setdefault(intento.leccion_id, []).append(intento)
    entregas = {entrega.leccion_id: entrega for entrega in inscripcion.entregas.all()}
    bloques, calificadas, todas = [], [], []
    for modulo in modulos:
        filas = []
        for leccion in modulo.visibles:
            if not leccion.publicada:
                continue
            fila = {'leccion': leccion, 'obligatoria': leccion.obligatoria,
                    'url': url_del_grupo('aula_curso_leccion', curso, inscripcion.edicion_id, leccion.pk),
                    'completada': leccion.pk in hechas, 'nota': None, 'nota_10': None,
                    'minima_10': nota_sobre_diez(leccion.nota_minima),
                    'intentos': [], 'usados': None, 'restantes': None,
                    'limite': leccion.intentos, 'bloqueada': leccion.bloqueada,
                    'aprobado': leccion.pk in hechas, 'cerrada_sin_aprobar': False,
                    'estado': 'completada' if leccion.pk in hechas else 'pendiente',
                    'rotulo': 'Completada' if leccion.pk in hechas else 'Pendiente'}
            if leccion.tipo == 'evaluacion':
                propios = por_leccion.get(leccion.pk, [])
                fila['intentos'] = [{'numero': numero, 'nota': intento.nota,
                                     'nota_10': nota_sobre_diez(intento.nota),
                                     'aprobado': intento.aprobado, 'fecha': intento.entregado_en}
                                    for numero, intento in enumerate(propios, 1)]
                fila['nota'] = max((intento.nota for intento in propios), default=None)
                fila['nota_10'] = nota_sobre_diez(fila['nota'])
                fila['usados'] = len(propios)
                fila['restantes'] = max(leccion.intentos - len(propios), 0)
                fila['aprobado'] = any(intento.aprobado for intento in propios)
                fila['cerrada_sin_aprobar'] = not fila['aprobado'] and (fila['restantes'] == 0 or leccion.vencida())
                if fila['aprobado']:
                    fila['estado'], fila['rotulo'] = 'aprobada', 'Aprobada'
                elif fila['cerrada_sin_aprobar']:
                    fila['estado'], fila['rotulo'] = 'reprobada', ('Plazo terminado' if leccion.vencida() else 'Intentos agotados')
                elif fila['bloqueada']:
                    fila['estado'], fila['rotulo'] = 'bloqueada', 'Completar lecciones anteriores'
                else:
                    fila['estado'], fila['rotulo'] = 'pendiente', ('Puede reintentar' if propios else 'Por rendir')
            elif leccion.tipo == 'deber':
                entrega = entregas.get(leccion.pk)
                fila['entrega'] = entrega
                fila['nota'] = entrega.nota if entrega else None
                fila['nota_10'] = nota_sobre_diez(fila['nota'])
                fila['aprobado'] = bool(entrega and entrega.estado == 'aprobada')
                fila['estado'], fila['rotulo'] = ({'aprobada': ('aprobada', 'Aprobada'),
                    'entregada': ('revision', 'Por revisar'),
                    'devuelta': ('corregir', 'Corregir y volver a entregar')}.get(entrega.estado)
                    if entrega else ('pendiente', 'Sin entregar'))
            if leccion.calificada:
                calificadas.append(fila)
            filas.append(fila)
            todas.append(fila)
        bloques.append({'modulo': modulo, 'actividades': filas})
    aprobado = bool(progreso['total'] and progreso['completadas'] == progreso['total'])
    reprobado = any(fila['obligatoria'] and fila['cerrada_sin_aprobar'] for fila in calificadas)
    estado = 'aprobado' if aprobado else 'reprobado' if reprobado else 'pendiente'
    obligatorias = [fila for fila in calificadas if fila['obligatoria']]
    notas = [fila['nota'] for fila in obligatorias if fila['nota'] is not None]
    promedio = (sum(notas) / Decimal(len(notas))).quantize(Decimal('0.01')) if notas else None
    certificados = list(inscripcion.certificados.all())
    certificado = next((propio for propio in certificados if not propio.anulado), None)
    if certificado:
        certificado_estado, certificado_rotulo = 'emitido', 'Disponible'
    elif any(propio.anulado for propio in certificados):
        certificado_estado, certificado_rotulo = 'anulado', 'Anulado: consultar con la unidad'
    elif not curso.emite_certificado:
        certificado_estado, certificado_rotulo = 'no_ofrece', 'Este curso no emite certificado'
    elif aprobado and inscripcion.estado == 'aceptada':
        certificado_estado, certificado_rotulo = 'listo', 'Requisitos completos: ingresar al aula'
    else:
        certificado_estado, certificado_rotulo = 'pendiente', 'Pendiente de completar los requisitos'
    return {'inscripcion': inscripcion, 'nombre': nombre_inscrito(inscripcion),
            'documento': getattr(inscripcion, 'documento', '') or '', 'avance': progreso,
            'estado_inscripcion': inscripcion.estado, 'inscripcion_rotulo': inscripcion.get_estado_display(),
            'acceso_aula': inscripcion.estado == 'aceptada' and curso.publicado and curso.unidad.activo,
            'modulos': bloques, 'actividades': todas, 'calificadas': calificadas,
            'estado': estado, 'rotulo': {'aprobado': 'Aprobado', 'reprobado': 'Reprobado', 'pendiente': 'Pendiente'}[estado],
            'promedio': promedio, 'promedio_10': nota_sobre_diez(promedio),
            'promedio_completo': bool(obligatorias) and len(notas) == len(obligatorias),
            'intentos_usados': sum(fila['usados'] or 0 for fila in calificadas),
            'oportunidades': sum(fila['restantes'] or 0 for fila in calificadas
                                 if not fila['aprobado'] and not fila['cerrada_sin_aprobar']),
            'tiene_agotadas': any(fila['cerrada_sin_aprobar'] for fila in calificadas),
            'certificado': certificado, 'certificado_estado': certificado_estado,
            'certificado_rotulo': certificado_rotulo,
            'certificado_url': url_del_grupo('mi_certificado', curso, inscripcion.edicion_id) if certificado else '',
            'aula_url': url_del_grupo('aula_curso', curso, inscripcion.edicion_id)}


@login_required
@require_GET
@never_cache
@xframe_options_sameorigin
def seguimiento_curso_view(request, slug, codigo):
    """Historial propio, incluso retirado o despublicado, sin habilitar acceso al aula."""
    propias = list(InscripcionCurso.objects.filter(edicion__curso__codigo=codigo,
                   edicion__curso__unidad__slug=slug, usuario=request.user)
                   .select_related('usuario', 'edicion__curso__unidad')
                   .order_by('-fecha_inscripcion', '-pk'))
    solicitada = request.GET.get('edicion')
    inscripcion = next((propia for propia in propias if str(propia.edicion_id) == solicitada), None) if solicitada is not None else (propias[0] if propias else None)
    if inscripcion is None:
        raise Http404('No tiene una inscripción en este grupo del curso.')
    # El selector necesita los nombres de las otras cohortes, no sus actividades.
    prefetch_related_objects([inscripcion], 'progresos', 'intentos', 'entregas', 'certificados')
    curso, unidad = inscripcion.edicion.curso, inscripcion.edicion.curso.unidad
    seguimiento = seguimiento_de(inscripcion)
    if request.GET.get('formato') == 'pdf':
        from apps.gestion_unidades.presentation.seguimiento_reportes import respuesta_pdf_seguimiento
        return respuesta_pdf_seguimiento(curso, seguimiento)
    return render(request, 'portal/pages/unidades/aula/curso_seguimiento.html', {
        'unidad': unidad, 'curso': curso, 'seguimiento': seguimiento,
        'mis_inscripciones': propias, 'elegida': inscripcion.edicion,
        'curso_url': reverse('mi_formacion'),
    })


# Alias de integración para paneles que sólo necesitan el resumen académico.
resumen_estado = seguimiento_de


@login_required
@require_GET
@never_cache
@xframe_options_sameorigin
def seguimiento_participante_view(request, slug, codigo, inscripcion_id):
    """Consulta de un participante exacto, sólo para quien gestiona su unidad."""
    unidad = get_object_or_404(Unidad, slug=slug)
    curso = get_object_or_404(Curso, unidad=unidad, codigo=codigo)
    if not puede_crear_cursos(request.user, unidad):
        if not curso.publicado:
            raise Http404('El curso no está publicado.')
        raise PermissionDenied('Sólo quien gestiona esta unidad consulta el reporte de sus participantes.')
    inscripcion = get_object_or_404(InscripcionCurso.objects.select_related('usuario', 'edicion__curso__unidad')
        .prefetch_related('progresos', 'intentos', 'entregas', 'certificados'),
        pk=inscripcion_id, edicion__curso=curso)
    seguimiento = seguimiento_de(inscripcion)
    if seguimiento['certificado']:
        seguimiento['certificado_url'] = reverse('certificado_curso_gestor',
            args=[unidad.slug, curso.codigo, seguimiento['certificado'].pk]) + '?descargar=1'
    if request.GET.get('formato') == 'pdf':
        from apps.gestion_unidades.presentation.seguimiento_reportes import respuesta_pdf_seguimiento
        return respuesta_pdf_seguimiento(curso, seguimiento)
    return render(request, 'portal/pages/unidades/aula/curso_seguimiento.html', {
        'unidad': unidad, 'curso': curso, 'seguimiento': seguimiento,
        'mis_inscripciones': [inscripcion], 'elegida': inscripcion.edicion, 'modo_gestion': True,
        'curso_url': url_del_grupo('inscritos_curso', curso, inscripcion.edicion_id),
    })
