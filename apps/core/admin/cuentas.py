"""Alta guiada de cuentas y lectura de su alcance real."""
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria


class AltaCuentaForm(AdminUserCreationForm):
    email = forms.EmailField(label='Correo electrónico', required=True)
    unidad_administrada = forms.ModelChoiceField(
        label='Administrar una unidad', queryset=Unidad.objects.none(), required=False,
        help_text='Opcional. Otorga automáticamente la gestión completa de esa unidad. '
                  'Sin selección, se crea una cuenta de usuario sin privilegios de gestión. '
                  'Las unidades que ya tienen administrador se reasignan desde su ficha.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unidad_administrada'].queryset = Unidad.objects.filter(
            activo=True, administrador__isnull=True).order_by('nombre')

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo. Revisa la cuenta existente.')
        return email

    def clean_unidad_administrada(self):
        unidad = self.cleaned_data.get('unidad_administrada')
        if unidad:
            unidad = Unidad.objects.select_for_update().get(pk=unidad.pk)
            if unidad.administrador_id or not unidad.activo:
                raise ValidationError('La unidad ya tiene administrador o está inactiva. Recarga las opciones.')
        return unidad


class CuentasInstitucionalesAdmin(UserAdmin):
    add_form = AltaCuentaForm
    add_fieldsets = (
        ('Identidad y acceso', {'fields': ('username', 'first_name', 'last_name', 'email',
                                          'usable_password', 'password1', 'password2')}),
        ('Administrador de unidad (opcional)', {'fields': ('unidad_administrada',)}),
    )
    list_display = ('username', 'first_name', 'last_name', 'email', 'alcance', 'tipo_perfil', 'is_active', 'last_login')
    list_filter = ('is_active', 'is_superuser', 'is_staff', 'profile__tipo_usuario', 'unidades_administradas')
    readonly_fields = (*UserAdmin.readonly_fields, 'alcance')
    fieldsets = UserAdmin.fieldsets + (('Alcance de gestión', {'fields': ('alcance',),
        'description': 'La asignación de unidad otorga los permisos operativos automáticamente. '
                       'Staff y superusuario corresponden al administrador institucional, no al administrador de unidad.'}),)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission

    def changelist_view(self, request, extra_context=None):
        # Conserva la tabla y sus acciones para tareas administrativas avanzadas.
        tabla = request.GET.get('vista') == 'tabla' or '_popup' in request.GET or request.method != 'GET'
        query = request.GET.copy()
        query.pop('vista', None)
        request.GET = query
        if tabla:
            return super().changelist_view(request, extra_context)
        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        from apps.core.usuarios.directorio_unidades import agrupar_cuentas
        cl = self.get_changelist_instance(request)
        grupos, sin_unidad = agrupar_cuentas(cl.queryset, incluir_vacias=not bool(query))
        return TemplateResponse(request, 'admin/usuarios/por_unidad.html', {
            **self.admin_site.each_context(request), **(extra_context or {}),
            'title': 'Usuarios por tipo y unidad', 'opts': self.model._meta,
            'grupos': grupos, 'sin_unidad': sin_unidad,
            'busqueda': query.get('q', ''), 'total': cl.queryset.count(),
            'query': query.urlencode(),
        })

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile').prefetch_related(
            'unidades_administradas', 'responsabilidades_en_unidades__unidad')

    @admin.display(description='Acceso y unidades')
    def alcance(self, obj):
        if not obj.pk:
            return 'Se define al guardar la cuenta.'
        if obj.is_superuser:
            return 'Superadministrador · Todas las unidades'
        unidades = list(obj.unidades_administradas.all())
        if unidades:
            return 'Administrador de unidad · ' + '; '.join(u.nombre for u in unidades)
        personal = [f'{r.get_rol_display()}: {r.unidad.nombre}' for r in obj.responsabilidades_en_unidades.all() if r.activo]
        if personal:
            return '; '.join(personal)
        return 'Acceso institucional delegado' if obj.is_staff else 'Usuario solicitante (sin gestión de unidades)'

    @admin.display(description='Tipo de usuario')
    def tipo_perfil(self, obj):
        return obj.profile.get_tipo_usuario_display() if hasattr(obj, 'profile') else 'Sin perfil'

    def save_model(self, request, obj, form, change):
        unidad = form.cleaned_data.get('unidad_administrada') if not change else None
        if unidad:
            # El alta del admin está dentro de una transacción; evita sustituir otra asignación concurrente.
            unidad = Unidad.objects.select_for_update().get(pk=unidad.pk)
            if unidad.administrador_id:
                raise ValidationError('Esta unidad acaba de recibir un administrador. Recarga el formulario.')
            obj.is_staff = False
            obj.is_superuser = False
        super().save_model(request, obj, form, change)
        if unidad:
            unidad.administrador = obj
            unidad.save(update_fields=['administrador'])
            registrar_auditoria(request, unidad=unidad, accion='actualizar', objeto=unidad,
                               descripcion='Asignación de administrador al crear la cuenta',
                               anteriores={'administrador': None}, nuevos={'administrador': obj.pk})


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), CuentasInstitucionalesAdmin)
