"""Calidad e inocuidad: planes con parámetros y límites, controles por lote,
no conformidades con su disposición y acciones correctivas, y el plan HACCP.

El plan dice qué se mide y con qué límite en la recepción, en el proceso o
al liberar; el control lo aplica a un lote (de producto o de materia prima)
o a una corrida y decide: conforme, el lote de producto se libera; no
conforme, nace la no conformidad y el lote espera la disposición (reproceso,
liberación condicionada, rechazo, devolución). El plan HACCP junta los puntos
críticos de cada proceso con los parámetros que los vigilan.
"""

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from apps.core.identificadores import id_solicitado

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.plantas_piloto.operacion.models.calidad import AccionCorrectiva, ControlCalidad, MedicionCalidad, NoConformidad, ParametroCalidad, PlanCalidad
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, FamiliaProducto, LoteProducto, OrdenProduccion, Producto
from apps.directorio_unidades.models.core import Unidad

from apps.documentos.presentation.documentos_gestion import render_documento_oficial
from apps.plantas_piloto.operacion.presentation.sesiones_erp import exigir_misma_sesion, puede_operar_en
from apps.reservas.presentation.seguridad import buscar_persona


# ------------------------------------------------------------------ los planes
def planes_de(unidad, momento=None, familia=None, solo_transversales=False):
    planes = (
        PlanCalidad.objects.filter(unidad=unidad, activo=True)
        .select_related('producto', 'consumible', 'familia')
        .prefetch_related('parametros__etapa__receta')
        .order_by('momento', 'nombre', 'pk')
    )
    if momento:
        planes = planes.filter(momento=momento)
    if solo_transversales:
        planes = planes.filter(familia__isnull=True)
    elif familia:
        planes = planes.filter(Q(familia=familia) | Q(familia__isnull=True))
    return list(planes)


def plan_para_lote_producto(lote):
    return (
        PlanCalidad.objects.filter(unidad=lote.unidad, activo=True, momento='liberacion', producto=lote.producto)
        .order_by('pk').first()
    )


def plan_para_lote_consumible(lote, unidad):
    return (
        PlanCalidad.objects.filter(unidad=unidad, activo=True, momento='recepcion', consumible=lote.consumible)
        .order_by('pk').first()
    )


def plan_para_orden(orden):
    return (
        PlanCalidad.objects.filter(unidad=orden.unidad, activo=True, momento='proceso', producto=orden.producto)
        .order_by('pk').first()
    )


# ---------------------------------------------------------------- el control
def _valor_numerico(texto, parametro):
    try:
        return Decimal(str(texto).strip().replace(',', '.'))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError(f'El valor de {parametro.nombre} debe ser un número.') from error


def evaluar_plan(plan, datos):
    """Las mediciones de cada parámetro del plan, evaluadas contra su límite."""
    mediciones = []
    for parametro in plan.parametros_ordenados():
        bruto = str(datos.get(f'parametro_{parametro.pk}') or '').strip()
        if not bruto:
            raise ValidationError(f'Registra el valor de {parametro.nombre}.')
        if parametro.tipo == 'numerico':
            valor = _valor_numerico(bruto, parametro)
            mediciones.append({
                'parametro': parametro, 'valor_numerico': valor, 'valor_texto': '',
                'conforme': parametro.evaluar(valor_numerico=valor),
            })
        else:
            mediciones.append({
                'parametro': parametro, 'valor_numerico': None, 'valor_texto': bruto[:120],
                'conforme': parametro.evaluar(valor_texto=bruto),
            })
    if not mediciones:
        raise ValidationError('El plan no tiene parámetros que medir.')
    return mediciones


def _descripcion_no_conforme(plan, mediciones):
    fallas = []
    for medicion in mediciones:
        if medicion['conforme']:
            continue
        parametro = medicion['parametro']
        valor = medicion['valor_texto'] if medicion['valor_numerico'] is None else (
            f"{format(medicion['valor_numerico'].normalize(), 'f')}{' ' + parametro.unidad_medida if parametro.unidad_medida else ''}"
        )
        fallas.append(f'{parametro.nombre} = {valor} (límite: {parametro.limite_texto})')
    return f'Control «{plan.nombre}» no conforme: ' + '; '.join(fallas) + '.'


