"""Las simulaciones que alguien guarda: volver a ellas, cambiarlas, borrarlas y bajarlas.

Un simulador del aula se maneja con parámetros en la dirección, así que una
simulación es reproducible con solo guardar esos parámetros. Eso es lo que se
guarda: no una foto de los resultados, sino las variables con que se corrió. Al
abrirla se vuelve a calcular con el mismo motor que usa la planta, de modo que
una simulación de marzo abierta en junio muestra el proceso como está hoy.

El resumen sí se guarda aparte, y solo para la lista: cuatro cifras con las que
reconocer una simulación entre quince sin recalcularlas todas para pintar una
tabla.
"""

import re
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.formacion.models.aula import SimulacionGuardada
from apps.directorio_unidades.models.core import Unidad

from apps.documentos.presentation.documentacion import entradas_y_salidas
from apps.documentos.presentation.documentos import enlaces_de_documento, formato_pedido, respuesta_pdf
from apps.formacion.presentation.documentos_aula import documento_de_pagina
from apps.plantas_piloto.operacion.presentation.escenarios import aplicar_escenario, cambios_del_escenario, leer_escenario
from apps.plantas_piloto.operacion.presentation.motores import balance_de_linea, requerimiento_de_materiales
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta, unidad_en_plural

# Lo que se guarda de la dirección: los mandos de cada simulador y los datos del
# escenario. Todo lo demás (el «formato», el nombre del formulario, el token) es
# de la petición y no de la simulación.
PARAMETROS_SIMPLES = {
    'receta', 'cantidad', 'reserva', 'programacion',
    't_inicial', 't_proceso', 't_final', 'eficiencia', 'potencia_kw',
    'corridas', 'jornada', 'rendimiento_esperado',
}
PARAMETROS_ESCENARIO = re.compile(r'^(rendimiento|insumo|salida|duracion|espera|omitir)_\d+(_\d+)?$')
NOMBRES_SIMULADOR = {
    'balance': 'simulador_balance',
    'linea': 'simulador_linea',
    'materiales': 'simulador_materiales',
}


def parametros_guardables(fuente):
    """Solo lo que reproduce la simulación, en el orden en que llegó."""
    return {
        clave: str(valor).strip()
        for clave, valor in fuente.items()
        if (clave in PARAMETROS_SIMPLES or PARAMETROS_ESCENARIO.match(clave)) and str(valor).strip()
    }


def url_de(simulacion):
    """La dirección que reabre el simulador tal como quedó guardado."""
    nombre = NOMBRES_SIMULADOR.get(simulacion.simulador, 'simulador_balance')
    base = reverse(nombre, args=[simulacion.unidad.slug])
    consulta = simulacion.consulta
    return f'{base}?{consulta}' if consulta else base


def _receta_de(unidad, parametros):
    identificador = (parametros.get('receta') or '').strip()
    if not identificador.isdigit():
        return None
    return Receta.objects.filter(pk=identificador, unidad=unidad, activa=True).first()


@login_required
@require_POST
def guardar_simulacion_view(request, slug):
    """Guarda la simulación que está en pantalla, o actualiza la que se abrió."""
    unidad = get_object_or_404(Unidad, slug=slug)
    simulador = request.POST.get('simulador', 'balance')
    if simulador not in NOMBRES_SIMULADOR:
        simulador = 'balance'
    parametros = parametros_guardables(request.POST)
    nombre = (request.POST.get('nombre') or '').strip()[:120]
    if not nombre:
        nombre = f'Simulación del {timezone.localdate():%d/%m/%Y}'
    # «Guardarla aparte» deja la original como está y crea otra con lo que hay
    # en pantalla: probar una variante no obliga a perder la simulación previa.
    identificador = '' if request.POST.get('accion') == 'copia' else (request.POST.get('simulacion') or '').strip()
    simulacion = None
    if identificador.isdigit():
        simulacion = SimulacionGuardada.objects.filter(
            pk=identificador, autor=request.user, unidad=unidad
        ).first()
    if simulacion is None:
        simulacion = SimulacionGuardada(unidad=unidad, autor=request.user, simulador=simulador)
    simulacion.simulador = simulador
    simulacion.nombre = nombre
    simulacion.notas = (request.POST.get('notas') or '').strip()
    simulacion.parametros = parametros
    simulacion.receta = _receta_de(unidad, parametros)
    simulacion.familia = simulacion.receta.familia if simulacion.receta_id else None
    simulacion.resumen = resumen_de(simulacion)
    simulacion.save()
    destino = f'{url_de(simulacion)}{"&" if simulacion.consulta else "?"}simulacion={simulacion.pk}&guardada=1'
    return redirect(destino)


