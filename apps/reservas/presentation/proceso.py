"""La práctica por proceso: lo que el proceso exige, marcado por defecto.

En una unidad que produce, el docente o el investigador no elige máquina por
máquina: elige el proceso y la escala. De las etapas salen las áreas, los
equipos con sus auxiliares, el software, los insumos escalados y la duración
de la sesión; lo obligatorio no se puede quitar y el solicitante completa
solo lo que únicamente él sabe. La solicitud entra por el mismo motor que
cualquier reserva de recursos y, al aprobarse, nace la orden de producción
de la práctica.
"""

from html import escape
from decimal import Decimal, InvalidOperation
from math import ceil

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_time
from django.views.decorators.http import require_GET

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.gestion_unidades.models.operaciones import HORA_ALMUERZO, ventana_atencion

from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta, guia_desde_proceso, resumen_proceso, unidad_en_plural
from apps.reservas.presentation.seguridad import proteccion_por_persona

TRES = Decimal('0.001')


def _texto(valor):
    return format(Decimal(str(valor)).quantize(TRES).normalize(), 'f')


def factor_valido(valor):
    """El factor de la corrida como decimal positivo, o un error legible."""
    try:
        factor = Decimal(str(valor or '1').replace(',', '.'))
    except InvalidOperation as error:
        raise ValueError('La escala del proceso debe ser un número.') from error
    if factor <= 0 or factor > 1000:
        raise ValueError('La escala del proceso debe estar entre 0,001 y 1000 corridas base.')
    return factor.quantize(TRES)


def recetas_para_practica(unidad):
    """Las recetas activas con etapas de una unidad que registra producción."""
    try:
        if not unidad.configuracion_operativa.registra_produccion:
            return []
    except ObjectDoesNotExist:
        return []
    return [
        receta
        for receta in Receta.objects.filter(unidad=unidad, activa=True)
        .select_related('producto', 'familia')
        .prefetch_related('etapas')
        .order_by('nombre')
        if receta.etapas.exists()
    ]


def catalogo_para_reserva(unidad):
    """Todas las familias y productos, con sus procesos técnicos disponibles.

    El producto pertenece al catálogo institucional aunque su receta todavía
    no haya sido levantada. Así puede identificarse en una reserva manual sin
    presentar como validada una ruta técnica que no existe.
    """
    recetas = recetas_para_practica(unidad)
    por_producto = {}
    for receta in recetas:
        por_producto.setdefault(receta.producto_id, []).append(receta)
    productos = (
        Producto.objects.filter(
            unidad=unidad,
            activo=True,
            publico=True,
            tipo__in=Producto.TIPOS_PUBLICOS,
            familia__activa=True,
        )
        .select_related('familia')
        .order_by('familia__orden', 'familia__nombre', 'nombre')
    )
    familias = []
    for producto in productos:
        if not familias or familias[-1]['id'] != producto.familia_id:
            familias.append({
                'id': producto.familia_id,
                'nombre': producto.familia.nombre,
                'orden': producto.familia.orden,
                'productos': [],
            })
        procesos = por_producto.get(producto.pk, [])
        familias[-1]['productos'].append({
            'id': producto.pk,
            'nombre': producto.nombre,
            'unidad_medida': producto.unidad_medida,
            'procesos': [
                {
                    'id': receta.pk,
                    'nombre': receta.nombre_publico,
                    'etapas': receta.etapas.count(),
                    'cantidad_base': format(receta.cantidad_base.normalize(), 'f'),
                    'unidad_base': receta.unidad_base,
                    'rinde': format(receta.rendimiento_esperado.normalize(), 'f'),
                    'unidad_producto': receta.producto.unidad_medida,
                }
                for receta in procesos
            ],
        })
    return familias


