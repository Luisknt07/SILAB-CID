"""Tablero interno de cobertura para las 33 secciones de Plantas Piloto.

Las metas proceden del mapa de contenidos entregado por la UPEC. Los conteos
se calculan desde objetos publicados o técnicamente utilizables; una fila de
ejemplo de los libros de cálculo nunca se convierte en contenido publicado.
"""

from collections import Counter

from apps.plantas_piloto.domain.completitud import (
    estado_cobertura,
    estado_ficha,
    porcentaje_cobertura,
)

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.reservas.models.reservas import GuiaActividadReserva
from apps.plantas_piloto.operacion.models.calidad import PlanCalidad
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad, unidades_gestionables
from apps.plantas_piloto.operacion.presentation.secciones_plantas import PESTANAS_PLANTA, SECCIONES_PLANTA
from apps.plantas_piloto.operacion.presentation.servicios_industriales import servicios_industriales


METAS_BASE = {
    '1.1': 1, '1.2': 1, '1.3': 3, '1.4': 3, '1.5': 3, '1.6': 2,
    '2.1': 8, '2.2': 5, '2.3': 3, '2.4': 8, '2.5': 6, '2.6': 8,
    '3.1': 7, '3.2': 17, '3.3': 6, '3.4': 3,
    '4.1': 11, '4.2': 11, '4.3': 3, '4.4': 8, '4.5': 2, '4.6': 3,
    '5.1': 8, '5.2': 11, '5.3': 6, '5.4': 4, '5.5': 4,
    '6.1': 2, '6.2': 5, '6.3': 1, '6.4': 1, '6.5': 3, '6.6': 1, '6.7': 1,
}

METAS_POR_PLANTA = {
    'CAR': {'2.1': 9, '2.4': 9, '2.6': 9, '3.1': 6, '3.2': 20, '4.1': 14, '4.2': 14, '4.4': 9, '5.1': 9, '5.2': 14},
    'HOR': {'2.1': 10, '2.4': 10, '2.6': 10, '3.1': 5, '3.2': 18, '4.1': 16, '4.2': 16, '4.4': 10, '5.1': 10, '5.2': 16},
    'ALM': {'2.1': 9, '2.4': 9, '2.6': 9, '3.1': 6, '3.2': 16, '4.1': 12, '4.2': 12, '4.4': 9, '5.1': 9, '5.2': 12, '5.3': 7},
    'PAN': {'3.1': 5, '3.2': 15, '4.1': 13, '4.2': 13, '5.2': 13},
}

RESPONSABLES = {
    '1': 'Responsable de unidad y Comunicación',
    '2': 'Ingeniería de producto, docentes y Calidad',
    '3': 'Mantenimiento e Ingeniería de planta',
    '4': 'Responsable, Calidad y Planificación',
    '5': 'Calidad',
    '6': 'Coordinación académica y docentes',
}

ETIQUETAS_ESTADO = {
    'aprobado': 'Aprobado',
    'parcial': 'Parcial',
    'pendiente': 'Pendiente',
    'bloqueado': 'Bloqueado',
}

SECCIONES_POR_TIPO = {
    'producto': {'4.1', '4.2', '4.3'},
    'proceso': {'2.1', '2.2', '2.3', '2.4', '2.5', '4.4'},
    'equipo': {'3.2', '3.4'},
    'pcc': {'5.1', '5.3'},
    'especificacion': {'5.2', '5.4'},
    'guia': {'2.6', '6.5'},
}


def codigo_planta(unidad):
    codigo = unidad.familias_producto.order_by('orden').values_list('codigo', flat=True).first()
    if codigo:
        return codigo.split('-', 1)[0].upper()
    nombre = unidad.nombre.lower()
    return next((c for texto, c in (
        ('lácte', 'LAC'), ('lacte', 'LAC'), ('cárnic', 'CAR'), ('carnic', 'CAR'),
        ('horto', 'HOR'), ('almid', 'ALM'), ('panific', 'PAN'),
    ) if texto in nombre), 'LAC')


def metas_de(unidad):
    metas = METAS_BASE.copy()
    metas.update(METAS_POR_PLANTA.get(codigo_planta(unidad), {}))
    return metas


