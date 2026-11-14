"""El aula de cada curso: inscripción, módulos y lecciones, progreso de cada persona y gestión de los inscritos.

Cada curso decide cómo se inscribe la gente: abierta (entra al momento, hasta llenar el cupo) o con aprobación de la
unidad. Quien está inscrito recorre los módulos en el aula del curso, con el contenido a la izquierda y el programa
con su avance a la derecha; marca como completadas las lecturas, videos y materiales, y la unidad registra la
asistencia a las clases en vivo. Los materiales se entregan desde el aula, solo a quien tiene acceso.
"""
import mimetypes
from pathlib import Path

from apps.core.identificadores import id_solicitado

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ProgresoLeccion
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.directorio_unidades.models.core import Unidad

from apps.formacion.presentation.cursos import puede_crear_cursos
from apps.formacion.presentation.matriculas_cursos import cupos_disponibles, edicion_solicitada, url_con_edicion
from apps.gestion_unidades.presentation.edicion_registro import ediciones_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad

ICONOS_DE_LECCION = {
    'texto': 'fas fa-book-open',
    'video': 'fas fa-play-circle',
    'material': 'fas fa-file-download',
    'en_vivo': 'fas fa-video',
    'evaluacion': 'fas fa-clipboard-check',
    'deber': 'fas fa-tasks',
}
# Lo que el navegador muestra dentro del aula; lo demás se descarga.
EN_LINEA = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp3', '.mp4', '.webm', '.txt'}


def _curso(slug, codigo, usuario):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    curso = get_object_or_404(Curso.objects.prefetch_related('ediciones'), unidad=unidad, codigo=codigo)
    if curso.es_externo:
        raise Http404('Esta actividad se realiza en la plataforma de la institución organizadora.')
    if not curso.publicado and not puede_gestionar_unidad(usuario, unidad):
        raise Http404('El curso no está publicado.')
    if not curso.activo and not puede_gestionar_unidad(usuario, unidad):
        propia = inscripcion_de(curso, usuario)
        if propia is None or propia.estado != 'aceptada':
            raise Http404('Esta actividad está desactivada.')
    return unidad, curso


def inscripcion_de(curso, usuario, edicion=None):
    """Inscripción de un grupo explícito, o la última aceptada para enlaces anteriores."""
    if usuario is None or not usuario.is_authenticated:
        return None
    propias = InscripcionCurso.objects.filter(edicion__curso=curso, usuario=usuario).select_related('edicion')
    if edicion is not None:
        if edicion.curso_id != curso.pk:
            raise Http404('El grupo no pertenece a este curso.')
        return propias.filter(edicion=edicion).exclude(estado='retirada').first()
    aceptada = propias.filter(estado='aceptada').order_by('-fecha_inscripcion').first()
    if aceptada is not None:
        return aceptada
    vigente = curso.edicion_vigente()
    return propias.filter(edicion=vigente, estado__in=('pendiente', 'rechazada')).first() if vigente else None


def cupos_libres(edicion):
    """Cupo menos inscritos aceptados e invitaciones activas que reservan una plaza."""
    return cupos_disponibles(edicion)


def puede_inscribirse(curso, edicion, usuario):
    if curso.es_externo or not curso.activo:
        return False, 'Esta actividad no admite matrículas en esta plataforma.'
    if edicion is None or edicion.curso_id != curso.pk or edicion.estado()[0] != 'inscripciones':
        return False, 'Las inscripciones de este grupo no están abiertas.'
    if inscripcion_de(curso, usuario, edicion):
        return False, 'Ya tienes una inscripción en este grupo.'
    if cupos_libres(edicion) == 0:
        return False, 'Los cupos de este grupo se agotaron.'
    return True, ''


def lecciones_de(curso, gestor=False):
    """Los módulos con sus lecciones en orden; los inscritos solo ven las publicadas."""
    modulos = list(curso.modulos.prefetch_related('lecciones'))
    for modulo in modulos:
        modulo.visibles = [leccion for leccion in modulo.lecciones.all() if leccion.publicada or gestor]
        for leccion in modulo.visibles:
            leccion.icono = ICONOS_DE_LECCION[leccion.tipo]
    return modulos


