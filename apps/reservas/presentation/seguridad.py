"""Seguridad industrial y acceso: lo que la unidad exige y quién lo cumple.

La unidad declara requisitos por categoría de persona; cada persona acumula
habilitaciones vigentes; la solicitud avisa lo pendiente; la aprobación
respeta el aforo del área más pequeña; el inicio exige el registro de
ingreso; y una sesión de inducción cerrada habilita a quienes asistieron.
Un laboratorio sin requisitos no cambia en nada.
"""

import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time

from apps.recursos.models.consumibles import Consumible
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso
from apps.reservas.models.reservas import Reserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.reservas.models.seguridad import CATEGORIAS_PERSONA, CLAVES_CATEGORIA

from apps.formacion.presentation.practicas_integracion import DocumentacionReservaPendiente, validar_compuerta_documental

NOMBRES_CATEGORIA = dict(CATEGORIAS_PERSONA)
CATEGORIA_POR_TIPO_USUARIO = {
    'estudiante': 'estudiante',
    'docente': 'docente',
    'investigador': 'docente',
    'administrativo': 'personal',
    'egresado': 'externo',
    'externo': 'externo',
}
MARCADO = {'1', 'on', 'true'}


# ------------------------------------------------------------ las personas
def categoria_de(tipo_usuario, *, es_personal=False):
    """La categoría de acceso de una persona según su tipo institucional."""
    if es_personal:
        return 'personal'
    return CATEGORIA_POR_TIPO_USUARIO.get(tipo_usuario or '', 'externo')


def _ids_personal(unidad):
    ids = set(
        ResponsableUnidad.objects.filter(unidad=unidad, activo=True, usuario__isnull=False)
        .values_list('usuario_id', flat=True)
    )
    if unidad.administrador_id:
        ids.add(unidad.administrador_id)
    return ids


def categoria_de_usuario(usuario, unidad):
    if not usuario or not getattr(usuario, 'is_authenticated', False):
        return 'externo'
    if usuario.pk in _ids_personal(unidad):
        return 'personal'
    perfil = getattr(usuario, 'profile', None)
    return categoria_de(getattr(perfil, 'tipo_usuario', ''))


def buscar_persona(texto):
    """Una persona por su usuario institucional, su correo o su cédula."""
    texto = (texto or '').strip()
    if not texto:
        return None
    return (
        get_user_model().objects.filter(
            Q(username__iexact=texto) | Q(email__iexact=texto) | Q(profile__cedula=texto)
        )
        .order_by('pk')
        .first()
    )


# ------------------------------------------------------------ los requisitos
def requisitos_de(unidad, categoria=None):
    """Los requisitos activos de la unidad, o solo los que aplican a una categoría."""
    requisitos = (
        RequisitoAcceso.objects.filter(unidad=unidad, activo=True)
        .select_related('consumible')
        .order_by('orden', 'nombre')
    )
    return [requisito for requisito in requisitos if categoria is None or requisito.aplica(categoria)]


def controla_acceso(unidad):
    """Una unidad controla el acceso cuando exige algo obligatorio para entrar."""
    return RequisitoAcceso.objects.filter(unidad=unidad, activo=True, obligatorio=True).exists()


def resumen_requisitos(unidad):
    """La lista pública de la ficha: qué se exige y a quién."""
    return [
        {
            'nombre': requisito.nombre,
            'tipo': requisito.tipo,
            'tipo_display': requisito.get_tipo_display(),
            'aplica_display': requisito.categorias_display,
            'obligatorio': requisito.obligatorio,
            'vigencia_dias': requisito.vigencia_dias,
            'descripcion': requisito.descripcion,
        }
        for requisito in requisitos_de(unidad)
    ]


def proteccion_por_persona(unidad, categoria, personas):
    """La protección que la unidad entrega del inventario, multiplicada por persona."""
    filas = []
    for requisito in requisitos_de(unidad, categoria):
        if requisito.tipo == 'proteccion' and requisito.consumible_id and requisito.consumible.activo:
            filas.append({
                'requisito': requisito,
                'consumible': requisito.consumible,
                'cantidad': requisito.cantidad_por_persona * personas,
            })
    return filas


