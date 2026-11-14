"""Administracion de tipologias: crear, ordenar, ocultar; nunca eliminar."""
import re

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.translation import gettext as _texto
from django.utils.translation import gettext_lazy as _

from apps.core.presentation.administracion import AdministracionTraducida
from .models import TipologiaUnidad


@admin.register(TipologiaUnidad)
class TipologiaUnidadAdmin(AdministracionTraducida):
    list_display = ('orden', 'codigo', 'nombre', 'nombre_plural', 'base', 'activa')
    list_display_links = ('codigo', 'nombre')
    list_filter = ('activa', 'base')
    search_fields = ('codigo', 'nombre', 'nombre_plural')
    ordering = ('orden', 'codigo')
    actions = None
    fieldsets = (
        (None, {
            'fields': ('codigo', 'nombre', 'nombre_plural', 'nombre_en', 'nombre_plural_en', 'descripcion'),
        }),
        (_('Presentación'), {
            'fields': ('icono', 'orden', 'activa', 'base'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # El codigo identifica unidades existentes y la base define su
        # comportamiento; ninguno cambia despues de crear la tipologia.
        return ('codigo', 'base') if obj else ()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        propias = [path(
            '<str:codigo>/publicacion/', self.admin_site.admin_view(self.cambiar_publicacion),
            name='configuracion_institucional_tipologiaunidad_publicacion',
        )]
        return propias + super().get_urls()

    def cambiar_publicacion(self, request, codigo):
        """Publica o retira del publico un tipo entero, desde su area del indice.

        Es el mismo campo `activa` del formulario; aqui se cambia con una
        casilla sin abrir la ficha. Solo quien puede editar tipologias.
        """
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        tipologia = get_object_or_404(TipologiaUnidad, codigo=codigo)
        if not self.has_change_permission(request, tipologia):
            raise PermissionDenied
        tipologia.activa = request.POST.get('activa') == '1'
        tipologia.save(update_fields=['activa'])
        estado = _texto('publicado al público') if tipologia.activa else _texto('retirado del público')
        self.log_change(request, tipologia, estado)
        self.message_user(request, _texto('«%(nombre)s» %(estado)s.') % {
            'nombre': tipologia.nombre_plural, 'estado': estado}, messages.SUCCESS)
        volver = request.POST.get('volver', '')
        ancla = f'#{volver}' if re.fullmatch(r'[a-z_]+', volver) else ''
        return redirect(reverse('admin:index') + ancla)