def marcar_avance(modulos, hechas, vista_previa=False):
    """Marca en cada módulo cuánto lleva la persona y, en cada evaluación, si ya puede rendirla.

    Una evaluación se habilita cuando están completas todas las lecciones obligatorias anteriores del curso:
    la de cada módulo, al terminar ese módulo; la final, al aprobar todo lo demás. La vista previa no bloquea.
    """
    pendientes = []
    for modulo in modulos:
        obligatorias = [leccion for leccion in modulo.visibles if leccion.obligatoria and leccion.publicada]
        modulo.total_obligatorias = len(obligatorias)
        modulo.hechas = sum(1 for leccion in obligatorias if leccion.pk in hechas)
        modulo.completo = modulo.hechas == modulo.total_obligatorias
        for leccion in modulo.visibles:
            leccion.pendientes = list(pendientes) if leccion.tipo == 'evaluacion' and not vista_previa else []
            leccion.bloqueada = bool(leccion.pendientes)
            if leccion.obligatoria and leccion.publicada and leccion.pk not in hechas:
                pendientes.append(leccion)
    return modulos


def certificado_de(inscripcion):
    """El certificado vigente de la inscripción, o None si no tiene o se anuló."""
    if inscripcion is None:
        return None
    return CertificadoCurso.objects.filter(inscripcion=inscripcion, anulado=False).first()


def completar(inscripcion, leccion, registrada_por=None):
    """Marca la lección como completada y, si con ella se cumplió todo, emite el certificado."""
    from apps.formacion.presentation.certificados_cursos import emitir_si_corresponde
    with transaction.atomic():
        inscripcion = InscripcionCurso.objects.select_for_update().get(pk=inscripcion.pk)
        ProgresoLeccion(inscripcion=inscripcion, leccion=leccion).clean()
        ProgresoLeccion.objects.get_or_create(inscripcion=inscripcion, leccion=leccion,
                                              defaults={'registrada_por': registrada_por})
        return emitir_si_corresponde(inscripcion)


def avance(curso, inscripcion, modulos=None, hechas=None):
    """Cuántas lecciones obligatorias publicadas completó la persona y qué porcentaje es (en la vista previa, con lo
    que quien gestiona marcó en su sesión)."""
    modulos = modulos if modulos is not None else lecciones_de(curso)
    obligatorias = [leccion.pk for modulo in modulos for leccion in modulo.visibles if leccion.publicada and leccion.obligatoria]
    if hechas is None:
        if inscripcion is not None and 'progresos' in getattr(inscripcion, '_prefetched_objects_cache', {}):
            hechas = {progreso.leccion_id for progreso in inscripcion.progresos.all()}
        else:
            hechas = set(inscripcion.progresos.values_list('leccion_id', flat=True)) if inscripcion else set()
    completadas = sum(1 for pk in obligatorias if pk in hechas)
    return {'hechas': hechas, 'completadas': completadas, 'total': len(obligatorias),
            'porcentaje': round(100 * completadas / len(obligatorias)) if obligatorias else 0}


