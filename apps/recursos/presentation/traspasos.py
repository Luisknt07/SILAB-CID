"""Alertas de equipos sin uso y traspasos entre unidades.

Detectar: cada activo se compara con los umbrales configurados por Dirección.
El seguimiento distingue uso real, falta de registros y cierres incompletos.
La unidad dispone de un compromiso y fecha de revisión antes de estudiar una redistribución.

Traspasar: la unidad que lo necesita (o la Dirección) lo solicita, la Dirección aprueba y, al ejecutarlo, cada
equipo pasa a la unidad que lo recibe con el próximo código de laboratorio de su área. El código del bien
(bodega) se conserva; el anterior queda como alias y la historia del equipo cita el acta del traspaso.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.recursos.models.redistribucion import AlertaUsoEquipo, EquipoEnTraspaso, TraspasoEquipo
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.models.unidades import UnidadEquipo

from apps.core.presentation.codigos_sistema import siguiente_codigo_unidad
from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.recursos.presentation.uso_equipos import politica_uso, situaciones


def puede_aprobar(usuario):
    """La Dirección: quien tiene el permiso de aprobar traspasos."""
    return usuario.is_authenticated and (usuario.is_superuser or usuario.has_perm('recursos.aprobar_traspasoequipo'))


def equipos_asignados(unidad=None):
    """El activo físico se cuenta una vez aunque sirva a varias unidades."""
    consulta = UnidadEquipo.objects.filter(
        Q(laboratorio__activo=True) | Q(laboratorios__activo=True))
    if unidad is not None:
        consulta = consulta.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
    return consulta.select_related('laboratorio', 'equipo').prefetch_related(
        'laboratorios', 'espacios_asociados').distinct().order_by('codigo_unidad')


def candidatura_reasignacion(alerta, lectura, hoy=None):
    """Sólo una revisión humana; nunca autoriza ni ejecuta un movimiento."""
    hoy = hoy or timezone.localdate()
    if not alerta or not alerta.vigente or alerta.estado == 'reasignacion':
        return dict(candidata=False, estado='sin_revision', motivo='Sin revisión de redistribución pendiente.')
    if not lectura.get('politica', {}).get('configurada'):
        return dict(candidata=False, estado='politica_pendiente', motivo='Configura la política institucional antes de evaluar inactividad o redistribución.')
    if lectura['clave'] in ('fuera', 'nuevo'):
        return dict(candidata=False, estado='no_disponible', motivo='Revisa la disponibilidad y puesta en operación del activo.')
    if lectura['pendientes']:
        return dict(candidata=False, estado='datos_pendientes', motivo='Completa los cierres antes de concluir si el equipo está sin uso.')
    if not alerta.notificada_en or not alerta.revisar_desde or not alerta.plan_uso.strip():
        return dict(candidata=False, estado='plan_pendiente', motivo='Comunica la alerta y acuerda actividades, responsable y fecha de revisión.')
    if hoy < alerta.revisar_desde:
        return dict(candidata=False, estado='en_correccion', motivo='La unidad dispone del plazo acordado para acreditar el uso.')
    if lectura['ultimo'] and lectura['ultimo'] >= alerta.notificada_en:
        return dict(candidata=False, estado='uso_reanudado', motivo='Hay uso acreditado después de la comunicación; revisa el compromiso.')
    if lectura['clave'] not in ('sin_uso', 'sin_registros', 'poco_uso'):
        return dict(candidata=False, estado='uso_acreditado', motivo='El uso actual no fundamenta una revisión por inactividad.')
    return dict(candidata=True, estado='revisar_redistribucion',
        motivo='Venció el plazo sin nuevo uso acreditado. Verifica causas y necesidades receptoras; cualquier traspaso requiere aprobación y acta.')


def transparencia_equipos(unidad=None, hoy=None, *, equipos=None):
    """Situación inmediata de todos los activos asignados, sin escrituras GET."""
    hoy = hoy or timezone.localdate()
    equipos = list(equipos_asignados(unidad) if equipos is None else equipos)
    lecturas = situaciones(equipos, hoy)
    alertas = {a.equipo_id: a for a in AlertaUsoEquipo.objects.filter(
        equipo__in=equipos, estado__in=AlertaUsoEquipo.VIGENTES)}
    filas = []
    for equipo in equipos:
        lectura = lecturas[equipo.pk]
        alerta = alertas.get(equipo.pk)
        filas.append(dict(equipo=equipo, equipo_id=equipo.pk, codigo=equipo.codigo_unidad,
            nombre=equipo.equipo.nombre, unidad=equipo.laboratorio,
            areas=list(equipo.espacios_asociados.all()), lectura=lectura, alerta=alerta,
            uso_en_unidad=next((u for u in lectura['por_unidad'] if u['unidad_id'] == getattr(unidad, 'pk', unidad)), None)
                          if unidad is not None else None,
            redistribucion=candidatura_reasignacion(alerta, lectura, hoy)))
    return dict(filas=filas, corte=hoy, desde=hoy - timedelta(days=365), politica=politica_uso(),
        resumen=dict(total=len(filas), con_uso=sum(f['lectura']['sesiones'] > 0 for f in filas),
            sin_registros=sum(f['lectura']['clave'] == 'sin_registros' for f in filas),
            datos_pendientes=sum(bool(f['lectura']['pendientes']) for f in filas),
            fuera_servicio=sum(f['lectura']['clave'] == 'fuera' for f in filas),
            alertas=sum(f['lectura']['alerta'] for f in filas),
            candidatas=sum(f['redistribucion']['candidata'] for f in filas)))


def _evidencia(lectura, hoy):
    return dict(corte=hoy.isoformat(), clave=lectura['clave'], horas=lectura['horas'],
        sesiones=lectura['sesiones'], ultimo=lectura['ultimo'].isoformat() if lectura['ultimo'] else None,
        fuentes=lectura['fuentes'], pendientes=lectura['pendientes'],
        limite=lectura['limite'], solapamientos=lectura['solapamientos'], politica=lectura['politica'])


def detectar_equipos_sin_uso(hoy=None, simular=False, *, unidad=None):
    """Persiste la lectura tras registrar actividad o por tarea, nunca al leer."""
    hoy = hoy or timezone.localdate()
    equipos = list(equipos_asignados(unidad).filter(activa=True))
    politica = politica_uso()
    if not politica['configurada']:
        return dict(revisados=len(equipos), nuevas=0, cerradas=0, politica_pendiente=True)
    por_equipo = situaciones(equipos, hoy)
    vigentes = {alerta.equipo_id: alerta for alerta in AlertaUsoEquipo.objects.filter(
        equipo__in=equipos, estado__in=AlertaUsoEquipo.VIGENTES)}
    # Una justificación no caduca con un plazo inventado. Si Dirección definió
    # días sin uso se vuelve a revisar después de ese lapso.
    justificadas = AlertaUsoEquipo.objects.filter(estado='justificada')
    if politica['dias_sin_uso'] is not None:
        justificadas = justificadas.filter(actualizada__date__gte=hoy - timedelta(days=politica['dias_sin_uso']))
    justificados = set(justificadas.values_list('equipo_id', flat=True))
    nuevas, cerradas, actualizadas = [], [], []
    for equipo in equipos:
        situacion = por_equipo[equipo.pk]
        alerta = vigentes.get(equipo.pk)
        if situacion['alerta_institucional'] and alerta is None and equipo.pk not in justificados:
            principal = equipo.laboratorio or next((u for u in equipo.laboratorios.all() if u.activo), None)
            nuevas.append(AlertaUsoEquipo(equipo=equipo, unidad=principal, motivo=situacion['clave'], detectada=hoy,
                horas_anuales=situacion['horas'], ultimo_uso=situacion['ultimo'],
                evidencia=_evidencia(situacion, hoy), ultima_revision=hoy))
        elif (alerta is not None and alerta.estado in ('abierta', 'en_estudio')
              and situacion['clave'] in ('en_uso', 'demandado')):
            cerradas.append(alerta)
        if alerta is not None:
            alerta.horas_anuales, alerta.ultimo_uso = situacion['horas'], situacion['ultimo']
            alerta.evidencia, alerta.ultima_revision = _evidencia(situacion, hoy), hoy
            actualizadas.append(alerta)
    if not simular:
        AlertaUsoEquipo.objects.bulk_create(nuevas, ignore_conflicts=True)
        if actualizadas:
            AlertaUsoEquipo.objects.bulk_update(actualizadas, ['horas_anuales', 'ultimo_uso', 'evidencia', 'ultima_revision'])
        for alerta in cerradas:
            alerta.estado = 'cerrada'
            alerta.justificacion = '\n'.join(filter(None, (alerta.justificacion, f'Volvió a usarse ({hoy:%d/%m/%Y}).')))
            alerta.save(update_fields=['estado', 'justificacion', 'actualizada'])
    return {'revisados': len(equipos), 'nuevas': len(nuevas), 'cerradas': len(cerradas)}


def solicitar_traspaso(usuario, equipos, destino, justificacion, motivo='necesidad', area=None, alerta=None):
    """Registra el traspaso de equipos de una misma unidad hacia otra, a la espera de la Dirección."""
    equipos = list(equipos)
    if not equipos:
        raise ValidationError('Elige al menos un equipo para traspasar.')
    origen = equipos[0].laboratorio
    if origen is None:
        raise ValidationError('Asigna y verifica la unidad principal de custodia antes de solicitar un traspaso.')
    if not (puede_aprobar(usuario) or puede_operar_modulo_unidad(usuario, origen, 'recursos')
            or puede_operar_modulo_unidad(usuario, destino, 'recursos')):
        raise PermissionDenied('El traspaso lo solicita Dirección o la gestión de recursos de una de las unidades involucradas.')
    if any(equipo.laboratorio_id != origen.pk for equipo in equipos):
        raise ValidationError('Los equipos de un traspaso deben salir de la misma unidad.')
    with transaction.atomic():
        traspaso = TraspasoEquipo(unidad_origen=origen, unidad_destino=destino, area_destino=area, motivo=motivo,
                                  justificacion=justificacion, alerta=alerta, solicitado_por=usuario)
        traspaso.full_clean(exclude=['codigo'])
        traspaso.save()
        for equipo in equipos:
            item = EquipoEnTraspaso(traspaso=traspaso, equipo=equipo, codigo_anterior=equipo.codigo_unidad,
                                    codigo_bien=equipo.codigo_bien or '', custodio_anterior=equipo.custodio or '')
            item.full_clean()
            item.save()
        marcar_en_reasignacion(traspaso)
    return traspaso


def marcar_en_reasignacion(traspaso):
    AlertaUsoEquipo.objects.filter(equipo__traspasos__traspaso=traspaso, estado__in=('abierta', 'en_estudio')).update(
        estado='reasignacion')


def resolver_traspaso(traspaso, usuario, aprobar, observacion=''):
    """La Dirección aprueba o rechaza; al rechazar, las alertas vuelven a estudio."""
    if not puede_aprobar(usuario):
        raise PermissionDenied('Solo la Dirección aprueba o rechaza traspasos.')
    if traspaso.estado != 'solicitado':
        raise ValidationError(f'El traspaso {traspaso.codigo} ya no está solicitado ({traspaso.get_estado_display()}).')
    traspaso.estado = 'aprobado' if aprobar else 'rechazado'
    traspaso.aprobado_por, traspaso.fecha_aprobacion = usuario, timezone.now()
    traspaso.observacion_direccion = observacion or traspaso.observacion_direccion
    traspaso.save(update_fields=['estado', 'aprobado_por', 'fecha_aprobacion', 'observacion_direccion'])
    if not aprobar:
        AlertaUsoEquipo.objects.filter(equipo__traspasos__traspaso=traspaso, estado='reasignacion').update(estado='en_estudio')
    return traspaso


def ejecutar_traspaso(traspaso, usuario, entrega='', recibe='', bodega='', custodio=''):
    """Pasa cada equipo a la unidad que lo recibe con su nuevo código de laboratorio; bodega no cambia."""
    if not puede_aprobar(usuario):
        raise PermissionDenied('Solo la Dirección ejecuta traspasos.')
    if traspaso.estado != 'aprobado':
        raise ValidationError(f'El traspaso {traspaso.codigo} debe estar aprobado para ejecutarse.')
    traspaso.entrega_nombre = entrega or traspaso.entrega_nombre
    traspaso.recibe_nombre = recibe or traspaso.recibe_nombre
    traspaso.bodega_nombre = bodega or traspaso.bodega_nombre
    traspaso.custodio_nuevo = custodio or traspaso.custodio_nuevo
    if not (traspaso.entrega_nombre and traspaso.recibe_nombre):
        raise ValidationError('Indica quién entrega y quién recibe: son las firmas del acta.')
    origen, destino, area = traspaso.unidad_origen, traspaso.unidad_destino, traspaso.area_destino
    with transaction.atomic():
        items = list(traspaso.equipos.select_related('equipo__equipo').select_for_update())
        for item in items:
            equipo = item.equipo
            if equipo.laboratorio_id != origen.pk:
                raise ValidationError(f'{equipo.codigo_unidad} ya no está en {origen.nombre}.')
            equipo.laboratorio = destino
            equipo.codigo_unidad = siguiente_codigo_unidad(destino, area, equipo.equipo)
            if traspaso.custodio_nuevo:
                equipo.custodio = traspaso.custodio_nuevo
            equipo.save()
            # Las áreas eran de la unidad que entrega: queda en la que la recibe (o sin área hasta ubicarlo).
            equipo.espacios_asociados.set([area] if area else [])
            equipo.laboratorios.remove(origen)
            item.codigo_nuevo = equipo.codigo_unidad
            item.save(update_fields=['codigo_nuevo'])
            evento = (EventoCicloVidaEquipo.objects.filter(equipo=equipo, tipo='transferencia').order_by('-fecha', '-pk').first())
            if evento:
                evento.descripcion = f'{evento.descripcion} Según el acta de traspaso {traspaso.codigo}.'
                evento.usuario = usuario
                evento.save(update_fields=['descripcion', 'usuario'])
        traspaso.estado, traspaso.ejecutado_por, traspaso.fecha_ejecucion = 'ejecutado', usuario, timezone.now()
        traspaso.save()
        AlertaUsoEquipo.objects.filter(equipo__in=[item.equipo for item in items], estado__in=AlertaUsoEquipo.VIGENTES).update(
            estado='cerrada', justificacion=f'Reasignado a {destino.nombre} por el traspaso {traspaso.codigo}.')
    return traspaso


def puede_ver_traspaso(usuario, traspaso):
    return puede_aprobar(usuario) or any(
        puede_operar_modulo_unidad(usuario, unidad, 'recursos') for unidad in (traspaso.unidad_origen, traspaso.unidad_destino))


@login_required
def acta_traspaso_view(request, codigo):
    """El acta de traspaso: los equipos con sus códigos antes y después, y las firmas de las partes."""
    traspaso = get_object_or_404(TraspasoEquipo.objects.select_related(
        'unidad_origen', 'unidad_destino', 'area_destino', 'aprobado_por', 'solicitado_por'), codigo=codigo)
    if not puede_ver_traspaso(request.user, traspaso):
        raise PermissionDenied('El acta la ven la Dirección y las unidades del traspaso.')
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/acta_traspaso.html', {
        'unidad': traspaso.unidad_origen,
        'movimiento': traspaso,
        'traspaso': traspaso,
        'items': list(traspaso.equipos.select_related('equipo__equipo')),
        'generado_en': timezone.localtime(),
        'volver_url': reverse('admin:recursos_traspasoequipo_change', args=[traspaso.pk]),
    })
