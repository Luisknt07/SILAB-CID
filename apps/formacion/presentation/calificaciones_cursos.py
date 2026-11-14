"""Evaluaciones y deberes de los cursos: se rinden y se entregan en el aula, y la unidad los califica.

Una evaluación tiene preguntas que se califican solas (una o varias respuestas correctas, o una respuesta corta) y
se aprueba al alcanzar su nota mínima dentro de los intentos permitidos. Un deber se entrega con un archivo, un
enlace o un comentario; el instructor lo califica con nota y retroalimentación, o lo devuelve para corregir. Ambos
cuentan como lección completada solo al aprobarlos, que es lo que después exige el certificado.
"""
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.core.identificadores import id_solicitado

from apps.formacion.models.cursos import Curso, EntregaDeber, IntentoEvaluacion, LeccionCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad

from apps.formacion.presentation.aula_cursos import _acceso_al_aula, _curso, archivo_protegido, avance, completar, lecciones_de, marcar_avance
from apps.formacion.presentation.cursos import puede_crear_cursos
from apps.formacion.presentation.notas_cursos import nota_desde_diez, nota_sobre_diez
from apps.formacion.presentation.seguimiento_cursos import seguimiento_de, url_del_grupo


TAMANO_MAXIMO_ENTREGA = 25 * 1024 * 1024


class EntregaForm(forms.ModelForm):
    class Meta:
        model = EntregaDeber
        fields = ('archivo', 'enlace', 'comentario')
        widgets = {'comentario': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Lo que el instructor debe saber de tu trabajo'}),
                   'enlace': forms.URLInput(attrs={'placeholder': 'https://…'})}

    def clean(self):
        datos = super().clean()
        archivo = datos.get('archivo')
        if archivo and getattr(archivo, 'size', 0) > TAMANO_MAXIMO_ENTREGA:
            self.add_error('archivo', f'El archivo pesa más de {TAMANO_MAXIMO_ENTREGA // (1024 * 1024)} MB: comprímelo o '
                                      'súbelo a la nube y pega el enlace.')
        if not archivo and not datos.get('enlace') and not (self.instance.pk and self.instance.archivo):
            raise forms.ValidationError('Suba el archivo del trabajo o escriba el enlace donde está.')
        return datos


def intentos_de(leccion, inscripcion):
    return list(IntentoEvaluacion.objects.filter(leccion=leccion, inscripcion=inscripcion).order_by('-entregado_en', '-pk')) if inscripcion else []


def contexto_calificada(leccion, inscripcion, vista_previa, formulario=None):
    """Lo que el aula muestra de una evaluación o un deber: preguntas, intentos, resultado o entrega."""
    if leccion is None or not leccion.calificada:
        return {}
    if leccion.tipo == 'evaluacion':
        preguntas = list(leccion.preguntas.all())
        intentos = intentos_de(leccion, inscripcion)
        aprobado = any(intento.aprobado for intento in intentos)
        restantes = max(leccion.intentos - len(intentos), 0)
        ultimo = intentos[0] if intentos else None
        # Qué se acertó, las respuestas correctas y las explicaciones se muestran solo al aprobar o al agotar los
        # intentos; mientras queden, el intento muestra su nota y cuántas preguntas acertó, para no aprobar probando.
        revelar = vista_previa or aprobado or restantes == 0
        for pregunta in preguntas:
            pregunta.respondio = ultimo.respuestas.get(str(pregunta.pk), []) if ultimo else []
            pregunta.acerto = ultimo.aciertos.get(str(pregunta.pk)) if ultimo and revelar else None
        return {'evaluacion': {
            'preguntas': preguntas, 'intentos': intentos, 'ultimo': ultimo, 'aprobado': aprobado,
            'restantes': restantes, 'revelar': revelar,
            'disponibles': restantes if not aprobado and not leccion.vencida() else 0,
            'correctas': sum(1 for acierto in ultimo.aciertos.values() if acierto) if ultimo else 0,
            'vencida': leccion.vencida(),
            'mejor': max((intento.nota for intento in intentos), default=None),
            'minima_10': nota_sobre_diez(leccion.nota_minima),
            'historial': [{'numero': numero, 'intento': intento}
                          for numero, intento in reversed(list(enumerate(reversed(intentos), 1)))],
            'bloqueada': getattr(leccion, 'bloqueada', False), 'pendientes': getattr(leccion, 'pendientes', []),
            'puede_rendir': (not vista_previa and bool(preguntas) and not aprobado and restantes > 0 and not leccion.vencida()
                             and not getattr(leccion, 'bloqueada', False)),
        }}
    entrega = EntregaDeber.objects.filter(leccion=leccion, inscripcion=inscripcion).first() if inscripcion else None
    return {'deber': {
        'entrega': entrega, 'vencida': leccion.vencida(),
        # Se puede entregar o reemplazar mientras no esté aprobado.
        'puede_entregar': not vista_previa and (entrega is None or entrega.estado != 'aprobada'),
        'formulario': formulario or EntregaForm(instance=entrega),
    }}


