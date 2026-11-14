"""Edición del certificado con texto limitado e imágenes raster normalizadas."""
import base64

from django import forms
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

from apps.core.presentation.catalogos import catalogo_actual
from apps.core.presentation.identidad import identidad_actual

from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso, IMAGENES_CERTIFICADO, TIPOS_CERTIFICADO
from apps.formacion.presentation.certificados_diseno import imagen_png


class ConfiguracionCertificadoForm(forms.ModelForm):
    facultad_catalogo = forms.ChoiceField(label='Facultad del catálogo', required=False)
    carrera_catalogo = forms.ChoiceField(label='Carrera del catálogo', required=False)

    quitar_firma_imagen = forms.BooleanField(label='Quitar imagen de la primera firma', required=False)
    quitar_segunda_firma_imagen = forms.BooleanField(label='Quitar imagen de la segunda firma', required=False)
    quitar_tercera_firma_imagen = forms.BooleanField(label='Quitar imagen de la tercera firma', required=False)
    quitar_logo_1_imagen = forms.BooleanField(label='Quitar primer logo', required=False)
    quitar_logo_2_imagen = forms.BooleanField(label='Quitar segundo logo', required=False)
    quitar_logo_3_imagen = forms.BooleanField(label='Quitar tercer logo', required=False)
    quitar_logo_4_imagen = forms.BooleanField(label='Quitar cuarto logo', required=False)

    quitar_imagen_fondo = forms.BooleanField(label='Quitar imagen propia de fondo', required=False)
    quitar_foto_alusiva = forms.BooleanField(label='Quitar fotografía alusiva', required=False)

    class Meta:
        model = ConfiguracionCertificadoCurso
        fields = ('emisor', 'mostrar_facultad', 'facultad_nombre', 'mostrar_carrera', 'carrera_nombre', 'entradilla', 'categoria_evento', 'tipo_certificado', 'fecha_inicio', 'fecha_fin', 'horas_certificadas',
                  'titulo_aprobacion', 'texto_aprobacion', 'titulo_participacion', 'texto_participacion',
                  'titulo_asistencia', 'texto_asistencia', 'titulo_ponente', 'texto_ponente',
                  'titulo_organizador', 'texto_organizador', 'diseno', 'alineacion_contenido', 'formato_contenido',
                  'tema_fondo', 'modo_fondo', 'intensidad_fondo', 'imagen_fondo', 'encuadre_fondo',
                  'subtitulo', 'competencias', 'foto_alusiva', 'usar_foto_unidad', 'color_primario', 'color_acento',
                  'color_texto', 'color_titulos', 'tipografia', 'mostrar_pie_tecnologico', 'estilo_pie_tecnologico',
                  'disposicion_logos', 'logo_1_nombre', 'logo_1_imagen', 'logo_1_posicion', 'logo_1_contraste', 'logo_2_nombre', 'logo_2_imagen', 'logo_2_posicion', 'logo_2_contraste',
                  'logo_3_nombre', 'logo_3_imagen', 'logo_3_posicion', 'logo_3_contraste', 'logo_4_nombre', 'logo_4_imagen', 'logo_4_posicion', 'logo_4_contraste',
                  'usar_firmante_curso', 'firma_nombre', 'firma_cargo', 'firma_imagen',
                  'segunda_firma_nombre', 'segunda_firma_cargo', 'segunda_firma_imagen',
                  'tercera_firma_nombre', 'tercera_firma_cargo', 'tercera_firma_imagen')
        widgets = {
            **{'texto_' + tipo: forms.Textarea(attrs={'rows': 4, 'maxlength': 700}) for tipo, _ in TIPOS_CERTIFICADO},
            **{campo: forms.FileInput(attrs={'accept': 'image/png,image/jpeg'}) for campo in IMAGENES_CERTIFICADO},
            'competencias': forms.Textarea(attrs={'rows': 6, 'maxlength': 600}),
            'subtitulo': forms.TextInput(attrs={'maxlength': 180}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'horas_certificadas': forms.NumberInput(attrs={'min': '0.01', 'max': '2000', 'step': '0.01'}),
            'color_primario': forms.TextInput(attrs={'placeholder': '#1E5A3D', 'maxlength': 7}),
            'color_acento': forms.TextInput(attrs={'placeholder': '#E1B93F', 'maxlength': 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se conserva el campo para leer configuraciones antiguas, sin un selector
        # que pueda oscurecer el contenido o el área de firmas.
        self.fields['modo_fondo'].widget = forms.HiddenInput()
        self.initial['modo_fondo'] = 'claro'
        catalogo = catalogo_actual()
        self._facultades = tuple((codigo, nombre) for codigo, nombre in catalogo.facultades if codigo != 'externo')
        self._carreras = tuple(catalogo.carreras)
        personalizados = [('__personalizado__', 'Conservar o editar otro nombre')]
        self.fields['facultad_catalogo'].choices = [('', 'Selecciona una facultad')] + list(self._facultades) + personalizados
        self.fields['carrera_catalogo'].choices = [('', 'Selecciona una carrera')] + [(codigo, nombre) for codigo, nombre, _ in self._carreras] + personalizados
        for clave, filas in (('facultad', self._facultades), ('carrera', self._carreras)):
            valor = str(self.initial.get(clave + '_nombre') or '').strip()
            seleccionado = self._codigo_academico(valor, filas) or ('__personalizado__' if valor else '')
            self.initial.setdefault(clave + '_catalogo', seleccionado)
            self.fields[clave + '_catalogo'].widget.attrs['data-catalogo-academico'] = clave
            self.fields[clave + '_nombre'].label = f'Nombre personalizado de {clave}'
        self.fields['facultad_catalogo'].help_text = 'Filtra las carreras disponibles. Sólo se imprime si activas la facultad.'
        self.fields['carrera_catalogo'].help_text = 'Selecciona una carrera de la facultad elegida o conserva un nombre anterior.'
        for campo, clave in (('color_primario', 'primario'), ('color_acento', 'acento')):
            self.fields[campo].widget.attrs.update({'placeholder': self.paleta_predeterminada[clave], 'pattern': '#[0-9a-fA-F]{6}', 'spellcheck': 'false'})
        for nombre, defecto in (('color_texto', '#263D33'), ('color_titulos', self.paleta_predeterminada['primario'])):
            self.fields[nombre].widget.attrs.update({'placeholder': defecto, 'maxlength': 7, 'pattern': '#[0-9a-fA-F]{6}', 'spellcheck': 'false'})
        for nombre in ('color_texto', 'color_titulos'):
            self.fields[nombre].help_text += ' Si falta contraste, se ajusta para mantener la lectura.'
        self.fields['color_primario'].label = 'Color del diseño'
        self.fields['color_acento'].label = 'Acento del diseño'
        self.fields['emisor'].label = 'Organizador o dependencia emisora'
        self.fields['emisor'].help_text = 'Se usa en el texto de la actividad. La institución y la unidad del curso encabezan el bloque principal; los colaboradores se indican por separado.'
        for clave in ('facultad', 'carrera'):
            self.fields['mostrar_' + clave].label = f'Incluir {clave} en el bloque principal'
            self.fields[clave + '_nombre'].help_text += ' Aparece junto a la institución y la unidad, al activarla.'
        self.fields['disposicion_logos'].label = 'Distribución de colaboradores'
        self.fields['disposicion_logos'].help_text = 'Organiza los logos secundarios del bloque «En colaboración con»; la institución principal se mantiene aparte.'
        for numero in range(1, 5):
            self.fields[f'logo_{numero}_nombre'].label = f'Nombre de la entidad colaboradora {numero}'
            self.fields[f'logo_{numero}_nombre'].help_text = 'Nombre real que acompaña al logo; también puede incluirse sin imagen.'
            self.fields[f'logo_{numero}_imagen'].label = f'Logo de la entidad colaboradora {numero}'
            self.fields[f'logo_{numero}_imagen'].help_text = 'PNG transparente o JPEG, hasta 2 MB. Se añade como colaborador; no sustituye el logo principal.'
            self.fields[f'quitar_logo_{numero}_imagen'].label = f'Quitar logo del colaborador {numero}'
            self.fields[f'logo_{numero}_posicion'].label = 'Alineación dentro del bloque de colaboradores'
            self.fields[f'logo_{numero}_posicion'].help_text = 'El nombre aparece debajo de su logo. La alineación se aplica en el espacio secundario, sin desplazar la institución principal.'
        for nombre in ('color_primario', 'color_acento'):
            self.fields[nombre].help_text = 'Vacío: paleta institucional. Un color personalizado se conserva al cambiar de modelo.'

    def clean_modo_fondo(self):
        return 'claro'

    @staticmethod
    def _codigo_academico(valor, filas):
        buscado = str(valor or '').strip().casefold()
        return next((fila[0] for fila in filas if buscado in (fila[0].casefold(), fila[1].casefold())), '')

    @property
    def catalogo_editor(self):
        return {'facultades': [{'codigo': codigo, 'nombre': nombre} for codigo, nombre in self._facultades],
                'carreras': [{'codigo': codigo, 'nombre': nombre, 'facultad': facultad} for codigo, nombre, facultad in self._carreras]}

    @property
    def paleta_predeterminada(self):
        paleta = dict(identidad_actual()[1].paleta)
        return {'primario': paleta.get('primario', '#006633'), 'acento': paleta.get('acento', '#ffce00')}

    @property
    def paletas_editor(self):
        return [{'clave': 'institucional', 'nombre': 'Institucional', **self.paleta_predeterminada},
                {'clave': 'laboratorio', 'nombre': 'Laboratorio', 'primario': '#0F5B55', 'acento': '#34C6AE'},
                {'clave': 'tecnologia', 'nombre': 'Tecnología', 'primario': '#163D5C', 'acento': '#38B9CF'}]

    @property
    def modelos_texto_editor(self):
        return {tipo: {prefijo: self._meta.model._meta.get_field(prefijo + '_' + tipo).get_default()
                       for prefijo in ('titulo', 'texto')} for tipo, _ in TIPOS_CERTIFICADO}

    @property
    def secciones_editor(self):
        grupos = [
            ('contexto', 'Institución, unidad y actividad', ('emisor', 'mostrar_facultad', 'facultad_catalogo', 'facultad_nombre', 'mostrar_carrera', 'carrera_catalogo', 'carrera_nombre', 'entradilla', 'categoria_evento', 'tipo_certificado', 'fecha_inicio', 'fecha_fin', 'horas_certificadas')),
            ('diseno', 'Diseño y colores', ('diseno', 'alineacion_contenido', 'color_primario', 'color_acento')),
            ('fondo', 'Fondo y ambiente tecnológico', ('tema_fondo', 'intensidad_fondo', 'imagen_fondo', 'encuadre_fondo', 'quitar_imagen_fondo', 'mostrar_pie_tecnologico', 'estilo_pie_tecnologico')),
            ('contenido', 'Organización del contenido', ('formato_contenido', 'subtitulo', 'competencias')),
            ('fotografia', 'Fotografía del laboratorio', ('foto_alusiva', 'usar_foto_unidad', 'quitar_foto_alusiva')),
            ('textos', 'Contenido por modalidad', tuple(prefijo + '_' + tipo for tipo, _ in TIPOS_CERTIFICADO for prefijo in ('titulo', 'texto'))),
            ('logos', 'En colaboración con', ('disposicion_logos',) + tuple(campo for numero in range(1, 5)
                for campo in (f'logo_{numero}_nombre', f'logo_{numero}_imagen', f'logo_{numero}_posicion', f'logo_{numero}_contraste', f'quitar_logo_{numero}_imagen'))),
            ('firmas', 'Firmantes', ('usar_firmante_curso',) + tuple(campo for prefijo in ('firma', 'segunda_firma', 'tercera_firma')
                for campo in (prefijo + '_nombre', prefijo + '_cargo', prefijo + '_imagen', 'quitar_' + prefijo + '_imagen'))),
        ]
        return [{'clave': clave, 'titulo': titulo, 'campos': [self[nombre] for nombre in nombres]}
                for clave, titulo, nombres in grupos]

    @property
    def instituciones_editor(self):
        return [{'numero': numero, **{clave: self[nombre] for clave, nombre in {
            'nombre': f'logo_{numero}_nombre', 'imagen': f'logo_{numero}_imagen',
            'posicion': f'logo_{numero}_posicion', 'contraste': f'logo_{numero}_contraste',
            'quitar': f'quitar_logo_{numero}_imagen',
        }.items()}} for numero in range(1, 5)]

    def _normalizar_imagen(self, campo):
        archivo = self.cleaned_data.get(campo)
        if self.cleaned_data.get('quitar_' + campo):
            if campo in self.files:
                raise ValidationError('Elija entre subir una imagen nueva o quitar la actual; no ambas opciones a la vez.')
            return False
        if campo not in self.files or not archivo:
            return archivo
        if archivo.size > 2 * 1024 * 1024:
            raise ValidationError('La imagen debe pesar como máximo 2 MB.')
        # ImageField comprueba el formato real; no se confía en la extensión ni en Content-Type.
        if getattr(archivo, 'image', None) and archivo.image.format not in ('PNG', 'JPEG'):
            raise ValidationError('Use una imagen PNG o JPEG.')
        maximo = (1600, 1200) if campo == 'imagen_fondo' else (1600, 1000) if campo == 'foto_alusiva' else (1000, 400) if campo.startswith('logo_') else (800, 300)
        datos = base64.b64decode(imagen_png(archivo, maximo))
        return ContentFile(datos, name='fondo.png' if campo == 'imagen_fondo' else 'foto.png' if campo == 'foto_alusiva' else 'logo.png' if campo.startswith('logo_') else 'firma.png')

    def clean(self):
        datos = super().clean()
        for clave, filas in (('facultad', self._facultades), ('carrera', self._carreras)):
            selector = clave + '_catalogo'
            if self.add_prefix(selector) in self.data and selector in datos:
                codigo = datos[selector]
                if codigo != '__personalizado__':
                    datos[clave + '_nombre'] = next((fila[1] for fila in filas if fila[0] == codigo), '')
        facultad = self._codigo_academico(datos.get('facultad_nombre'), self._facultades)
        carrera = self._codigo_academico(datos.get('carrera_nombre'), self._carreras)
        esperada = next((relacion for codigo, _, relacion in self._carreras if codigo == carrera), '')
        if carrera and facultad and esperada != facultad:
            self.add_error('carrera_catalogo', 'La carrera seleccionada no pertenece a esa facultad.')
        elif carrera and not facultad and datos.get('carrera_catalogo') not in ('', None, '__personalizado__'):
            self.add_error('facultad_catalogo', 'Selecciona la facultad de la carrera para filtrar el catálogo.')
        for campo in IMAGENES_CERTIFICADO:
            try:
                datos[campo] = self._normalizar_imagen(campo)
            except ValidationError as exc:
                self.add_error(campo, exc)
        for numero in range(1, 5):
            imagen, nombre = f'logo_{numero}_imagen', f'logo_{numero}_nombre'
            # Un logo histórico sin nombre puede conservarse; no inventamos su identidad.
            if imagen in self.files and datos.get(imagen) and not (datos.get(nombre) or '').strip():
                self.add_error(nombre, 'Escriba el nombre real de la institución del logo que está subiendo.')
        # La nota sirve para aprobar en el aula; no forma parte de certificados nuevos.
        self.instance.mostrar_nota = False
        return datos


class AcreditacionCertificadoForm(forms.Form):
    inscripcion = forms.IntegerField(min_value=1)
    tipo = forms.ChoiceField(choices=[(tipo, titulo) for tipo, titulo in TIPOS_CERTIFICADO if tipo != 'aprobacion'])
    motivo = forms.CharField(max_length=300, min_length=10, strip=True,
                             label='Registro que respalda la acreditación', widget=forms.Textarea(attrs={'rows': 2}))
    confirmacion = forms.BooleanField(label='Confirmo el registro de asistencia, participación o función desempeñada')

    def clean_motivo(self):
        motivo = self.cleaned_data['motivo']
        if '<' in motivo or '>' in motivo or any(ord(c) < 32 for c in motivo):
            raise ValidationError('Use texto normal sin HTML ni caracteres de control.')
        return motivo
