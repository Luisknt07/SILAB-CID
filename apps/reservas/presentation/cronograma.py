"""El cronograma de una programación: sesión por sesión, con su proceso.

Al reservar varias sesiones, la persona dice qué práctica hará en cada
fecha y con qué proceso; cada sesión nace con los recursos que ese proceso
exige, la guía general lleva el cronograma y cada sesión su guía. Después,
mientras la sesión sigue pendiente, la persona la completa (proceso,
materia prima e insumos) desde «Mis sesiones programadas».
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext
from django.views.decorators.http import require_GET, require_http_methods

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.formacion.models.practicas import PlanificacionPractica
from apps.reservas.models.reservas import ProgramacionReserva, Reserva, ReservaConsumible
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.recursos.models.software import SoftwareDisponible
from apps.formacion.models.asignaturas import TemaAsignatura
from apps.directorio_unidades.models.core import Unidad

from apps.reservas.presentation.capacidad import operacion_reservas

from apps.formacion.presentation.aula import enlaces_del_aula
from apps.reservas.presentation.periodos import resolver_periodo_reserva
from apps.reservas.presentation.proceso import factor_valido, recetas_para_practica, seleccion_por_proceso

ESTADOS_ACTIVOS = ('pendiente', 'confirmada', 'en_proceso')


# ----------------------------------------------------------- las fechas
def fechas_de_programacion(frecuencia, primera_fecha, fecha_fin_texto, contexto_actividad, tipo_solicitud):
    """Las sesiones semanales concretas que alimentarán calendario y reportes."""
    if frecuencia not in dict(ProgramacionReserva.FRECUENCIA_CHOICES):
        raise ValueError('Selecciona una modalidad temporal válida para la reserva')
    if frecuencia == 'unica':
        return frecuencia, [primera_fecha], []
    if tipo_solicitud == 'servicio':
        raise ValueError(
            'Los servicios se solicitan por una fecha preferida; la programación semanal '
            'corresponde a reservas de recursos.'
        )
    if contexto_actividad.get('vinculacion_actividad') not in {
        'catalogo', 'manual', 'independiente',
    }:
        raise ValueError('Selecciona cómo se identificará la programación semanal.')
    periodo = contexto_actividad.get('periodo')
    version = contexto_actividad.get('version_calendario')
    if not periodo or not version:
        raise ValueError(
            'Para reservar semanalmente debe existir un período académico publicado.'
        )
    if primera_fecha > version.fecha_fin_periodo:
        raise ValueError('La primera sesión debe estar dentro del período seleccionado')

    fecha_limite = version.fecha_fin_clases
    if frecuencia == 'semanal_rango':
        if not fecha_fin_texto:
            raise ValueError('Selecciona hasta qué fecha se repetirá la reserva semanal')
        try:
            fecha_limite = datetime.strptime(fecha_fin_texto, '%Y-%m-%d').date()
        except ValueError as error:
            raise ValueError('La fecha final de la repetición no es válida') from error
        if fecha_limite < primera_fecha + timedelta(days=7):
            raise ValueError(
                'El rango semanal debe incluir al menos una segunda sesión'
            )
        if fecha_limite > version.fecha_fin_periodo:
            raise ValueError(
                f'La fecha final no puede superar el cierre de {periodo.codigo}'
            )
        if fecha_limite > primera_fecha + timedelta(days=7 * 25):
            raise ValueError('La programación no puede superar 26 sesiones semanales')

    fechas = []
    omitidas = []
    actual = primera_fecha
    while actual <= fecha_limite:
        semana = periodo.semana_para_fecha(actual)
        if semana and semana.permite_reservas:
            fechas.append(actual)
        else:
            omitidas.append(actual)
        actual += timedelta(days=7)
    if len(fechas) < 2:
        raise ValueError(
            'La fecha seleccionada no permite construir al menos dos sesiones semanales '
            'dentro del período.'
        )
    return frecuencia, fechas, omitidas


@login_required
@require_GET
def fechas_programacion_view(request):
    """Las sesiones que una programación semanal crearía desde una fecha."""
    unidad = get_object_or_404(Unidad, slug=(request.GET.get('unidad') or '').strip())
    texto = (request.GET.get('fecha') or '').strip()
    try:
        primera_fecha = datetime.strptime(texto, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Elige la primera fecha de la programación.'}, status=400)
    frecuencia = (request.GET.get('frecuencia') or 'unica').strip()
    try:
        contexto = resolver_periodo_reserva(
            primera_fecha, {'actividad_catalogo': None, 'periodo_academico': ''}, 'docencia_practica'
        )
        contexto['vinculacion_actividad'] = 'manual'
        frecuencia, fechas, omitidas = fechas_de_programacion(
            frecuencia, primera_fecha, (request.GET.get('fin') or '').strip(), contexto, 'recursos'
        )
    except ValueError as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)
    periodo = contexto.get('periodo')
    return JsonResponse({
        'success': True,
        'unidad': unidad.slug,
        'periodo': periodo.codigo if periodo else '',
        'sesiones': [
            {
                'numero': numero,
                'fecha': fecha.isoformat(),
                'fecha_texto': fecha.strftime('%d/%m/%Y'),
                'semana': (semana.numero if (semana := periodo.semana_para_fecha(fecha)) else None) if periodo else None,
            }
            for numero, fecha in enumerate(fechas, start=1)
        ],
        'omitidas': [fecha.isoformat() for fecha in omitidas],
    })


# ------------------------------------------------------------ las filas
def _fila_vacia(fecha):
    return {'fecha': fecha, 'tema': '', 'tema_id': None, 'receta': None, 'factor': None, 'cantidad': ''}


def factor_de_cantidad(receta, cantidad):
    """Cuántas corridas base son `cantidad` unidades de materia prima."""
    base = receta.cantidad_base or Decimal('1')
    try:
        return factor_valido(str((Decimal(str(cantidad)) / base).quantize(Decimal('0.001'))))
    except (InvalidOperation, ArithmeticError) as error:
        raise ValueError('La materia prima indicada no es válida') from error


def normalizar_cronograma(texto, fechas, laboratorio, *, receta_principal=None, factor_principal=None):
    """Las filas del cronograma alineadas con las fechas de la programación."""
    if not texto or not texto.strip() or len(fechas) < 2:
        return []
    try:
        filas = json.loads(texto)
    except (TypeError, ValueError) as error:
        raise ValueError('El cronograma de sesiones no tiene un formato válido') from error
    if not isinstance(filas, list) or len(filas) != len(fechas):
        raise ValueError(f'El cronograma debe tener una fila por sesión ({len(fechas)} sesiones)')
    recetas = {
        receta.pk: receta
        for receta in Receta.objects.filter(unidad=laboratorio, activa=True).select_related('producto')
    }
    temas = {tema.pk: tema for tema in TemaAsignatura.objects.filter(asignatura__unidad=laboratorio)}
    resultado = []
    for indice, (fecha, fila) in enumerate(zip(fechas, filas)):
        if not isinstance(fila, dict):
            raise ValueError('El cronograma de sesiones no tiene un formato válido')
        if str(fila.get('fecha') or '') != fecha.isoformat():
            raise ValueError(
                'Las fechas del cronograma no coinciden con las sesiones programadas; vuelve a cargar el cronograma'
            )
        normalizada = _fila_vacia(fecha)
        normalizada['tema'] = str(fila.get('tema') or '').strip()[:240]
        tema_id = fila.get('tema_id')
        if tema_id not in (None, '', 0):
            try:
                tema = temas[int(tema_id)]
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError('Uno de los temas del cronograma no pertenece a esta unidad') from error
            normalizada['tema_id'] = tema.pk
            normalizada['tema'] = normalizada['tema'] or tema.nombre
        receta_id = fila.get('receta_id')
        if receta_id not in (None, '', 'ninguno', 0):
            try:
                receta = recetas[int(receta_id)]
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError('Uno de los procesos del cronograma no está disponible en esta unidad') from error
            if not receta.etapas.exists():
                raise ValueError(f'El proceso «{receta.nombre}» no tiene etapas definidas')
            cantidad = str(fila.get('cantidad') or '').strip()
            try:
                factor = factor_de_cantidad(receta, cantidad) if cantidad else Decimal('1.000')
            except ValueError as error:
                raise ValueError(f'La materia prima de la sesión del {fecha:%d/%m/%Y} no es válida') from error
            normalizada.update(receta=receta, factor=factor, cantidad=cantidad or format(receta.cantidad_base.normalize(), 'f'))
        resultado.append(normalizada)
    # La primera sesión es la que se configura en el asistente: su proceso es el del contexto.
    primera = resultado[0]
    if receta_principal is not None:
        if primera['receta'] is not None and primera['receta'].pk != receta_principal.pk:
            raise ValueError('El proceso de la primera sesión debe ser el elegido en el paso de contexto')
        primera.update(receta=receta_principal, factor=factor_principal or Decimal('1.000'))
    elif primera['receta'] is not None:
        raise ValueError('El proceso de la primera sesión se elige en el paso de contexto del asistente')
    return resultado


# --------------------------------------------------------- los recursos
def recursos_de_sesion(receta, factor, personas=1):
    """Lo que el proceso exige, en la forma en que la reserva lo guarda."""
    seleccion = seleccion_por_proceso(receta, factor, personas=personas)
    consumibles = {
        consumible.pk: consumible
        for consumible in Consumible.objects.filter(pk__in=[item['id'] for item in seleccion['insumos']])
    }
    return {
        'seleccion': seleccion,
        'recursos': [
            {
                'id': item['id'],
                'codigo': item['codigo'],
                'ubicacion': item['ubicacion'] or 'No especificada',
                'equipo_id': item['equipo_id'],
                'equipo_codigo': item['equipo_codigo'],
                'equipo_nombre': item['equipo_nombre'],
            }
            for item in seleccion['equipos']
        ],
        'espacios': list(EspacioReservable.objects.filter(pk__in=[item['id'] for item in seleccion['espacios']])),
        'software': list(SoftwareDisponible.objects.filter(pk__in=[item['id'] for item in seleccion['software']])),
        'consumibles': [
            (consumibles[item['id']], Decimal(item['cantidad']), 'simulacion')
            for item in seleccion['insumos']
            if item['id'] in consumibles
        ],
    }


def aplicar_recursos_a_sesion(sesion, receta, factor, recursos):
    """La sesión toma el proceso y todo lo que exige."""
    primero = recursos['recursos'][0] if recursos['recursos'] else None
    sesion.receta = receta
    sesion.producto_solicitado = receta.producto
    sesion.factor_proceso = factor
    sesion.cantidad_piezas = recursos['seleccion']['piezas']
    sesion.unidades_seleccionadas = json.dumps(recursos['recursos'], ensure_ascii=False)
    sesion.incluye_espacio = True
    sesion.solicito_espacio = True
    sesion.solicito_equipo = True
    sesion.solicito_software = bool(recursos['software'])
    sesion.alcance_espacio = 'areas'
    sesion.provision_consumibles = 'unidad' if recursos['consumibles'] else 'ninguno'
    if primero is not None:
        sesion.equipo_codigo = primero['equipo_codigo']
        sesion.equipo_nombre = primero['equipo_nombre']
    sesion.save()
    sesion.espacios_solicitados.set(recursos['espacios'])
    sesion.software_solicitado.set(recursos['software'])
    sesion.consumibles_solicitados.all().delete()
    for consumible, cantidad, metodo in recursos['consumibles']:
        ReservaConsumible.objects.create(
            reserva=sesion, consumible=consumible, cantidad_solicitada=cantidad, metodo_estimacion=metodo,
        )


# ------------------------------------------------------ completar la sesión
def _plan_de(reserva):
    return (
        PlanificacionPractica.objects.filter(reserva=reserva, eliminado_en__isnull=True)
        .select_related('guia', 'guia__guia_general', 'tema_asignatura')
        .first()
    )


def numero_de_sesion(reserva):
    """El lugar de la sesión en su programación y cuántas son."""
    sesiones = list(
        Reserva.objects.filter(programacion=reserva.programacion).order_by('fecha', 'pk').values_list('pk', flat=True)
    )
    return (sesiones.index(reserva.pk) + 1 if reserva.pk in sesiones else 0), len(sesiones)


@operacion_reservas
@transaction.atomic
def completar_sesion(reserva, datos, usuario, *, unidad_esperada=None):
    """La persona define (o cambia) el proceso, la materia prima y los insumos de su sesión pendiente."""
    from apps.formacion.presentation.asignaturas import actualizar_fila_cronograma, prellenar_guia_de_sesion
    from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
    from apps.reservas.presentation.conflictos import validar_conflictos_recursos

    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada
    reserva = Reserva.objects.select_for_update(of=('self',)).select_related('laboratorio').filter(pk=reserva.pk).first()
    if reserva is None:
        raise ValueError(gettext('La sesión ya no está disponible.'))
    exigir_autoridad_reserva(reserva, usuario, operacion='completar_sesion', unidad_esperada=alcance)
    if reserva.programacion_id is None:
        raise ValueError(gettext('La reserva no pertenece a una programación.'))
    if reserva.estado != 'pendiente':
        raise ValueError(
            'La sesión ya fue aprobada: pide el cambio desde «Mis reservas» para que la unidad lo revise.'
        )
    tema = str(datos.get('tema') or '').strip()[:240]
    receta_id = str(datos.get('receta_id') or '').strip()
    receta = None
    if receta_id and receta_id != 'ninguno':
        receta = (
            Receta.objects.filter(pk=receta_id, unidad=reserva.laboratorio, activa=True).first()
            if receta_id.isdigit() else None
        )
        if receta is None or not receta.etapas.exists():
            raise ValueError('El proceso seleccionado no está disponible en esta unidad')
    personas = reserva.numero_participantes or 1
    if receta is not None:
        factor = factor_de_cantidad(receta, str(datos.get('cantidad') or '').strip() or receta.cantidad_base)
        recursos = recursos_de_sesion(receta, factor, personas=personas)
        obligatorios = {
            item['id'] for item in recursos['seleccion']['insumos'] if item['obligatorio']
        }
        ajustados = []
        for consumible, cantidad, metodo in recursos['consumibles']:
            valor = str(datos.get(f'insumo_{consumible.pk}') or '').strip()
            if valor:
                try:
                    cantidad = Decimal(valor)
                except InvalidOperation as error:
                    raise ValueError(f'La cantidad de {consumible.nombre} no es válida') from error
            if cantidad <= 0:
                if consumible.pk in obligatorios:
                    raise ValueError(f'{consumible.nombre} es obligatorio para el proceso: indica una cantidad')
                continue
            ajustados.append((consumible, cantidad, metodo))
        recursos['consumibles'] = ajustados
        validar_conflictos_recursos(
            reserva.laboratorio,
            reserva.fecha,
            reserva.hora_inicio,
            reserva.hora_fin,
            recursos['recursos'],
            recursos['software'],
            recursos['espacios'],
            incluye_espacio=True,
            alcance_espacio='areas',
            tipo_solicitud=reserva.tipo_solicitud,
            modalidad_servicio=reserva.modalidad_servicio,
            proposito_codigo=reserva.proposito_codigo,
            numero_participantes=personas,
            excluir_reserva_id=reserva.pk,
        )
        aplicar_recursos_a_sesion(reserva, receta, factor, recursos)
    else:
        reserva.receta = None
        reserva.producto_solicitado = None
        reserva.factor_proceso = None
        reserva.save(update_fields=[
            'receta', 'producto_solicitado', 'factor_proceso', 'fecha_actualizacion',
        ])
    plan = _plan_de(reserva)
    if plan is not None:
        if tema:
            plan.tema = tema
            plan.save(update_fields=['tema', 'actualizado_en'])
        guia = plan.guia
        if guia is not None and guia.alcance == 'sesion' and guia.estado_publicacion == 'borrador':
            prellenar_guia_de_sesion(guia, reserva, plan, tema or plan.tema, actor=usuario)
        if guia is not None and guia.guia_general_id:
            actualizar_fila_cronograma(guia.guia_general, reserva, tema or plan.tema, receta)
    return reserva


def _insumos_de_formulario(reserva):
    """Los insumos del proceso de la sesión con la cantidad que hoy tiene la reserva."""
    if not reserva.receta_id:
        return []
    seleccion = seleccion_por_proceso(
        reserva.receta, reserva.factor_proceso or Decimal('1'), personas=reserva.numero_participantes or 1
    )
    actuales = {
        pedido.consumible_id: pedido.cantidad_solicitada for pedido in reserva.consumibles_solicitados.all()
    }
    filas = []
    for item in seleccion['insumos']:
        cantidad = actuales.get(item['id'])
        filas.append({
            **item,
            'cantidad_actual': format(cantidad.normalize(), 'f') if cantidad is not None else ('' if not item['obligatorio'] else item['cantidad']),
            'pedido': item['id'] in actuales,
        })
    return seleccion, filas


@login_required
@require_http_methods(['GET', 'POST'])
def completar_sesion_view(request, reserva_id):
    """La sesión programada, completada por quien la reservó mientras sigue pendiente."""
    from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

    reserva = get_object_or_404(
        Reserva.objects.select_related('laboratorio', 'programacion', 'programacion__asignatura', 'receta', 'usuario'),
        pk=reserva_id,
    )
    if reserva.programacion_id is None:
        raise Http404('La reserva no pertenece a una programación')
    unidad = reserva.laboratorio
    es_operador = puede_operar_modulo_unidad(request.user, unidad, 'practicas')
    if reserva.usuario_id != request.user.pk and not es_operador:
        raise PermissionDenied('Solo quien programó la sesión puede completarla.')
    error = ''
    if request.method == 'POST':
        try:
            reserva = completar_sesion(reserva, request.POST, request.user, unidad_esperada=unidad.pk)
        except ValueError as excepcion:
            error = str(excepcion)
        else:
            return redirect(f"{reverse('completar_sesion', args=[reserva.pk])}?guardado=1")
        try:
            reserva.refresh_from_db()
        except Reserva.DoesNotExist:
            raise Http404 from None
    plan = _plan_de(reserva)
    numero, total = numero_de_sesion(reserva)
    seleccion, insumos = _insumos_de_formulario(reserva) if reserva.receta_id else (None, [])
    guia = plan.guia if plan else None
    return render(request, 'portal/pages/unidades/reservas/completar_sesion.html', {
        'unidad': unidad,
        'reserva': reserva,
        'plan': plan,
        'guia': guia,
        'numero': numero,
        'total': total,
        'editable': reserva.estado == 'pendiente',
        'error': error,
        'guardado': request.GET.get('guardado') == '1',
        'procesos': recetas_para_practica(unidad),
        'seleccion': seleccion,
        'insumos': insumos,
        'cantidad_actual': (
            format((reserva.receta.cantidad_base * (reserva.factor_proceso or Decimal('1'))).normalize(), 'f')
            if reserva.receta_id else ''
        ),
        'url_guia': (
            reverse('editar_guia_practica', args=[unidad.slug, guia.pk])
            if guia and guia.estado_publicacion in {'borrador', 'rechazada', 'revision'}
            else (reverse('ver_guia_actividad', args=[guia.pk]) if guia else '')
        ),
        'url_sesiones': reverse('mis_sesiones', args=[unidad.slug]),
        'aula': enlaces_del_aula(reserva),
        'page_title': f'Sesión {numero} de {total} · {unidad.nombre}',
    })


@login_required
def mis_sesiones_view(request, slug):
    """Las sesiones programadas de quien inicia sesión en esta unidad, con lo que les falta."""
    unidad = get_object_or_404(Unidad, slug=slug)
    sesiones = (
        Reserva.objects.filter(laboratorio=unidad, usuario=request.user, programacion__isnull=False)
        .select_related('programacion', 'programacion__asignatura', 'receta', 'laboratorio')
        .order_by('-programacion_id', 'fecha', 'pk')
    )
    numeros = {}
    for programacion_id in {sesion.programacion_id for sesion in sesiones}:
        ids = list(Reserva.objects.filter(programacion_id=programacion_id).order_by('fecha', 'pk').values_list('pk', flat=True))
        numeros.update({pk: (numero, len(ids)) for numero, pk in enumerate(ids, start=1)})
    planes = {
        plan.reserva_id: plan
        for plan in PlanificacionPractica.objects.filter(reserva__in=sesiones, eliminado_en__isnull=True)
        .select_related('guia', 'tema_asignatura')
    }
    filas = []
    for sesion in sesiones:
        plan = planes.get(sesion.pk)
        guia = plan.guia if plan else None
        numero, total = numeros.get(sesion.pk, (0, 0))
        programacion = sesion.programacion
        filas.append({
            'reserva': sesion,
            'numero': numero,
            'total': total,
            'programa': (
                programacion.asignatura.nombre if programacion.asignatura_id
                else (programacion.actividad.nombre if programacion.actividad_id else 'Programación')
            ),
            'tema': plan.tema if plan else sesion.titulo_solicitud,
            'proceso': sesion.receta.nombre if sesion.receta_id else '',
            'aula': enlaces_del_aula(sesion),
            'guia': guia,
            'guia_lista': bool(guia and guia.estado_publicacion == 'publicada' and guia.activo),
            'pendiente_materiales': sesion.estado == 'pendiente' and not sesion.receta_id,
            'url_completar': reverse('completar_sesion', args=[sesion.pk]),
            'url_comprobante': reverse('comprobante_reserva', args=[sesion.pk]),
            'url_guia': (
                reverse('editar_guia_practica', args=[unidad.slug, guia.pk])
                if guia and guia.estado_publicacion in {'borrador', 'rechazada', 'revision'}
                else (reverse('ver_guia_actividad', args=[guia.pk]) if guia else '')
            ),
        })
    return render(request, 'portal/pages/unidades/reservas/mis_sesiones.html', {
        'unidad': unidad,
        'filas': filas,
        'pendientes': sum(1 for fila in filas if fila['reserva'].estado in ESTADOS_ACTIVOS and (not fila['guia_lista'] or fila['pendiente_materiales'])),
        'page_title': f'Mis sesiones programadas · {unidad.nombre}',
    })