def registrar_control(unidad, plan, datos, usuario, *, lote_producto=None, lote_consumible=None, orden=None):
    """Mide el plan sobre un lote o una corrida y decide: libera el lote o abre la no conformidad."""
    if plan.unidad_id != unidad.pk or not plan.activo:
        raise ValidationError('El plan de calidad no pertenece a esta unidad o está inactivo.')
    if lote_producto is None and lote_consumible is None and orden is None:
        raise ValidationError('Elige el lote o la corrida que se controla.')
    mediciones = evaluar_plan(plan, datos)
    conforme = all(medicion['conforme'] for medicion in mediciones)
    with transaction.atomic():
        control = ControlCalidad.objects.create(
            unidad=unidad,
            plan=plan,
            lote_producto=lote_producto,
            lote_consumible=lote_consumible,
            orden=orden,
            registrado_por=usuario,
            resultado='conforme' if conforme else 'no_conforme',
            observaciones=str(datos.get('observaciones') or '').strip()[:2000],
        )
        MedicionCalidad.objects.bulk_create([
            MedicionCalidad(
                control=control,
                parametro=medicion['parametro'],
                valor_numerico=medicion['valor_numerico'],
                valor_texto=medicion['valor_texto'],
                conforme=medicion['conforme'],
            )
            for medicion in mediciones
        ])
        if conforme:
            if (
                lote_producto is not None
                and plan.momento == 'liberacion'
                and lote_producto.control_calidad == 'pendiente'
            ):
                lote_producto.aprobar_calidad()
        else:
            critica = any(not medicion['conforme'] and medicion['parametro'].critico for medicion in mediciones)
            NoConformidad.objects.create(
                unidad=unidad,
                control=control,
                lote_producto=lote_producto,
                lote_consumible=lote_consumible,
                descripcion=_descripcion_no_conforme(plan, mediciones),
                gravedad='critica' if critica else 'mayor',
                detectada_por=usuario,
            )
    return control


def decidir_no_conformidad(no_conformidad, datos, usuario):
    """La disposición del lote y el estado del tratamiento; el rechazo retira el lote."""
    estado = str(datos.get('estado') or no_conformidad.estado).strip()
    disposicion = str(datos.get('disposicion') or no_conformidad.disposicion).strip()
    if estado not in dict(NoConformidad.ESTADOS):
        raise ValidationError('Elige un estado válido.')
    if disposicion not in dict(NoConformidad.DISPOSICIONES):
        raise ValidationError('Elige una disposición válida.')
    if estado == 'cerrada' and disposicion == 'pendiente':
        raise ValidationError('Una no conformidad se cierra con su disposición decidida.')
    no_conformidad.causa = str(datos.get('causa') or '').strip()[:2000]
    lote_producto = no_conformidad.lote_producto
    lote_consumible = no_conformidad.lote_consumible
    with transaction.atomic():
        if disposicion == 'rechazo' and lote_producto is not None and lote_producto.control_calidad != 'rechazado':
            lote_producto.rechazar_calidad(
                usuario=usuario, motivo=f'{no_conformidad.codigo}: {no_conformidad.descripcion[:200]}',
            )
        if disposicion in ('rechazo', 'devolucion') and lote_consumible is not None and lote_consumible.estado != 'retirado':
            lote_consumible.estado = 'retirado'
            lote_consumible.equipo_en_uso = None
            lote_consumible.observaciones = (
                f'{lote_consumible.observaciones}\nRetirado por {no_conformidad.codigo}: {disposicion}.'
            ).strip()
            lote_consumible.save(update_fields=['estado', 'equipo_en_uso', 'observaciones', 'actualizado_en'])
        if (
            disposicion == 'liberacion_condicionada'
            and lote_producto is not None
            and lote_producto.control_calidad == 'pendiente'
        ):
            lote_producto.aprobar_calidad()
        no_conformidad.disposicion = disposicion
        no_conformidad.estado = estado
        no_conformidad.cerrada_en = timezone.now() if estado == 'cerrada' else None
        no_conformidad.save(update_fields=['causa', 'disposicion', 'estado', 'cerrada_en', 'actualizado_en'])
    return no_conformidad