def estado_para(curso, usuario, unidad, edicion=None):
    """Acciones del curso conservando el grupo elegido y la identidad propia."""
    from apps.formacion.presentation.inscripciones_cursos import aplicar_invitaciones, es_pagado
    from apps.formacion.presentation.matriculas_forms import InscripcionGrupoForm
    aplicar_invitaciones(usuario)
    vigente = edicion or curso.edicion_vigente()
    inscripcion = inscripcion_de(curso, usuario, edicion)
    if edicion is None and inscripcion is not None:
        vigente = inscripcion.edicion
    disponibles = []
    for grupo in curso.ediciones.filter(activa=True):
        if grupo.estado()[0] == 'inscripciones':
            grupo.cupos_disponibles = cupos_libres(grupo)
            disponibles.append(grupo)
    inicial = {}
    if usuario.is_authenticated:
        inicial['nombres_completos'] = usuario.get_full_name()
        inicial['documento'] = getattr(getattr(usuario, 'profile', None), 'cedula', '')
    if edicion is not None:
        inicial['edicion'] = edicion.pk
    base = {'edicion': vigente, 'edicion_seleccionada': edicion,
            'ediciones_disponibles': disponibles,
            'formulario_inscripcion': InscripcionGrupoForm(curso=curso, initial=inicial)}
    pagar = url_con_edicion(reverse('pagar_curso', args=[unidad.slug, curso.codigo]), edicion)
    gestor = puede_gestionar_unidad(usuario, unidad)
    aula = url_con_edicion(reverse('aula_curso', args=[unidad.slug, curso.codigo]), vigente)
    if inscripcion and inscripcion.estado == 'aceptada':
        return {**base, 'accion': 'aula', 'url': aula, 'inscripcion': inscripcion,
                'progreso': avance(curso, inscripcion), 'certificado': certificado_de(inscripcion)}
    if not curso.activo or curso.es_externo:
        return {**base, 'accion': 'cerrada', 'motivo': 'La oferta está desactivada.',
                'vista_previa': aula if gestor else ''}
    pago = getattr(inscripcion, 'pago', None) if inscripcion else None
    if inscripcion and inscripcion.estado == 'pendiente':
        return {**base, 'accion': 'revision', 'inscripcion': inscripcion, 'pago': pago}
    if inscripcion and inscripcion.estado == 'rechazada':
        if pago is not None and pago.estado == 'rechazado':
            return {**base, 'accion': 'reenviar', 'inscripcion': inscripcion, 'pago': pago,
                    'url': url_con_edicion(pagar, inscripcion.edicion)}
        return {**base, 'accion': 'rechazada', 'inscripcion': inscripcion}
    pagina = url_con_edicion(reverse('curso_unidad', args=[unidad.slug, curso.codigo]), edicion)
    if not usuario.is_authenticated:
        from urllib.parse import urlencode
        return {**base, 'accion': 'identificarse' if disponibles else 'cerrada',
                'url': reverse('login') + '?' + urlencode({'next': pagina})}
    permitido, motivo = puede_inscribirse(curso, vigente, usuario)
    if edicion is None:
        permitido = any(grupo.cupos_disponibles is None or grupo.cupos_disponibles > 0 for grupo in disponibles)
    return {**base, 'accion': 'inscribirse' if permitido else 'cerrada', 'motivo': motivo,
            'cupos': cupos_libres(vigente) if vigente else None,
            'url': pagar if es_pagado(curso) else reverse('inscribirse_curso', args=[unidad.slug, curso.codigo]),
            'pagado': es_pagado(curso), 'vista_previa': aula if gestor else ''}


@login_required
@require_POST
def inscribirse_view(request, slug, codigo):
    from apps.formacion.presentation.inscripciones_cursos import es_pagado
    from apps.formacion.presentation.matriculas_cursos import guardar_datos_matricula
    from apps.formacion.presentation.matriculas_forms import InscripcionGrupoForm
    unidad, curso = _curso(slug, codigo, request.user)
    elegida = edicion_solicitada(curso, request)
    destino = url_con_edicion(reverse('curso_unidad', args=[unidad.slug, curso.codigo]) + '#inscripcion', elegida)
    if es_pagado(curso):
        return redirect(url_con_edicion(reverse('pagar_curso', args=[unidad.slug, curso.codigo]), elegida))
    formulario = InscripcionGrupoForm(request.POST, curso=curso)
    if formulario.is_valid():
        elegida = formulario.cleaned_data['edicion']
        destino = url_con_edicion(destino, elegida)
        try:
            with transaction.atomic():
                curso = get_object_or_404(Curso.objects.select_for_update(), pk=curso.pk, unidad=unidad)
                elegida = EdicionCurso.objects.select_for_update().get(pk=elegida.pk)
                permitido, motivo = puede_inscribirse(curso, elegida, request.user)
                if not permitido:
                    previa = inscripcion_de(curso, request.user, elegida)
                    if previa is not None:
                        return redirect(destino)
                    raise ValidationError(motivo)
                inscripcion = (InscripcionCurso.objects.filter(edicion=elegida, usuario=request.user, estado='retirada').first()
                               or InscripcionCurso(edicion=elegida, usuario=request.user))
                abierta = curso.inscripcion == 'abierta'
                inscripcion.estado = 'aceptada' if abierta else 'pendiente'
                inscripcion.fecha_respuesta = timezone.now() if abierta else None
                inscripcion.save()
                guardar_datos_matricula(inscripcion, formulario.cleaned_data['nombres_completos'],
                                       formulario.cleaned_data['documento'])
            return redirect(destino)
        except ValidationError as error:
            formulario.add_error(None, error.messages)
        except IntegrityError:
            formulario.add_error(None, 'Otra operación registró esta matrícula. Revisa el grupo y tus datos antes de repetir.')
    return render(request, 'portal/pages/unidades/aula/curso_inscripcion_grupo.html', {
        'unidad': unidad, 'curso': curso, 'formulario': formulario, 'curso_url': destino})