# ----------------------------------------------------------- el estado de cada quien
def _habilitacion_vigente(usuario, requisito, fecha):
    if usuario is None:
        return None
    habilitaciones = HabilitacionAcceso.objects.filter(
        usuario=usuario, requisito=requisito, activa=True
    ).order_by('-fecha', '-pk')
    return next((habilitacion for habilitacion in habilitaciones if habilitacion.vigente_en(fecha)), None)


def estado_de_persona(unidad, usuario, categoria, fecha=None):
    """Cada requisito que aplica a la persona y en qué está para esa fecha."""
    fecha = fecha or timezone.localdate()
    filas = []
    for requisito in requisitos_de(unidad, categoria):
        fila = {
            'id': requisito.pk,
            'codigo': requisito.codigo,
            'nombre': requisito.nombre,
            'tipo': requisito.tipo,
            'tipo_display': requisito.get_tipo_display(),
            'obligatorio': requisito.obligatorio,
            'momento': requisito.momento,
            'descripcion': requisito.descripcion,
        }
        if requisito.habilitable:
            habilitacion = _habilitacion_vigente(usuario, requisito, fecha)
            if habilitacion is None:
                fila.update(
                    estado='pendiente',
                    vence='',
                    detalle=(
                        'Sin inducción vigente: la unidad la programa'
                        if requisito.tipo == 'induccion'
                        else 'Sin documento vigente registrado'
                    ),
                )
            else:
                fila.update(
                    estado='vigente',
                    vence=habilitacion.vence.isoformat() if habilitacion.vence else '',
                    detalle=(
                        f'Vigente hasta {habilitacion.vence:%d/%m/%Y}'
                        if habilitacion.vence
                        else 'Vigente sin vencimiento'
                    ),
                )
        else:
            fila.update(estado='ingreso', vence='', detalle='Se verifica al ingresar')
        filas.append(fila)
    return filas


def acceso_de_usuario(unidad, usuario, fecha=None):
    """Lo que la unidad exige a quien va a solicitar, con su estado."""
    categoria = categoria_de_usuario(usuario, unidad)
    autenticado = usuario if getattr(usuario, 'is_authenticated', False) else None
    requisitos = estado_de_persona(unidad, autenticado, categoria, fecha)
    return {
        'controlado': bool(requisitos),
        'categoria': categoria,
        'categoria_display': NOMBRES_CATEGORIA[categoria],
        'requisitos': requisitos,
        'pendientes': [fila['nombre'] for fila in requisitos if fila['obligatorio'] and fila['estado'] == 'pendiente'],
    }


def pendientes_al_reservar(unidad, usuario, fecha=None):
    """Lo obligatorio que la persona aún no cumple y que la unidad pide al reservar."""
    acceso = acceso_de_usuario(unidad, usuario, fecha)
    return [
        fila['nombre']
        for fila in acceso['requisitos']
        if fila['obligatorio'] and fila['momento'] == 'reservar' and fila['estado'] == 'pendiente'
    ]


# ------------------------------------------------------------- la sesión
def aforo_de(reserva):
    """El área más pequeña de la reserva frente a las personas declaradas."""
    espacios = list(reserva.espacios_solicitados.all())
    if not espacios:
        return None
    menor = min(espacios, key=lambda espacio: espacio.capacidad)
    personas = reserva.numero_participantes or 1
    return {
        'espacio': menor.nombre,
        'capacidad': menor.capacidad,
        'personas': personas,
        'excede': personas > menor.capacidad,
    }


def es_induccion(reserva):
    return reserva.proposito_codigo == 'capacitacion' and reserva.subtipo_actividad == 'induccion'


