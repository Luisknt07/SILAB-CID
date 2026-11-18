"""Alertas de equipos sin uso y traspasos entre unidades.

Detectar: cada activo se compara con los umbrales configurados por Dirección.
El seguimiento distingue uso real, falta de registros y cierres incompletos.
La unidad dispone de un compromiso y fecha de revisión antes de estudiar una redistribución.

Traspasar, sin estados nuevos (solicitado → aprobado → ejecutado, o rechazado):
1. la unidad que entrega lo propone desde su lista de equipos (queda «Solicitado»);
2. la unidad que recibe lo acepta (sigue «Solicitado», con su aceptación en la auditoría) o lo rechaza;
3. la Dirección lo aprueba con un clic en Administración (no puede ser quien lo propuso);
4. la unidad que recibe registra la recepción física y el equipo pasa a ella con el próximo código de laboratorio
   de su área, su nuevo custodio y su ubicación. El código del bien (bodega) se conserva; el anterior queda como
   alias y la historia del equipo cita el acta del traspaso.
Cada paso deja su registro de auditoría en la unidad correspondiente (quién, cuándo, etapa anterior y nueva).
"""
from datetime import datetime, timedelta
from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

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


def solicitar_traspaso(usuario, equipos, destino, justificacion, motivo='necesidad', area=None, alerta=None,
                       entrega='', custodio=''):
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
                                  justificacion=justificacion, alerta=alerta, solicitado_por=usuario,
                                  entrega_nombre=entrega[:160], custodio_nuevo=custodio[:160])
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


def nombre_de(usuario):
    return ((usuario.get_full_name() or usuario.get_username()) if usuario else '')[:160]


def aceptacion_destino(traspaso):
    """La aceptación de la unidad que recibe: su registro de auditoría (el estado sigue «Solicitado»)."""
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad
    return (RegistroAuditoriaUnidad.objects.filter(
        unidad_id=traspaso.unidad_destino_id, entidad=TraspasoEquipo._meta.label, objeto_id=str(traspaso.pk),
        accion='aprobar', datos_nuevos__etapa='aceptado').select_related('usuario').order_by('-creado_en', '-pk').first())


def etapa_del_traspaso(traspaso, aceptado=None):
    """La etapa que se lee en pantalla: el estado guardado y, si está solicitado, si la unidad que recibe ya aceptó."""
    if traspaso.estado == 'solicitado':
        aceptado = aceptacion_destino(traspaso) is not None if aceptado is None else aceptado
        return 'aceptado' if aceptado else 'propuesto'
    return traspaso.estado


ETAPAS = {
    'propuesto': 'Propuesto: espera la aceptación de la unidad que recibe',
    'aceptado': 'Aceptado por la unidad que recibe: espera la aprobación de la Dirección',
    'aprobado': 'Aprobado por la Dirección: espera la recepción física',
    'ejecutado': 'Recibido: el equipo ya está en la unidad que lo recibe',
    'rechazado': 'Rechazado', 'anulado': 'Anulado',
}


def _auditar(traspaso, usuario, unidades, accion, descripcion, anterior, nueva, request=None, **datos):
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    for unidad in unidades:
        registrar_auditoria(request, unidad=unidad, accion=accion, objeto=traspaso, usuario=usuario,
                            descripcion=f'Traspaso {traspaso.codigo}: {descripcion}',
                            anteriores={'etapa': anterior}, nuevos={'etapa': nueva, 'estado': traspaso.estado, **datos})


def _bloquear(traspaso):
    return TraspasoEquipo.objects.select_for_update().select_related('unidad_origen', 'unidad_destino').get(pk=traspaso.pk)


def proponer_traspaso(usuario, equipo, destino, justificacion, motivo='necesidad', custodio='', request=None):
    """La unidad que entrega propone el traspaso de un equipo activo; la de destino decide si lo acepta."""
    origen = equipo.laboratorio
    if origen is None or not puede_operar_modulo_unidad(usuario, origen, 'recursos'):
        raise PermissionDenied('El traspaso lo propone la gestión de recursos de la unidad que entrega.')
    if not equipo.activa or equipo.fecha_baja:
        raise ValidationError('Solo se propone el traspaso de un equipo activo, sin baja registrada.')
    if destino is None or not destino.activo:
        raise ValidationError('Elige una unidad activa que reciba el equipo.')
    if not (justificacion or '').strip():
        raise ValidationError('Explica para qué lo necesita la unidad que recibe.')
    with transaction.atomic():
        traspaso = solicitar_traspaso(usuario, [equipo], destino, justificacion.strip(), motivo=motivo,
                                      entrega=nombre_de(usuario), custodio=(custodio or '').strip())
        _auditar(traspaso, usuario, [origen], 'crear', f'propuesto a {destino.nombre}', '', 'propuesto', request,
                 equipo=equipo.codigo_unidad, destino=destino.pk, motivo=motivo)
    return traspaso


