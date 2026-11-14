"""Editor de presentacion con confirmacion de publicacion e historial de lectura."""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Exists, OuterRef
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from apps.core.presentation.administracion import AdministracionTraducida
from apps.core.presentation.identidad import identidad_actual, identidad_de_despliegue

from .models import CAMPOS_PRESENTACION, PublicacionInstitucional, RevisionPresentacion
from .selectors import identidad_de_revision
from .imagenes import CAMPOS_IMAGENES, preparar_imagen
from .paleta import PaletaField
from .widgets import LogoPreviewInput
from .services import guardar_borrador, puede_publicar, publicar_revision
from .versionado import actor_con_permiso
from .catalogos.admin import RevisionCatalogoAcademicoAdmin
from .catalogos.models import RevisionCatalogoAcademico

from .niveles.admin import RevisionNivelesAcademicosAdmin
from .niveles.models import RevisionNivelesAcademicos
from .calendario.admin import RevisionPoliticaCalendarioAdmin
from .calendario.models import RevisionPoliticaCalendario

admin.site.register(RevisionCatalogoAcademico, RevisionCatalogoAcademicoAdmin)
admin.site.register(RevisionNivelesAcademicos, RevisionNivelesAcademicosAdmin)
admin.site.register(RevisionPoliticaCalendario, RevisionPoliticaCalendarioAdmin)
from .capacidades import admin as capacidades_admin  # noqa: F401,E402
from .tipologias import admin as tipologias_admin  # noqa: F401,E402


class ConfirmarPublicacionForm(forms.Form):
    base_esperada = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    confirmar = forms.BooleanField(label=_('Confirmo que revisé estos datos públicos y quiero publicarlos.'))


class PresentacionForm(forms.ModelForm):
    paleta = PaletaField(label=_('Paleta institucional'))
    fuente_imagenes = forms.IntegerField(required=False, min_value=1, max_value=9223372036854775807,
                                        widget=forms.HiddenInput)
    def __init__(self, *args, **kwargs):
        actor = kwargs.pop('actor', None)
        super().__init__(*args, **kwargs)
        self._fuente_invalida = False
        # Admin aplica initial solamente en GET. Recuperar las imágenes desde una
        # revisión identificada en POST, nunca desde rutas ocultas del cliente.
        if self.is_bound and 'fuente_imagenes' in self.fields:
            fuente = str(self.data.get('fuente_imagenes', ''))
            if fuente:
                self._fuente_invalida = True
                if fuente.isdigit() and len(fuente) <= 19 and int(fuente) <= 9223372036854775807:
                    producto, institucion = identidad_de_despliegue()
                    origen = RevisionPresentacion.objects.filter(pk=int(fuente),
                        producto_codigo=producto.codigo, institucion_codigo=institucion.siglas).first()
                    if origen and origen.estado != 'publicada':
                        try:
                            with transaction.atomic():
                                actor_con_permiso(actor, 'configuracion_institucional.view_revisionpresentacion')
                        except PermissionDenied:
                            origen = None
                    if origen:
                        self.initial.update({campo: getattr(origen, campo) for campo in CAMPOS_IMAGENES})
                        self._fuente_invalida = False
        for campo in CAMPOS_IMAGENES:
            if campo in self.fields:
                self.fields[campo].widget.attrs.update({'accept': 'image/png,image/jpeg,image/webp', 'style': 'max-width:100%;box-sizing:border-box'})

    def clean(self):
        datos = super().clean()
        if self._fuente_invalida:
            self.add_error('fuente_imagenes', _('La revisión de imágenes no está disponible para este editor. Recarga el formulario.'))
        for campo in CAMPOS_IMAGENES:
            archivo = datos.get(campo)
            if archivo and not getattr(archivo, '_committed', False):
                try:
                    datos[campo] = preparar_imagen(archivo)
                except ValidationError as exc:
                    self.add_error(campo, exc)
        return datos

    class Meta:
        model = RevisionPresentacion
        fields = CAMPOS_PRESENTACION
        field_classes = {campo: forms.FileField for campo in CAMPOS_IMAGENES}
        widgets = {campo: LogoPreviewInput() for campo in CAMPOS_IMAGENES}


