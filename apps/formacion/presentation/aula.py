"""Aula y simuladores: las funciones de la planta en el visor público de la unidad.

Cada pestaña de la ficha recibe sus carpetas: en «Procesos y protocolos», los
sistemas de producción (línea de producción → proceso, con la ficha de cada
uno) y los simuladores del proceso (balance de materia y energía, balance de
línea); en «Producción y lotes», el catálogo público, el agregado de corridas
y lotes y el requerimiento de materiales; en «Calidad e inocuidad», los
protocolos de control, el control de calidad de los lotes y los requisitos
de ingreso; en «Equipos e infraestructura», las áreas con sus equipos. Las
páginas se cargan dentro del visor (iframe del mismo origen) o solas. Un
simulador toma los datos de una reserva o de una programación («si pidió
100 litros, simula con 100 litros») o corre libre.
"""

import csv
from collections import Counter, OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import FamiliaProducto, LoteProducto, OrdenProduccion, Producto
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.plantas_piloto.operacion.models.calidad import PlanCalidad
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad

from apps.laboratorios.operacion.presentation.actividad_laboratorio import GRUPOS, actividades_de
from apps.gestion_unidades.presentation.novedades import novedades_de
from apps.laboratorios.operacion.presentation import procesos_laboratorio
from apps.plantas_piloto.operacion.presentation.calidad import calidad_publicada, planes_de
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, puede_operar_modulo_unidad
from apps.recursos.presentation.verificacion_equipos import publicos_para, puede_verificar
from apps.documentos.presentation.documentacion import balance_general, entradas_y_salidas, flujo_por_etapa
from apps.documentos.presentation.documentos import enlaces_de_documento, formato_pedido, respuesta_pdf
from apps.formacion.presentation.documentos_aula import documento_de_pagina
from apps.recursos.presentation.codigos_equipo import ve_datos_patrimoniales
from apps.gestion_unidades.presentation.conoce import foto_de_portada
from apps.recursos.presentation.equipo_publico import detalle_de_equipo, imagen_de
from apps.recursos.presentation.ficha_equipo import linea_de_trazabilidad, pantalla_de_edicion
from apps.gestion_unidades.presentation.gobierno_editorial import objeto_visible_para as _objeto_visible_para, visibles_para
from apps.plantas_piloto.operacion.presentation.escenarios import aplicar_escenario, cambios_del_escenario, escenario_del_formulario, valores_del_formulario
from apps.plantas_piloto.operacion.presentation.motores import CALOR_ESPECIFICO, CALOR_LATENTE_VAPOR, COP_FRIO, DENSIDAD, TRES, _decimal, _num, _texto, balance_de_energia, balance_de_linea, etapas_termicas, requerimiento_de_materiales
from apps.plantas_piloto.operacion.presentation.planta_operativa import SECCIONES_ERP
from apps.plantas_piloto.operacion.presentation.navegacion_proceso import acciones_del_proceso, fichas_relacionadas_del_proceso, metadatos_editoriales
from apps.formacion.presentation.simulaciones import NOMBRES_SIMULADOR, estado_guardado
from apps.plantas_piloto.operacion.presentation.diagramas import diagrama_flujo, diagramas_de_ficha
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa, cronograma, cursograma_analitico, datos_de_receta, resumen_proceso
from apps.reservas.presentation.proceso import recetas_para_practica
from apps.gestion_unidades.presentation.repositorio import artefactos_publicos, contexto_adjuntos
from apps.reservas.presentation.seguridad import resumen_requisitos
from apps.plantas_piloto.operacion.presentation.servicios_industriales import servicios_industriales
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_PLANTA, ajustes_de, mapa_de, seccion_de, secciones_con_nombre

LINEA_SIN_NOMBRE = 'Otros procesos'
MODULOS_PROCESOS = ('procesos-protocolos', 'areas-productivas')
MODULOS_PRODUCCION = ('produccion-lotes', 'produccion-ensayos')
MODULOS_CALIDAD = ('calidad-inocuidad',)
MODULOS_EQUIPOS = ('equipos-infraestructura', 'infraestructura-equipos', 'areas-equipos')

SIMULADORES = (
    ('balance', 'Balance de materia y energía', 'simulador_balance', 'fas fa-balance-scale',
     'Cuánto entra, cuánto sale y cuánto calor exige una corrida.'),
    ('linea', 'Balance de línea', 'simulador_linea', 'fas fa-stream',
     'Tiempos por estación, cuello de botella y capacidad de la jornada.'),
    ('materiales', 'Requerimiento de materiales', 'simulador_materiales', 'fas fa-boxes',
     'Lo que el inventario debe tener para un plan de corridas.'),
)


# ---------------------------------------------------- los sistemas de producción
def procesos_publicos(unidad, usuario=None):
    """Los procesos que la unidad publica: los mismos que se pueden practicar."""
    return [
        receta for receta in recetas_para_practica(unidad)
        if _objeto_visible_para(receta, unidad, usuario)
    ]


def _por_linea(objetos, nombre_de_linea, orden_de_linea=None):
    lineas = OrderedDict()
    for objeto in objetos:
        nombre = (nombre_de_linea(objeto) or '').strip() or LINEA_SIN_NOMBRE
        linea = lineas.setdefault(nombre, {'elementos': [], 'orden': None})
        linea['elementos'].append(objeto)
        if orden_de_linea is not None and linea['orden'] is None:
            linea['orden'] = orden_de_linea(objeto)
    ordenadas = sorted(
        lineas.items(),
        key=lambda item: (
            item[0] == LINEA_SIN_NOMBRE,
            item[1]['orden'] is None,
            item[1]['orden'] if item[1]['orden'] is not None else 0,
            item[0].lower(),
        ),
    )
    return [{'nombre': nombre, 'elementos': datos['elementos']} for nombre, datos in ordenadas]


def lineas_de_procesos(procesos):
    """Los procesos agrupados por la familia maestra de su producto."""
    return [
        {'nombre': linea['nombre'], 'procesos': linea['elementos']}
        for linea in _por_linea(
            procesos,
            lambda receta: receta.familia.nombre if receta.familia_id else '',
            lambda receta: receta.familia.orden if receta.familia_id else None,
        )
    ]


def simuladores_de(unidad, receta=None):
    sufijo = f'?receta={receta.pk}' if receta is not None else ''
    return [
        {
            'clave': clave,
            'nombre': nombre,
            'url': reverse(nombre_url, args=[unidad.slug]) + sufijo,
            'icono': icono,
            'detalle': detalle,
        }
        for clave, nombre, nombre_url, icono, detalle in SIMULADORES
    ]


def _modulo_entre(claves, candidatos, respaldo):
    return next((clave for clave in candidatos if clave in claves), respaldo)


def modulo_del_aula(modulos):
    """El módulo donde viven los procesos: «Procesos y protocolos» o, si no existe, el de reservas."""
    modulos = list(modulos)
    claves = [modulo.clave for modulo in modulos]
    reservas = next((modulo.clave for modulo in modulos if modulo.mostrar_herramientas_reserva), '')
    return _modulo_entre(claves, MODULOS_PROCESOS, reservas or (claves[0] if claves else ''))


def _boton(identificador, nombre, url, icono, detalle, estado='', subtitulo='', imagen=''):
    return {
        'id': identificador,
        'nombre': nombre,
        'url': url,
        'icono': icono,
        'titulo': detalle,
        'estado': estado,
        'subtitulo': subtitulo,
        'imagen': imagen,
    }


def _carpeta(modulo, identificador, titulo, icono, grupos, abierta=True, numero='', seccion=False, mapa=None):
    if seccion:
        titulo = (mapa or MAPA_PLANTA).secciones[numero]['titulo']
    return {
        'modulo': modulo,
        'id': identificador,
        'titulo': titulo,
        'icono': icono,
        'abierta': abierta,
        'grupos': grupos,
        'numero': numero,
        'seccion': seccion,
        'total': sum(len(grupo['botones']) for grupo in grupos),
    }


ICONOS_SECCION = {
    '2.1': 'fas fa-industry',
    '2.2': 'fas fa-boxes',
    '2.3': 'fas fa-stopwatch',
    '2.4': 'fas fa-calculator',
    '2.5': 'fas fa-book',
    '3.1': 'fas fa-warehouse',
    '3.2': 'fas fa-microchip',
    '3.3': 'fas fa-plug',
    '3.4': 'fas fa-stream',
    '4.1': 'fas fa-box-open',
    '4.2': 'fas fa-file-alt',
    '4.3': 'fas fa-box',
    '4.4': 'fas fa-boxes',
    '4.5': 'fas fa-industry',
    '4.6': 'fas fa-flask',
    '5.1': 'fas fa-clipboard-check',
    '5.2': 'fas fa-ruler-combined',
    '5.3': 'fas fa-file-medical',
    '5.4': 'fas fa-vial',
    '5.5': 'fas fa-hands-wash',
}

# Íconos de las secciones de los laboratorios, por clave; las plantas usan ICONOS_SECCION por número.
ICONOS_CLAVE = {
    **{MAPA_PLANTA.secciones[numero]['clave']: icono for numero, icono in ICONOS_SECCION.items()},
    'novedades': 'fas fa-bullhorn',
    'software': 'fas fa-laptop-code',
    'materiales': 'fas fa-boxes',
    'procesos': 'fas fa-project-diagram',
    'guias': 'fas fa-book-open',
    'asignaturas': 'fas fa-graduation-cap',
    'cursos': 'fas fa-chalkboard-teacher',
    'recursos_aprendizaje': 'fas fa-cube',
    'proyectos_formativos': 'fas fa-lightbulb',
    'colaboracion_centros': 'fas fa-microscope',
    'resultados': 'fas fa-file-alt',
    'vinculacion': 'fas fa-handshake',
    # Observatorios.
    'indicadores': 'fas fa-chart-line',
    'datos': 'fas fa-table',
    'mapas': 'fas fa-map-marked-alt',
    'fichas_metodologicas': 'fas fa-clipboard-list',
    'alertas': 'fas fa-bell',
    'umbrales': 'fas fa-sliders-h',
    'fuentes': 'fas fa-database',
    'boletines': 'fas fa-newspaper',
    'informes': 'fas fa-file-alt',
    'calendario': 'fas fa-calendar-alt',
    'estudios': 'fas fa-search',
    'encuestas': 'fas fa-poll',
    'aliados': 'fas fa-handshake',
    'impacto': 'fas fa-bullseye',
    'solicitudes': 'fas fa-inbox',
    'servicios_datos': 'fas fa-concierge-bell',
    'participa': 'fas fa-user-plus',
    'api_datos': 'fas fa-code',
    'lineas': 'fas fa-layer-group',
    'visores': 'fas fa-external-link-square-alt',
    'actualizaciones': 'fas fa-sync-alt',
    'sala': 'fas fa-desktop',
    # Centros experimentales.
    'funcionamiento': 'fas fa-sitemap',
    'ejes': 'fas fa-layer-group',
    'calendario_productivo': 'fas fa-calendar-alt',
    'simuladores_campo': 'fas fa-calculator',
    'registros_produccion': 'fas fa-clipboard-list',
    'ensayos': 'fas fa-flask',
    'destino': 'fas fa-truck-loading',
    'temas_investigacion': 'fas fa-search',
    'relaciones': 'fas fa-project-diagram',
    'como_reservar': 'fas fa-route',
}


def _icono(mapa, numero):
    return ICONOS_CLAVE.get(mapa.secciones[numero]['clave'], 'fas fa-folder')


def _completar_secciones(carpetas, claves, mapa):
    """Hace visible el mapa completo sin duplicar los objetos que viven en otra ficha."""
    presentes = {carpeta['numero'] for carpeta in carpetas if carpeta.get('numero')}
    # La primera pestaña y la de reservas las dibuja la plantilla; las guías, la vista de detalle.
    dibujadas = {'informacion-general', mapa.modulo_reservas}
    for modulo, (_titulo, secciones) in mapa.pestanas.items():
        if modulo in dibujadas or modulo not in claves:
            continue
        for numero, titulo in secciones:
            if numero == mapa.numero('guias') or numero in presentes:
                continue
            carpeta = _carpeta(
                modulo,
                f'Seccion{numero.replace(".", "_")}',
                titulo,
                _icono(mapa, numero),
                [{'nombre': '', 'botones': []}],
                abierta=False,
                numero=numero,
                seccion=True,
                mapa=mapa,
            )
            carpeta['pendiente'] = True
            carpeta['mensaje'] = 'Contenido pendiente de publicación por la unidad.'
            carpetas.append(carpeta)

    orden_modulo = {clave: indice for indice, clave in enumerate(mapa.pestanas)}
    orden_seccion = {
        numero: indice
        for _clave, (_titulo, secciones) in mapa.pestanas.items()
        for indice, (numero, _nombre) in enumerate(secciones)
    }
    carpetas.sort(key=lambda carpeta: (
        orden_modulo.get(carpeta['modulo'], len(orden_modulo)),
        orden_seccion.get(carpeta.get('numero'), 99),
        carpeta.get('orden_propio', 0),
        carpeta['titulo'],
    ))


