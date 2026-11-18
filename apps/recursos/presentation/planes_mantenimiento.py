"""Lo que la unidad registra de sus equipos desde su panel y antes solo cabía en Administración.

- El plan de mantenimiento de cada equipo (tabla 2.1 del anexo de mantenimiento).
- El plan al que responde una orden y el informe que la respalda: sin los dos, una orden completada no
  cuenta como «ejecutada con respaldo» en los equipos críticos (tabla 2.3) ni sirve de respaldo de una
  calibración.
- El retiro (baja) de un equipo, con su motivo, su justificación y su respaldo (tabla 3.3 del inventario).

Las cuentas de unidad no entran a Administración: estas operaciones van por el mismo despacho que el resto
del panel (`gestion_operacion_accion`), con el permiso del módulo y el rastro de auditoría de la unidad.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.recursos.models.mantenimiento import PlanMantenimientoEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.ciclo_vida_equipo import guardar_ciclo_vida, validar_respaldo_retiro


def _equipos_de(unidad):
    return UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()


def _equipo_de(unidad, equipo_id, *, existente=False):
    """El equipo de la unidad, bloqueado; con `existente`, ni referencia ni dado de baja."""
    clave = str(equipo_id or '').strip()
    if not clave.isdecimal():
        raise ValidationError('Selecciona el equipo.')
    equipos = _equipos_de(unidad)
    if existente:
        equipos = equipos.filter(activa=True, fecha_baja__isnull=True)
    if not equipos.filter(pk=clave).exists():
        if existente and _equipos_de(unidad).filter(pk=clave).exists():
            raise ValidationError('Ese equipo no existe en la unidad: es una referencia o se dio de baja.')
        raise Http404('El equipo no pertenece a esta unidad.')
    return UnidadEquipo.objects.select_for_update().get(pk=clave)


def _fecha(valor, etiqueta, *, defecto=None):
    texto = str(valor or '').strip()
    if not texto:
        return defecto
    fecha = parse_date(texto)
    if fecha is None:
        raise ValidationError(f'{etiqueta} no tiene un formato válido (AAAA-MM-DD).')
    return fecha


def _entero(valor, etiqueta, *, defecto, minimo=1, maximo=3650):
    texto = str(valor or '').strip()
    if not texto:
        return defecto
    if not texto.isdecimal() or not minimo <= int(texto) <= maximo:
        raise ValidationError(f'{etiqueta} debe ser un número entero entre {minimo} y {maximo}.')
    return int(texto)


def operar_plan(request, unidad):
    """Crea, corrige o desactiva el plan de mantenimiento de un equipo de la unidad."""
    registro_id = (request.POST.get('registro_id') or '').strip()
    if registro_id:
        objeto = get_object_or_404(PlanMantenimientoEquipo.objects.select_for_update(), pk=registro_id,
                                   equipo__in=_equipos_de(unidad))
        creado = False
    else:
        objeto = PlanMantenimientoEquipo(equipo=_equipo_de(unidad, request.POST.get('equipo_id'), existente=True))
        creado = True
    if (request.POST.get('accion') or '') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el plan que se desactiva.')
        objeto.activo = False
        objeto.save(update_fields=['activo', 'actualizado_en'])
        return objeto, 'Plan de mantenimiento desactivado', False
    objeto.tipo = (request.POST.get('tipo') or objeto.tipo or 'preventivo').strip()
    # Sin nombre, el plan se llama como lo que es: «Mantenimiento preventivo de FAB-IMP-01».
    objeto.nombre = ((request.POST.get('nombre') or '').strip()
                     or f'{objeto.get_tipo_display()} de {objeto.equipo.codigo_unidad}')[:160]
    objeto.frecuencia_dias = _entero(request.POST.get('frecuencia_dias'), 'La frecuencia', defecto=180)
    hoy = timezone.localdate()
    objeto.fecha_inicio = _fecha(request.POST.get('fecha_inicio'), 'El inicio del plan',
                                 defecto=hoy if creado else objeto.fecha_inicio)
    # Sin próxima fecha se calcula sola: el inicio más la frecuencia.
    objeto.proxima_ejecucion = _fecha(
        request.POST.get('proxima_ejecucion'), 'La próxima ejecución',
        defecto=objeto.fecha_inicio + timedelta(days=objeto.frecuencia_dias))
    objeto.anticipacion_dias = _entero(request.POST.get('anticipacion_dias'), 'El aviso anticipado', defecto=15,
                                       minimo=0, maximo=365)
    objeto.ejecutor = (request.POST.get('ejecutor') or objeto.ejecutor or 'interno').strip()
    responsable_id = (request.POST.get('responsable') or '').strip()
    objeto.responsable = get_object_or_404(
        ResponsableUnidad.objects.select_related('usuario'), unidad=unidad, usuario_id=responsable_id, activo=True,
    ).usuario if responsable_id else None
    objeto.proveedor = (request.POST.get('proveedor') or '').strip()
    objeto.instrucciones = (request.POST.get('instrucciones') or '').strip()
    objeto.activo = True
    objeto.full_clean()
    objeto.save()
    return objeto, 'Plan de mantenimiento creado' if creado else 'Plan de mantenimiento actualizado', creado


def completar_orden(request, orden):
    """El plan al que responde la orden y el informe que la respalda, tal como llegan del formulario.

    Un formulario que no trae el plan no lo borra. Sin plan elegido, la orden toma sola el plan vigente de
    su mismo tipo cuando el equipo tiene uno solo: es el caso corriente y evita un paso que se olvida.
    """
    if 'plan_id' in request.POST:
        plan_id = (request.POST.get('plan_id') or '').strip()
        orden.plan = (PlanMantenimientoEquipo.objects.filter(pk=plan_id, equipo_id=orden.equipo_id).first()
                      if plan_id.isdecimal() else None)
        if plan_id and orden.plan is None:
            raise ValidationError('El plan elegido no es de este equipo: elige uno del equipo de la orden o deja '
                                  'el plan en automático.')
    if orden.plan_id is None:
        vigentes = list(PlanMantenimientoEquipo.objects.filter(equipo_id=orden.equipo_id, activo=True,
                                                               tipo=orden.tipo)[:2])
        if len(vigentes) == 1:
            orden.plan = vigentes[0]
    informe = request.FILES.get('informe')
    if informe:
        try:
            validar_respaldo_retiro(informe)
        except ValidationError as error:
            raise ValidationError('El informe de la orden: ' + ' '.join(error.messages)) from error
        orden.informe = informe


def operar_baja(request, unidad):
    """Registra el retiro de operación de un equipo de la unidad, o corrige el ya registrado.

    Es el mismo registro que hace Administración (`guardar_ciclo_vida`): conserva la decisión como un
    evento con su autoría y su respaldo, y no sustituye la autorización patrimonial.
    """
    equipo = _equipo_de(unidad, request.POST.get('registro_id'))
    if equipo.laboratorio_id != unidad.pk:
        raise ValidationError('El retiro lo registra la unidad a la que está asignado el equipo.')
    motivo = (request.POST.get('motivo_baja') or '').strip()
    if motivo not in dict(UnidadEquipo.MOTIVOS_BAJA):
        raise ValidationError('Indica el motivo del retiro.')
    equipo.fecha_baja = _fecha(request.POST.get('fecha_baja'), 'La fecha del retiro', defecto=timezone.localdate())
    equipo.motivo_baja = motivo
    equipo.observacion_baja = (request.POST.get('observacion_baja') or '').strip()
    sustituto_id = (request.POST.get('reemplazado_por') or '').strip()
    equipo.reemplazado_por = (get_object_or_404(UnidadEquipo, pk=sustituto_id, laboratorio=unidad)
                              if sustituto_id else None)
    guardar_ciclo_vida(equipo, request.user, evidencia=request.FILES.get('respaldo_retiro'),
                       justificacion=request.POST.get('justificacion_rectificacion', ''))
    return equipo, 'Retiro del equipo registrado', False


OPERADORES_MANTENIMIENTO = {'plan_mantenimiento': operar_plan, 'baja_equipo': operar_baja}
PERMISOS_MANTENIMIENTO = {'plan_mantenimiento': 'mantenimiento', 'baja_equipo': 'recursos'}
MODELOS_MANTENIMIENTO = {'plan_mantenimiento': PlanMantenimientoEquipo, 'baja_equipo': UnidadEquipo}
