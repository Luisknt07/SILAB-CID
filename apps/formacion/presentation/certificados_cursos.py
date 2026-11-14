"""Certificados de cursos y eventos con identidad, actividad y diseño congelados.

La aprobación respeta los requisitos académicos. Las acreditaciones de asistencia o
funciones en eventos requieren autorización y motivo. El código y el QR permiten
consultar el estado vigente; las emisiones anteriores conservan su PDF original.
"""
import secrets
from decimal import Decimal
import hashlib
import json
import re

from django.core import signing

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.core.identificadores import id_solicitado

from apps.formacion.models.cursos import CertificadoCurso, InscripcionCurso, Curso, ParticipanteEvento
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.formacion.models.cursos_certificacion import CATEGORIAS_EVENTO, IMAGENES_CERTIFICADO, TIPOS_CERTIFICADO

LETRAS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # Sin 0/O ni 1/I, que se confunden al copiarlo a mano.


def nuevo_codigo():
    while True:
        cuerpo = ''.join(secrets.choice(LETRAS) for _ in range(8))
        codigo = f'CERT-{cuerpo[:4]}-{cuerpo[4:]}'
        if not CertificadoCurso.objects.filter(codigo=codigo).exists():
            return codigo


def direccion_de_verificacion(certificado):
    """Con el dominio oficial, para que el QR impreso funcione desde cualquier celular."""
    congelada = (getattr(certificado, 'diseno_certificado', None) or {}).get('verificacion_url')
    return congelada or settings.SITE_URL.rstrip('/') + reverse('verificar_certificado', args=[certificado.codigo])


def _verificacion_local():
    from urllib.parse import urlsplit
    host = urlsplit(settings.SITE_URL).hostname or ''
    return (host.lower() in {'localhost', '127.0.0.1', '0.0.0.0', '::1', 'testserver'}
            or host.lower().endswith('.localhost') or not host)


def firmante_de(curso):
    """(nombre, cargo) de quien firma: lo que diga el curso o, si no, la coordinación de la unidad."""
    cargo = curso.firma_cargo or f'Coordinación de {curso.unidad.nombre}'
    if curso.firma_nombre:
        return curso.firma_nombre, cargo
    coordinacion = curso.unidad.responsables_unidad.filter(rol='coordinacion').select_related('usuario').first()
    if coordinacion is None:
        return '', cargo
    nombre = coordinacion.nombre or (coordinacion.usuario.get_full_name() if coordinacion.usuario else '')
    return nombre, cargo


def nota_final_de(inscripcion, modulos):
    """El promedio de lo calificado obligatorio: la mejor nota de cada evaluación y la nota de cada deber."""
    notas = []
    calificadas = [leccion for modulo in modulos for leccion in modulo.visibles
                   if leccion.calificada and leccion.obligatoria and leccion.publicada]
    for leccion in calificadas:
        if leccion.tipo == 'evaluacion':
            mejor = max((intento.nota for intento in inscripcion.intentos.all() if intento.leccion_id == leccion.pk), default=None)
        else:
            mejor = next((entrega.nota for entrega in inscripcion.entregas.all() if entrega.leccion_id == leccion.pk), None)
        if mejor is not None:
            notas.append(Decimal(mejor))
    return (sum(notas) / len(notas)).quantize(Decimal('0.01')) if notas else None, bool(calificadas)


MESES_EN_ESPANOL = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


def presentar_fecha(fecha):
    """Fecha larga estable, sin depender del idioma o locale del servidor."""
    if fecha is None:
        return ''
    return f'{fecha.day} de {MESES_EN_ESPANOL[fecha.month - 1]} de {fecha.year}'


def periodo_actividad(inicio, fin):
    """Rango natural para el párrafo; una actividad incompleta no inventa fechas."""
    if inicio is None or fin is None:
        return ''
    if fin < inicio:
        raise ValidationError('Revise las fechas de la actividad: termina antes de empezar.')
    if inicio == fin:
        return f'el {presentar_fecha(inicio)}'
    if inicio.year == fin.year:
        if inicio.month == fin.month:
            return f'del {inicio.day} al {presentar_fecha(fin)}'
        return f'del {inicio.day} de {MESES_EN_ESPANOL[inicio.month - 1]} al {presentar_fecha(fin)}'
    return f'del {presentar_fecha(inicio)} al {presentar_fecha(fin)}'


