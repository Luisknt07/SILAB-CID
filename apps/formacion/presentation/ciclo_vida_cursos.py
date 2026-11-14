"""Estado y eliminación explícita de la oferta, conservando el historial."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.formacion.models.cursos import Curso
from apps.directorio_unidades.models.core import Unidad

from apps.formacion.presentation.cursos import puede_crear_cursos


@login_required
@require_POST
def estado_curso_view(request, slug, codigo):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    if not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('No puedes administrar la oferta de esta unidad.')
    accion = request.POST.get('accion')
    if accion not in ('activar', 'desactivar', 'eliminar'):
        return HttpResponseBadRequest('Acción no válida.')
    with transaction.atomic():
        curso = get_object_or_404(Curso.objects.select_for_update(), unidad=unidad, codigo=codigo)
        destino = reverse('editor_curso', args=[unidad.slug, curso.codigo])
        if accion == 'eliminar':
            if request.POST.get('confirmar') != curso.codigo:
                return HttpResponseBadRequest('Confirma la eliminación con el código de la actividad.')
            try:
                curso.delete()
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                destino = reverse('gestion_unidad', args=[unidad.slug]) + '?view=cursos'
                messages.success(request, 'Actividad eliminada.')
        else:
            curso.activo = accion == 'activar'
            curso.save(update_fields=['activo', 'fecha_actualizacion'])
            messages.success(request, 'Actividad activada.' if curso.activo else 'Actividad desactivada. Se conserva su historial.')
    if request.POST.get('volver') == 'gestion':
        destino = reverse('gestion_unidad', args=[unidad.slug]) + '?view=cursos'
    return redirect(destino)