def acceso_de_reserva(reserva):
    """Persona por persona: requisitos, pendientes e ingreso registrado."""
    unidad = reserva.laboratorio
    requisitos = requisitos_de(unidad)
    acceso = {
        'controlado': False,
        'obligatorio': False,
        'reserva_id': reserva.pk,
        'codigo': reserva.codigo_reserva or f'RES-{reserva.pk:06d}',
        'estado': reserva.estado,
        'puede_registrar': reserva.estado in {'confirmada', 'en_proceso'},
        'requisitos': [],
        'personas': [],
        'pendientes': 0,
        'ingresados': 0,
        'sin_registro': 0,
        'aforo': None,
        'listo': True,
    }
    if not requisitos:
        return acceso
    personal = _ids_personal(unidad)
    ingresos = {ingreso.participante_id: ingreso for ingreso in reserva.ingresos.all()}
    induccion = es_induccion(reserva)
    personas = []
    for registro in reserva.registros_participantes.select_related('usuario').order_by('rol', 'nombre'):
        categoria = categoria_de(registro.tipo_usuario, es_personal=registro.usuario_id in personal)
        filas = estado_de_persona(unidad, registro.usuario, categoria, reserva.fecha)
        # A la inducción se viene sin inducción: eso no bloquea la entrada.
        pendientes = [
            fila['nombre']
            for fila in filas
            if fila['obligatorio'] and fila['estado'] == 'pendiente' and not (induccion and fila['tipo'] == 'induccion')
        ]
        ingreso = ingresos.get(registro.pk)
        personas.append({
            'participante_id': registro.pk,
            'usuario_id': registro.usuario_id,
            'nombre': registro.nombre,
            'rol': registro.get_rol_display(),
            'categoria': categoria,
            'categoria_display': NOMBRES_CATEGORIA[categoria],
            'requisitos': filas,
            'pendientes': pendientes,
            'ingreso': None if ingreso is None else {
                'ingresa': ingreso.ingresa,
                'motivo': ingreso.motivo,
                'hora_ingreso': ingreso.hora_ingreso.strftime('%H:%M') if ingreso.hora_ingreso else '',
                'hora_salida': ingreso.hora_salida.strftime('%H:%M') if ingreso.hora_salida else '',
                'proteccion_verificada': ingreso.proteccion_verificada,
                'restricciones_verificadas': ingreso.restricciones_verificadas,
                'pendientes': ingreso.pendientes,
            },
        })
    obligatorio = any(requisito.obligatorio for requisito in requisitos)
    ingresados = sum(1 for persona in personas if persona['ingreso'] and persona['ingreso']['ingresa'])
    acceso.update(
        controlado=True,
        obligatorio=obligatorio,
        requisitos=[
            {
                'id': requisito.pk,
                'nombre': requisito.nombre,
                'tipo': requisito.tipo,
                'tipo_display': requisito.get_tipo_display(),
                'obligatorio': requisito.obligatorio,
                'aplica_display': requisito.categorias_display,
            }
            for requisito in requisitos
        ],
        personas=personas,
        pendientes=sum(1 for persona in personas if persona['pendientes']),
        ingresados=ingresados,
        sin_registro=sum(1 for persona in personas if not persona['ingreso']),
        aforo=aforo_de(reserva),
        listo=(not obligatorio) or ingresados > 0,
    )
    return acceso


def validar_aforo(reserva):
    """Al aprobar en una unidad con control de acceso, nadie sobra en el área más pequeña."""
    if not controla_acceso(reserva.laboratorio):
        return
    aforo = aforo_de(reserva)
    if aforo and aforo['excede']:
        raise ValueError(
            f"El aforo de {aforo['espacio']} es de {aforo['capacidad']} personas y la reserva "
            f"declara {aforo['personas']}. Reduce el grupo o divide la sesión."
        )


def validar_inicio(reserva):
    """En una unidad con control de acceso, la sesión empieza con el ingreso registrado."""
    if not controla_acceso(reserva.laboratorio):
        return
    from apps.reservas.presentation.visitas import asistencia_registrada

    # Una visita empieza con su lista de asistencia; el grupo no tiene cuenta.
    if asistencia_registrada(reserva):
        return
    if acceso_de_reserva(reserva)['ingresados'] == 0:
        raise ValueError(
            'Registra el ingreso de las personas (habilitaciones, protección y restricciones) '
            'antes de iniciar la sesión.'
        )