def responder_traspaso(traspaso, usuario, aceptar, motivo='', request=None):
    """La unidad que recibe acepta o rechaza; quien propuso no acepta por la otra unidad."""
    with transaction.atomic():
        traspaso = _bloquear(traspaso)
        destino = traspaso.unidad_destino
        if not puede_operar_modulo_unidad(usuario, destino, 'recursos'):
            raise PermissionDenied('Acepta o rechaza el traspaso la gestión de recursos de la unidad que recibe.')
        if traspaso.solicitado_por_id == usuario.pk:
            raise PermissionDenied('Quien propone el traspaso no puede aceptarlo ni rechazarlo por la unidad que recibe.')
        if etapa_del_traspaso(traspaso) != 'propuesto':
            raise ValidationError(f'El traspaso {traspaso.codigo} ya no espera respuesta ({ETAPAS[etapa_del_traspaso(traspaso)]}).')
        if aceptar:
            _auditar(traspaso, usuario, [destino], 'aprobar', f'aceptado por {destino.nombre}', 'propuesto',
                     'aceptado', request)
            return traspaso
        motivo = (motivo or '').strip()
        if not motivo:
            raise ValidationError('Indica por qué la unidad no acepta el traspaso.')
        traspaso.estado = 'rechazado'
        traspaso.observacion_direccion = f'Rechazado por la unidad que recibe ({nombre_de(usuario)}): {motivo}'
        traspaso.save(update_fields=['estado', 'observacion_direccion'])
        AlertaUsoEquipo.objects.filter(equipo__traspasos__traspaso=traspaso, estado='reasignacion').update(estado='en_estudio')
        _auditar(traspaso, usuario, [destino, traspaso.unidad_origen], 'observar', f'rechazado por {destino.nombre}',
                 'propuesto', 'rechazado', request, motivo=motivo)
    return traspaso


def resolver_traspaso(traspaso, usuario, aprobar, observacion=''):
    """La Dirección aprueba (después de la aceptación de la unidad que recibe) o rechaza; al rechazar, las alertas
    vuelven a estudio. Quien propuso el traspaso no lo aprueba."""
    if not puede_aprobar(usuario):
        raise PermissionDenied('Solo la Dirección aprueba o rechaza traspasos.')
    if traspaso.estado != 'solicitado':
        raise ValidationError(f'El traspaso {traspaso.codigo} ya no está solicitado ({traspaso.get_estado_display()}).')
    anterior = etapa_del_traspaso(traspaso)
    if aprobar and traspaso.solicitado_por_id == usuario.pk:
        raise PermissionDenied('Quien propuso el traspaso no puede aprobarlo.')
    if aprobar and anterior != 'aceptado':
        raise ValidationError(f'La unidad que recibe ({traspaso.unidad_destino.nombre}) todavía no acepta el traspaso.')
    traspaso.estado = 'aprobado' if aprobar else 'rechazado'
    traspaso.aprobado_por, traspaso.fecha_aprobacion = usuario, timezone.now()
    traspaso.observacion_direccion = observacion or traspaso.observacion_direccion
    traspaso.save(update_fields=['estado', 'aprobado_por', 'fecha_aprobacion', 'observacion_direccion'])
    if not aprobar:
        AlertaUsoEquipo.objects.filter(equipo__traspasos__traspaso=traspaso, estado='reasignacion').update(estado='en_estudio')
    _auditar(traspaso, usuario, [traspaso.unidad_origen, traspaso.unidad_destino], 'aprobar' if aprobar else 'observar',
             'aprobado por la Dirección' if aprobar else 'rechazado por la Dirección', anterior, traspaso.estado)
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
    with transaction.atomic():
        _trasladar(traspaso, usuario, timezone.now())
        _auditar(traspaso, usuario, [traspaso.unidad_destino, traspaso.unidad_origen], 'actualizar',
                 'ejecutado por la Dirección', 'aprobado', 'ejecutado', custodio=traspaso.custodio_nuevo)
    return traspaso


