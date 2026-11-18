"""Registro directo de fuentes de medición dentro del editor modal del expediente."""
from pathlib import Path
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import alcances_inventario, requiere_inspecciones_fisicas
from apps.documentos.models.infraestructura import TIPOS_INFRAESTRUCTURA, es_laboratorio_infraestructura
from apps.documentos.models.funcionalidad import TIPO_FUNCIONALIDAD
from apps.documentos.models.resultados_gestion import (
    CLAVES_DETALLE, CLAVES_RESULTADO, CLAVES_INSPECCION, CONDICIONES_REVISION, EMERGENCIAS_SIMULACRO,
    ESTADOS_CONDICIONES, ESTADOS_ACCION, TIPOS_PRODUCTO, TIPOS_RESULTADO, TIPO_SIMULACRO,
    TIPOS_ESTRUCTURADOS, condiciones_de, errores_resultado, lectura_condiciones,
)
from apps.documentos.presentation.medicion_metas import (
    habilitada, registrar_evidencia, rectificar_evidencia, evidencias_verificadas,
)
from apps.documentos.presentation.infraestructura_formularios import campos_infraestructura, detalle_infraestructura
from apps.documentos.presentation.funcionalidad_formularios import campos_funcionalidad
from apps.documentos.presentation.expediente import periodo_pedido
from apps.documentos.presentation.expediente_redaccion import actividades_para
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad, puede_leer_expediente
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.models.recursos import Recurso
from django.utils import timezone
from .formularios_perfiles import campos_perfil, detalle_perfil


