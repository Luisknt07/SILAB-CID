"""Pantalla del segundo factor: alta la primera vez, código en los ingresos siguientes."""
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.core.acceso import segundo_factor, totp


def _destino(request):
    """Solo se vuelve a una página del propio administrador."""
    inicio = reverse('admin:index')
    destino = request.POST.get('next') or request.GET.get('next') or inicio
    if (not url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure())
            or not urlsplit(destino).path.startswith(inicio)):
        return inicio
    return destino


def _emisor():
    # Nombre breve: es lo que la aplicación autenticadora muestra junto al código.
    return settings.PRODUCT_IDENTITY.get('codigo') or 'SLCID'


@never_cache
@require_http_methods(['GET', 'POST'])
def segundo_factor_view(request):
    if not segundo_factor.red_autorizada(request):
        raise Http404
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), login_url=reverse('login'))
    if not admin.site.has_permission(request):
        raise PermissionDenied
    destino = _destino(request)
    alta = not segundo_factor.tiene_alta(request.user)
    if request.method == 'GET' and not alta and segundo_factor.sesion_verificada(request):
        return redirect(destino)

    contexto = {'next': destino, 'alta': alta, 'error': ''}
    estado = 200
    if request.method == 'POST':
        propuesto = request.POST.get('codigo', '')
        try:
            if alta:
                respaldo = segundo_factor.confirmar_alta(request.user, propuesto)
                correcto = respaldo is not None
            else:
                respaldo = None
                correcto = segundo_factor.verificar(request.user, propuesto)
        except segundo_factor.AccesoBloqueado as bloqueo:
            minutos = max(1, int((bloqueo.hasta - timezone.now()).total_seconds() // 60) + 1)
            contexto['error'] = _('Demasiados intentos. Vuelve a intentarlo en %(minutos)s minutos.') % {
                'minutos': minutos}
            correcto, respaldo, estado = False, None, 429
        if correcto:
            # La sesión gana privilegio: cambia de identificador antes de anotarlo.
            request.session.cycle_key()
            segundo_factor.marcar_sesion(request)
            if respaldo:
                return render(request, 'registration/segundo_factor.html',
                              {'next': destino, 'codigos_respaldo': respaldo})
            return redirect(destino)
        if not contexto['error']:
            contexto['error'] = _('El código no es válido. Comprueba la hora del teléfono e inténtalo de nuevo.')
            estado = 400

    if alta:
        _factor, secreto = segundo_factor.iniciar_alta(request.user)
        cuenta = request.user.email or request.user.get_username()
        contexto['clave'] = ' '.join(secreto[i:i + 4] for i in range(0, len(secreto), 4))
        contexto['qr'] = segundo_factor.imagen_qr(totp.direccion_de_alta(secreto, cuenta, _emisor()))
    return render(request, 'registration/segundo_factor.html', contexto, status=estado)