@login_required
@require_POST
def eliminar_simulacion_view(request, slug, simulacion_id):
    """Borra una simulación propia. Solo la borra quien la guardó."""
    unidad = get_object_or_404(Unidad, slug=slug)
    simulacion = get_object_or_404(
        SimulacionGuardada, pk=simulacion_id, unidad=unidad, autor=request.user
    )
    simulacion.delete()
    return redirect(reverse('mis_simulaciones', args=[unidad.slug]) + '?borrada=1')


def resumen_de(simulacion):
    """Las cifras con que se reconoce la simulación en la lista."""
    if simulacion.receta_id is None:
        return []
    if simulacion.simulador == 'linea':
        linea = _linea_de(simulacion)
        return [
            ('Ritmo que pide', f"{linea['takt']} min por corrida"),
            ('Ciclo real', f"{linea['ciclo']} min"),
            ('Estaciones', str(linea['numero_estaciones'])),
            ('Alcanza la jornada', 'Sí' if linea['alcanza'] else 'No'),
        ]
    if simulacion.simulador == 'materiales':
        requerimiento = _materiales_de(simulacion)
        return [
            ('Insumos', str(requerimiento['insumos'])),
            ('Cubiertos', str(requerimiento['cubiertos'])),
            ('Faltantes', str(requerimiento['faltantes'])),
            ('Corridas', requerimiento['corridas']),
        ]
    _receta_datos, datos, ajustes = _escenario_de(simulacion)
    flujo = entradas_y_salidas(datos)
    balance = flujo['balance']
    return [
        ('Entra', f"{balance['entrada']} {balance['unidad_base']}"),
        ('Producto', f"{balance['producto_por_balance']} {balance['unidad_producto']}"),
        ('Merma', f"{flujo['merma_total']} {balance['unidad_base']}"),
        ('Datos movidos', str(len(ajustes))),
    ]


def _decimal_de(parametros, clave, predeterminado):
    try:
        valor = Decimal(str(parametros.get(clave) or predeterminado).replace(',', '.'))
    except InvalidOperation:
        return Decimal(str(predeterminado))
    return valor if valor > 0 else Decimal(str(predeterminado))


def _linea_de(simulacion):
    """El balance de línea con las corridas y la jornada que se guardaron."""
    parametros = simulacion.parametros or {}
    _receta_datos, datos, _ajustes = _escenario_de(simulacion)
    return balance_de_linea(
        datos,
        corridas=_decimal_de(parametros, 'corridas', 1),
        jornada_min=_decimal_de(parametros, 'jornada', 8) * 60,
    )


def _materiales_de(simulacion):
    """El requerimiento de materiales de la corrida guardada, contra el inventario de hoy."""
    _receta_datos, datos, _ajustes = _escenario_de(simulacion)
    return requerimiento_de_materiales([
        {
            'receta': simulacion.receta,
            'factor': Decimal(datos['factor']),
            'etiqueta': simulacion.nombre,
        }
    ])


def _escenario_de(simulacion):
    """La receta a la escala guardada, el escenario y lo que los separa."""
    parametros = simulacion.parametros or {}
    cantidad = Decimal(str(parametros.get('cantidad') or simulacion.receta.cantidad_base))
    base = Decimal(str(simulacion.receta.cantidad_base or 1))
    factor = (cantidad / base) if base else Decimal('1')
    receta_datos = datos_de_receta(simulacion.receta, factor)
    ajustes = leer_escenario(parametros, receta_datos)
    return receta_datos, aplicar_escenario(receta_datos, ajustes), ajustes