def datos_de_la_actividad(curso, edicion=None, configuracion=None, exigir_completos=False):
    """Las fechas y horas del grupo prevalecen; nunca se estiman horas a partir de una nota."""
    categoria = getattr(configuracion, 'categoria_evento', '') or (
        curso.clasificacion if curso.clasificacion in dict(CATEGORIAS_EVENTO) else 'curso')
    if categoria not in dict(CATEGORIAS_EVENTO):
        raise ValidationError('Seleccione un tipo de actividad válido antes de emitir.')
    inicio = getattr(edicion, 'inicio', None) or getattr(configuracion, 'fecha_inicio', None)
    fin = getattr(edicion, 'fin', None) or getattr(configuracion, 'fecha_fin', None)
    horas = (getattr(edicion, 'horas_certificadas', None) or
             getattr(configuracion, 'horas_certificadas', None) or curso.duracion_horas)
    if exigir_completos and (not inicio or not fin or horas is None):
        raise ValidationError('Configure la fecha inicial, la fecha final y las horas reales del grupo o del certificado antes de emitir.')
    if inicio and fin and fin < inicio:
        raise ValidationError('Revise las fechas de la actividad: termina antes de empezar.')
    if horas is not None and not (Decimal('0.01') <= Decimal(horas) <= Decimal('2000')):
        raise ValidationError('Las horas que se certifican deben estar entre 0,01 y 2000.')
    return {'categoria_evento': categoria, 'fecha_inicio': inicio, 'fecha_fin': fin,
            'horas': Decimal(horas) if horas is not None else None}


def _crear_certificado(inscripcion, configuracion, tipo, nota=None, actor=None, motivo='', participante_evento=None):
    from apps.formacion.presentation.certificados_diseno import crear_diseno, dibujar_certificado
    persona = inscripcion or participante_evento
    curso = persona.edicion.curso
    firma, cargo = firmante_de(curso)
    usuario = inscripcion.usuario if inscripcion else None
    perfil = getattr(usuario, 'profile', None)
    actividad = datos_de_la_actividad(curso, persona.edicion, configuracion, exigir_completos=True)
    # El índice único sigue siendo la autoridad ante peticiones simultáneas o una colisión de código.
    for _ in range(3):
        codigo = nuevo_codigo()
        try:
            with transaction.atomic():
                certificado = CertificadoCurso(
                    inscripcion=inscripcion, participante_evento=participante_evento, codigo=codigo, tipo=tipo,
                    nombre=(persona.nombres_completos or (usuario.get_full_name() or usuario.get_username())),
                    documento=(persona.documento or getattr(perfil, 'cedula', '') or ''),
                    curso_nombre=curso.nombre, clasificacion=dict(CATEGORIAS_EVENTO)[actividad['categoria_evento']],
                    edicion=persona.edicion.nombre, unidad_nombre=curso.unidad.nombre,
                    nota_final=nota, firma_nombre=firma, firma_cargo=cargo,
                    emision_manual=actor is not None, emitido_por=actor, motivo_emision=motivo, **actividad)
                certificado.diseno_certificado = crear_diseno(certificado, configuracion, (firma, cargo))
                firmantes = certificado.diseno_certificado['firmantes']
                certificado.firma_nombre = firmantes[0]['nombre'] if firmantes else ''
                certificado.firma_cargo = firmantes[0]['cargo'] if firmantes else ''
                dibujar_certificado(certificado)
                certificado.save()
                return certificado
        except IntegrityError:
            identidad = {'inscripcion': inscripcion} if inscripcion else {'participante_evento': participante_evento}
            existente = CertificadoCurso.objects.filter(**identidad, anulado=False).first()
            if existente is not None:
                return existente
            if not CertificadoCurso.objects.filter(codigo=codigo).exists():
                raise
    raise ValidationError('No se pudo generar un código único; vuelva a intentar la emisión.')


def _identidad_externa_en_grupo(inscripcion):
    """La copia de matrícula prevalece; sólo las matrículas antiguas usan el perfil."""
    perfil = getattr(inscripcion.usuario, 'profile', None)
    documento = inscripcion.documento or getattr(perfil, 'cedula', '') or ''
    return bool(documento) and inscripcion.edicion.participantes_evento.filter(
        documento__iexact=documento).exists()