GRUPOS_PRESENTACION = (
    (_('1. Identidad y contactos'), {
        'description': _('Nombres y datos públicos que aparecen en la cabecera, el pie, los correos y los documentos. '
                        'No cambian las siglas, los códigos, los permisos ni las credenciales del despliegue.'),
        'fields': ('nombre_producto', 'nombre_corto_producto', 'nombre_institucion',
                   'telefono', 'correo', 'ubicacion'),
    }),
    (_('2. Logotipos'), {
        'description': _('Sube aquí los logotipos. Se usan en el portal y también en los PDF: comprobantes, guías, '
                        'prácticas y reportes. Si dejas una variante vacía, el sistema usa la más parecida que exista.'),
        'fields': ('logo_claro', 'logo_oscuro', 'logo_movil_claro', 'logo_movil_oscuro', 'logo_secundario_subido'),
    }),
    (_('3. Logotipos de respaldo (avanzado)'), {
        'classes': ('grp-collapse', 'grp-closed', 'collapse'),
        'description': _('Solo para imágenes ya instaladas en los archivos estáticos del despliegue. Se usan cuando no '
                        'hay ningún logotipo subido arriba. Si no sabes qué poner, deja estos campos como están.'),
        'fields': ('logo', 'logo_secundario'),
    }),
    (_('4. Colores, tipografía y acabados'), {
        'description': _('Sin marcar “Usar paleta personalizada” se conserva el diseño actual. La vista previa muestra '
                        'el efecto antes de guardar; el servidor vuelve a comprobar el contraste al publicar.'),
        'fields': ('paleta',),
    }),
)


