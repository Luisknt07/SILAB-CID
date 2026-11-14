"""Inscripción a los cursos con costo, códigos de descuento, verificación de pagos y matrícula por la unidad.

Un curso gratuito se inscribe con un clic (abierto o con aprobación, según el curso). Uno con costo pide el medio de
pago y el comprobante; un código de descuento rebaja el costo y, si lo deja en cero, la persona entra sin pagar. La
unidad verifica cada pago y, al hacerlo, la persona entra al curso mientras haya cupo. La unidad también matricula
directamente, una persona o un grupo, por usuario o por correo; los correos sin cuenta quedan como invitaciones que
se activan cuando la persona entra a la plataforma con ese correo.
"""
import re

from apps.core.identificadores import id_solicitado

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.formacion.models.cursos_inscripcion import CodigoDescuento, InvitacionCurso, PagoInscripcion
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso
from apps.formacion.models.cursos_inscripcion import MEDIOS_DE_PAGO, monto_con_descuento

from apps.formacion.presentation.aula_cursos import _curso, archivo_protegido, cupos_libres, inscripcion_de, puede_inscribirse
from apps.formacion.presentation.cursos import puede_crear_cursos
from apps.formacion.presentation.matriculas_forms import DatosMatriculaForm
from apps.formacion.presentation.matriculas_cursos import edicion_solicitada, guardar_datos_matricula, url_con_edicion


def es_pagado(curso):
    return bool(curso.costo and curso.costo > 0)


def medios_de(curso):
    habilitados = {'transferencia': curso.pago_transferencia, 'ventanilla': curso.pago_ventanilla,
                   'enlace': curso.pago_enlace and bool(curso.enlace_pago)}
    return [(clave, texto) for clave, texto in MEDIOS_DE_PAGO if habilitados[clave]]


CODIGO_INVALIDO = 'Ese código no es válido para este curso (no existe, venció o ya se usó todas las veces).'
INTENTOS_DE_CODIGO = 10  # fallidos por persona y curso en una hora


def buscar_codigo(curso, texto, usuario=None):
    """(código, error): el código vigente del curso que la persona escribió. Todos los códigos inválidos dan el mismo
    mensaje y los intentos fallidos se limitan, para que no se puedan adivinar probando."""
    texto = (texto or '').strip().upper()
    if not texto:
        return None, ''
    llave = f'codigos-fallidos:{curso.pk}:{getattr(usuario, "pk", "anonimo")}'
    if cache.get(llave, 0) >= INTENTOS_DE_CODIGO:
        return None, 'Probaste demasiados códigos. Vuelve a intentarlo en una hora.'
    codigo = CodigoDescuento.objects.filter(curso=curso, codigo=texto).first()
    if codigo is None or codigo.motivo_invalido():
        cache.set(llave, cache.get(llave, 0) + 1, 3600)
        return None, CODIGO_INVALIDO
    return codigo, ''


TAMANO_MAXIMO_COMPROBANTE = 10 * 1024 * 1024


