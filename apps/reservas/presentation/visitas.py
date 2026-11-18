"""Visitas: un papel en una solicitud, no un cuarto tipo de usuario.

Las internas requieren cuenta; las externas admiten contacto sin cuenta. La solicitud crea la
reserva de las áreas del recorrido (agenda, aforo, aprobación, comprobante y
avisos de siempre) y guarda lo propio de la visita: institución, grupo,
recorrido por las áreas visitables, guías que exige (uno por cada tantas
personas), protección del inventario por visitante y lista de asistencia
que se toma en la puerta. La ficha publica la oferta; el panel asigna el
guía, registra la asistencia y define la oferta.
"""

import json
import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.reservas.models.visitas import AsistenteVisita, SolicitudVisita
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.reservas.models.reservas import Reserva, ReservaConsumible
from apps.directorio_unidades.models.core import Unidad

from apps.core.usuarios.middleware import AVISO as AVISO_PERFIL
from apps.core.usuarios.vigencia import perfil_vigente

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.periodos import resolver_periodo_reserva
from apps.reservas.presentation.seguridad import buscar_persona, proteccion_por_persona, requisitos_de
from apps.reservas.presentation.asistentes_visita import asistentes_desde_json
from apps.reservas.presentation.visita_identidad import categoria_visita, contacto_externo, asistentes_internos
from apps.reservas.presentation.cotizaciones import calcular_costo_referencial_recursos

DOS = Decimal('0.01')
NOMBRES_PROPOSITO = dict(SolicitudVisita.PROPOSITOS)
ESTADOS_VIGENTES = ('pendiente', 'confirmada', 'en_proceso')


# ------------------------------------------------------------------ la oferta
def _configuracion(unidad):
    # Consulta fresca: la oferta puede cambiar en la misma petición que la lee.
    return ConfiguracionOperativaUnidad.objects.filter(unidad=unidad).first()


def costo_por_guia(servicio):
    """Referencia del guía que asume la UPEC; nunca es un cargo al visitante."""
    if servicio is None:
        return Decimal('0')
    return (
        Decimal(servicio.tarifa_base or 0)
        + Decimal(servicio.horas_mano_obra_estimadas or 0) * Decimal(servicio.costo_hora_mano_obra or 0)
    ).quantize(DOS, rounding=ROUND_HALF_UP)


def guias_necesarios(personas, personas_por_guia):
    """Un guía por cada tantas personas; siempre al menos uno."""
    return max(1, math.ceil(int(personas) / max(int(personas_por_guia or 1), 1)))


def oferta_de_visitas(unidad):
    """Lo que la ficha publica: áreas visitables, aforo, guías, requisitos del visitante y costo."""
    configuracion = _configuracion(unidad)
    areas = list(
        EspacioReservable.objects.filter(unidad=unidad, activo=True, visitable=True).order_by('orden', 'nombre')
    )
    areas_restringidas = list(
        EspacioReservable.objects.filter(unidad=unidad, activo=True, visitable=False).order_by('orden', 'nombre')
    )
    servicio = (
        FablabService.objects.filter(unidad=unidad, tipo_servicio='visita', activo=True).order_by('pk').first()
    )
    requisitos = requisitos_de(unidad, 'visitante')
    configurada = configuracion.acepta_visitas if configuracion else (
        unidad.codigo_base in {'laboratorios', 'centro_experimental', 'plantas_piloto', 'observatorios'}
    )
    return {
        'acepta': configurada,
        'acepta_configurada': configurada,
        'personas_por_guia': configuracion.personas_por_guia if configuracion else 15,
        'texto': configuracion.visitas_texto if configuracion else '',
        'areas': areas,
        'areas_restringidas': areas_restringidas,
        'recorrido_por_coordinar': not bool(areas),
        'temas': [area.nombre for area in (areas or areas_restringidas)[:6]],
        'aforo': min((area.capacidad for area in areas if area.capacidad), default=0) if areas else (unidad.capacidad_personas or 0),
        'requisitos': requisitos,
        'proteccion': [requisito for requisito in requisitos if requisito.tipo == 'proteccion'],
        'restricciones': [requisito for requisito in requisitos if requisito.tipo == 'restriccion'],
        'servicio': servicio,
        'costo_por_guia': costo_por_guia(servicio),
        'materiales_por_visitante': [
            {
                'nombre': fila['consumible'].nombre,
                'cantidad': str(fila['cantidad']),
                'unidad': fila['consumible'].unidad_medida,
                'precio_unitario': str(fila['consumible'].precio_unitario or 0),
            }
            for fila in proteccion_por_persona(unidad, 'visitante', 1)
        ],
        'impuestos': {
            'aplica': bool(configuracion and configuracion.aplicar_iva),
            'porcentaje': str(configuracion.porcentaje_iva if configuracion else 0),
        },
    }


