"""Editor de Inicio, sin permisos ni datos de las otras secciones del portal."""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.cache import patch_cache_control
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_GET

from apps.core.presentation.administracion import AdministracionTraducida
from .defaults import contenido_base
from .control import inicio_activo
from .forms import ETIQUETAS, ConfirmarInicioForm, PortadaInicioForm
from .models import PublicacionInicio, RevisionInicio
from .selectors import portada_de_revision
from .services import exportar_revision, guardar_borrador, publicar_revision, validar_revision


@admin.register(RevisionInicio)
class RevisionInicioAdmin(AdministracionTraducida):
    change_form_template = 'admin/portal/inicio/revision.html'
    list_display = ('titulo', 'estado', 'en_uso', 'autor', 'fecha')
    list_filter = ('estado',)
    actions = None

    class Media:
        css = {'all': ('portal/editorial.css',)}

    def url(self, accion, revision=None):
        return reverse(f'admin:portal_revisioninicio_{accion}', args=[revision.pk] if revision else None)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('autor').annotate(
            es_vigente=Exists(PublicacionInicio.objects.filter(revision_id=OuterRef('pk'))))

    @admin.display(description=_('En uso'), boolean=True)
    def en_uso(self, obj):
        return obj.es_vigente

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return super().has_add_permission(request) and inicio_activo()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def puede_publicar(self, request):
        return self.has_view_permission(request) and request.user.has_perm('portal.publicar_inicio') and inicio_activo()

    def contexto(self, request, **datos):
        return {**self.admin_site.each_context(request), 'opts': self.model._meta,
                'media': self.media, **datos}

    def datos_revision(self, revision):
        try:
            return validar_revision(revision)
        except ValidationError:
            raise PermissionDenied from None

    def render_change_form(self, request, context, *args, **kwargs):
        revision = context.get('original')
        if revision:
            context.update(inicio_crear_url=self.url('add'),
                           inicio_preview_url=self.url('previsualizar', revision),
                           inicio_exportar_url=self.url('exportar', revision),
                           inicio_publicar_url=self.url('publicar', revision),
                           inicio_puede_crear=self.has_add_permission(request),
                           inicio_puede_publicar=self.puede_publicar(request))
        return super().render_change_form(request, context, *args, **kwargs)

    def get_urls(self):
        return [path(f'<int:revision_id>/{accion}/', self.admin_site.admin_view(vista),
                     name=f'portal_revisioninicio_{accion}')
                for accion, vista in [('publicar', self.publicar), ('previsualizar', self.previsualizar),
                                     ('exportar', self.exportar)]] + super().get_urls()

    @method_decorator(require_GET)
    def exportar(self, request, revision_id):
        try:
            datos = exportar_revision(revision_id, request.user)
        except RevisionInicio.DoesNotExist:
            raise Http404 from None
        except ValidationError:
            raise PermissionDenied from None
        respuesta = JsonResponse(datos, json_dumps_params={'ensure_ascii': False})
        respuesta['Content-Disposition'] = f'attachment; filename="portada-inicio-{revision_id}.json"'
        respuesta['X-Content-Type-Options'] = 'nosniff'
        patch_cache_control(respuesta, private=True, no_store=True)
        return respuesta

    @method_decorator(require_http_methods(['GET', 'POST']))
    def add_view(self, request, form_url='', extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        datos = contenido_base()
        actual = PublicacionInicio.objects.select_related('revision').filter(pk=1).first()
        actual_id = actual.revision_id if actual else None
        # El permiso de creación no permite consultar ni copiar historia privada.
        if self.has_view_permission(request):
            if actual and actual.revision:
                datos = self.datos_revision(actual.revision)
        fuente = request.GET.get('fuente', '')
        if fuente:
            if (not fuente.isascii() or not fuente.isdecimal() or len(fuente) > 19
                    or not self.has_view_permission(request)):
                raise PermissionDenied
            datos = self.datos_revision(get_object_or_404(RevisionInicio, pk=fuente))
        form = PortadaInicioForm(request.POST if request.method == 'POST' else None,
                                contenido=datos, initial={'titulo': _('Revisión de la portada'), 'base_esperada': actual_id})
        if request.method == 'POST' and form.is_valid():
            try:
                revision = guardar_borrador(form.cleaned_data['contenido'], request.user,
                                            titulo=form.cleaned_data['titulo'], base_esperada=form.cleaned_data['base_esperada'])
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                self.log_addition(request, revision, str(_('Borrador de Inicio creado.')))
                messages.success(request, _('Borrador guardado. Revisa ambos idiomas antes de publicar.'))
                return redirect(self.url('change', revision) if self.has_view_permission(request) else self.url('add'))
        return TemplateResponse(request, 'admin/portal/inicio/editor.html', self.contexto(
            request, title=_('Crear portada de Inicio'), form=form, volver_url=self.url('changelist')))

    @method_decorator(require_GET)
    def previsualizar(self, request, revision_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        revision = get_object_or_404(RevisionInicio, pk=revision_id)
        try:
            portada = portada_de_revision(revision)
        except ValidationError:
            raise PermissionDenied from None
        respuesta = render(request, 'portal/pages/inicio/inicio.html', {
            'active_section': 'home', 'portada_inicio': portada, 'inicio_preview': True,
            'inicio_volver_url': self.url('change', revision),
        })
        patch_cache_control(respuesta, private=True, no_store=True)
        return respuesta

    @method_decorator(require_http_methods(['GET', 'POST']))
    def publicar(self, request, revision_id):
        if not self.puede_publicar(request):
            raise PermissionDenied
        revision = get_object_or_404(RevisionInicio, pk=revision_id)
        try:
            contenido = validar_revision(revision)
        except ValidationError:
            raise PermissionDenied from None
        actual = PublicacionInicio.objects.select_related('revision').filter(pk=1).first()
        actual_id = actual.revision_id if actual else None
        form = ConfirmarInicioForm(request.POST if request.method == 'POST' else None,
                                   initial={'base_esperada': actual_id})
        if request.method == 'POST' and form.is_valid():
            try:
                publicada = publicar_revision(revision.pk, request.user,
                                              base_esperada=form.cleaned_data['base_esperada'])
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                self.log_addition(request, publicada, str(_('Portada de Inicio publicada.')))
                messages.success(request, _('Portada de Inicio publicada.'))
                return redirect(self.url('changelist'))
        return TemplateResponse(request, 'admin/portal/inicio/publicar.html', self.contexto(
            request, title=_('Revisar y publicar Inicio'), revision=revision, contenido=contenido,
            grupos=[(idioma, [(ETIQUETAS[campo], texto) for campo, texto in textos.items()])
                    for idioma, textos in contenido.items()],
            form=form, preview_url=self.url('previsualizar', revision),
            volver_url=self.url('change', revision),
            base_obsoleta=revision.estado == 'borrador' and revision.basada_en_id != actual_id))