def registrar_recepcion(traspaso, usuario, fecha, custodio='', area=None, acta=None, observaciones='', request=None):
    """La unidad que recibe registra la recepción física: el equipo cambia de unidad, ubicación y custodio."""
    with transaction.atomic():
        traspaso = _bloquear(traspaso)
        destino = traspaso.unidad_destino
        if not puede_operar_modulo_unidad(usuario, destino, 'recursos'):
            raise PermissionDenied('La recepción la registra la gestión de recursos de la unidad que recibe.')
        if traspaso.estado != 'aprobado':
            raise ValidationError(f'El traspaso {traspaso.codigo} debe estar aprobado por la Dirección para recibirlo.')
        hoy = timezone.localdate()
        aprobado_el = timezone.localdate(traspaso.fecha_aprobacion) if traspaso.fecha_aprobacion else None
        if fecha is None or fecha > hoy or (aprobado_el and fecha < aprobado_el):
            raise ValidationError('Registra la fecha real de la recepción: no futura ni anterior a la aprobación.')
        if area is not None and area.unidad_id != destino.pk:
            raise ValidationError('El área debe ser de la unidad que recibe.')
        traspaso.recibe_nombre = nombre_de(usuario)
        traspaso.entrega_nombre = traspaso.entrega_nombre or nombre_de(traspaso.solicitado_por)
        traspaso.custodio_nuevo = (custodio or '').strip()[:160] or traspaso.custodio_nuevo or traspaso.recibe_nombre
        if area is not None:
            traspaso.area_destino = area
        if acta:
            traspaso.acta_firmada.save(Path(acta.name).name, acta, save=False)
        momento = timezone.make_aware(datetime.combine(fecha, timezone.localtime().time()))
        _trasladar(traspaso, usuario, momento, observaciones=(observaciones or '').strip())
        _auditar(traspaso, usuario, [destino, traspaso.unidad_origen], 'actualizar', f'recibido en {destino.nombre}',
                 'aprobado', 'ejecutado', request, fecha=fecha.isoformat(), custodio=traspaso.custodio_nuevo,
                 area=traspaso.area_destino_id, acta=traspaso.acta_firmada.name or '',
                 observaciones=(observaciones or '').strip(),
                 equipos=list(traspaso.equipos.values_list('codigo_nuevo', flat=True)))
    return traspaso


def _trasladar(traspaso, usuario, momento, observaciones=''):
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
            # La ubicación específica era de la unidad que entrega; en la que recibe la da su área.
            equipo.ubicacion_especifica = ''
            equipo.save()
            # Las áreas eran de la unidad que entrega: queda en la que la recibe (o sin área hasta ubicarlo).
            equipo.espacios_asociados.set([area] if area else [])
            equipo.laboratorios.remove(origen)
            item.codigo_nuevo = equipo.codigo_unidad
            item.save(update_fields=['codigo_nuevo'])
            evento = (EventoCicloVidaEquipo.objects.filter(equipo=equipo, tipo='transferencia').order_by('-fecha', '-pk').first())
            if evento:
                evento.descripcion = ' '.join(filter(None, (
                    evento.descripcion, f'Según el acta de traspaso {traspaso.codigo}.',
                    f'Recepción: {observaciones}' if observaciones else '')))
                evento.usuario = usuario
                evento.save(update_fields=['descripcion', 'usuario'])
        traspaso.estado, traspaso.ejecutado_por, traspaso.fecha_ejecucion = 'ejecutado', usuario, momento
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
        'volver_url': (reverse('admin:recursos_traspasoequipo_change', args=[traspaso.pk]) if puede_aprobar(request.user)
                       else _url_panel(traspaso.unidad_destino if puede_operar_modulo_unidad(
                           request.user, traspaso.unidad_destino, 'recursos') else traspaso.unidad_origen)),
    })


# ---- pantallas de la unidad: proponer, responder y recibir ------------------------------------------------

MAXIMO_BYTES_ACTA = 25 * 1024 * 1024