@xframe_options_sameorigin
@login_required
def mis_simulaciones_view(request, slug):
    """Las simulaciones que guardó quien entra, para abrirlas, bajarlas o borrarlas."""
    unidad = get_object_or_404(Unidad, slug=slug)
    simulaciones = [
        {
            'objeto': simulacion,
            'abrir_url': url_de(simulacion) + (
                f'{"&" if simulacion.consulta else "?"}simulacion={simulacion.pk}'
            ),
            'reporte_url': reverse('reporte_simulacion', args=[unidad.slug, simulacion.pk]),
            'eliminar_url': reverse('eliminar_simulacion', args=[unidad.slug, simulacion.pk]),
        }
        for simulacion in SimulacionGuardada.objects.filter(
            autor=request.user, unidad=unidad
        ).select_related('receta', 'unidad')
    ]
    contexto = {
        'unidad': unidad,
        'simulaciones': simulaciones,
        'autor': request.user.get_full_name() or request.user.username,
        'borrada': request.GET.get('borrada') == '1',
        'generado_en': timezone.localtime(),
        'volver_url': unidad.get_absolute_url(),
        'simulador': 'guardadas',
        'simuladores': [],
        **enlaces_de_documento(request),
    }
    formato = formato_pedido(request)
    if formato:
        return respuesta_pdf(
            documento_de_pagina('mis_simulaciones', contexto),
            f'mis-simulaciones-{unidad.slug}.pdf',
            formato,
        )
    return render(request, 'portal/pages/unidades/aula/mis_simulaciones.html', contexto)


def _cabecera(simulacion, criterios):
    """Lo que toda simulación pone en la cabecera del documento."""
    hoy = timezone.localdate()
    return {
        'scope_label': f'{simulacion.unidad.nombre} · {simulacion.nombre}',
        'generated_at': timezone.localtime(),
        'start_date': hoy,
        'end_date': hoy,
        'category_label': f'Simulación: {simulacion.get_simulador_display()}',
        'filter_summary': [
            ('Proceso', f"{simulacion.receta.codigo} · {simulacion.receta.nombre}"),
            *criterios,
            ('Autor', simulacion.autor.get_full_name() or simulacion.autor.username),
            ('Guardada', f'{timezone.localtime(simulacion.actualizada_en):%d/%m/%Y %H:%M}'),
        ],
        'is_generic': True,
        'notas': simulacion.notas,
    }


def _reporte_de_linea(simulacion):
    """El balance de línea guardado: el ritmo que pide la jornada y quién no lo alcanza."""
    linea = _linea_de(simulacion)
    cuello = linea['cuello'] or {}
    return {
        **_cabecera(simulacion, [
            ('Corridas en la jornada', linea['corridas']),
            ('Jornada', f"{linea['jornada_min']} min"),
        ]),
        'dataset': {
            'headers': [
                'N.º', 'Etapa', 'Equipo', 'Trabajo (min)', 'Espera (min)', 'Personas',
                'Utilización del takt',
            ],
            'rows': [
                [
                    etapa['orden'], etapa['nombre'], etapa['equipo'] or '—',
                    etapa['trabajo'], etapa['espera'], etapa['personas'],
                    f"{etapa['utilizacion']} %",
                ]
                for etapa in linea['etapas']
            ],
            'matrix': False, 'matrix_kind': '', 'structured': False, 'records': [],
            'document_meta': {}, 'truncated': False, 'state_choices': (), 'column_count': 7,
            'cards': [
                ('Ritmo que pide la jornada', f"{linea['takt']} min", 'takt por corrida'),
                (
                    'Ciclo real',
                    f"{linea['ciclo']} min",
                    f"cuello de botella: {cuello.get('nombre') or 'sin etapas'}",
                ),
                (
                    'Estaciones',
                    str(linea['numero_estaciones']),
                    f"mínimo teórico: {linea['estaciones_minimas']}",
                ),
                (
                    'Alcanza la jornada',
                    'Sí' if linea['alcanza'] else 'No',
                    f"eficiencia de línea {linea['eficiencia']} %",
                ),
            ],
            'tablas': [{
                'titulo': 'CÓMO QUEDAN LAS ESTACIONES',
                'headers': ['Estación', 'Etapas que agrupa', 'Tiempo (min)', 'Ocupación del takt', 'Personas'],
                'rows': [
                    [
                        estacion['numero'],
                        ' · '.join(f"{etapa['orden']}. {etapa['nombre']}" for etapa in estacion['etapas']),
                        estacion['tiempo'],
                        f"{estacion['ocupacion']} %" + (' (excede el takt)' if estacion['excede'] else ''),
                        estacion['personas'],
                    ]
                    for estacion in linea['estaciones']
                ],
                'vacio': 'El proceso no declara etapas con tiempo de trabajo.',
            }],
        },
    }