# --------------------------------------------------------------- la solicitud
def _valor(datos, clave):
    return (datos.get(clave) or '').strip() if hasattr(datos, 'get') else ''


def _lista(datos, clave):
    if hasattr(datos, 'getlist'):
        return [str(valor) for valor in datos.getlist(clave)]
    valor = datos.get(clave) if hasattr(datos, 'get') else None
    if valor is None:
        return []
    return [str(item) for item in (valor if isinstance(valor, (list, tuple, set)) else [valor])]


def _si(valor):
    return str(valor or '').strip().lower() in {'on', 'true', '1', 'si', 'sí'}


def _entero(texto, nombre, minimo=1):
    try:
        numero = int(str(texto).strip())
    except (TypeError, ValueError) as error:
        raise ValidationError(f'{nombre} debe ser un número entero.') from error
    if numero < minimo:
        raise ValidationError(f'{nombre} debe ser al menos {minimo}.')
    return numero


def _hora(texto, nombre):
    valor = parse_time(texto or '')
    if valor is None:
        raise ValidationError(f'{nombre} no es válida.')
    if valor.minute or valor.second or valor.microsecond:
        raise ValidationError('Selecciona bloques de horas completas en el calendario.')
    return valor


def _fecha(texto):
    try:
        return datetime.strptime(texto or '', '%Y-%m-%d').date()
    except ValueError as error:
        raise ValidationError('Elige la fecha de la visita.') from error


def asistentes_desde_texto(texto):
    """Una persona por línea: «Nombre; documento»."""
    filas = []
    for linea in (texto or '').splitlines():
        nombre, _, documento = linea.strip().partition(';')
        if nombre.strip():
            filas.append({'nombre': nombre.strip()[:150], 'documento': documento.strip()[:40]})
    return filas


def aforo_del_recorrido(recorrido):
    return min((area.capacidad for area in recorrido if area.capacidad), default=0)


def seleccionar_recorrido_visita(oferta, elegidas):
    """Ningún área ajena o fuera del recorrido publicado se puede solicitar."""
    elegidas = {str(valor) for valor in elegidas}
    publicadas = {str(area.pk) for area in oferta['areas']}
    if elegidas - publicadas:
        raise ValidationError('El recorrido contiene áreas que no están habilitadas para visitas.')
    if publicadas and not elegidas:
        raise ValidationError('Elige al menos un área visitable para el recorrido.')
    return [area for area in oferta['areas'] if str(area.pk) in elegidas]


