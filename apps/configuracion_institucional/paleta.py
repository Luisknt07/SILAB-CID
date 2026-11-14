"""Selectores de color sin CSS arbitrario desde el administrador."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.paleta import CLAVES_PALETA, CLAVE_DEGRADADO, PALETA_SUGERIDA, normalizar_hex, validar_paleta
from apps.core.estilos_marca import FUENTES, OPCIONES_ESTILO
from apps.core.plantillas_marca import catalogo_plantillas

ETIQUETAS_ESTILO = (
    _('Color de las líneas (HEX)'), _('Degradado de las líneas (opcional)'),
    _('Grosor de línea (1-6 px)'), _('Intensidad de línea (25-100 %)'), _('Ancho de línea (20-100 %)'),
    _('Degradado de bandas oscuras (opcional)'), _('Color de la capa sobre imágenes (HEX)'),
    _('Intensidad de la capa (30-100 %)'), _('Extensión de la capa (35-100 %)'),
    _('Fuente del contenido'), _('Fuente de los títulos'), _('Escala de lectura (90-115 %)'),
    _('Color de los títulos sobre fondo claro (HEX)'), _('Color de los iconos sobre fondo claro (HEX)'),
    _('Intensidad de los degradados (0-100 %)'), _('Extensión de los degradados (20-100 %)'),
    _('¿Dónde se aplica el degradado?'),
    _('Fondo de tarjetas y paneles'), _('Color de los botones principales'),
    _('Color de los botones destacados'), _('Color de la barra superior'),
    _('Degradado de la barra superior (opcional)'),
    _('Color del distintivo del módulo'), _('Color del filete de la carpeta'),
    _('Color del archivo seleccionado'), _('Fondo de la fila del módulo'),
    _('Fondo de la carpeta abierta'), _('Degradado del panel (opcional)'),
    _('Degradado de los botones (opcional)'),
)

ALCANCES = (('bandas', _('Solo en bandas y cabeceras')), ('botones', _('Solo en los botones')),
            ('ambos', _('En bandas y en botones')))

# Que cambia cada grupo, en el orden en que aparece en el editor.
AYUDAS_GRUPO = {
    'colores': _('El color principal pinta los botones de acción y las bandas verdes; el oscuro, la cabecera y los '
                'pies; el de acento, los subtítulos y detalles destacados; texto y fondo son la lectura general.'),
    'lineas': _('Los filetes bajo los títulos y sobre las tarjetas del catálogo.'),
    'imagenes': _('La veladura que oscurece las fotos para que el texto encima se lea.'),
    'fuentes': _('Tipografía y tamaño de lectura del portal. Los PDF y los correos conservan sus fuentes compatibles.'),
    'acciones': _('Elige si el degradado principal se aplica a las bandas y cabeceras, solo a los botones o a '
                 'ambos, y con cuánta fuerza. Sin elegir nada se aplica solo a las bandas.'),
    'panel': _('El panel «Contenidos» de una unidad tiene tres niveles: el módulo con su distintivo numerado, '
              'la carpeta con su filete lateral y el archivo, que se resalta cuando es el que se está viendo. '
              'Se puede cambiar el color de cada pieza y el fondo de sus filas, y darles un degradado propio. '
              'Lo que dejes vacío sigue el color del botón que le corresponde.'),
    'superficies': _('Colores propios e independientes de los colores base: el fondo de las tarjetas y los paneles, '
                    'el de los botones y el de la barra superior, plana o con degradado propio. Lo que dejes vacío '
                    'conserva lo de siempre: blanco para las tarjetas y el color base para botones y barra.'),
}



# Grupos que se configuran pulsando su pieza en la vista previa. Siguen en el
# formulario -hacen falta para enviarlo- pero no se muestran dos veces.
GRUPOS_SOLO_VISUALIZADOR = {'colores', 'lineas', 'imagenes', 'fuentes', 'acciones',
                            'superficies', 'panel'}

TITULOS_GRUPO = {
    'colores': _('Colores base'),
    'lineas': _('Líneas decorativas'),
    'imagenes': _('Veladura sobre fotografías'),
    'fuentes': _('Tipografía, títulos e iconos'),
    'acciones': _('Alcance e intensidad del degradado'),
    'superficies': _('Colores propios de paneles, botones y barra'),
    'panel': _('Panel de contenidos'),
}

# El grupo de cada opcion se declara aqui, no se deduce del orden: asi una
# opcion nueva puede ir al final de OPCIONES_ESTILO sin caer en el ultimo grupo.
GRUPO_DE_ESTILO = {
    'linea_color': 'lineas', 'linea_degradado': 'lineas', 'linea_grosor': 'lineas',
    'linea_intensidad': 'lineas', 'linea_ancho': 'lineas',
    'degradado_superficie': 'imagenes', 'capa_color': 'imagenes',
    'capa_intensidad': 'imagenes', 'capa_ancho': 'imagenes',
    'fuente_cuerpo': 'fuentes', 'fuente_titulos': 'fuentes', 'escala_fuente': 'fuentes',
    'titulo_color': 'fuentes', 'icono_color': 'fuentes',
    'degradado_intensidad': 'acciones', 'degradado_ancho': 'acciones',
    'degradado_alcance': 'acciones', 'boton_degradado': 'acciones',
    'color_secundario': 'superficies', 'boton_principal': 'superficies',
    'boton_acento': 'superficies', 'barra_color': 'superficies', 'barra_degradado': 'superficies',
    'panel_modulo': 'panel', 'panel_carpeta': 'panel', 'panel_seleccion': 'panel',
    'panel_modulo_fondo': 'panel', 'panel_carpeta_fondo': 'panel', 'panel_degradado': 'panel',
}

def campos_estilo():
    campos = []
    for clave, (tipo, limites) in OPCIONES_ESTILO.items():
        attrs = {'data-palette-style': clave}
        if tipo == 'numero':
            campos.append(forms.IntegerField(required=False, min_value=limites[0], max_value=limites[1],
                          widget=forms.NumberInput(attrs={**attrs, 'min': limites[0], 'max': limites[1], 'step': 1})))
        elif tipo == 'fuente':
            campos.append(forms.ChoiceField(required=False, choices=[('', _('Conservar fuente actual')),
                *[(k, _('Fuente del sistema') if k == 'sistema' else k.title()) for k in FUENTES]], widget=forms.Select(attrs=attrs)))
        elif tipo == 'alcance':
            campos.append(forms.ChoiceField(required=False, choices=[('', _('Conservar el alcance actual')), *ALCANCES],
                          widget=forms.Select(attrs=attrs)))
        else:
            campos.append(forms.CharField(required=False, max_length=512 if tipo.startswith('degradado') else 32,
                widget=(forms.Textarea(attrs={**attrs, 'rows': 2, 'maxlength': 512}) if tipo.startswith('degradado')
                        else forms.TextInput(attrs={**attrs, 'maxlength': 32, 'placeholder': '#ffce00'}))))
    return campos


class ColorInput(forms.TextInput):
    template_name = 'configuracion_institucional/color_hex.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        try:
            color = normalizar_hex(value)
        except ValueError:
            color = self.attrs['data-default-color']
        context['widget']['color'] = color
        return context


class PaletaWidget(forms.MultiWidget):
    template_name = 'configuracion_institucional/paleta_widget.html'

    def __init__(self, attrs=None):
        super().__init__([forms.CheckboxInput(), *[
            ColorInput(attrs={'maxlength': 32, 'spellcheck': 'false', 'data-palette-color': clave,
                              'data-default-color': PALETA_SUGERIDA[clave]}) for clave in CLAVES_PALETA
        ], forms.Textarea(attrs={'rows': 3, 'maxlength': 512, 'spellcheck': 'false',
                                'data-palette-gradient': '',
                                'placeholder': 'linear-gradient(135deg, #00381c, #006633)'}),
                         *[campo.widget for campo in campos_estilo()]], attrs)

    def decompress(self, value):
        colores = dict(value or {})
        return [bool(colores), *[colores.get(c, PALETA_SUGERIDA[c]) for c in CLAVES_PALETA],
                colores.get(CLAVE_DEGRADADO, ''), *[colores.get(c, '') for c in OPCIONES_ESTILO]]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Combinaciones listas: se eligen y quedan aplicadas, o se ajustan luego.
        context['widget']['plantillas'] = catalogo_plantillas()
        etiquetas = (_('Usar paleta personalizada'), _('Color principal'), _('Color oscuro'),
                     _('Color de acento'), _('Color del texto'), _('Color de fondo'),
                     _('Degradado principal (opcional)'), *ETIQUETAS_ESTILO)
        for widget, etiqueta in zip(context['widget']['subwidgets'], etiquetas):
            widget['etiqueta'] = etiqueta
        context['widget']['subwidgets'][1]['grupo'] = _('Colores base')
        context['widget']['subwidgets'][1]['ayuda_grupo'] = AYUDAS_GRUPO['colores']
        for widget in context['widget']['subwidgets'][1:7]:
            widget['solo_visualizador'] = 'colores' in GRUPOS_SOLO_VISUALIZADOR
        for clave, widget in zip(OPCIONES_ESTILO, context['widget']['subwidgets'][7:]):
            grupo = GRUPO_DE_ESTILO[clave]
            widget['grupo'], widget['ayuda_grupo'] = TITULOS_GRUPO[grupo], AYUDAS_GRUPO[grupo]
            widget['solo_visualizador'] = grupo in GRUPOS_SOLO_VISUALIZADOR
        return context


class PaletaField(forms.MultiValueField):
    def __init__(self, **kwargs):
        super().__init__(fields=[forms.BooleanField(required=False), *[
            forms.CharField(required=False, max_length=32) for _ in CLAVES_PALETA
        ], forms.CharField(required=False, max_length=512), *campos_estilo()], require_all_fields=False, required=False, widget=PaletaWidget(),
            help_text=_('Pega HEX con o sin #. El degradado es opcional; desactivado conserva el diseño original. Se valida el contraste antes de publicar.'),
            **kwargs)

    def compress(self, data_list):
        if not data_list or not data_list[0]:
            return {}
        try:
            colores = dict(zip(CLAVES_PALETA, data_list[1:6]))
            if len(data_list) > 6 and data_list[6]:
                colores[CLAVE_DEGRADADO] = data_list[6]
            colores.update({clave: valor for clave, valor in zip(OPCIONES_ESTILO, data_list[7:]) if valor not in (None, '')})
            return dict(validar_paleta(colores))
        except ValueError as exc:
            raise ValidationError(_(str(exc))) from exc
