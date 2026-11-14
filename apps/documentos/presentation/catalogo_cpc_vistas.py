"""Búsqueda de referencias CPC para quien prepara el plan de una unidad."""
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@login_required
@require_GET
@never_cache
def buscar_cpc_necesidad_view(request, slug, documento_id):
    from .catalogo_cpc import buscar_cpc, fuente_catalogo_cpc
    from .expediente_redaccion import _documento_redactable

    _unidad, documento = _documento_redactable(request, slug, documento_id)
    if documento.exigido.codigo != 'PLAN-COMPRAS-ANUAL' or documento.exigido.fuente_reporte != 'compras':
        raise Http404('La clasificación CPC se consulta al preparar las necesidades de compra.')
    consulta = request.GET.get('q', '')
    if len(consulta) > 120:
        return JsonResponse({'error': 'Busca por código o nombre de hasta 120 caracteres.'}, status=400)
    fuente = fuente_catalogo_cpc()
    return JsonResponse({'resultados': buscar_cpc(consulta, request.GET.get('limit', 20)),
                         'fuente': fuente, 'total': fuente['registros']})
