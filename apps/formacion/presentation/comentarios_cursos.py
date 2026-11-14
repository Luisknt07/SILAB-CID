"""Preguntas y comentarios en cada lección del aula.

Quien está inscrito y quien gestiona los cursos de la unidad pregunta, aporta y responde debajo de cada lección; las
respuestas del instructor se distinguen. Cada persona puede retirar lo suyo y la unidad puede ocultar lo que no
corresponda: lo oculto deja de verse para los inscritos, pero queda registrado.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.formacion.models.cursos import ComentarioLeccion, LeccionCurso, VotoComentario

from apps.formacion.presentation.aula_cursos import _acceso_al_aula, _curso
from apps.formacion.presentation.cursos import puede_crear_cursos
from apps.formacion.presentation.matriculas_cursos import edicion_solicitada, url_con_edicion

LARGO_MAXIMO = 2000


ORDENES = ('votos', 'recientes')
TONOS = 6
UN_MINUTO = timedelta(minutes=1)


def iniciales_de(usuario):
    nombre = usuario.get_full_name().strip() or usuario.get_username()
    partes = [parte for parte in nombre.replace('.', ' ').split() if parte]
    return ''.join(parte[0] for parte in partes[:2]).upper() or '?'


def contexto_comentarios(leccion, usuario, unidad, vista_previa, orden='votos'):
    """Las preguntas de la lección con sus respuestas, sus «Me gusta» y quién las escribe; se ordenan por los más
    votados o por los más recientes. Quien modera ve también lo oculto, marcado."""
    if leccion is None:
        return {}
    orden = orden if orden in ORDENES else 'votos'
    moderador = puede_crear_cursos(usuario, unidad)
    todos = list(leccion.comentarios.select_related('usuario').annotate(total_votos=Count('me_gusta')).order_by('creado'))
    visibles = [comentario for comentario in todos if moderador or not comentario.oculto]
    votados = set(VotoComentario.objects.filter(comentario__in=visibles, usuario_id=usuario.pk)
                  .values_list('comentario_id', flat=True))
    instructores, ahora = {}, timezone.now()
    for comentario in visibles:
        if comentario.usuario_id not in instructores:
            instructores[comentario.usuario_id] = puede_crear_cursos(comentario.usuario, unidad)
        comentario.de_instructor = instructores[comentario.usuario_id]
        comentario.propio = comentario.usuario_id == usuario.pk
        comentario.autor = comentario.usuario.get_full_name().strip() or comentario.usuario.get_username()
        comentario.iniciales = iniciales_de(comentario.usuario)
        comentario.tono = comentario.usuario_id % TONOS
        comentario.votos, comentario.votado = comentario.total_votos, comentario.pk in votados
        comentario.reciente = ahora - comentario.creado < UN_MINUTO
        comentario.lista_respuestas = [respuesta for respuesta in visibles if respuesta.respuesta_a_id == comentario.pk]
    preguntas = [comentario for comentario in visibles if comentario.respuesta_a_id is None]
    if orden == 'votos':
        preguntas.sort(key=lambda comentario: (comentario.votos, comentario.creado), reverse=True)
    else:
        preguntas.reverse()
    return {'comentarios': {'preguntas': preguntas, 'total': len(visibles), 'moderador': moderador,
                            'largo': LARGO_MAXIMO, 'orden': orden}}


def _leccion(request, slug, codigo, leccion_id):
    unidad, curso = _curso(slug, codigo, request.user)
    _inscripcion, vista_previa = _acceso_al_aula(request, unidad, curso)
    lecciones = LeccionCurso.objects.filter(modulo__curso=curso)
    # Las lecciones sin publicar solo las ve (y comenta) quien gestiona la unidad.
    leccion = get_object_or_404(lecciones if vista_previa else lecciones.filter(publicada=True), pk=leccion_id)
    return unidad, curso, leccion


@login_required
@require_POST
def comentar_view(request, slug, codigo, leccion_id):
    unidad, curso, leccion = _leccion(request, slug, codigo, leccion_id)
    texto = request.POST.get('texto', '').strip()[:LARGO_MAXIMO]
    respuesta_a = request.POST.get('respuesta_a', '')
    padre = (ComentarioLeccion.objects.filter(leccion=leccion, pk=respuesta_a, respuesta_a__isnull=True).first()
             if respuesta_a.isdigit() else None)
    if texto:
        ComentarioLeccion.objects.create(leccion=leccion, usuario=request.user, texto=texto, respuesta_a=padre)
    destino = url_con_edicion(reverse('aula_curso_leccion', args=[unidad.slug, curso.codigo, leccion.pk]),
                              edicion_solicitada(curso, request))
    return redirect(f'{destino}#comentario-{padre.pk}' if padre else f'{destino}#comentarios')


@login_required
@require_POST
def votar_comentario_view(request, slug, codigo, comentario_id):
    """Da o quita el «Me gusta» de la persona a un comentario que puede ver; responde el nuevo total sin recargar."""
    comentario = get_object_or_404(ComentarioLeccion, pk=comentario_id, leccion__modulo__curso__codigo=codigo,
                                   leccion__modulo__curso__unidad__slug=slug)
    unidad, curso, leccion = _leccion(request, slug, codigo, comentario.leccion_id)
    if comentario.oculto and not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('Ese comentario no está visible.')
    voto, creado = VotoComentario.objects.get_or_create(comentario=comentario, usuario=request.user)
    if not creado:
        voto.delete()
    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({'votado': creado, 'votos': comentario.me_gusta.count()})
    return redirect(url_con_edicion(reverse('aula_curso_leccion', args=[unidad.slug, curso.codigo, leccion.pk]),
                                   edicion_solicitada(curso, request))
                    + f'#comentario-{comentario.pk}')


@login_required
@require_POST
def moderar_comentario_view(request, slug, codigo, comentario_id):
    """El autor retira su comentario; la unidad oculta o vuelve a mostrar el de cualquiera."""
    comentario = get_object_or_404(ComentarioLeccion.objects.select_related('leccion__modulo__curso__unidad'),
                                   pk=comentario_id, leccion__modulo__curso__codigo=codigo,
                                   leccion__modulo__curso__unidad__slug=slug)
    curso = comentario.leccion.modulo.curso
    unidad = curso.unidad
    edicion = edicion_solicitada(curso, request)
    if puede_crear_cursos(request.user, unidad):
        comentario.oculto = not comentario.oculto
        comentario.save(update_fields=['oculto'])
    elif comentario.usuario_id == request.user.pk:
        # Si ya la respondieron, se retira el texto pero quedan las respuestas de los demás.
        if comentario.respuestas.exists():
            comentario.texto = 'Pregunta retirada por su autor.'
            comentario.save(update_fields=['texto'])
        else:
            comentario.delete()
    else:
        raise PermissionDenied('Solo el autor o la unidad pueden retirar este comentario.')
    return redirect(url_con_edicion(reverse('aula_curso_leccion', args=[slug, codigo, comentario.leccion_id]),
                                   edicion) + '#comentarios')
