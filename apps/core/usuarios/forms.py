"""Formularios de identidad institucional y registro de usuarios."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from apps.core.documentos_identidad import cedula_ecuatoriana_valida
from apps.core.presentation.catalogos import carreras_academicas, facultades, tipos_con_carrera, tipos_usuario
from apps.core.presentation.identidad import identidad_actual
from apps.core.presentation.niveles import niveles_estudiantiles
from apps.core.presentation.traducciones import traducir_campos
from apps.core.models.usuarios_base import UserProfile


class DatosInstitucionalesMixin(forms.Form):
    """Valida dimensiones estables para reservas y reportes."""

    tipo_usuario = forms.ChoiceField(
        choices=(),
        label='Tipo de usuario',
    )
    facultad = forms.ChoiceField(
        choices=(),
        label='Facultad o dependencia',
        required=False,
    )
    carrera = forms.ChoiceField(
        choices=(),
        label='Carrera o programa académico',
        required=False,
    )
    nivel_academico = forms.ChoiceField(
        choices=(),
        required=False,
    )
    institucion = forms.CharField(max_length=200, required=False)
    cedula = forms.CharField(
        max_length=20,
        required=False,
        label='Cédula o documento de identidad',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_usuario'].choices = (
            ('', 'Selecciona tu tipo de usuario'),
        ) + tipos_usuario()
        self.fields['facultad'].choices = (
            ('', 'Selecciona tu facultad o dependencia'),
        ) + facultades()
        self.fields['carrera'].choices = (
            ('', 'Selecciona tu carrera o programa académico'),
        ) + carreras_academicas()
        self.fields['nivel_academico'].choices = (
            ('', 'Selecciona tu nivel académico'),
        ) + niveles_estudiantiles()
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        traducir_campos(self)

    def clean_cedula(self):
        """Diez dígitos se validan como cédula; el resto pasa como documento.

        Un pasaporte o un documento extranjero no siguen el dígito verificador
        ecuatoriano, así que solo se comprueba lo que sí puede comprobarse.
        """
        valor = (self.cleaned_data.get('cedula') or '').strip().upper()
        if valor.isdigit() and len(valor) == 10 and not cedula_ecuatoriana_valida(valor):
            raise forms.ValidationError(
                'La cédula no es válida. Revisa los diez dígitos.'
            )
        return valor

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_usuario')
        facultad = cleaned.get('facultad')
        carrera = cleaned.get('carrera')
        nivel = cleaned.get('nivel_academico')
        institucion = (cleaned.get('institucion') or '').strip()

        if tipo == 'externo':
            if not institucion or institucion.lower() in {'gmail', 'externo'}:
                self.add_error('institucion', 'Indica la institución, empresa u organización de procedencia.')
            cleaned['facultad'] = 'externo'
            cleaned['carrera'] = ''
            cleaned['nivel_academico'] = ''
            return cleaned

        cleaned['institucion'] = identidad_actual()[1].siglas
        if not facultad or facultad == 'externo':
            self.add_error('facultad', 'Selecciona tu facultad o dependencia institucional.')
        if tipo in tipos_con_carrera():
            if not carrera:
                self.add_error('carrera', 'Selecciona la carrera o programa académico al que estás asociado.')
        if carrera:
            facultad_esperada = UserProfile.facultad_para_carrera(carrera)
            if not facultad_esperada:
                self.add_error('carrera', 'Selecciona una carrera académica válida.')
            elif facultad != facultad_esperada:
                self.add_error('facultad', 'La facultad no corresponde a la carrera seleccionada.')
        if tipo == 'estudiante':
            if nivel not in dict(niveles_estudiantiles()):
                self.add_error('nivel_academico', 'Selecciona el nivel académico que cursas.')
            if not cleaned.get('cedula'):
                self.add_error('cedula', 'Ingresa tu cédula o documento de identidad.')
        else:
            cleaned['nivel_academico'] = ''
        return cleaned


class RegistroInstitucionalForm(DatosInstitucionalesMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, label='Nombres')
    last_name = forms.CharField(max_length=150, label='Apellidos')
    email = forms.EmailField(label='Correo electrónico')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta registrada con este correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = user.profile
            for field in (
                'tipo_usuario', 'facultad', 'carrera', 'nivel_academico',
                'cedula', 'institucion',
            ):
                setattr(profile, field, self.cleaned_data.get(field, ''))
            profile.save()
        return user


class PerfilInstitucionalForm(DatosInstitucionalesMixin, forms.Form):
    first_name = forms.CharField(max_length=150, label='Nombres')
    last_name = forms.CharField(max_length=150, label='Apellidos')
    email = forms.EmailField(label='Correo electrónico')
    telefono = forms.CharField(max_length=20, required=False)
    cargo = forms.CharField(max_length=100, required=False)
    biografia = forms.CharField(required=False, widget=forms.Textarea)
    avatar = forms.ImageField(required=False)

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen de perfil no puede superar 5 MB.")
        return avatar
