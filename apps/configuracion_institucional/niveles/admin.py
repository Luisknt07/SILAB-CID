"""Configuracion del editor compartido para niveles y rutas."""
from django.utils.translation import gettext_lazy as _
from apps.core.niveles import datos_niveles
from apps.core.presentation.niveles import niveles_actuales
from ..editor_revisiones import EditorRevisionAdmin
from .forms import NivelesRevisionForm
from .models import PublicacionNivelesAcademicos
from .selectors import niveles_de_revision
from .services import guardar_borrador_niveles, puede_publicar_niveles, publicar_niveles, revisar_compatibilidad


class RevisionNivelesAcademicosAdmin(EditorRevisionAdmin):
    modelo_publicacion = PublicacionNivelesAcademicos
    formulario = NivelesRevisionForm
    datos_actuales = staticmethod(niveles_actuales)
    serializar = staticmethod(datos_niveles)
    validar_revision = staticmethod(niveles_de_revision)
    guardar_borrador = staticmethod(guardar_borrador_niveles)
    puede_publicar = staticmethod(puede_publicar_niveles)
    publicar_revision = staticmethod(publicar_niveles)
    revisar_compatibilidad = staticmethod(revisar_compatibilidad)
    plantilla_editor = 'admin/configuracion_institucional/niveles/editor.html'
    plantilla_publicar = 'admin/configuracion_institucional/niveles/publicar.html'
    titulo_inicial = _('Niveles académicos institucionales')
    titulo_editor = _('Crear revisión de niveles')
    titulo_publicar = _('Revisar y publicar niveles')
    mensaje_creado = _('Borrador de niveles creado.')
    mensaje_guardado = _('Borrador guardado; los niveles en uso no cambiaron.')
    mensaje_publicado = _('Niveles académicos institucionales publicados.')
    aviso_historial = _('El historial es de lectura. Para modificar los niveles, crea y publica una nueva revisión.')