def validar_acta(archivo):
    """PDF, PNG o JPG de hasta 25 MB y con contenido legible."""
    from django.core.files.base import ContentFile
    from apps.documentos.models.respaldo_medicion import validar_respaldo

    if Path(archivo.name).suffix.lower() not in ('.pdf', '.png', '.jpg', '.jpeg'):
        raise ValidationError('El acta debe ser un archivo PDF, PNG o JPG.')
    if archivo.size > MAXIMO_BYTES_ACTA:
        raise ValidationError('El acta no puede superar 25 MB.')
    archivo.seek(0)
    copia = ContentFile(archivo.read(), name=archivo.name)
    archivo.seek(0)
    try:
        validar_respaldo(copia)
    except ValidationError as error:
        raise ValidationError('El acta debe ser un PDF o una imagen legible y con contenido.') from error


class PropuestaTraspasoForm(forms.Form):
    destino = forms.ModelChoiceField(label='Unidad que lo recibe', queryset=None, empty_label='Elige la unidad')
    motivo = forms.ChoiceField(label='Motivo', choices=TraspasoEquipo.MOTIVOS, initial='necesidad')
    justificacion = forms.CharField(label='Para qué lo necesita la unidad que recibe', widget=forms.Textarea(attrs={'rows': 3}),
                                    max_length=2000)
    custodio = forms.CharField(label='Nuevo custodio (si se sabe)', required=False, max_length=160,
                               help_text='Si queda vacío, lo indica la unidad que recibe al registrar la recepción.')

    def __init__(self, *args, origen, **kwargs):
        from apps.directorio_unidades.models.core import Unidad
        super().__init__(*args, **kwargs)
        self.fields['destino'].queryset = Unidad.objects.filter(activo=True).exclude(pk=origen.pk).order_by('nombre')


class RecepcionTraspasoForm(forms.Form):
    fecha = forms.DateField(label='Fecha de la recepción', widget=forms.DateInput(attrs={'type': 'date'}))
    area = forms.ModelChoiceField(label='Área donde queda', queryset=None, required=False, empty_label='Sin área todavía',
                                  help_text='Define el nuevo código de laboratorio del equipo.')
    custodio = forms.CharField(label='Custodio en la unidad', max_length=160)
    acta = forms.FileField(label='Acta firmada (opcional)', required=False, validators=[validar_acta],
                           help_text='PDF, PNG o JPG.')
    observaciones = forms.CharField(label='Observaciones', required=False, max_length=1000,
                                    widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, traspaso, **kwargs):
        from apps.gestion_unidades.models.espacios import EspacioReservable
        super().__init__(*args, **kwargs)
        self.fields['area'].queryset = EspacioReservable.objects.filter(
            unidad=traspaso.unidad_destino, activo=True).order_by('nombre')
        self.fields['area'].initial = traspaso.area_destino_id
        self.fields['fecha'].initial = timezone.localdate()
        self.fields['custodio'].initial = traspaso.custodio_nuevo


def _url_panel(unidad):
    return reverse('gestion_unidad', args=[unidad.slug]) + '?view=recursos&modo_recursos=activos'


def traspasos_de_unidad(unidad):
    """Los traspasos en curso que la unidad recibe o entrega, con su etapa, para la lista de equipos."""
    en_curso = list(TraspasoEquipo.objects.filter(
        Q(unidad_destino=unidad) | Q(unidad_origen=unidad), estado__in=TraspasoEquipo.EN_CURSO)
        .select_related('unidad_origen', 'unidad_destino', 'solicitado_por')
        .prefetch_related('equipos__equipo__equipo').order_by('fecha_solicitud'))
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad
    aceptados = set(RegistroAuditoriaUnidad.objects.filter(
        entidad=TraspasoEquipo._meta.label, objeto_id__in=[str(t.pk) for t in en_curso], accion='aprobar',
        datos_nuevos__etapa='aceptado').values_list('objeto_id', flat=True))
    for traspaso in en_curso:
        traspaso.etapa = etapa_del_traspaso(traspaso, str(traspaso.pk) in aceptados)
        traspaso.etapa_texto = ETAPAS[traspaso.etapa]
    return dict(por_recibir=[t for t in en_curso if t.unidad_destino_id == unidad.pk],
                propuestos=[t for t in en_curso if t.unidad_origen_id == unidad.pk])


def _texto_error(error):
    return ' '.join(error.messages) if isinstance(error, ValidationError) else str(error)