def _reporte_de_materiales(simulacion):
    """El requerimiento de materiales guardado, contra las existencias de hoy."""
    requerimiento = _materiales_de(simulacion)
    return {
        **_cabecera(simulacion, [('Corridas', requerimiento['corridas'])]),
        'dataset': {
            'headers': [
                'Insumo', 'Clasificación', 'Necesita', 'En bodega', 'Reserva',
                'Disponible', 'Falta comprar',
            ],
            'rows': [
                [
                    f"{fila['nombre']} ({fila['unidad']})" + ('' if fila['obligatorio'] else ' · opcional'),
                    fila['clasificacion'], fila['bruto'], fila['stock'], fila['seguridad'],
                    fila['disponible'], '—' if fila['cubre'] else fila['neto'],
                ]
                for fila in requerimiento['filas']
            ],
            'matrix': False, 'matrix_kind': '', 'structured': False, 'records': [],
            'document_meta': {}, 'truncated': False, 'state_choices': (), 'column_count': 7,
            'cards': [
                ('Insumos', str(requerimiento['insumos']), 'que pide el plan'),
                ('Cubiertos', str(requerimiento['cubiertos']), 'con lo que hay en bodega'),
                ('Faltantes', str(requerimiento['faltantes']), 'hay que comprarlos'),
                ('Corridas', requerimiento['corridas'], 'del plan simulado'),
            ],
            'tablas': [{
                'titulo': 'LO QUE EL PLAN DEBERÍA ENTREGAR',
                'headers': ['Producto', 'Tipo', 'Cantidad', 'Papel'],
                'rows': [
                    [
                        f"{salida['nombre']} ({salida['unidad']})", salida['tipo'], salida['cantidad'],
                        'Producto principal' if salida['principal'] else 'Subproducto',
                    ]
                    for salida in requerimiento['salidas']
                ],
                'vacio': 'La receta no declara productos de salida.',
            }],
        },
    }


def reporte_de_simulacion(simulacion):
    """La simulación como reporte institucional: el mismo que se ve y el que se baja."""
    if simulacion.simulador == 'linea':
        return _reporte_de_linea(simulacion)
    if simulacion.simulador == 'materiales':
        return _reporte_de_materiales(simulacion)
    receta_datos, datos, ajustes = _escenario_de(simulacion)
    flujo = entradas_y_salidas(datos)
    balance = flujo['balance']
    cambios = cambios_del_escenario(receta_datos, ajustes)
    producto = unidad_en_plural(balance['unidad_producto'], balance['producto_por_balance'])
    return {
        **_cabecera(simulacion, [
            ('Escala', f"{balance['entrada']} {balance['unidad_base']}"),
            ('Datos movidos', str(len(ajustes))),
        ]),
        'dataset': {
            'headers': ['N.º', 'Etapa', 'Rendimiento', 'Entra', 'Se incorpora', 'Continúa', 'Sale declarado', 'Pérdida'],
            'rows': [
                [
                    fila['orden'], fila['nombre'], f"{fila['rendimiento_pct']} %",
                    fila['entra'],
                    f"+{fila['agregado']}" if fila['agregado'] != '0' else '—',
                    fila['continua'],
                    ' · '.join(fila['salidas']) or '—',
                    fila['perdida'] if fila['perdida'] != '0' else '—',
                ]
                for fila in balance['filas']
            ],
            'matrix': False,
            'matrix_kind': '',
            'structured': False,
            'records': [],
            'document_meta': {},
            'cards': [
                (
                    'Entra',
                    f"{balance['entrada']} {balance['unidad_base']}",
                    'materia prima de la corrida',
                ),
                (
                    'Producto por balance',
                    f"{balance['producto_por_balance']} {producto}",
                    'lo que deja este escenario',
                ),
                (
                    'Producto esperado',
                    f"{balance['producto_esperado']} {producto}",
                    'lo que la receta promete',
                ),
                (
                    'Merma total',
                    f"{flujo['merma_total']} {balance['unidad_base']}",
                    'masa que sale sin declararse',
                ),
            ],
            'truncated': False,
            'state_choices': (),
            'column_count': 8,
            'tablas': [
                {
                    'titulo': 'LO QUE SE MOVIÓ RESPECTO DE LA RECETA',
                    'headers': ['Variable', 'La receta dice', 'Este escenario'],
                    'rows': [[cambio['variable'], cambio['de'], cambio['a']] for cambio in cambios],
                    'vacio': 'Esta simulación corre con los datos de la receta, sin cambios.',
                },
                {
                    'titulo': 'TODO LO QUE ENTRA',
                    'headers': ['Etapa', 'Insumo', 'Cantidad', 'Su papel en el balance'],
                    'rows': [
                        [entrada['etapa'] or 'Sin etapa', entrada['nombre'], entrada['cantidad'], entrada['rol']]
                        for entrada in flujo['entradas']
                    ],
                    'vacio': 'La receta no declara insumos.',
                },
                {
                    'titulo': 'TODO LO QUE SALE',
                    'headers': ['Etapa', 'Salida', 'Cantidad', 'Qué es'],
                    'rows': [
                        [salida['etapa'], salida['nombre'], salida['cantidad'] or '—', f"{salida['tipo']} · {salida['detalle']}"]
                        for salida in flujo['salidas']
                    ],
                    'vacio': 'Con estos datos el proceso no pierde masa ni declara subproductos.',
                },
            ],
        },
    }