@operacion_reservas
def crear_visita(unidad, responsable, datos):
    """La solicitud: valida el grupo, el recorrido, el aforo y la agenda, y crea la reserva con la visita."""
    from apps.reservas.presentation.cambios import asegurar_revision_inicial
    from apps.reservas.presentation.notificaciones import crear_notificacion
    from apps.reservas.presentation.conflictos import validar_conflictos_recursos
    from apps.reservas.presentation.participantes import datos_usuario_para_periodo
    from apps.reservas.presentation.horarios import validar_horario_operativo

    categoria = categoria_visita(responsable, datos)
    contacto = contacto_externo(datos) if responsable is None else {
        'nombre': responsable.get_full_name() or responsable.username,
        'correo': responsable.email or '',
        'telefono': getattr(getattr(responsable, 'profile', None), 'telefono', '') or '',
    }
    oferta = oferta_de_visitas(unidad)
    if not oferta['acepta']:
        raise ValidationError('La unidad no recibe visitas por ahora.')
    institucion = _valor(datos, 'institucion')[:180]
    if not institucion:
        raise ValidationError('Indica la institución o el grupo que visita.')
    proposito = _valor(datos, 'proposito') or 'academica'
    if proposito not in NOMBRES_PROPOSITO:
        raise ValidationError('Elige el propósito de la visita.')
    if categoria == 'interna':
        asistentes = asistentes_internos(datos.get('usuarios_json'))
        if not asistentes:
            raise ValidationError('Busca y añade al menos un visitante interno registrado.')
    else:
        asistentes = asistentes_desde_json(datos.get('asistentes_json')) if 'asistentes_json' in datos else asistentes_desde_texto(datos.get('asistentes'))
    conteo = 'lista' if categoria == 'interna' else (_valor(datos, 'conteo') or 'estimado')
    if conteo not in {'lista', 'estimado'}:
        raise ValidationError('Selecciona cómo calcular el número de visitantes.')
    if conteo == 'lista' and not asistentes:
        raise ValidationError('Añade al menos un asistente o elige una cantidad estimada.')
    personas = len(asistentes) if conteo == 'lista' else _entero(_valor(datos, 'personas'), 'El número de personas')
    if personas > 200:
        raise ValidationError('Cada solicitud admite hasta 200 visitantes; coordina varios grupos con la unidad.')
    fecha = _fecha(_valor(datos, 'fecha'))
    if fecha <= timezone.localdate():
        raise ValidationError('La visita se programa con al menos un día de anticipación.')
    if fecha > timezone.localdate() + timedelta(days=366):
        raise ValidationError('Programa la visita dentro de los próximos doce meses.')
    hora_inicio = _hora(_valor(datos, 'hora_inicio'), 'La hora de inicio')
    hora_fin = _hora(_valor(datos, 'hora_fin'), 'La hora de fin')
    if hora_fin <= hora_inicio:
        raise ValidationError('La hora de fin debe ser posterior a la de inicio.')
    recorrido = seleccionar_recorrido_visita(oferta, _lista(datos, 'recorrido'))
    alcance = 'areas' if recorrido else 'unidad_completa'
    aforo = aforo_del_recorrido(recorrido) if recorrido else (unidad.capacidad_personas or 0)
    if aforo and personas > aforo:
        nombre = min((area for area in recorrido if area.capacidad), key=lambda area: area.capacidad).nombre if recorrido else unidad.nombre
        raise ValidationError(
            f'{nombre} admite {aforo} personas y la visita declara {personas}: '
            'reduce el grupo, divide la visita en turnos o quita esa área del recorrido.'
        )
    if not _si(datos.get('requisitos_aceptados')):
        raise ValidationError('Acepta los requisitos de la visita para continuar.')
    if len(asistentes) > personas:
        raise ValidationError('La lista de asistentes tiene más nombres que personas declaradas.')
    guias = guias_necesarios(personas, oferta['personas_por_guia'])
    descripcion = _valor(datos, 'descripcion')[:2000]
    rango_edades = _valor(datos, 'rango_edades')[:60]
    try:
        contexto = resolver_periodo_reserva(
            fecha, {'actividad_catalogo': None, 'periodo_academico': ''}, 'vinculacion'
        )
    except ValueError as error:
        raise ValidationError(str(error)) from error
    perfil = datos_usuario_para_periodo(responsable, contexto['periodo']) if responsable else {
        'tipo_usuario': 'externo', 'facultad': '', 'carrera': '',
    }
    validacion = {
        'incluye_espacio': True,
        'alcance_espacio': alcance,
        'tipo_solicitud': 'recursos',
        'modalidad_servicio': '',
        'proposito_codigo': 'vinculacion',
        'numero_participantes': personas + guias,
    }
    try:
        validar_horario_operativo(
            unidad,
            periodo=contexto['periodo'],
            semana=contexto['semana_academica'],
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            tipo_solicitud='recursos',
            modalidad_servicio='',
            tipo_usuario=perfil['tipo_usuario'],
            proposito_codigo='vinculacion',
            es_administrador=bool(responsable and responsable.is_staff),
        )
        validar_conflictos_recursos(unidad, fecha, hora_inicio, hora_fin, [], [], recorrido, **validacion)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    proteccion = proteccion_por_persona(unidad, 'visitante', personas)
    cotizacion = calcular_costo_referencial_recursos(
        [(fila['consumible'], fila['cantidad'], 'estimacion') for fila in proteccion],
        responsable,
        configuracion=_configuracion(unidad),
        espacios=recorrido,
        incluye_espacio=True,
        duracion_horas=Decimal(str((datetime.combine(fecha, hora_fin) - datetime.combine(fecha, hora_inicio)).total_seconds())) / Decimal('3600'),
        acompanamiento_visita=(guias, oferta['costo_por_guia']),
    )
    costo = Decimal(cotizacion['total'])
    nombre_proposito = NOMBRES_PROPOSITO[proposito].lower()
    plural = 's' if guias != 1 else ''
    with transaction.atomic():
        Unidad.objects.select_for_update().get(pk=unidad.pk)
        try:
            validar_conflictos_recursos(
                unidad, fecha, hora_inicio, hora_fin, [], [], recorrido, bloquear_existentes=True, **validacion,
            )
        except ValueError as error:
            raise ValidationError(str(error)) from error
        reserva = Reserva.objects.create(
            laboratorio=unidad,
            usuario=responsable,
            tipo_solicitud='recursos',
            provision_consumibles='unidad' if proteccion else 'ninguno',
            incluye_espacio=True,
            solicito_espacio=True,
            alcance_espacio=alcance,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            horas_seleccionadas=json.dumps(
                list(range(hora_inicio.hour, max(hora_fin.hour, hora_inicio.hour + 1)))
            ),
            duracion=max(1, hora_fin.hour - hora_inicio.hour),
            equipo_codigo=recorrido[0].codigo[:60] if len(recorrido) == 1 else 'VISITA',
            equipo_nombre=recorrido[0].nombre[:100] if len(recorrido) == 1 else 'Visita guiada a la unidad',
            nombre_solicitante=contacto['nombre'][:100],
            correo_solicitante=contacto['correo'],
            telefono_solicitante=contacto['telefono'][:20],
            institucion=institucion,
            tipo_usuario_solicitante=(perfil['tipo_usuario'] or '')[:20],
            facultad_solicitante=perfil['facultad'] or '',
            carrera_solicitante=perfil['carrera'] or '',
            proposito=f'Visita {nombre_proposito} de {institucion}: {personas} personas',
            proposito_codigo='vinculacion',
            subtipo_actividad='transferencia_conocimiento',
            alcance_beneficiario='interno' if categoria == 'interna' else 'externo',
            entidad_beneficiaria=institucion,
            vinculacion_actividad='independiente',
            referencia_actividad=f'Visita de {institucion}'[:220],
            periodo=contexto['periodo'],
            periodo_academico=contexto['periodo_academico'] or '',
            version_calendario=contexto['version_calendario'],
            semana_academica=contexto['semana_academica'],
            semana_academica_numero=contexto['semana_academica_numero'],
            origen_programacion='adicional',
            descripcion_proyecto=descripcion or f'Visita {nombre_proposito} de {institucion}.',
            intencion_solicitud=descripcion,
            titulo_solicitud=f'Visita de {institucion}'[:255],
            numero_participantes=personas,
            desglose_cotizacion=cotizacion,
            costo_estimado=costo,
            descuento_aplicado=Decimal(cotizacion['descuento_porcentaje']),
            estado='pendiente',
        )
        reserva.espacios_solicitados.set(recorrido)
        for fila in proteccion:
            ReservaConsumible.objects.create(
                reserva=reserva,
                consumible=fila['consumible'],
                cantidad_solicitada=fila['cantidad'],
                metodo_estimacion='estimacion',
            )
        visita = SolicitudVisita.objects.create(
            unidad=unidad,
            reserva=reserva,
            responsable=responsable,
            categoria=categoria,
            institucion=institucion,
            proposito=proposito,
            personas=personas,
            rango_edades=rango_edades,
            descripcion=descripcion,
            guias_necesarios=guias,
            requisitos_aceptados=True,
            costo_estimado=costo,
        )
        visita.recorrido.set(recorrido)
        AsistenteVisita.objects.bulk_create([AsistenteVisita(visita=visita, **fila) for fila in asistentes])
        asegurar_revision_inicial(reserva, actor=responsable)
    crear_notificacion(
        reserva=reserva,
        usuario=responsable,
        tipo='confirmacion',
        titulo=f'Visita de {institucion} registrada',
        mensaje=(
            f'La unidad recibió la solicitud de visita de {institucion} para el {fecha:%d/%m/%Y} '
            f'({personas} personas, {guias} guía{plural}). La revisará y te avisará.'
        ),
        clave=f'reserva:{reserva.pk}:visita:solicitada',
        enviar_email=True,
        url=reverse('comprobante_reserva', args=[reserva.pk]),
    )
    return visita