def seleccion_por_proceso(receta, factor, *, hora_inicio=None, es_administrador=False, personas=None):
    """Todo lo que el proceso exige para una corrida de `factor` veces la base."""
    factor = Decimal(str(factor))
    unidad = receta.unidad
    datos = datos_de_receta(receta, factor)
    resumen = resumen_proceso(datos)
    etapas = list(receta.etapas.select_related('equipo', 'espacio').order_by('orden'))

    espacios, vistos = [], set()
    for etapa in etapas:
        espacio = etapa.espacio if etapa.espacio_id else None
        if espacio is None or espacio.pk in vistos or not (espacio.activo and espacio.reservable):
            continue
        vistos.add(espacio.pk)
        espacios.append({
            'id': espacio.pk,
            'nombre': espacio.nombre,
            'tipo': espacio.get_tipo_display(),
            'etapas': [e.orden for e in etapas if e.espacio_id == espacio.pk],
            'obligatorio': True,
        })

    modelos = {}
    for etapa in etapas:
        if etapa.equipo_id:
            modelos.setdefault(etapa.equipo_id, {'equipo': etapa.equipo, 'etapas': []})['etapas'].append(etapa.orden)
    equipos, faltantes = [], []
    for equipo_id, info in modelos.items():
        unidad_equipo = (
            UnidadEquipo.objects.filter(equipo_id=equipo_id, activa=True, estado_unidad='disponible')
            .filter(Q(laboratorio=unidad) | Q(laboratorios=unidad))
            .order_by('codigo_unidad')
            .first()
        )
        if unidad_equipo is None:
            faltantes.append(f'{info["equipo"].nombre}: sin una unidad disponible en la planta')
            continue
        equipos.append({
            'id': unidad_equipo.pk,
            'codigo': unidad_equipo.codigo_unidad,
            'equipo_id': info['equipo'].pk,
            'equipo_codigo': info['equipo'].codigo,
            'equipo_nombre': info['equipo'].nombre,
            'ubicacion': unidad_equipo.ubicacion_especifica or '',
            'etapas': info['etapas'],
            'auxiliares': [aux.nombre for aux in info['equipo'].auxiliares.filter(estado='disponible')],
            'obligatorio': True,
        })

    # Cada equipo se usa donde la planta lo publica: si ninguna etapa lo ubica
    # en su área, esa área entra en la selección y la solicitud sigue siendo válida.
    for info in equipos:
        ubicaciones = list(
            EspacioReservable.objects.filter(
                unidad=unidad, activo=True, reservable=True, equipos_asociados=info['id']
            ).order_by('nombre')
        )
        if ubicaciones and not any(espacio.pk in vistos for espacio in ubicaciones):
            espacio = ubicaciones[0]
            vistos.add(espacio.pk)
            espacios.append({
                'id': espacio.pk,
                'nombre': espacio.nombre,
                'tipo': espacio.get_tipo_display(),
                'etapas': info['etapas'],
                'obligatorio': True,
            })

    software = [
        {
            'id': programa.pk,
            'nombre': programa.nombre,
            'version': programa.version,
            'acceso': programa.get_tipo_acceso_display(),
            'obligatorio': False,
        }
        for programa in receta.software.filter(activo=True, requiere_reserva=True, licencias_disponibles__gt=0)
    ]

    insumos = []
    for item in receta.insumos_para(factor):
        consumible = item['consumible']
        insumos.append({
            'id': consumible.pk,
            'nombre': consumible.nombre,
            'cantidad': _texto(item['cantidad']),
            'unidad': consumible.unidad_medida,
            'clasificacion': consumible.get_clasificacion_display(),
            'etapa': item['etapa'],
            'obligatorio': bool(item['obligatorio']),
            'agotado': consumible.stock_total <= 0,
        })

    # La misma receta gobierna la ayuda visual del asistente. Cada estación de
    # la ruta conserva su área, equipo e insumos para que la persona entienda
    # por qué el sistema los propone y en qué orden se utilizarán.
    insumos_por_etapa = {}
    for insumo in insumos:
        if insumo['etapa'] is not None:
            insumos_por_etapa.setdefault(insumo['etapa'], []).append(insumo['nombre'])
    ruta = [
        {
            'orden': etapa.orden,
            'nombre': etapa.nombre,
            'tipo': etapa.get_tipo_display(),
            'simbolo': etapa.simbolo,
            'duracion_min': etapa.duracion_min,
            'espera_min': etapa.espera_min,
            'espacio': etapa.espacio.nombre if etapa.espacio_id else '',
            'equipo': etapa.equipo.nombre if etapa.equipo_id else '',
            'insumos': insumos_por_etapa.get(etapa.orden, []),
            'punto_critico': etapa.punto_critico,
        }
        for etapa in etapas
    ]

    # La protección que la planta entrega por persona sale del inventario con la práctica.
    personas = max(1, int(personas or resumen['personas_max'] or 1))
    ya_pedidos = {insumo['id'] for insumo in insumos}
    for fila in proteccion_por_persona(unidad, 'estudiante', personas):
        consumible = fila['consumible']
        if consumible.pk in ya_pedidos:
            continue
        insumos.append({
            'id': consumible.pk,
            'nombre': consumible.nombre,
            'cantidad': _texto(fila['cantidad']),
            'unidad': consumible.unidad_medida,
            'clasificacion': 'Protección por persona',
            'etapa': None,
            'obligatorio': fila['requisito'].obligatorio,
            'agotado': consumible.stock_total <= 0,
        })

    # La sesión: hasta la última etapa con personas, sin contar el almacenamiento.
    apertura, cierre = ventana_atencion(unidad.configuracion_operativa, es_administrador=es_administrador)
    inicio = hora_inicio.hour if hora_inicio else apertura
    inicio = min(max(inicio, apertura), max(apertura, cierre - 1))
    ultimo_trabajado = max((i for i, e in enumerate(etapas) if e.personas > 0), default=-1)
    minutos_sesion = sum(
        e.duracion_min + (e.espera_min if e.tipo != 'almacenamiento' else 0)
        for e in etapas[:ultimo_trabajado + 1]
    )
    horas_necesarias = max(1, ceil(minutos_sesion / 60))
    fin = min(inicio + horas_necesarias, cierre)
    horas = list(range(inicio, fin))
    jornada_min = max(60, (cierre - apertura) * 60)
    # Lo trabajado que no cabe en la sesión ocupa jornadas más; el reposo y el
    # almacenamiento corren día y noche, así que cuentan en días de calendario.
    trabajo_pendiente = max(0, minutos_sesion - len(horas) * 60)
    reposo = max(0, resumen['duracion_min'] - minutos_sesion)
    dias_extra = ceil(trabajo_pendiente / jornada_min) + ceil(reposo / 1440)
    sesion = {
        'hora_inicio': f'{inicio:02d}:00',
        'hora_fin': f'{fin:02d}:00',
        'horas': horas,
        'minutos_sesion': minutos_sesion,
        'minutos_trabajo': resumen['trabajo_min'],
        'minutos_totales': resumen['duracion_min'],
        'cabe_en_jornada': inicio + horas_necesarias <= cierre,
        'cruza_almuerzo': HORA_ALMUERZO in horas,
        'dias_extra': dias_extra,
        'apertura': f'{apertura:02d}:00',
        'cierre': f'{cierre:02d}:00',
    }
    return {
        'receta_id': receta.pk,
        'proceso': datos['nombre'],
        'producto': datos['producto'],
        'factor': _texto(factor),
        'escala': f"{_texto(Decimal(datos['cantidad_base']) * factor)} {datos['unidad_base']}",
        'producto_esperado': (
            f"{_texto(Decimal(datos['rendimiento_esperado']) * factor)} "
            f"{unidad_en_plural(datos['unidad_producto'], Decimal(datos['rendimiento_esperado']) * factor)}"
        ),
        'personas_max': resumen['personas_max'],
        'puntos_criticos': resumen['puntos_criticos'],
        'espacios': espacios,
        'equipos': equipos,
        'software': software,
        'insumos': insumos,
        'ruta': ruta,
        'faltantes': faltantes,
        'sesion': sesion,
        'piezas': max(1, ceil(factor)),
        'personas': personas,
    }