# ------------------------------------------------------------------ el HACCP
def plan_haccp(unidad, procesos):
    """Los puntos críticos de cada proceso con los parámetros que los vigilan y la acción prevista."""
    parametros_por_etapa = {}
    for parametro in (
        ParametroCalidad.objects.filter(
            plan__unidad=unidad, plan__activo=True, activo=True, etapa__isnull=False,
        )
        .select_related('plan', 'etapa')
        .order_by('plan__momento', 'orden', 'pk')
    ):
        parametros_por_etapa.setdefault(parametro.etapa_id, []).append(parametro)
    from apps.plantas_piloto.operacion.presentation.diagramas import diagrama_flujo, numeros_pcc
    from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta
    resultado = []
    for receta in procesos:
        # El Codex (CXC 1-1969) pide el diagrama de flujo con los PCC: los mismos números aquí y en él.
        datos = datos_de_receta(receta)
        numeros = numeros_pcc(datos['etapas'])
        filas = []
        for etapa in receta.etapas.filter(punto_critico=True).select_related('equipo').order_by('orden'):
            filas.append({
                'etapa': etapa,
                'codigo': numeros.get(etapa.orden, ''),
                'peligro': etapa.parametro or 'Parámetro del proceso',
                'limite': etapa.limite or '—',
                'parametros': parametros_por_etapa.get(etapa.pk, []),
                'monitoreo': 'En cada corrida, por quien conduce la etapa; queda en el control del lote.',
                'accion': 'Detener la etapa, corregir y registrar la no conformidad; el lote espera su disposición.',
            })
        resultado.append({'receta': receta, 'filas': filas, 'diagrama': diagrama_flujo(datos).svg()})
    return resultado


# ------------------------------------------------------------- indicadores
def indicadores_calidad(unidad):
    hoy = timezone.localdate()
    desde = timezone.now() - timedelta(days=30)
    controles = ControlCalidad.objects.reales().filter(unidad=unidad, fecha__gte=desde)
    total = controles.count()
    conformes = controles.filter(resultado='conforme').count()
    abiertas = NoConformidad.objects.reales().filter(unidad=unidad).exclude(estado='cerrada')
    return {
        'controles_30': total,
        'conformidad_pct': round(conformes * 100 / total) if total else 100,
        'no_conformidades_abiertas': abiertas.count(),
        'criticas_abiertas': abiertas.filter(gravedad='critica').count(),
        'acciones_pendientes': AccionCorrectiva.objects.filter(
            no_conformidad__unidad=unidad, estado='pendiente',
        ).count(),
        'acciones_vencidas': AccionCorrectiva.objects.filter(
            no_conformidad__unidad=unidad, estado='pendiente', fecha_compromiso__lt=hoy,
        ).count(),
        'lotes_por_liberar': LoteProducto.objects.reales().filter(unidad=unidad, control_calidad='pendiente').count(),
    }


# ---------------------------------------------------------------- el panel
def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def _decimal_opcional(texto, nombre):
    texto = (texto or '').strip()
    if not texto:
        return None
    try:
        return Decimal(texto.replace(',', '.'))
    except InvalidOperation as error:
        raise ValidationError(f'{nombre} debe ser un número.') from error


