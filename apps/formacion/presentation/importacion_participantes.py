"""Planificación y confirmación atómica de importaciones, limitadas a un grupo."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Upper

from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.formacion.models.cursos import Curso, EdicionCurso, ParticipanteEvento
from apps.formacion.presentation.certificados_cursos import datos_de_la_actividad, emitir_certificado_evento, emitir_certificado_externo
from apps.formacion.presentation.matriculas_cursos import matricular_lista
from apps.formacion.presentation.matriculas_datos import validar_datos_matricula
from apps.formacion.models.cursos_certificacion import TIPOS_CERTIFICADO

TIPOS_EVENTO = ('participacion', 'asistencia', 'ponente', 'organizador')


def contexto_evento(edicion, tipo, motivo, confirmacion=False):
    from apps.formacion.presentation.certificados_forms import AcreditacionCertificadoForm
    formulario = AcreditacionCertificadoForm({'inscripcion': 1, 'tipo': tipo, 'motivo': motivo,
                                              'confirmacion': '1' if confirmacion else ''})
    if not formulario.is_valid():
        raise ValidationError([str(e) for errores in formulario.errors.values() for e in errores])
    config = ConfiguracionCertificadoCurso.objects.filter(curso=edicion.curso).first()
    actividad = datos_de_la_actividad(edicion.curso, edicion, config, exigir_completos=True)
    if not edicion.curso.emite_certificado or actividad['categoria_evento'] == 'curso':
        raise ValidationError('Configure una actividad de evento, taller o capacitación que emita certificados. La aprobación de cursos se obtiene con sus evaluaciones.')
    actividad.update(emisor=getattr(config, 'emisor', '') or edicion.curso.unidad.nombre,
                     tipo=tipo, tipo_rotulo=dict(TIPOS_CERTIFICADO)[tipo], motivo=formulario.cleaned_data['motivo'])
    return actividad


def _planes_evento(edicion, filas, tipo):
    documentos = [f['datos']['documento'] for f in filas]
    inscritos, externos = {}, {}
    inscripciones = edicion.inscripciones.annotate(_documento=Upper('documento'),
        _cedula=Upper('usuario__profile__cedula')).filter(Q(_documento__in=documentos) |
        Q(documento='', _cedula__in=documentos)).select_related('usuario', 'usuario__profile').prefetch_related('certificados')
    for persona in inscripciones:
        perfil = getattr(persona.usuario, 'profile', None)
        documento = (persona.documento or getattr(perfil, 'cedula', '') or '').upper()
        inscritos.setdefault(documento, []).append(persona)
    for persona in edicion.participantes_evento.annotate(_documento=Upper('documento')).filter(
            _documento__in=documentos).prefetch_related('certificados'):
        externos.setdefault(persona.documento.upper(), []).append(persona)
    planes = []
    for fila in filas:
        datos = validar_datos_matricula(**{k: fila['datos'][k] for k in ('documento', 'nombres_completos')})
        matriculados = inscritos.get(datos['documento'], [])
        registrados = externos.get(datos['documento'], [])
        if len(matriculados) > 1 or len(registrados) > 1 or (matriculados and registrados):
            fila['errores'].append('Este documento identifica varios registros del grupo. La unidad debe resolver la identidad antes de emitir.')
        persona = next(iter(matriculados or registrados), None)
        if persona:
            nombre = persona.nombres_completos or (persona.usuario.get_full_name() if hasattr(persona, 'usuario') else '')
            if nombre and nombre.casefold() != datos['nombres_completos'].casefold():
                fila['errores'].append('El documento ya tiene otros nombres en este grupo. Revise la identidad antes de importar.')
            if hasattr(persona, 'estado') and persona.estado != 'aceptada':
                fila['errores'].append('La matrícula existente no está aceptada. Resuelva sus requisitos o pagos antes de acreditar.')
            certificados = list(persona.certificados.all())
            vigente = next((c for c in certificados if not c.anulado), None)
            if vigente and vigente.tipo != tipo:
                fila['errores'].append('Ya existe un certificado vigente con otra modalidad.')
            if certificados and not vigente:
                fila['errores'].append('El certificado anterior está anulado. Use la acción de reemisión.')
            fila['estado'] = 'Ya emitido' if vigente else 'Emitir sobre matrícula' if hasattr(persona, 'usuario') else 'Emitir'
        else:
            fila['estado'] = 'Registrar participante y emitir'
        planes.append((fila, persona))
    return planes


def _resolver_correos(filas):
    """Un correo vacío sólo se resuelve con una identidad única y verificada."""
    from allauth.account.models import EmailAddress
    from apps.core.models.usuarios_base import UserProfile
    from apps.formacion.presentation.matriculas_cursos import cuenta_con_correo_verificado
    for fila in filas:
        if fila['errores'] or fila['datos'].get('correo'):
            continue
        perfiles = list(UserProfile.objects.filter(cedula__iexact=fila['datos']['documento'],
            user__is_active=True).select_related('user')[:2])
        if len(perfiles) != 1:
            fila['errores'].append('Completa el correo: la cédula no identifica una cuenta única.')
            continue
        persona = perfiles[0].user
        correos = list(EmailAddress.objects.filter(user=persona, verified=True).values_list('email', flat=True))
        principal = next((c for c in correos if c.casefold() == persona.email.casefold()), None)
        correo = principal or (correos[0] if len(correos) == 1 else None)
        if not correo or cuenta_con_correo_verificado(correo) != persona:
            fila['errores'].append('Completa un correo: la cuenta no tiene un correo verificado y único.')
        else:
            fila['datos']['correo'] = correo.lower()


def revisar_importacion(edicion, filas, gestor, modo, tipo='', motivo='', confirmacion=False):
    from apps.formacion.presentation.cursos import puede_crear_cursos
    if not puede_crear_cursos(gestor, edicion.curso.unidad):
        raise PermissionDenied('Solo el gestor de esta unidad puede importar participantes.')
    if edicion.curso.es_externo or not edicion.curso.activo:
        raise ValidationError('Esta actividad no admite nuevos participantes en esta plataforma.')
    if modo not in ('evento', 'matricula') or not filas or len(filas) > 500:
        raise ValidationError('Seleccione una operación y una lista de 1 a 500 personas.')
    vistos = set()
    for fila in filas:
        documento = fila['datos'].get('documento', '').upper()
        if documento in vistos:
            fila['errores'].append('Documento repetido en esta lista.')
        vistos.add(documento)
    if modo == 'evento':
        actividad = contexto_evento(edicion, tipo, motivo, confirmacion)
        if not any(f['errores'] for f in filas):
            _planes_evento(edicion, filas, tipo)
        return actividad
    _resolver_correos(filas)
    if any(f['errores'] for f in filas):
        return None
    datos = [f['datos'] for f in filas]
    try:
        matricular_lista(edicion, datos, gestor, exonerar=False, solo_validar=True, limite=500)
    except ValidationError as exc:
        # Sólo desglosa consultas por fila si hay un conflicto; el camino válido se valida una vez.
        for fila in filas:
            try:
                matricular_lista(edicion, [fila['datos']], gestor, exonerar=False, solo_validar=True, limite=500)
            except ValidationError as individual:
                fila['errores'].extend(individual.messages)
        if not any(f['errores'] for f in filas):
            raise exc  # Por ejemplo, el cupo total insuficiente para la lista completa.
    for fila in filas:
        fila['estado'] = 'Matrícula o invitación; pago pendiente si corresponde'
    return None


@transaction.atomic
def confirmar_importacion(edicion, filas, gestor, modo, tipo='', motivo='', confirmacion=False):
    Curso.objects.select_for_update().only('pk').get(pk=edicion.curso_id)
    edicion = EdicionCurso.objects.select_for_update(of=('self',)).select_related('curso__unidad').get(pk=edicion.pk)
    # Repite identidad, cupos, autorización y condiciones actuales; no confía en el preview guardado.
    filas = [{**f, 'datos': dict(f['datos']), 'errores': []} for f in filas]
    revisar_importacion(edicion, filas, gestor, modo, tipo, motivo, confirmacion)
    if any(f['errores'] for f in filas):
        raise ValidationError([f'Fila {f["numero"]}: ' + ' '.join(f['errores']) for f in filas if f['errores']])
    if modo == 'matricula':
        resultados = matricular_lista(edicion, [f['datos'] for f in filas], gestor, exonerar=False, limite=500)
        for fila in filas:
            correo = fila['datos']['correo']
            fila['estado'] = ('Ya registrado' if correo in resultados['ya_estaban'] else
                              'Invitación registrada' if correo in resultados['invitadas'] else
                              'Matrícula registrada; pago pendiente si corresponde')
        return filas
    contexto_evento(edicion, tipo, motivo, confirmacion)
    for fila, persona in _planes_evento(edicion, filas, tipo):
        if persona is None:
            persona = ParticipanteEvento.objects.create(edicion=edicion, creado_por=gestor, **fila['datos'])
        existente = persona.certificados.filter(anulado=False).exists()
        if hasattr(persona, 'usuario_id'):
            certificado = emitir_certificado_evento(persona, gestor, tipo, motivo, confirmacion=confirmacion)
        else:
            certificado = emitir_certificado_externo(persona, gestor, tipo, motivo, confirmacion=confirmacion)
        fila.update(estado='Ya emitido' if existente else 'Certificado emitido', certificado_id=certificado.pk,
                    codigo=certificado.codigo)
    return filas