def validar_cobertura_del_proceso(receta, equipos, espacios, consumibles):
    """Lo obligatorio del proceso tiene que estar en la solicitud."""
    etapas = list(receta.etapas.select_related('equipo', 'espacio').order_by('orden'))
    # El motor entrega los modelos de equipo pedidos, no las unidades concretas.
    modelos_pedidos = {equipo.pk for equipo in equipos}
    espacios_pedidos = {espacio.pk for espacio in espacios}
    consumibles_pedidos = {consumible.pk for consumible, _cantidad, _metodo in consumibles}
    faltan = []
    for etapa in etapas:
        if etapa.equipo_id and etapa.equipo_id not in modelos_pedidos:
            faltan.append(f'{etapa.equipo.nombre} (equipo de la etapa {etapa.orden})')
            modelos_pedidos.add(etapa.equipo_id)
        if (
            etapa.espacio_id
            and etapa.espacio.activo and etapa.espacio.reservable
            and etapa.espacio_id not in espacios_pedidos
        ):
            faltan.append(f'{etapa.espacio.nombre} (área de la etapa {etapa.orden})')
            espacios_pedidos.add(etapa.espacio_id)
    for insumo in receta.insumos.select_related('consumible').filter(obligatorio=True):
        if insumo.consumible_id not in consumibles_pedidos:
            faltan.append(f'{insumo.consumible.nombre} (insumo obligatorio)')
    if faltan:
        raise ValueError(
            f'El proceso «{receta.nombre}» exige recursos que no están en la solicitud: '
            + '; '.join(faltan)
            + '. Elige el proceso en el asistente para que la planta los marque.'
        )


