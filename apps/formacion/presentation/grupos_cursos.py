"""Gestión de grupos o ediciones que comparten el contenido de un mismo curso."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.formacion.models.cursos import Curso, EdicionCurso
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.presentation.cursos import puede_crear_cursos
from apps.formacion.presentation.matriculas_cursos import cupos_disponibles, seleccionar_edicion, url_con_edicion
from apps.formacion.presentation.matriculas_forms import GrupoCursoForm


@login_required
@xframe_options_sameorigin
def grupos_curso_view(request, slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    curso = get_object_or_404(Curso, unidad=unidad, codigo=codigo)
    if curso.es_externo:
        raise Http404('Las convocatorias se gestionan en la plataforma organizadora.')
    if not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad puede organizar sus grupos.')
    dato = request.POST.get('edicion') if request.method == 'POST' else request.GET.get('edicion')
    grupo = seleccionar_edicion(curso, dato) if dato else None
    formulario = GrupoCursoForm(request.POST or None, curso=curso, instance=grupo,
                                initial={'anio': timezone.localdate().year})
    if request.method == 'POST':
        guardado = False
        try:
            with transaction.atomic():
                curso = get_object_or_404(Curso.objects.select_for_update(), pk=curso.pk, unidad=unidad)
                if curso.es_externo:
                    raise Http404('Las convocatorias se gestionan en la plataforma organizadora.')
                if grupo:
                    grupo = EdicionCurso.objects.select_for_update().get(pk=grupo.pk)
                formulario = GrupoCursoForm(request.POST, curso=curso, instance=grupo)
                if formulario.is_valid():
                    grupo = formulario.save()
                    guardado = True
            if guardado:
                messages.success(request, 'Grupo guardado correctamente.')
                return redirect(url_con_edicion(reverse('grupos_curso', args=[unidad.slug, curso.codigo]), grupo))
        except IntegrityError:
            formulario.add_error(None, 'Ya existe un grupo con ese nombre. Revisa la lista antes de repetir.')
    grupos = list(curso.ediciones.all())
    for actual in grupos:
        actual.cupos_disponibles = cupos_disponibles(actual)
        actual.matriculados = actual.inscripciones.filter(estado='aceptada').count()
        actual.reservadas = actual.invitaciones.filter(activa=True, inscripcion__isnull=True).count()
    return render(request, 'portal/pages/unidades/aula/grupos_curso.html', {
        'unidad': unidad, 'curso': curso, 'grupos': grupos, 'grupo': grupo, 'formulario': formulario,
        'curso_url': reverse('curso_unidad', args=[unidad.slug, curso.codigo]),
        'inscritos_url': reverse('inscritos_curso', args=[unidad.slug, curso.codigo]),
    })