@transaction.atomic
def emitir_si_corresponde(inscripcion, reemitir=False):
    """Emite al completar los requisitos académicos; no concede roles de eventos."""
    from apps.formacion.presentation.aula_cursos import avance, lecciones_de
    inscripcion = InscripcionCurso.objects.select_for_update().select_related('edicion__curso__unidad', 'usuario').get(pk=inscripcion.pk)
    curso = inscripcion.edicion.curso
    if curso.es_externo or inscripcion.estado != 'aceptada' or not curso.emite_certificado:
        return None
    existente = CertificadoCurso.objects.filter(inscripcion=inscripcion, anulado=False).first()
    if existente is not None:
        return existente
    if not reemitir and CertificadoCurso.objects.filter(inscripcion=inscripcion, anulado=True).exists():
        return None
    if _identidad_externa_en_grupo(inscripcion):
        return None
    modulos = lecciones_de(curso)
    progreso = avance(curso, inscripcion, modulos)
    if not progreso['total'] or progreso['completadas'] < progreso['total']:
        return None
    nota, calificado = nota_final_de(inscripcion, modulos)
    configuracion = ConfiguracionCertificadoCurso.objects.filter(curso=curso).first()
    tipo = getattr(configuracion, 'tipo_certificado', 'auto')
    if tipo == 'auto':
        tipo = 'aprobacion' if calificado else 'participacion'
    if tipo not in {'aprobacion', 'participacion', 'asistencia'} or (tipo == 'aprobacion' and not calificado):
        return None
    try:
        datos_de_la_actividad(curso, inscripcion.edicion, configuracion, exigir_completos=True)
    except ValidationError:
        return None
    return _crear_certificado(inscripcion, configuracion, tipo, nota=nota)


@transaction.atomic
def emitir_certificado_evento(inscripcion, actor, tipo, motivo, confirmacion=False, reemitir=False):
    """Acredita una función o asistencia registrada por el gestor; nunca sustituye una aprobación académica."""
    from apps.formacion.presentation.cursos import puede_crear_cursos
    from apps.formacion.presentation.certificados_forms import AcreditacionCertificadoForm
    inscripcion = InscripcionCurso.objects.select_for_update().select_related('edicion__curso__unidad', 'usuario').get(pk=inscripcion.pk)
    curso = inscripcion.edicion.curso
    if not puede_crear_cursos(actor, curso.unidad):
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad acredita participantes de eventos.')
    if curso.es_externo:
        raise ValidationError('La certificación de esta actividad corresponde a su plataforma organizadora.')
    formulario = AcreditacionCertificadoForm({'inscripcion': inscripcion.pk, 'tipo': tipo, 'motivo': motivo,
                                              'confirmacion': '1' if confirmacion else ''})
    if not formulario.is_valid():
        raise ValidationError([str(error) for errores in formulario.errors.values() for error in errores])
    if inscripcion.estado != 'aceptada' or not curso.emite_certificado:
        raise ValidationError('La inscripción debe estar aceptada y la actividad debe emitir certificados.')
    existente = CertificadoCurso.objects.filter(inscripcion=inscripcion, anulado=False).first()
    if existente is not None:
        if existente.tipo != tipo:
            raise ValidationError('Ya existe un certificado vigente con otra modalidad. Revíselo antes de anular y reemitir.')
        return existente
    if not reemitir and CertificadoCurso.objects.filter(inscripcion=inscripcion, anulado=True).exists():
        raise ValidationError('El certificado anterior fue anulado. Use la acción de reemisión para corregirlo.')
    if _identidad_externa_en_grupo(inscripcion):
        raise ValidationError('Este documento también identifica a un participante externo de este grupo. La unidad debe resolver la identidad antes de emitir.')
    configuracion = ConfiguracionCertificadoCurso.objects.filter(curso=curso).first()
    return _crear_certificado(inscripcion, configuracion, tipo, actor=actor, motivo=formulario.cleaned_data['motivo'])