def contexto_calidad(unidad, permisos_operativos, configuracion, sesion=None):
    """Lo que la pestaña de calidad muestra; una unidad que no produce lotes no la abre."""
    puede = bool(permisos_operativos.get('produccion'))
    if not configuracion.registra_produccion:
        return {'calidad_habilitada': False, 'puede_operar_calidad': False}
    planes = planes_de(unidad)
    for plan in planes:
        plan.lista_parametros = plan.parametros_ordenados()
    lotes_por_liberar = []
    for lote in (
        LoteProducto.objects.en_sesion(sesion).filter(unidad=unidad, control_calidad='pendiente')
        .select_related('producto', 'orden')
        .order_by('fecha_produccion', 'pk')[:40]
    ):
        lotes_por_liberar.append({
            'lote': lote,
            'plan': plan_para_lote_producto(lote),
            'url': reverse('control_calidad', args=[unidad.slug]) + f'?lote_producto={lote.pk}',
        })
    recepciones = []
    # Lo que entra por un pedido se controla igual que el material del cliente; en una
    # sesión lo recibido suma a sus existencias y no hay lotes de insumo que controlar.
    for lote in (
        LoteConsumible.objects.none() if sesion is not None else LoteConsumible.objects.filter(consumible__unidad=unidad)
        .filter(Q(material_cliente=True) | Q(movimientos__entregas_pedido__isnull=False))
        .exclude(estado__in=('retirado', 'agotado'))
        .annotate(controles=Count('controles_calidad'))
        .filter(controles=0)
        .select_related('consumible', 'reserva')
        .distinct()
        .order_by('-fecha_ingreso', '-pk')[:40]
    ):
        if not lote.material_cliente and plan_para_lote_consumible(lote, unidad) is None:
            continue
        recepciones.append({
            'lote': lote,
            'plan': plan_para_lote_consumible(lote, unidad),
            'url': reverse('control_calidad', args=[unidad.slug]) + f'?lote_consumible={lote.pk}',
        })
    controles = list(
        ControlCalidad.objects.en_sesion(sesion).filter(unidad=unidad)
        .select_related('plan', 'lote_producto', 'lote_consumible', 'orden', 'registrado_por')
        .prefetch_related('mediciones__parametro')
        .order_by('-fecha', '-pk')[:40]
    )
    no_conformidades = list(
        NoConformidad.objects.en_sesion(sesion).filter(unidad=unidad)
        .select_related('lote_producto', 'lote_consumible', 'control', 'detectada_por')
        .prefetch_related('acciones__responsable')
        .order_by('-detectada_en', '-pk')[:60]
    )
    etapas = list(
        EtapaReceta.objects.filter(receta__unidad=unidad, receta__activa=True)
        .select_related('receta')
        .order_by('receta__nombre', 'orden')
    )
    return {
        # El personal de la planta consulta la calidad; la opera con el permiso de producción.
        'calidad_habilitada': True,
        'puede_operar_calidad': puede,
        'calidad_metricas': indicadores_calidad(unidad),
        'planes_calidad': planes,
        'lotes_por_liberar': lotes_por_liberar,
        'recepciones_por_controlar': recepciones,
        'controles_calidad': controles,
        'no_conformidades': no_conformidades,
        'momentos_calidad': PlanCalidad.MOMENTOS,
        'tipos_parametro': ParametroCalidad.TIPOS,
        'gravedades_nc': NoConformidad.GRAVEDADES,
        'estados_nc': NoConformidad.ESTADOS,
        'disposiciones_nc': NoConformidad.DISPOSICIONES,
        'estados_accion': AccionCorrectiva.ESTADOS,
        'productos_para_calidad': list(Producto.objects.filter(unidad=unidad, activo=True).order_by('nombre')),
        'consumibles_para_calidad': list(Consumible.objects.filter(unidad=unidad, activo=True).order_by('nombre')),
        'etapas_para_calidad': etapas,
        'plan_haccp_url': reverse('plan_haccp', args=[unidad.slug]),
        'hoy_calidad': timezone.localdate(),
    }


def seccion_calidad(contexto):
    metricas = contexto['calidad_metricas']
    return {
        'clave': 'calidad',
        'titulo': 'Calidad e inocuidad',
        'descripcion': 'Planes con parámetros y límites, controles por lote, no conformidades y acciones; plan HACCP.',
        'icono': 'iconsminds-check',
        'dato': f"{metricas['lotes_por_liberar']} lotes por liberar",
        'etiqueta': f"{metricas['no_conformidades_abiertas']} no conformidades abiertas"
        + ('' if contexto['puede_operar_calidad'] else ' · solo consulta'),
        'habilitada': contexto['calidad_habilitada'],
    }