def evaluacion_bloqueada(leccion, inscripcion):
    """Si a la persona todavía le faltan lecciones obligatorias anteriores a esta evaluación."""
    curso = leccion.modulo.curso
    modulos = lecciones_de(curso)
    marcar_avance(modulos, avance(curso, inscripcion, modulos)['hechas'])
    return next((propia.bloqueada for modulo in modulos for propia in modulo.visibles if propia.pk == leccion.pk), True)


def calificar_intento(leccion, datos):
    """(respuestas, aciertos, nota en %) de lo que llegó en el formulario."""
    respuestas, aciertos, obtenidos, total = {}, {}, 0, 0
    for pregunta in leccion.preguntas.all():
        clave = str(pregunta.pk)
        respuesta = [valor.strip() for valor in datos.getlist(f'p{pregunta.pk}') if valor.strip()]
        respuestas[clave] = respuesta
        aciertos[clave] = pregunta.es_correcta(respuesta)
        total += pregunta.puntos
        obtenidos += pregunta.puntos if aciertos[clave] else 0
    nota = (Decimal(100) * obtenidos / total).quantize(Decimal('0.01')) if total else Decimal(0)
    return respuestas, aciertos, nota


def _leccion_del_aula(request, slug, codigo, leccion_id, tipo):
    unidad, curso = _curso(slug, codigo, request.user)
    inscripcion, vista_previa = _acceso_al_aula(request, unidad, curso)
    if vista_previa:
        raise PermissionDenied('La vista previa no rinde evaluaciones ni entrega deberes.')
    leccion = get_object_or_404(LeccionCurso, pk=leccion_id, modulo__curso=curso, publicada=True, tipo=tipo)
    destino = url_del_grupo('aula_curso_leccion', curso, inscripcion.edicion_id, leccion.pk)
    return inscripcion, leccion, destino


@login_required
@require_POST
def rendir_evaluacion_view(request, slug, codigo, leccion_id):
    inscripcion, leccion, destino = _leccion_del_aula(request, slug, codigo, leccion_id, 'evaluacion')
    with transaction.atomic():
        # Con la inscripción bloqueada, dos envíos a la vez no pasan del número de intentos.
        type(inscripcion).objects.select_for_update().filter(pk=inscripcion.pk).first()
        intentos = intentos_de(leccion, inscripcion)
        if (leccion.vencida() or any(intento.aprobado for intento in intentos) or len(intentos) >= leccion.intentos
                or not leccion.preguntas.exists() or evaluacion_bloqueada(leccion, inscripcion)):
            return redirect(destino)
        respuestas, aciertos, nota = calificar_intento(leccion, request.POST)
        aprobado = nota >= leccion.nota_minima
        IntentoEvaluacion.objects.create(inscripcion=inscripcion, leccion=leccion, respuestas=respuestas,
                                         aciertos=aciertos, nota=nota, aprobado=aprobado)
        if aprobado:
            completar(inscripcion, leccion)
    return redirect(destino + '#resultado')