def _estado_editorial(estado):
    return {
        'publicada': 'publicada',
        'en_revision': 'parcial',
        'borrador': 'pendiente',
        'archivada': 'pendiente',
    }.get(estado, '')


def carpetas_del_aula(unidad, modulos, procesos, usuario=None):
    """Las carpetas que cada pestaña de la ficha recibe, con sus botones."""
    modulos = list(modulos)
    claves = [modulo.clave for modulo in modulos]
    slug = unidad.slug
    carpetas = []
    es_planta = unidad.dependencia == 'plantas_piloto'
    # El mapa numerado de su tipo; sin mapa las carpetas no llevan número.
    mapa = mapa_de(unidad)
    num = mapa.numero if mapa else (lambda clave: '')
    fichas_objeto = {}
    fichas_simulador = {}
    fichas_documento = {}
    if es_planta:
        for ficha in FichaContenido.objects.filter(unidad=unidad).select_related('content_type'):
            estado = _estado_editorial(ficha.estado)
            if ficha.content_type_id and ficha.object_id:
                fichas_objeto[(ficha.content_type.model, ficha.object_id)] = estado
            elif ficha.tipo == 'simulador':
                fichas_simulador[ficha.titulo] = estado
            elif ficha.tipo == 'documento':
                fichas_documento[ficha.codigo] = ficha

    def estado_objeto(objeto):
        return fichas_objeto.get((objeto._meta.model_name, objeto.pk), '')

    if procesos:
        base = modulo_del_aula(modulos)
        modulo_produccion = _modulo_entre(claves, MODULOS_PRODUCCION, base)
        modulo_calidad = _modulo_entre(claves, MODULOS_CALIDAD, base)
        def boton_simulador(clave, receta=None, identificador=''):
            item = next(item for item in simuladores_de(unidad, receta) if item['clave'] == clave)
            return _boton(
                identificador or f'simulador-{clave}', item['nombre'], item['url'], item['icono'], item['detalle'],
                fichas_simulador.get(item['nombre'], ''),
            )

        procesos_por_producto = {}
        for receta in procesos:
            procesos_por_producto.setdefault(receta.producto_id, []).append(receta)
        lineas_produccion = produccion_publica(unidad, procesos, usuario)['lineas']
        # 2.1 muestra los procesos técnicos cargados; cada producto, con o sin proceso,
        # tiene su ficha en 4.2. Así ninguno aparece dos veces ni vacío.
        grupos_sistemas = []
        nombres_procesos = {}
        if unidad.slug == 'planta-piloto-cafe':
            from apps.plantas_piloto.operacion.management.plantas.cafe_medios import nombre_de_proceso
            nombres_procesos = {r.codigo: nombre_de_proceso(r, unidad) for r in procesos}
        for linea in lineas_produccion:
            botones = [
                _boton(
                    f'ficha-proceso-{receta.pk}',
                    nombres_procesos.get(receta.codigo, f'{receta.producto.nombre} · derivado' if receta.origen == 'derivado' else receta.producto.nombre),
                    reverse('ficha_proceso_publica', args=[slug, receta.pk]),
                    'fas fa-project-diagram',
                    f'Ficha de proceso: {receta.nombre_publico}',
                    estado_objeto(receta),
                    f'Proceso técnico · {receta.etapas.count()} etapas'
                    + (' · por validar' if receta.origen == 'derivado' else ''),
                )
                for producto in linea['productos']
                for receta in procesos_por_producto.get(producto.pk, [])
            ]
            if botones:
                nombre_linea = ('Trilla, clasificación y café verde'
                                if unidad.slug == 'planta-piloto-cafe' and linea['nombre'] == 'Café verde y preparación de lotes'
                                else linea['nombre'])
                grupos_sistemas.append({'nombre': nombre_linea, 'botones': botones})
        cadena_cafe = None
        if es_planta:
            from apps.plantas_piloto.operacion.presentation.cafe import resumen_cadena_cafe
            cadena_cafe = resumen_cadena_cafe(unidad)
            if cadena_cafe:
                grupos_sistemas.insert(0, {'nombre': 'Vista general de la cadena', 'botones': [_boton(
                    'cafe-cadena', cadena_cafe['nombre'], cadena_cafe['url'], 'fas fa-route',
                    'Flujo completo, laboratorio transversal y fichas de cada equipo; grano o molido en 250, 500 y 1.000 g',
                )]})
        carpetas.append(_carpeta(
            base, 'SistemasProduccion', 'Sistemas de producción', 'fas fa-industry',
            grupos_sistemas, numero='2.1' if es_planta else '', seccion=es_planta,
        ))
        if cadena_cafe:
            carpetas[-1]['total'] -= 1
        if es_planta:
            carpetas.extend((
                _carpeta(
                    base, 'MaterialesInsumos', 'Materiales e insumos', 'fas fa-boxes',
                    [{'nombre': '', 'botones': [_boton(
                        'indice-materiales-insumos', 'Matriz de materiales e insumos',
                        reverse('materiales_insumos', args=[slug]), 'fas fa-th-list',
                        'Materias primas, ingredientes y auxiliares agrupados por familia y proceso.',
                    ), _boton(
                        'insumos-unidad', 'Inventario de insumos y materiales', reverse('insumos_unidad', args=[slug]),
                        'fas fa-boxes', 'Cada insumo y material registrado, con su área, los equipos que lo usan y su stock.',
                    )]}], abierta=False, numero='2.2', seccion=True,
                ),
                _carpeta(
                    base, 'MetodosTiempos', 'Métodos y tiempos', 'fas fa-stopwatch',
                    [{'nombre': '', 'botones': [_boton(
                        'indice-metodos-tiempos', 'Métodos, tiempos y secuencia',
                        reverse('metodos_tiempos', args=[slug]), 'fas fa-tasks',
                        'Secuencia, tiempos de trabajo y espera, recursos y controles de cada proceso.',
                    )]}], abierta=False, numero='2.3', seccion=True,
                ),
                _carpeta(
                    base, 'RutaSaberDocumentacion', 'Documentación de los procesos', 'fas fa-book',
                    [{'nombre': '', 'botones': [_boton(
                        'ruta-saber-documentacion', 'Ruta del saber y documentación técnica',
                        reverse('ruta_saber_documentacion', args=[slug]), 'fas fa-route',
                        'Fundamentos, fórmulas y documentación vinculados con cada proceso.',
                    )]}], abierta=False, numero='2.5', seccion=True,
                ),
            ))
        grupos_simuladores = [{
            'nombre': 'Herramientas personales' if es_planta else '',
            'botones': [
                boton_simulador('balance'),
                _boton(
                    'mis-simulaciones', 'Mis simulaciones', reverse('mis_simulaciones', args=[slug]),
                    'fas fa-save', 'Las simulaciones que guardaste: retomarlas, verlas o descargarlas',
                ),
                _boton(
                    'mis-ejercicios', 'Mis ejercicios', reverse('mis_ejercicios', args=[slug]),
                    'fas fa-user-graduate', 'Los ejercicios que te asignaron, cada uno con tu propia escala',
                ),
            ],
        }]
        if es_planta:
            from apps.plantas_piloto.operacion.presentation.cafe import herramientas_de_cafe
            grupos_simuladores[0]['botones'].extend(
                _boton(h['id'], h['nombre'], h['url'], 'fas fa-coffee', h['descripcion'])
                for h in herramientas_de_cafe(unidad)
            )
            artefactos = list(artefactos_publicos(unidad, usuario).filter(receta__in=procesos))
            for linea in lineas_de_procesos(procesos):
                botones = [
                    _boton(
                        f'artefacto-{artefacto.pk}', artefacto.nombre,
                        reverse('artefacto_externo', args=[slug, artefacto.codigo]),
                        'fas fa-cube',
                        f'Artefacto nivel {artefacto.nivel_integracion}: {artefacto.get_tipo_display()}',
                    )
                    for artefacto in artefactos
                    if artefacto.receta in linea['procesos']
                ]
                if botones:
                    grupos_simuladores.append({'nombre': linea['nombre'], 'botones': botones})
        carpetas.append(_carpeta(
            base,
            'SimuladoresProceso',
            'Simuladores y cálculo del proceso' if es_planta else 'Simuladores del proceso',
            'fas fa-calculator', grupos_simuladores,
            abierta=es_planta, numero='2.4' if es_planta else '', seccion=es_planta,
        ))
        if not es_planta:
            carpeta_simuladores = carpetas[-1]
            carpeta_simuladores['grupos'][0]['botones'].insert(1, boton_simulador('linea'))
            carpeta_simuladores['total'] += 1
            carpetas.append(_carpeta(
                base, 'DocumentacionProcesos', 'Documentación de los procesos', 'fas fa-book', [
                    {
                        'nombre': linea['nombre'],
                        'botones': [
                            _boton(
                                f'documentacion-proceso-{receta.pk}', receta.nombre,
                                reverse('documentacion_proceso', args=[slug, receta.pk]),
                                'fas fa-book-open',
                                f'Documentación: operaciones unitarias, variables y datos de {receta.nombre}',
                                estado_objeto(receta),
                            )
                            for receta in linea['procesos']
                        ],
                    }
                    for linea in lineas_de_procesos(procesos)
                ], abierta=False,
            ))
        if es_planta:
            carpetas.append(_carpeta(
                modulo_produccion, 'CatalogoProduccion', 'Lo que produce la planta', 'fas fa-box-open',
                [{'nombre': '', 'botones': [_boton(
                    'produccion-planta', 'Catálogo de productos', reverse('produccion_publica', args=[slug]),
                    'fas fa-box-open', 'Productos publicados, agrupados por la taxonomía institucional',
                )]}],
                numero='4.1', seccion=True,
            ))
            carpetas.append(_carpeta(
                modulo_produccion, 'FichasProducto', '', ICONOS_SECCION['4.2'],
                [{'nombre': linea['nombre'], 'botones': [_boton(
                    f'ficha-producto-{producto.pk}', producto.nombre,
                    reverse('ficha_producto_publica', args=[slug, producto.pk]), 'fas fa-box-open',
                    f'Ficha técnica: {producto.nombre}', estado_objeto(producto),
                    'Con proceso técnico' if producto.pk in procesos_por_producto else 'Sin proceso técnico cargado',
                ) for producto in linea['productos']]} for linea in lineas_produccion if linea['productos']],
                abierta=False, numero='4.2', seccion=True,
            ))
            carpetas.append(_carpeta(
                modulo_produccion, 'EmpaquePresentacion', '', ICONOS_SECCION['4.3'],
                [{'nombre': '', 'botones': [_boton(
                    'empaque-presentacion', 'Empaque y presentación de cada producto',
                    reverse('empaque_presentacion', args=[slug]), 'fas fa-box',
                    'Presentación, conservación, vida útil y materiales de empaque por proceso',
                )]}],
                abierta=False, numero='4.3', seccion=True,
            ))
            carpetas.append(_carpeta(
                modulo_produccion, 'RequerimientoMateriales', 'Requerimiento de materiales', 'fas fa-boxes',
                [{'nombre': '', 'botones': [boton_simulador('materiales')]}],
                abierta=False, numero='4.4', seccion=True,
            ))
            ficha_agregado = next((
                ficha for codigo, ficha in fichas_documento.items()
                if codigo.endswith('-DOC-CORRIDAS-RESUMEN')
                and ficha.estado == 'publicada' and ficha.visibilidad == 'publica'
            ), None)
            if ficha_agregado:
                carpetas.append(_carpeta(
                    modulo_produccion, 'CorridasLotes', 'Corridas y lotes', 'fas fa-industry',
                    [{'nombre': '', 'botones': [_boton(
                        'corridas-lotes', 'Actividad de la planta',
                        reverse('corridas_lotes_publicos', args=[slug]), 'fas fa-chart-bar',
                        'Agregado público de corridas cerradas y lotes vigentes',
                        _estado_editorial(ficha_agregado.estado),
                    )]}],
                    abierta=False, numero='4.5', seccion=True,
                ))
        else:
            carpetas.append(_carpeta(
                modulo_produccion, 'ProduccionLotes', 'Producción y lotes', 'fas fa-boxes',
                [{'nombre': '', 'botones': [
                    _boton(
                        'produccion-planta', 'Lo que produce la planta',
                        reverse('produccion_publica', args=[slug]), 'fas fa-box-open',
                        'Productos por línea, corridas recientes y lotes disponibles',
                    ),
                    boton_simulador('materiales'),
                ]}],
            ))
        lineas_calidad = [
            {'codigo': grupo['procesos'][0].familia.codigo, 'nombre': grupo['nombre']}
            for grupo in lineas_de_procesos(procesos)
            if grupo['procesos'] and grupo['procesos'][0].familia_id
        ]
        boton_protocolos = lambda linea: _boton(  # noqa: E731
            f'protocolos-control-{linea["codigo"]}', 'Protocolos de control',
            reverse('protocolos_control', args=[slug]) + f'?familia={linea["codigo"]}',
            'fas fa-clipboard-check', 'Puntos críticos de control de cada proceso',
        )
        boton_calidad = lambda linea: _boton(  # noqa: E731
            f'calidad-lotes-{linea["codigo"]}', 'Control de calidad y requisitos',
            reverse('calidad_publica', args=[slug]) + f'?familia={linea["codigo"]}',
            'fas fa-vial', 'Control de calidad de los lotes, requisitos de ingreso y normas de seguridad',
        )
        boton_especificaciones = lambda linea: _boton(  # noqa: E731
            f'especificaciones-{linea["codigo"]}', 'Especificaciones de producto',
            reverse('especificaciones_producto', args=[slug]) + f'?familia={linea["codigo"]}',
            'fas fa-ruler-combined', 'Lo que cada lote debe cumplir para salir al despacho',
        )
        boton_haccp = lambda linea: _boton(  # noqa: E731
            f'plan-haccp-{linea["codigo"]}', 'Plan HACCP',
            reverse('plan_haccp', args=[slug]) + f'?familia={linea["codigo"]}',
            'fas fa-file-medical', 'Puntos críticos, límites, vigilancia y acción correctiva de cada proceso',
        )
        transversales = es_planta and PlanCalidad.objects.filter(
            unidad=unidad, activo=True, familia__isnull=True).exists()
        grupo_transversal = {'nombre': 'Controles transversales', 'botones': [_boton(
            'calidad-transversal', 'Recepción y controles comunes',
            reverse('calidad_publica', args=[slug]) + '?transversales=1', 'fas fa-vial',
            'Controles de materias primas y requisitos que aplican a más de una familia.',
        )]}
        if es_planta:
            # Cada control en su sección numerada (5.1 a 5.4), en su pestaña. Si la
            # unidad desactivó «Calidad e inocuidad», no se muestra en otra.
            if 'calidad-inocuidad' in claves:
                for numero, identificador, boton in (('5.1', 'Seccion5_1', boton_protocolos),
                                                     ('5.2', 'Seccion5_2', boton_especificaciones),
                                                     ('5.3', 'Seccion5_3', boton_haccp),
                                                     ('5.4', 'Seccion5_4', boton_calidad)):
                    grupos = [{'nombre': linea['nombre'], 'botones': [boton(linea)]} for linea in lineas_calidad]
                    if numero == '5.4' and transversales:
                        grupos.append(grupo_transversal)
                    carpetas.append(_carpeta('calidad-inocuidad', identificador, '', ICONOS_SECCION[numero],
                                             grupos, abierta=False, numero=numero, seccion=True))
        else:
            carpetas.append(_carpeta(modulo_calidad, 'CalidadInocuidad', 'Calidad e inocuidad',
                                     'fas fa-clipboard-check', [
                {'nombre': linea['nombre'], 'botones': [boton_protocolos(linea), boton_calidad(linea), boton_haccp(linea)]}
                for linea in lineas_calidad
            ]))
    # Las áreas y los equipos van a su pestaña; sin ella, junto a los procesos de la planta.
    modulo_equipos = _modulo_entre(claves, MODULOS_EQUIPOS, modulo_del_aula(modulos) if procesos else '')
    vista_gestor_catalogo = usuario is not None and puede_gestionar_unidad(usuario, unidad)
    equipos_unidad = list(
        UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad),
            **({} if vista_gestor_catalogo else {'activa': True, 'fecha_baja__isnull': True}),
        ).select_related('equipo').distinct().order_by('equipo__nombre', 'codigo_unidad')
    ) if modulo_equipos else []
    if usuario is not None:
        equipos_unidad = publicos_para(visibles_para(equipos_unidad, unidad, usuario), unidad, usuario)
    # Cada área es un botón del menú y abre su propia página.
    areas = list(
        EspacioReservable.objects.filter(unidad=unidad, **({} if vista_gestor_catalogo else {'activo': True}))
        .annotate(total_equipos=Count('equipos_asociados', filter=Q(equipos_asociados__activa=True), distinct=True))
        .order_by('orden', 'nombre')
    ) if modulo_equipos else []
    # El número de cada área cuenta lo que el visitante puede ver, igual que la lista de fichas.
    visibles = {equipo.pk for equipo in equipos_unidad if equipo.activa and not equipo.fecha_baja}
    por_area = Counter(
        espacio_id for espacio_id, equipo_id in EspacioReservable.equipos_asociados.through.objects
        .filter(espacioreservable__in=areas).values_list('espacioreservable_id', 'unidadequipo_id') if equipo_id in visibles)
    for area in areas:
        area.total_equipos = por_area.get(area.pk, 0)
    from apps.recursos.presentation.equipo_referencia import referencias_por_area
    referencias_equipo = referencias_por_area(areas, usuario)
    for area in areas:
        area.total_referencias = len(referencias_equipo.get(area.pk, []))
    if areas:
        carpetas.append(_carpeta(modulo_equipos, 'AreasEquipos', 'Áreas de la unidad', 'fas fa-warehouse', [
            {'nombre': '', 'botones': [
                _boton(
                    f'area-{area.pk}', area.nombre, reverse('area_unidad', args=[slug, area.codigo]),
                    ICONOS_DE_ESPACIO.get(area.tipo, 'fas fa-vector-square'),
                    f'{area.nombre}: qué se hace, cómo se reserva, quién la atiende y sus equipos',
                    subtitulo=(f'{area.total_equipos} registrado{pluralize(area.total_equipos)} · '
                               f'{area.total_referencias} ficha{pluralize(area.total_referencias)} de referencia'
                               if area.total_referencias else f'{area.get_tipo_display()} · {area.total_equipos} equipo{pluralize(area.total_equipos)}'),
                )
                for area in areas
            ]},
        ], numero=num('areas_equipos'), seccion=bool(mapa), mapa=mapa))
    elif modulo_equipos and equipos_unidad:
        # Sin áreas registradas, los equipos se consultan juntos.
        carpetas.append(_carpeta(modulo_equipos, 'AreasEquipos', 'Equipos de la unidad', 'fas fa-warehouse', [
            {'nombre': '', 'botones': [
                _boton('areas-equipos', 'Equipos de la unidad', reverse('areas_equipos', args=[slug]),
                       'fas fa-cogs', 'Los equipos de la unidad con su ficha técnica'),
            ]},
        ], numero=num('areas_equipos'), seccion=bool(mapa), mapa=mapa))
    if mapa and modulo_equipos and (equipos_unidad or referencias_equipo):
        # Primero el escáner: se lee la etiqueta o el QR de un equipo y se llega a su ficha.
        escaner = {'nombre': 'Escáner de equipos', 'clave': 'escaner', 'botones': [_boton(
            'escaner-equipos', 'Escáner de equipos', reverse('escaner_unidad', args=[slug]), 'fas fa-barcode',
            'Lee la etiqueta de bodega o el QR de un equipo y abre su ficha', subtitulo='Etiqueta de bodega o QR',
        )]}
        fichas = _carpeta(modulo_equipos, 'FichasEquipo', 'Fichas de equipo', 'fas fa-microchip',
                          [escaner] + _fichas_por_area(slug, areas, equipos_unidad, estado_objeto, referencias_equipo),
                          numero=num('fichas_equipo'), seccion=True, mapa=mapa)
        fichas['total'] -= 1  # El escáner es una herramienta: el número de la carpeta cuenta equipos.
        carpetas.append(fichas)
    if es_planta and modulo_equipos and equipos_unidad:
        carpetas.append(_carpeta(modulo_equipos, 'ServiciosIndustriales', 'Servicios industriales', 'fas fa-plug', [
            {'nombre': '', 'botones': [
                _boton(
                    'servicios-industriales', 'Servicios industriales de la planta',
                    reverse('servicios_industriales', args=[slug]), 'fas fa-plug',
                    'Energía, vapor, agua, aire, frío y efluentes de equipos y procesos',
                ),
            ]},
        ], numero='3.3', seccion=True))
    if es_planta and procesos and modulo_equipos:
        carpetas.append(_carpeta(
            modulo_equipos,
            'CapacidadEquilibrado',
            'Capacidad, cuellos de botella y equilibrado',
            'fas fa-stream',
            [{'nombre': '', 'botones': [boton_simulador('linea')]}],
            numero='3.4',
            seccion=True,
        ))
    # Las secciones que la unidad creó con plantilla, después de las comunes de su pestaña.
    from apps.gestion_unidades.presentation.secciones_propias import carpetas_de_secciones
    carpetas.extend(carpetas_de_secciones(unidad, claves, usuario))
    if mapa:
        carpetas.extend(_carpetas_de_laboratorio(unidad, mapa, claves, usuario))
        _completar_secciones(carpetas, claves, mapa)
    elif claves:
        # Sin mapa numerado, las novedades van a la pestaña de información o a la primera.
        modulo = 'informacion-general' if 'informacion-general' in claves else claves[0]
        carpetas.extend(_carpeta_novedades(unidad, usuario, modulo))
    for carpeta in carpetas:
        # La clave identifica la subcarpeta para que la unidad la renombre, ordene u oculte.
        carpeta['grupos'] = [
            {**grupo, 'id': f'{carpeta["id"]}Grupo{indice}', 'abierta': indice == 1,
             'clave': grupo.get('clave') or slugify(grupo['nombre']) or f'grupo-{indice}'}
            for indice, grupo in enumerate(carpeta['grupos'], start=1)
        ]
    if mapa:
        modulos_abiertos = set()
        for carpeta in carpetas:
            carpeta['abierta'] = carpeta['modulo'] not in modulos_abiertos
            modulos_abiertos.add(carpeta['modulo'])
    return carpetas


