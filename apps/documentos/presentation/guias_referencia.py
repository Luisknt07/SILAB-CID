"""Guías de práctica de referencia (2.6), una por proceso de referencia de la planta.

Cada guía sigue el formato institucional FT04 y se arma desde el proceso: los
objetivos, el fundamento de sus operaciones unitarias, los equipos y materiales,
el procedimiento etapa por etapa con sus controles, la seguridad, los resultados
del balance y el manejo de residuos. Es una guía de referencia: el docente la
adapta a su asignatura y una nueva carga no pisa lo que haya editado.
"""
from decimal import Decimal

from django.db import transaction

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva
from apps.plantas_piloto.operacion.models.calidad import PlanCalidad
from apps.plantas_piloto.operacion.models.produccion import Receta

from apps.documentos.presentation.documentacion import clasificar_etapa
from apps.plantas_piloto.operacion.presentation.procesos import _minutos, _nombre_tipo, _texto_cantidad, balance_de_masa, datos_de_receta, resumen_proceso, unidad_en_plural

EPP = 'Cofia, mascarilla, mandil limpio, botas de caucho y manos lavadas y desinfectadas antes de entrar.'


def _paso(etapa):
    donde = ' · '.join(filter(None, [etapa.get('equipo'), etapa.get('espacio')]))
    tiempo = _minutos(int(etapa['duracion_min']) + int(etapa['espera_min']))
    partes = [f"{etapa['nombre']} ({_nombre_tipo(etapa['tipo'])}{', ' + donde if donde else ''}, {tiempo})."]
    if etapa.get('instrucciones'):
        partes.append(etapa['instrucciones'])
    entra = ', '.join(f"{i['nombre']} {_texto_cantidad(i['cantidad'])} {unidad_en_plural(i['unidad'], i['cantidad'])}" for i in etapa.get('insumos', []))
    if entra:
        partes.append(f'Entra: {entra}.')
    if etapa.get('punto_critico'):
        partes.append(f"PCC (inocuidad): {etapa.get('parametro')}, {etapa.get('limite')}.")
    elif etapa.get('punto_control'):
        partes.append(f"PC (calidad): {etapa.get('parametro')}, {etapa.get('limite')}.")
    return ' '.join(partes)