def operar_plan_calidad(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(PlanCalidad.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id else PlanCalidad(unidad=unidad)
    )
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el plan que quieres desactivar.')
        objeto.activo = False
        objeto.save(update_fields=['activo', 'actualizado_en'])
        return objeto, 'Plan de calidad desactivado', False
    objeto.codigo = _texto(request, 'codigo', 40).upper()
    objeto.nombre = _texto(request, 'nombre', 160)
    objeto.momento = _texto(request, 'momento') or 'liberacion'
    if objeto.momento not in dict(PlanCalidad.MOMENTOS):
        raise ValidationError('Elige el momento del control.')
    producto_id = _texto(request, 'producto_id')
    consumible_id = _texto(request, 'consumible_id')
    objeto.producto = get_object_or_404(Producto, pk=producto_id, unidad=unidad) if producto_id else None
    objeto.consumible = get_object_or_404(Consumible, pk=consumible_id, unidad=unidad) if consumible_id else None
    familia_id = _texto(request, 'familia_id')
    objeto.familia = objeto.producto.familia if objeto.producto_id else (
        get_object_or_404(FamiliaProducto, pk=familia_id, unidad=unidad, activa=True)
        if familia_id else None
    )
    if objeto.momento == 'recepcion' and objeto.consumible is None:
        raise ValidationError('Un plan de recepción dice qué materia prima recibe.')
    if objeto.momento != 'recepcion' and objeto.producto is None:
        raise ValidationError('Un plan de proceso o de liberación dice a qué producto aplica.')
    objeto.descripcion = _texto(request, 'descripcion')
    objeto.activo = True
    objeto.full_clean()
    objeto.save()
    return objeto, 'Plan de calidad creado' if creado else 'Plan de calidad actualizado', creado


def operar_parametro_calidad(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(ParametroCalidad.objects.select_for_update(), pk=registro_id, plan__unidad=unidad)
        if registro_id else ParametroCalidad()
    )
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el parámetro que quieres quitar.')
        objeto.activo = False
        objeto.save(update_fields=['activo'])
        return objeto, 'Parámetro desactivado', False
    plan_id = _texto(request, 'plan_id')
    if not plan_id:
        raise ValidationError('Selecciona el plan del parámetro.')
    objeto.plan = get_object_or_404(PlanCalidad, pk=plan_id, unidad=unidad)
    orden = _texto(request, 'orden')
    objeto.orden = int(orden) if orden.isdigit() and int(orden) > 0 else 1
    objeto.nombre = _texto(request, 'nombre', 120)
    objeto.tipo = _texto(request, 'tipo') or 'numerico'
    if objeto.tipo not in dict(ParametroCalidad.TIPOS):
        raise ValidationError('Elige el tipo del parámetro.')
    objeto.unidad_medida = _texto(request, 'unidad_medida', 30)
    objeto.minimo = _decimal_opcional(request.POST.get('minimo'), 'El mínimo')
    objeto.maximo = _decimal_opcional(request.POST.get('maximo'), 'El máximo')
    if objeto.tipo == 'numerico' and objeto.minimo is None and objeto.maximo is None:
        raise ValidationError('Un parámetro numérico necesita un mínimo, un máximo o ambos.')
    if objeto.minimo is not None and objeto.maximo is not None and objeto.minimo > objeto.maximo:
        raise ValidationError('El mínimo no puede superar al máximo.')
    objeto.valor_esperado = _texto(request, 'valor_esperado', 120)
    objeto.metodo = _texto(request, 'metodo', 200)
    etapa_id = _texto(request, 'etapa_id')
    objeto.etapa = get_object_or_404(EtapaReceta, pk=etapa_id, receta__unidad=unidad) if etapa_id else None
    objeto.critico = str(request.POST.get('critico') or '').strip().lower() in {'on', 'true', '1', 'si', 'sí'}
    objeto.activo = True
    objeto.full_clean()
    objeto.save()
    return objeto, 'Parámetro creado' if creado else 'Parámetro actualizado', creado


def sesion_de_la_no_conformidad(no_conformidad):
    """La sesión del lote o de la corrida donde se detectó; sin ella, la producción real."""
    if no_conformidad.lote_producto_id and no_conformidad.lote_producto.orden_id:
        return no_conformidad.lote_producto.orden.sesion_id
    if no_conformidad.control_id and no_conformidad.control.orden_id:
        return no_conformidad.control.orden.sesion_id
    return None


def operar_no_conformidad(request, unidad):
    registro_id = _texto(request, 'registro_id')
    if not registro_id:
        raise ValidationError('Selecciona la no conformidad.')
    objeto = get_object_or_404(NoConformidad.objects.select_for_update(), pk=registro_id, unidad=unidad)
    exigir_misma_sesion(sesion_de_la_no_conformidad(objeto), request)
    decidir_no_conformidad(objeto, request.POST, request.user)
    return objeto, 'No conformidad actualizada', False


def operar_accion_correctiva(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(
            AccionCorrectiva.objects.select_for_update(), pk=registro_id, no_conformidad__unidad=unidad,
        )
        if registro_id else AccionCorrectiva()
    )
    if registro_id:
        exigir_misma_sesion(sesion_de_la_no_conformidad(objeto.no_conformidad), request)
    if creado:
        no_conformidad_id = _texto(request, 'no_conformidad_id')
        if not no_conformidad_id:
            raise ValidationError('Selecciona la no conformidad de la acción.')
        objeto.no_conformidad = get_object_or_404(NoConformidad, pk=no_conformidad_id, unidad=unidad)
        exigir_misma_sesion(sesion_de_la_no_conformidad(objeto.no_conformidad), request)
    objeto.descripcion = _texto(request, 'descripcion', 2000)
    if not objeto.descripcion:
        raise ValidationError('Describe la acción correctiva.')
    responsable = _texto(request, 'responsable', 150)
    if responsable:
        persona = buscar_persona(responsable)
        if persona is None:
            raise ValidationError('No encontramos a esa persona: escribe su usuario institucional, su correo o su cédula.')
        objeto.responsable = persona
    compromiso = _texto(request, 'fecha_compromiso')
    objeto.fecha_compromiso = datetime.strptime(compromiso, '%Y-%m-%d').date() if compromiso else None
    estado = _texto(request, 'estado') or 'pendiente'
    if estado not in dict(AccionCorrectiva.ESTADOS):
        raise ValidationError('Elige el estado de la acción.')
    objeto.estado = estado
    objeto.verificacion = _texto(request, 'verificacion', 2000)
    objeto.fecha_cierre = timezone.localdate() if estado != 'pendiente' else None
    objeto.full_clean()
    objeto.save()
    if objeto.no_conformidad.estado == 'abierta':
        objeto.no_conformidad.estado = 'en_tratamiento'
        objeto.no_conformidad.save(update_fields=['estado', 'actualizado_en'])
    return objeto, 'Acción registrada' if creado else 'Acción actualizada', creado


OPERADORES_CALIDAD = {
    'plan_calidad': operar_plan_calidad,
    'parametro_calidad': operar_parametro_calidad,
    'no_conformidad': operar_no_conformidad,
    'accion_correctiva': operar_accion_correctiva,
}
PERMISOS_CALIDAD = {clave: 'produccion' for clave in OPERADORES_CALIDAD}
MODELOS_CALIDAD = {
    'plan_calidad': PlanCalidad,
    'parametro_calidad': ParametroCalidad,
    'no_conformidad': NoConformidad,
    'accion_correctiva': AccionCorrectiva,
}


# ---------------------------------------------------------------- las vistas
def _objeto_controlado(request, unidad):
    """El lote o la corrida que se controla, y el plan que le corresponde."""
    claves = {campo: id_solicitado(request.GET[campo]) if request.GET.get(campo) else None
              for campo in ('lote_producto', 'lote_consumible', 'orden', 'plan')}
    lote_producto = lote_consumible = orden = None
    if claves['lote_producto'] is not None:
        lote_producto = get_object_or_404(
            LoteProducto.objects.select_related('producto'), pk=claves['lote_producto'], unidad=unidad,
        )
    elif claves['lote_consumible'] is not None:
        lote_consumible = get_object_or_404(
            LoteConsumible.objects.select_related('consumible'), pk=claves['lote_consumible'],
            consumible__unidad=unidad,
        )
    elif claves['orden'] is not None:
        orden = get_object_or_404(OrdenProduccion.objects.select_related('producto', 'receta'), pk=claves['orden'], unidad=unidad)
    plan = None
    if claves['plan'] is not None:
        plan = get_object_or_404(PlanCalidad, pk=claves['plan'], unidad=unidad, activo=True)
    elif lote_producto is not None:
        plan = plan_para_lote_producto(lote_producto)
    elif lote_consumible is not None:
        plan = plan_para_lote_consumible(lote_consumible, unidad)
    elif orden is not None:
        plan = plan_para_orden(orden)
    return plan, lote_producto, lote_consumible, orden


@login_required
@require_http_methods(['GET', 'POST'])
def control_calidad_view(request, slug):
    """El control de un lote o una corrida: los parámetros del plan, medidos y evaluados."""
    unidad = get_object_or_404(Unidad, slug=slug)
    plan, lote_producto, lote_consumible, orden = _objeto_controlado(request, unidad)
    corrida = orden or (lote_producto.orden if lote_producto is not None and lote_producto.orden_id else None)
    sesion = corrida.sesion if corrida is not None else None
    if not puede_operar_en(request.user, unidad, sesion):
        raise PermissionDenied('Solo quien opera la producción, o participa en la sesión, registra controles.')
    error = ''
    control = None
    if request.method == 'POST':
        try:
            if plan is None:
                raise ValidationError('No hay un plan de calidad activo para lo que quieres controlar.')
            control = registrar_control(
                unidad, plan, request.POST, request.user,
                lote_producto=lote_producto, lote_consumible=lote_consumible, orden=orden,
            )
        except ValidationError as excepcion:
            error = ' '.join(excepcion.messages)
        else:
            # La recarga vuelve al mismo lote con el control recién hecho, sin arrastrar
            # la cadena de consultas anteriores.
            consulta = {'plan': plan.pk, 'hecho': control.pk}
            if lote_producto is not None:
                consulta['lote_producto'] = lote_producto.pk
            elif lote_consumible is not None:
                consulta['lote_consumible'] = lote_consumible.pk
            elif orden is not None:
                consulta['orden'] = orden.pk
            return redirect(f'{request.path}?{urlencode(consulta)}')
    hecho = None
    if request.GET.get('hecho'):
        hecho = (
            ControlCalidad.objects.filter(pk=id_solicitado(request.GET['hecho']), unidad=unidad)
            .select_related('plan').prefetch_related('mediciones__parametro', 'no_conformidades').first()
        )
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/control_calidad.html', {
        'unidad': unidad,
        'plan': plan,
        'parametros': plan.parametros_ordenados() if plan else [],
        'planes': planes_de(unidad),
        'lote_producto': lote_producto,
        'lote_consumible': lote_consumible,
        'orden': orden,
        'error': error,
        'hecho': hecho,
        'generado_en': timezone.localtime(),
        'volver_url': reverse('erp_planta', args=[unidad.slug]) + '?view=calidad' + (
            f'&sesion={sesion.codigo}' if sesion is not None else ''
        ),
    })