@transaction.atomic
def emitir_certificado_externo(participante, actor, tipo, motivo, confirmacion=False, reemitir=False):
    """Acredita una identidad externa registrada, sin matrícula ni aprobación académica."""
    from apps.formacion.presentation.cursos import puede_crear_cursos
    from apps.formacion.presentation.certificados_forms import AcreditacionCertificadoForm
    participante = ParticipanteEvento.objects.select_for_update().select_related('edicion__curso__unidad').get(pk=participante.pk)
    curso = participante.edicion.curso
    if not puede_crear_cursos(actor, curso.unidad):
        raise PermissionDenied('Solo el gestor de esta unidad acredita a participantes externos.')
    if curso.es_externo:
        raise ValidationError('La certificación de esta actividad corresponde a su plataforma organizadora.')
    formulario = AcreditacionCertificadoForm({'inscripcion': participante.pk, 'tipo': tipo, 'motivo': motivo,
                                              'confirmacion': '1' if confirmacion else ''})
    if not formulario.is_valid():
        raise ValidationError([str(e) for errores in formulario.errors.values() for e in errores])
    configuracion = ConfiguracionCertificadoCurso.objects.filter(curso=curso).first()
    actividad = datos_de_la_actividad(curso, participante.edicion, configuracion, exigir_completos=True)
    if not curso.emite_certificado or actividad['categoria_evento'] == 'curso':
        raise ValidationError('La acreditación externa corresponde a eventos, talleres o capacitaciones; no sustituye la aprobación de un curso.')
    existente = participante.certificados.filter(anulado=False).first()
    if existente:
        if existente.tipo != tipo:
            raise ValidationError('Ya existe un certificado vigente con otra modalidad. Revise la emisión anterior.')
        return existente
    if participante.edicion.inscripciones.filter(
            Q(documento__iexact=participante.documento) |
            Q(documento='', usuario__profile__cedula__iexact=participante.documento)).exists():
        raise ValidationError('La persona ya tiene una matrícula en este grupo. Use esa matrícula para evitar certificados duplicados.')
    if not reemitir and participante.certificados.filter(anulado=True).exists():
        raise ValidationError('El certificado anterior fue anulado. Use la acción de reemisión.')
    return _crear_certificado(None, configuracion, tipo, actor=actor, motivo=formulario.cleaned_data['motivo'],
                               participante_evento=participante)


def _certificados_del_curso(curso):
    return CertificadoCurso.objects.select_related('inscripcion__edicion__curso__unidad',
        'participante_evento__edicion__curso__unidad').filter(
        Q(inscripcion__edicion__curso=curso) | Q(participante_evento__edicion__curso=curso))


@login_required
@require_POST
def emitir_certificado_manual_view(request, slug, codigo):
    from apps.formacion.presentation.certificados_forms import AcreditacionCertificadoForm
    curso = _curso_del_editor(request, slug, codigo)
    formulario = AcreditacionCertificadoForm(request.POST)
    destino = reverse('inscritos_curso', args=[slug, codigo])
    if not formulario.is_valid():
        messages.error(request, 'No se emitió el certificado. ' + ' '.join(str(error) for errores in formulario.errors.values() for error in errores))
        return redirect(destino)
    inscripcion = get_object_or_404(InscripcionCurso.objects.select_related('edicion'),
                                    pk=formulario.cleaned_data['inscripcion'], edicion__curso=curso)
    try:
        certificado = emitir_certificado_evento(inscripcion, request.user, formulario.cleaned_data['tipo'],
                                                formulario.cleaned_data['motivo'], confirmacion=True)
    except ValidationError as exc:
        messages.error(request, 'No se emitió el certificado. ' + ' '.join(exc.messages))
    else:
        messages.success(request, f'Certificado {certificado.codigo} emitido y registrado.')
    return redirect(destino + f'?edicion={inscripcion.edicion_id}')



def pdf_del_certificado(certificado, mostrar_documento=True, vista_previa=False):
    """PDF autocontenido; la verificación pública siempre omite el documento de identidad."""
    from apps.formacion.presentation.certificados_diseno import dibujar_certificado
    return dibujar_certificado(certificado, mostrar_documento, vista_previa)


def _respuesta_pdf(certificado, descargar, mostrar_documento=True):
    respuesta = HttpResponse(pdf_del_certificado(certificado, mostrar_documento), content_type='application/pdf')
    disposicion = 'attachment' if descargar else 'inline'
    respuesta['Content-Disposition'] = f'{disposicion}; filename="certificado-{certificado.codigo}.pdf"'
    respuesta['X-Frame-Options'] = 'SAMEORIGIN'
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
@require_GET
def mi_certificado_view(request, slug, codigo):
    """Certificado propio por edición; una retirada posterior no anula el documento emitido."""
    from apps.formacion.presentation.matriculas_cursos import edicion_solicitada
    curso = get_object_or_404(Curso.objects.select_related('unidad'), codigo=codigo, unidad__slug=slug)
    if curso.es_externo:
        raise Http404('Los certificados se consultan en la plataforma organizadora.')
    edicion = edicion_solicitada(curso, request)
    inscripciones = (InscripcionCurso.objects.filter(usuario=request.user, edicion__curso=curso)
                     .select_related('edicion__curso__unidad').order_by('-fecha_inscripcion'))
    if edicion is not None:
        inscripciones = inscripciones.filter(edicion=edicion)
    elegida = request.GET.get('inscripcion', '')
    if elegida:
        inscripciones = inscripciones.filter(pk=id_solicitado(elegida))
    certificado = CertificadoCurso.objects.filter(inscripcion__in=inscripciones, anulado=False).first()
    if certificado is None:
        inscripcion = inscripciones.filter(estado='aceptada').first()
        if inscripcion is None:
            raise Http404('No tienes una inscripción en este curso.')
        certificado = emitir_si_corresponde(inscripcion)
    if certificado is None:
        raise Http404('Todavía no hay un certificado para este curso.')
    return _respuesta_pdf(certificado, request.GET.get('descargar') == '1')