def _carpeta_novedades(unidad, usuario, modulo, numero='', mapa=None):
    """«Novedades y avisos»: un botón a la página de la unidad; nada si no tiene ninguna."""
    novedades = novedades_de(unidad, usuario)
    if not novedades:
        return []
    return [_carpeta(modulo, 'NovedadesUnidad', 'Novedades y avisos', 'fas fa-bullhorn', [{'nombre': '', 'botones': [
        _boton('novedades-unidad', f'Novedades y avisos ({len(novedades)})',
               reverse('novedades_unidad', args=[unidad.slug]), 'fas fa-bullhorn',
               'Noticias, logros, eventos y convocatorias de la unidad', subtitulo=novedades[0].titulo),
    ]}], abierta=False, numero=numero, seccion=bool(numero), mapa=mapa)]


def _carpetas_de_procesos(unidad, mapa, claves, usuario):
    """3.1 a 3.3 del laboratorio: cada proceso en su página, sus métodos y lo que entrega.

    Quien gestiona la unidad ve también los borradores, marcados como pendientes.
    """
    slug = unidad.slug
    borradores = usuario is not None and puede_gestionar_unidad(usuario, unidad)
    carpetas = []

    def agregar(clave, identificador, botones):
        numero = mapa.numero(clave)
        if numero and mapa.modulo_de(numero) in claves and botones:
            carpetas.append(_carpeta(mapa.modulo_de(numero), identificador, '', _icono(mapa, numero),
                                     [{'nombre': '', 'botones': botones}],
                                     abierta=False, numero=numero, seccion=True, mapa=mapa))

    procesos = procesos_laboratorio.procesos_de(unidad, borradores)
    agregar('procesos', 'ProcesosLaboratorio', [
        _boton(f'proceso-{proceso.pk}', proceso.nombre, reverse('proceso_laboratorio', args=[slug, proceso.pk]),
               'fas fa-project-diagram', f'{proceso.nombre}: paso a paso, con sus equipos, insumos y controles',
               '' if proceso.activa else 'pendiente', subtitulo=procesos_laboratorio.resumen_de(proceso))
        for proceso in procesos
    ])
    metodos = procesos_laboratorio.con_metodo(procesos)
    agregar('metodos', 'MetodosLaboratorio', [
        _boton('metodos-laboratorio', f'Métodos y parámetros ({len(metodos)})',
               reverse('metodos_laboratorio', args=[slug]), 'fas fa-ruler',
               'Cómo se hace cada etapa y qué se controla en ella'),
    ] if metodos else [])
    productos = procesos_laboratorio.productos_de(unidad, borradores)
    agregar('productos', 'ProductosLaboratorio', [
        _boton('productos-laboratorio', f'Productos y servicios ({len(productos)})',
               reverse('productos_laboratorio', args=[slug]), 'fas fa-cube',
               'Lo que entrega la unidad y con qué proceso'),
    ] if productos else [])
    return carpetas


