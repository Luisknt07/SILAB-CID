"""Matrícula por grupos: identidad de la matrícula, cupos e invitaciones verificadas."""
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso
from apps.formacion.models.cursos_inscripcion import InvitacionCurso, PagoInscripcion
from apps.formacion.presentation.matriculas_datos import normalizar_correo, validar_datos_matricula


def seleccionar_edicion(curso, dato):
    """Un identificador explícito siempre pertenece al curso; nunca elige otro grupo."""
    try:
        identificador = int(dato)
    except (TypeError, ValueError) as error:
        raise Http404('Selecciona un grupo válido del curso.') from error
    try:
        return curso.ediciones.get(pk=identificador)
    except EdicionCurso.DoesNotExist as error:
        raise Http404('El grupo no pertenece a este curso.') from error


def edicion_solicitada(curso, request, obligatoria=False):
    if request.method == 'POST' and 'edicion' in request.POST:
        dato = request.POST.get('edicion')
    else:
        dato = request.GET.get('edicion')
    if dato not in (None, ''):
        return seleccionar_edicion(curso, dato)
    if obligatoria:
        raise ValidationError('Selecciona el grupo o edición antes de inscribirte.')
    return None


def url_con_edicion(url, edicion):
    if edicion is None:
        return url
    partes = urlsplit(url)
    parametros = [(clave, valor) for clave, valor in parse_qsl(partes.query, keep_blank_values=True) if clave != 'edicion']
    parametros.append(('edicion', str(edicion.pk)))
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(parametros), partes.fragment))


def cupos_disponibles(edicion):
    if edicion is None or edicion.cupo is None:
        return None
    aceptadas = edicion.inscripciones.filter(estado='aceptada').count()
    reservadas = edicion.invitaciones.filter(activa=True).filter(
        Q(inscripcion__isnull=True) | Q(inscripcion__estado='pendiente', exonerar_matricula=False)).count()
    return max(edicion.cupo - aceptadas - reservadas, 0)


def correo_verificado(persona, correo):
    from allauth.account.models import EmailAddress
    return bool(persona and persona.is_active and EmailAddress.objects.filter(
        user=persona, email__iexact=correo, verified=True).exists())


def cuenta_con_correo_verificado(correo):
    from allauth.account.models import EmailAddress
    identificadores = list(EmailAddress.objects.filter(email__iexact=correo, verified=True, user__is_active=True)
                           .values_list('user_id', flat=True).distinct()[:2])
    if len(identificadores) > 1:
        raise ValidationError('Ese correo está verificado en más de una cuenta. Resuelve la identidad antes de matricular.')
    return get_user_model().objects.get(pk=identificadores[0]) if identificadores else None


def _datos_de_persona(persona):
    perfil = getattr(persona, 'profile', None)
    return {'nombres_completos': persona.get_full_name().strip(),
            'documento': (getattr(perfil, 'cedula', '') or '').strip().upper()}


def _comprobar_documento(edicion, documento, *, persona=None, correo=None):
    if not documento:
        return
    inscripciones = edicion.inscripciones.filter(documento__iexact=documento)
    if persona is not None:
        inscripciones = inscripciones.exclude(usuario=persona)
    invitaciones = edicion.invitaciones.filter(activa=True, documento__iexact=documento)
    if correo:
        invitaciones = invitaciones.exclude(correo__iexact=correo)
    if persona is not None:
        invitaciones = invitaciones.exclude(inscripcion__usuario=persona)
        anterior = _datos_de_persona(persona)['documento']
        if anterior and anterior != documento:
            raise ValidationError('El documento no coincide con la identidad de la cuenta. No se modificó esa cuenta.')
    externos = edicion.participantes_evento.filter(documento__iexact=documento)
    if externos.exists():
        raise ValidationError('Ese documento ya está registrado como participante externo del evento. La unidad debe revisar su vinculación antes de matricular.')
    if inscripciones.exists() or invitaciones.exists():
        raise ValidationError('Ese documento ya tiene una matrícula o invitación en este grupo.')


def guardar_datos_matricula(inscripcion, nombres_completos, documento):
    datos = validar_datos_matricula(nombres_completos=nombres_completos, documento=documento)
    _comprobar_documento(inscripcion.edicion, datos['documento'], persona=inscripcion.usuario,
                        correo=inscripcion.usuario.email)
    for campo in ('nombres_completos', 'documento'):
        anterior = getattr(inscripcion, campo)
        if anterior and anterior != datos[campo]:
            raise ValidationError('La matrícula ya tiene datos de identidad. Solicita su revisión a la unidad.')
        setattr(inscripcion, campo, datos[campo])
    inscripcion.save(update_fields=['nombres_completos', 'documento'])
    return inscripcion


