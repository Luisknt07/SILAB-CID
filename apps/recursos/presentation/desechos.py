"""Entrega de desechos al gestor autorizado, registrada desde la gestión de la unidad.

La generación y el almacenamiento de cada desecho se registran en el panel de administración.
Aquí la unidad anota, sobre esos registros, a qué gestor los entregó, con qué manifiesto y en
qué fecha, y adjunta el manifiesto escaneado: es lo que presenta y enlaza la tabla «Entregas al
gestor autorizado» del anexo de desechos. El archivo se abre solo con la vista protegida.
"""
from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_leer_expediente, puede_operar_modulo_unidad
from apps.recursos.models.desechos import RegistroDesecho

# El mismo módulo que ya protege el archivo del manifiesto (apps/recursos/entrega/archivos_acceso.py).
MODULO_DESECHOS = 'seguridad'
EXTENSIONES_MANIFIESTO = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg',
                          '.jpeg': 'image/jpeg'}
MAXIMO_BYTES_MANIFIESTO = 25 * 1024 * 1024
CAMPOS_DE_LA_ENTREGA = ('fecha_entrega', 'gestor_autorizado', 'licencia_gestor', 'manifiesto', 'responsable')
REGISTROS_EN_PANTALLA = 200


def validar_manifiesto(archivo):
    """PDF, PNG o JPG de hasta 25 MB y con contenido legible, como lo exige después la medición."""
    from apps.documentos.models.respaldo_medicion import validar_respaldo

    if Path(archivo.name).suffix.lower() not in EXTENSIONES_MANIFIESTO:
        raise ValidationError('El manifiesto debe ser un archivo PDF, PNG o JPG.')
    if archivo.size > MAXIMO_BYTES_MANIFIESTO:
        raise ValidationError('El manifiesto no puede superar 25 MB.')
    archivo.seek(0)
    copia = ContentFile(archivo.read(), name=archivo.name)
    archivo.seek(0)
    try:
        # Se revisa una copia: la comprobación cierra el archivo que recibe.
        validar_respaldo(copia)
    except ValidationError as error:
        raise ValidationError('El manifiesto debe ser un PDF o una imagen legible y con contenido; '
                              'revisa que el archivo no esté vacío, dañado ni protegido.') from error


def _etiqueta(desecho):
    return (f'{desecho.nombre} · {desecho.cantidad:g} {desecho.get_unidad_medida_display()} · '
            f'generado el {desecho.fecha_generacion:%d/%m/%Y}')


def _instantanea(desecho):
    """Los datos de la entrega, para dejar en la auditoría cómo estaban y cómo quedaron."""
    return {'etapa': desecho.etapa,
            'fecha_entrega': desecho.fecha_entrega.isoformat() if desecho.fecha_entrega else None,
            'gestor_autorizado': desecho.gestor_autorizado, 'licencia_gestor': desecho.licencia_gestor,
            'manifiesto': desecho.manifiesto, 'documento': desecho.documento.name if desecho.documento else '',
            'responsable': desecho.responsable_id}


