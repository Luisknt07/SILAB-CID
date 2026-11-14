"""El formulario con el que se pide algo a un Centro I+D: la ficha inicial de la ruta de atención."""
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import CentroID, CuentaCentro, EquipoCentro, SolicitudCentro
from .identidades import alias_centros, alias_identidades, identidad_de
from .escenarios import filtro_contenido


class CuentaChoiceField(forms.ModelChoiceField):
    """Selecciona en auth y entrega únicamente una identidad local del mismo ID."""
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()

    def to_python(self, value):
        if self.disabled and value not in self.empty_values:
            identificador = getattr(value, 'pk', value)
            try:
                return CuentaCentro.objects.using(alias_centros()).get(pk=identificador)
            except (CuentaCentro.DoesNotExist, TypeError, ValueError):
                raise forms.ValidationError(self.error_messages['invalid_choice'], code='invalid_choice') from None
        principal = super().to_python(value)
        return identidad_de(principal) if principal is not None else None


class CuentasChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()

    def clean(self, value):
        principales = super().clean(value)
        return [identidad_de(principal) for principal in principales]


class CentroIDForm(forms.ModelForm):
    # El puente explícito conserva la tabla/columnas históricas; Django admin
    # requiere un campo propio para editar una M2M con through declarado.
    cuentas_gestoras = CuentasChoiceField(label='Gestores', required=False,
        queryset=get_user_model()._default_manager.using(alias_identidades()).filter(is_active=True))

    class Meta:
        model = CentroID
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('gestores', None)
        if self.instance.pk:
            self.initial.setdefault('cuentas_gestoras', list(self.instance.gestores.values_list('pk', flat=True)))

    def _save_m2m(self):
        super()._save_m2m()
        if 'cuentas_gestoras' in self.cleaned_data:
            self.instance.gestores.set(self.cleaned_data['cuentas_gestoras'])


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudCentro
        fields = ('tipo', 'perfil', 'institucion', 'titulo', 'problema', 'resultado_esperado', 'servicio', 'componente',
                  'zona', 'equipo', 'inicio_preferido', 'fin_preferido', 'fecha_preferida', 'participantes', 'finalidad', 'proyecto', 'desarrollo')
        widgets = {
            'problema': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Qué problema, necesidad u oportunidad hay que '
                                                                         'resolver y para quién.'}),
            'resultado_esperado': forms.TextInput(attrs={'placeholder': 'Prototipo, software, validación, informe, '
                                                                         'capacitación, servicio…'}),
            'fecha_preferida': forms.DateInput(attrs={'type': 'date'}),
            'inicio_preferido': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'fin_preferido': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        labels = {'zona': 'Espacio del centro', 'equipo': 'Equipo individual', 'servicio': 'Servicio del portafolio',
                  'componente': 'División o plataforma (si sabes cuál)'}

    def __init__(self, *args, centro, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.centro = centro
        self.fields['proyecto'].queryset = centro.proyectos.filter(publicado=True, **filtro_contenido(centro))
        self.fields['desarrollo'].queryset = centro.resultados.filter(publicado=True, confidencial=False, **filtro_contenido(centro))
        self.fields['servicio'].queryset = centro.servicios.filter(activo=True).exclude(estado_oferta='suspendido').order_by('linea', 'nombre')
        self.fields['componente'].queryset = centro.componentes.filter(publicado=True)
        self.fields['zona'].queryset = centro.zonas.filter(reservable=True).filter(
            Q(componente__isnull=True) | Q(componente__publicado=True))
        self.fields['equipo'].queryset = EquipoCentro.objects.filter(componente__centro=centro, componente__publicado=True,
            es_activo_individual=True, cantidad=1, reservable=True, estado='operativo').exclude(codigo='')
        for nombre in ('servicio', 'componente', 'zona', 'equipo', 'proyecto', 'desarrollo', 'finalidad'):
            self.fields[nombre].required = False

        tipo = self.data.get('tipo') if self.is_bound else self.initial.get('tipo', 'reto')
        comunes = {'tipo', 'perfil', 'institucion', 'titulo', 'problema', 'resultado_esperado'}
        especificos = {
            'reto': {'proyecto', 'desarrollo', 'finalidad', 'componente'},
            'servicio': {'servicio', 'componente', 'fecha_preferida', 'proyecto', 'desarrollo'},
            'uso': {'zona', 'equipo', 'inicio_preferido', 'fin_preferido', 'participantes', 'proyecto'},
            'visita': {'fecha_preferida', 'participantes', 'componente', 'desarrollo', 'finalidad'},
            'capacitacion': {'fecha_preferida', 'participantes', 'componente'},
            'asesoria': {'servicio', 'proyecto', 'desarrollo', 'fecha_preferida'},
        }
        for nombre in list(self.fields):
            if nombre not in comunes | especificos.get(tipo, set()):
                del self.fields[nombre]
        self.fields['tipo'].widget = forms.HiddenInput()
        if tipo == 'uso':
            for nombre in ('zona', 'equipo'):
                recursos = self.fields[nombre].queryset.select_related('componente')
                self.fields[nombre].queryset = recursos.filter(pk__in=[r.pk for r in recursos if r.apto_reserva])
            for nombre in ('inicio_preferido', 'fin_preferido', 'participantes'):
                self.fields[nombre].required = True
        if tipo == 'visita':
            self.fields['participantes'].required = True
        if tipo == 'servicio':
            self.fields['servicio'].required = True

    def clean(self):
        from django.utils import timezone
        datos = super().clean()
        if datos.get('inicio_preferido') and datos['inicio_preferido'] < timezone.now():
            self.add_error('inicio_preferido', 'Elige un inicio futuro.')
        if datos.get('participantes') is not None and datos['participantes'] < 1:
            self.add_error('participantes', 'Indica al menos una persona.')
        if datos.get('tipo') == 'uso' and not (datos.get('zona') or datos.get('equipo')):
            self.add_error('zona', 'Elige un espacio o un equipo individual.')
        if datos.get('tipo') == 'servicio' and not datos.get('servicio'):
            self.add_error('servicio', 'Elige el servicio del portafolio que necesitas.')
        return datos


class DisponibilidadForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def clean_fecha(self):
        from datetime import timedelta
        from django.utils import timezone
        fecha = self.cleaned_data['fecha']
        hoy = timezone.localdate()
        if not hoy <= fecha <= hoy + timedelta(days=90):
            raise forms.ValidationError('Consulta una fecha entre hoy y los próximos 90 días.')
        return fecha


class SeguimientoForm(forms.Form):
    detalle = forms.CharField(label='Información o motivo', max_length=2000, widget=forms.Textarea(attrs={'rows': 3}))