TIPOS_LIBRES = ('texto', 'video', 'material')


def modo_del_aula(request, unidad, curso):
    """(modo, inscripción): «inscrito» para quien está aceptado, «previa» para quien gestiona la unidad y «libre»
    para los demás, que recorren gratis la primera unidad."""
    inscripcion = inscripcion_de(curso, request.user, edicion_solicitada(curso, request))
    if inscripcion and inscripcion.estado == 'aceptada':
        return 'inscrito', inscripcion
    if puede_gestionar_unidad(request.user, unidad):
        return 'previa', None
    return 'libre', None


def lecciones_libres(modulos):
    """La primera unidad, abierta a todos: sus lecturas, videos y materiales publicados. Lo demás, con candado."""
    primera = next((modulo for modulo in modulos if modulo.visibles), None)
    return {leccion.pk for leccion in primera.visibles if leccion.publicada and leccion.tipo in TIPOS_LIBRES} if primera else set()


def _clave_previa(curso):
    return f'vista_previa_curso_{curso.pk}'


def hechas_en_vista_previa(request, curso):
    """Lo que quien gestiona marcó como visto al probar el curso: vive en su sesión, sin crear inscripciones."""
    return set(request.session.get(_clave_previa(curso), []))


def _acceso_al_aula(request, unidad, curso):
    """(inscripción, es vista previa): entra quien está inscrito y aceptado, o quien gestiona la unidad."""
    inscripcion = inscripcion_de(curso, request.user, edicion_solicitada(curso, request))
    if inscripcion and inscripcion.estado == 'aceptada':
        return inscripcion, False
    if puede_gestionar_unidad(request.user, unidad):
        return None, True
    raise PermissionDenied('El aula es para quienes están inscritos en el curso.')