def _publicados(unidad):
    """Objetos publicados por sección, con validaciones mínimas para calcular."""
    fichas = FichaContenido.objects.filter(
        unidad=unidad, estado='publicada', visibilidad__in=('publica', 'restringida'),
    )
    por_tipo = Counter(fichas.values_list('tipo', flat=True))
    recetas = list(Receta.objects.filter(unidad=unidad, activa=True).prefetch_related('etapas', 'insumos'))
    productos = list(Producto.objects.filter(
        unidad=unidad, activo=True, publico=True, tipo__in=Producto.TIPOS_PUBLICOS,
    ))
    equipos = list(
        UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True)
        .select_related('equipo').distinct()
    )
    guias = GuiaActividadReserva.objects.filter(
        actividad__unidad=unidad, activo=True, estado_publicacion='publicada', visibilidad='publica',
    ).count()
    planes = PlanCalidad.objects.filter(unidad=unidad, activo=True).count()

    procesos_con_insumos = sum(bool(list(receta.insumos.all())) for receta in recetas)
    procesos_con_tiempos = sum(
        bool(list(receta.etapas.all())) and all(
            etapa.duracion_min or etapa.espera_min for etapa in receta.etapas.all()
        ) for receta in recetas
    )
    procesos_calculables = sum(
        bool(list(receta.etapas.all())) and bool(list(receta.insumos.all()))
        for receta in recetas
    )
    capacidad_calculable = 0
    for receta in recetas:
        usados = [etapa.equipo for etapa in receta.etapas.all() if etapa.equipo_id]
        if usados and all(
            equipo.capacidad_util_max is not None
            and equipo.modo_operacion
            and equipo.tiempo_setup is not None
            and equipo.tiempo_limpieza is not None
            for equipo in usados
        ):
            capacidad_calculable += 1
    servicios = set()
    for unidad_equipo in equipos:
        equipo = unidad_equipo.equipo
        for campo in ('potencia_kw', 'consumo_vapor', 'consumo_agua', 'consumo_aire'):
            if getattr(equipo, campo) is not None:
                servicios.add(campo)
    return {
        '1.1': int(bool(unidad.descripcion)),
        '1.2': int(unidad.responsables_unidad.filter(activo=True).exists()),
        '1.3': sum(
            equipo.equipo.coordenada_x is not None and equipo.equipo.coordenada_y is not None
            for equipo in equipos
        ),
        '1.4': por_tipo['documento'], '1.5': por_tipo['documento'],
        '1.6': unidad.novedades.filter(publicada=True).count(),
        '2.1': por_tipo['proceso'], '2.2': procesos_con_insumos,
        '2.3': procesos_con_tiempos, '2.4': procesos_calculables,
        '2.5': procesos_calculables, '2.6': guias,
        '3.1': EspacioReservable.objects.filter(unidad=unidad, activo=True).count(),
        '3.2': por_tipo['equipo'], '3.3': servicios_industriales(unidad)['con_datos'], '3.4': capacidad_calculable,
        '4.1': len(productos),
        '4.2': sum(bool(p.descripcion and p.unidad_medida and p.presentacion) for p in productos),
        '4.3': sum(bool(p.presentacion) for p in productos),
        '4.4': procesos_con_insumos, '4.5': por_tipo['documento'], '4.6': 0,
        '5.1': por_tipo['pcc'], '5.2': max(por_tipo['especificacion'], planes),
        '5.3': 0, '5.4': planes, '5.5': 0,
        '6.1': 2, '6.2': por_tipo['documento'], '6.3': 1,
        '6.4': 1, '6.5': guias, '6.6': int(hasattr(unidad, 'reglamento_publico')),
        '6.7': 1,
    }