def visita_de(reserva):
    """La visita que respalda una reserva, si la hay."""
    return (
        SolicitudVisita.objects.filter(reserva=reserva)
        .select_related('guia', 'responsable')
        .prefetch_related('recorrido', 'asistentes')
        .first()
    )


# ------------------------------------------------------------ la asistencia
@operacion_reservas
def registrar_asistencia(visita, datos, usuario=None):
    """La lista de asistencia en la puerta: quién vino, quién se sumó y qué se observó."""
    ahora = timezone.now()
    presentes = set(_lista(datos, 'presentes'))
    for asistente in visita.asistentes.all():
        asistio = str(asistente.pk) in presentes
        if asistio != asistente.asistio:
            asistente.asistio = asistio
            asistente.ingreso_en = ahora if asistio else None
            asistente.save(update_fields=['asistio', 'ingreso_en'])
    nuevos = asistentes_desde_texto(datos.get('nuevos') if hasattr(datos, 'get') else '')
    AsistenteVisita.objects.bulk_create([
        AsistenteVisita(visita=visita, asistio=True, ingreso_en=ahora, **fila) for fila in nuevos
    ])
    observaciones = _valor(datos, 'observaciones')
    if observaciones != visita.observaciones:
        visita.observaciones = observaciones
        visita.save(update_fields=['observaciones', 'actualizada_en'])
    return visita