@require_GET
def verificar_certificado_view(request, codigo=None):
    """La página pública que confirma si un certificado es auténtico y vigente; también busca por código escrito."""
    codigo = (codigo or request.GET.get('codigo', '')).strip().upper()
    certificado = CertificadoCurso.objects.filter(codigo=codigo).select_related(
        'inscripcion__edicion__curso__unidad', 'participante_evento__edicion__curso__unidad').first() if codigo else None
    if certificado is not None and request.GET.get('formato') == 'pdf' and not certificado.anulado:
        return _respuesta_pdf(certificado, False, mostrar_documento=False)
    return render(request, 'portal/pages/unidades/aula/certificado_verificar.html', {
        'codigo': codigo, 'certificado': certificado, 'buscado': bool(codigo),
    }, status=200 if certificado or not codigo else 404)


@login_required
@require_POST
def anular_certificado_view(request, slug, codigo, certificado_id):
    """La unidad anula un certificado emitido por error, con su motivo; la verificación pública lo muestra."""
    from apps.formacion.presentation.cursos import puede_crear_cursos

    curso = _curso_del_editor(request, slug, codigo, solo_activa=False)
    certificado = get_object_or_404(_certificados_del_curso(curso), pk=certificado_id)
    if not puede_crear_cursos(request.user, curso.unidad):
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad anula certificados.')
    motivo = request.POST.get('motivo', '').strip()[:300]
    if motivo and not certificado.anulado:
        certificado.anulado, certificado.motivo_anulacion = True, motivo
        certificado.anulado_por, certificado.anulado_en = request.user, timezone.now()
        certificado.save(update_fields=['anulado', 'motivo_anulacion', 'anulado_por', 'anulado_en'])
    return redirect(reverse('inscritos_curso', args=[slug, codigo]) + f'?edicion={certificado.edicion_origen.pk}')


@login_required
@require_POST
def reemitir_certificado_view(request, slug, codigo, certificado_id):
    """La unidad emite un certificado nuevo en lugar de uno anulado, con los datos corregidos de la persona."""
    from apps.formacion.presentation.cursos import puede_crear_cursos

    curso = _curso_del_editor(request, slug, codigo, solo_activa=False)
    anulado = get_object_or_404(_certificados_del_curso(curso), pk=certificado_id, anulado=True)
    if not puede_crear_cursos(request.user, curso.unidad):
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad emite certificados.')
    try:
        if anulado.participante_evento_id:
            nuevo = emitir_certificado_externo(anulado.participante_evento, request.user, anulado.tipo,
                                                anulado.motivo_emision, confirmacion=True, reemitir=True)
        elif anulado.emision_manual:
            nuevo = emitir_certificado_evento(anulado.inscripcion, request.user, anulado.tipo,
                                              anulado.motivo_emision, confirmacion=True, reemitir=True)
        else:
            nuevo = emitir_si_corresponde(anulado.inscripcion, reemitir=True)
    except ValidationError as exc:
        messages.error(request, 'No se reemitió el certificado. ' + ' '.join(exc.messages))
    else:
        if nuevo is None:
            messages.error(request, 'No se reemitió el certificado. Revise los requisitos, las fechas y las horas de la actividad.')
        else:
            messages.success(request, f'Certificado {nuevo.codigo} reemitido y registrado.')
    return redirect(reverse('inscritos_curso', args=[slug, codigo]) + f'?edicion={anulado.edicion_origen.pk}')


_SAL_PREVIA = 'cursos.diseno-certificado.v1'


def _curso_del_editor(request, slug, codigo, solo_activa=True):
    from apps.formacion.presentation.cursos import puede_crear_cursos
    unidades = Unidad.objects.filter(activo=True) if solo_activa else Unidad.objects.all()
    unidad = get_object_or_404(unidades, slug=slug)
    curso = get_object_or_404(Curso.objects.select_related('unidad'), unidad=unidad, codigo=codigo)
    if not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('Solo quien gestiona los cursos de la unidad configura certificados.')
    if curso.es_externo:
        raise Http404('La certificación se gestiona en la plataforma organizadora.')
    return curso