@xframe_options_sameorigin
def aula_view(request, slug, codigo, leccion_id=None):
    """El aula del curso: la lección abierta a la izquierda y el programa con el avance a la derecha. Quien no está
    inscrito recorre gratis la primera unidad y ve el resto con candado."""
    from apps.formacion.presentation.calificaciones_cursos import contexto_calificada
    from apps.formacion.presentation.comentarios_cursos import contexto_comentarios
    unidad, curso = _curso(slug, codigo, request.user)
    modo, inscripcion = modo_del_aula(request, unidad, curso)
    vista_previa, libre = modo == 'previa', modo == 'libre'
    if vista_previa and request.GET.get('reiniciar') == '1':
        request.session.pop(_clave_previa(curso), None)
        return redirect(url_con_edicion(request.path, edicion_solicitada(curso, request)))
    modulos = lecciones_de(curso, gestor=vista_previa)
    progreso = avance(curso, inscripcion, modulos, hechas_en_vista_previa(request, curso) if vista_previa else None)
    marcar_avance(modulos, progreso['hechas'], vista_previa)
    libres = lecciones_libres(modulos) if libre else None
    for modulo in modulos:
        for leccion in modulo.visibles:
            leccion.cerrada = libres is not None and leccion.pk not in libres
    recorrido = [leccion for modulo in modulos for leccion in modulo.visibles]
    if leccion_id is None:
        # Se retoma en la primera lección pendiente.
        actual = next((leccion for leccion in recorrido if leccion.pk not in progreso['hechas']), recorrido[0] if recorrido else None)
    else:
        actual = next((leccion for leccion in recorrido if leccion.pk == leccion_id), None)
        if actual is None:
            raise Http404('La lección no existe en este curso.')
    elegida = inscripcion.edicion if inscripcion else edicion_solicitada(curso, request)
    if actual is not None and actual.tipo == 'en_vivo' and actual.sala == 'plataforma':
        from apps.formacion.presentation.clases_en_vivo import grabacion_del_grupo
        for campo, valor in grabacion_del_grupo(actual, elegida).items():
            setattr(actual, campo, valor)
    posicion = recorrido.index(actual) if actual else -1
    cerrada = actual is not None and actual.cerrada
    return render(request, 'portal/pages/unidades/aula/curso_aula.html', {
        'unidad': unidad, 'curso': curso, 'modulos': modulos, 'actual': actual, 'progreso': progreso,
        'inscripcion': inscripcion, 'vista_previa': vista_previa, 'libre': libre, 'cerrada': cerrada,
        'editor_curso_url': reverse('editor_curso', args=[unidad.slug, curso.codigo]) if puede_crear_cursos(request.user, unidad) else '',
        'dominio': request.get_host().split(':')[0],
        'participar': estado_para(curso, request.user, unidad, edicion=edicion_solicitada(curso, request)) if libre else None,
        'edicion_seleccionada': inscripcion.edicion if inscripcion else edicion_solicitada(curso, request),
        'edicion_query': '?edicion=' + str(inscripcion.edicion_id) if inscripcion else ('?edicion=' + str(edicion_solicitada(curso, request).pk) if edicion_solicitada(curso, request) else ''),
        'anterior': recorrido[posicion - 1] if posicion > 0 else None,
        'siguiente': recorrido[posicion + 1] if 0 <= posicion < len(recorrido) - 1 else None,
        'completada': actual is not None and actual.pk in progreso['hechas'],
        'ediciones': ediciones_de(request.user, unidad),
        'curso_url': url_con_edicion(reverse('curso_unidad', args=[unidad.slug, curso.codigo]), inscripcion.edicion if inscripcion else edicion_solicitada(curso, request)),
        'certificado': certificado_de(inscripcion),
        'modulo_actual': next((modulo for modulo in modulos if actual in modulo.visibles), None),
        # Las lecturas, videos y materiales se marcan como vistos solos al cumplirlos.
        'automatico': (actual is not None and not libre and actual.tipo in TIPOS_LIBRES
                       and actual.pk not in progreso['hechas']),
        'posicion': posicion + 1, 'total_lecciones': len(recorrido),
        **(contexto_comentarios(actual, request.user, unidad, vista_previa, request.GET.get('orden', 'votos'))
           if not libre else {}),
        **(contexto_calificada(actual, inscripcion, vista_previa, getattr(request, 'entrega_con_errores', None))
           if not libre else {}),
    })


@login_required
@require_POST
def completar_leccion_view(request, slug, codigo, leccion_id):
    """El inscrito marca como completada una lectura, un video o un material; la clase en vivo la registra la unidad
    y las evaluaciones y deberes se completan al aprobarlos. En la vista previa, quien gestiona prueba el avance en
    su sesión."""
    unidad, curso = _curso(slug, codigo, request.user)
    modo, inscripcion = modo_del_aula(request, unidad, curso)
    if modo == 'libre':
        raise PermissionDenied('Inscríbete en el curso para guardar tu avance.')
    vista_previa = modo == 'previa'
    leccion = get_object_or_404(LeccionCurso, pk=leccion_id, modulo__curso=curso,
                                **({} if vista_previa else {'publicada': True}))
    certificado = None
    if vista_previa and not leccion.en_vivo and not leccion.calificada:
        request.session[_clave_previa(curso)] = sorted(hechas_en_vista_previa(request, curso) | {leccion.pk})
    if not vista_previa and not leccion.en_vivo and not leccion.calificada:
        tenia = CertificadoCurso.objects.filter(inscripcion=inscripcion, anulado=False).exists()
        emitido = completar(inscripcion, leccion)
        # Solo un certificado recién emitido recarga la página para mostrarlo.
        certificado = None if tenia else emitido
    if request.headers.get('X-Requested-With') == 'fetch':
        # Marcada como vista desde el aula sin recargar: el avance del curso y de su unidad para ponerlos al día.
        if leccion.en_vivo or leccion.calificada:
            return JsonResponse({'ok': False})
        modulos = lecciones_de(curso, gestor=vista_previa)
        progreso = avance(curso, inscripcion, modulos, hechas_en_vista_previa(request, curso) if vista_previa else None)
        marcar_avance(modulos, progreso['hechas'], vista_previa)
        modulo = next(modulo for modulo in modulos if modulo.pk == leccion.modulo_id)
        return JsonResponse({
            'ok': True, 'porcentaje': progreso['porcentaje'], 'completadas': progreso['completadas'],
            'total': progreso['total'], 'certificado': bool(certificado),
            'modulo': {'id': modulo.pk, 'hechas': modulo.hechas, 'total': modulo.total_obligatorias,
                       'completo': modulo.completo},
        })
    siguiente = request.POST.get('siguiente', '')
    destino = reverse('aula_curso_leccion', args=[unidad.slug, curso.codigo, int(siguiente)]) if siguiente.isdigit() \
        else reverse('aula_curso_leccion', args=[unidad.slug, curso.codigo, leccion.pk])
    return redirect(url_con_edicion(destino, inscripcion.edicion if inscripcion else edicion_solicitada(curso, request)))