def asistencia_registrada(reserva):
    """Una visita empieza cuando alguien del grupo ya ingresó."""
    try:
        visita = reserva.visita
    except ObjectDoesNotExist:
        return False
    return visita.asistentes.filter(asistio=True).exists()


# ---------------------------------------------------------------- el panel
def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def contexto_visitas(unidad, permisos_operativos):
    puede = bool(permisos_operativos.get('reservas'))
    hoy = timezone.localdate()
    oferta = oferta_de_visitas(unidad)
    visitas = list(
        SolicitudVisita.objects.filter(unidad=unidad)
        .select_related('reserva', 'responsable', 'guia')
        .prefetch_related('recorrido', 'asistentes')
        .order_by('-reserva__fecha', '-pk')[:60]
    )
    for visita in visitas:
        lista = list(visita.asistentes.all())
        visita.total_lista = len(lista)
        visita.presentes_total = sum(1 for asistente in lista if asistente.asistio)
        visita.url_asistencia = reverse('asistencia_visita', args=[unidad.slug, visita.pk])
        visita.url_comprobante = reverse('comprobante_reserva', args=[visita.reserva_id])
        visita.vigente = visita.reserva.fecha >= hoy and visita.reserva.estado in ESTADOS_VIGENTES
    proximas = [visita for visita in visitas if visita.vigente]
    metricas = {
        'proximas': len(proximas),
        'pendientes': sum(1 for visita in proximas if visita.reserva.estado == 'pendiente'),
        'personas': sum(visita.personas for visita in proximas),
        'sin_guia': sum(1 for visita in proximas if visita.guia_id is None),
    }
    return {
        'visitas_habilitadas': puede,
        'puede_operar_visitas': puede,
        'puede_configurar_visitas': bool(permisos_operativos.get('configuracion')),
        'visitas_metricas': metricas,
        'visitas_unidad': visitas,
        'oferta_visitas_panel': oferta,
        'areas_para_visitas': list(
            EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre')
        ),
    }


