"""Importación privada de participantes: plantilla, revisión, confirmación y descarga."""
import csv
import hashlib
import io
import json
import secrets
import tempfile
import time
import zipfile

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.formacion.presentation.certificados_cursos import _certificados_del_curso, _curso_del_editor, pdf_del_certificado
from apps.recursos.presentation.importacion_archivos import leer_participantes
from apps.formacion.presentation.importacion_participantes import confirmar_importacion, contexto_evento, revisar_importacion
from apps.formacion.presentation.matriculas_cursos import seleccionar_edicion

CLAVE_SESION = 'importacion_participantes_v1'
VIGENCIA = 20 * 60


class ImportacionParticipantesForm(forms.Form):
    edicion = forms.ModelChoiceField(label='Grupo o edición', queryset=None, empty_label='Selecciona un grupo')
    modo = forms.ChoiceField(label='Qué deseas importar', choices=(('matricula', 'Inscribir en el curso'), ('evento', 'Emitir certificados de un evento')))
    tipo = forms.ChoiceField(label='Certificado del evento', required=False, choices=(
        ('asistencia', 'Participación por asistencia'), ('participacion', 'Participación'),
        ('ponente', 'Participación como ponente'), ('organizador', 'Participación en la organización')))
    motivo = forms.CharField(label='Registro que respalda la acreditación del evento', required=False,
        min_length=10, max_length=300, widget=forms.Textarea(attrs={'rows': 2}),
        help_text='Por ejemplo: asistencia comprobada en el registro del evento. Para matrículas no se requiere.')
    archivo = forms.FileField(label='Lista de participantes', widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.csv'}))

    def __init__(self, *args, curso, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['edicion'].queryset = curso.ediciones.all()

    def clean(self):
        datos = super().clean()
        if datos.get('modo') == 'evento':
            for campo in ('tipo', 'motivo'):
                if not datos.get(campo):
                    self.add_error(campo, 'Completa este dato para acreditar un evento.')
        return datos


def _huella_actividad(edicion, tipo, motivo):
    actividad = contexto_evento(edicion, tipo, motivo, True)
    return hashlib.sha256(json.dumps(actividad, sort_keys=True, default=str).encode()).hexdigest()


def _estado_session(request, curso, token):
    estado = request.session.get(CLAVE_SESION, {})
    if (not token or not secrets.compare_digest(str(estado.get('token', '')), str(token)) or
            estado.get('actor') != request.user.pk or estado.get('curso') != curso.pk or
            time.time() - estado.get('creado', 0) > VIGENCIA):
        raise ValidationError('La revisión expiró o no corresponde a esta sesión. Vuelve a subir la lista.')
    return estado


def _contexto(curso, formulario, **extra):
    return {'curso': curso, 'unidad': curso.unidad, 'formulario': formulario,
        'inscritos_url': reverse('inscritos_curso', args=[curso.unidad.slug, curso.codigo]),
        'plantilla_url': reverse('plantilla_participantes_curso', args=[curso.unidad.slug, curso.codigo]), **extra}


@login_required
@never_cache
@xframe_options_sameorigin
@require_http_methods(['GET', 'POST'])
def importar_participantes_view(request, slug, codigo):
    curso = _curso_del_editor(request, slug, codigo)
    if settings.SESSION_ENGINE == 'django.contrib.sessions.backends.signed_cookies':
        return HttpResponse('La importación requiere sesiones almacenadas en el servidor. Configure el backend de sesiones de la institución.', status=503)
    inicial = {'edicion': request.GET.get('edicion'), 'modo': request.GET.get('modo', 'matricula'), 'tipo': 'asistencia'}
    formulario = ImportacionParticipantesForm(curso=curso, initial=inicial)
    contexto = _contexto(curso, formulario)
    if request.method == 'POST' and request.POST.get('accion') == 'confirmar':
        try:
            estado = _estado_session(request, curso, request.POST.get('token'))
            if estado.get('resultado') is not None:
                contexto.update(resultado=estado['resultado'], estado=estado)
            else:
                if not request.POST.get('confirmacion'):
                    raise ValidationError('Confirma que revisaste la lista y, para eventos, el registro que respalda la acreditación.')
                edicion = seleccionar_edicion(curso, estado['edicion'])
                if estado['modo'] == 'evento' and estado['huella'] != _huella_actividad(edicion, estado['tipo'], estado['motivo']):
                    raise ValidationError('Las fechas, horas o datos de la actividad cambiaron. Revisa nuevamente la lista antes de emitir.')
                resultado = confirmar_importacion(edicion, estado['filas'], request.user, estado['modo'],
                    estado['tipo'], estado['motivo'], True)
                estado['resultado'] = resultado
                request.session[CLAVE_SESION] = estado
                contexto.update(resultado=resultado, estado=estado)
        except ValidationError as exc:
            contexto['errores'] = exc.messages
    elif request.method == 'POST':
        request.session.pop(CLAVE_SESION, None)
        formulario = ImportacionParticipantesForm(request.POST, request.FILES, curso=curso)
        contexto['formulario'] = formulario
        if formulario.is_valid():
            datos = formulario.cleaned_data
            try:
                filas = leer_participantes(datos['archivo'], datos['modo'])
                contexto.update(filas=filas, modo=datos['modo'], edicion=datos['edicion'])
                actividad = revisar_importacion(datos['edicion'], filas, request.user, datos['modo'],
                    datos['tipo'], datos['motivo'], True)
                contexto.update(filas=filas, actividad=actividad, modo=datos['modo'], edicion=datos['edicion'])
                if not any(f['errores'] for f in filas):
                    estado = {'token': secrets.token_urlsafe(32), 'actor': request.user.pk, 'curso': curso.pk,
                        'edicion': datos['edicion'].pk, 'modo': datos['modo'], 'tipo': datos['tipo'],
                        'motivo': datos['motivo'], 'filas': filas, 'creado': time.time(),
                        'huella': _huella_actividad(datos['edicion'], datos['tipo'], datos['motivo']) if actividad else ''}
                    request.session[CLAVE_SESION] = estado
                    contexto['estado'] = estado
            except ValidationError as exc:
                contexto['errores'] = exc.messages
    respuesta = render(request, 'portal/pages/unidades/aula/importar_participantes.html', contexto)
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
@never_cache
@require_GET
def plantilla_participantes_view(request, slug, codigo):
    _curso_del_editor(request, slug, codigo)
    modo = request.GET.get('modo', 'matricula')
    if modo not in ('evento', 'matricula'):
        raise Http404('Operación no válida.')
    columnas = ['cedula', 'nombres_completos'] + (['correo'] if modo == 'matricula' else [])
    if request.GET.get('formato') == 'csv':
        contenido = io.StringIO(newline='')
        csv.writer(contenido).writerow(columnas)
        respuesta = HttpResponse('\ufeff' + contenido.getvalue(), content_type='text/csv; charset=utf-8')
        extension = 'csv'
    else:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
        libro = Workbook()
        hoja = libro.active
        hoja.title = 'Participantes'
        hoja.append(columnas)
        hoja.freeze_panes = 'A2'
        for celda in hoja[1]:
            celda.font = Font(bold=True, color='FFFFFF', size=12)
            celda.fill = PatternFill('solid', fgColor='235D38')
            celda.alignment = Alignment(vertical='center')
        hoja.row_dimensions[1].height = 28
        for indice, ancho in enumerate((25, 58, 45)[:len(columnas)], start=1):
            hoja.column_dimensions[chr(64 + indice)].width = ancho
        for fila in hoja.iter_rows(min_row=2, max_row=501, max_col=len(columnas)):
            for celda in fila:
                celda.number_format = '@'
        validacion = DataValidation(type='textLength', operator='between', formula1=4, formula2=30, allow_blank=True)
        validacion.errorTitle, validacion.error = 'Documento como texto', 'Escribe la cédula completa conservando los ceros iniciales.'
        validacion.showErrorMessage = True
        hoja.add_data_validation(validacion)
        validacion.add('A2:A501')
        contenido = io.BytesIO()
        libro.save(contenido)
        libro.close()
        respuesta = HttpResponse(contenido.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        extension = 'xlsx'
    respuesta['Content-Disposition'] = f'attachment; filename="plantilla-{modo}.{extension}"'
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
@never_cache
@require_POST
def descargar_certificados_importados_view(request, slug, codigo):
    curso = _curso_del_editor(request, slug, codigo, solo_activa=False)
    try:
        estado = _estado_session(request, curso, request.POST.get('token'))
    except ValidationError as exc:
        return HttpResponse(' '.join(exc.messages), status=400, content_type='text/plain; charset=utf-8')
    if estado['modo'] != 'evento' or not estado.get('resultado'):
        raise Http404('No hay certificados emitidos en esta importación.')
    ids = [f['certificado_id'] for f in estado['resultado']]
    certificados = list(_certificados_del_curso(curso).filter(pk__in=ids, anulado=False))
    if len(certificados) != len(set(ids)):
        return HttpResponse('Un certificado fue anulado. Revisa los resultados antes de descargar.', status=409)
    archivo = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode='w+b')
    try:
        total = 0
        with zipfile.ZipFile(archivo, 'w', zipfile.ZIP_DEFLATED) as paquete:
            for certificado in certificados:
                pdf = pdf_del_certificado(certificado)
                total += len(pdf)
                if total > 200 * 1024 * 1024:
                    raise ValidationError('La descarga supera 200 MB. Descarga los certificados individualmente desde la lista.')
                paquete.writestr(f'certificado-{certificado.codigo}.pdf', pdf)
        archivo.seek(0)
        respuesta = FileResponse(archivo, as_attachment=True, filename='certificados-evento.zip', content_type='application/zip')
        respuesta['Cache-Control'] = 'private, no-store'
        return respuesta
    except ValidationError as exc:
        archivo.close()
        return HttpResponse(' '.join(exc.messages), status=400, content_type='text/plain; charset=utf-8')
    except Exception:
        archivo.close()
        raise