def material_view(request, slug, codigo, leccion_id):
    """El archivo de una lección, para quien está inscrito o gestiona la unidad; los de la primera unidad, para todos.
    Se muestra en línea si el navegador puede."""
    unidad, curso = _curso(slug, codigo, request.user)
    modo, _inscripcion = modo_del_aula(request, unidad, curso)
    leccion = get_object_or_404(LeccionCurso, pk=leccion_id, modulo__curso=curso)
    if not leccion.archivo or (not leccion.publicada and modo != 'previa'):
        raise Http404()
    if modo == 'libre' and leccion.pk not in lecciones_libres(lecciones_de(curso)):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        raise PermissionDenied('Este material es para quienes están inscritos en el curso.')
    return archivo_protegido(leccion.archivo, request=request if leccion.tipo == 'video' else None)


def archivo_protegido(archivo, request=None):
    """Un archivo privado del curso: en línea si el navegador puede mostrarlo, sin ejecutar nada en el origen."""
    extension = Path(archivo.name).suffix.lower()
    tipo, _ = mimetypes.guess_type(archivo.name)
    if request is not None and extension in {'.mp4', '.webm'}:
        from apps.formacion.presentation.video_protegido import respuesta_video_con_rango
        respuesta = respuesta_video_con_rango(archivo, request, nombre=Path(archivo.name).name,
                                              tipo=tipo or 'application/octet-stream')
    else:
        respuesta = FileResponse(archivo.open('rb'), as_attachment=extension not in EN_LINEA,
                                 filename=Path(archivo.name).name, content_type=tipo or 'application/octet-stream')
    respuesta['X-Frame-Options'] = 'SAMEORIGIN'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Content-Security-Policy'] = "sandbox; default-src 'none'; img-src 'self'; media-src 'self'"
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
@never_cache
@xframe_options_sameorigin
def inscritos_view(request, slug, codigo):
    """Quien gestiona los cursos acepta inscripciones, verifica pagos, matricula, registra la asistencia a las clases
    en vivo y ve el avance."""
    from apps.formacion.presentation.inscripciones_cursos import atender_gestion, es_pagado
    from apps.formacion.presentation.matriculas_forms import ListaMatriculaForm, MatriculaIndividualForm
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    curso = get_object_or_404(Curso, unidad=unidad, codigo=codigo)
    if not puede_crear_cursos(request.user, unidad):
        # Un curso sin publicar no revela que existe a quien no lo gestiona.
        if not curso.publicado:
            raise Http404('El curso no está publicado.')
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad ve a sus inscritos.')
    seleccionada = edicion_solicitada(curso, request)
    if request.method == 'POST':
        mensaje = atender_gestion(request, curso)
        if mensaje is None:
            _atender(request, curso, edicion=seleccionada)
        elif mensaje:
            request.session['mensaje_inscritos'] = mensaje
        return redirect(url_con_edicion(request.get_full_path(), seleccionada))
    ediciones = list(curso.ediciones.all())
    elegida = seleccionada or curso.edicion_vigente() or (ediciones[0] if ediciones else None)
    modulos = lecciones_de(curso)
    en_vivo = [leccion for modulo in modulos for leccion in modulo.visibles if leccion.en_vivo and leccion.publicada]
    inscritos = list(elegida.inscripciones.select_related('usuario', 'usuario__profile', 'pago').prefetch_related('progresos', 'intentos', 'entregas', 'certificados')
                     .order_by('estado', 'usuario__last_name', 'usuario__first_name')) if elegida else []
    from apps.formacion.presentation.seguimiento_cursos import seguimiento_de
    resumen = {'matriculados': len(inscritos), 'aprobados': 0, 'certificados': 0, 'por_revisar': 0}
    for inscrito in inscritos:
        # El seguimiento usa las relaciones precargadas y no modifica la matrícula.
        # Consultar la cohorte nunca genera certificados: esa operación es explícita.
        inscrito.seguimiento = seguimiento_de(inscrito, modulos)
        inscrito.avance = inscrito.seguimiento['avance']
        inscrito.asistencias = [(leccion, leccion.pk in inscrito.avance['hechas']) for leccion in en_vivo]
        inscrito.certificado_emitido = (inscrito.seguimiento['certificado']
                                       or next(iter(inscrito.certificados.all()), None))
        resumen['aprobados'] += int(inscrito.seguimiento['estado'] == 'aprobado')
        resumen['certificados'] += int(inscrito.seguimiento['certificado_estado'] == 'emitido')
        resumen['por_revisar'] += sum(1 for entrega in inscrito.entregas.all() if entrega.estado == 'entregada')
    participantes_evento = list(elegida.participantes_evento.prefetch_related('certificados')) if elegida else []
    for participante in participantes_evento:
        certificados = list(participante.certificados.all())
        participante.certificado_emitido = certificados[0] if certificados else None
        resumen['certificados'] += int(any(not c.anulado for c in certificados))
    filtro_estado = request.GET.get('estado', '')
    filtro_certificado = request.GET.get('certificado', '')
    busqueda = request.GET.get('q', '').strip()[:200]
    if filtro_estado in ('aprobado', 'reprobado', 'pendiente'):
        inscritos = [i for i in inscritos if i.seguimiento['estado'] == filtro_estado]
    if filtro_certificado in ('emitido', 'anulado', 'pendiente', 'listo', 'no_ofrece'):
        inscritos = [i for i in inscritos if i.seguimiento['certificado_estado'] == filtro_certificado]
    if busqueda:
        termino = busqueda.casefold()
        inscritos = [i for i in inscritos if termino in ' '.join((i.seguimiento['nombre'], i.usuario.email, i.documento)).casefold()]
    return render(request, 'portal/pages/unidades/aula/curso_inscritos.html', {
        'unidad': unidad, 'curso': curso, 'ediciones_curso': ediciones, 'elegida': elegida, 'inscritos': inscritos,
        'participantes_evento': participantes_evento,
        'en_vivo': en_vivo, 'cupos': cupos_libres(elegida) if elegida else None,
        'resumen_grupo': resumen, 'filtro_estado': filtro_estado, 'filtro_certificado': filtro_certificado, 'busqueda': busqueda,
        'diseno_certificado_url': reverse('editar_certificado_curso', args=[unidad.slug, curso.codigo]),
        'curso_url': reverse('curso_unidad', args=[unidad.slug, curso.codigo]),
        # Gestión de la inscripción: pagos por verificar, matrícula, códigos de descuento e invitaciones por correo.
        'pagado': es_pagado(curso), 'mensaje': request.session.pop('mensaje_inscritos', ''),
        'pagos_pendientes': [inscrito.pago for inscrito in inscritos
                             if getattr(inscrito, 'pago', None) is not None and inscrito.pago.estado == 'pendiente'],
        'codigos': list(curso.codigos_descuento.all()),
        'grupos_url': reverse('grupos_curso', args=[unidad.slug, curso.codigo]),
        'matricula_individual_form': MatriculaIndividualForm(curso=curso, initial={'edicion': elegida.pk if elegida else None}, auto_id='individual_%s'),
        'matricula_lista_form': ListaMatriculaForm(curso=curso, initial={'edicion': elegida.pk if elegida else None}, auto_id='lista_%s'),
        'invitaciones': list(InvitacionCurso.objects.filter(edicion=elegida, activa=True, inscripcion__isnull=True)
                             .select_related('edicion')),
        'ediciones': ediciones_de(request.user, unidad),
    })


