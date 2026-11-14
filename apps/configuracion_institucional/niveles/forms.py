"""Editor progresivo de niveles y rutas con validacion del payload unico."""
from django import forms
from django.utils.translation import gettext_lazy as _
from apps.core.niveles import niveles_academicos, datos_niveles
from config.niveles import configuracion_niveles
from ..formularios import JsonRevisionField, TituloRevisionForm


class NivelesWidget(forms.Textarea):
    template_name = 'admin/configuracion_institucional/niveles/widget.html'

    class Media:
        css = {'all': ['configuracion_institucional/editor.css']}
        js = ['configuracion_institucional/niveles.js']


class ContenidoNivelesField(JsonRevisionField):
    cargar = staticmethod(configuracion_niveles)
    validar = staticmethod(niveles_academicos)
    serializar = staticmethod(datos_niveles)
    clave_entorno = 'ACADEMIC_LEVELS_JSON'
    mensaje_error = _('Revisa los códigos, las etiquetas y las rutas de niveles.')


class NivelesRevisionForm(TituloRevisionForm):
    contenido = ContenidoNivelesField(label=_('Niveles académicos'), max_length=100_000,
                                     widget=NivelesWidget(attrs={'rows': 18}), strip=False)