def _bloqueos(unidad):
    bloqueos = Counter()
    equipos = UnidadEquipo.objects.filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True,
    ).select_related('equipo').distinct()
    for unidad_equipo in equipos:
        for campo in unidad_equipo.equipo.campos_criticos_vacios:
            bloqueos[(campo['nombre'], campo['bloquea'], ('3.2', '3.4'))] += 1
    for receta in Receta.objects.filter(unidad=unidad, activa=True).prefetch_related('etapas', 'insumos'):
        etapas = list(receta.etapas.all())
        if not etapas or any(not (etapa.duracion_min or etapa.espera_min) for etapa in etapas):
            bloqueos[('Tiempos de etapa', 'métodos, capacidad y simulación', ('2.3', '2.4', '2.5', '3.4'))] += 1
        if not list(receta.insumos.all()):
            bloqueos[('Corrientes e insumos', 'balance, materiales y documentación', ('2.2', '2.4', '2.5', '4.4'))] += 1
        if any((etapa.punto_critico or etapa.punto_control) and not (etapa.parametro and etapa.limite)
               for etapa in etapas):
            bloqueos[('Parámetro y límite del PCC o PC', 'protocolos y HACCP', ('5.1', '5.3'))] += 1
    return [
        {'campo': campo, 'bloquea': bloquea, 'secciones': secciones, 'fichas': cantidad}
        for (campo, bloquea, secciones), cantidad in bloqueos.most_common()
    ]


def _vacios_ficha(ficha):
    """Devuelve ausencias técnicas comprobables sin inventar datos institucionales."""
    objeto = ficha.objeto
    if objeto is None:
        return [{'nombre': 'Objeto de origen', 'bloquea': 'trazabilidad de la ficha'}]
    if ficha.tipo == 'equipo' and hasattr(objeto, 'equipo'):
        return objeto.equipo.campos_criticos_vacios
    vacios = []
    if ficha.tipo == 'producto':
        for campo, nombre in (
            ('descripcion', 'Descripción'), ('unidad_medida', 'Unidad de medida'),
            ('presentacion', 'Presentación'),
        ):
            if not getattr(objeto, campo, None):
                vacios.append({'nombre': nombre, 'bloquea': 'ficha técnica del producto'})
    elif ficha.tipo == 'proceso':
        etapas = list(objeto.etapas.all())
        if not etapas:
            vacios.append({'nombre': 'Etapas', 'bloquea': 'método y simulación'})
        elif any(not (etapa.duracion_min or etapa.espera_min) for etapa in etapas):
            vacios.append({'nombre': 'Tiempos de etapa', 'bloquea': 'método y capacidad'})
        if not objeto.insumos.exists():
            vacios.append({'nombre': 'Corrientes e insumos', 'bloquea': 'balance de materiales'})
    elif ficha.tipo == 'pcc':
        if not getattr(objeto, 'parametro', ''):
            vacios.append({'nombre': 'Parámetro del PCC', 'bloquea': 'validación de calidad'})
        if not getattr(objeto, 'limite', ''):
            vacios.append({'nombre': 'Límite del PCC', 'bloquea': 'validación de calidad'})
    elif ficha.tipo == 'especificacion' and not objeto.parametros.filter(activo=True).exists():
        vacios.append({'nombre': 'Parámetros de calidad', 'bloquea': 'especificación'})
    return vacios


def _validacion_por_seccion(fichas):
    resumen = {numero: Counter() for numero in SECCIONES_PLANTA}
    for ficha in fichas:
        for numero in SECCIONES_POR_TIPO.get(ficha.tipo, ()):
            resumen[numero]['total'] += 1
            resumen[numero][ficha.estado_validacion] += 1
    return resumen