class PagoForm(DatosMatriculaForm):
    edicion = forms.ModelChoiceField(label="Grupo o edición", queryset=EdicionCurso.objects.none(), empty_label="Selecciona el grupo")
    codigo = forms.CharField(label='Código de descuento', max_length=30, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'Si tienes uno', 'autocomplete': 'off'}))
    medio = forms.ChoiceField(label='Medio de pago', required=False)
    referencia = forms.CharField(label='Número de comprobante o transacción', max_length=80, required=False)
    comprobante = forms.FileField(label='Comprobante (PDF o imagen)', required=False)

    def __init__(self, *args, curso=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.curso, self.usuario = curso, usuario
        self.fields['edicion'].queryset = curso.ediciones.filter(activa=True)
        self.fields['medio'].choices = medios_de(curso)
        self.codigo_aplicado = None

    def clean(self):
        datos = super().clean()
        codigo, error = buscar_codigo(self.curso, datos.get('codigo'), self.usuario)
        if error:
            self.add_error('codigo', error)
            return datos
        self.codigo_aplicado = codigo
        datos['monto'] = monto_con_descuento(self.curso.costo, codigo.porcentaje if codigo else 0)
        if datos['monto'] > 0:
            if not datos.get('medio'):
                self.add_error('medio', 'Elige cómo pagaste.')
            if not datos.get('comprobante') and not datos.get('referencia'):
                raise ValidationError('Adjunta el comprobante o escribe el número de la transacción.')
        comprobante = datos.get('comprobante')
        if comprobante and not re.search(r'\.(pdf|png|jpe?g|webp)$', comprobante.name, re.IGNORECASE):
            self.add_error('comprobante', 'Sube el comprobante en PDF o como imagen.')
        elif comprobante and comprobante.size > TAMANO_MAXIMO_COMPROBANTE:
            self.add_error('comprobante', 'El comprobante pesa más de 10 MB.')
        return datos


def _registrar_pago(inscripcion, curso, formulario):
    datos = formulario.cleaned_data
    codigo = formulario.codigo_aplicado
    pago = getattr(inscripcion, 'pago', None) or PagoInscripcion(inscripcion=inscripcion)
    pago.monto_original, pago.codigo = curso.costo, codigo
    pago.descuento, pago.monto = (codigo.porcentaje if codigo else 0), datos['monto']
    pago.medio, pago.referencia = datos.get('medio', '') if datos['monto'] > 0 else '', datos.get('referencia', '')
    if datos.get('comprobante'):
        pago.comprobante = datos['comprobante']
    pago.estado = 'pendiente' if datos['monto'] > 0 else 'exonerado'
    pago.verificado_por, pago.verificado_en, pago.observacion = None, None, ''
    pago.save()
    return pago


@login_required
@xframe_options_sameorigin
def pagar_curso_view(request, slug, codigo):
    """Elige un grupo y presenta sus datos y comprobante, conservando esa edición."""
    unidad, curso = _curso(slug, codigo, request.user)
    if not curso.activo:
        raise Http404('Esta actividad no admite nuevas matrículas.')
    if not es_pagado(curso):
        raise Http404('Este curso es gratuito.')
    elegida = edicion_solicitada(curso, request)
    destino = url_con_edicion(reverse('curso_unidad', args=[unidad.slug, curso.codigo]) + '#inscripcion', elegida)
    previa = inscripcion_de(curso, request.user, elegida) if elegida else None
    reenvio = bool(previa and previa.estado == 'rechazada' and getattr(previa, 'pago', None)
                   and previa.pago.estado == 'rechazado' and previa.edicion.estado()[0] == 'inscripciones')
    if previa is not None and not reenvio:
        return redirect(destino)
    inicial = {'edicion': elegida.pk if elegida else None,
               'nombres_completos': previa.nombres_completos if previa else request.user.get_full_name(),
               'documento': previa.documento if previa else getattr(getattr(request.user, 'profile', None), 'cedula', '')}
    formulario = PagoForm(request.POST or None, request.FILES or None, curso=curso, usuario=request.user, initial=inicial)
    if request.method == 'POST' and formulario.is_valid():
        elegida = formulario.cleaned_data['edicion']
        destino = url_con_edicion(destino, elegida)
        try:
            with transaction.atomic():
                curso = get_object_or_404(Curso.objects.select_for_update(), pk=curso.pk, unidad=unidad)
                if curso.es_externo or not curso.activo:
                    raise ValidationError('Esta actividad no admite nuevas matrículas en esta plataforma.')
                edicion = EdicionCurso.objects.select_for_update().get(pk=elegida.pk)
                previa = InscripcionCurso.objects.filter(edicion=edicion, usuario=request.user).select_related('pago').first()
                reenvio = bool(previa and previa.estado == 'rechazada' and getattr(previa, 'pago', None)
                               and previa.pago.estado == 'rechazado' and edicion.estado()[0] == 'inscripciones')
                if previa and previa.estado in ('aceptada', 'pendiente'):
                    return redirect(destino)
                if not reenvio:
                    permitido, motivo = puede_inscribirse(curso, edicion, request.user)
                    if not permitido:
                        raise ValidationError(motivo)
                elif cupos_libres(edicion) == 0:
                    raise ValidationError('Los cupos de este grupo se agotaron.')
                codigo_aplicado = formulario.codigo_aplicado
                if codigo_aplicado is not None:
                    codigo_aplicado = CodigoDescuento.objects.select_for_update().get(pk=codigo_aplicado.pk)
                    if codigo_aplicado.motivo_invalido():
                        raise ValidationError(CODIGO_INVALIDO)
                inscripcion = previa or InscripcionCurso(edicion=edicion, usuario=request.user)
                inscripcion.estado, inscripcion.observacion = 'pendiente', ''
                inscripcion.fecha_respuesta = None
                inscripcion.save()
                guardar_datos_matricula(inscripcion, formulario.cleaned_data['nombres_completos'],
                                       formulario.cleaned_data['documento'])
                pago = _registrar_pago(inscripcion, curso, formulario)
                if pago.estado == 'exonerado':
                    abierta = curso.inscripcion == 'abierta' and cupos_libres(edicion) != 0
                    inscripcion.estado = 'aceptada' if abierta else 'pendiente'
                    inscripcion.fecha_respuesta = timezone.now() if abierta else None
                    inscripcion.save(update_fields=['estado', 'fecha_respuesta'])
            return redirect(destino)
        except ValidationError as error:
            formulario.add_error(None, error.messages)
        except IntegrityError:
            formulario.add_error(None, 'Otra operación modificó esta matrícula. Revisa el grupo antes de repetir.')
    return render(request, 'portal/pages/unidades/aula/curso_pago.html', {
        'unidad': unidad, 'curso': curso, 'edicion': elegida, 'formulario': formulario, 'reenvio': reenvio,
        'medios': medios_de(curso), 'curso_url': destino,
    })


def verificar_pago(pago, usuario, aprobar, observacion=''):
    """Decisión autorizada y atómica: verifica la plaza con el grupo bloqueado."""
    if not puede_crear_cursos(usuario, pago.inscripcion.edicion.curso.unidad):
        raise PermissionDenied('No puedes verificar pagos de esta unidad.')
    with transaction.atomic():
        curso = Curso.objects.select_for_update(of=('self',)).select_related('unidad').get(pk=pago.inscripcion.edicion.curso_id)
        if curso.es_externo or not puede_crear_cursos(usuario, curso.unidad):
            raise PermissionDenied('No puedes verificar pagos locales de esta actividad.')
        edicion = EdicionCurso.objects.select_for_update().get(pk=pago.inscripcion.edicion_id)
        pago = PagoInscripcion.objects.select_for_update().select_related('inscripcion').get(pk=pago.pk)
        inscripcion = pago.inscripcion
        if aprobar:
            if cupos_libres(edicion) == 0 and inscripcion.estado != 'aceptada':
                return False
            pago.estado = 'verificado'
            inscripcion.estado = 'aceptada'
        else:
            pago.estado = 'rechazado'
            if inscripcion.estado != 'aceptada':
                inscripcion.estado = 'rechazada'
        pago.verificado_por, pago.verificado_en, pago.observacion = usuario, timezone.now(), observacion[:300]
        inscripcion.fecha_respuesta, inscripcion.observacion = timezone.now(), observacion[:300]
        pago.save()
        inscripcion.save(update_fields=['estado', 'fecha_respuesta', 'observacion'])
    return True


SEPARADORES = re.compile(r'[\s,;]+')


def correo_verificado(persona, correo):
    from apps.formacion.presentation.matriculas_cursos import correo_verificado as confirmado
    return confirmado(persona, correo)


def persona_por_dato(dato):
    """Usuario explícito del gestor, o propietario único de un correo confirmado."""
    from apps.formacion.presentation.matriculas_cursos import cuenta_con_correo_verificado
    if '@' in dato:
        return cuenta_con_correo_verificado(dato)
    return get_user_model().objects.filter(username__iexact=dato, is_active=True).first()


def matricular(edicion, texto, usuario):
    """Compatibilidad con la lista antigua; las nuevas listas exigen ficha de identidad."""
    from apps.formacion.presentation.matriculas_cursos import matricular_lista
    filas, no_reconocidas = [], []
    for dato in dict.fromkeys(parte.strip() for parte in SEPARADORES.split(texto or '') if parte.strip()):
        persona = persona_por_dato(dato)
        correo = persona.email if persona and '@' not in dato else dato
        try:
            validate_email(correo)
        except ValidationError:
            no_reconocidas.append(dato)
            continue
        fila = {'correo': correo}
        if persona and '@' not in dato:
            fila['persona'] = persona  # Elección explícita de una cuenta, sólo por gestor autorizado.
        filas.append(fila)
    if filas:
        resultado = matricular_lista(edicion, filas, usuario, legacy=True)
    else:
        resultado = {'matriculadas': [], 'ya_estaban': [], 'invitadas': [], 'no_reconocidas': []}
    resultado['no_reconocidas'] = no_reconocidas
    return resultado


def aplicar_invitaciones(usuario):
    from apps.formacion.presentation.matriculas_cursos import aplicar_invitaciones as vincular
    return vincular(usuario)


def atender_gestion(request, curso):
    """Acciones autorizadas del gestor: pagos, matrícula con ficha y listas, o cancelación."""
    if not puede_crear_cursos(request.user, curso.unidad):
        raise PermissionDenied('No puedes gestionar las matrículas de esta unidad.')
    from apps.formacion.presentation.matriculas_cursos import matricular_lista
    from apps.formacion.presentation.matriculas_forms import ListaMatriculaForm, MatriculaIndividualForm
    accion = request.POST.get('accion')
    if accion in ('verificar_pago', 'rechazar_pago'):
        pago = get_object_or_404(PagoInscripcion, pk=id_solicitado(request.POST.get('pago')), inscripcion__edicion__curso=curso)
        if not verificar_pago(pago, request.user, accion == 'verificar_pago', request.POST.get('observacion', '')):
            return 'No quedan cupos: el pago no se verificó.'
        messages.success(request, 'Pago actualizado correctamente.')
        return ''
    if accion == 'cancelar_invitacion':
        invitacion = get_object_or_404(InvitacionCurso, pk=id_solicitado(request.POST.get('invitacion')),
                                       edicion__curso=curso, inscripcion__isnull=True)
        with transaction.atomic():
            EdicionCurso.objects.select_for_update().get(pk=invitacion.edicion_id)
            InvitacionCurso.objects.filter(pk=invitacion.pk, inscripcion__isnull=True).update(activa=False)
        messages.success(request, 'Invitación cancelada; su cupo queda disponible.')
        return 'Invitación cancelada; su cupo queda disponible.'
    if accion in ('matricular_individual', 'matricular_lista', 'matricular'):
        try:
            if accion == 'matricular':
                edicion = get_object_or_404(curso.ediciones, pk=id_solicitado(request.POST.get('edicion')))
                resultado = matricular(edicion, request.POST.get('personas', ''), request.user)
            else:
                clase = MatriculaIndividualForm if accion == 'matricular_individual' else ListaMatriculaForm
                formulario = clase(request.POST, request.FILES or None, curso=curso)
                if not formulario.is_valid():
                    return 'No se guardó la matrícula: ' + ' '.join(str(error) for errores in formulario.errors.values() for error in errores)
                datos = formulario.cleaned_data
                filas = ([{campo: datos[campo] for campo in ('correo', 'nombres_completos', 'documento')}]
                         if accion == 'matricular_individual' else datos['filas'])
                resultado = matricular_lista(datos['edicion'], filas, request.user)
        except (ValidationError, IntegrityError) as error:
            return 'No se guardó la matrícula: ' + (' '.join(error.messages) if isinstance(error, ValidationError)
                                                   else 'Otra operación modificó estos datos; revisa la lista y el cupo.')
        partes = [f'{len(resultado["matriculadas"])} matriculadas', f'{len(resultado["invitadas"])} invitadas por correo',
                  f'{len(resultado["ya_estaban"])} ya estaban']
        if resultado['no_reconocidas']:
            partes.append('no se reconocieron: ' + ', '.join(resultado['no_reconocidas'][:10]))
        resumen = ' · '.join(partes)
        messages.success(request, resumen)
        return resumen
    return None


@login_required
def comprobante_view(request, slug, codigo, pago_id):
    pago = get_object_or_404(PagoInscripcion.objects.select_related('inscripcion__edicion__curso__unidad'), pk=pago_id,
                             inscripcion__edicion__curso__codigo=codigo, inscripcion__edicion__curso__unidad__slug=slug)
    unidad = pago.inscripcion.edicion.curso.unidad
    if pago.inscripcion.usuario_id != request.user.pk and not puede_crear_cursos(request.user, unidad):
        raise PermissionDenied('Solo quien pagó y quien verifica ven este comprobante.')
    if not pago.comprobante:
        raise Http404()
    return archivo_protegido(pago.comprobante)