@xframe_options_sameorigin
def plan_haccp_view(request, slug):
    """El plan HACCP de la unidad: puntos críticos de cada proceso, límites, vigilancia y acción."""
    from apps.formacion.presentation.aula import procesos_publicos

    unidad = get_object_or_404(Unidad, slug=slug)
    procesos = procesos_publicos(unidad)
    familia_codigo = (request.GET.get('familia') or '').strip().upper()
    familia = None
    if familia_codigo:
        familia = get_object_or_404(FamiliaProducto, unidad=unidad, codigo=familia_codigo, activa=True)
        procesos = [proceso for proceso in procesos if proceso.familia_id == familia.pk]
    if not procesos:
        raise Http404('La unidad no publica procesos')
    return render_documento_oficial(request, 'portal/pages/unidades/gestion/plan_haccp.html', {
        'unidad': unidad,
        'haccp': plan_haccp(unidad, procesos),
        'planes': planes_de(unidad),
        'familia_activa': familia,
        'generado_en': timezone.localtime(),
        'volver_url': unidad.get_absolute_url(),
    })


def calidad_publicada(unidad, familia=None, solo_transversales=False):
    """Lo que la ficha publica: qué mide cada plan, con qué límite, y cuánto se controló.

    Sin mediciones ni nombres: quien mira la unidad desde afuera ve el compromiso de
    control, no el expediente interno de cada lote.
    """
    planes = [
        {'plan': plan, 'parametros': plan.parametros_ordenados()}
        for plan in planes_de(
            unidad, familia=familia, solo_transversales=solo_transversales,
        )
    ]
    controles = ControlCalidad.objects.reales().filter(unidad=unidad)
    return {
        'planes': planes,
        'parametros_totales': sum(len(item['parametros']) for item in planes),
        'controles': controles.count(),
        'conformes': controles.filter(resultado='conforme').count(),
        'no_conformidades_abiertas': (
            NoConformidad.objects.reales().filter(unidad=unidad).exclude(estado='cerrada').count()
        ),
    }
