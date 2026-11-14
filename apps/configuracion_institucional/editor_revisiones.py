"""Editor guiado y publicaciones academicas; historial sin cambios directos."""
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from apps.core.presentation.administracion import AdministracionTraducida


class ConfirmarRevisionForm(forms.Form):
    base_esperada = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    confirmar = forms.BooleanField(label=_("Confirmo que revisé la propuesta y su compatibilidad antes de publicarla."))


class EditorRevisionAdmin(AdministracionTraducida):
    change_form_template = 'admin/configuracion_institucional/editor_revision.html'
    list_display = ('titulo', 'institucion_codigo', 'estado', 'en_uso', 'autor', 'fecha')
    list_filter = ('estado',)
    actions = None

    def nombre_url(self, accion):
        return f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_{accion}'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('autor').annotate(
            es_vigente=Exists(self.modelo_publicacion.objects.filter(revision_id=OuterRef('pk'))),
        )

    @admin.display(description=_('En uso'), boolean=True)
    def en_uso(self, obj):
        return obj.es_vigente

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def render_change_form(self, request, context, *args, **kwargs):
        context['puede_publicar_revision'] = self.puede_publicar(request.user)
        context['puede_crear_revision'] = self.has_add_permission(request)
        context['crear_revision_url'] = reverse(self.nombre_url('add'))
        context['publicar_revision_url'] = reverse(self.nombre_url('publicar'), args=[context['original'].pk]) if context.get('original') else ''
        context['aviso_historial'] = self.aviso_historial
        return super().render_change_form(request, context, *args, **kwargs)

    @method_decorator(require_http_methods(['GET', 'POST']))
    def add_view(self, request, form_url='', extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        datos = self.serializar(self.datos_actuales())
        fuente = request.GET.get('fuente', '')
        if fuente:
            if not fuente.isdigit() or not self.has_view_permission(request):
                raise PermissionDenied
            origen = get_object_or_404(self.model, pk=fuente)
            try:
                datos = self.serializar(self.validar_revision(origen))
            except (ValueError, ValidationError):
                raise PermissionDenied from None
        form = self.formulario(request.POST if request.method == 'POST' else None,
                                   initial={'titulo': self.titulo_inicial, 'contenido': datos})
        if request.method == 'POST' and form.is_valid():
            revision = self.guardar_borrador(form.cleaned_data['contenido'], request.user,
                                                titulo=form.cleaned_data['titulo'])
            self.log_addition(request, revision, str(self.mensaje_creado))
            messages.success(request, self.mensaje_guardado)
            return redirect(self.nombre_url('change'), revision.pk)
        return TemplateResponse(request, self.plantilla_editor, {
            **self.admin_site.each_context(request), 'opts': self.model._meta,
            'title': self.titulo_editor, 'form': form, 'media': form.media,
            'volver_url': reverse(self.nombre_url('changelist')),
        })

    def get_urls(self):
        return [path('<int:revision_id>/publicar/', self.admin_site.admin_view(self.publicar),
                     name=self.nombre_url('publicar').removeprefix('admin:'))] + super().get_urls()

    @method_decorator(require_http_methods(['GET', 'POST']))
    def publicar(self, request, revision_id):
        if not self.puede_publicar(request.user):
            raise PermissionDenied
        revision = get_object_or_404(self.model, pk=revision_id)
        actual = self.modelo_publicacion.objects.select_related('revision').filter(pk=1).first()
        actual_id = actual.revision_id if actual else None
        try:
            propuesto = self.validar_revision(revision)
        except (ValueError, ValidationError):
            raise PermissionDenied from None
        problemas = []
        resultados = []
        try:
            _propuesto, _relaciones, resultados = self.revisar_compatibilidad(revision, actual.revision if actual else None)
        except ValidationError as exc:
            problemas = exc.messages
        if revision.estado == 'borrador' and revision.basada_en_id != actual_id:
            problemas.append(_('Este borrador tiene una base anterior. Crea una revisión nueva con los datos actuales.'))
        form = ConfirmarRevisionForm(request.POST if request.method == 'POST' else None,
                                    initial={'base_esperada': actual_id})
        if request.method == 'POST' and form.is_valid():
            try:
                publicada = self.publicar_revision(revision.pk, request.user, base_esperada=form.cleaned_data['base_esperada'])
            except ValidationError as exc:
                for mensaje in exc.messages:
                    form.add_error(None, mensaje)
            else:
                self.log_addition(request, publicada, str(self.mensaje_publicado))
                messages.success(request, self.mensaje_publicado)
                return redirect(self.nombre_url('changelist'))
        return TemplateResponse(request, self.plantilla_publicar, {
            **self.admin_site.each_context(request), 'opts': self.model._meta,
            'title': self.titulo_publicar, 'revision': revision, 'catalogo': propuesto,
            'form': form, 'media': self.formulario().media, 'problemas': problemas,
            'campos_revisados': len(resultados),
            'volver_url': reverse(self.nombre_url('change'), args=[revision.pk]),
        })
