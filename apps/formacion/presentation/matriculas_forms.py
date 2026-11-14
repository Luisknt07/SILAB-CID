"""Formularios de grupos, matrícula individual y listas del curso."""
from django import forms
from django.core.exceptions import ValidationError

from apps.formacion.models.cursos import EdicionCurso
from apps.formacion.presentation.matriculas_datos import leer_lista_matricula, validar_datos_matricula


class GrupoCursoForm(forms.ModelForm):
    class Meta:
        model = EdicionCurso
        fields = ('nombre', 'tipo_grupo', 'destinatario', 'anio', 'inicio', 'fin', 'horas_certificadas',
                  'inscripciones_desde', 'inscripciones_hasta', 'cupo', 'horario', 'lugar', 'activa')
        widgets = {campo: forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
                   for campo in ('inicio', 'fin', 'inscripciones_desde', 'inscripciones_hasta')}

    def __init__(self, *args, curso, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.curso = curso
        self.fields['nombre'].label = 'Nombre del grupo'
        self.fields['destinatario'].label = 'Organización o público del grupo'
        self.fields['destinatario'].help_text = 'Para grupos a medida: empresa, asociación o colectivo. Sin datos personales.'
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'form-control')


    def clean(self):
        datos = super().clean()
        nombre = (datos.get('nombre') or '').strip()
        if self.instance.curso.ediciones.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists():
            self.add_error('nombre', 'Ese grupo ya existe en este curso.')
        if self.instance.pk and datos.get('cupo') is not None:
            ocupadas = (self.instance.inscripciones.filter(estado='aceptada').count()
                        + self.instance.invitaciones.filter(activa=True, inscripcion__isnull=True).count())
            if datos['cupo'] < ocupadas:
                self.add_error('cupo', f'Hay {ocupadas} plazas ocupadas o reservadas. Cancela o retira matrículas antes de reducir el cupo.')
        return datos


class _EdicionForm(forms.Form):
    edicion = forms.ModelChoiceField(label='Grupo o edición', queryset=EdicionCurso.objects.none(), empty_label='Selecciona el grupo')

    def __init__(self, *args, curso, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['edicion'].queryset = curso.ediciones.filter(activa=True)


class DatosMatriculaForm(forms.Form):
    nombres_completos = forms.CharField(label='Nombres y apellidos completos', max_length=200)
    documento = forms.CharField(label='Cédula o documento de identidad', max_length=30)

    def clean(self):
        datos = super().clean()
        if all(campo in datos for campo in ('nombres_completos', 'documento')):
            try:
                datos.update(validar_datos_matricula(**{campo: datos[campo] for campo in ('nombres_completos', 'documento')}))
            except ValidationError as error:
                for campo, mensajes in error.message_dict.items():
                    self.add_error(campo, mensajes)
        return datos


class InscripcionGrupoForm(_EdicionForm, DatosMatriculaForm):
    pass


class MatriculaIndividualForm(_EdicionForm, DatosMatriculaForm):
    correo = forms.EmailField(label='Correo de la persona', max_length=254)

    def clean_correo(self):
        return self.cleaned_data['correo'].strip().lower()


class ListaMatriculaForm(_EdicionForm):
    personas = forms.CharField(label='Lista CSV', required=False, widget=forms.Textarea(attrs={'rows': 6}))
    archivo = forms.FileField(label='O sube un CSV UTF-8 (hasta 1 MB y 100 personas)', required=False)

    def clean(self):
        datos = super().clean()
        texto, archivo = datos.get('personas', '').strip(), datos.get('archivo')
        if bool(texto) == bool(archivo):
            raise ValidationError('Pega la lista o sube un archivo; utiliza una sola opción.')
        if archivo:
            if archivo.size > 1_048_576 or not archivo.name.lower().endswith('.csv'):
                raise ValidationError('Sube un CSV de hasta 1 MB.')
            contenido = archivo.read(1_048_577)
        else:
            contenido = texto
        datos['filas'] = leer_lista_matricula(contenido)
        return datos