def _guardar_inscripcion(edicion, persona, datos, *, exonerar=True):
    inscripcion = InscripcionCurso.objects.filter(edicion=edicion, usuario=persona).first()
    ya_aceptada = inscripcion is not None and inscripcion.estado == 'aceptada'
    inscripcion = inscripcion or InscripcionCurso(edicion=edicion, usuario=persona)
    if datos.get('nombres_completos') and datos.get('documento'):
        for campo in ('nombres_completos', 'documento'):
            if getattr(inscripcion, campo) and getattr(inscripcion, campo) != datos[campo]:
                raise ValidationError('La matrícula existente tiene otra identidad. Solicita su revisión.')
            setattr(inscripcion, campo, datos[campo])
    pago = getattr(inscripcion, 'pago', None)
    requiere_pago = bool(edicion.curso.costo and not exonerar and
                         (pago is None or pago.estado not in ('verificado', 'exonerado')))
    inscripcion.estado = 'pendiente' if requiere_pago else 'aceptada'
    inscripcion.fecha_respuesta = timezone.now()
    inscripcion.observacion = 'Matriculado por la unidad.'
    inscripcion.save()
    if requiere_pago and pago is None:
        PagoInscripcion.objects.create(inscripcion=inscripcion, monto_original=edicion.curso.costo,
            descuento=0, monto=edicion.curso.costo, estado='pendiente', observacion='Pendiente de pago; importación de matrícula.')
    elif exonerar and edicion.curso.costo and (pago is None or pago.estado == 'rechazado'):
        PagoInscripcion.objects.update_or_create(inscripcion=inscripcion, defaults={
            'monto_original': edicion.curso.costo, 'descuento': 100, 'monto': Decimal('0.00'),
            'estado': 'exonerado', 'observacion': 'Matrícula sin costo de la unidad.'})
    return inscripcion, not ya_aceptada


def matricular_lista(edicion, filas, gestor, *, legacy=False, exonerar=True, solo_validar=False, limite=100):
    """Valida y guarda toda la lista en una transacción; las invitaciones reservan plaza."""
    from apps.formacion.presentation.cursos import puede_crear_cursos
    if not puede_crear_cursos(gestor, edicion.curso.unidad):
        raise PermissionDenied('Solo quien gestiona los cursos de esta unidad puede matricular.')
    if not filas or len(filas) > min(limite, 500):
        raise ValidationError(f'La lista debe contener entre 1 y {min(limite, 500)} personas.')
    resultado = {'matriculadas': [], 'ya_estaban': [], 'invitadas': [], 'no_reconocidas': []}
    with transaction.atomic():
        curso = Curso.objects.select_for_update(of=('self',)).select_related('unidad').get(pk=edicion.curso_id)
        if not puede_crear_cursos(gestor, curso.unidad):
            raise PermissionDenied('Solo quien gestiona los cursos de esta unidad puede matricular.')
        edicion = EdicionCurso.objects.select_for_update(of=('self',)).select_related('curso__unidad').get(pk=edicion.pk)
        if edicion.curso.es_externo or not edicion.curso.activo:
            raise ValidationError('Esta actividad no admite matrículas en esta plataforma.')
        if not edicion.activa or edicion.estado()[0] == 'finalizada':
            raise ValidationError('Este grupo no admite nuevas matrículas.')
        planes, correos, documentos, cuentas = [], set(), set(), set()
        plazas = 0
        for fila in filas:
            persona = fila.get('persona') if legacy else None
            correo = normalizar_correo(fila.get('correo') or (persona.email if persona else ''))
            if legacy:
                datos = {campo: fila.get(campo, '') for campo in ('nombres_completos', 'documento')}
            else:
                datos = validar_datos_matricula(correo=correo, nombres_completos=fila.get('nombres_completos'),
                                               documento=fila.get('documento'))
            if correo in correos or (datos.get('documento') and datos['documento'] in documentos):
                raise ValidationError('Hay un correo o documento repetido en la lista.')
            correos.add(correo)
            if datos.get('documento'):
                documentos.add(datos['documento'])
            persona = persona or cuenta_con_correo_verificado(correo)
            if persona is not None:
                if not persona.is_active:
                    raise ValidationError('Una cuenta de la lista no está activa.')
                if persona.pk in cuentas:
                    raise ValidationError('Dos correos de la lista pertenecen a la misma cuenta.')
                cuentas.add(persona.pk)
            invitacion = edicion.invitaciones.filter(correo__iexact=correo).select_related('inscripcion').first()
            inscripcion = edicion.inscripciones.filter(usuario=persona).first() if persona else None
            if invitacion and invitacion.inscripcion_id and (persona is None or invitacion.inscripcion.usuario_id != persona.pk):
                raise ValidationError('Ese correo ya tiene una matrícula vinculada a otra cuenta. La unidad debe revisar su identidad.')
            _comprobar_documento(edicion, datos.get('documento'), persona=persona, correo=correo)
            if invitacion and invitacion.activa:
                for campo in ('nombres_completos', 'documento'):
                    if getattr(invitacion, campo) and datos.get(campo) and getattr(invitacion, campo) != datos[campo]:
                        raise ValidationError('Una invitación existente tiene otros datos. Revísala antes de repetir la matrícula.')
            if inscripcion and inscripcion.estado == 'aceptada':
                resultado['ya_estaban'].append(correo)
                continue
            reservada = bool(invitacion and invitacion.activa and (not invitacion.inscripcion_id or
                (not invitacion.exonerar_matricula and invitacion.inscripcion.estado == 'pendiente')))
            plazas += 0 if reservada else 1
            planes.append((persona, correo, datos, invitacion, reservada))
        libres = cupos_disponibles(edicion)
        if libres is not None and plazas > libres:
            raise ValidationError(f'No se guardó la lista: necesita {plazas} cupos nuevos y quedan {libres}.')
        if solo_validar:
            return resultado
        for persona, correo, datos, invitacion, reservada in planes:
            sin_costo_autorizado = bool(exonerar or (invitacion and invitacion.activa and invitacion.exonerar_matricula))
            invitacion = invitacion or InvitacionCurso(edicion=edicion, correo=correo, creada_por=gestor)
            invitacion.exonerar_matricula = sin_costo_autorizado
            invitacion.activa = True
            for campo in ('nombres_completos', 'documento'):
                if datos.get(campo):
                    setattr(invitacion, campo, datos[campo])
            if persona is None:
                invitacion.inscripcion = None
                invitacion.save()
                resultado['ya_estaban' if reservada else 'invitadas'].append(correo)
            else:
                inscripcion, creada = _guardar_inscripcion(edicion, persona, datos, exonerar=sin_costo_autorizado)
                invitacion.inscripcion = inscripcion
                invitacion.save()
                resultado['matriculadas' if creada else 'ya_estaban'].append(correo)
    return resultado