def contenido_de_referencia(receta):
    """El contenido FT04 de la guía, desde los datos del proceso."""
    datos = datos_de_receta(receta, Decimal('1'))
    etapas = datos['etapas']
    producto = receta.producto.nombre.lower()
    resumen = resumen_proceso(datos)
    balance = balance_de_masa(datos)
    equipos, materiales = [], []
    for etapa in etapas:
        if etapa.get('equipo') and etapa['equipo'] not in equipos:
            equipos.append(etapa['equipo'])
        for insumo in etapa.get('insumos', []):
            materiales.append(
                f"{insumo['nombre']}: {_texto_cantidad(insumo['cantidad'])} {unidad_en_plural(insumo['unidad'], insumo['cantidad'])} (etapa {etapa['orden']})"
            )
    operaciones = []
    for etapa in etapas:
        operacion = clasificar_etapa(etapa)
        if operacion['clave'] in ('operacion', 'transporte', 'espera', 'limpieza'):
            continue
        texto = f"{operacion['nombre']}: {operacion['fenomeno']}"
        if texto not in operaciones:
            operaciones.append(texto)
    controles = [
        f"{etapa['nombre']}: {etapa.get('parametro')} ({etapa.get('limite')}), "
        + ('PCC de inocuidad.' if etapa.get('punto_critico') else 'PC de calidad.')
        for etapa in etapas if etapa.get('punto_critico') or etapa.get('punto_control')
    ]
    residuos = [
        f"{salida['nombre']}: {_texto_cantidad(salida['cantidad'])} {unidad_en_plural(salida['unidad'], salida['cantidad'])} por corrida base"
        + (', sale del flujo hacia tratamiento.' if salida.get('externa_al_flujo') else '.')
        for etapa in etapas for salida in etapa.get('salidas', [])
    ]
    especificacion = PlanCalidad.objects.filter(
        producto=receta.producto, momento='liberacion', activo=True,
    ).first()
    return {
        'asignatura': f'Tecnología de {receta.familia.nombre.lower()}' if receta.familia_id else 'Tecnología de alimentos',
        'carrera_semestre': 'Agroindustria · según la planificación del docente',
        'docente_responsable': 'Docente de la asignatura',
        'laboratorio': receta.unidad.nombre,
        'duracion': f"{resumen['duracion_texto']} ({resumen['trabajo_texto']} de trabajo)",
        'maximo_estudiantes': '12',
        'categoria_uso': 'Docencia',
        'resultado_aprendizaje': (
            f'Conduce el proceso de {producto} en la planta con buenas prácticas de manufactura, '
            'control de sus puntos críticos y registro trazable de lo que entra y lo que sale.'
        ),
        'objetivos': [
            f'Elaborar {producto} siguiendo el proceso «{receta.nombre}» a escala de una corrida base.',
            'Operar cada equipo dentro de sus parámetros y registrar los PCC y PC del proceso.',
            'Calcular el balance de masa de la corrida y comparar el rendimiento obtenido con el esperado.',
        ],
        'fundamento_teorico': operaciones,
        'equipos': equipos,
        'software': list(datos.get('software', [])),
        'materiales': materiales,
        'reactivos': [],
        'medidas_seguridad': [EPP, 'Inducción de la planta y requisitos de acceso vigentes.', *controles],
        'formato_procedimiento': 'numerado',
        'procedimiento': [_paso(etapa) for etapa in etapas],
        'resultados_esperados': [
            f"Con {balance['entrada']} {balance['unidad_base']} se esperan {balance['producto_esperado']} "
            f"{balance['unidad_producto']} de {producto}; el balance por etapas da {balance['producto_por_balance']}.",
            'Registro de los controles de cada PCC y PC con su valor medido.',
        ] + ([f'El lote cumple la especificación «{especificacion.nombre}».'] if especificacion else []),
        'criterios_evaluacion': [
            'Preparación y buenas prácticas: 20 %.',
            'Operación de los equipos y control de PCC y PC: 35 %.',
            'Balance de masa y rendimiento: 25 %.',
            'Informe con los registros de la corrida: 20 %.',
        ],
        'manejo_residuos': residuos or ['Los residuos del proceso se separan y se entregan al gestor autorizado.'],
        'bibliografia': [
            'Codex Alimentarius CXC 1-1969: Principios generales de higiene de los alimentos.',
            f'Ficha técnica del proceso {receta.codigo} de la {receta.unidad.nombre}.',
        ],
    }


@transaction.atomic
def crear_guias_de_referencia(unidad):
    """Una actividad y una guía publicadas por proceso de referencia; devuelve las creadas."""
    creadas = []
    for receta in (
        Receta.objects.filter(unidad=unidad, activa=True, origen='referencia')
        .select_related('producto', 'familia', 'unidad').order_by('codigo')
    ):
        actividad, _ = CatalogoActividadReserva.objects.get_or_create(
            unidad=unidad,
            codigo=receta.codigo.replace('-REC-', '-PRA-', 1),
            defaults={
                'proposito_codigo': 'docencia_practica',
                'subtipo_actividad': 'practica_curricular',
                'nombre': f'Práctica: {receta.producto.nombre}',
                'responsable': 'Responsable técnico de la planta',
                'descripcion': f'Práctica de elaboración de {receta.producto.nombre.lower()} con el proceso {receta.codigo}.',
                'estado_publicacion': 'publicado',
                'visibilidad': 'unidad',
                'activo': True,
            },
        )
        codigo = receta.codigo.replace('-REC-', '-GUI-', 1)
        if GuiaActividadReserva.objects.filter(actividad=actividad, codigo_guia=codigo).exists():
            continue
        creadas.append(GuiaActividadReserva.objects.create(
            actividad=actividad,
            familia=receta.familia,
            titulo=f'Guía de práctica: {receta.producto.nombre}',
            descripcion=(
                f'Guía de referencia generada desde el proceso {receta.codigo}: el docente la adapta a su '
                'asignatura y la planta la valida.'
            ),
            codigo_guia=codigo,
            numero_version=1,
            es_estructurada=True,
            es_vigente=True,
            contenido=contenido_de_referencia(receta),
            visibilidad='publica',
            estado_publicacion='publicada',
            permite_descarga=True,
            activo=True,
        ))
    return creadas