@admin.register(RevisionPresentacion)
class RevisionPresentacionAdmin(AdministracionTraducida):
    form = PresentacionForm
    change_form_template = 'admin/configuracion_institucional/revision_form.html'
    change_list_template = 'admin/configuracion_institucional/revision_list.html'
    list_display = ('nombre_corto_producto', 'institucion_codigo', 'estado', 'en_uso', 'acciones', 'autor', 'fecha')
    list_filter = ('estado',)
    actions = None

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)
        class FormConAutor(base):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, actor=request.user, **form_kwargs)
        return FormConAutor

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('autor').annotate(
            es_vigente=Exists(PublicacionInstitucional.objects.filter(revision_id=OuterRef('pk'))),
        )

    @admin.display(description=_('En uso'), boolean=True)
    def en_uso(self, obj):
        return obj.es_vigente

    @admin.display(description=_('Acciones'))
    def acciones(self, obj):
        """Publicar y duplicar desde el listado; el historial nunca se borra."""
        enlaces = []
        if self._puede_publicar and not obj.es_vigente:
            enlaces.append((
                reverse('admin:configuracion_institucional_revisionpresentacion_publicar', args=[obj.pk]),
                _('Restaurar esta presentación') if obj.estado == 'publicada' else _('Revisar y publicar'),
            ))
        if self._puede_crear:
            enlaces.append((
                f"{reverse('admin:configuracion_institucional_revisionpresentacion_add')}?fuente={obj.pk}",
                _('Crear revisión desde estos datos'),
            ))
        if not enlaces:
            return format_html('<span class="institution-revision-current">{}</span>', _('Presentación vigente'))
        return format_html_join(' · ', '<a href="{}">{}</a>', enlaces)

    def changelist_view(self, request, extra_context=None):
        # Se resuelven una vez por listado en lugar de por fila.
        self._puede_publicar = puede_publicar(request.user)
        self._puede_crear = self.has_add_permission(request)
        return super().changelist_view(request, extra_context)

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields] if obj else []

    def get_fields(self, request, obj=None):
        return self.get_readonly_fields(request, obj) if obj else CAMPOS_PRESENTACION

    def get_fieldsets(self, request, obj=None):
        if obj:
            return super().get_fieldsets(request, obj)
        return GRUPOS_PRESENTACION

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_changeform_initial_data(self, request):
        producto, institucion = identidad_actual()
        datos = {'nombre_producto': producto.nombre, 'nombre_corto_producto': producto.nombre_corto,
                 'nombre_institucion': institucion.nombre,
                 **{campo: getattr(institucion, campo) for campo in CAMPOS_PRESENTACION[3:] if campo not in CAMPOS_IMAGENES}}
        datos['paleta'] = dict(institucion.paleta)
        archivos_actuales = RevisionPresentacion(**dict(institucion.imagenes))
        datos.update({campo: getattr(archivos_actuales, campo) for campo in CAMPOS_IMAGENES})
        datos['fuente_imagenes'] = None
        if institucion.imagenes:
            imagenes = dict(institucion.imagenes)
            datos['fuente_imagenes'] = RevisionPresentacion.objects.filter(
                estado='publicada', institucion_codigo=institucion.siglas,
                producto_codigo=producto.codigo,
                **{campo: imagenes.get(campo, '') for campo in CAMPOS_IMAGENES}
            ).values_list('pk', flat=True).first()
        fuente = request.GET.get('fuente', '')
        if fuente.isdigit() and self.has_view_permission(request):
            origen = get_object_or_404(RevisionPresentacion, pk=fuente)
            try:
                identidad_de_revision(origen, *identidad_de_despliegue())
            except (ValueError, ValidationError):
                raise PermissionDenied from None
            datos = {campo: getattr(origen, campo) for campo in CAMPOS_PRESENTACION}
            datos['fuente_imagenes'] = origen.pk
        return datos

    def save_model(self, request, obj, form, change):
        guardar_borrador(obj, request.user)

    def render_change_form(self, request, context, *args, **kwargs):
        context['puede_publicar_presentacion'] = puede_publicar(request.user)
        context['puede_crear_presentacion'] = self.has_add_permission(request)
        return super().render_change_form(request, context, *args, **kwargs)

    def get_urls(self):
        return [path('<int:revision_id>/publicar/', self.admin_site.admin_view(self.publicar),
                     name='configuracion_institucional_revisionpresentacion_publicar')] + super().get_urls()

    @method_decorator(require_http_methods(['GET', 'POST']))
    def publicar(self, request, revision_id):
        if not puede_publicar(request.user):
            raise PermissionDenied
        revision = get_object_or_404(RevisionPresentacion, pk=revision_id)
        try:
            identidad_de_revision(revision, *identidad_de_despliegue())
        except (ValueError, ValidationError):
            raise PermissionDenied from None
        puntero = PublicacionInstitucional.objects.filter(pk=1).first()
        actual_id = puntero.revision_id if puntero else None
        form = ConfirmarPublicacionForm(request.POST if request.method == 'POST' else None,
                                       initial={'base_esperada': actual_id})
        if request.method == 'POST' and form.is_valid():
            try:
                publicada = publicar_revision(revision.pk, request.user,
                                              base_esperada=form.cleaned_data['base_esperada'])
            except ValidationError as exc:
                for mensaje in exc.messages:
                    form.add_error(None, mensaje)
            else:
                self.log_addition(request, publicada, str(_('Presentación institucional publicada.')))
                messages.success(request, _('Presentación institucional publicada.'))
                return redirect('admin:configuracion_institucional_revisionpresentacion_changelist')
        contexto = {
            **self.admin_site.each_context(request), 'opts': self.model._meta,
            'title': _('Revisar y publicar presentación'), 'revision': revision, 'form': form,
            'datos_presentacion': [(self.model._meta.get_field(campo).verbose_name, getattr(revision, campo))
                                  for campo in CAMPOS_PRESENTACION if campo != 'paleta' and campo not in CAMPOS_IMAGENES],
            'paleta_propuesta': revision.paleta,
            'imagenes_propuestas': [(self.model._meta.get_field(c).verbose_name, getattr(revision, c).url) for c in CAMPOS_IMAGENES if getattr(revision, c)],
            'volver_url': reverse('admin:configuracion_institucional_revisionpresentacion_change',
                                  args=[revision.pk]),
        }
        return TemplateResponse(request, 'admin/configuracion_institucional/publicar.html', contexto)
