"""Solicitudes de cambio y versiones verificables de una reserva.

La propuesta del solicitante se conserva separada del expediente vigente. Solo
``aplicar_solicitud_cambio`` puede trasladarla a la reserva, dentro de una
transacción y después de volver a validar agenda, recursos e identidades.
"""

import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.translation import gettext

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.reservas.models.reservas import Reserva, ReservaConsumible, RevisionReserva, SolicitudCambioReserva
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo

from apps.reservas.presentation.capacidad import operacion_reservas


CAMPOS_CAMBIO = dict(SolicitudCambioReserva.CAMPOS_CHOICES)

GRUPOS_PROPUESTA = {
    'fecha': 'fecha_horario',
    'hora_inicio': 'fecha_horario',
    'hora_fin': 'fecha_horario',
    'titulo_solicitud': 'actividad',
    'motivo': 'actividad',
    'descripcion_proyecto': 'actividad',
    'requisitos_especiales': 'actividad',
    'numero_participantes': 'participantes',
    'participantes_ids': 'participantes',
    'unidades_ids': 'equipos',
    'software_ids': 'software',
    'espacios_ids': 'espacios',
    'servicios_ids': 'servicios',
    'consumibles': 'insumos',
}

ETIQUETAS_PROPUESTA = {
    'fecha': 'Fecha',
    'hora_inicio': 'Hora de inicio',
    'hora_fin': 'Hora de finalización',
    'titulo_solicitud': 'Título',
    'motivo': 'Motivo o necesidad',
    'descripcion_proyecto': 'Descripción',
    'requisitos_especiales': 'Requisitos especiales',
    'numero_participantes': 'Cantidad de participantes',
    'participantes_ids': 'Participantes identificados',
    'unidades_ids': 'Equipos',
    'software_ids': 'Software',
    'espacios_ids': 'Espacios',
    'servicios_ids': 'Servicios',
    'consumibles': 'Insumos y cantidades',
}


def _ids(values):
    return sorted(int(value) for value in values if value is not None)


def instantanea_reserva(reserva):
    """Devuelve una fotografía estructurada, estable y serializable."""
    unidades = reserva.get_unidades_seleccionadas_list()
    return {
        'fecha': reserva.fecha.isoformat() if reserva.fecha else '',
        'hora_inicio': reserva.hora_inicio.strftime('%H:%M') if reserva.hora_inicio else '',
        'hora_fin': reserva.hora_fin.strftime('%H:%M') if reserva.hora_fin else '',
        'titulo_solicitud': reserva.titulo_solicitud or '',
        'motivo': reserva.motivo or '',
        'descripcion_proyecto': reserva.descripcion_proyecto or '',
        'requisitos_especiales': reserva.requisitos_especiales or '',
        'numero_participantes': reserva.numero_participantes or 1,
        'participantes_ids': _ids(reserva.participantes.values_list('pk', flat=True)),
        'unidades_ids': _ids(
            item.get('id')
            for item in unidades
            if isinstance(item, dict) and item.get('id') is not None
        ),
        'software_ids': _ids(reserva.software_solicitado.values_list('pk', flat=True)),
        'espacios_ids': _ids(reserva.espacios_solicitados.values_list('pk', flat=True)),
        'servicios_ids': _ids(reserva.servicios_solicitados.values_list('pk', flat=True)),
        'equipo_codigo': reserva.equipo_codigo or '',
        'equipo_nombre': reserva.equipo_nombre or '',
        'consumibles': [
            {
                'id': item.consumible_id,
                'cantidad_solicitada': (
                    str(item.cantidad_solicitada)
                    if item.cantidad_solicitada is not None
                    else None
                ),
                'metodo_estimacion': item.metodo_estimacion,
            }
            for item in reserva.consumibles_solicitados.order_by('consumible_id')
        ],
        'participantes_registrados': [
            {
                'usuario_id': item.usuario_id,
                'nombre': item.nombre or '',
                'correo': item.correo or '',
                'rol': item.rol,
                'tipo_usuario': item.tipo_usuario or '',
                'facultad': item.facultad or '',
                'carrera': item.carrera or '',
                'nivel_academico': item.nivel_academico or '',
                'institucion': item.institucion or '',
                'asistencia': item.asistencia,
            }
            for item in reserva.registros_participantes.order_by('rol', 'nombre', 'pk')
        ],
        'adjuntos': [
            {
                'id': item.pk,
                'nombre': item.nombre_original or '',
                'extension': item.extension or '',
                'tamano': item.tamano,
            }
            for item in reserva.archivos_tecnicos.order_by('pk')
        ],
        'proposito_codigo': reserva.proposito_codigo or '',
        'proposito': reserva.proposito or '',
        'modalidad_servicio': reserva.modalidad_servicio or '',
        'provision_consumibles': reserva.provision_consumibles or '',
        'alcance_beneficiario': reserva.alcance_beneficiario or '',
        'entidad_beneficiaria': reserva.entidad_beneficiaria or '',
        'desglose_cotizacion': reserva.desglose_cotizacion or {},
        'costo_estimado': (
            str(reserva.costo_estimado)
            if reserva.costo_estimado is not None
            else None
        ),
        'descuento_aplicado': str(reserva.descuento_aplicado or 0),
        'metodo_pago': reserva.metodo_pago or '',
        'estado': reserva.estado,
        'cotizacion_aceptada': reserva.cotizacion_aceptada,
    }