def _carpetas_de_laboratorio(unidad, mapa, claves, usuario):
    """Las secciones de los mapas numerados que se arman con datos propios de la unidad."""
    slug = unidad.slug
    carpetas = []
    es_logistica = mapa.tipo == 'laboratorios' and slug == 'laboratorio-logistica-comercio-internacional'

    def modulo_de(clave):
        numero = mapa.numero(clave)
        return numero, (mapa.modulo_de(numero) if numero else '')

    numero, modulo = modulo_de('novedades')
    if numero and modulo in claves:
        carpetas.extend(_carpeta_novedades(unidad, usuario, modulo, numero, mapa))
    if mapa.tipo == 'laboratorios':
        carpetas.extend(_carpetas_de_procesos(unidad, mapa, claves, usuario))
    if mapa.tipo == 'observatorios':
        from apps.observatorios.operacion.presentation.observatorio import carpetas_de_observatorio
        carpetas.extend(carpetas_de_observatorio(unidad, mapa, claves, usuario))
    if mapa.tipo == 'centro_experimental':
        from apps.centros_experimentales.operacion.presentation.centro_experimental import carpetas_de_centro
        carpetas.extend(carpetas_de_centro(unidad, mapa, claves, usuario))
    numero, modulo = modulo_de('software')
    if numero and modulo in claves:
        total = unidad.software_disponible.filter(activo=True).count()
        if total:
            carpetas.append(_carpeta(modulo, 'SoftwarePlataformas', '', _icono(mapa, numero), [{'nombre': '', 'botones': [
                _boton('software-unidad', f'Software y plataformas ({total})', reverse('software_unidad', args=[slug]),
                       'fas fa-laptop-code', 'Programas, licencias y forma de acceso de cada uno'),
            ]}], abierta=False, numero=numero, seccion=True, mapa=mapa))
    numero, modulo = modulo_de('materiales')
    if numero and modulo in claves:
        total = Consumible.objects.filter(unidad=unidad, activo=True).count()
        if total:
            carpetas.append(_carpeta(modulo, 'MaterialesInsumos', '', _icono(mapa, numero), [{'nombre': '', 'botones': [
                _boton('insumos-unidad', f'Insumos y materiales ({total})', reverse('insumos_unidad', args=[slug]),
                       'fas fa-boxes', 'Cada insumo y material registrado, con su área, los equipos que lo usan y su stock'),
            ]}], abierta=False, numero=numero, seccion=True, mapa=mapa))
    numero, modulo = modulo_de('asignaturas')
    if numero and modulo in claves:
        total = unidad.asignaturas.filter(activa=True).count()
        if total:
            botones_asignaturas = [
                _boton('asignaturas-unidad', f'Asignaturas y carreras ({total})', reverse('asignaturas_unidad', args=[slug]),
                       'fas fa-graduation-cap', 'Qué asignaturas practican aquí, de qué carreras y en qué semestre'),
            ]
            if es_logistica:
                botones_asignaturas.append(_boton(
                    'logistica-matriz-academica', 'Mapa académico y rutas logísticas',
                    reverse('logistica_identidad', args=[slug]) + '#matriz', 'fas fa-project-diagram',
                    'Relación entre las asignaturas registradas, las carreras y las seis áreas del laboratorio',
                ))
            carpetas.append(_carpeta(modulo, 'AsignaturasCarreras', '', _icono(mapa, numero),
                                     [{'nombre': '', 'botones': botones_asignaturas}],
                                     abierta=False, numero=numero, seccion=True, mapa=mapa))
    numero, modulo = modulo_de('recursos_aprendizaje')
    if numero and modulo in claves:
        por_area = {}
        for artefacto in artefactos_publicos(unidad, usuario).order_by('area__orden', 'area__nombre', 'nombre'):
            por_area.setdefault(artefacto.area.nombre if artefacto.area_id else 'Generales', []).append(artefacto)
        grupos_aprendizaje = [
            {'nombre': area if len(por_area) > 1 else '', 'botones': [
                _boton(f'artefacto-{artefacto.pk}', artefacto.nombre,
                       reverse('artefacto_externo', args=[slug, artefacto.codigo]), 'fas fa-cube',
                       f'{artefacto.get_tipo_display()}: {artefacto.nombre}')
                for artefacto in artefactos
            ]} for area, artefactos in por_area.items()
        ]
        if es_logistica:
            grupos_aprendizaje.insert(0, {'nombre': 'Simulación de cadena de suministro', 'botones': [
                _boton('logistica-centro-distribucion', 'Centro de distribución: práctica guiada',
                       reverse('logistica_distribucion', args=[slug]), 'fas fa-warehouse',
                       'Recepción, control, ubicación, picking, embalaje y despacho en tres variantes',
                       subtitulo='Normal · pico · falla · datasets y comparación'),
                _boton('logistica-operaciones-3d', 'Laboratorio de simulación 3D',
                       reverse('logistica_operaciones', args=[slug]), 'fas fa-cubes',
                       'Casos de almacén, puerto, fábrica, distribución, robótica y pronóstico',
                       subtitulo='Casos por área · analítica · partidas guardadas'),
                _boton('logistica-cerveza-multijugador', 'Juego de la cerveza: multijugador',
                       reverse('logistica_cerveza_multijugador', args=[slug]), 'fas fa-users',
                       'Cuatro roles humanos, salas por código y evaluación de cadena al finalizar',
                       subtitulo='Partidas compartidas · pedidos privados · efecto látigo'),
                _boton('logistica-juego-cerveza', 'Juego de la cerveza: práctica individual',
                       reverse('logistica_juego_cerveza', args=[slug]), 'fas fa-network-wired',
                       'Decide pedidos, observa los retardos y compara inventarios, faltantes y costos',
                       subtitulo='Simulador propio · datos educativos · cuatro eslabones'),
            ]})
        if grupos_aprendizaje:
            carpetas.append(_carpeta(modulo, 'RecursosAprendizaje', '', _icono(mapa, numero), grupos_aprendizaje,
                                     abierta=False, numero=numero, seccion=True, mapa=mapa))
    # Formación: accesos al catálogo, sin construir un enlace por cada curso.
    numero, modulo = modulo_de('cursos')
    if numero and modulo in claves:
        from apps.formacion.presentation.cursos import grupos_de_cursos
        grupos = grupos_de_cursos(unidad, usuario)
        if mapa.tipo == 'centro_experimental':
            # Un centro dice además qué cursos debería dictar, por eje.
            from apps.centros_experimentales.operacion.presentation.centro_experimental import grupo_cursos_recomendados
            recomendados = grupo_cursos_recomendados(unidad)
            grupos += [recomendados] if recomendados else []
        if grupos:
            cursos = _carpeta(modulo, 'CursosCapacitaciones', '', _icono(mapa, numero), grupos,
                              abierta=False, numero=numero, seccion=True, mapa=mapa)
            cursos['total'] = sum(grupo.get('total_formacion', 0) for grupo in grupos)
            carpetas.append(cursos)
    actividades = None
    for clave, (titulo, _propositos, _subtipos) in GRUPOS.items():
        numero, modulo = modulo_de(clave)
        if not numero or modulo not in claves:
            continue
        actividades = actividades if actividades is not None else actividades_de(unidad)
        if actividades[clave]:
            carpetas.append(_carpeta(modulo, f'Actividades{clave.title().replace("_", "")}', '', _icono(mapa, numero), [
                {'nombre': '', 'botones': [
                    _boton(f'actividades-{clave}', f'{titulo} ({len(actividades[clave])})',
                           reverse('proyectos_unidad', args=[slug, clave]), _icono(mapa, numero),
                           'Actividad, carrera, sesiones y horas en el laboratorio'),
                ]}], abierta=False, numero=numero, seccion=True, mapa=mapa))
    return carpetas


# Botones que son herramientas del menú, no contenido: no cuentan en el número de la carpeta.
HERRAMIENTAS_DEL_MENU = {'escaner-equipos', 'cursos-por-anio', 'mis-cursos', 'cafe-cadena'}


def ajustar_grupos(carpeta, ajuste, con_ocultos=False):
    """Aplica a una carpeta automática lo que la unidad decidió de sus subcarpetas y elementos: nombre propio,
    orden y lo oculto. Con `con_ocultos` (el organizador del admin) conserva lo oculto, marcado."""
    decisiones = (ajuste.grupos if ajuste else None) or {}
    ocultos = set((ajuste.elementos_ocultos if ajuste else None) or ())
    if not decisiones and not ocultos and not con_ocultos:
        return carpeta
    grupos = []
    for posicion, grupo in enumerate(carpeta['grupos']):
        decision = decisiones.get(grupo['clave']) or {}
        botones = [{**boton, 'oculto': boton['id'] in ocultos} for boton in grupo['botones']]
        grupo = {**grupo, 'nombre_comun': grupo['nombre'], 'nombre': decision.get('titulo') or grupo['nombre'],
                 'oculto': bool(decision.get('oculta')), 'posicion': decision.get('orden', posicion),
                 'botones': botones if con_ocultos else [boton for boton in botones if not boton['oculto']]}
        if con_ocultos or (not grupo['oculto'] and grupo['botones']):
            grupos.append(grupo)
    grupos.sort(key=lambda grupo: grupo['posicion'])
    for indice, grupo in enumerate(grupos):
        grupo['abierta'] = indice == 0
    visibles = [boton for grupo in grupos if not grupo['oculto'] for boton in grupo['botones']
                if not boton['oculto'] and boton['id'] not in HERRAMIENTAS_DEL_MENU]
    carpeta = {**carpeta, 'grupos': grupos, 'total': len(visibles)}
    if not visibles and not carpeta.get('pendiente') and not con_ocultos:
        carpeta.update(pendiente=True, mensaje='La unidad retiró del menú el contenido automático de esta sección.')
    return carpeta


def contexto_aula(unidad, modulos, usuario=None):
    """Lo que la ficha pública necesita para dibujar el aula en sus pestañas."""
    procesos = procesos_publicos(unidad, usuario)
    modulos = list(modulos)
    claves = [modulo.clave for modulo in modulos]
    ajustes = ajustes_de(unidad)
    mapa = mapa_de(unidad)
    carpetas = []
    # Cada unidad puede renombrar u ocultar una sección común; la oculta se va con sus carpetas.
    for carpeta in carpetas_del_aula(unidad, modulos, procesos, usuario):
        if carpeta['seccion']:
            seccion = seccion_de(carpeta['numero'], ajustes, mapa)
            if seccion['oculta']:
                continue
            carpeta['titulo'] = seccion['titulo']
            carpeta = ajustar_grupos(carpeta, ajustes.get(carpeta['numero']))
        carpetas.append(carpeta)
    base = modulo_del_aula(modulos) if procesos else ''
    if mapa:
        # Un observatorio no tiene guías de práctica: su mapa no trae la sección.
        guias_modulo = mapa.modulo_de(mapa.numero('guias')) if mapa.numero('guias') else ''
    else:
        guias_modulo = base or (claves[0] if claves else '')
    return {
        'aula': {
            'procesos': procesos,
            'carpetas': carpetas,
            'modulos_con_carpetas': sorted({carpeta['modulo'] for carpeta in carpetas}),
        },
        'guias_modulo_clave': guias_modulo,
        'secciones_planta': secciones_con_nombre(unidad, ajustes, mapa),
    }


