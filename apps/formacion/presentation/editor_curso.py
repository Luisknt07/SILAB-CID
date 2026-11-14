"""Editor privado del programa completo de un curso, incluido lo no publicado.

Esta pantalla reúne los formularios existentes; consultar el programa no cambia
su contenido, las matrículas ni el historial académico.
"""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from apps.formacion.models.cursos import Curso, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.directorio_unidades.models.core import Unidad

from apps.formacion.presentation.aula_cursos import ICONOS_DE_LECCION
from apps.formacion.presentation.cursos import puede_crear_cursos
from apps.gestion_unidades.presentation.edicion_registro import REGISTRO


SECCIONES = {
    'presentacion': ('Nombre, portada, video, modalidad y publicación.', 'fas fa-image'),
    'contenido': ('Descripción, aprendizajes, destinatarios y requisitos.', 'fas fa-book-open'),
    'datos': ('Duración, inscripción, vinculación y emisión de certificados.', 'fas fa-sliders-h'),
    'instructores': ('Personas que imparten el curso y sus especialidades.', 'fas fa-chalkboard-teacher'),
    'pagos': ('Costo, medios de pago e instrucciones para los participantes.', 'fas fa-credit-card'),
    'oferta': ('Plataforma externa, institución organizadora y colaboración de la unidad.', 'fas fa-external-link-alt'),
}


def _editar_url(unidad, clave, pk, volver, *, grupo='', padre=None):
    """La misma edición validada de la ficha, con regreso al editor del curso."""
    consulta = {'volver': volver}
    if grupo:
        consulta['grupo'] = grupo
    if padre is not None:
        consulta['padre'] = str(padre)
    return reverse('editar_registro', args=[unidad.slug, clave, pk]) + '?' + urlencode(consulta)


def _secciones_curso(unidad, curso, editor_url):
    registro = REGISTRO['curso']
    secciones = []
    agrupados = set()
    for clave, (titulo, campos) in registro.grupos.items():
        if (curso.es_externo and clave in ('datos', 'pagos')) or (not curso.es_externo and clave == 'duracion'):
            agrupados.update(campos)
            continue
        descripcion, icono = SECCIONES.get(clave, ('Configuración de esta parte del curso.', 'fas fa-edit'))
        agrupados.update(campos)
        secciones.append({
            'clave': clave,
            'titulo': titulo,
            'descripcion': descripcion,
            'icono': icono,
            'url': _editar_url(unidad, 'curso', curso.pk, editor_url + '#datos', grupo=clave),
        })
    # Si el registro incorpora campos todavía no agrupados, siguen editables.
    if set(registro.campos) - agrupados or not secciones:
        secciones.append({
            'clave': 'completo',
            'titulo': 'Configuración completa',
            'descripcion': 'Todos los datos editables del curso en un formulario.',
            'icono': 'fas fa-cogs',
            'url': _editar_url(unidad, 'curso', curso.pk, editor_url + '#datos'),
        })
    return secciones


def contexto_editor(unidad, curso):
    """Programa sin filtros de publicación y sin consultas por cada lección."""
    argumentos = [unidad.slug, curso.codigo]
    editor_url = reverse('editor_curso', args=argumentos)
    volver_programa = editor_url + '#programa'
    preguntas = PreguntaEvaluacion.objects.only(
        'pk', 'leccion_id', 'orden', 'enunciado', 'tipo', 'puntos',
    ).order_by('orden', 'pk')
    lecciones = LeccionCurso.objects.only(
        'pk', 'modulo_id', 'orden', 'titulo', 'tipo', 'publicada', 'obligatoria',
        'duracion_min', 'nota_minima', 'intentos', 'fecha_limite',
    ).prefetch_related(Prefetch('preguntas', queryset=preguntas)).order_by('orden', 'pk')
    programa = ModuloCurso.objects.filter(curso=curso).prefetch_related(
        Prefetch('lecciones', queryset=lecciones),
    ).order_by('orden', 'pk')
    modulos = []
    evaluaciones = []
    trabajos = []
    total_lecciones = total_preguntas = 0
    for modulo in programa:
        contenidos = []
        for leccion in modulo.lecciones.all():
            preguntas_leccion = [{
                'pregunta': pregunta,
                'editar_url': _editar_url(unidad, 'pregunta_curso', pregunta.pk, volver_programa),
            } for pregunta in leccion.preguntas.all()]
            fila = {
                'leccion': leccion,
                'modulo': modulo,
                'editar_url': _editar_url(unidad, 'leccion_curso', leccion.pk, volver_programa),
                'aula_url': reverse('aula_curso_leccion', args=[*argumentos, leccion.pk]),
                'icono': ICONOS_DE_LECCION.get(leccion.tipo, 'fas fa-file-alt'),
                'preguntas': preguntas_leccion,
                'nueva_pregunta_url': _editar_url(
                    unidad, 'pregunta_curso', 'nuevo', volver_programa, padre=leccion.pk,
                ) if leccion.tipo == 'evaluacion' else '',
            }
            contenidos.append(fila)
            total_lecciones += 1
            total_preguntas += len(preguntas_leccion)
            if leccion.tipo == 'evaluacion':
                evaluaciones.append(fila)
            elif leccion.tipo == 'deber':
                trabajos.append(fila)
        modulos.append({
            'modulo': modulo,
            'editar_url': _editar_url(unidad, 'modulo_curso', modulo.pk, volver_programa),
            'nueva_leccion_url': _editar_url(
                unidad, 'leccion_curso', 'nuevo', volver_programa, padre=modulo.pk,
            ),
            'lecciones': contenidos,
        })
    return {
        'url': editor_url,
        'curso_url': reverse('curso_unidad', args=argumentos),
        'aula_url': reverse('aula_curso', args=argumentos),
        'gestion_url': reverse('gestion_unidad', args=[unidad.slug]) + '?view=cursos',
        'estado_url': reverse('estado_curso', args=argumentos),
        'grupo_url': reverse('grupos_curso', args=argumentos),
        'inscritos_url': reverse('inscritos_curso', args=argumentos),
        'calificaciones_url': reverse('calificaciones_curso', args=argumentos),
        'certificado_url': reverse('editar_certificado_curso', args=argumentos),
        'resumen': {
            'modulos': len(modulos),
            'lecciones': total_lecciones,
            'evaluaciones': len(evaluaciones),
            'deberes': len(trabajos),
            'preguntas': total_preguntas,
        },
        'secciones_curso': _secciones_curso(unidad, curso, editor_url),
        'modulos': modulos,
        'nuevo_modulo_url': _editar_url(unidad, 'modulo_curso', 'nuevo', volver_programa, padre=curso.pk),
        'evaluaciones': evaluaciones,
        'trabajos': trabajos,
    }


@login_required
@never_cache
@require_GET
@xframe_options_sameorigin
def editor_curso_view(request, slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    if not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('No tienes permiso para editar los cursos de esta unidad.')
    curso = get_object_or_404(Curso, unidad=unidad, codigo=codigo)
    respuesta = render(request, 'portal/pages/unidades/aula/curso_editor.html', {
        'unidad': unidad,
        'curso': curso,
        'editor': contexto_editor(unidad, curso),
    })
    respuesta['Cache-Control'] = 'private, no-store, no-cache, must-revalidate, max-age=0'
    return respuesta