@login_required
@require_http_methods(['GET', 'POST'])
def proponer_traspaso_view(request, slug, equipo_id):
    """«Proponer traspaso» en la fila de un equipo activo de la unidad que lo entrega."""
    from apps.directorio_unidades.models.core import Unidad
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, 'recursos'):
        raise PermissionDenied('El traspaso lo propone la gestión de recursos de la unidad que entrega.')
    equipo = get_object_or_404(UnidadEquipo.objects.select_related('equipo', 'laboratorio'), pk=equipo_id,
                               laboratorio=unidad)
    en_curso = (EquipoEnTraspaso.objects.filter(equipo=equipo, traspaso__estado__in=TraspasoEquipo.EN_CURSO)
                .select_related('traspaso').first())
    form = PropuestaTraspasoForm(request.POST or None, origen=unidad)
    if request.method == 'POST' and en_curso is None and form.is_valid():
        datos = form.cleaned_data
        try:
            traspaso = proponer_traspaso(request.user, equipo, datos['destino'], datos['justificacion'],
                                         motivo=datos['motivo'], custodio=datos['custodio'], request=request)
        except (ValidationError, PermissionDenied) as error:
            form.add_error(None, _texto_error(error))
        else:
            messages.success(request, f'Traspaso {traspaso.codigo} propuesto a {traspaso.unidad_destino.nombre}: '
                                      'espera su aceptación y después la aprobación de la Dirección.')
            return redirect(_url_panel(unidad))
    return render(request, 'portal/pages/unidades/gestion/traspaso_equipo.html', {
        'unidad': unidad, 'equipo': equipo, 'en_curso': en_curso and en_curso.traspaso, 'form': form,
        'volver_url': _url_panel(unidad),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def traspaso_unidad_view(request, slug, codigo):
    """El traspaso visto por una de sus unidades; la que recibe lo acepta, lo rechaza o registra la recepción."""
    from apps.directorio_unidades.models.core import Unidad
    unidad = get_object_or_404(Unidad, slug=slug)
    traspaso = get_object_or_404(TraspasoEquipo.objects.select_related(
        'unidad_origen', 'unidad_destino', 'area_destino', 'solicitado_por', 'aprobado_por'), codigo=codigo)
    if unidad.pk not in (traspaso.unidad_origen_id, traspaso.unidad_destino_id) or not (
            puede_operar_modulo_unidad(request.user, unidad, 'recursos')):
        raise PermissionDenied('El traspaso lo ven las unidades que entregan y reciben el equipo.')
    recibe = unidad.pk == traspaso.unidad_destino_id
    accion = request.POST.get('accion', '') if request.method == 'POST' else ''
    if accion and not recibe:
        raise PermissionDenied('Acepta, rechaza o recibe el traspaso la unidad que lo recibe.')
    recepcion = RecepcionTraspasoForm(request.POST if accion == 'recibir' else None,
                                      request.FILES if accion == 'recibir' else None, traspaso=traspaso)
    error = ''
    try:
        if accion in ('aceptar', 'rechazar'):
            responder_traspaso(traspaso, request.user, accion == 'aceptar', request.POST.get('motivo', ''),
                               request=request)
            messages.success(request, f'Traspaso {traspaso.codigo} ' + (
                'aceptado: queda a la espera de la aprobación de la Dirección.' if accion == 'aceptar' else 'rechazado.'))
            return redirect(_url_panel(unidad))
        if accion == 'recibir' and recepcion.is_valid():
            datos = recepcion.cleaned_data
            registrar_recepcion(traspaso, request.user, datos['fecha'], custodio=datos['custodio'], area=datos['area'],
                                acta=datos['acta'], observaciones=datos['observaciones'], request=request)
            messages.success(request, f'Recepción del traspaso {traspaso.codigo} registrada: el equipo ya es de '
                                      f'{unidad.nombre}.')
            return redirect(_url_panel(unidad))
    except (ValidationError, PermissionDenied) as fallo:
        error = _texto_error(fallo)
    aceptacion = aceptacion_destino(traspaso)
    etapa = etapa_del_traspaso(traspaso, aceptacion is not None)
    return render(request, 'portal/pages/unidades/gestion/traspaso_equipo.html', {
        'unidad': unidad, 'traspaso': traspaso, 'items': list(traspaso.equipos.select_related('equipo__equipo')),
        'etapa': etapa, 'etapa_texto': ETAPAS[etapa], 'aceptacion': aceptacion, 'recibe': recibe,
        'propio': traspaso.solicitado_por_id == request.user.pk, 'recepcion': recepcion, 'error': error,
        'volver_url': _url_panel(unidad),
    }, status=400 if error or (accion == 'recibir' and recepcion.errors) else 200)
