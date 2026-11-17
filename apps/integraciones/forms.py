from django import forms


class PeriodoForm(forms.Form):
    ambito = forms.ChoiceField(label="Responsabilidad", choices=())
    inicio = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    fin = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, opciones=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ambito"].choices = opciones


class EvidenciaForm(forms.Form):
    centro = forms.ChoiceField(label="Centro", choices=())
    codigo = forms.SlugField(label="Código documental", max_length=100)
    inicio = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    fin = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    titulo = forms.CharField(label="Título", max_length=240)
    fuente = forms.URLField(
        label="Enlace HTTPS al documento o expediente", max_length=1000
    )
    huella_archivo = forms.CharField(
        label="SHA-256 verificada (opcional)", required=False, max_length=64
    )
    documento_id = forms.TypedChoiceField(
        coerce=int,
        empty_value=None,
        choices=(),
        label="Documento del Centro (opcional)",
        required=False,
    )


class ReferenciaForm(forms.Form):
    registro = forms.ChoiceField(label="Proyecto o resultado del Centro", choices=())
    sistema = forms.CharField(label="Sistema oficial de origen", max_length=150)
    identificador = forms.CharField(
        label="Expediente o identificador oficial", max_length=200
    )
    fuente = forms.URLField(label="Fuente oficial HTTPS", max_length=1000)
    estado_oficial = forms.CharField(
        label="Estado consignado en la fuente oficial", max_length=120
    )


class ActivoForm(forms.Form):
    codigo = forms.CharField(label="Código institucional del activo", max_length=80)
    registro = forms.ChoiceField(
        label="Equipo individual y su inventario de origen", choices=()
    )
    fuente = forms.URLField(
        label="Respaldo institucional HTTPS de la identificación", max_length=1000
    )