def asegurar_revision_inicial(reserva, actor=None, motivo=None):
    """Registra una sola vez el punto de partida del expediente."""
    revision = reserva.revisiones.filter(numero=1).first()
    if revision:
        return revision
    return RevisionReserva.objects.create(
        reserva=reserva,
        numero=1,
        tipo='inicial',
        estado_reserva=reserva.estado,
        datos=instantanea_reserva(reserva),
        motivo=(
            motivo
            or 'Registro base antes de la primera solicitud de cambio.'
        ),
        creada_por=actor,
    )


def crear_revision_reserva(reserva, *, tipo, actor=None, motivo=''):
    """Agrega una versión inmutable del estado vigente de la reserva."""
    numero = (
        reserva.revisiones.aggregate(maximo=Max('numero'))['maximo'] or 0
    ) + 1
    return RevisionReserva.objects.create(
        reserva=reserva,
        numero=numero,
        tipo=tipo,
        estado_reserva=reserva.estado,
        datos=instantanea_reserva(reserva),
        motivo=(motivo or '').strip(),
        creada_por=actor,
    )


def diferencias_propuesta(datos_base, propuesta):
    """Lista solo los campos realmente modificados por el solicitante."""
    diferencias = []
    for campo, valor_nuevo in (propuesta or {}).items():
        if campo not in GRUPOS_PROPUESTA:
            continue
        valor_anterior = (datos_base or {}).get(campo)
        if valor_anterior == valor_nuevo:
            continue
        diferencias.append(
            {
                'campo': campo,
                'etiqueta': ETIQUETAS_PROPUESTA.get(campo, campo),
                'anterior': valor_anterior,
                'nuevo': valor_nuevo,
            }
        )
    return diferencias


def _decimal_solicitada(valor, metodo):
    if valor in (None, ''):
        if metodo == 'revision':
            return None
        raise ValidationError('Indica la cantidad solicitada de cada insumo.')
    try:
        cantidad = Decimal(str(valor).replace(',', '.'))
    except InvalidOperation as error:
        raise ValidationError('Una cantidad de insumo no es válida.') from error
    if cantidad <= 0:
        raise ValidationError('Las cantidades de insumos deben ser mayores que cero.')
    return cantidad


