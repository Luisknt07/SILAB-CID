"""Editor de filas accesible; payload unico validado tambien sin JavaScript."""

from django import forms
from django.utils.translation import gettext, gettext_lazy as _

from apps.core.catalogos import TIPOS_USUARIO, catalogo_academico, datos_catalogo
from ..formularios import JsonRevisionField, TituloRevisionForm
from config.catalogos import configuracion_catalogo


class CatalogoWidget(forms.Textarea):
    template_name = 'admin/configuracion_institucional/catalogos/widget.html'

    class Media:
        css = {'all': ['configuracion_institucional/editor.css']}
        js = ['configuracion_institucional/catalogos.js']

    def get_context(self, name, value, attrs):
        contexto = super().get_context(name, value, attrs)
        contexto['tipos_catalogo'] = [(codigo, gettext(etiqueta)) for codigo, etiqueta in TIPOS_USUARIO if codigo != 'externo']
        return contexto


class ContenidoCatalogoField(JsonRevisionField):
    cargar = staticmethod(configuracion_catalogo)
    validar = staticmethod(catalogo_academico)
    serializar = staticmethod(datos_catalogo)
    clave_entorno = 'ACADEMIC_CATALOG_JSON'
    mensaje_error = _('Revisa los códigos, los nombres y las relaciones del catálogo.')


class CatalogoRevisionForm(TituloRevisionForm):
    contenido = ContenidoCatalogoField(label=_('Catálogo académico'), max_length=1_000_000,
                                       widget=CatalogoWidget(attrs={'rows': 18}), strip=False)
