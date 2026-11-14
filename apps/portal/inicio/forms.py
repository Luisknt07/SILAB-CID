from django import forms
from django.utils.translation import gettext_lazy as _
from .contracts import LIMITES, validar_contenido

ETIQUETAS = {'lema': _('Lema'), 'titulo': _('Título de portada'), 'resumen': _('Resumen'),
             'boton_centros': _('Botón de Centros I+D'), 'boton_unidades': _('Botón de unidades'),
             'mensaje_marca': _('Mensaje junto al logo')}


class PortadaInicioForm(forms.Form):
    titulo = forms.CharField(label=_('Nombre de la revisión'), max_length=200)
    base_esperada = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)

    def __init__(self, *args, contenido=None, **kwargs):
        super().__init__(*args, **kwargs)
        for idioma in ('es', 'en'):
            for campo, limite in LIMITES.items():
                self.fields[f'{campo}_{idioma}'] = forms.CharField(
                    label=ETIQUETAS[campo], max_length=limite, required=campo != 'titulo',
                    initial=(contenido or {}).get(idioma, {}).get(campo, ''),
                    widget=forms.Textarea(attrs={'rows': 3}) if campo == 'resumen' else forms.TextInput(),
                    help_text=_('Vacío conserva el nombre del sistema y las siglas de la institución.') if campo == 'titulo' else '',
                )

    def clean(self):
        datos = super().clean()
        if self.errors:
            return datos
        try:
            datos['contenido'] = validar_contenido({idioma: {campo: datos[f'{campo}_{idioma}']
                                                            for campo in LIMITES} for idioma in ('es', 'en')})
        except ValueError as exc:
            raise forms.ValidationError(_(str(exc))) from exc
        if any(ord(c) < 32 or c in '<>' for c in datos['titulo']):
            self.add_error('titulo', _('Usa texto simple para el nombre de la revisión.'))
        return datos

    def grupos(self):
        return [(idioma, [self[f'{campo}_{idioma}'] for campo in LIMITES]) for idioma in ('es', 'en')]


class ConfirmarInicioForm(forms.Form):
    base_esperada = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    confirmar = forms.BooleanField(label=_('Confirmo que revisé los textos en español e inglés antes de publicarlos.'))