def _objetos_propuesta(reserva, datos):
    unidad = reserva.laboratorio
    try:
        unidad_ids = set(_ids(datos.get('unidades_ids', [])))
        software_ids = set(_ids(datos.get('software_ids', [])))
        espacio_ids = set(_ids(datos.get('espacios_ids', [])))
        servicio_ids = set(_ids(datos.get('servicios_ids', [])))
        participante_ids = set(_ids(datos.get('participantes_ids', [])))
    except (TypeError, ValueError) as error:
        raise ValidationError('La propuesta contiene identificadores no válidos.') from error

    unidades = list(
        UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad),
            pk__in=unidad_ids,
            activa=True,
        ).select_related('equipo').distinct()
    )
    software = list(
        SoftwareDisponible.objects.filter(
            unidad=unidad,
            pk__in=software_ids,
            activo=True,
        )
    )
    espacios = list(
        EspacioReservable.objects.filter(
            unidad=unidad,
            pk__in=espacio_ids,
            activo=True,
            reservable=True,
        )
    )
    servicios = list(
        FablabService.objects.filter(
            Q(unidad=unidad) | Q(unidad__isnull=True),
            pk__in=servicio_ids,
            activo=True,
        ).distinct()
    )
    if any(
        (
            len(unidades) != len(unidad_ids),
            len(software) != len(software_ids),
            len(espacios) != len(espacio_ids),
            len(servicios) != len(servicio_ids),
        )
    ):
        raise ValidationError(
            'Algún recurso propuesto ya no está disponible o no pertenece a esta unidad.'
        )

    from apps.reservas.presentation.participantes import validar_participantes

    participantes = validar_participantes(
        json.dumps(sorted(participante_ids)),
        reserva.usuario,
    )
    return unidades, software, espacios, servicios, participantes


def _bloquear_solicitud_cambio(solicitud):
    """Caller atomic: reserva antes de solicitud, como los cierres del panel."""
    # Cargar la unidad despues de esperar ambos bloqueos evita permisos de un
    # JOIN leido con el snapshot anterior a una revocacion concurrente.
    reserva = (Reserva.objects.select_for_update(of=('self',))
               .filter(solicitudes_cambio__pk=solicitud.pk).first())
    if reserva is None:
        raise ValidationError(gettext('La solicitud de cambio ya no está disponible.'), code='no_disponible')
    fresca = (SolicitudCambioReserva.objects.select_for_update(of=('self',))
              .filter(pk=solicitud.pk, reserva=reserva).first())
    if fresca is None:
        raise ValidationError(gettext('La solicitud de cambio ya no está disponible.'), code='no_disponible')
    fresca.reserva = reserva
    return fresca, reserva


@operacion_reservas
@transaction.atomic
def enviar_propuesta_cambio(solicitud, propuesta, *, actor, request=None, unidad_esperada=None):
    """Envia una sola propuesta autorizada sin modificar la reserva vigente."""
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva

    if solicitud._state.db not in {None, 'default'}:
        raise ValidationError(gettext('El envío de propuestas requiere la base de datos principal.'), code='no_disponible')
    alcance = solicitud.reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    solicitud, reserva = _bloquear_solicitud_cambio(solicitud)
    actor = exigir_autoridad_reserva(reserva, actor, operacion='enviar_propuesta', unidad_esperada=alcance)
    if solicitud.solicitada_por_id != actor.pk:
        raise PermissionDenied(gettext('No tienes autorización para modificar esta reserva.'))
    if not solicitud.puede_editar:
        raise ValidationError(gettext('La ventana de edición ya no está disponible.'), code='ventana_cerrada')
    if reserva.estado not in {'pendiente', 'confirmada'}:
        raise ValidationError(gettext('La reserva ya inició o está cerrada; no admite este cambio.'), code='ventana_cerrada')
    permitidos = set(solicitud.campos_autorizados or [])
    if not isinstance(propuesta, dict) or any(
        campo not in GRUPOS_PROPUESTA or GRUPOS_PROPUESTA[campo] not in permitidos
        for campo in propuesta
    ):
        raise ValidationError(gettext('Los campos autorizados cambiaron; vuelve a revisar tu propuesta.'), code='campos_cambiados')
    if not diferencias_propuesta(solicitud.datos_base, propuesta):
        raise ValidationError(gettext('Modifica al menos un dato antes de enviar la propuesta.'))
    solicitud.propuesta = dict(propuesta)
    solicitud.estado = 'enviada'
    solicitud.enviada_en = timezone.now()
    solicitud.save(update_fields=['propuesta', 'estado', 'enviada_en', 'actualizada_en'])
    registrar_auditoria(
        request, unidad=reserva.laboratorio, accion='enviar', objeto=solicitud,
        descripcion='El titular envió una propuesta de cambios para revisión.',
        anteriores=solicitud.datos_base, nuevos=propuesta, usuario=actor)
    return solicitud


@operacion_reservas
@transaction.atomic
def aplicar_solicitud_cambio(solicitud, *, actor, request=None, observacion='', unidad_esperada=None):
    """Valida y aplica una propuesta enviada; devuelve la nueva revisión."""
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    from apps.formacion.presentation.practicas_integracion import sincronizar_planificacion_reserva
    from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
    from apps.reservas.presentation.cotizaciones import recalcular_estimacion_reserva
    from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
    from apps.reservas.presentation.conflictos import validar_conflictos_recursos
    from apps.reservas.presentation.participantes import registrar_participantes
    from apps.reservas.presentation.horarios import validar_horario_operativo

    solicitud, reserva = _bloquear_solicitud_cambio(solicitud)
    exigir_autoridad_reserva(reserva, actor, operacion='aplicar_cambio', unidad_esperada=unidad_esperada)
    if solicitud.estado != 'enviada':
        raise ValidationError('La propuesta todavía no está lista para aprobarse.')
    if reserva.estado not in {'pendiente', 'confirmada'}:
        raise ValidationError(
            'La reserva ya inició o está cerrada; no admite este cambio.'
        )
    permitidos = set(solicitud.campos_autorizados or [])
    propuesta = {
        campo: valor
        for campo, valor in (solicitud.propuesta or {}).items()
        if GRUPOS_PROPUESTA.get(campo) in permitidos
    }
    actual = instantanea_reserva(reserva)
    conflictos_con_base = [
        campo
        for campo in propuesta
        if actual.get(campo) != (solicitud.datos_base or {}).get(campo)
    ]
    if conflictos_con_base:
        nombres = ', '.join(
            ETIQUETAS_PROPUESTA.get(campo, campo) for campo in conflictos_con_base
        )
        raise ValidationError(
            'La reserva cambió mientras se preparaba la propuesta. '
            f'Revisa nuevamente: {nombres}.'
        )
    datos = dict(actual)
    datos.update(propuesta)
    if not diferencias_propuesta(solicitud.datos_base, propuesta):
        raise ValidationError('La propuesta no contiene cambios frente a la reserva vigente.')

    from django.utils.dateparse import parse_date, parse_time

    fecha = parse_date(str(datos.get('fecha') or ''))
    hora_inicio = parse_time(str(datos.get('hora_inicio') or ''))
    hora_fin = parse_time(str(datos.get('hora_fin') or ''))
    try:
        numero_participantes = int(datos.get('numero_participantes') or 1)
    except (TypeError, ValueError) as error:
        raise ValidationError('La cantidad de participantes no es válida.') from error
    if not fecha or not hora_inicio or not hora_fin or hora_inicio >= hora_fin:
        raise ValidationError('Completa una fecha y un horario válidos.')
    if numero_participantes < 1:
        raise ValidationError('Debe registrarse al menos una persona.')

    unidades, software, espacios, servicios, participantes = _objetos_propuesta(
        reserva, datos
    )
    if numero_participantes != 1 + len(participantes):
        numero_participantes = 1 + len(participantes)
    unidades_json = [
        {
            'id': item.pk,
            'codigo': item.codigo_unidad,
            'nombre': item.equipo.nombre,
            'ubicacion': item.ubicacion_especifica or '',
        }
        for item in unidades
    ]
    incluye_espacio = bool(espacios)
    validar_horario_operativo(
        reserva.laboratorio,
        periodo=reserva.periodo,
        semana=None,
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        tipo_solicitud=reserva.tipo_solicitud,
        modalidad_servicio=reserva.modalidad_servicio,
        tipo_usuario=reserva.tipo_usuario_solicitante,
        proposito_codigo=reserva.proposito_codigo,
        es_administrador=True,
        permitir_almuerzo=True,
    )
    validar_conflictos_recursos(
        reserva.laboratorio,
        fecha,
        hora_inicio,
        hora_fin,
        unidades_json,
        software,
        espacios,
        incluye_espacio=incluye_espacio,
        alcance_espacio='areas' if espacios else 'sin_espacio',
        tipo_solicitud=reserva.tipo_solicitud,
        modalidad_servicio=reserva.modalidad_servicio,
        proposito_codigo=reserva.proposito_codigo,
        numero_participantes=numero_participantes,
        bloquear_existentes=True,
        excluir_reserva_id=reserva.pk,
    )

    anterior = instantanea_reserva(reserva)
    reserva.fecha = fecha
    reserva.hora_inicio = hora_inicio
    reserva.hora_fin = hora_fin
    reserva.horas_seleccionadas = json.dumps(
        [f'{hora:02d}:00' for hora in range(hora_inicio.hour, hora_fin.hour)]
    )
    reserva.titulo_solicitud = str(datos.get('titulo_solicitud') or '').strip()
    reserva.motivo = str(datos.get('motivo') or '').strip()
    reserva.descripcion_proyecto = (
        str(datos.get('descripcion_proyecto') or '').strip()
        or 'Sin descripción especificada'
    )
    reserva.requisitos_especiales = str(
        datos.get('requisitos_especiales') or ''
    ).strip()
    reserva.numero_participantes = numero_participantes
    if 'unidades_ids' in propuesta:
        reserva.unidades_seleccionadas = json.dumps(
            unidades_json, ensure_ascii=False
        )
        reserva.solicito_equipo = bool(unidades)
    if 'software_ids' in propuesta:
        reserva.solicito_software = bool(software)
    if 'espacios_ids' in propuesta:
        reserva.solicito_espacio = incluye_espacio
        reserva.incluye_espacio = incluye_espacio
        reserva.alcance_espacio = 'areas' if espacios else 'sin_espacio'
    recursos_modificados = any(
        campo in propuesta
        for campo in ('unidades_ids', 'software_ids', 'espacios_ids', 'servicios_ids')
    )
    if recursos_modificados:
        if unidades:
            reserva.equipo_codigo = unidades[0].codigo_unidad
            reserva.equipo_nombre = unidades[0].equipo.nombre
        elif software:
            reserva.equipo_codigo = 'SOFTWARE'
            reserva.equipo_nombre = software[0].nombre
        elif espacios:
            reserva.equipo_codigo = 'ESPACIOS'
            reserva.equipo_nombre = espacios[0].nombre
        elif servicios:
            reserva.equipo_codigo = 'SERVICIO'
            reserva.equipo_nombre = servicios[0].nombre
        else:
            reserva.equipo_codigo = 'RECURSOS'
            reserva.equipo_nombre = 'Recursos por definir'
    campos_con_impacto_economico = {
        'fecha',
        'hora_inicio',
        'hora_fin',
        'numero_participantes',
        'unidades_ids',
        'software_ids',
        'espacios_ids',
        'servicios_ids',
        'consumibles',
    }
    if campos_con_impacto_economico.intersection(propuesta):
        reserva.cotizacion_aceptada = False
    reserva.full_clean()
    reserva.save()
    if 'software_ids' in propuesta:
        reserva.software_solicitado.set(software)
    if 'espacios_ids' in propuesta:
        reserva.espacios_solicitados.set(espacios)
    if 'servicios_ids' in propuesta:
        reserva.servicios_solicitados.set(servicios)
    if 'participantes_ids' in propuesta or 'numero_participantes' in propuesta:
        reserva.participantes.set(participantes)
        reserva.registros_participantes.all().delete()
        if reserva.usuario_id:
            registrar_participantes(reserva, reserva.usuario, participantes)

    if 'consumibles' in propuesta:
        consumibles = datos.get('consumibles') or []
        consumible_ids = []
        normalizados = []
        metodos = dict(ReservaConsumible.METODO_ESTIMACION_CHOICES)
        for fila in consumibles:
            try:
                consumible_id = int(fila.get('id'))
            except (AttributeError, TypeError, ValueError) as error:
                raise ValidationError('Uno de los insumos no es válido.') from error
            metodo = str(fila.get('metodo_estimacion') or 'estimacion')
            if metodo not in metodos:
                raise ValidationError('El método de estimación no es válido.')
            cantidad = _decimal_solicitada(fila.get('cantidad_solicitada'), metodo)
            if consumible_id in consumible_ids:
                raise ValidationError('No selecciones dos veces el mismo insumo.')
            consumible_ids.append(consumible_id)
            normalizados.append((consumible_id, cantidad, metodo))
        catalogo = {
            item.pk: item
            for item in Consumible.objects.filter(
                unidad=reserva.laboratorio,
                pk__in=consumible_ids,
                activo=True,
                visible_en_reservas=True,
            )
        }
        if len(catalogo) != len(consumible_ids):
            raise ValidationError('Algún insumo ya no está activo en esta unidad.')
        eliminables = reserva.consumibles_solicitados.exclude(
            consumible_id__in=consumible_ids
        )
        if eliminables.filter(
            Q(cantidad_consumida__gt=0) | Q(cantidad_desperdiciada__gt=0)
        ).exists():
            raise ValidationError(
                'No se puede quitar un insumo que ya tiene consumo o desperdicio registrado.'
            )
        eliminables.delete()
        for consumible_id, cantidad, metodo in normalizados:
            registro, _ = ReservaConsumible.objects.update_or_create(
                reserva=reserva,
                consumible_id=consumible_id,
                defaults={
                    'cantidad_solicitada': cantidad,
                    'metodo_estimacion': metodo,
                    'cantidad_aprobada': None,
                },
            )
            registro.full_clean()

    # La estimacion y el comprobante deben reflejar las cantidades aprobadas.
    recalcular_estimacion_reserva(reserva)
    nueva = instantanea_reserva(reserva)
    revision = crear_revision_reserva(
        reserva,
        tipo='cambio_aprobado',
        motivo=observacion or solicitud.motivo_solicitud,
        actor=actor,
    )
    solicitud.estado = 'aprobada'
    solicitud.revisada_por = actor
    solicitud.revisada_en = timezone.now()
    solicitud.observacion_revision = observacion
    solicitud.revision_aplicada = revision
    solicitud.save(
        update_fields=[
            'estado',
            'revisada_por',
            'revisada_en',
            'observacion_revision',
            'revision_aplicada',
            'actualizada_en',
        ]
    )
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion='actualizar',
        objeto=reserva,
        descripcion='Cambio solicitado por el titular, aprobado y aplicado.',
        anteriores=anterior,
        nuevos=nueva,
        usuario=actor,
    )
    sincronizar_planificacion_reserva(reserva, actor=actor)
    notificar_cambio_reserva(
        reserva,
        'cambio_aprobado',
        observacion or 'La propuesta fue validada y ya consta en la reserva vigente.',
    )
    return revision


