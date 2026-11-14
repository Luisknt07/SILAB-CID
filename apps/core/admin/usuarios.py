"""Administración de perfiles institucionales con permisos especializados."""

from apps.core.presentation.administracion import AdministracionTraducida

from django.contrib import admin
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.core.models.usuarios import Decanato
from apps.core.models.usuarios_base import UserProfile
from apps.core.models.verificaciones import VerificacionInstitucional
from apps.core.usuarios.verificacion import estado_verificacion, puede_revisar, registrar_revision


class RevisionInstitucionalForm(forms.Form):
    decision = forms.ChoiceField(label=_('Decisión'), choices=VerificacionInstitucional.Decision.choices)
    fundamento = forms.CharField(
        label=_('Fundamento de la revisión'), max_length=2000, widget=forms.Textarea,
    )
    referencia = forms.CharField(label=_('Referencia de la evidencia'), max_length=250)
    vigente_hasta = forms.DateField(
        label=_('Vigente hasta'), required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    huella = forms.CharField(widget=forms.HiddenInput, max_length=64, min_length=64)


@admin.register(UserProfile)
class UserProfileAdmin(AdministracionTraducida):
    list_display = [
        'usuario_nombre', 'tipo_usuario', 'facultad', 'carrera',
        'nivel_academico', 'institucion', 'perfil_completo', 'verificacion',
    ]
    list_filter = ['tipo_usuario', 'facultad', 'carrera', 'nivel_academico']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'user__email', 'institucion', 'cedula',
    ]
    autocomplete_fields = ['user']
    fields = [
        'user', 'tipo_usuario', 'facultad', 'carrera', 'nivel_academico',
        'cedula', 'institucion', 'cargo', 'telefono', 'biografia', 'avatar',
        'verificacion', 'revision_institucional',
    ]
    readonly_fields = ['verificacion', 'revision_institucional']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def get_urls(self):
        return [path(
            '<int:object_id>/verificar/', self.admin_site.admin_view(self.verificar),
            name='core_userprofile_verificar',
        )] + super().get_urls()

    def verificar(self, request, object_id):
        perfil = get_object_or_404(UserProfile.objects.select_related('user'), pk=object_id)
        if not puede_revisar(request.user, perfil) or not self.has_view_permission(request, perfil):
            raise PermissionDenied
        estado = estado_verificacion(perfil)
        form = RevisionInstitucionalForm(
            request.POST if request.method == 'POST' else None,
            initial={'huella': estado['huella']},
        )
        if request.method == 'POST' and form.is_valid():
            try:
                registrar_revision(perfil_id=perfil.pk, revisor=request.user, **form.cleaned_data)
            except ValidationError as exc:
                # Los errores del perfil tienen campos que este formulario no edita.
                form.add_error(None, ValidationError(exc.messages))
            else:
                self.log_change(request, perfil, _('Revisión institucional registrada.'))
                self.message_user(request, _('Revisión institucional registrada.'))
                return redirect('admin:core_userprofile_verificar', object_id=perfil.pk)
        return TemplateResponse(request, 'admin/usuarios/verificar.html', {
            **self.admin_site.each_context(request), 'opts': self.model._meta,
            'title': _('Revisión institucional'), 'perfil': perfil, 'estado': estado,
            'form': form,
            'historial': Paginator(
                perfil.verificaciones_institucionales.select_related('revisor'), 20,
            ).get_page(request.GET.get('pagina')),
            'datos': (
                (_('Usuario'), perfil.user.get_full_name() or perfil.user.username),
                (_('Correo'), perfil.user.email),
                (_('Tipo de usuario'), perfil.get_tipo_usuario_display()),
                (_('Institución'), perfil.institucion),
                (_('Facultad'), perfil.get_facultad_display()),
                (_('Carrera'), perfil.get_carrera_display()),
                (_('Documento de identidad'), perfil.cedula),
            ),
        })

    @admin.display(description=_('Verificación institucional'))
    def verificacion(self, obj):
        if not obj.pk:
            return _('Pendiente de revisión institucional')
        return estado_verificacion(obj)['etiqueta']

    @admin.display(description=_('Revisión institucional'))
    def revision_institucional(self, obj):
        if not obj.pk:
            return _('Guarda el perfil antes de revisarlo.')
        return format_html('<a href="{}">{}</a>', reverse(
            'admin:core_userprofile_verificar', args=[obj.pk],
        ), _('Abrir revisión e historial'))

    @admin.display(description='Usuario', ordering='user__last_name')
    def usuario_nombre(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description=_('Datos completos'), boolean=True)
    def perfil_completo(self, obj):
        return obj.perfil_reserva_completo


@admin.register(VerificacionInstitucional)
class VerificacionInstitucionalAdmin(AdministracionTraducida):
    list_display = ['perfil', 'decision', 'revisor', 'fecha', 'vigente_hasta']
    list_filter = ['decision', 'fecha']
    search_fields = ['perfil__user__username', 'perfil__user__email']
    readonly_fields = [campo.name for campo in VerificacionInstitucional._meta.fields]
    actions = None

    def has_view_permission(self, request, obj=None):
        return puede_revisar(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Decanato)
class DecanatoAdmin(AdministracionTraducida):
    list_display = ['usuario', 'cargo']
    search_fields = [
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
        'cargo',
    ]
    autocomplete_fields = ['usuario']