# ------------------------------------------------------ la reserva de referencia
def _reserva_visible(usuario, reserva):
    if not getattr(usuario, 'is_authenticated', False):
        return False
    if reserva.usuario_id == usuario.pk or reserva.participantes.filter(pk=usuario.pk).exists():
        return True
    return any(
        puede_operar_modulo_unidad(usuario, reserva.laboratorio, modulo) for modulo in ('practicas', 'produccion')
    )


def sesion_de_referencia(request, unidad):
    """La reserva o la programación cuyos datos alimentan el simulador, si quien entra puede verla."""
    reserva_id = (request.GET.get('reserva') or '').strip()
    programacion_id = (request.GET.get('programacion') or '').strip()
    if reserva_id.isdigit():
        reserva = (
            Reserva.objects.filter(pk=reserva_id, laboratorio=unidad)
            .select_related('receta', 'programacion', 'laboratorio')
            .first()
        )
        if reserva is None or not _reserva_visible(request.user, reserva):
            return None
        return {
            'reserva': reserva,
            'programacion': reserva.programacion,
            'sesiones': [reserva],
            'etiqueta': f'{reserva.codigo_reserva or reserva.pk} · {reserva.fecha:%d/%m/%Y}',
            'parametro': ('reserva', str(reserva.pk)),
        }
    if programacion_id.isdigit():
        sesiones = list(
            Reserva.objects.filter(programacion_id=programacion_id, laboratorio=unidad)
            .select_related('receta', 'laboratorio', 'programacion')
            .order_by('fecha', 'pk')
        )
        if not sesiones or not _reserva_visible(request.user, sesiones[0]):
            return None
        return {
            'reserva': None,
            'programacion': sesiones[0].programacion,
            'sesiones': sesiones,
            'etiqueta': f'programación de {len(sesiones)} sesiones desde el {sesiones[0].fecha:%d/%m/%Y}',
            'parametro': ('programacion', programacion_id),
        }
    return None


def _escala(receta, factor):
    return f'{_texto(receta.cantidad_base * _num(factor))} {receta.unidad_base}'


def enlaces_del_aula(reserva):
    """Los simuladores y la ficha del proceso de una reserva, con sus datos ya cargados."""
    if not reserva.receta_id:
        return None
    slug = reserva.laboratorio.slug
    consulta = f'?reserva={reserva.pk}'
    return {
        'proceso': reserva.receta.nombre,
        'escala': _escala(reserva.receta, reserva.factor_proceso or 1),
        'ficha_url': reverse('ficha_proceso_publica', args=[slug, reserva.receta_id]),
        'balance_url': reverse('simulador_balance', args=[slug]) + consulta,
        'linea_url': reverse('simulador_linea', args=[slug]) + consulta,
        'materiales_url': reverse('simulador_materiales', args=[slug]) + (
            f'?programacion={reserva.programacion_id}' if reserva.programacion_id else consulta
        ),
    }


def _receta_elegida(request, procesos, referencia):
    receta_id = (request.GET.get('receta') or '').strip()
    elegida = next((receta for receta in procesos if str(receta.pk) == receta_id), None)
    if elegida is not None:
        return elegida
    reserva = referencia['reserva'] if referencia else None
    if reserva is not None and reserva.receta_id:
        return next((receta for receta in procesos if receta.pk == reserva.receta_id), procesos[0])
    return procesos[0]


def _cantidad_elegida(request, receta, referencia):
    """La materia prima: la escrita, la de la reserva o la corrida base."""
    reserva = referencia['reserva'] if referencia else None
    predeterminada = _num(receta.cantidad_base)
    if reserva is not None and reserva.receta_id == receta.pk:
        predeterminada = _num(receta.cantidad_base) * _num(reserva.factor_proceso or 1)
    cantidad = _decimal(request.GET.get('cantidad'), predeterminada)
    return cantidad if cantidad > 0 else predeterminada


def _factor(receta, cantidad):
    factor = (_num(cantidad) / _num(receta.cantidad_base)).quantize(TRES, rounding=ROUND_HALF_UP)
    return factor if factor > 0 else TRES


# ------------------------------------------------------------ protocolos de control
def protocolos_de_control(procesos):
    """Los puntos críticos de control de cada proceso, con su parámetro y su límite."""
    resultado = []
    for receta in procesos:
        puntos = [
            {
                'orden': etapa.orden,
                'nombre': etapa.nombre,
                'tipo': etapa.get_tipo_display(),
                'control': 'PCC · inocuidad' if etapa.punto_critico else 'PC · calidad',
                'critico': etapa.punto_critico,
                'parametro': etapa.parametro,
                'limite': etapa.limite,
                'equipo': etapa.equipo.nombre if etapa.equipo_id else '',
                'espacio': etapa.espacio.nombre if etapa.espacio_id else '',
                'instrucciones': etapa.instrucciones,
            }
            for etapa in receta.etapas.filter(Q(punto_critico=True) | Q(punto_control=True))
            .select_related('equipo', 'espacio').order_by('orden')
        ]
        resultado.append({'receta': receta, 'puntos': puntos, 'total_etapas': receta.etapas.count()})
    return resultado


# ------------------------------------------------------------ producción y lotes
def produccion_publica(unidad, procesos, usuario=None):
    """Catálogo estable que la planta publica, sin datos de su operación diaria."""
    productos = list(
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
    productos = [
        producto for producto in productos
        if _objeto_visible_para(producto, unidad, usuario)
    ]
    return {
        'lineas': [
            {'nombre': linea['nombre'], 'productos': linea['elementos']}
            for linea in _por_linea(
                productos,
                lambda producto: producto.familia.nombre if producto.familia_id else '',
                lambda producto: producto.familia.orden if producto.familia_id else None,
            )
        ],
        'resumen': {'productos': len(productos), 'procesos': len(procesos)},
    }


def corridas_lotes_publicos(unidad, hoy=None):
    """Solo las dos cifras que demuestran actividad, nunca registros operativos."""
    hoy = hoy or timezone.localdate()
    ficha = FichaContenido.objects.filter(
        unidad=unidad,
        tipo='documento',
        codigo__endswith='-DOC-CORRIDAS-RESUMEN',
        estado='publicada',
        visibilidad='publica',
    ).first()
    if ficha is None:
        raise Http404('La unidad no publica el resumen de corridas y lotes')
    lotes_vigentes = (
        LoteProducto.objects.reales().filter(
            unidad=unidad, estado='disponible', control_calidad='aprobado', cantidad_disponible__gt=0,
        )
        .filter(Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gte=hoy))
        .count()
    )
    return {
        'ficha': ficha,
        'corridas_mes': OrdenProduccion.objects.reales().filter(
            unidad=unidad, estado='terminada', fecha_fin__gte=hoy.replace(day=1),
        ).count(),
        'lotes_vigentes': lotes_vigentes,
    }


# ------------------------------------------------------------ calidad e inocuidad
def calidad_publica(unidad, procesos, familia=None, solo_transversales=False):
    """El control de calidad de los lotes, los requisitos de ingreso y las normas de seguridad."""
    lotes = LoteProducto.objects.reales().filter(unidad=unidad).select_related('producto')
    # La familia consultada ve sus lotes; los controles transversales no miran lotes de producto.
    if solo_transversales:
        lotes = lotes.none()
    elif familia is not None:
        lotes = lotes.filter(producto__familia=familia)
    conteo = {
        clave: lotes.filter(control_calidad=clave).count() for clave in ('pendiente', 'aprobado', 'rechazado')
    }
    try:
        reglamento = unidad.reglamento_publico
    except ObjectDoesNotExist:
        reglamento = None
    normas = (
        [linea.strip() for linea in (reglamento.seguridad or '').splitlines() if linea.strip()]
        if reglamento is not None and reglamento.activo else []
    )
    protocolos = protocolos_de_control(procesos)
    return {
        'conteo': conteo,
        'publicada': calidad_publicada(
            unidad, familia=familia, solo_transversales=solo_transversales,
        ),
        # Resumido por producto: el detalle de cada lote queda en la superficie interna.
        'por_producto': list(
            lotes.values('producto__nombre')
            .annotate(
                total=Count('pk'),
                liberados=Count('pk', filter=Q(control_calidad='aprobado')),
                rechazados=Count('pk', filter=Q(control_calidad='rechazado')),
                por_liberar=Count('pk', filter=Q(control_calidad='pendiente')),
            )
            .order_by('producto__nombre')
        ),
        'requisitos': resumen_requisitos(unidad),
        'normas': normas,
        'protocolos': protocolos,
        'total_puntos': sum(len(item['puntos']) for item in protocolos),
    }


def simuladores_proceso_legacy_view(request, slug):
    """Lleva el acceso antiguo del acordeón a la sección 2.4 de la ficha."""
    unidad = get_object_or_404(Unidad, slug=slug)
    destino = f'{unidad.get_absolute_url()}?recurso=simulador-balance#procesos-protocolos'
    return redirect(destino, permanent=True)


# ----------------------------------------------------------- áreas y equipos
# El icono con que cada tipo de espacio aparece en el menú de la ficha y en las páginas de áreas.
ICONOS_DE_ESPACIO = {
    'area': 'fas fa-vector-square',
    'estacion': 'fas fa-desktop',
    'sala': 'fas fa-chalkboard',
    'puesto': 'fas fa-user-cog',
    'cabina': 'fas fa-vr-cardboard',
    'linea': 'fas fa-industry',
    'camara': 'fas fa-snowflake',
    'parcela': 'fas fa-seedling',
    'invernadero': 'fas fa-leaf',
    'establo': 'fas fa-horse',
}


def _fichas_por_area(slug, areas, equipos_unidad, estado_objeto, referencias=None):
    """Las fichas de equipo agrupadas por área: un botón por equipo (no por unidad física), con su foto o
    su ícono y cuántas unidades tiene; lo que no está en ningún área va al final."""
    ids_por_area = {}
    for espacio_id, equipo_id in EspacioReservable.equipos_asociados.through.objects.filter(
            espacioreservable__in=areas).values_list('espacioreservable_id', 'unidadequipo_id'):
        ids_por_area.setdefault(espacio_id, set()).add(equipo_id)

    def botones(fisicas):
        por_tipo = OrderedDict()
        for fisica in fisicas:
            por_tipo.setdefault(fisica.equipo_id, []).append(fisica)
        resultado = []
        for unidades in por_tipo.values():
            primera, tipo = unidades[0], unidades[0].equipo
            disponibles = sum(1 for fisica in unidades if fisica.estado_unidad == 'disponible')
            subtitulo = (f'{primera.codigo_unidad} · {primera.get_estado_unidad_display()}' if len(unidades) == 1
                         else f'{len(unidades)} unidades · {disponibles} disponible{pluralize(disponibles)}')
            existentes = sum(1 for fisica in unidades if fisica.activa and not fisica.fecha_baja)
            if existentes < len(unidades):
                subtitulo = f'{existentes} existentes · {len(unidades) - existentes} referencias inactivas (vista de gestión)'
            resultado.append(_boton(
                f'ficha-equipo-{primera.pk}', tipo.nombre,
                reverse('ficha_equipo_publica', args=[slug, primera.codigo_unidad]),
                tipo.icono or 'fas fa-cogs', f'Ficha técnica de {tipo.nombre}: unidades, estado, insumos y software',
                estado_objeto(primera), subtitulo=subtitulo, imagen=imagen_de(tipo)[0],
            ))
        return resultado

    asignados, grupos = set(), []
    for area in areas:
        ids = ids_por_area.get(area.pk, set())
        fisicas = [fisica for fisica in equipos_unidad if fisica.pk in ids]
        asignados |= ids
        items = botones(fisicas)
        items.extend(_boton(
            f'equipo-referencia-{elemento.pk}', elemento.nombre,
            reverse('ficha_equipo_referencia', args=[slug, elemento.pk]),
            elemento.icono or 'fas fa-cogs', elemento.para_que,
            subtitulo='Ficha técnica de referencia', imagen=elemento.imagen_url,
        ) for elemento in (referencias or {}).get(area.pk, []))
        if items:
            grupos.append({'nombre': area.nombre, 'clave': f'area-{slugify(area.codigo)}', 'botones': items})
    sueltos = [fisica for fisica in equipos_unidad if fisica.pk not in asignados]
    if sueltos:
        grupos.append({'nombre': 'Sin área asignada' if grupos else '', 'clave': 'sin-area', 'botones': botones(sueltos)})
    return grupos