def operar_visita(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if not registro_id:
        raise ValidationError('Selecciona la visita.')
    visita = get_object_or_404(SolicitudVisita.objects.select_for_update(), pk=registro_id, unidad=unidad)
    guia = _texto(request, 'guia', 150)
    if guia:
        persona = buscar_persona(guia)
        if persona is None:
            raise ValidationError('No encontramos a esa persona: escribe su usuario institucional, su correo o su cédula.')
        visita.guia = persona
    else:
        visita.guia = None
    visita.observaciones = _texto(request, 'observaciones')
    # El rango de edades solo si el formulario lo trae: uno abierto antes del campo no lo borra.
    if 'rango_edades' in request.POST:
        visita.rango_edades = _texto(request, 'rango_edades', 60)
    visita.save(update_fields=['guia', 'rango_edades', 'observaciones', 'actualizada_en'])
    return visita, 'Visita actualizada', False


def operar_oferta_visitas(request, unidad):
    configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(unidad=unidad)
    configuracion.acepta_visitas = _si(request.POST.get('acepta_visitas'))
    personas = _texto(request, 'personas_por_guia')
    configuracion.personas_por_guia = int(personas) if personas.isdigit() and 1 <= int(personas) <= 60 else 15
    configuracion.visitas_texto = _texto(request, 'visitas_texto')
    configuracion.save(update_fields=['acepta_visitas', 'personas_por_guia', 'visitas_texto'])
    ids = [valor for valor in request.POST.getlist('areas_visitables') if valor.isdigit()]
    EspacioReservable.objects.filter(unidad=unidad).update(visitable=False)
    EspacioReservable.objects.filter(unidad=unidad, pk__in=ids).update(visitable=True)
    return configuracion, 'Oferta de visitas actualizada', False


OPERADORES_VISITAS = {
    'visita': operar_visita,
    'oferta_visitas': operar_oferta_visitas,
}
PERMISOS_VISITAS = {'visita': 'reservas', 'oferta_visitas': 'configuracion'}
MODELOS_VISITAS = {'visita': SolicitudVisita, 'oferta_visitas': ConfiguracionOperativaUnidad}


# ---------------------------------------------------------------- las vistas
@xframe_options_sameorigin
def oferta_visitas_view(request, slug):
    """La oferta pública de visitas, dentro del visor de la ficha o sola."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    oferta = oferta_de_visitas(unidad)
    if not oferta['acepta']:
        raise Http404('La unidad no recibe visitas')
    return render_documento_oficial(request, 'portal/pages/unidades/visitas/oferta.html', {
        'unidad': unidad,
        'oferta': oferta,
        'simuladores': [],
        'simulador': '',
        'referencia': None,
        'volver_url': unidad.get_absolute_url(),
        'generado_en': timezone.localtime(),
        'solicitar_url': reverse('solicitar_visita', args=[unidad.slug]),
    })


@require_http_methods(['GET', 'POST'])
def solicitar_visita_view(request, slug):
    """Los enlaces anteriores abren la tercera ruta del asistente único."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    oferta = oferta_de_visitas(unidad)
    if not oferta['acepta']:
        raise Http404('La unidad no recibe visitas')
    if request.method == 'GET':
        return redirect(f'{unidad.get_absolute_url()}?reserva=visita#reservas-servicios')
    # Quien responde por el grupo actúa a nombre propio: su perfil debe estar al día, como al reservar.
    if request.method == 'POST' and not request.user.is_authenticated:
        return redirect_to_login(request.path)
    if request.user.is_authenticated and not perfil_vigente(request.user):
        messages.warning(request, AVISO_PERFIL)
        return redirect(f"{reverse('profile')}?completar=1")
    # Compatibilidad de envíos anteriores; la interfaz usa /reservas/crear/.
    try:
        visita = crear_visita(unidad, request.user, request.POST)
    except ValidationError as excepcion:
        return JsonResponse({'success': False, 'error': ' '.join(excepcion.messages)}, json_dumps_params={'ensure_ascii': False})
    return redirect(reverse('comprobante_reserva', args=[visita.reserva_id]))


@login_required
@require_http_methods(['GET', 'POST'])
def asistencia_visita_view(request, slug, visita_id):
    """La lista de asistencia de una visita, para la unidad: quién ingresa y quién se suma."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not any(puede_operar_modulo_unidad(request.user, unidad, modulo) for modulo in ('reservas', 'seguridad')):
        raise PermissionDenied('Solo la unidad registra la asistencia de una visita.')
    visita = get_object_or_404(
        SolicitudVisita.objects.select_related('reserva', 'responsable', 'guia').prefetch_related('recorrido'),
        pk=visita_id,
        unidad=unidad,
    )
    if request.method == 'POST':
        registrar_asistencia(visita, request.POST, request.user)
        return redirect(f"{reverse('asistencia_visita', args=[unidad.slug, visita.pk])}?guardado=1")
    return render_documento_oficial(request, 'portal/pages/unidades/visitas/asistencia.html', {
        'unidad': unidad,
        'visita': visita,
        'reserva': visita.reserva,
        'asistentes': list(visita.asistentes.all()),
        'guardado': request.GET.get('guardado') == '1',
        'generado_en': timezone.localtime(),
        'volver_url': reverse('gestion_unidad', args=[unidad.slug]) + '?view=visitas',
    })