def registrar_ingresos(reserva, usuario, datos):
    """El control de la puerta, persona por persona: solo entra quien cumple."""
    acceso = acceso_de_reserva(reserva)
    if not acceso['controlado']:
        raise ValidationError('Esta unidad no exige requisitos de ingreso.')
    personas = {persona['participante_id']: persona for persona in acceso['personas']}
    registros = {registro.pk: registro for registro in reserva.registros_participantes.all()}
    ids = [int(valor) for valor in (datos.get('personas_ids') or '').split(',') if valor.strip().isdigit()]
    if not ids:
        raise ValidationError('No hay personas identificadas en esta sesión.')
    creados = 0
    for participante_id in ids:
        persona = personas.get(participante_id)
        registro = registros.get(participante_id)
        if persona is None or registro is None:
            raise ValidationError('Una de las personas ya no pertenece a esta sesión.')
        prefijo = f'persona_{participante_id}_'
        ingresa = (datos.get(prefijo + 'ingresa') or '') in MARCADO
        proteccion = (datos.get(prefijo + 'proteccion') or '') in MARCADO
        restricciones = (datos.get(prefijo + 'restricciones') or '') in MARCADO
        motivo = (datos.get(prefijo + 'motivo') or '').strip()[:200]
        hora_texto = (datos.get(prefijo + 'hora') or '').strip()
        hora = parse_time(hora_texto) if hora_texto else None
        faltan = list(persona['pendientes'])
        exige_proteccion = any(fila['tipo'] == 'proteccion' and fila['obligatorio'] for fila in persona['requisitos'])
        exige_restricciones = any(fila['tipo'] == 'restriccion' and fila['obligatorio'] for fila in persona['requisitos'])
        if exige_proteccion and not proteccion:
            faltan.append('protección personal verificada')
        if exige_restricciones and not restricciones:
            faltan.append('restricciones de ingreso verificadas')
        if ingresa and faltan:
            raise ValidationError(
                f"{persona['nombre']} no puede ingresar: falta {'; '.join(faltan)}. "
                'Regístrala como «no ingresa» con el motivo, o completa lo que falta.'
            )
        if not ingresa and not motivo:
            raise ValidationError(f"Indica por qué {persona['nombre']} no ingresa.")
        _, creado = RegistroIngreso.objects.update_or_create(
            reserva=reserva,
            participante=registro,
            defaults={
                'usuario': registro.usuario,
                'nombre': registro.nombre,
                'categoria': persona['categoria'],
                'ingresa': ingresa,
                'motivo': motivo,
                'hora_ingreso': hora if ingresa else None,
                'proteccion_verificada': proteccion,
                'restricciones_verificadas': restricciones,
                'habilitaciones_vigentes': not persona['pendientes'],
                'pendientes': faltan if not ingresa else [],
                'registrado_por': usuario,
            },
        )
        creados += int(creado)
    return creados, len(ids)


def otorgar_habilitaciones_por_sesion(reserva, usuario):
    """Una sesión de inducción cerrada habilita a quienes asistieron."""
    if not es_induccion(reserva):
        return 0
    requisitos = [requisito for requisito in requisitos_de(reserva.laboratorio) if requisito.tipo == 'induccion']
    if not requisitos:
        return 0
    personal = _ids_personal(reserva.laboratorio)
    otorgadas = 0
    asistentes = reserva.registros_participantes.filter(asistencia='asistio', usuario__isnull=False).select_related('usuario')
    for registro in asistentes:
        categoria = categoria_de(registro.tipo_usuario, es_personal=registro.usuario_id in personal)
        for requisito in requisitos:
            if not requisito.aplica(categoria):
                continue
            if HabilitacionAcceso.objects.filter(usuario=registro.usuario, requisito=requisito, reserva=reserva).exists():
                continue
            HabilitacionAcceso.objects.create(
                usuario=registro.usuario,
                requisito=requisito,
                fecha=reserva.fecha,
                origen='sesion',
                reserva=reserva,
                otorgada_por=usuario,
                observaciones=f'Inducción {reserva.codigo_reserva or reserva.pk}: {reserva.titulo_solicitud}',
            )
            otorgadas += 1
    return otorgadas


