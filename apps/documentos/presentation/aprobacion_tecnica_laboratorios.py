"""Huella de lo que el responsable acaba de aprobar, sin reconstruir legados.

Se añade al evento real de aprobación dentro de su misma transacción. Conserva
campos, relaciones documentales y bytes de los adjuntos; no cambia estados ni
permisos. La lectura se hace en lote para todos los anexos de una unidad.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from apps.documentos.presentation.perfil_laboratorios import es_laboratorio


ESQUEMA_APROBACION = 1
ENTIDADES = {
    'planificaciones': 'formacion.PlanificacionPractica',
    'ejecuciones': 'formacion.EjecucionPractica',
    'guias': 'reservas.GuiaActividadReserva',
}


def _normal(valor):
    if isinstance(valor, dict):
        return {str(k): _normal(v) for k, v in sorted(valor.items())}
    if isinstance(valor, (list, tuple)):
        return [_normal(v) for v in valor]
    if isinstance(valor, (date, datetime, time)):
        return valor.isoformat()
    if isinstance(valor, (Decimal, UUID)):
        return str(valor)
    return valor


def huella_captura(datos):
    return hashlib.sha256(json.dumps(_normal(datos), sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def _archivo(campo, cache):
    nombre = campo.name or ''
    clave = (id(campo.storage), nombre)
    if clave not in cache:
        huella, cantidad = hashlib.sha256(), 0
        try:
            if nombre:
                with campo.storage.open(nombre, 'rb') as archivo:
                    for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
                        huella.update(bloque)
                        cantidad += len(bloque)
        except (OSError, ValueError):
            cantidad = 0
        cache[clave] = dict(nombre=nombre, bytes=cantidad, sha256=huella.hexdigest() if cantidad else '',
                            disponible=bool(cantidad))
    return cache[clave]


def _campos(objeto, cache):
    if objeto is None:
        return None
    datos = {}
    for campo in objeto._meta.concrete_fields:
        # Un guardado sin cambios no altera el contenido técnico aprobado.
        if campo.name == 'actualizado_en':
            continue
        valor = getattr(objeto, campo.attname)
        datos[campo.attname] = (_archivo(valor, cache) if campo.get_internal_type() in ('FileField', 'ImageField')
                               else _normal(valor))
    return datos


def _guia(guia, cache, *, embebida=False):
    if guia is None:
        return None
    datos = dict(campos=_campos(guia, cache),
                 figuras=[_campos(f, cache) for f in sorted(guia.imagenes.all(), key=lambda f: f.pk)])
    if embebida:
        # Volver a revisar el mismo contenido o cambiar quién puede descargarlo
        # no reescribe la versión técnica utilizada por una práctica.
        for campo in ('revisado_por_id', 'revisado_en', 'aprobado_por_id', 'aprobado_en',
                      'visibilidad', 'permite_descarga', 'solicita_publicacion', 'observaciones_revision'):
            datos['campos'].pop(campo, None)
    return datos


def _responsable(responsable):
    # La identidad/asignación documental es estable frente a cambios de foto,
    # contacto o delegaciones operativas posteriores a la práctica.
    return dict(id=responsable.pk, unidad=responsable.unidad_id,
                usuario=responsable.usuario_id, nombre=responsable.nombre) if responsable else None


def _plan(plan, cache, *, historica=False):
    reserva = plan.reserva if plan.reserva_id else None
    tema = plan.tema_asignatura if plan.tema_asignatura_id else None
    # El cierre de la reserva cambia legítimamente al validar la ejecución. Se firma
    # su programación y asignaciones, no el estado operativo posterior.
    agenda = (dict(id=reserva.pk, unidad=reserva.laboratorio_id, fecha=reserva.fecha.isoformat(),
        inicio=reserva.hora_inicio.isoformat(), fin=reserva.hora_fin.isoformat(),
        equipo_codigo=reserva.equipo_codigo, equipo_nombre=reserva.equipo_nombre,
        responsable=reserva.responsable_asignado_id,
        espacios=[_campos(e, cache) for e in sorted(reserva.espacios_solicitados.all(), key=lambda e: e.pk)],
        software=[_campos(s, cache) for s in sorted(reserva.software_solicitado.all(), key=lambda s: s.pk)],
        servicios=[_campos(s, cache) for s in sorted(reserva.servicios_solicitados.all(), key=lambda s: s.pk)])
        if reserva else None)
    datos = dict(campos=_campos(plan, cache), agenda=agenda,
        tema=_campos(tema, cache), asignatura=_campos(tema.asignatura, cache) if tema else None,
        responsable=_responsable(plan.responsable_tecnico) if plan.responsable_tecnico_id else None,
        guia=_guia(plan.guia, cache, embebida=True) if plan.guia_id else None)
    if historica:
        # Una sucesora no cambia el contenido ni la versión que se ejecutó.
        # Estado, autoría, campos, archivos y sus hashes siguen protegidos.
        datos['campos'].pop('es_version_vigente', None)
        if datos['guia']:
            datos['guia']['campos'].pop('es_vigente', None)
    return datos


def capturas_tecnicas(unidad, ids_por_grupo):
    """Lote de instantáneas actuales; sin escrituras ni consultas por cada anexo."""
    from apps.formacion.models.practicas import PlanificacionPractica, EjecucionPractica
    from apps.reservas.models.reservas import GuiaActividadReserva
    cache, salida = {}, {}
    relacionados = ('reserva', 'tema_asignatura__asignatura', 'responsable_tecnico', 'guia')
    precarga = ('reserva__espacios_solicitados', 'reserva__software_solicitado',
                'reserva__servicios_solicitados', 'guia__imagenes')
    planes = PlanificacionPractica.objects.filter(unidad=unidad,
        pk__in=ids_por_grupo.get('planificaciones', [])).select_related(*relacionados).prefetch_related(*precarga)
    for plan in planes:
        salida[(ENTIDADES['planificaciones'], str(plan.pk))] = _plan(plan, cache)
    ejecuciones = EjecucionPractica.objects.filter(planificacion__unidad=unidad,
        pk__in=ids_por_grupo.get('ejecuciones', [])).select_related(
            *(('planificacion__' + r) for r in relacionados), 'responsable_tecnico').prefetch_related(
            *(('planificacion__' + r) for r in precarga), 'evidencias')
    for ejecucion in ejecuciones:
        salida[(ENTIDADES['ejecuciones'], str(ejecucion.pk))] = dict(campos=_campos(ejecucion, cache),
            planificacion=_plan(ejecucion.planificacion, cache, historica=True),
            responsable=_responsable(ejecucion.responsable_tecnico) if ejecucion.responsable_tecnico_id else None,
            adjuntos=[_campos(a, cache) for a in sorted(ejecucion.evidencias.all(), key=lambda a: a.pk)])
    guias = GuiaActividadReserva.objects.filter(actividad__unidad=unidad,
        pk__in=ids_por_grupo.get('guias', [])).prefetch_related('imagenes')
    for guia in guias:
        salida[(ENTIDADES['guias'], str(guia.pk))] = _guia(guia, cache)
    return salida


def registrar_aprobacion_tecnica(objeto, actor, *, evento):
    """Completa sólo el evento que acaba de producir una aprobación autorizada.

    No sirve para completar auditorías históricas, aprobar en nombre de otra
    persona ni promover estados. Los permisos del flujo original se conservan.
    """
    from django.conf import settings
    from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
    entidad = objeto._meta.label
    if entidad not in ENTIDADES.values():
        raise ValueError('Tipo de aprobación técnica no admitido.')
    unidad = (objeto.actividad.unidad if entidad == ENTIDADES['guias'] else
              objeto.planificacion.unidad if entidad == ENTIDADES['ejecuciones'] else objeto.unidad)
    if not es_laboratorio(unidad):
        return None
    if not connection.in_atomic_block:
        raise ValidationError('Registra la aprobación técnica dentro de su transacción original.')
    if not actor or not puede_operar_modulo_unidad(actor, unidad, 'practicas'):
        raise ValidationError('La aprobación debe realizarla un responsable autorizado de la unidad.')
    estado, aprobador, fecha = (
        (objeto.estado_publicacion == 'publicada', objeto.aprobado_por_id, objeto.aprobado_en)
        if entidad == ENTIDADES['guias'] else
        (objeto.estado == 'validada', objeto.validado_por_id, objeto.validado_en)
        if entidad == ENTIDADES['ejecuciones'] else
        (objeto.estado == 'aprobada', objeto.revisado_por_id, objeto.revisado_en))
    ahora = timezone.now()
    if (not estado or aprobador != actor.pk or not fecha or not evento.pk or
            evento.unidad_id != unidad.pk or evento.entidad != entidad or evento.objeto_id != str(objeto.pk) or
            evento.accion != 'aprobar' or evento.usuario_id != actor.pk or
            abs(ahora - evento.creado_en) > timedelta(minutes=2) or
            abs(fecha - evento.creado_en) > timedelta(minutes=2)):
        raise ValidationError('Falta un evento real y reciente de aprobación de esta versión por su responsable.')
    grupo = next(g for g, e in ENTIDADES.items() if e == entidad)
    captura = capturas_tecnicas(unidad, {grupo: [objeto.pk]})[(entidad, str(objeto.pk))]
    datos = dict(evento.datos_nuevos)
    datos['aprobacion_tecnica'] = dict(esquema=ESQUEMA_APROBACION, unidad=unidad.pk, entidad=entidad,
        objeto=objeto.pk, actor=actor.pk, aprobado_en=fecha.isoformat(), captura=captura,
        sha256=huella_captura(captura), demostracion=bool(getattr(settings, 'MEDICION_SOLO_DEMO', False) or
            str(unidad.nombre).startswith('[DEMO REPORTES]')))
    evento.datos_nuevos = datos
    evento.save(update_fields=['datos_nuevos'])
    return datos['aprobacion_tecnica']