def _nombre_academico_real(valor):
    nombre = str(valor or '').strip()
    normalizado = re.sub(r'\s+', ' ', nombre.casefold())
    sin_tipo = re.sub(r'^(facultad|carrera)\s+', '', normalizado)
    pendientes = {'por registrar', 'por definir', 'por asignar', 'pendiente', 'sin asignar',
                  'no asignado', 'no asignada', 'no registrado', 'no registrada', 'no disponible',
                  'sin definir', 'sin carrera', 'ninguna', 'ninguno', 'n/a', 'externo', '-'}
    return '' if sin_tipo in pendientes or normalizado in pendientes else nombre


def _datos_reales_del_editor(request, curso, configuracion):
    """Sugiere datos registrados, sin persistirlos ni elegir una adscripción ambigua."""
    from apps.core.presentation.catalogos import carreras, facultades
    from apps.formacion.presentation.matriculas_cursos import edicion_solicitada

    unidad = curso.unidad
    iniciales = {}
    if not configuracion.emisor.strip():
        iniciales['emisor'] = unidad.nombre
    nombre_facultad = _nombre_academico_real(unidad.facultad)
    nombre_facultad = dict(facultades()).get(nombre_facultad, nombre_facultad)
    if not configuracion.facultad_nombre.strip() and nombre_facultad:
        iniciales['facultad_nombre'] = nombre_facultad
    catalogo_carreras = dict(carreras())
    sugeridas = []
    vistos = set()
    for valor in re.split(r'[,;\r\n]+', unidad.carreras or ''):
        nombre = _nombre_academico_real(catalogo_carreras.get(valor.strip(), valor.strip()))
        if nombre and nombre.casefold() not in vistos:
            sugeridas.append(nombre)
            vistos.add(nombre.casefold())
    if not configuracion.carrera_nombre.strip() and len(sugeridas) == 1:
        iniciales['carrera_nombre'] = sugeridas[0]

    edicion = edicion_solicitada(curso, request)
    if edicion is None:
        posibles = list(curso.ediciones.filter(activa=True).order_by('pk')[:2])
        edicion = posibles[0] if len(posibles) == 1 else None
    configuracion._edicion_de_muestra = edicion
    inicio = configuracion.fecha_inicio or getattr(edicion, 'inicio', None)
    fin = configuracion.fecha_fin or getattr(edicion, 'fin', None)
    if not (inicio and fin and fin < inicio):
        if not configuracion.fecha_inicio and inicio:
            iniciales['fecha_inicio'] = inicio
        if not configuracion.fecha_fin and fin:
            iniciales['fecha_fin'] = fin
    if configuracion.horas_certificadas is None:
        horas = getattr(edicion, 'horas_certificadas', None) or curso.duracion_horas
        if horas is not None:
            iniciales['horas_certificadas'] = horas
    if configuracion.usar_firmante_curso and not configuracion.firma_nombre.strip():
        nombre, cargo = firmante_de(curso)
        if nombre:
            iniciales['firma_nombre'] = nombre
            if not configuracion.firma_cargo.strip():
                iniciales['firma_cargo'] = cargo
    return iniciales, sugeridas


def _institucion_del_editor():
    from apps.core.presentation.identidad import identidad_actual, fuentes_logo
    institucion = identidad_actual()[1]
    return {'nombre': institucion.nombre, 'siglas': institucion.siglas,
            'logo_url': fuentes_logo(institucion, fondo='claro')['escritorio']}


def _formulario_certificado(request, curso):
    from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
    configuracion = ConfiguracionCertificadoCurso.objects.filter(curso=curso).first()
    categoria = curso.clasificacion if curso.clasificacion in dict(CATEGORIAS_EVENTO) else 'curso'
    configuracion = configuracion or ConfiguracionCertificadoCurso(curso=curso, categoria_evento=categoria)
    # Reutiliza el curso autorizado y su unidad: el contexto heredado debe ser el mismo que se revisa.
    configuracion.curso = curso
    iniciales, sugeridas = _datos_reales_del_editor(request, curso, configuracion)
    formulario = ConfiguracionCertificadoForm(request.POST if request.method == 'POST' else None,
                                              request.FILES if request.method == 'POST' else None,
                                              instance=configuracion, initial=iniciales)
    formulario.carreras_sugeridas = sugeridas
    from apps.core.presentation.identidad import identidad_actual
    paleta = dict(identidad_actual()[1].paleta)
    automaticos = {'primario': paleta.get('primario', '#006633'),
                   'acento': paleta.get('acento', '#ffce00')}
    for campo, clave in (('color_primario', 'primario'), ('color_acento', 'acento')):
        formulario.fields[campo].widget.attrs['placeholder'] = automaticos[clave]
    return formulario


