"""Listado privado de la formación propia, reunida entre todas las unidades."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.formacion.models.cursos import InscripcionCurso

from apps.formacion.presentation.inscripciones_cursos import aplicar_invitaciones
from apps.formacion.presentation.seguimiento_cursos import seguimiento_de, url_del_grupo


@login_required
@require_GET
@never_cache
def mi_formacion_view(request):
    aplicar_invitaciones(request.user)
    propias = (InscripcionCurso.objects.filter(usuario=request.user)
               .select_related('usuario', 'edicion__curso__unidad')
               .prefetch_related('progresos', 'intentos', 'entregas', 'certificados')
               .order_by('-fecha_inscripcion', '-pk'))
    pagina = Paginator(propias, 20).get_page(request.GET.get('pagina'))
    filas = []
    for inscripcion in pagina:
        curso = inscripcion.edicion.curso
        resumen = seguimiento_de(inscripcion)
        filas.append({
            'inscripcion': inscripcion, 'curso': curso, 'resumen': resumen,
            'reporte_url': url_del_grupo('seguimiento_curso', curso, inscripcion.edicion_id),
            'aula_url': resumen['aula_url'] if (inscripcion.estado == 'aceptada' and curso.publicado
                                              and curso.unidad.activo) else '',
            'certificado_url': resumen['certificado_url'],
            'curso_url': url_del_grupo('curso_unidad', curso, inscripcion.edicion_id),
        })
    return render(request, 'portal/pages/unidades/aula/mi_formacion.html', {
        'filas': filas, 'pagina': pagina, 'total': propias.count(),
        'perfil_url': reverse('profile'),
    })