def aplicar_invitaciones(usuario):
    """Vincula solo correos confirmados y unívocos, sin editar identidad de la cuenta."""
    from allauth.account.models import EmailAddress
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return []
    correos = list(EmailAddress.objects.filter(user=usuario, verified=True).values_list('email', flat=True))
    vinculadas = []
    for correo in correos:
        try:
            propietario = cuenta_con_correo_verificado(correo)
        except ValidationError:
            continue
        if propietario != usuario:
            continue
        candidatas = InvitacionCurso.objects.filter(correo__iexact=correo, activa=True, inscripcion__isnull=True,
                                                   edicion__curso__activo=True, edicion__curso__origen='nativo')
        for clave, edicion_id, curso_id in candidatas.values_list('pk', 'edicion_id', 'edicion__curso_id'):
            with transaction.atomic():
                Curso.objects.select_for_update().only('pk').get(pk=curso_id)
                edicion = EdicionCurso.objects.select_for_update(of=('self',)).select_related('curso').get(pk=edicion_id)
                invitacion = InvitacionCurso.objects.select_for_update().filter(pk=clave, activa=True, inscripcion__isnull=True).first()
                if (invitacion is None or not edicion.activa or edicion.estado()[0] == 'finalizada'
                        or edicion.curso.es_externo or not edicion.curso.activo):
                    continue
                propia = edicion.inscripciones.filter(usuario=usuario).first()
                if edicion.cupo is not None and edicion.inscripciones.filter(estado='aceptada').exclude(usuario=usuario).count() >= edicion.cupo:
                    continue
                datos = {campo: getattr(invitacion, campo) for campo in ('nombres_completos', 'documento')}
                try:
                    _comprobar_documento(edicion, datos['documento'], persona=usuario, correo=correo)
                    if propia:
                        for campo in ('nombres_completos', 'documento'):
                            if getattr(propia, campo) and datos[campo] and getattr(propia, campo) != datos[campo]:
                                raise ValidationError('La inscripción ya tiene otra identidad.')
                except ValidationError:
                    continue  # Una verificación no corrige identidades conflictivas de forma automática.
                inscripcion, _ = _guardar_inscripcion(edicion, usuario, datos, exonerar=invitacion.exonerar_matricula)
                invitacion.inscripcion = inscripcion
                invitacion.save(update_fields=['inscripcion'])
                vinculadas.append(inscripcion)
    return vinculadas