class EvidenciaForm(forms.ModelForm):
    archivo = forms.FileField(required=False, label='Subir respaldo (PDF o imagen)')
    alcance = forms.MultipleChoiceField(required=False, choices=[('equipos', 'Equipos'),
        ('software', 'Software y licencias'), ('espacios', 'Espacios'),
        ('insumos', 'Reactivos e insumos')], widget=forms.CheckboxSelectMultiple)
    verificar = forms.BooleanField(required=False, label='He comprobado la actividad y su evidencia')
    proyecto = forms.CharField(required=False, max_length=300, label='Proyecto, trabajo o convenio relacionado')
    tipo_producto = forms.ChoiceField(required=False, choices=[('', 'Selecciona el tipo de producto')] + list(TIPOS_PRODUCTO),
        label='Tipo de producto o entregable')
    producto = forms.CharField(required=False, max_length=300, label='Producto o entregable obtenido')
    beneficiario = forms.CharField(required=False, max_length=300, label='Beneficiario o destinatario')
    aceptacion = forms.ChoiceField(required=False, choices=[('pendiente', 'Pendiente de aceptación'),
        ('aceptado', 'Aceptado por el destinatario')], label='Aceptación del entregable')
    fecha_aceptacion = forms.DateField(required=False, label='Fecha de aceptación',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    referencia_aceptacion = forms.CharField(required=False, max_length=300,
        label='Acta, constancia o referencia de aceptación',
        help_text='Debe estar respaldada por el archivo o enlace adjunto.')
    area = forms.CharField(required=False, max_length=300, label='Área o alcance de la inspección')
    condiciones_revisadas = forms.MultipleChoiceField(required=False, choices=CONDICIONES_REVISION,
        label='Condiciones revisadas', widget=forms.CheckboxSelectMultiple)
    sin_hallazgos = forms.BooleanField(required=False, label='Confirmo que la revisión no detectó hallazgos')
    hallazgos = forms.CharField(required=False, max_length=3000, label='Hallazgos detectados',
        widget=forms.Textarea(attrs={'rows': 3}))
    accion_correctiva = forms.CharField(required=False, max_length=3000, label='Acción correctiva o medida adoptada',
        widget=forms.Textarea(attrs={'rows': 3}))
    estado_condiciones = forms.ChoiceField(required=False,
        choices=[('', 'Selecciona la condición documentada')] + list(ESTADOS_CONDICIONES),
        label='Condición documentada')
    estado_accion = forms.ChoiceField(required=False,
        choices=[('', 'Selecciona el estado de la acción')] + list(ESTADOS_ACCION),
        label='Seguimiento de la acción')
    plazo_accion = forms.DateField(required=False, label='Plazo de la acción pendiente',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    class Meta:
        model = EvidenciaGestionUnidad
        fields = ['codigo', 'fecha', 'titulo', 'descripcion', 'responsable', 'recurso', 'enlace',
                  'desde', 'hasta', 'total_observado', 'alcance']
        labels = {'codigo': 'Código o referencia', 'titulo': 'Actividad realizada',
                  'descripcion': 'Resultado y evidencia', 'recurso': 'Usar un respaldo ya guardado',
                  'enlace': 'Enlace a una publicación', 'desde': 'Inicio del tramo observado',
                  'hasta': 'Fin del tramo observado', 'total_observado': 'Total observado en la bitácora'}
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'desde': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'hasta': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'descripcion': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, unidad, tipo, inicio, fin, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.unidad, self.instance.tipo = unidad, tipo
        self.inicio, self.fin = inicio, fin
        ids = list(unidad.responsables_unidad.filter(activo=True).exclude(usuario=None).values_list('usuario_id', flat=True))
        ids.append(unidad.administrador_id)
        self.fields['responsable'].initial = unidad.administrador_id
        self.fields['responsable'].queryset = get_user_model().objects.filter(pk__in=ids, is_active=True)
        self.fields['recurso'].queryset = Recurso.objects.filter(unidad=unidad, activo=True).exclude(archivo='')
        if tipo not in ('USO', 'DESECHOS'):
            for clave in ('desde', 'hasta', 'total_observado'):
                self.fields.pop(clave)
        if tipo != 'INVENTARIO':
            self.fields.pop('alcance')
        elif es_laboratorio_infraestructura(unidad):
            esperados = alcances_inventario(unidad)
            self.fields['alcance'].choices = [(clave, etiqueta) for clave, etiqueta in
                self.fields['alcance'].choices if clave in esperados]
            self.fields['revision_criticidad'] = forms.BooleanField(required=False,
                label='He revisado la criticidad de todos los equipos del inventario')
        if tipo not in TIPOS_RESULTADO:
            for clave in CLAVES_RESULTADO:
                self.fields.pop(clave)
        else:
            self.fields['fecha'].label = 'Fecha del resultado documentado'
            self.fields['titulo'].label = 'Título del resultado o servicio'
            self.fields['descripcion'].label = 'Resultado obtenido y aporte verificable'
            self.fields['descripcion'].help_text = (
                'Explica qué se obtuvo, para quién y cómo se comprobó. Reservas, horas de uso '
                'o actividades previstas no sustituyen el resultado.')
            self.fields['beneficiario'].help_text = (
                'Identifica la institución o grupo destinatario; evita datos personales innecesarios.')
            self.fields['verificar'].label = 'He comprobado el producto y su respaldo; corresponde a un resultado realizado'
            if tipo == 'INVESTIGACION':
                for clave in ('aceptacion', 'fecha_aceptacion', 'referencia_aceptacion'):
                    self.fields.pop(clave)
            self.order_fields(['codigo', 'fecha', 'titulo', 'proyecto', 'tipo_producto', 'producto',
                'beneficiario', 'descripcion', 'aceptacion', 'fecha_aceptacion', 'referencia_aceptacion',
                'responsable', 'archivo', 'recurso', 'enlace', 'verificar'])
        if tipo != 'INSPECCION':
            for clave in CLAVES_INSPECCION:
                self.fields.pop(clave)
        else:
            # Las comunes y las propias del tipo de unidad; las de otros tipos no se ofrecen.
            self.fields['condiciones_revisadas'].choices = condiciones_de(unidad)
            self.fields['fecha'].label = 'Fecha de la inspección realizada'
            self.fields['titulo'].label = 'Título o referencia del chequeo'
            self.fields['descripcion'].label = 'Descripción y conclusión de la revisión'
            self.fields['descripcion'].help_text = (
                'Describe lo comprobado y la conclusión del chequeo. Este registro no concede '
                'una habilitación de acceso ni sustituye las autorizaciones de operación.')
            self.fields['responsable'].label = 'Responsable de la revisión y su seguimiento'
            self.fields['verificar'].label = 'He comprobado la inspección y el respaldo de sus hallazgos y acciones'
            self.order_fields(['codigo', 'fecha', 'titulo', 'area', 'condiciones_revisadas',
                'estado_condiciones', 'sin_hallazgos', 'hallazgos', 'accion_correctiva',
                'estado_accion', 'plazo_accion', 'descripcion', 'responsable',
                'archivo', 'recurso', 'enlace', 'verificar'])
        if tipo == TIPO_SIMULACRO:
            # Lo propio del simulacro; su resultado u observaciones es la descripción de la evidencia.
            self.fields['emergencia'] = forms.ChoiceField(required=False, label='Emergencia ensayada',
                choices=[('', 'Selecciona la emergencia ensayada')] + list(EMERGENCIAS_SIMULACRO))
            self.fields['participantes'] = forms.IntegerField(required=False, min_value=1, max_value=100000,
                label='Número de participantes')
            self.fields['accion_mejora'] = forms.CharField(required=False, max_length=3000,
                label='Acción de mejora (opcional)', widget=forms.Textarea(attrs={'rows': 3}))
            self.fields['fecha'].label = 'Fecha del simulacro o la práctica'
            self.fields['titulo'].label = 'Nombre del simulacro o la práctica'
            self.fields['descripcion'].label = 'Resultado u observaciones'
            self.fields['descripcion'].help_text = (
                'Describe cómo se desarrolló el ejercicio y qué se observó: tiempos, rutas, equipos de '
                'emergencia y comportamiento de los participantes.')
            self.fields['responsable'].label = 'Responsable del simulacro'
            self.fields['archivo'].help_text = 'Adjunta el acta, la lista de participantes o las fotografías del ejercicio.'
            self.fields['verificar'].label = 'He comprobado que el simulacro se realizó y que su respaldo corresponde'
            self.order_fields(['codigo', 'fecha', 'titulo', 'emergencia', 'participantes', 'descripcion',
                'accion_mejora', 'responsable', 'archivo', 'recurso', 'enlace', 'verificar'])
        if tipo in TIPOS_INFRAESTRUCTURA:
            self.fields.update(campos_infraestructura(unidad, tipo))
            self.fields.pop('enlace')
            self.fields['archivo'].help_text = 'Adjunta un PDF o imagen legible. El plan y cada ejecución requieren su propio respaldo.'
            self.fields['fecha'].label = 'Fecha del plan documentado' if tipo == 'PLAN-INFRA' else 'Fecha del informe de ejecución'
            self.fields['titulo'].label = 'Título o referencia del plan' if tipo == 'PLAN-INFRA' else 'Título del informe de intervención'
            self.fields['descripcion'].label = 'Alcance y justificación del mantenimiento' if tipo == 'PLAN-INFRA' else 'Descripción de los trabajos realizados'
            self.fields['responsable'].label = 'Responsable de la planificación' if tipo == 'PLAN-INFRA' else 'Responsable de la ejecución'
            self.fields['verificar'].label = 'He comprobado el plan y su respaldo' if tipo == 'PLAN-INFRA' else 'He comprobado los trabajos finalizados y su informe'
            self.order_fields(['codigo', 'fecha', 'titulo', 'alcance_infraestructura', 'justificacion_alcance',
                'alcance_todo_laboratorio', 'espacio_id', 'ubicacion', 'intervencion',
                'criticidad', 'fecha_programada', 'frecuencia_dias', 'fecha_fin_programacion',
                'plan_id', 'fecha_inicio', 'fecha_fin', 'resultado', 'descripcion', 'responsable',
                'archivo', 'recurso', 'verificar'])
        elif tipo == TIPO_FUNCIONALIDAD:
            self.fields.update(campos_funcionalidad(unidad))
            self.fields.pop('enlace')
            self.fields['fecha'].label = 'Fecha de la prueba funcional realizada'
            self.fields['titulo'].label = 'Título o referencia de la verificación funcional'
            self.fields['descripcion'].label = 'Conclusión y alcance de la comprobación'
            self.fields['archivo'].help_text = 'Adjunta el informe, acta o evidencia legible de la prueba específica de este equipo.'
            self.fields['verificar'].label = 'He comprobado el procedimiento, el resultado y su respaldo'
            self.order_fields(['codigo', 'fecha', 'titulo', 'equipo_id', 'procedimiento', 'criterio',
                'resultado_funcional', 'hallazgos_funcionales', 'descripcion', 'responsable', 'archivo', 'recurso', 'verificar'])
        self.campos_del_perfil = campos_perfil(unidad, tipo, inicio, fin)
        if self.campos_del_perfil:
            self.fields.update(self.campos_del_perfil)
            self.fields['verificar'].label = 'Como responsable técnico o coordinación, he comprobado estos datos y su respaldo'
            self.order_fields(['codigo', 'fecha', 'titulo', *self.campos_del_perfil, 'descripcion',
                               'responsable', 'archivo', 'recurso', 'enlace', 'verificar'])

    def clean(self):
        datos = super().clean()
        if self.instance.tipo in TIPOS_ESTRUCTURADOS:
            detalle = {}
            for clave in CLAVES_DETALLE:
                if clave not in self.fields:
                    continue
                valor = datos.get(clave)
                detalle[clave] = valor.pk if hasattr(valor, 'pk') else (
                    valor.isoformat() if hasattr(valor, 'isoformat') else '' if valor is None else valor)
            if self.instance.tipo in TIPOS_INFRAESTRUCTURA:
                detalle = detalle_infraestructura(datos, self.fields)
            if self.campos_del_perfil:
                detalle = detalle_perfil(datos, self.campos_del_perfil)
            self.instance.detalle = detalle
            if datos.get('verificar'):
                for clave, error in errores_resultado(self.instance.tipo, detalle, datos.get('fecha'),
                                                      unidad=self.instance.unidad).items():
                    if clave in datos or clave not in self.errors:
                        self.add_error(clave, error)
        elif self.instance.tipo == 'INVENTARIO' and 'revision_criticidad' in self.fields:
            self.instance.detalle = {'revision_criticidad': bool(datos.get('revision_criticidad'))}
        return datos

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if not self.inicio <= fecha <= self.fin:
            raise ValidationError('La fecha debe pertenecer al período seleccionado.')
        return fecha


@login_required
@require_http_methods(['GET', 'POST'])
def fuentes_metas_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not habilitada() or not puede_operar_modulo_unidad(request.user, unidad, 'reportes'):
        raise PermissionDenied('No tienes acceso al registro de evidencias de esta unidad.')
    anio, corte, cortes = periodo_pedido(request, timezone.localdate())
    corte = corte or 'B'
    inicio, fin = cortes[corte]
    tipos = {a.codigo for a in actividades_para(unidad)} & dict(EvidenciaGestionUnidad.TIPOS).keys()
    tipos.add('INSPECCION')  # Registro documental disponible sin crear una meta numérica adicional.
    if requiere_inspecciones_fisicas(unidad):
        # Los simulacros se registran donde hay inspecciones físicas; el observatorio no las lleva. No son una meta.
        tipos.add(TIPO_SIMULACRO)
    if es_laboratorio_infraestructura(unidad):
        tipos.update(TIPOS_INFRAESTRUCTURA)
        tipos.add(TIPO_FUNCIONALIDAD)
    tipo = request.POST.get('tipo') or request.GET.get('tipo') or 'CAPACITACION'
    alias_perfil = {'DATOS-ACTUALIZADOS': ('BOLETINES', 'datos'), 'CONTROL-CALIDAD': ('PRODUCCION', 'control_calidad')}
    subtipo_inicial = ''
    if tipo in alias_perfil and tipo in {a.codigo for a in actividades_para(unidad)}:
        tipo, subtipo_inicial = alias_perfil[tipo]
    if tipo not in tipos:
        raise PermissionDenied('El indicador no corresponde a este tipo de unidad.')
    form = EvidenciaForm(request.POST or None, request.FILES or None, unidad=unidad, tipo=tipo, inicio=inicio, fin=fin)
    if subtipo_inicial and 'subtipo' in form.fields:
        form.fields['subtipo'].initial = subtipo_inicial
    if request.method == 'POST':
        try:
            if request.POST.get('accion') == 'rectificar':
                # Acota por unidad antes de pasar al servicio y no confía en un ID de otra unidad.
                clave = request.POST.get('evidencia', '')
                if not clave.isdecimal():
                    raise Http404
                e = get_object_or_404(EvidenciaGestionUnidad, pk=clave, unidad=unidad, tipo=tipo)
                rectificar_evidencia(unidad, request.user, e.pk, request.POST.get('motivo'))
                messages.success(request, 'Evidencia rectificada. El archivo anterior y el historial se conservan.')
            elif form.is_valid():
                datos = {k: v for k, v in form.cleaned_data.items()
                         if k not in ('verificar', 'archivo') and k not in CLAVES_DETALLE}
                datos['detalle'] = form.instance.detalle
                registrar_evidencia(unidad, request.user, dict(datos, tipo=tipo),
                    verificar=form.cleaned_data['verificar'], archivo=form.cleaned_data['archivo'])
                messages.success(request, 'Simulacro guardado. Se presenta en su documento de «Respaldo para auditoría», en el Centro de reportes.'
                    if tipo == TIPO_SIMULACRO else 'Evidencia guardada. Solo las verificadas acreditan cumplimiento.')
            else:
                raise ValidationError('Revisa los campos indicados.')
            return redirect(reverse('fuentes_metas_unidad', args=[slug]) + f'?anio={anio}&corte={corte}&tipo={tipo}&_panel=1')
        except ValidationError as error:
            form.add_error(None, ValidationError(error.messages))
    filas = list(EvidenciaGestionUnidad.objects.filter(unidad=unidad, tipo=tipo, fecha__range=(inicio, fin)).select_related('recurso'))
    verificadas = {e.pk for e in evidencias_verificadas(unidad, filas, inicio, fin)}
    for fila in filas:
        fila.respaldo_pdf = bool(fila.recurso_id and Path(fila.recurso.archivo.name).suffix.lower() == '.pdf')
        fila.estado_lectura = ('Verificación pendiente' if
            fila.estado == 'validado' and fila.pk not in verificadas else fila.get_estado_display())
        if tipo == 'INSPECCION':
            detalle = fila.detalle if isinstance(fila.detalle, dict) else {}
            fila.condicion_lectura = dict(ESTADOS_CONDICIONES).get(detalle.get('estado_condiciones'), 'Sin documentar')
            fila.accion_lectura = dict(ESTADOS_ACCION).get(detalle.get('estado_accion'), 'Sin documentar')
            revisadas, exigidas, _cuales = lectura_condiciones(unidad, detalle.get('condiciones_revisadas'))
            fila.condiciones_lectura = f'{revisadas} de {exigidas}'
        elif tipo == TIPO_SIMULACRO:
            detalle = fila.detalle if isinstance(fila.detalle, dict) else {}
            emergencia = detalle.get('emergencia') if isinstance(detalle.get('emergencia'), str) else ''
            fila.emergencia_lectura = dict(EMERGENCIAS_SIMULACRO).get(emergencia, 'Sin identificar')
        elif tipo in TIPOS_INFRAESTRUCTURA:
            from apps.documentos.models.infraestructura import CRITICIDADES_INFRAESTRUCTURA
            detalle = fila.detalle if isinstance(fila.detalle, dict) else {}
            criticidad = detalle.get('criticidad') if isinstance(detalle.get('criticidad'), str) else ''
            fila.criticidad_lectura = dict(CRITICIDADES_INFRAESTRUCTURA).get(criticidad, 'Sin definir')
        elif tipo == TIPO_FUNCIONALIDAD:
            from apps.documentos.models.funcionalidad import RESULTADOS_FUNCIONALES
            detalle = fila.detalle if isinstance(fila.detalle, dict) else {}
            resultado = detalle.get('resultado_funcional') if isinstance(detalle.get('resultado_funcional'), str) else ''
            fila.resultado_lectura = dict(RESULTADOS_FUNCIONALES).get(resultado, 'Sin resultado documentado')
    return render(request, 'portal/pages/unidades/gestion/fuentes_metas.html', dict(unidad=unidad, form=form,
        filas=filas, anio=anio, corte=corte, tipo=tipo, resultado_estructurado=tipo in TIPOS_RESULTADO,
        infraestructura=tipo in TIPOS_INFRAESTRUCTURA, funcionalidad=tipo == TIPO_FUNCIONALIDAD,
        simulacro=tipo == TIPO_SIMULACRO,
        nombre=dict(EvidenciaGestionUnidad.TIPOS)[tipo]))


@login_required
@require_http_methods(['GET'])
def respaldo_meta_view(request, slug, evidencia_id):
    unidad = get_object_or_404(Unidad, slug=slug)
    if not habilitada() or not puede_leer_expediente(request.user, unidad):
        raise Http404
    evidencia = get_object_or_404(EvidenciaGestionUnidad.objects.select_related('recurso'),
        pk=evidencia_id, unidad=unidad, recurso__isnull=False, recurso__activo=True)
    archivo = evidencia.recurso.archivo
    tipos = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
    tipo = tipos.get(Path(archivo.name).suffix.lower())
    if not tipo or not archivo.storage.exists(archivo.name):
        raise Http404
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad
    original = RegistroAuditoriaUnidad.objects.filter(unidad=unidad, entidad=evidencia._meta.label,
        objeto_id=str(evidencia.pk), accion='crear').order_by('-pk').first()
    if not original or original.datos_nuevos.get('sha256') != evidencia.recurso.hash_sha256:
        raise Http404('El archivo cambió después de registrar la evidencia.')
    from apps.documentos.models.respaldo_medicion import validar_respaldo
    try:
        if validar_respaldo(archivo) != evidencia.recurso.hash_sha256:
            raise Http404('La huella del archivo no coincide con la evidencia.')
    except ValidationError as error:
        raise Http404 from error
    respuesta = FileResponse(archivo.open('rb'), content_type=tipo,
        as_attachment=request.GET.get('download') == '1', filename=Path(archivo.name).name)
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    registrar_auditoria(request, unidad=unidad, accion='consultar', objeto=evidencia,
        descripcion='Consulta de respaldo de medición: ' + evidencia.codigo)
    return respuesta
