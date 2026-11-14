"""Configuracion del editor compartido para calendario y sus límites."""
from django.utils.translation import gettext_lazy as _
from apps.core.calendario import datos_calendario
from apps.core.presentation.calendario import calendario_actual
from ..editor_revisiones import EditorRevisionAdmin
from .forms import CalendarioRevisionForm
from .models import PublicacionPoliticaCalendario
from .selectors import calendario_de_revision
from .services import guardar_borrador_calendario, puede_publicar_calendario, publicar_calendario, revisar_compatibilidad


class RevisionPoliticaCalendarioAdmin(EditorRevisionAdmin):
    modelo_publicacion = PublicacionPoliticaCalendario
    formulario = CalendarioRevisionForm
    datos_actuales = staticmethod(calendario_actual)
    serializar = staticmethod(datos_calendario)
    validar_revision = staticmethod(calendario_de_revision)
    guardar_borrador = staticmethod(guardar_borrador_calendario)
    puede_publicar = staticmethod(puede_publicar_calendario)
    publicar_revision = staticmethod(publicar_calendario)
    revisar_compatibilidad = staticmethod(revisar_compatibilidad)
    plantilla_editor = 'admin/configuracion_institucional/calendario/editor.html'
    plantilla_publicar = 'admin/configuracion_institucional/calendario/publicar.html'
    titulo_inicial = _('Política de calendario institucional')
    titulo_editor = _('Crear revisión de calendario')
    titulo_publicar = _('Revisar y publicar calendario')
    mensaje_creado = _('Borrador de calendario creado.')
    mensaje_guardado = _('Borrador guardado; la política de calendario en uso no cambió.')
    mensaje_publicado = _('Política de calendario institucional publicada.')
    aviso_historial = _('El historial es de lectura. Para modificar la política de calendario, crea y publica una nueva revisión.')