def _atender(request, curso, *, edicion=None):
    accion = request.POST.get('accion')
    criterios = {'pk': id_solicitado(request.POST.get('inscripcion')), 'edicion__curso': curso}
    if accion == 'emitir_certificado_academico' and edicion is not None:
        criterios['edicion'] = edicion
    inscripcion = get_object_or_404(InscripcionCurso, **criterios)
    if accion in ('aceptar', 'rechazar', 'retirar'):
        with transaction.atomic():
            edicion = EdicionCurso.objects.select_for_update().get(pk=inscripcion.edicion_id)
            inscripcion = InscripcionCurso.objects.select_for_update().get(pk=inscripcion.pk)
            if accion == 'aceptar' and inscripcion.estado != 'aceptada' and cupos_libres(edicion) == 0:
                request.session['mensaje_inscritos'] = 'No quedan cupos en este grupo; no se aceptó la inscripción.'
                return
            inscripcion.estado = {'aceptar': 'aceptada', 'rechazar': 'rechazada', 'retirar': 'retirada'}[accion]
            inscripcion.fecha_respuesta = timezone.now()
            inscripcion.observacion = request.POST.get('observacion', '')[:300]
            inscripcion.save(update_fields=['estado', 'fecha_respuesta', 'observacion'])
        messages.success(request, 'Estado de la inscripción actualizado.')
    elif accion == 'asistencia' and inscripcion.estado == 'aceptada':
        leccion = get_object_or_404(LeccionCurso, pk=id_solicitado(request.POST.get('leccion')), modulo__curso=curso, tipo='en_vivo')
        if request.POST.get('asistio') == '1':
            completar(inscripcion, leccion, request.user)
        else:
            ProgresoLeccion.objects.filter(inscripcion=inscripcion, leccion=leccion).delete()
        messages.success(request, 'Asistencia actualizada.')
    elif accion == 'emitir_certificado_academico':
        from apps.formacion.presentation.certificados_cursos import emitir_si_corresponde
        certificado = emitir_si_corresponde(inscripcion)
        if certificado is not None:
            messages.success(request, 'Certificado académico disponible.')
        else:
            messages.warning(request, 'No se emitió el certificado: revise los requisitos académicos, '
                             'los datos de la actividad y si existe una anulación previa.')


