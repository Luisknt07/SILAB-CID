"""Configuracion del editor compartido para catalogos academicos."""
from django.utils.translation import gettext_lazy as _
from apps.core.catalogos import datos_catalogo
from apps.core.presentation.catalogos import catalogo_actual
from ..editor_revisiones import EditorRevisionAdmin
from .forms import CatalogoRevisionForm
from .models import PublicacionCatalogoAcademico
from .selectors import catalogo_de_revision
from .services import guardar_borrador_catalogo, puede_publicar_catalogo, publicar_catalogo, revisar_compatibilidad


class RevisionCatalogoAcademicoAdmin(EditorRevisionAdmin):
    modelo_publicacion = PublicacionCatalogoAcademico
    formulario = CatalogoRevisionForm
    datos_actuales = staticmethod(catalogo_actual)
    serializar = staticmethod(datos_catalogo)
    validar_revision = staticmethod(catalogo_de_revision)
    guardar_borrador = staticmethod(guardar_borrador_catalogo)
    puede_publicar = staticmethod(puede_publicar_catalogo)
    publicar_revision = staticmethod(publicar_catalogo)
    revisar_compatibilidad = staticmethod(revisar_compatibilidad)
    plantilla_editor = 'admin/configuracion_institucional/catalogos/editor.html'
    plantilla_publicar = 'admin/configuracion_institucional/catalogos/publicar.html'
    titulo_inicial = _('Catálogo institucional')
    titulo_editor = _('Crear revisión del catálogo')
    titulo_publicar = _('Revisar y publicar catálogo')
    mensaje_creado = _('Borrador de catálogo creado.')
    mensaje_guardado = _('Borrador guardado; el catálogo en uso no cambió.')
    mensaje_publicado = _('Catálogo institucional publicado.')
    aviso_historial = _('El historial es de lectura. Para modificar el catálogo, crea y publica una nueva revisión.')