def tablero_unidad(unidad):
    metas, publicados = metas_de(unidad), _publicados(unidad)
    fichas = list(
        FichaContenido.objects.filter(unidad=unidad)
        .select_related('content_type', 'familia', 'validado_por', 'decision_editorial_por')
        .order_by('tipo', 'codigo')
    )
    bloqueos = _bloqueos(unidad)
    secciones_bloqueadas = {
        numero for bloqueo in bloqueos for numero in bloqueo['secciones']
    }
    validacion_secciones = _validacion_por_seccion(fichas)
    secciones = []
    for numero, definicion in SECCIONES_PLANTA.items():
        esperado = metas[numero]
        publicado = min(publicados.get(numero, 0), esperado)
        porcentaje = porcentaje_cobertura(publicado, esperado)
        validacion = validacion_secciones[numero]
        bloqueado = numero in secciones_bloqueadas or bool(validacion['bloqueada'])
        estado = estado_cobertura(publicado, esperado, bloqueado=bloqueado)
        if estado == 'aprobado' and validacion['total'] > validacion['validada']:
            estado = 'parcial'
        secciones.append({
            'numero': numero, 'titulo': definicion['titulo'], 'modulo': definicion['modulo'],
            'esperado': esperado, 'publicado': publicado, 'porcentaje': porcentaje,
            'estado': estado, 'estado_etiqueta': ETIQUETAS_ESTADO[estado],
            'validacion': validacion,
        })
    pestanas = []
    for modulo, (titulo, definiciones) in PESTANAS_PLANTA.items():
        numeros = {numero for numero, _nombre in definiciones}
        filas = [fila for fila in secciones if fila['numero'] in numeros]
        esperado = sum(fila['esperado'] for fila in filas)
        publicado = sum(fila['publicado'] for fila in filas)
        pestanas.append({
            'modulo': modulo, 'titulo': titulo, 'secciones': filas,
            'esperado': esperado, 'publicado': publicado,
            'porcentaje': porcentaje_cobertura(publicado, esperado),
            'responsable': RESPONSABLES[filas[0]['numero'].split('.')[0]],
            'estados': Counter(fila['estado'] for fila in filas),
        })
    esperado = sum(item['esperado'] for item in pestanas)
    publicado = sum(item['publicado'] for item in pestanas)
    detalle_fichas = []
    for ficha in fichas:
        vacios = _vacios_ficha(ficha)
        estado = estado_ficha(
            ficha.completitud,
            ficha.estado,
            ficha.estado_validacion,
            bloqueado=bool(vacios),
        )
        detalle_fichas.append({
            'ficha': ficha,
            'vacios': vacios,
            'estado': estado,
            'estado_etiqueta': ETIQUETAS_ESTADO[estado],
        })

    detalle_por_id = {item['ficha'].pk: item for item in detalle_fichas}
    familias = []
    for familia in unidad.familias_producto.filter(activa=True).order_by('orden', 'nombre'):
        items = [detalle_por_id[ficha.pk] for ficha in fichas if ficha.familia_id == familia.pk]
        estados = Counter(item['estado'] for item in items)
        aprobado = estados['aprobado']
        estado = estado_cobertura(aprobado, len(items)) if items else 'pendiente'
        if estados['bloqueado']:
            estado = 'bloqueado'
        elif items and aprobado < len(items):
            estado = 'parcial' if aprobado or estados['parcial'] else 'pendiente'
        familias.append({
            'familia': familia,
            'total': len(items),
            'aprobado': aprobado,
            'porcentaje': porcentaje_cobertura(aprobado, len(items)) if items else 0,
            'estado': estado,
            'estado_etiqueta': ETIQUETAS_ESTADO[estado],
            'estados': estados,
        })
    return {
        'unidad': unidad, 'codigo': codigo_planta(unidad), 'pestanas': pestanas,
        'esperado': esperado, 'publicado': publicado,
        'porcentaje': porcentaje_cobertura(publicado, esperado),
        'bloqueos': bloqueos, 'fichas': detalle_fichas, 'familias': familias,
        'estados_fichas': Counter(item['estado'] for item in detalle_fichas),
    }


@login_required
def completitud_plantas_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug, dependencia='plantas_piloto')
    if not puede_gestionar_unidad(request.user, unidad):
        raise PermissionDenied('No tienes autorización para consultar la completitud de esta unidad.')
    alcance = unidades_gestionables(request.user).filter(dependencia='plantas_piloto').order_by('nombre')
    plantas = [tablero_unidad(item) for item in alcance]
    esperado = sum(item['esperado'] for item in plantas)
    publicado = sum(item['publicado'] for item in plantas)
    return render(request, 'portal/pages/unidades/gestion/completitud.html', {
        'unidad': unidad,
        'tablero': next(item for item in plantas if item['unidad'].pk == unidad.pk),
        'plantas': plantas,
        'plataforma': {
            'esperado': esperado, 'publicado': publicado,
            'porcentaje': porcentaje_cobertura(publicado, esperado),
        },
    })