@xframe_options_sameorigin
@login_required
def reporte_simulacion_view(request, slug, simulacion_id):
    """La simulación como documento: primero se ve cómo queda y después se baja."""
    unidad = get_object_or_404(Unidad, slug=slug)
    simulacion = get_object_or_404(
        SimulacionGuardada.objects.select_related('receta', 'unidad', 'autor'),
        pk=simulacion_id, unidad=unidad, autor=request.user,
    )
    if simulacion.receta_id is None:
        return redirect(reverse('mis_simulaciones', args=[unidad.slug]))
    reporte = reporte_de_simulacion(simulacion)
    formato = formato_pedido(request)
    if formato:
        return respuesta_pdf(reporte, f'simulacion-{unidad.slug}-{simulacion.pk}.pdf', formato)
    return render(request, 'portal/pages/unidades/aula/reporte_simulacion.html', {
        'unidad': unidad,
        'simulacion': simulacion,
        'reporte_gestion': reporte,
        'generado_en': timezone.localtime(),
        'volver_url': reverse('mis_simulaciones', args=[unidad.slug]),
        'abrir_url': url_de(simulacion) + (f'{"&" if simulacion.consulta else "?"}simulacion={simulacion.pk}'),
        'ver_url': reverse('reporte_simulacion', args=[unidad.slug, simulacion.pk]) + '?formato=pdf',
        'descargar_url': (
            reverse('reporte_simulacion', args=[unidad.slug, simulacion.pk]) + '?formato=pdf&descargar=1'
        ),
    })


def estado_guardado(request, unidad, simulador):
    """Lo que un simulador necesita para ofrecer guardar y para saber qué abrió.

    Guardar exige haber entrado: una simulación es de alguien. Quien entra sin
    cuenta usa el simulador igual, pero no puede dejar nada guardado.
    """
    if not request.user.is_authenticated:
        return {'puede_guardar': False, 'simulacion_abierta': None, 'guardado': ''}
    identificador = (request.GET.get('simulacion') or '').strip()
    abierta = None
    if identificador.isdigit():
        abierta = SimulacionGuardada.objects.filter(
            pk=identificador, autor=request.user, unidad=unidad, simulador=simulador
        ).first()
    return {
        'puede_guardar': True,
        'simulacion_abierta': abierta,
        # El formulario de guardar viaja por POST, así que lleva escondido lo
        # mismo que la dirección tiene puesto: se guarda lo que se está viendo.
        'parametros_actuales': parametros_guardables(request.GET),
        'guardado': (
            'La simulación quedó guardada. Sigue cambiándola y vuelve a guardarla cuando quieras.'
            if request.GET.get('guardada') == '1' else ''
        ),
        'guardar_url': reverse('guardar_simulacion', args=[unidad.slug]),
        'mis_simulaciones_url': reverse('mis_simulaciones', args=[unidad.slug]),
        'reporte_url_abierta': (
            reverse('reporte_simulacion', args=[unidad.slug, abierta.pk]) if abierta else ''
        ),
    }