def _muestra_certificado(curso, configuracion, tipo='aprobacion', nombre=None):
    from apps.formacion.presentation.certificados_diseno import crear_diseno
    firma, cargo = firmante_de(curso)
    edicion = getattr(configuracion, '_edicion_de_muestra', None)
    actividad = datos_de_la_actividad(curso, edicion, configuracion=configuracion)
    muestra = CertificadoCurso(
        codigo='CERT-DEMO-2026', tipo=tipo,
        nombre=nombre or 'María Fernanda Ejemplo de Muestra', documento='DOCUMENTO DE MUESTRA',
        curso_nombre=curso.nombre, clasificacion=dict(CATEGORIAS_EVENTO)[configuracion.categoria_evento],
        **actividad,
        edicion=edicion.nombre if edicion else 'Edición por definir', unidad_nombre=curso.unidad.nombre,
        nota_final=Decimal('92.50') if tipo == 'aprobacion' else None,
        firma_nombre=firma, firma_cargo=cargo,
    )
    muestra.es_muestra_editor = True
    muestra.diseno_certificado = crear_diseno(muestra, configuracion, (firma, cargo))
    return muestra


def _huella_previa(configuracion, curso, usuario, muestra=None):
    """Vincula campos e imágenes con el contexto visible resuelto; el token sólo contiene su hash."""
    from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
    from apps.formacion.presentation.certificados_diseno import imagen_png
    campos = {}
    for campo in ConfiguracionCertificadoForm.Meta.fields:
        valor = getattr(configuracion, campo)
        if campo in IMAGENES_CERTIFICADO:
            maximo = ((1600, 1200) if campo == 'imagen_fondo' else (1600, 1000) if campo == 'foto_alusiva'
                      else (1000, 500) if campo.startswith('logo_') else (800, 300))
            campos[campo] = imagen_png(valor, maximo)
        else:
            campos[campo] = valor.isoformat() if hasattr(valor, 'isoformat') else str(valor) if isinstance(valor, Decimal) else valor
    muestra = muestra or _muestra_certificado(curso, configuracion)
    # Incluye logos institucionales, fotografía y firmante heredados, textos resueltos y URL del QR.
    # Si cualquiera cambia entre la vista previa y el guardado, exige revisar el diseño actualizado.
    contenido = json.dumps({'campos': campos, 'contexto': muestra.diseno_certificado,
                            'curso': curso.pk, 'usuario': usuario.pk},
                            ensure_ascii=False, sort_keys=True).encode('utf8')
    return hashlib.sha256(contenido).hexdigest()


def _validar_composicion(curso, configuracion):
    # Comprueba todas las modalidades y un nombre largo antes de permitir guardar el diseño.
    nombre_largo = ('Nombre y apellidos compuestos de participante de muestra ' * 4)[:200]
    for tipo, etiqueta in TIPOS_CERTIFICADO:
        try:
            pdf_del_certificado(_muestra_certificado(curso, configuracion, tipo, nombre_largo), vista_previa=True)
        except ValidationError as exc:
            raise ValidationError([f'{etiqueta}: {mensaje}' for mensaje in exc.messages]) from exc


