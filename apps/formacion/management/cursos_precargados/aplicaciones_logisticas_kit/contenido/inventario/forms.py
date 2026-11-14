import uuid
from django import forms
from .models import Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["codigo", "nombre", "unidad", "minimo"]

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


class MovimientoForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.all())
    tipo = forms.ChoiceField(choices=[("E", "Entrada"), ("S", "Salida")])
    cantidad = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        localize=False,
        help_text="Use punto decimal; ejemplo: 12.50.",
    )
    motivo = forms.CharField(max_length=160)
    clave = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)


class ImportarForm(forms.Form):
    archivo = forms.FileField(help_text="CSV UTF-8, comas, hasta 100 productos y 1 MB.")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > 1_048_576:
            raise forms.ValidationError("El archivo supera 1 MB.")
        if not archivo.name.lower().endswith(".csv"):
            raise forms.ValidationError("Seleccione un archivo .csv.")
        return archivo
