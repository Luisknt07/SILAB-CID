"""Seleccion personal de idioma; no cambia configuracion o permisos institucionales."""

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils import translation
from django.views.decorators.cache import cache_control
from django.views.decorators.gzip import gzip_page
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_cookie
from django.views.i18n import JavaScriptCatalog, set_language


@require_POST
def cambiar_idioma(request):
    if request.POST.get("language") not in dict(settings.LANGUAGES):
        return HttpResponseBadRequest(translation.gettext("Selecciona español o inglés."))
    return set_language(request)  # Django valida el destino y configura la cookie.


@cache_control(private=True, max_age=3600)
@vary_on_cookie
@gzip_page
def catalogo_javascript(request):
    idioma = request.GET.get("language", getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE)).split("-")[0]
    if idioma not in dict(settings.LANGUAGES):
        return HttpResponseBadRequest(translation.gettext("Selecciona español o inglés."))
    with translation.override(idioma):
        return JavaScriptCatalog.as_view(domain="django")(request)
