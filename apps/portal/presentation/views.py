"""Vistas públicas que no dependen del dominio de Unidades."""

from django.conf import settings
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils.module_loading import import_string
from django.views.decorators.http import require_safe
from django.views.generic import TemplateView

# El único proveedor que «Noticias» acepta: las novedades que publican las unidades.
# Sin él declarado en la configuración, la página muestra su contenido institucional.
PROVEEDOR_NOVEDADES = 'apps.gestion_unidades.presentation.novedades.novedades_del_portal'


@require_safe
def favicon(request):
    """Resuelve también la petición automática del navegador al icono del sitio."""
    return redirect(static('favicon.ico'))


def proveedor_novedades():
    ruta = getattr(settings, 'PORTAL_NEWS_PROVIDER', '')
    if not ruta:
        return None
    if ruta != PROVEEDOR_NOVEDADES:
        raise ValueError('El proveedor de novedades no esta registrado.')
    return import_string(ruta)


def home_view(request):
    """Muestra la portada institucional."""
    from apps.portal.inicio.selectors import portada_publicada

    return render(
        request,
        "portal/pages/inicio/inicio.html",
        {"active_section": "home", "portada_inicio": portada_publicada()},
    )


class PortalPageView(TemplateView):
    """Base mínima para páginas institucionales de contenido estático."""

    page_key = ""
    page_title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(page_key=self.page_key, page_title=self.page_title)
        return context


class QuienesSomosView(PortalPageView):
    template_name = "portal/pages/quienes_somos/quienes_somos.html"
    page_key = "quienes"
    page_title = "Quiénes somos"


class ServiciosView(PortalPageView):
    template_name = "portal/pages/servicios/servicios.html"
    page_key = "servicios"
    page_title = "Servicios"


class NormativaView(PortalPageView):
    template_name = "portal/pages/normativa/normativa.html"
    page_key = "normativa"
    page_title = "Normativa"


class NoticiasView(PortalPageView):
    template_name = "portal/pages/noticias/noticias.html"
    page_key = "noticias"
    page_title = "Noticias"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proveedor = proveedor_novedades()
        context["novedades"] = proveedor() if proveedor else {}
        return context