def mis_inscripciones(unidad, usuario):
    if usuario is None or not usuario.is_authenticated:
        return InscripcionCurso.objects.none()
    return (InscripcionCurso.objects.filter(usuario=usuario, edicion__curso__unidad=unidad).exclude(estado='retirada')
            .select_related('edicion__curso').order_by('-fecha_inscripcion'))


@login_required
@xframe_options_sameorigin
def mis_cursos_view(request, slug):
    """Los cursos de la persona en la unidad, con su estado y su avance, para retomarlos donde los dejó."""
    from apps.formacion.presentation.inscripciones_cursos import aplicar_invitaciones
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    aplicar_invitaciones(request.user)
    filas = []
    for inscripcion in mis_inscripciones(unidad, request.user):
        curso = inscripcion.edicion.curso
        filas.append({'inscripcion': inscripcion, 'curso': curso,
                      'progreso': avance(curso, inscripcion) if inscripcion.estado == 'aceptada' else None,
                      'certificado': certificado_de(inscripcion),
                      'aula': url_con_edicion(reverse('aula_curso', args=[unidad.slug, curso.codigo]), inscripcion.edicion),
                      'pagina': url_con_edicion(reverse('curso_unidad', args=[unidad.slug, curso.codigo]), inscripcion.edicion)})
    return render(request, 'portal/pages/unidades/aula/mis_cursos.html', {
        'unidad': unidad, 'filas': filas, 'ediciones': ediciones_de(request.user, unidad),
        'todos_url': reverse('cursos_unidad', args=[unidad.slug])})
