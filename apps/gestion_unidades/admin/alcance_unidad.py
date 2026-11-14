"""Autorización por asignación para los administradores de expedientes por tipo."""
from django.contrib import admin
from django import forms
from django.core.exceptions import PermissionDenied
from apps.gestion_unidades.admin.acceso import unidades_editables


class AlcanceUnidadAdmin:
    def _local(self, request):
        return not request.user.is_superuser and unidades_editables(request.user).exists()

    def _unidades(self, request):
        return unidades_editables(request.user).filter(dependencia__in=self.codigos())

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if self._local(request):
            consulta = consulta.filter(**{f'{self.ruta}__in': self._unidades(request)}).distinct()
        return consulta

    def has_module_permission(self, request):
        return self._unidades(request).exists() if self._local(request) else super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if self._local(request):
            return self.get_queryset(request).filter(pk=obj.pk).exists() if obj else self._unidades(request).exists()
        return super().has_view_permission(request, obj)

    def _permiso_escritura(self, request, obj, metodo):
        original = getattr(super(), metodo)
        if not self._local(request):
            return original(request) if metodo == 'has_add_permission' else original(request, obj)
        if not self.has_view_permission(request, obj):
            return False
        # Las fichas compartidas y los registros sin unidad se asignan desde Gestión.
        if self.ruta_inversa:
            return False
        # Conservar restricciones expresas del flujo original (reservas, documentos, auditoría).
        if original.__func__ is not getattr(admin.ModelAdmin, metodo):
            return original(request) if metodo == 'has_add_permission' else original(request, obj)
        return True

    def has_add_permission(self, request):
        return self._permiso_escritura(request, None, 'has_add_permission')

    def has_change_permission(self, request, obj=None):
        return self._permiso_escritura(request, obj, 'has_change_permission')

    def has_delete_permission(self, request, obj=None):
        # Las bajas operativas usan los comandos auditados del panel.
        return False if self._local(request) else super().has_delete_permission(request, obj)

    def get_actions(self, request):
        return {} if self._local(request) else super().get_actions(request)

    def get_list_filter(self, request):
        # Los filtros relacionados estándar enumeran registros ajenos al queryset.
        if self._local(request):
            return []
        return super().get_list_filter(request)

    def _acotar_campo(self, campo, request):
        if campo is None or not hasattr(campo, 'queryset') or not self._local(request):
            return campo
        from apps.directorio_unidades.models.core import Unidad
        from apps.integraciones.admin.por_tipo import ruta_a_la_unidad, ruta_es_inversa, AcotadoPorTipologia
        modelo = campo.queryset.model
        if modelo._meta.concrete_model is Unidad:
            campo.queryset = campo.queryset.filter(pk__in=self._unidades(request))
        else:
            ruta = ruta_a_la_unidad(modelo)
            if ruta and ruta_es_inversa(modelo, ruta):
                # Usuarios, períodos y catálogos no pertenecen a una unidad por
                # el mero hecho de ser referenciados desde sus registros.
                expedientes = {m._meta.concrete_model for m, a in self.admin_site._registry.items()
                               if isinstance(a, AcotadoPorTipologia)}
                if modelo._meta.concrete_model not in expedientes:
                    return campo
            if ruta:
                campo.queryset = campo.queryset.filter(**{f'{ruta}__in': self._unidades(request)}).distinct()
        return campo

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        return self._acotar_campo(super().formfield_for_foreignkey(db_field, request, **kwargs), request)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        return self._acotar_campo(super().formfield_for_manytomany(db_field, request, **kwargs), request)

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)
        if not self._local(request):
            return base
        administrador = self
        class FormularioAcotado(base):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                for campo in self.fields.values():
                    administrador._acotar_campo(campo, request)
                    if isinstance(campo, forms.ModelMultipleChoiceField):
                        campo.widget = forms.SelectMultiple(choices=campo.choices)
                    elif isinstance(campo, forms.ModelChoiceField):
                        campo.widget = forms.Select(choices=campo.choices)
        return FormularioAcotado

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if self._local(request) and all(campo.name in campos for campo in self.model._meta.fields):
            campos.extend(campo.name for campo in self.model._meta.many_to_many)
        if self._local(request) and obj and not self.ruta_inversa:
            campos.append(self.ruta.split('__')[0])
        return campos

    def save_model(self, request, obj, form, change):
        if self._local(request):
            if change and not self.has_change_permission(request, obj):
                raise PermissionDenied
            valor = obj
            for parte in self.ruta.split('__'):
                valor = getattr(valor, parte, None)
                if valor is None:
                    raise PermissionDenied('El registro debe pertenecer a tu unidad.')
            if not self._unidades(request).filter(pk=valor.pk).exists():
                raise PermissionDenied('El registro está fuera de tu unidad.')
        super().save_model(request, obj, form, change)