def areas_y_equipos(unidad, usuario=None):
    """Cada área activa con sus equipos, su software, sus recursos en línea y su responsable."""
    unidades_equipo = list(
        UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True)
        .select_related('equipo')
        .prefetch_related('equipo__auxiliares')
        .distinct()
        .order_by('equipo__nombre', 'codigo_unidad')
    )
    if usuario is not None:
        # El gobierno editorial de las plantas: lo que no está publicado no aparece en sus áreas; tampoco lo que
        # no está en servicio, salvo para quien gestiona.
        unidades_equipo = publicos_para(visibles_para(unidades_equipo, unidad, usuario), unidad, usuario)
    espacios = list(
        EspacioReservable.objects.filter(unidad=unidad, activo=True)
        .select_related('responsable', 'responsable__usuario')
        .prefetch_related('equipos_asociados__software_instalado')
        .order_by('orden', 'nombre')
    )
    recursos_por_area = {}
    for artefacto in artefactos_publicos(unidad, usuario).filter(area__isnull=False).order_by('nombre'):
        recursos_por_area.setdefault(artefacto.area_id, []).append(artefacto)
    asignados, areas = set(), []
    for espacio in espacios:
        ids = {unidad_equipo.pk for unidad_equipo in espacio.equipos_asociados.all()}
        asignados |= ids
        areas.append({
            'espacio': espacio,
            'equipos': [unidad_equipo for unidad_equipo in unidades_equipo if unidad_equipo.pk in ids],
            'software': sorted({software.nombre for unidad_equipo in espacio.equipos_asociados.all()
                                for software in unidad_equipo.software_instalado.all() if software.activo}),
            'recursos': recursos_por_area.get(espacio.pk, []),
            'responsable': espacio.responsable if espacio.responsable_id and espacio.responsable.activo
            and espacio.responsable.publico else None,
            'url': reverse('area_unidad', args=[unidad.slug, espacio.codigo]),
            'icono': ICONOS_DE_ESPACIO.get(espacio.tipo, 'fas fa-vector-square'),
        })
    return {
        'areas': areas,
        'sin_area': [unidad_equipo for unidad_equipo in unidades_equipo if unidad_equipo.pk not in asignados],
        'total_equipos': len(unidades_equipo),
        'total_areas': len(areas),
    }


# ------------------------------------------------------------------- las vistas
def _pagina_o_documento(request, contexto, clave, plantilla, nombre):
    """La página; o su documento, si la dirección lo pidió.

    Antes la única forma de bajar una de estas páginas era el «Imprimir» del
    navegador, que escribe la dirección y la fecha en los bordes y corta las
    tablas donde caiga. Ahora el mismo contexto que pinta la pantalla arma el
    PDF institucional, así que lo revisado es exactamente lo descargado.
    """
    formato = formato_pedido(request)
    if formato:
        return respuesta_pdf(documento_de_pagina(clave, contexto), nombre, formato)
    return render(request, plantilla, contexto)


def _respuesta_csv(nombre, encabezados, filas):
    """CSV UTF-8 compatible con Excel, generado desde la misma fuente de la ficha."""
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    respuesta.write('\ufeff')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return respuesta


def _unidad_con_procesos(slug, usuario=None):
    unidad = get_object_or_404(Unidad, slug=slug)
    procesos = procesos_publicos(unidad, usuario)
    if not procesos:
        raise Http404('La unidad no publica procesos')
    return unidad, procesos


# Desde cada página del aula, quien gestiona la planta salta al módulo donde eso se opera.
VISTA_DE_LA_CONSOLA = {
    'ficha': 'produccion', 'documentacion': 'produccion', 'producto': 'produccion',
    'produccion': 'produccion', 'corridas_lotes': 'produccion', 'balance': 'produccion',
    'linea': 'produccion', 'indice_metodos': 'produccion', 'indice_empaque': 'produccion',
    'indice_documentacion': 'produccion', 'materiales': 'planificacion', 'indice_materiales': 'planificacion',
    'protocolos': 'calidad', 'calidad': 'calidad', 'especificaciones': 'calidad',
    'equipo': 'mantenimiento', 'areas': 'recursos', 'servicios': 'recursos',
}


def _contexto(request, unidad, procesos, clave):
    referencia = sesion_de_referencia(request, unidad)
    modulo = modulo_del_aula(unidad.modulos_contenido.filter(activo=True).order_by('orden', 'id'))
    # Una simulación se guarda; una ficha de proceso, no: la ficha es la receta
    # de la planta y no hay nada que el estudiante pueda haber movido en ella.
    guardado = estado_guardado(request, unidad, clave) if clave in NOMBRES_SIMULADOR else {}
    return {
        **guardado,
        # La página es la vista previa de su propio documento: estos dos
        # enlaces la abren en PDF y la bajan, con los mismos filtros puestos.
        **enlaces_de_documento(request),
        'unidad': unidad,
        'procesos': procesos,
        'simulador': clave,
        'operar_url': (
            reverse('erp_planta' if VISTA_DE_LA_CONSOLA[clave] in SECCIONES_ERP else 'gestion_unidad',
                    args=[unidad.slug]) + f'?view={VISTA_DE_LA_CONSOLA[clave]}'
            if unidad.dependencia == 'plantas_piloto' and clave in VISTA_DE_LA_CONSOLA
            and puede_gestionar_unidad(request.user, unidad) else ''
        ),
        'simuladores': simuladores_de(unidad),
        'referencia': referencia,
        'volver_url': f'{unidad.get_absolute_url()}#{modulo}' if modulo else unidad.get_absolute_url(),
        'generado_en': timezone.localtime(),
        'foto_portada': foto_de_portada(unidad),
        # La página pública del aula lleva el diseño de los laboratorios; la consola de gestión, el documento.
        'aula_moderna': True,
        'constantes': {
            'cp': _texto(CALOR_ESPECIFICO, Decimal('0.01')),
            'densidad': _texto(DENSIDAD, Decimal('0.01')),
            'vapor': _texto(CALOR_LATENTE_VAPOR, Decimal('1')),
            'cop': _texto(COP_FRIO, Decimal('0.1')),
        },
    }


def _grupos_indice_procesos(procesos, modo):
    """Resume el núcleo técnico sin reproducir las fichas que ya son su fuente."""
    grupos = []
    for linea in lineas_de_procesos(procesos):
        fichas = []
        for receta in linea['procesos']:
            if modo == 'materiales':
                filas = [
                    {
                        'principal': insumo.consumible.nombre,
                        'detalle': f'{insumo.cantidad:g} {insumo.consumible.unidad_medida}',
                        'meta': insumo.get_forma_parte_display(),
                        'extra': insumo.etapa.nombre if insumo.etapa_id else 'Aplica a la corrida',
                    }
                    for insumo in receta.insumos.select_related('consumible', 'etapa')
                ]
            elif modo == 'empaque':
                producto = receta.producto
                conservacion = producto.conservacion
                filas = [{
                    'principal': producto.nombre,
                    'detalle': producto.presentacion or 'Presentación sin declarar',
                    'meta': 'Producto',
                    'extra': ' · '.join(filter(None, (
                        conservacion, f'vida útil {producto.vida_util_dias} días' if producto.vida_util_dias else '',
                    ))),
                }] + [
                    {
                        'principal': insumo.consumible.nombre,
                        'detalle': f'{insumo.cantidad:g} {insumo.consumible.unidad_medida} por corrida',
                        'meta': 'Material de empaque',
                        'extra': insumo.etapa.nombre if insumo.etapa_id else 'Aplica a la corrida',
                    }
                    for insumo in receta.insumos.select_related('consumible', 'etapa')
                    if insumo.consumible.clasificacion == 'empaque'
                ]
            elif modo == 'metodos':
                filas = [
                    {
                        'principal': f'{etapa.orden}. {etapa.nombre}',
                        'detalle': (
                            f'{etapa.duracion_min} min de trabajo · {etapa.espera_min} min de espera'
                        ),
                        'meta': etapa.get_tipo_display(),
                        'extra': ' · '.join(filter(None, (
                            etapa.equipo.nombre if etapa.equipo_id else '',
                            etapa.espacio.nombre if etapa.espacio_id else '',
                            f'{etapa.personas} persona(s)',
                        ))),
                    }
                    for etapa in receta.etapas.select_related('equipo', 'espacio')
                ]
            else:
                filas = [
                    {
                        'principal': 'Fundamentos y variables del proceso',
                        'detalle': 'Definiciones, ecuaciones, supuestos, unidades y ejemplos de aplicación.',
                        'meta': 'Ruta del saber',
                        'extra': 'La teoría se calcula con los mismos datos de la ficha técnica.',
                    },
                    {
                        'principal': 'Documento técnico del proceso',
                        'detalle': 'Operaciones unitarias, balance, capacidad, calidad y referencias.',
                        'meta': 'Documento vivo',
                        'extra': 'Se actualiza cuando cambia la receta o sus etapas.',
                    },
                ]
            fichas.append({
                'receta': receta,
                'filas': filas,
                'total': len(filas),
                'ficha_url': reverse('ficha_proceso_publica', args=[receta.unidad.slug, receta.pk]),
                'documentacion_url': reverse('documentacion_proceso', args=[receta.unidad.slug, receta.pk]),
            })
        grupos.append({'nombre': linea['nombre'], 'fichas': fichas})
    return grupos