# --------------------------------------------------------------- el panel
def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def operar_requisito_acceso(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(RequisitoAcceso.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id
        else RequisitoAcceso(unidad=unidad)
    )
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el requisito que quieres desactivar.')
        objeto.activo = False
        objeto.save(update_fields=['activo'])
        return objeto, 'Requisito desactivado', False
    objeto.codigo = _texto(request, 'codigo', 30).upper()
    objeto.nombre = _texto(request, 'nombre', 120)
    objeto.tipo = _texto(request, 'tipo', 12)
    objeto.aplica_a = [clave for clave in request.POST.getlist('aplica_a') if clave in CLAVES_CATEGORIA]
    objeto.obligatorio = _texto(request, 'obligatorio') in MARCADO
    objeto.momento = _texto(request, 'momento', 12) or 'reservar'
    vigencia = _texto(request, 'vigencia_dias')
    objeto.vigencia_dias = int(vigencia) if vigencia.isdigit() and int(vigencia) > 0 else None
    consumible_id = _texto(request, 'consumible_id')
    objeto.consumible = get_object_or_404(Consumible, pk=consumible_id, unidad=unidad) if consumible_id else None
    try:
        objeto.cantidad_por_persona = Decimal(_texto(request, 'cantidad_por_persona') or '1')
    except InvalidOperation as error:
        raise ValidationError('La cantidad por persona no es válida.') from error
    objeto.descripcion = _texto(request, 'descripcion')
    orden = _texto(request, 'orden')
    objeto.orden = int(orden) if orden.isdigit() else 0
    objeto.activo = True
    objeto.full_clean()
    objeto.save()
    return objeto, 'Requisito creado' if creado else 'Requisito actualizado', creado


def operar_habilitacion_acceso(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if registro_id:
        objeto = get_object_or_404(
            HabilitacionAcceso.objects.select_for_update(), pk=registro_id, requisito__unidad=unidad
        )
        if _texto(request, 'accion') != 'desactivar':
            raise ValidationError('Una habilitación no se edita: retírala y registra la nueva.')
        objeto.activa = False
        objeto.save(update_fields=['activa'])
        return objeto, 'Habilitación retirada', False
    requisito_id = _texto(request, 'requisito_id')
    if not requisito_id:
        raise ValidationError('Selecciona el requisito que se habilita.')
    requisito = get_object_or_404(RequisitoAcceso, pk=requisito_id, unidad=unidad, activo=True)
    if not requisito.habilitable:
        raise ValidationError('La protección y las restricciones se verifican al ingresar; no se habilitan por persona.')
    persona = buscar_persona(_texto(request, 'persona', 150))
    if persona is None:
        raise ValidationError('No encontramos a esa persona: escribe su usuario institucional, su correo o su cédula.')
    fecha_texto = _texto(request, 'fecha')
    vence_texto = _texto(request, 'vence')
    objeto = HabilitacionAcceso(
        usuario=persona,
        requisito=requisito,
        fecha=(parse_date(fecha_texto) if fecha_texto else None) or timezone.localdate(),
        vence=parse_date(vence_texto) if vence_texto else None,
        origen=_texto(request, 'origen', 12) or 'manual',
        documento=_texto(request, 'documento', 120),
        otorgada_por=request.user,
        observaciones=_texto(request, 'observaciones'),
    )
    objeto.full_clean()
    objeto.save()
    return objeto, f'Habilitación registrada para {persona.get_full_name() or persona.get_username()}', True


def operar_ingreso(request, unidad):
    if _texto(request, 'registro_id') or _texto(request, 'accion') == 'desactivar':
        raise ValidationError('El registro de ingreso se corrige volviendo a registrarlo, no se borra.')
    reserva_id = _texto(request, 'reserva_id')
    if not reserva_id:
        raise ValidationError('Selecciona la sesión.')
    reserva = get_object_or_404(Reserva.objects.select_for_update(), pk=reserva_id, laboratorio=unidad)
    if reserva.estado not in {'confirmada', 'en_proceso'}:
        raise ValidationError('El ingreso se registra en una sesión aprobada o en curso.')
    # Sin la guía de la sesión aprobada no se ejecuta: tampoco se registra el ingreso.
    try:
        validar_compuerta_documental(reserva, 'iniciar')
    except DocumentacionReservaPendiente as error:
        raise ValidationError(f'No se registra el ingreso: {error}') from error
    _, total = registrar_ingresos(reserva, request.user, request.POST)
    return reserva, f'Ingreso registrado para {total} persona{"" if total == 1 else "s"}', False


OPERADORES_SEGURIDAD = {
    'requisito_acceso': operar_requisito_acceso,
    'habilitacion_acceso': operar_habilitacion_acceso,
    'ingreso': operar_ingreso,
}
PERMISOS_SEGURIDAD = {clave: 'seguridad' for clave in OPERADORES_SEGURIDAD}
MODELOS_SEGURIDAD = {
    'requisito_acceso': RequisitoAcceso,
    'habilitacion_acceso': HabilitacionAcceso,
    'ingreso': Reserva,
}


def personas_para_formulario(acceso):
    """Lo que el cajón de ingreso necesita de cada persona, sin el detalle completo."""
    return [
        {
            'participante_id': persona['participante_id'],
            'nombre': persona['nombre'],
            'rol': persona['rol'],
            'categoria_display': persona['categoria_display'],
            'pendientes': persona['pendientes'],
            'ingreso': persona['ingreso'],
        }
        for persona in acceso['personas']
    ]


def contexto_seguridad(unidad, permisos_operativos):
    puede = bool(permisos_operativos.get('seguridad'))
    hoy = timezone.localdate()
    requisitos = list(
        RequisitoAcceso.objects.filter(unidad=unidad)
        .select_related('consumible')
        .order_by('-activo', 'orden', 'nombre')
    )
    for requisito in requisitos:
        requisito.aplica_a_csv = ','.join(requisito.aplica_a)
    habilitaciones = list(
        HabilitacionAcceso.objects.filter(requisito__unidad=unidad, activa=True)
        .select_related('usuario', 'requisito', 'otorgada_por')
        .order_by('-fecha', '-pk')[:60]
    )
    for habilitacion in habilitaciones:
        habilitacion.vigente = habilitacion.vigente_en(hoy)
        habilitacion.por_vencer = bool(habilitacion.vence and hoy <= habilitacion.vence <= hoy + timedelta(days=30))
    sesiones = list(
        Reserva.objects.filter(
            laboratorio=unidad,
            estado__in=('confirmada', 'en_proceso'),
            fecha__range=(hoy, hoy + timedelta(days=7)),
        )
        .select_related('usuario')
        .order_by('fecha', 'hora_inicio', 'pk')
    ) if requisitos else []
    for sesion in sesiones:
        sesion.acceso = acceso_de_reserva(sesion)
        sesion.personas_json = json.dumps(personas_para_formulario(sesion.acceso), ensure_ascii=False)
    vigentes = HabilitacionAcceso.objects.filter(
        requisito__unidad=unidad, activa=True, fecha__lte=hoy
    ).filter(Q(vence__isnull=True) | Q(vence__gte=hoy))
    metricas = {
        'requisitos_activos': sum(1 for requisito in requisitos if requisito.activo),
        'obligatorios': sum(1 for requisito in requisitos if requisito.activo and requisito.obligatorio),
        'habilitaciones_vigentes': vigentes.count(),
        'por_vencer': vigentes.filter(vence__lte=hoy + timedelta(days=30)).count(),
        'sesiones_por_registrar': sum(1 for sesion in sesiones if sesion.acceso['sin_registro']),
    }
    return {
        'seguridad_habilitada': puede,
        'puede_operar_seguridad': puede,
        'seguridad_metricas': metricas,
        'requisitos_acceso': requisitos,
        'requisitos_habilitables': [requisito for requisito in requisitos if requisito.activo and requisito.habilitable],
        'habilitaciones_acceso': habilitaciones,
        'sesiones_acceso': sesiones,
        'tipos_requisito': RequisitoAcceso.TIPOS,
        'momentos_requisito': RequisitoAcceso.MOMENTOS,
        'categorias_persona': CATEGORIAS_PERSONA,
        'origenes_habilitacion': HabilitacionAcceso.ORIGENES,
        'consumibles_proteccion': Consumible.objects.filter(unidad=unidad, activo=True).order_by('clasificacion', 'nombre'),
        'hoy_seguridad': hoy,
    }
