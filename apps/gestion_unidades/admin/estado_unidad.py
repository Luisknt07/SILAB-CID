"""«Estado de la unidad»: activarla, desactivarla o, si no tiene historial, eliminarla.

Desactivar la retira del portal y conserva todo lo suyo; es la forma normal de dar
de baja una unidad. Eliminar la borra con todo lo que cuelga de ella, así que solo
se ofrece cuando no tiene historial (apps.gestion_unidades.presentation.baja). Las dos cosas
las decide la administración institucional, no el personal de la unidad.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from apps.gestion_unidades.presentation.baja import historial_de


def url_estado(modelo_admin, unidad):
    opciones = modelo_admin.model._meta
    return reverse(f'admin:{opciones.app_label}_{opciones.model_name}_estado', args=[unidad.pk])


def puede_cambiar_estado(modelo_admin, request, unidad):
    """Quien administra toda la institución; el personal de una unidad no la retira."""
    return not modelo_admin._alcance_local(request) and modelo_admin.has_change_permission(request, unidad)


def vista_estado(modelo_admin, request, object_id):
    """La página del estado; fuera del alcance de la cuenta, la unidad no existe."""
    unidad = get_object_or_404(modelo_admin.get_queryset(request), pk=object_id)
    if not modelo_admin.has_view_or_change_permission(request, unidad):
        raise PermissionDenied
    opciones = modelo_admin.model._meta
    editor_url = reverse(f'admin:{opciones.app_label}_{opciones.model_name}_change', args=[unidad.pk])
    puede_cambiar = puede_cambiar_estado(modelo_admin, request, unidad)
    puede_eliminar = puede_cambiar and request.user.is_superuser
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion in ('desactivar', 'reactivar'):
            if not puede_cambiar:
                raise PermissionDenied
            unidad.activo = accion == 'reactivar'
            unidad.save(update_fields=['activo'])
            mensaje = (f'«{unidad.nombre}» vuelve a verse en el portal.' if unidad.activo else
                       f'«{unidad.nombre}» queda desactivada: ya no aparece en el portal y todo lo suyo se conserva.')
            modelo_admin.log_change(request, unidad, mensaje)
            messages.success(request, mensaje)
            return redirect(editor_url)
        if accion == 'eliminar':
            if not puede_eliminar:
                raise PermissionDenied
            if historial_de(unidad):
                messages.error(request, 'Tiene historial: no se puede eliminar. Desactívela para retirarla del portal.')
                return redirect(request.path)
            nombre = unidad.nombre
            modelo_admin.log_deletions(request, type(unidad)._default_manager.filter(pk=unidad.pk))
            unidad.delete()
            messages.success(request, f'La unidad «{nombre}» se eliminó.')
            return redirect(reverse('admin:index') + f'#{opciones.app_label}')
        messages.error(request, 'Acción desconocida.')
        return redirect(request.path)
    return TemplateResponse(request, 'admin/unidades/estado_unidad.html', {
        **modelo_admin.admin_site.each_context(request),
        'title': f'Estado · {unidad.nombre}',
        'unidad': unidad,
        'opts': opciones,
        'editor_url': editor_url,
        'historial': historial_de(unidad),
        'puede_cambiar': puede_cambiar,
        'puede_eliminar': puede_eliminar,
    })
