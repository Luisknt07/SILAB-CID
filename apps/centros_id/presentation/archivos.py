"""Archivos del centro: validar publicación y permisos antes de abrir storage."""
from pathlib import PurePosixPath

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_safe

from .views import _centro


@require_safe
@xframe_options_sameorigin
def descarga_archivo_view(request, slug, tipo, pk):
    from apps.centros_id.escenarios import contenido_admitido
    from apps.centros_id.models import DocumentoCentro, RecursoCentro

    centro = _centro(slug)
    if tipo == 'documento':
        objeto = get_object_or_404(DocumentoCentro, centro=centro, pk=pk)
        objeto.centro = centro
        publico = objeto.publico and objeto.estado_documental != 'borrador' and contenido_admitido(objeto)
    elif tipo == 'recurso':
        objeto = get_object_or_404(RecursoCentro.objects.select_related('carpeta'),
            carpeta__centro=centro, carpeta__activa=True, activo=True, pk=pk, tipo='archivo')
        publico = objeto.carpeta.visibilidad == 'publica'
    else:
        raise Http404
    # La copia local de identidad nunca decide permisos. La política del centro
    # vuelve a consultar el principal de autenticación vigente.
    if not publico and not centro.puede_gestionar(request.user):
        raise Http404
    if not objeto.archivo:
        raise Http404
    try:
        archivo = objeto.archivo.open('rb')
    except FileNotFoundError as error:
        raise Http404 from error
    nombre = PurePosixPath(objeto.archivo.name.replace('\\', '/')).name
    es_pdf = nombre.lower().endswith('.pdf')
    respuesta = FileResponse(archivo, filename=nombre,
        as_attachment=request.GET.get('descargar') == '1' or not es_pdf,
        content_type='application/pdf' if es_pdf else 'application/octet-stream')
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta
