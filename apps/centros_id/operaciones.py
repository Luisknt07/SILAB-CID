"""Confirmación transaccional de recursos propios y seguimiento de atención.

Los motores de las unidades vinculadas conservan sus operaciones y permisos.
"""
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import router, transaction
from django.utils import timezone

from .escenarios import contenido_admitido
from .identidades import identidad_de

ACTIVOS = ('aprobada', 'ejecucion')


def validar_recurso(objeto):
    if bool(objeto.zona_id) == bool(objeto.equipo_id):
        raise ValidationError('Seleccione exactamente un espacio o un equipo.')
    recurso = objeto.zona or objeto.equipo
    centro_id = recurso.centro_id if objeto.zona_id else recurso.componente.centro_id
    if objeto.centro_id and centro_id != objeto.centro_id:
        raise ValidationError('El recurso debe pertenecer al centro.')


def validar_solicitud(s):
    from .models import HabilitacionEquipo, SesionAcompanamiento, SolicitudCentro

    if s.equipo_id and s.equipo.componente.centro_id != s.centro_id:
        raise ValidationError({'equipo': 'El equipo debe pertenecer al centro.'})
    for inicio, fin, campo in ((s.inicio_preferido, s.fin_preferido, 'fin_preferido'),
                               (s.inicio_reservado, s.fin_reservado, 'fin_reservado')):
        if bool(inicio) != bool(fin) or (inicio and fin <= inicio):
            raise ValidationError({campo: 'Indique inicio y fin; el final debe ser posterior al inicio.'})
    if s.servicio_id and s.estado in ('recibida', 'evaluacion', *ACTIVOS):
        if not s.servicio.solicitable:
            raise ValidationError({'servicio': 'El servicio no recibe solicitudes actualmente.'})
        if s.perfil == 'externo' and s.servicio.usuarios == 'internos':
            raise ValidationError({'servicio': 'Este servicio está dirigido a la comunidad universitaria.'})
        if s.perfil == 'interno' and s.servicio.usuarios == 'externos':
            raise ValidationError({'servicio': 'Este servicio está dirigido a usuarios externos.'})
    if s.tipo == 'asesoria' and s.estado in ACTIVOS:
        if not (s.responsable_atencion_id and s.diagnostico.strip() and s.plan.strip()):
            raise ValidationError('El acompañamiento aprobado requiere responsable, diagnóstico y plan.')
    if s.estado == 'cerrada' and s.tipo == 'asesoria' and not s.evaluacion_cierre.strip():
        raise ValidationError({'evaluacion_cierre': 'Registre la evaluación y el motivo del cierre.'})
    for persona in (s.supervisor, s.responsable_atencion):
        if persona and (not persona.vigente or not contenido_admitido(persona)):
            raise ValidationError('La persona de atención debe estar vigente y ser un registro institucional.')
    if s.estado not in ACTIVOS:
        return
    if s.tipo == 'uso' and not (s.zona_id or s.equipo_id):
        raise ValidationError('La confirmación de acceso necesita un recurso concreto.')
    if not (s.zona_id or s.equipo_id):
        return
    if not (s.inicio_reservado and s.fin_reservado):
        raise ValidationError('Confirme el intervalo de uso del recurso.')
    if not (s.requisitos_validados and s.evidencia_requisitos.strip()):
        raise ValidationError('Compruebe y documente los requisitos antes de confirmar el acceso.')
    inicio, fin = s.inicio_reservado, s.fin_reservado
    for campo in ('zona', 'equipo'):
        recurso = getattr(s, campo)
        if recurso is None:
            continue
        if not recurso.apto_reserva:
            raise ValidationError({campo: 'El recurso no está habilitado para reservas.'})
        if campo == 'zona' and (not s.participantes or s.participantes > recurso.aforo):
            raise ValidationError({'participantes': 'Indique participantes dentro del aforo autorizado.'})
        margen = timedelta(minutes=recurso.margen_minutos)
        desde, hasta = timezone.localtime(inicio - margen), timezone.localtime(fin + margen)
        if desde.date() != hasta.date() or not recurso.horarios.filter(
                dia=desde.weekday(), abre__lte=desde.time(), cierra__gte=hasta.time()).exists():
            raise ValidationError({'inicio_reservado': 'El intervalo, incluida preparación y cierre, queda fuera del horario autorizado.'})
        if recurso.bloqueos.filter(inicio__lt=fin + margen, fin__gt=inicio - margen).exists():
            raise ValidationError({campo: 'El recurso tiene un bloqueo en ese intervalo.'})
        if SolicitudCentro.objects.filter(**{campo: recurso}, estado__in=ACTIVOS,
                inicio_reservado__lt=fin + 2 * margen, fin_reservado__gt=inicio - 2 * margen).exclude(pk=s.pk).exists():
            raise ValidationError({'inicio_reservado': 'El recurso ya está asignado en ese intervalo.'})
    if s.equipo_id:
        if s.equipo.calibracion_requerida and s.equipo.calibracion_hasta < timezone.localtime(fin).date():
            raise ValidationError({'equipo': 'La calibración no cubre el día de uso solicitado.'})
        if s.equipo.requiere_supervision and not s.supervisor_id:
            raise ValidationError({'supervisor': 'Asigne supervisión para este equipo.'})
        if s.equipo.requiere_induccion and not HabilitacionEquipo.objects.filter(
                equipo=s.equipo, usuario_id=s.usuario_id, revocada=False,
                desde__lte=timezone.localtime(inicio).date(), hasta__gte=timezone.localtime(fin).date()).exists():
            raise ValidationError({'equipo': 'El solicitante necesita habilitación vigente para este equipo.'})
    if s.supervisor_id:
        if SolicitudCentro.objects.filter(supervisor_id=s.supervisor_id, estado__in=ACTIVOS,
                inicio_reservado__lt=fin, fin_reservado__gt=inicio).exclude(pk=s.pk).exists():
            raise ValidationError({'supervisor': 'La persona asignada ya supervisa otro uso en ese horario.'})
        if SesionAcompanamiento.objects.filter(responsable_id=s.supervisor_id, estado='programada',
                                               inicio__lt=fin, fin__gt=inicio).exists():
            raise ValidationError({'supervisor': 'La persona asignada tiene una sesión en ese horario.'})


def guardar_solicitud(s, persistir, actor, motivo):
    from .models import EquipoCentro, Integrante, RegistroSolicitud, SolicitudCentro, Zona

    with transaction.atomic(using=router.db_for_write(type(s))):
        anterior = SolicitudCentro.objects.select_for_update().filter(pk=s.pk).first() if s.pk else None
        if anterior and (anterior.centro_id != s.centro_id or anterior.usuario_id != s.usuario_id):
            raise ValidationError('El centro y el solicitante de un expediente no se pueden reasignar.')
        if anterior and anterior.estado != s.estado and s.estado not in s.SIGUIENTES[anterior.estado]:
            raise ValidationError('La transición de estado no sigue la ruta de atención.')
        for modelo, campo in ((Zona, 'zona'), (EquipoCentro, 'equipo'), (Integrante, 'supervisor')):
            ids = {getattr(objeto, campo + '_id') for objeto in (s, anterior) if objeto and getattr(objeto, campo + '_id')}
            bloqueados = {obj.pk: obj for obj in modelo.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
            if getattr(s, campo + '_id'):
                setattr(s, campo, bloqueados[getattr(s, campo + '_id')])
        if actor is not None and not s.centro.puede_gestionar(actor):
            if s.usuario_id != actor.pk or (anterior is None and s.estado != 'recibida'):
                raise ValidationError('No puede modificar este expediente.')
            if anterior is not None and not (s.estado == 'cancelada' and anterior.puede_retirar):
                raise ValidationError('La decisión corresponde a la gestión del centro.')
        if actor is not None and s.estado in ('no_procede', 'cancelada') and (not anterior or anterior.estado != s.estado):
            if not (motivo.strip() or s.respuesta.strip()):
                raise ValidationError('Registre un motivo o respuesta antes de rechazar o cancelar.')
            motivo = motivo.strip() or s.respuesta.strip()
        s.clean()
        if s.estado in ('cerrada', 'no_procede', 'cancelada') and not s.cerrada_en:
            s.cerrada_en = timezone.now()
        resultado = persistir()
        if s.estado == 'cancelada':
            s.sesiones.filter(estado='programada').update(estado='cancelada')
        campos = ('estado', 'inicio_reservado', 'fin_reservado', 'zona_id', 'equipo_id', 'supervisor_id',
                  'responsable_atencion_id', 'respuesta', 'diagnostico', 'plan', 'entregable', 'evaluacion_cierre')
        if not anterior or any(getattr(anterior, c) != getattr(s, c) for c in campos):
            detalle = motivo.strip() or ('Solicitud registrada.' if not anterior else 'Atención actualizada.')
            if anterior and (anterior.inicio_reservado != s.inicio_reservado or anterior.fin_reservado != s.fin_reservado):
                detalle += ' Horario: ' + (f'{timezone.localtime(s.inicio_reservado):%d/%m/%Y %H:%M} a '
                           f'{timezone.localtime(s.fin_reservado):%d/%m/%Y %H:%M}.' if s.inicio_reservado else 'sin confirmar.')
            RegistroSolicitud.objects.create(solicitud=s, autor=identidad_de(actor) if actor is not None else None, estado_anterior=anterior.estado if anterior else '',
                                              estado_nuevo=s.estado, detalle=detalle)
        return resultado


def validar_sesion(sesion):
    from .models import SesionAcompanamiento, SolicitudCentro

    if not isinstance(sesion.inicio, datetime) or not isinstance(sesion.fin, datetime):
        raise ValidationError('Indique inicio y fin válidos para la sesión.')
    if sesion.solicitud_id and sesion.responsable_id:
        if sesion.responsable.centro_id != sesion.solicitud.centro_id or not sesion.responsable.vigente or not contenido_admitido(sesion.responsable):
            raise ValidationError('La persona responsable debe estar vigente en el centro.')
    if sesion.inicio and sesion.fin and sesion.fin <= sesion.inicio:
        raise ValidationError('La sesión debe terminar después de empezar.')
    if sesion.estado == 'realizada' and (not sesion.acuerdos.strip() or sesion.fin > timezone.now()):
        raise ValidationError('Una sesión realizada necesita acuerdos y no puede terminar en el futuro.')
    if sesion.estado == 'programada' and sesion.solicitud.estado not in ACTIVOS:
        raise ValidationError('Solo se programan sesiones para una atención aprobada o en ejecución.')
    if sesion.estado != 'programada':
        return
    if SesionAcompanamiento.objects.filter(responsable=sesion.responsable, estado='programada',
            inicio__lt=sesion.fin, fin__gt=sesion.inicio).exclude(pk=sesion.pk).exists():
        raise ValidationError('La persona responsable tiene otra sesión en ese horario.')
    if SolicitudCentro.objects.filter(supervisor=sesion.responsable, estado__in=ACTIVOS,
            inicio_reservado__lt=sesion.fin, fin_reservado__gt=sesion.inicio).exists():
        raise ValidationError('La persona responsable supervisa otro uso en ese horario.')


def disponibilidad(recurso, dia):
    """Ventanas orientativas sin identidad, finalidad ni motivos privados de otras operaciones."""
    from .models import SolicitudCentro

    campo = 'zona' if hasattr(recurso, 'centro_id') else 'equipo'
    margen = timedelta(minutes=recurso.margen_minutos)
    ventanas = []
    if not recurso.apto_reserva:
        return ventanas
    if campo == 'equipo' and recurso.calibracion_requerida and dia > recurso.calibracion_hasta:
        return ventanas
    inicio_dia = timezone.make_aware(datetime.combine(dia, datetime.min.time()))
    fin_dia = inicio_dia + timedelta(days=1)
    usos = SolicitudCentro.objects.filter(**{campo: recurso}, estado__in=ACTIVOS,
             inicio_reservado__lt=fin_dia + 2 * margen, fin_reservado__gt=inicio_dia - 2 * margen)
    ocupados = [(u.inicio_reservado - 2 * margen, u.fin_reservado + 2 * margen) for u in usos]
    ocupados += [(b.inicio - margen, b.fin + margen) for b in recurso.bloqueos.filter(inicio__lt=fin_dia, fin__gt=inicio_dia)]
    for horario in recurso.horarios.filter(dia=dia.weekday()):
        segmentos = [(timezone.make_aware(datetime.combine(dia, horario.abre)) + margen,
                      timezone.make_aware(datetime.combine(dia, horario.cierra)) - margen)]
        for ocupado_inicio, ocupado_fin in ocupados:
            restantes = []
            for inicio, fin in segmentos:
                if ocupado_fin <= inicio or ocupado_inicio >= fin:
                    restantes.append((inicio, fin))
                else:
                    if inicio < ocupado_inicio:
                        restantes.append((inicio, min(fin, ocupado_inicio)))
                    if ocupado_fin < fin:
                        restantes.append((max(inicio, ocupado_fin), fin))
            segmentos = restantes
        if dia == timezone.localdate():
            segmentos = [(max(inicio, timezone.now() + margen), fin) for inicio, fin in segmentos]
        ventanas += [{'inicio': timezone.localtime(inicio), 'fin': timezone.localtime(fin)}
                     for inicio, fin in segmentos if fin > inicio]
    return sorted(ventanas, key=lambda fila: fila['inicio'])


def guardar_regla(regla, persistir):
    """Serializa cambios de horarios y bloqueos con la confirmación del mismo recurso."""
    from .models import BloqueoRecurso, EquipoCentro, SolicitudCentro, Zona

    with transaction.atomic(using=router.db_for_write(type(regla))):
        modelo, campo = (Zona, 'zona') if regla.zona_id else (EquipoCentro, 'equipo')
        anterior = type(regla).objects.filter(pk=regla.pk).first() if regla.pk else None
        if anterior and (anterior.zona_id != regla.zona_id or anterior.equipo_id != regla.equipo_id):
            raise ValidationError('Para otro recurso cree una regla independiente.')
        actual = modelo.objects.select_for_update().filter(pk=getattr(regla, campo + '_id')).first()
        if actual is not None:
            setattr(regla, campo, actual)
        regla.full_clean()
        if isinstance(regla, BloqueoRecurso):
            recurso = getattr(regla, campo)
            margen = timedelta(minutes=recurso.margen_minutos)
            if SolicitudCentro.objects.filter(**{campo: recurso}, estado__in=ACTIVOS,
                    inicio_reservado__lt=regla.fin + margen, fin_reservado__gt=regla.inicio - margen).exists():
                raise ValidationError('Reprograme o cancele la reserva confirmada antes de bloquear ese intervalo.')
        return persistir()
