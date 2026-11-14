"""Una sola entrada de sesión; el personal de unidad usa su alcance operativo."""
from urllib.parse import urlencode, urlsplit

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache


def unidades_editables(usuario):
    from django.db.models import Q
    from apps.directorio_unidades.models.core import Unidad
    if not usuario.is_authenticated or not usuario.is_active:
        return Unidad.objects.none()
    return Unidad.objects.filter(
        Q(administrador=usuario) | Q(responsables_unidad__usuario=usuario,
            responsables_unidad__activo=True, responsables_unidad__rol='coordinacion')
    ).distinct()


def usa_admin_institucional(usuario):
    return usuario.is_authenticated and usuario.is_active and (
        (usuario.is_staff and (usuario.is_superuser or bool(usuario.get_all_permissions())))
        or unidades_editables(usuario).exists())


def permiso_entrada_admin(request):
    return (request.user.is_active and request.user.is_staff) or usa_admin_institucional(request.user)


def indice_admin(original):
    @never_cache
    def vista(request, extra_context=None):
        if not usa_admin_institucional(request.user):
            return acceso_admin(request, extra_context)
        respuesta = original(request, extra_context)
        areas = respuesta.context_data.get('app_list', [])
        respuesta.context_data['solo_gestion_unidades'] = bool(areas) and all(
            area.get('slug', '').startswith('mi_unidad_') for area in areas)
        return respuesta
    return vista


@never_cache
def acceso_admin(request, extra_context=None):
    destino = request.GET.get('next') or reverse('admin:index')
    if (not url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure())
            or not urlsplit(destino).path.startswith(reverse('admin:index'))
            or urlsplit(destino).path in (reverse('admin:login'), reverse('admin:logout'))):
        destino = reverse('admin:index')
    if not request.user.is_authenticated:
        return redirect_to_login(destino, login_url=reverse('login'))
    if not request.user.is_active:
        raise PermissionDenied
    if usa_admin_institucional(request.user):
        return redirect(destino)
    from apps.gestion_unidades.presentation.permisos import unidades_gestionables
    unidades = list(unidades_gestionables(request.user).filter(activo=True)[:2])
    if len(unidades) == 1:
        return redirect('gestion_unidad', slug=unidades[0].slug)
    # El perfil contiene el selector de las unidades autorizadas, sin exponer las demás.
    if unidades:
        return redirect(reverse('profile') + '?' + urlencode({'gestion': 'unidades'}))
    raise PermissionDenied('Tu cuenta no tiene una unidad asignada ni acceso administrativo.')