@login_required
@never_cache
@xframe_options_sameorigin
def editar_certificado_curso_view(request, slug, codigo):
    curso = _curso_del_editor(request, slug, codigo)
    if request.method == 'POST':
        # Serializa también la primera configuración del curso; evita perder imágenes si dos
        # gestores guardan a la vez. Las validaciones terminan antes de escribir archivos o filas.
        with transaction.atomic():
            from apps.formacion.presentation.cursos import puede_crear_cursos
            curso = get_object_or_404(Curso.objects.select_for_update().select_related('unidad'),
                                     pk=curso.pk, codigo=codigo, unidad__slug=slug, unidad__activo=True)
            if not puede_crear_cursos(request.user, curso.unidad):
                raise PermissionDenied('Solo quien gestiona los cursos de la unidad configura certificados.')
            formulario = _formulario_certificado(request, curso)
            if formulario.is_valid():
                try:
                    configuracion = formulario.save(commit=False)
                    tipo = request.POST.get('tipo_muestra', 'aprobacion')
                    if tipo not in dict(TIPOS_CERTIFICADO):
                        raise ValidationError('Seleccione una modalidad de certificado válida para la vista previa.')
                    token = signing.loads(request.POST.get('vista_previa_token', ''), salt=_SAL_PREVIA, max_age=1800)
                    muestra = _muestra_certificado(curso, configuracion, tipo)
                    if token != _huella_previa(configuracion, curso, request.user, muestra):
                        raise signing.BadSignature
                    _validar_composicion(curso, configuracion)
                except signing.BadSignature:
                    formulario.add_error(None, 'La vista previa está desactualizada o caducó. Espere a que se actualice antes de guardar.')
                except ValidationError as exc:
                    formulario.add_error(None, exc)
                else:
                    anteriores = ConfiguracionCertificadoCurso.objects.filter(curso=curso).values(*IMAGENES_CERTIFICADO).first() or {}
                    configuracion.actualizado_por = request.user
                    configuracion.save()
                    for campo, anterior in anteriores.items():
                        actual = getattr(configuracion, campo)
                        if anterior and anterior != actual.name:
                            almacenamiento = actual.storage
                            transaction.on_commit(lambda ruta=anterior, storage=almacenamiento: storage.delete(ruta))
                    destino = reverse('editar_certificado_curso', args=[slug, codigo])
                    destino += '?embed=1&guardado=1' if request.GET.get('embed') == '1' else '?guardado=1'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'ok': True, 'url': destino})
                    return redirect(destino)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'errores': formulario.errors.get_json_data()}, status=400)
    else:
        formulario = _formulario_certificado(request, curso)
    respuesta = render(request, 'portal/pages/unidades/aula/certificado_editor.html', {
        'curso': curso, 'unidad': curso.unidad, 'formulario': formulario,
        'embebido': request.GET.get('embed') == '1', 'guardado': request.GET.get('guardado') == '1',
        'curso_url': reverse('curso_unidad', args=[slug, codigo]),
        'previa_url': reverse('previsualizar_certificado_curso', args=[slug, codigo]) +
                      ('?edicion=' + str(request.GET['edicion']) if request.GET.get('edicion') else ''),
        'institucion_certificado': _institucion_del_editor(),
        'verificacion_url_base': settings.SITE_URL.rstrip('/') + reverse('verificar_certificado_buscar'),
        'verificacion_es_local': _verificacion_local(),
    }, status=400 if request.method == 'POST' else 200)
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
@require_POST
@never_cache
@xframe_options_sameorigin
def previsualizar_certificado_curso_view(request, slug, codigo):
    """Genera un PDF ficticio con los campos enviados, sin guardar configuración ni emitir."""
    curso = _curso_del_editor(request, slug, codigo)
    formulario = _formulario_certificado(request, curso)
    if not formulario.is_valid():
        return JsonResponse({'errores': formulario.errors.get_json_data()}, status=400)
    configuracion = formulario.save(commit=False)
    try:
        # La previa automática renderiza sólo la modalidad visible; guardar valida las cinco.
        tipo = request.POST.get('tipo_muestra', 'aprobacion')
        if tipo not in dict(TIPOS_CERTIFICADO):
            raise ValidationError('Seleccione una modalidad de certificado válida para la vista previa.')
        muestra = _muestra_certificado(curso, configuracion, tipo)
        contenido = pdf_del_certificado(muestra, mostrar_documento=False, vista_previa=True)
    except ValidationError as exc:
        return JsonResponse({'errores': {'__all__': [{'message': str(mensaje)} for mensaje in exc.messages]}}, status=400)
    respuesta = HttpResponse(contenido, content_type='application/pdf')
    respuesta['Content-Disposition'] = 'inline; filename="vista-previa-certificado.pdf"'
    respuesta['X-Certificado-Vista-Previa'] = signing.dumps(_huella_previa(configuracion, curso, request.user, muestra), salt=_SAL_PREVIA)
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
@require_GET
@xframe_options_sameorigin
def certificado_gestor_view(request, slug, codigo, certificado_id):
    curso = _curso_del_editor(request, slug, codigo, solo_activa=False)
    certificado = get_object_or_404(_certificados_del_curso(curso), pk=certificado_id)
    return _respuesta_pdf(certificado, request.GET.get('descargar') == '1')