def guia_integrada_desde_proceso(receta, factor, *, asignatura='', escala=''):
    """Los apartados obligatorios de la guía FT04, prellenados desde el proceso."""
    datos = datos_de_receta(receta, factor)
    guia = guia_desde_proceso(datos)
    objetivos = [
        f'Elaborar {receta.producto.nombre.lower()} siguiendo el proceso «{receta.nombre}» a escala de {escala or "una corrida base"}.',
        'Operar cada equipo del proceso dentro de sus parámetros y registrar los puntos críticos de control.',
        'Calcular el balance de masa de la corrida y comparar el rendimiento obtenido con el esperado.',
    ]
    return {
        'guia_asignatura': asignatura,
        'guia_resultado_aprendizaje': (
            f'<p>Conduce el proceso de {escape(receta.producto.nombre.lower())} de principio a fin en la planta, '
            'con buenas prácticas de manufactura, control de los puntos críticos y registro trazable de '
            'lo que entra y lo que sale.</p>'
        ),
        'guia_objetivos': '<ul>' + ''.join(f'<li>{escape(objetivo)}</li>' for objetivo in objetivos) + '</ul>',
        'guia_procedimiento': guia['procedimiento_html'],
        'guia_medidas_seguridad': guia['seguridad_html'],
        'guia_resultados_esperados': guia['resultados_html'],
        'guia_formato_procedimiento': 'numerado',
        'guia_formato_contenido': 'html',
        'equipos': guia['equipos'],
        'software': guia['software'],
        'materiales': guia['materiales'],
        'duracion': guia['duracion'],
    }


# ------------------------------------------------------------------ vistas
def _receta_de_practica(slug, receta_id):
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    receta = get_object_or_404(
        Receta.objects.select_related('producto', 'unidad'), pk=receta_id, unidad=unidad, activa=True
    )
    if not any(r.pk == receta.pk for r in recetas_para_practica(unidad)):
        raise Http404('Esta unidad no ofrece prácticas por proceso.')
    return unidad, receta


@login_required
@require_GET
def seleccion_por_proceso_view(request, slug, receta_id):
    """La selección derivada del proceso para una escala y una hora de inicio."""
    _unidad, receta = _receta_de_practica(slug, receta_id)
    try:
        factor = factor_valido(request.GET.get('factor'))
    except ValueError as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)
    hora = parse_time((request.GET.get('hora') or '').strip()) if request.GET.get('hora') else None
    personas = (request.GET.get('personas') or '').strip()
    seleccion = seleccion_por_proceso(
        receta, factor, hora_inicio=hora, es_administrador=request.user.is_staff,
        personas=int(personas) if personas.isdigit() else None,
    )
    if request.GET.get('guia'):
        # Los apartados de la guía FT04 que el proceso sabe llenar, para el asistente.
        guia = guia_integrada_desde_proceso(receta, factor, escala=seleccion['escala'])
        seleccion['guia'] = {
            clave: guia[clave]
            for clave in (
                'guia_resultado_aprendizaje', 'guia_objetivos', 'guia_procedimiento',
                'guia_medidas_seguridad', 'guia_resultados_esperados',
            )
        }
    seleccion['success'] = True
    return JsonResponse(seleccion)