class EntregaDesechoForm(forms.Form):
    """Una entrega al gestor: los desechos que salieron, los datos del manifiesto y su archivo."""

    desechos = forms.ModelMultipleChoiceField(
        queryset=RegistroDesecho.objects.none(), widget=forms.CheckboxSelectMultiple,
        label='Desechos almacenados que se entregaron',
        help_text='Marca todos los que salieron con este manifiesto.',
        error_messages={'required': 'Marca al menos un desecho almacenado.'})
    fecha_entrega = forms.DateField(label='Fecha de entrega al gestor',
                                    widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    gestor_autorizado = forms.CharField(label='Gestor ambiental autorizado', max_length=160)
    licencia_gestor = forms.CharField(label='Licencia o registro del gestor', max_length=80)
    manifiesto = forms.CharField(label='Número de manifiesto de entrega', max_length=80)
    responsable = forms.ModelChoiceField(queryset=get_user_model().objects.none(),
                                         label='Responsable de la entrega en la unidad')
    documento = forms.FileField(
        label='Manifiesto o acta escaneada', validators=[validar_manifiesto],
        widget=forms.FileInput(attrs={'accept': '.pdf,.png,.jpg,.jpeg'}),
        help_text='PDF, PNG o JPG de hasta 25 MB. La unidad comprueba que la autorización del gestor '
                  'corresponda al desecho entregado.')

    def __init__(self, *args, unidad, corregido=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidad, self.corregido = unidad, corregido
        personal = list(unidad.responsables_unidad.filter(activo=True).exclude(usuario=None)
                        .values_list('usuario_id', flat=True))
        personal.append(unidad.administrador_id)
        self.fields['responsable'].queryset = get_user_model().objects.filter(pk__in=personal, is_active=True)
        self.fields['responsable'].label_from_instance = lambda usuario: (
            usuario.get_full_name() or usuario.get_username())
        self.fields['responsable'].initial = unidad.administrador_id
        if corregido is None:
            self.fields['desechos'].queryset = RegistroDesecho.objects.filter(
                unidad=unidad, etapa='almacenado').order_by('fecha_generacion', 'pk')
            self.fields['desechos'].label_from_instance = _etiqueta
        else:
            # Se corrige una entrega ya registrada: el desecho está dado y el archivo actual se conserva
            # si no se sube otro.
            del self.fields['desechos']
            for campo in CAMPOS_DE_LA_ENTREGA:
                self.fields[campo].initial = (corregido.responsable_id if campo == 'responsable'
                                              else getattr(corregido, campo))
            if not corregido.responsable_id:
                self.fields['responsable'].initial = unidad.administrador_id
            if corregido.documento:
                self.fields['documento'].required = False
                self.fields['documento'].label = 'Reemplazar el manifiesto o acta escaneada'

    def clean_fecha_entrega(self):
        fecha = self.cleaned_data['fecha_entrega']
        if fecha > timezone.localdate():
            raise ValidationError('La entrega se registra cuando ya ocurrió: la fecha no puede ser futura.')
        return fecha

    def registros(self):
        return [self.corregido] if self.corregido is not None else list(self.cleaned_data['desechos'])


def registrar_entrega(request, unidad, form):
    """Deja entregados los desechos del formulario, con un mismo manifiesto, y lo anota en la auditoría.

    Nada se guarda si alguno de los registros no admite la entrega (por ejemplo, una fecha anterior
    a su generación): el modelo valida cada uno.
    """
    datos = form.cleaned_data
    archivo, guardado = datos.get('documento'), None
    try:
        with transaction.atomic():
            ids = [desecho.pk for desecho in form.registros()]
            registros = list(RegistroDesecho.objects.select_for_update().filter(unidad=unidad, pk__in=ids)
                             .order_by('fecha_generacion', 'pk'))
            if len(registros) != len(ids):
                raise ValidationError('Uno de los desechos ya no pertenece a esta unidad. Recarga la página.')
            for desecho in registros:
                esperada = 'entregado' if form.corregido is not None else 'almacenado'
                if desecho.etapa != esperada:
                    raise ValidationError(f'«{desecho.nombre}» cambió de etapa mientras llenabas el formulario. '
                                          'Recarga la página.')
                anteriores = _instantanea(desecho)
                desecho.etapa = 'entregado'
                for campo in CAMPOS_DE_LA_ENTREGA:
                    setattr(desecho, campo, datos[campo])
                if archivo:
                    if guardado is None:
                        # Un solo archivo para todos los desechos del manifiesto.
                        desecho.documento.save(archivo.name, archivo, save=False)
                        guardado = (desecho.documento.storage, desecho.documento.name)
                    else:
                        desecho.documento = guardado[1]
                try:
                    desecho.full_clean()
                except ValidationError as error:
                    raise ValidationError([f'{desecho.nombre}: {mensaje}' for mensaje in error.messages]) from error
                desecho.save()
                registrar_auditoria(
                    request, unidad=unidad, accion='actualizar', objeto=desecho,
                    descripcion=('Corrección de la entrega de desechos al gestor: manifiesto '
                                 if form.corregido is not None else
                                 'Entrega de desechos al gestor: manifiesto ') + desecho.manifiesto,
                    anteriores=anteriores, nuevos=_instantanea(desecho))
    except Exception:
        if guardado:
            guardado[0].delete(guardado[1])
        raise
    return registros


@login_required
@xframe_options_sameorigin
@require_http_methods(['GET', 'POST'])
def entregas_desechos_view(request, slug):
    """La pantalla de la unidad: registra una entrega nueva o corrige una ya registrada."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, MODULO_DESECHOS):
        raise PermissionDenied('No tienes acceso al registro de desechos de esta unidad.')
    clave = request.POST.get('corregir') or request.GET.get('corregir') or ''
    corregido = None
    if clave:
        if not clave.isdecimal():
            raise Http404
        # Acota por unidad: no se confía en el identificador de un registro de otra.
        corregido = get_object_or_404(RegistroDesecho, pk=clave, unidad=unidad, etapa='entregado')
    form = EntregaDesechoForm(request.POST or None, request.FILES or None, unidad=unidad, corregido=corregido)
    if request.method == 'POST' and form.is_valid():
        try:
            registros = registrar_entrega(request, unidad, form)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            if corregido is not None:
                messages.success(request, f'Entrega corregida: manifiesto {registros[0].manifiesto}.')
            else:
                cuantos = 'un desecho' if len(registros) == 1 else f'{len(registros)} desechos'
                messages.success(request, f'Entrega registrada: {cuantos} con el manifiesto '
                                          f'{registros[0].manifiesto}.')
            return redirect(reverse('entregas_desechos_unidad', args=[slug]))
    filas = list(RegistroDesecho.objects.filter(unidad=unidad).select_related('responsable')
                 .order_by('-fecha_generacion', '-pk')[:REGISTROS_EN_PANTALLA])
    return render(request, 'portal/pages/unidades/gestion/entregas_desechos.html', {
        'unidad': unidad, 'form': form, 'corregido': corregido, 'filas': filas,
        'hay_almacenados': corregido is not None or form.fields['desechos'].queryset.exists(),
    })


@login_required
@require_http_methods(['GET'])
def manifiesto_desecho_view(request, slug, desecho_id):
    """Entrega el manifiesto a quien gestiona la unidad o lee su expediente; nunca por la ruta de medios."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not (puede_operar_modulo_unidad(request.user, unidad, MODULO_DESECHOS)
            or puede_leer_expediente(request.user, unidad)):
        raise Http404
    desecho = get_object_or_404(RegistroDesecho, pk=desecho_id, unidad=unidad)
    archivo = desecho.documento
    if not archivo or not archivo.storage.exists(archivo.name):
        raise Http404
    extension = Path(archivo.name).suffix.lower()
    tipo = EXTENSIONES_MANIFIESTO.get(extension)
    respuesta = FileResponse(
        archivo.open('rb'), content_type=tipo,
        # Un archivo antiguo de otro formato se descarga; no se abre dentro del portal.
        as_attachment=not tipo or request.GET.get('download') == '1',
        filename=f'manifiesto-{desecho.pk}{extension}')
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    registrar_auditoria(request, unidad=unidad, accion='consultar', objeto=desecho,
                        descripcion='Consulta del manifiesto de desechos: ' + (desecho.manifiesto or 'sin número'))
    return respuesta
