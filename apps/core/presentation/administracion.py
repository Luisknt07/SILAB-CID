"""Traducción de presentación sin modificar modelos, permisos ni identificadores."""

from django.contrib import admin
from django.utils.translation import gettext

from .traducciones import FormularioTraducidoMixin


def _formulario(base):
    if issubclass(base, FormularioTraducidoMixin):
        return base
    return type("FormularioTraducido", (FormularioTraducidoMixin, base), {})


class _SeccionesTraducidas:
    def get_fieldsets(self, request, obj=None):
        return [(gettext(str(nombre)) if nombre else nombre, opciones)
                for nombre, opciones in super().get_fieldsets(request, obj)]


class AdministracionTraducida(_SeccionesTraducidas, admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        return _formulario(super().get_form(request, obj, **kwargs))


class _InlineTraducido(_SeccionesTraducidas):
    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)
        # Grappelli solo pliega bloques `grp-collapse`; la clase `collapse` de
        # Django no hace nada bajo su plantilla. Se declara `collapse` y aqui se
        # traduce: el grupo abre para verse de un vistazo y cada elemento queda
        # plegado (valor de Grappelli), así una ficha no abre todo su contenido.
        if self.classes and 'collapse' in self.classes:
            self.classes = ['grp-collapse', 'grp-open',
                            *(clase for clase in self.classes if clase != 'collapse')]

    def get_formset(self, request, obj=None, **kwargs):
        formulario = super().get_formset(request, obj, **kwargs)
        formulario.form = _formulario(formulario.form)
        return formulario


class TablaTraducida(_InlineTraducido, admin.TabularInline):
    pass


class BloqueTraducido(_InlineTraducido, admin.StackedInline):
    pass
