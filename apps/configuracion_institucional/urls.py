"""Lectura controlada de logos; nunca exponer el directorio privado."""
from django.http import FileResponse, Http404
from django.urls import re_path
from django.db.models import Q
from django.db import transaction
from django.views.decorators.http import require_safe

from apps.core.presentation.identidad import identidad_de_despliegue
from .imagenes import CAMPOS_IMAGENES, almacen_logos
from .models import RevisionPresentacion
from .versionado import actor_con_permiso
from django.core.exceptions import PermissionDenied


@require_safe
def imagen_institucional(request, nombre):
    producto, institucion = identidad_de_despliegue()
    consulta = Q()
    for campo in CAMPOS_IMAGENES:
        consulta |= Q(**{campo: nombre})
    revisiones = RevisionPresentacion.objects.filter(
        consulta, producto_codigo=producto.codigo, institucion_codigo=institucion.siglas)
    publica = revisiones.filter(estado='publicada').exists()
    if not publica:
        try:
            with transaction.atomic():
                actor_con_permiso(request.user, 'configuracion_institucional.view_revisionpresentacion')
        except PermissionDenied:
            raise Http404 from None
        if not revisiones.exists():
            raise Http404
    try:
        archivo = almacen_logos.open(nombre, 'rb')
    except FileNotFoundError:
        raise Http404 from None
    respuesta = FileResponse(archivo, content_type='image/png')
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'public, max-age=3600' if publica else 'private, no-store'
    return respuesta


urlpatterns = [re_path(r'^marca/imagenes/(?P<nombre>[a-f0-9]{32}\.png)$', imagen_institucional, name='imagen_institucional')]
