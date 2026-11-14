"""Administracion de habilitacion; los derechos de despliegue no son editables."""
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from apps.core.presentation.administracion import AdministracionTraducida
from apps.core.presentation.identidad import identidad_de_despliegue
from config.capacidades import CAPACIDADES_CONTROLADAS
from .models import CambioCapacidad, EstadoCapacidad
from .selectors import estado_actual
from .services import cambiar_habilitacion


PRESENTACION_CAPACIDADES = {
    ('portal', 'portada_inicio'): {
        'nombre': _('Inicio editorial'),
        'descripcion': _('La suspensión bloquea nuevas revisiones y publicaciones.'),
        'continuidad': _('Inicio muestra su portada base y conserva el historial y sus exportaciones.'),
    },
    ('reservas', 'reservas_operativas'): {
        'nombre': _('Operación de reservas'),
        'descripcion': _('La suspensión bloquea nuevas reservas y cambios operativos.'),
        'continuidad': _('La consulta, el historial y los documentos existentes siguen disponibles.'),
    },
}


class HabilitacionForm(forms.Form):
    habilitada = forms.BooleanField(label=_('Habilitar capacidad'), required=False)
    version_esperada = forms.IntegerField(min_value=0, max_value=9223372036854775806, widget=forms.HiddenInput)
    motivo = forms.CharField(label=_('Motivo del cambio'), max_length=500,
                            widget=forms.Textarea(attrs={'rows': 3, 'cols': 30}))
    confirmar = forms.BooleanField(label=_('Confirmo el cambio de habilitación institucional.'))

    def clean(self):
        datos = super().clean()
        if set(self.data) - set(self.fields) - {'csrfmiddlewaretoken'}:
            raise forms.ValidationError(_('Solo puedes cambiar la habilitación institucional.'))
        return datos


class ArchivoCapacidadesAdmin(AdministracionTraducida):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def get_queryset(self, request):
        producto, institucion = identidad_de_despliegue()
        prefijo = 'estado__' if self.model is CambioCapacidad else ''
        return super().get_queryset(request).filter(**{
            prefijo + 'producto_codigo': producto.codigo, prefijo + 'institucion_codigo': institucion.siglas})


@admin.register(EstadoCapacidad)
class EstadoCapacidadAdmin(ArchivoCapacidadesAdmin):
    change_list_template = 'admin/configuracion_institucional/capacidades/listado.html'
    list_display = ('modulo', 'capacidad', 'habilitada', 'version')

    class Media:
        css = {'all': ('configuracion_institucional/capacidades.css',)}

    def puede_administrar(self, request):
        return self.has_view_permission(request) and request.user.has_perm('configuracion_institucional.administrar_capacidades')

    def get_urls(self):
        return [
            path('configurar/', self.admin_site.admin_view(self.configurar),
                 name='configuracion_institucional_estadocapacidad_configurar'),
            path('configurar/<str:modulo>/<str:capacidad>/',
                 self.admin_site.admin_view(self.configurar_capacidad),
                 name='configuracion_institucional_estadocapacidad_configurar_capacidad'),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        capacidades = []
        for modulo, capacidad in CAPACIDADES_CONTROLADAS:
            habilitada, version = estado_actual(modulo, capacidad)
            presentacion = PRESENTACION_CAPACIDADES[(modulo, capacidad)]
            capacidades.append({
                'modulo': modulo,
                'capacidad': capacidad,
                'nombre': presentacion['nombre'],
                'habilitada': habilitada,
                'version': version,
                'url': reverse(
                    'admin:configuracion_institucional_estadocapacidad_configurar_capacidad',
                    args=(modulo, capacidad),
                ),
            })
        return super().changelist_view(request, {
            **(extra_context or {}),
            'capacidades_puede_administrar': self.puede_administrar(request),
            'capacidades': capacidades,
            # Contrato conservado para enlaces y pruebas de la primera capacidad.
            'capacidades_configurar_url': reverse(
                'admin:configuracion_institucional_estadocapacidad_configurar'
            ),
        })

    @method_decorator(require_http_methods(['GET', 'POST']))
    def configurar(self, request):
        return self._configurar(request, 'portal', 'portada_inicio')

    @method_decorator(require_http_methods(['GET', 'POST']))
    def configurar_capacidad(self, request, modulo, capacidad):
        return self._configurar(request, modulo, capacidad)

    def _configurar(self, request, modulo, capacidad):
        if not self.puede_administrar(request):
            raise PermissionDenied
        clave = (modulo, capacidad)
        if clave not in CAPACIDADES_CONTROLADAS or clave not in PRESENTACION_CAPACIDADES:
            raise Http404
        presentacion = PRESENTACION_CAPACIDADES[clave]
        habilitada, version = estado_actual(modulo, capacidad)
        form = HabilitacionForm(request.POST if request.method == 'POST' else None,
                               initial={'habilitada': habilitada, 'version_esperada': version})
        form.fields['habilitada'].label = _('Habilitar %(capacidad)s') % {
            'capacidad': presentacion['nombre']
        }
        if request.method == 'POST' and form.is_valid():
            try:
                cambio = cambiar_habilitacion(modulo, capacidad, form.cleaned_data['habilitada'], request.user,
                    version_esperada=form.cleaned_data['version_esperada'], motivo=form.cleaned_data['motivo'])
            except ValidationError as error:
                form.add_error(None, error.messages)
            else:
                self.log_addition(request, cambio, str(_('Habilitación institucional modificada.')))
                messages.success(request, _('Habilitación institucional modificada.'))
                return redirect('admin:configuracion_institucional_estadocapacidad_changelist')
        return TemplateResponse(request, 'admin/configuracion_institucional/capacidades/configurar.html', {
            **self.admin_site.each_context(request), 'opts': self.model._meta, 'media': self.media,
            'title': _('Configurar %(capacidad)s') % {'capacidad': presentacion['nombre']},
            'form': form,
            'descripcion_capacidad': presentacion['descripcion'],
            'continuidad_capacidad': presentacion['continuidad'],
            'volver_url': reverse('admin:configuracion_institucional_estadocapacidad_changelist')})


@admin.register(CambioCapacidad)
class CambioCapacidadAdmin(ArchivoCapacidadesAdmin):
    list_display = ('estado', 'habilitada_anterior', 'habilitada_nueva', 'version', 'autor', 'fecha')