def cerrar_solicitudes_activas(reserva, *, motivo, actor=None):
    """Cancela la solicitud de cambio activa cuando la reserva ya no admite cambios.

    Sin esto, una reserva cancelada o cerrada conservaba una solicitud en
    "solicitada", "autorizada" o "enviada": el panel seguia ofreciendo
    autorizarla y el titular veia una gestion pendiente sobre algo terminado.
    """
    activas = SolicitudCambioReserva.objects.filter(
        reserva=reserva,
        estado__in=SolicitudCambioReserva.ESTADOS_ACTIVOS,
    )
    return activas.update(
        estado='cancelada',
        observacion_revision=str(motivo or '')[:500],
        revisada_por=actor,
        revisada_en=timezone.now(),
    )


# Nombre publico de la validacion de cantidades: el editor de la propuesta la
# aplica al enviar, con el mismo criterio que la aplicacion final.
cantidad_insumo_normalizada = _decimal_solicitada


def _fecha_legible(valor):
    try:
        return date.fromisoformat(str(valor)).strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return str(valor or '')


def describir_diferencias(reserva, datos_base, propuesta):
    """Diferencias con nombres legibles para el titular y el laboratorio.

    ``diferencias_propuesta`` compara identificadores. Aqui se traducen a
    nombres de equipos, software, espacios, servicios, personas e insumos para
    que quien lee la propuesta no vea listas de numeros.
    """
    cambios = diferencias_propuesta(datos_base, propuesta)
    if not cambios:
        return []
    claves_ids = (
        'unidades_ids', 'software_ids', 'espacios_ids', 'servicios_ids',
        'participantes_ids',
    )
    ids = {clave: set() for clave in claves_ids}
    consumible_ids = set()
    for cambio in cambios:
        for lado in ('anterior', 'nuevo'):
            valor = cambio.get(lado)
            if not isinstance(valor, (list, tuple)):
                continue
            if cambio['campo'] in ids:
                ids[cambio['campo']].update(int(v) for v in valor if v is not None)
            elif cambio['campo'] == 'consumibles':
                consumible_ids.update(
                    int(fila['id']) for fila in valor
                    if isinstance(fila, dict) and fila.get('id') is not None
                )
    nombres = {
        'unidades_ids': {
            item.pk: f'{item.codigo_unidad} · {item.equipo.nombre}'
            for item in UnidadEquipo.objects.filter(
                pk__in=ids['unidades_ids']
            ).select_related('equipo')
        },
        'software_ids': {
            item.pk: item.nombre
            for item in SoftwareDisponible.objects.filter(pk__in=ids['software_ids'])
        },
        'espacios_ids': {
            item.pk: item.nombre
            for item in EspacioReservable.objects.filter(pk__in=ids['espacios_ids'])
        },
        'servicios_ids': {
            item.pk: item.nombre
            for item in FablabService.objects.filter(pk__in=ids['servicios_ids'])
        },
        'participantes_ids': {
            item.pk: item.get_full_name() or item.get_username()
            for item in get_user_model().objects.filter(pk__in=ids['participantes_ids'])
        },
    }
    consumibles = {
        item.pk: item for item in Consumible.objects.filter(pk__in=consumible_ids)
    }
    metodos = dict(ReservaConsumible.METODO_ESTIMACION_CHOICES)

    def legible(campo, valor):
        if campo == 'fecha':
            return _fecha_legible(valor)
        if campo in nombres:
            if not valor:
                return 'Ninguno'
            return ', '.join(nombres[campo].get(int(v), f'#{v}') for v in valor)
        if campo == 'consumibles':
            if not valor:
                return 'Ninguno'
            partes = []
            for fila in valor:
                if not isinstance(fila, dict):
                    continue
                consumible = consumibles.get(int(fila.get('id') or 0))
                nombre = consumible.nombre if consumible else f"#{fila.get('id')}"
                cantidad = fila.get('cantidad_solicitada')
                unidad_medida = (consumible.unidad_medida if consumible else '') or 'unidades'
                metodo = metodos.get(
                    fila.get('metodo_estimacion'), fila.get('metodo_estimacion') or ''
                )
                if cantidad in (None, ''):
                    texto = f'{nombre}: cantidad por definir'
                else:
                    texto = f'{nombre}: {cantidad} {unidad_medida}'
                if metodo:
                    texto += f' ({metodo})'
                partes.append(texto)
            return '; '.join(partes) or 'Ninguno'
        if valor in (None, ''):
            return 'Sin registrar'
        return str(valor)

    return [
        {
            'campo': cambio['campo'],
            'etiqueta': cambio['etiqueta'],
            'anterior': legible(cambio['campo'], cambio['anterior']),
            'nuevo': legible(cambio['campo'], cambio['nuevo']),
        }
        for cambio in cambios
    ]
