"""Editor progresivo de calendario y sus límites con validacion del payload unico."""
from django import forms
from django.utils.translation import gettext_lazy as _
from apps.core.calendario import politica_calendario, datos_calendario
from config.calendario import configuracion_calendario
from ..formularios import JsonRevisionField, TituloRevisionForm


class CalendarioWidget(forms.Textarea):
    template_name = 'admin/configuracion_institucional/calendario/widget.html'

    class Media:
        css = {'all': ['configuracion_institucional/editor.css']}
        js = ['configuracion_institucional/calendario.js']


class ContenidoCalendarioField(JsonRevisionField):
    cargar = staticmethod(configuracion_calendario)
    validar = staticmethod(politica_calendario)
    serializar = staticmethod(datos_calendario)
    clave_entorno = 'ACADEMIC_CALENDAR_JSON'
    mensaje_error = _('Revisa los ciclos, los ámbitos y las semanas.')


class CalendarioRevisionForm(TituloRevisionForm):
    contenido = ContenidoCalendarioField(label=_('Política de calendario'), max_length=100_000,
                                     widget=CalendarioWidget(attrs={'rows': 18, 'class': 'catalogo-json'}), strip=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            self.fields['contenido'].widget.attrs['data-payload-rechazado'] = 'true'
