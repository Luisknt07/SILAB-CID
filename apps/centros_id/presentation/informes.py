"""Centro privado de reportes científicos; HTML y exportaciones comparten scope."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@login_required
@never_cache
@require_safe
def informes_view(request):
    from apps.centros_id.informes import construir_reporte_centros

    formato = request.GET.get('formato', '')
    if formato not in ('', 'pdf', 'docx', 'xlsx'):
        return HttpResponseBadRequest('Formato no reconocido.', content_type='text/plain; charset=utf-8')
    try:
        reporte = construir_reporte_centros(request.user, request.GET, exportar=bool(formato))
    except ValidationError as error:
        return HttpResponseBadRequest('\n'.join(error.messages), content_type='text/plain; charset=utf-8')
    if formato:
        from apps.core.reportes import respuesta_reporte
        return respuesta_reporte(reporte, formato, 'centros-id', descargar=request.GET.get('descargar') != '0')
    parametros = {k: v for k, v in request.GET.items() if k not in ('pagina', 'formato', 'descargar')}
    base = reverse('reportes_centros_id')

    def enlace(**extras):
        return base + '?' + urlencode({**parametros, **extras})

    paginacion = reporte['pagination']
    return render(request, 'centros_id/informes.html', {
        'reporte': reporte, 'page_title': reporte['title'], 'page_key': 'centros',
        'anterior_url': enlace(pagina=paginacion['previous']) if paginacion['previous'] else '',
        'siguiente_url': enlace(pagina=paginacion['next']) if paginacion['next'] else '',
        'exportaciones': [(nombre, enlace(formato=clave)) for clave, nombre in
                         (('pdf', 'Descargar PDF'), ('docx', 'Descargar Word'), ('xlsx', 'Descargar Excel'))],
        'pdf_url': enlace(formato='pdf', descargar='0'),
    })