def _indice_procesos_view(request, slug, modo):
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    if unidad.dependencia != 'plantas_piloto':
        raise Http404('Este índice pertenece a Plantas Piloto')
    configuracion = {
        'materiales': (
            'Materiales e insumos', '2.2',
            'Qué consume cada proceso, en qué cantidad de referencia y en qué etapa se incorpora.',
        ),
        'metodos': (
            'Métodos y tiempos', '2.3',
            'Cómo se ejecuta cada proceso: secuencia, trabajo, espera, personas, equipo y área.',
        ),
        'empaque': (
            'Empaque y presentación', '4.3',
            'Cómo sale cada producto: presentación, conservación, vida útil y los materiales de empaque de su proceso.',
        ),
        'documentacion': (
            'Ruta del saber y documentación', '2.5',
            'La teoría explica el porqué; la ficha técnica y los simuladores muestran cómo se aplica.',
        ),
    }[modo]
    clave = f'indice_{modo}'
    contexto = _contexto(request, unidad, procesos, clave)
    contexto.update({
        'modo_indice': modo,
        'titulo_indice': configuracion[0],
        'numero_indice': configuracion[1],
        'descripcion_indice': configuracion[2],
        'grupos_indice': _grupos_indice_procesos(procesos, modo),
    })
    return _pagina_o_documento(
        request, contexto, clave,
        'portal/pages/unidades/aula/indice_procesos.html',
        f'{configuracion[1].replace(".", "-")}-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def materiales_insumos_view(request, slug):
    return _indice_procesos_view(request, slug, 'materiales')


@xframe_options_sameorigin
def metodos_tiempos_view(request, slug):
    return _indice_procesos_view(request, slug, 'metodos')


@xframe_options_sameorigin
def empaque_presentacion_view(request, slug):
    return _indice_procesos_view(request, slug, 'empaque')


@xframe_options_sameorigin
def ruta_saber_documentacion_view(request, slug):
    return _indice_procesos_view(request, slug, 'documentacion')


@xframe_options_sameorigin
def ficha_proceso_publica_view(request, slug, receta_id):
    """La ficha del proceso en el visor de la unidad: la misma del panel, sin su barra de gestión."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    receta = next((item for item in procesos if item.pk == int(receta_id)), None)
    if receta is None:
        raise Http404('El proceso no está publicado')
    datos = datos_de_receta(receta)
    contexto = _contexto(request, unidad, procesos, 'ficha')
    editorial = metadatos_editoriales(receta, titulo=receta.nombre_publico, codigo=receta.codigo)
    contexto.update({
        'receta': receta,
        'proceso': datos,
        'resumen': resumen_proceso(datos),
        'balance': balance_de_masa(datos),
        'cronograma': cronograma(datos),
        'cursograma': cursograma_analitico(datos),
        **diagramas_de_ficha(datos, cursograma_analitico(datos)),
        'acciones_proceso': acciones_del_proceso(unidad, receta, 'ficha'),
        'fichas_relacionadas': fichas_relacionadas_del_proceso(unidad, receta),
        'cita': editorial['cita'],
        'publica': True,
        **contexto_adjuntos(receta, unidad, request.user),
    })
    return _pagina_o_documento(
        request, contexto, 'ficha',
        'portal/pages/unidades/gestion/ficha_proceso.html',
        f'ficha-{receta.codigo.lower()}.pdf',
    )


@xframe_options_sameorigin
def ficha_producto_publica_view(request, slug, producto_id):
    """Publica una ficha de producto, separada de la ficha técnica del proceso."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    if unidad.dependencia != 'plantas_piloto':
        raise Http404('La ficha de catálogo pertenece a Plantas Piloto')
    producto = get_object_or_404(
        Producto.objects.select_related('familia'),
        pk=producto_id,
        unidad=unidad,
        activo=True,
        publico=True,
        tipo__in=Producto.TIPOS_PUBLICOS,
    )
    if not _objeto_visible_para(producto, unidad, request.user):
        raise Http404('El producto no está publicado')
    receta = next((item for item in procesos if item.producto_id == producto.pk), None)
    contexto = _contexto(request, unidad, procesos, 'producto')
    editorial = metadatos_editoriales(producto)
    contexto.update({
        'producto': producto,
        'receta': receta,
        'catalogo_url': reverse('produccion_publica', args=[unidad.slug]),
        'acciones_producto': [
            {
                'nombre': 'Ficha del producto',
                'url': reverse('ficha_producto_publica', args=[unidad.slug, producto.pk]),
                'activa': True,
            },
            *([{
                'nombre': 'Abrir proceso técnico',
                'url': reverse('ficha_proceso_publica', args=[unidad.slug, receta.pk]),
                'activa': False,
            }] if receta is not None else []),
        ],
        'acciones_proceso': acciones_del_proceso(unidad, receta, 'producto') if receta else [],
        'fichas_relacionadas': fichas_relacionadas_del_proceso(unidad, receta) if receta else [],
        'datos_csv_url': reverse('datos_producto_csv', args=[unidad.slug, producto.pk]),
        'cita': editorial['cita'],
        **contexto_adjuntos(producto, unidad, request.user),
    })
    return _pagina_o_documento(
        request, contexto, 'producto',
        'portal/pages/unidades/aula/producto.html',
        f'ficha-producto-{producto.codigo.lower()}.pdf',
    )


def datos_proceso_csv_view(request, slug, receta_id):
    """Datos tabulares que generan ficha, diagramas y simuladores del proceso."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    receta = next((item for item in procesos if item.pk == int(receta_id)), None)
    if receta is None:
        raise Http404('El proceso no está publicado')
    datos = datos_de_receta(receta)
    filas = []
    for etapa in datos['etapas']:
        filas.append((
            receta.codigo, receta.nombre_publico, etapa['orden'], etapa['nombre'], etapa['tipo'],
            etapa.get('equipo') or '', etapa.get('espacio') or '', etapa.get('duracion_min') or 0,
            etapa.get('espera_min') or 0, etapa.get('personas') or 0,
            etapa.get('rendimiento_pct') or '', etapa.get('parametro') or '', etapa.get('limite') or '',
        ))
    return _respuesta_csv(
        f'datos-{receta.codigo.lower()}.csv',
        ('Código', 'Proceso', 'Orden', 'Etapa', 'Tipo', 'Equipo', 'Área', 'Trabajo min',
         'Espera min', 'Personas', 'Rendimiento %', 'Parámetro', 'Límite'),
        filas,
    )


def datos_producto_csv_view(request, slug, producto_id):
    """Datos estables del producto del catálogo institucional."""
    unidad = get_object_or_404(Unidad, slug=slug)
    producto = get_object_or_404(
        Producto.objects.select_related('familia'), pk=producto_id, unidad=unidad,
        activo=True, publico=True, tipo__in=Producto.TIPOS_PUBLICOS,
    )
    if not _objeto_visible_para(producto, unidad, request.user):
        raise Http404('El producto no está publicado')
    return _respuesta_csv(
        f'datos-{producto.codigo.lower()}.csv',
        ('Código', 'Producto', 'Familia', 'Tipo', 'Unidad de medida', 'Presentación',
         'Requiere frío', 'Vida útil días', 'Descripción'),
        [(
            producto.codigo, producto.nombre, producto.familia.nombre if producto.familia_id else '',
            producto.get_tipo_display(), producto.unidad_medida, producto.presentacion,
            'Sí' if producto.requiere_frio else 'No', producto.vida_util_dias, producto.descripcion,
        )],
    )


def _escenario_frente_a_receta(receta_datos, datos, ajustes):
    """«¿Qué pasa si?»: el proceso del escenario frente a la receta, y su diagrama de flujo."""
    if not ajustes:
        return [], None
    antes, despues = resumen_proceso(receta_datos), resumen_proceso(datos)
    balance_antes, balance_despues = balance_de_masa(receta_datos), balance_de_masa(datos)
    unidad = balance_despues['unidad_producto']
    comparacion = [
        ('Etapas', str(antes['etapas']), str(despues['etapas'])),
        ('Duración de la corrida', antes['duracion_texto'], despues['duracion_texto']),
        ('Trabajo', antes['trabajo_texto'], despues['trabajo_texto']),
        ('Puntos críticos de control', str(antes['puntos_criticos']), str(despues['puntos_criticos'])),
        ('Producto por balance', f"{balance_antes['producto_por_balance']} {unidad}",
         f"{balance_despues['producto_por_balance']} {unidad}"),
        ('Diferencia con lo esperado', f"{balance_antes['diferencia']} {unidad}", f"{balance_despues['diferencia']} {unidad}"),
    ]
    return comparacion, (diagrama_flujo(datos) if datos.get('etapas') else None)


@xframe_options_sameorigin
def simulador_balance_view(request, slug):
    """Balance de materia y energía de una corrida: libre o con los datos de la reserva."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    contexto = _contexto(request, unidad, procesos, 'balance')
    receta = _receta_elegida(request, procesos, contexto['referencia'])
    cantidad = _cantidad_elegida(request, receta, contexto['referencia'])
    factor = _factor(receta, cantidad)
    receta_datos = datos_de_receta(receta, factor)
    # El escenario del aula: los datos de la receta con lo que el estudiante
    # movio. Todo lo que sigue corre sobre el escenario, no sobre la receta.
    origen = f'{receta.pk}:{_texto(cantidad)}'
    ajustes = escenario_del_formulario(request.GET, receta_datos, origen)
    datos = aplicar_escenario(receta_datos, ajustes)
    flujo = entradas_y_salidas(datos)
    comparacion, diagrama_escenario = _escenario_frente_a_receta(receta_datos, datos, ajustes)
    calientes, frias = etapas_termicas(datos)
    t_proceso_defecto = next((fila['temperatura'] for fila in calientes if fila['temperatura'] is not None), Decimal('65'))
    parametros = {
        't_inicial': _decimal(request.GET.get('t_inicial'), 4),
        't_proceso': _decimal(request.GET.get('t_proceso'), t_proceso_defecto),
        't_final': _decimal(request.GET.get('t_final'), 4),
        'eficiencia': _decimal(request.GET.get('eficiencia'), 85),
        'potencia_kw': _decimal(request.GET.get('potencia_kw'), 0),
        'densidad': _decimal(request.GET.get('densidad'), DENSIDAD),
        'calor_especifico': _decimal(request.GET.get('calor_especifico'), CALOR_ESPECIFICO),
        'calor_latente_vapor': _decimal(request.GET.get('calor_latente_vapor'), CALOR_LATENTE_VAPOR),
        'cop_frio': _decimal(request.GET.get('cop_frio'), COP_FRIO),
    }
    editorial = metadatos_editoriales(receta, titulo=receta.nombre_publico, codigo=receta.codigo)
    contexto.update({
        'receta': receta,
        'cantidad': _texto(cantidad),
        'factor': _texto(factor),
        'proceso': datos,
        'balance': flujo['balance'],
        'general': balance_general(datos, flujo),
        'resumen': resumen_proceso(datos),
        'flujo': flujo_por_etapa(datos, flujo['balance']),
        'entradas': flujo['entradas'],
        'salidas': flujo['salidas'],
        'variables': valores_del_formulario(receta_datos, ajustes),
        'ajustes': ajustes,
        'origen': origen,
        'cambios': cambios_del_escenario(receta_datos, ajustes),
        'comparacion': comparacion,
        'diagrama_escenario': diagrama_escenario.svg() if diagrama_escenario else '',
        'diagrama_escenario_lienzo': diagrama_escenario,
        'energia': balance_de_energia(
            datos,
            t_inicial=parametros['t_inicial'],
            t_proceso=parametros['t_proceso'],
            t_final=parametros['t_final'],
            eficiencia=parametros['eficiencia'] / 100,
            potencia_kw=parametros['potencia_kw'],
            densidad=parametros['densidad'],
            calor_especifico=parametros['calor_especifico'],
            calor_latente_vapor=parametros['calor_latente_vapor'],
            cop_frio=parametros['cop_frio'],
        ),
        'parametros': {clave: _texto(valor, Decimal('0.1')) for clave, valor in parametros.items()},
        'calientes': calientes,
        'frias': frias,
        'acciones_proceso': acciones_del_proceso(unidad, receta, 'balance'),
        'fichas_relacionadas': fichas_relacionadas_del_proceso(unidad, receta),
        'cita': editorial['cita'],
        'reiniciar_url': f"{reverse('simulador_balance', args=[unidad.slug])}?receta={receta.pk}&cantidad={_texto(cantidad)}",
        'propiedades_referencia_lactea': receta.codigo.upper().startswith('LAC-'),
    })
    return _pagina_o_documento(
        request, contexto, 'balance',
        'portal/pages/unidades/aula/balance.html',
        f'balance-{receta.codigo.lower()}.pdf',
    )


@xframe_options_sameorigin
def simulador_linea_view(request, slug):
    """Balance de línea: las etapas del proceso frente al ritmo de la jornada."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    contexto = _contexto(request, unidad, procesos, 'linea')
    receta = _receta_elegida(request, procesos, contexto['referencia'])
    corridas = _decimal(request.GET.get('corridas'), 1)
    jornada = _decimal(request.GET.get('jornada'), 8)
    corridas = corridas if corridas > 0 else Decimal('1')
    jornada = jornada if jornada > 0 else Decimal('8')
    datos = datos_de_receta(receta)
    editorial = metadatos_editoriales(receta, titulo=receta.nombre_publico, codigo=receta.codigo)
    contexto.update({
        'receta': receta,
        'proceso': datos,
        'linea': balance_de_linea(datos, corridas=corridas, jornada_min=jornada * 60),
        'corridas': _texto(corridas),
        'jornada': _texto(jornada, Decimal('0.1')),
        'acciones_proceso': acciones_del_proceso(unidad, receta, 'linea'),
        'fichas_relacionadas': fichas_relacionadas_del_proceso(unidad, receta),
        'cita': editorial['cita'],
    })
    return _pagina_o_documento(
        request, contexto, 'linea',
        'portal/pages/unidades/aula/linea.html',
        f'balance-de-linea-{receta.codigo.lower()}.pdf',
    )


def _plan_de_materiales(request, procesos, referencia):
    """El plan: las sesiones de la referencia o la materia prima escrita por proceso."""
    if referencia:
        plan = [
            {
                'receta': sesion.receta,
                'factor': _num(sesion.factor_proceso or 1),
                'etiqueta': f'{sesion.codigo_reserva or sesion.pk} · {sesion.fecha:%d/%m/%Y}',
                'cantidad': _texto(_num(sesion.receta.cantidad_base) * _num(sesion.factor_proceso or 1)),
                'unidad': sesion.receta.unidad_base,
            }
            for sesion in referencia['sesiones']
            if sesion.receta_id
        ]
        if plan:
            return plan, True
    plan = []
    for receta in procesos:
        cantidad = _decimal(request.GET.get(f'cantidad_{receta.pk}'), 0)
        if cantidad > 0:
            plan.append({
                'receta': receta,
                'factor': _factor(receta, cantidad),
                'etiqueta': receta.nombre,
                'cantidad': _texto(cantidad),
                'unidad': receta.unidad_base,
            })
    return plan, False


@xframe_options_sameorigin
def simulador_materiales_view(request, slug):
    """Requerimiento de materiales de un plan de corridas frente al inventario de la unidad."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    contexto = _contexto(request, unidad, procesos, 'materiales')
    plan, desde_referencia = _plan_de_materiales(request, procesos, contexto['referencia'])
    cantidades = {} if desde_referencia else {fila['receta'].pk: fila['cantidad'] for fila in plan}
    contexto.update({
        'plan': plan,
        'desde_referencia': desde_referencia,
        'requerimiento': requerimiento_de_materiales(plan) if plan else None,
        'filas_formulario': [
            {'receta': receta, 'cantidad': cantidades.get(receta.pk, '')} for receta in procesos
        ],
    })
    return _pagina_o_documento(
        request, contexto, 'materiales',
        'portal/pages/unidades/aula/materiales.html',
        f'requerimiento-de-materiales-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def protocolos_control_view(request, slug):
    """Los puntos críticos de control de todos los procesos de la unidad."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    familia_codigo = (request.GET.get('familia') or '').strip().upper()
    familia = None
    if familia_codigo:
        familia = get_object_or_404(FamiliaProducto, unidad=unidad, codigo=familia_codigo, activa=True)
        procesos = [proceso for proceso in procesos if proceso.familia_id == familia.pk]
    contexto = _contexto(request, unidad, procesos, 'protocolos')
    contexto['familia_activa'] = familia
    contexto['protocolos'] = protocolos_de_control(procesos)
    contexto['total_puntos'] = sum(len(item['puntos']) for item in contexto['protocolos'])
    return _pagina_o_documento(
        request, contexto, 'protocolos',
        'portal/pages/unidades/aula/protocolos.html',
        f'protocolos-de-control-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def produccion_publica_view(request, slug):
    """Catálogo público de productos, separado del movimiento diario de la planta."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    contexto = _contexto(request, unidad, procesos, 'produccion')
    contexto['produccion'] = produccion_publica(unidad, procesos, request.user)
    contexto['hoy'] = timezone.localdate()
    return _pagina_o_documento(
        request, contexto, 'produccion',
        'portal/pages/unidades/aula/produccion.html',
        f'produccion-y-lotes-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def corridas_lotes_publicos_view(request, slug):
    """Agregado público; el detalle vive en el panel interno de la unidad."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    contexto = _contexto(request, unidad, procesos, 'corridas_lotes')
    contexto['actividad'] = corridas_lotes_publicos(unidad)
    contexto['hoy'] = timezone.localdate()
    return _pagina_o_documento(
        request, contexto, 'corridas_lotes',
        'portal/pages/unidades/aula/corridas_lotes.html',
        f'actividad-de-produccion-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def calidad_publica_view(request, slug):
    """Calidad e inocuidad: control de los lotes, requisitos de ingreso y normas de seguridad."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    familia_codigo = (request.GET.get('familia') or '').strip().upper()
    solo_transversales = request.GET.get('transversales') == '1'
    familia = None
    if familia_codigo:
        familia = get_object_or_404(FamiliaProducto, unidad=unidad, codigo=familia_codigo, activa=True)
        procesos = [proceso for proceso in procesos if proceso.familia_id == familia.pk]
    procesos_visibles = [] if solo_transversales else procesos
    contexto = _contexto(request, unidad, procesos_visibles, 'calidad')
    contexto['calidad'] = calidad_publica(
        unidad, procesos_visibles, familia=familia,
        solo_transversales=solo_transversales,
    )
    contexto['familia_activa'] = familia
    contexto['solo_transversales'] = solo_transversales
    consulta = f'?familia={familia.codigo}' if familia else ''
    contexto['protocolos_url'] = reverse('protocolos_control', args=[unidad.slug]) + consulta
    contexto['haccp_url'] = reverse('plan_haccp', args=[unidad.slug]) + consulta
    return _pagina_o_documento(
        request, contexto, 'calidad',
        'portal/pages/unidades/aula/calidad.html',
        f'calidad-e-inocuidad-{unidad.slug}.pdf',
    )


def especificaciones_view(request, slug):
    """5.2: la especificación de liberación de cada producto, por familia."""
    unidad, procesos = _unidad_con_procesos(slug, request.user)
    familia_codigo = (request.GET.get('familia') or '').strip().upper()
    familia = (
        get_object_or_404(FamiliaProducto, unidad=unidad, codigo=familia_codigo, activa=True)
        if familia_codigo else None
    )
    especificaciones = [
        {'plan': plan, 'parametros': plan.parametros_ordenados()}
        for plan in planes_de(unidad, momento='liberacion')
        if familia is None or plan.familia_id == familia.pk
    ]
    contexto = _contexto(request, unidad, procesos, 'especificaciones')
    contexto.update({
        'especificaciones': especificaciones,
        'parametros_totales': sum(len(item['parametros']) for item in especificaciones),
        'familia_activa': familia,
    })
    return _pagina_o_documento(
        request, contexto, 'especificaciones',
        'portal/pages/unidades/aula/especificaciones.html',
        f'especificaciones-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def areas_equipos_view(request, slug):
    """Las áreas de la unidad con los equipos que alojan y sus auxiliares."""
    unidad = get_object_or_404(Unidad, slug=slug)
    contexto = _contexto(request, unidad, procesos_publicos(unidad), 'areas')
    contexto['infraestructura'] = areas_y_equipos(unidad, request.user)
    return _pagina_o_documento(
        request, contexto, 'areas',
        'portal/pages/unidades/detalle/areas_unidad.html',
        f'areas-y-equipos-{unidad.slug}.pdf',
    )


def servicios_industriales_view(request, slug):
    """Lo que consumen los equipos de la planta y lo que descargan sus procesos."""
    unidad = get_object_or_404(Unidad, slug=slug, dependencia='plantas_piloto')
    contexto = _contexto(request, unidad, procesos_publicos(unidad), 'servicios')
    contexto['servicios_planta'] = servicios_industriales(unidad)
    return _pagina_o_documento(
        request, contexto, 'servicios',
        'portal/pages/unidades/aula/servicios_industriales.html',
        f'servicios-industriales-{unidad.slug}.pdf',
    )


@xframe_options_sameorigin
def ficha_equipo_publica_view(request, slug, codigo):
    """Ficha de un equipo; los códigos históricos redirigen de forma permanente."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct()
    unidad_equipo = equipos.filter(codigo_unidad=codigo).select_related('equipo', 'laboratorio').first()
    if unidad_equipo is None:
        alias = (
            AliasCodigoUnidadEquipo.objects.filter(codigo=codigo, unidad_equipo__in=equipos)
            .select_related('unidad_equipo').first()
        )
        if alias is None:
            raise Http404('El equipo no existe en esta unidad')
        return redirect('ficha_equipo_publica', slug=slug, codigo=alias.unidad_equipo.codigo_unidad, permanent=True)
    if not _objeto_visible_para(unidad_equipo, unidad, request.user):
        raise Http404('El equipo no está publicado')
    gestor = ve_datos_patrimoniales(request.user, unidad_equipo)
    # Un equipo retirado solo lo consulta quien gestiona la unidad (sigue su historia).
    if not unidad_equipo.activa and not gestor:
        raise Http404('El equipo fue retirado del inventario')
    if not unidad_equipo.es_publico and not gestor:
        raise Http404('El equipo no está en servicio')
    procesos = procesos_publicos(unidad, request.user)
    contexto = _contexto(request, unidad, procesos, 'equipo')
    editorial = metadatos_editoriales(
        unidad_equipo, titulo=unidad_equipo.equipo.nombre, codigo=unidad_equipo.codigo_unidad,
    )
    contexto.update({
        'unidad_equipo': unidad_equipo,
        'detalle': detalle_de_equipo(unidad, unidad_equipo, gestor=gestor),
        # El custodio, el valor y la historia completa solo los ve quien opera los recursos o el mantenimiento.
        'gestor': gestor,
        'historia': linea_de_trazabilidad(unidad_equipo, limite=40) if gestor else [],
        'puede_verificar': puede_verificar(request.user, unidad),
        # Editar la ficha desde la ficha: lo que se ve aquí se corrige aquí, sin pasar por el administrador.
        'editar_ficha_url': (reverse('editar_equipo_ficha', args=[unidad.slug, unidad_equipo.codigo_unidad])
                             if unidad_equipo.laboratorio_id == unidad.pk and puede_operar_modulo_unidad(request.user, unidad, 'recursos') else ''),
        # Solicitar el traslado a otra unidad: abre el traspaso con la unidad, el equipo y la alerta ya puestos.
        'traslado_url': reverse('admin:recursos_traspasoequipo_add') if request.user.has_perm('recursos.add_traspasoequipo') else '',
        'editar_url': pantalla_de_edicion(request.user, unidad, 'unidadequipo', pk=unidad_equipo.pk),
        # Un equipo inactivo no tiene levantamiento ni etiqueta: no se ofrecen descargas que responderían 404.
        'datos_csv_url': (reverse('datos_equipo_csv', args=[unidad.slug, unidad_equipo.codigo_unidad])
                          if unidad_equipo.activa else ''),
        'cita': editorial['cita'],
        'fichas_relacionadas': [
            {
                'tipo': 'Proceso', 'nombre': receta.nombre_publico,
                'icono': 'fas fa-project-diagram',
                'url': reverse('ficha_proceso_publica', args=[unidad.slug, receta.pk]),
            }
            for receta in procesos
            if receta.etapas.filter(equipo_id=unidad_equipo.equipo_id).exists()
        ],
        **contexto_adjuntos(unidad_equipo, unidad, request.user),
    })
    return _pagina_o_documento(
        request, contexto, 'equipo',
        'portal/pages/unidades/aula/equipo.html',
        f'ficha-equipo-{unidad_equipo.codigo_unidad.lower()}.pdf',
    )


def datos_equipo_csv_view(request, slug, codigo):
    """Ficha de levantamiento del equipo sin rellenar ausencias con estimaciones."""
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    unidad_equipo = get_object_or_404(
        UnidadEquipo.objects.select_related('equipo').filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad),
        ).distinct(),
        codigo_unidad=codigo,
        activa=True,
    )
    if not _objeto_visible_para(unidad_equipo, unidad, request.user):
        raise Http404('El equipo no está publicado')
    equipo = unidad_equipo.equipo
    campos = (
        ('Código', unidad_equipo.codigo_unidad), ('Equipo', equipo.nombre),
        ('Marca', equipo.marca or ''), ('Modelo', equipo.modelo or ''),
        ('Modo de operación', equipo.get_modo_operacion_display() if equipo.modo_operacion else ''),
        ('Capacidad nominal', equipo.capacidad_nominal or ''), ('Unidad', equipo.unidad_capacidad),
        ('Carga útil mínima', equipo.capacidad_util_min or ''), ('Carga útil máxima', equipo.capacidad_util_max or ''),
        ('Setup min', equipo.tiempo_setup or ''), ('Limpieza min', equipo.tiempo_limpieza or ''),
        ('Potencia kW', equipo.potencia_kw or ''), ('Vapor kg/h', equipo.consumo_vapor or ''),
        ('Agua L/ciclo', equipo.consumo_agua or ''), ('Aire m³/h', equipo.consumo_aire or ''),
        ('Coordenada X', equipo.coordenada_x or ''), ('Coordenada Y', equipo.coordenada_y or ''),
        ('MTBF h', equipo.mtbf or ''), ('MTTR h', equipo.mttr or ''), ('Criticidad', equipo.criticidad),
    )
    return _respuesta_csv(
        f'datos-{unidad_equipo.codigo_unidad.lower()}.csv', ('Campo', 'Valor'), campos,
    )
