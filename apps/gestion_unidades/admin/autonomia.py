"""Entrada administrativa a las operaciones con autorización por unidad."""
from functools import lru_cache
from django.urls import reverse
from apps.gestion_unidades.admin.acceso import unidades_editables


@lru_cache(maxsize=None)
def contenido_inline(clase):
    class ContenidoLocal(clase):
        def _permitido(self, request, obj):
            from apps.directorio_unidades.presentation.contexto_editor import unidad_en_edicion
            unidad_id = obj.pk if obj else unidad_en_edicion(request)
            return bool(unidad_id and unidades_editables(request.user).filter(pk=unidad_id).exists())

        def has_view_permission(self, request, obj=None):
            return self._permitido(request, obj)

        def has_change_permission(self, request, obj=None):
            return self._permitido(request, obj)

        def has_add_permission(self, request, obj=None):
            return self._permitido(request, obj)

        def has_delete_permission(self, request, obj=None):
            return self.can_delete and self._permitido(request, obj)
    return ContenidoLocal


def areas_operativas(request):
    if request.user.is_superuser:
        return []
    areas = []
    for unidad in unidades_editables(request.user).order_by('dependencia', 'nombre'):
        url = reverse('gestion_unidad', args=[unidad.slug])
        tarjetas = [
            {
                'name': 'Editar datos y contenidos', 'object_name': f'unidad_{unidad.pk}_datos',
                'admin_url': reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk]),
                'add_url': None, 'perms': {'view': True},
                'descripcion': 'Ficha, multimedia, reglamento, espacios, software y documentos.',
            },
            {
                'name': 'Abrir gesti\u00f3n de la unidad', 'object_name': f'unidad_{unidad.pk}_gestion',
                'admin_url': url, 'add_url': None, 'perms': {'view': True},
                'navegacion_directa': True,
                'descripcion': 'Reservas, recursos, personal, mantenimiento e indicadores. Abre el panel completo en esta misma pesta\u00f1a.',
            },
        ]
        areas.append({'name': unidad.nombre, 'app_label': f'mi_unidad_{unidad.pk}',
                      'app_url': f'#mi_unidad_{unidad.pk}', 'slug': f'mi_unidad_{unidad.pk}',
                      'description': 'Administración completa de esta unidad. Las operaciones quedan registradas.',
                      'icon': 'settings', 'has_module_perms': True, 'models': tarjetas,
                      'grupos': [], 'publicacion': []})
    return areas