@login_required
@require_POST
@transaction.atomic
def entregar_deber_view(request, slug, codigo, leccion_id):
    inscripcion, leccion, destino = _leccion_del_aula(request, slug, codigo, leccion_id, 'deber')
    # La misma fila coordina envíos, calificaciones y finalización del aula.
    type(inscripcion).objects.select_for_update().get(pk=inscripcion.pk)
    entrega = EntregaDeber.objects.filter(leccion=leccion, inscripcion=inscripcion).first()
    if entrega is not None and entrega.estado == 'aprobada':
        return redirect(destino)
    entrega = entrega or EntregaDeber(leccion=leccion, inscripcion=inscripcion)
    formulario = EntregaForm(request.POST, request.FILES, instance=entrega)
    if formulario.is_valid():
        anterior = EntregaDeber.objects.filter(pk=entrega.pk).values_list('archivo', flat=True).first() if entrega.pk else None
        entrega = formulario.save(commit=False)
        # Una entrega nueva o corregida vuelve a esperar la revisión del instructor.
        entrega.estado, entrega.entregada_en, entrega.nota = 'entregada', timezone.now(), None
        entrega.save()
        # Conservar el original hasta confirmar también cualquier transacción exterior.
        if anterior and anterior != entrega.archivo.name:
            almacen = entrega.archivo.storage
            transaction.on_commit(
                lambda nombre=anterior, storage=almacen: storage.delete(nombre),
                robust=True,
            )
        return redirect(destino + '#entrega')
    # El aula de nuevo, con el formulario de entrega y sus errores.
    from apps.formacion.presentation.aula_cursos import aula_view
    request.entrega_con_errores = formulario
    return aula_view(request, slug, codigo, leccion.pk)


def _puede_ver_entrega(usuario, entrega):
    curso = entrega.leccion.modulo.curso
    return entrega.inscripcion.usuario_id == usuario.pk or puede_crear_cursos(usuario, curso.unidad)


@login_required
def archivo_entrega_view(request, slug, codigo, entrega_id):
    entrega = get_object_or_404(EntregaDeber.objects.select_related('leccion__modulo__curso__unidad', 'inscripcion'),
                                pk=entrega_id, leccion__modulo__curso__codigo=codigo,
                                leccion__modulo__curso__unidad__slug=slug)
    if not _puede_ver_entrega(request.user, entrega):
        raise PermissionDenied('Solo quien entregó y quien califica ven este trabajo.')
    if not entrega.archivo:
        raise Http404()
    return archivo_protegido(entrega.archivo)


@login_required
@never_cache
@xframe_options_sameorigin
def calificaciones_view(request, slug, codigo):
    """Libro de una cohorte: notas /10, cada intento y estados académicos."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    curso = get_object_or_404(Curso, unidad=unidad, codigo=codigo)
    if not puede_crear_cursos(request.user, unidad):
        if not curso.publicado:
            raise Http404('El curso no está publicado.')
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad califica.')
    ediciones = list(curso.ediciones.all())
    solicitada = request.GET.get('edicion')
    if solicitada is not None:
        elegida = next((edicion for edicion in ediciones if str(edicion.pk) == solicitada), None)
        if elegida is None:
            raise Http404('Este grupo no pertenece al curso.')
    else:
        elegida = curso.edicion_vigente() or (ediciones[0] if ediciones else None)
    error_calificacion = None
    if request.method == 'POST':
        error_calificacion = _calificar(request, curso, elegida)
        if error_calificacion is None:
            messages.success(request, 'Trabajo devuelto para corregir.' if request.POST.get('accion') == 'devolver'
                             else 'Calificación guardada correctamente.')
            return redirect(request.get_full_path())
    modulos = lecciones_de(curso)
    calificadas = [leccion for modulo in modulos for leccion in modulo.visibles if leccion.calificada and leccion.publicada]
    inscritos = list(elegida.inscripciones.filter(estado='aceptada').select_related('usuario', 'edicion__curso__unidad')
                     .prefetch_related('progresos', 'intentos', 'entregas', 'certificados')
                     .order_by('usuario__last_name', 'usuario__first_name', 'pk')) if elegida else []
    for inscrito in inscritos:
        inscrito.seguimiento = seguimiento_de(inscrito, modulos)
        inscrito.avance = inscrito.seguimiento['avance']
        inscrito.notas = [{**fila, 'detalle': (f"{fila['usados']} de {fila['limite']} intentos" if fila['usados'] is not None
                                              else fila['rotulo'])} for fila in inscrito.seguimiento['calificadas']]
    q = request.GET.get('q', '').strip()[:200]
    estado = request.GET.get('estado', '')
    intentos = request.GET.get('intentos', '')
    totales = {clave: sum(inscrito.seguimiento['estado'] == clave for inscrito in inscritos)
               for clave in ('aprobado', 'reprobado', 'pendiente')}
    if q:
        inscritos = [inscrito for inscrito in inscritos if q.casefold() in ' '.join((
            inscrito.seguimiento['nombre'], inscrito.seguimiento['documento'],
            inscrito.usuario.username, inscrito.usuario.email)).casefold()]
    if estado in totales:
        inscritos = [inscrito for inscrito in inscritos if inscrito.seguimiento['estado'] == estado]
    if intentos == 'agotados':
        inscritos = [inscrito for inscrito in inscritos if inscrito.seguimiento['tiene_agotadas']]
    elif intentos == 'realizados':
        inscritos = [inscrito for inscrito in inscritos if inscrito.seguimiento['intentos_usados'] > 0]
    elif intentos == 'sin_rendir':
        inscritos = [inscrito for inscrito in inscritos if inscrito.seguimiento['intentos_usados'] == 0]
    por_revisar = [fila['entrega'] for inscrito in inscritos for fila in inscrito.seguimiento['calificadas']
                   if fila['leccion'].tipo == 'deber' and fila.get('entrega') and fila['entrega'].estado == 'entregada']
    if request.GET.get('formato') == 'csv':
        from apps.gestion_unidades.presentation.seguimiento_reportes import csv_del_libro
        return csv_del_libro(curso, elegida, inscritos)
    parametros_csv = request.GET.copy()
    parametros_csv['formato'] = 'csv'
    if elegida:
        parametros_csv['edicion'] = str(elegida.pk)
    return render(request, 'portal/pages/unidades/aula/curso_calificaciones.html', {
        'unidad': unidad, 'curso': curso, 'ediciones_curso': ediciones, 'elegida': elegida, 'inscritos': inscritos,
        'calificadas': calificadas, 'por_revisar': sorted(por_revisar, key=lambda entrega: entrega.entregada_en),
        'totales': totales, 'filtros': {'q': q, 'estado': estado, 'intentos': intentos},
        'error_calificacion': error_calificacion,
        'csv_url': '?' + parametros_csv.urlencode(),
        'curso_url': reverse('curso_unidad', args=[unidad.slug, curso.codigo]),
        'inscritos_url': reverse('inscritos_curso', args=[unidad.slug, curso.codigo]),
    })


@transaction.atomic
def _calificar(request, curso, edicion=None):
    consulta = EntregaDeber.objects.select_related('leccion', 'inscripcion').filter(
        leccion__modulo__curso=curso, inscripcion__edicion__curso=curso)
    if edicion is not None:
        consulta = consulta.filter(inscripcion__edicion=edicion)
    identificador = request.POST.get('entrega', '')
    entrega = get_object_or_404(consulta, pk=id_solicitado(identificador))
    type(entrega.inscripcion).objects.select_for_update().get(pk=entrega.inscripcion_id)
    # Releer tras obtener el bloqueo: puede haber terminado otra calificación.
    entrega = consulta.get(pk=entrega.pk)
    if entrega.estado == 'aprobada' and entrega.inscripcion.certificados.filter(anulado=False).exists():
        return ('Esta entrega sustenta un certificado vigente. Revise y anule explícitamente el certificado '
                'antes de cambiar la calificación; el sistema no lo anula automáticamente.')
    retroalimentacion = request.POST.get('retroalimentacion', '')[:4000]
    if request.POST.get('accion') == 'devolver':
        entrega.estado, entrega.nota = 'devuelta', None
    else:
        try:
            if 'nota_sobre_10' in request.POST:
                # El formulario actual expresa explícitamente su escala. Nunca
                # interprete una entrada inválida como nota antigua sobre cien.
                nota = nota_desde_diez(request.POST.get('nota_sobre_10'))
            else:
                # Compatibilidad con clientes anteriores: nota sigue siendo 0–100.
                texto = request.POST.get('nota', '').strip().replace(',', '.')
                if len(texto) > 32:
                    raise ValidationError('Escriba una nota válida.')
                nota = Decimal(texto)
                if not nota.is_finite() or not 0 <= nota <= 100:
                    raise ValidationError('Escriba una nota válida.')
                nota = nota.quantize(Decimal('0.01'))
        except (ArithmeticError, ValidationError, ValueError, TypeError):
            return 'Escriba una nota entre 0 y 10, con hasta tres decimales.'
        entrega.nota = nota
        entrega.estado = 'aprobada' if nota >= entrega.leccion.nota_minima else 'devuelta'
    entrega.retroalimentacion = retroalimentacion
    entrega.calificada_por, entrega.calificada_en = request.user, timezone.now()
    entrega.save()
    if entrega.estado == 'aprobada':
        completar(entrega.inscripcion, entrega.leccion, request.user)
    else:
        ProgresoLeccion.objects.filter(inscripcion=entrega.inscripcion, leccion=entrega.leccion).delete()
    return None
