"""La documentación de un proceso: la teoría detrás de cada etapa y los datos que usa.

La ficha de proceso dice **qué** hace la planta paso a paso. Esta documentación
dice **por qué**: qué operación unitaria es cada etapa, qué fenómeno ocurre,
qué variable la gobierna, qué pasa cuando esa variable se va de rango y cómo se
mide. Además pone sobre la mesa de dónde sale cada número de la ficha y qué
variables se pueden mover en los simuladores.

Nada de esto se escribe a mano por proceso: cada etapa se clasifica por su
nombre y su tipo en una de las operaciones unitarias del glosario, y el resto
sale de la receta cargada. Así vale igual para el queso de lácteos, el chorizo
de cárnicos y el almidón de papa, y para los procesos que la planta cargue
mañana.
"""

import re
from decimal import Decimal

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.plantas_piloto.operacion.presentation.navegacion_proceso import acciones_del_proceso, fichas_relacionadas_del_proceso, metadatos_editoriales

from apps.plantas_piloto.operacion.models.calidad import ParametroCalidad
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.directorio_unidades.models.core import Unidad

from apps.documentos.presentation.documentos import enlaces_de_documento, formato_pedido, respuesta_pdf
from apps.formacion.presentation.documentos_aula import documento_de_pagina
from apps.plantas_piloto.operacion.presentation.motores import etapas_termicas
from apps.plantas_piloto.operacion.presentation.procesos import FACTOR_MASA, _texto_cantidad, balance_de_masa, datos_de_receta, resumen_proceso, unidad_en_plural

# El glosario de operaciones unitarias. Cada entrada dice qué es la operación,
# qué fenómeno ocurre, qué variable la gobierna, qué pasa fuera de rango y con
# qué se mide. El patrón reconoce la etapa por su nombre.
OPERACIONES = (
    {
        'clave': 'recepcion',
        'icono': 'fas fa-clipboard-check',
        'patron': r'recepci[oó]n|control de (la )?(leche|carne|materia|fruta|harina|papa)|selecci[oó]n',
        'nombre': 'Recepción y control de materia prima',
        'familia': 'Inspección',
        'fenomeno': (
            'No hay transformación: hay una decisión. La materia prima se mide y se compara con un '
            'límite, y de esa comparación depende que el lote entre a la planta o se devuelva.'
        ),
        'variable': 'Los parámetros de aceptación de la materia prima (temperatura, acidez, pH, densidad, sanidad).',
        'fuera_de_rango': (
            'Una materia prima fuera de especificación arrastra el defecto a todo el lote y ya no se '
            'corrige aguas abajo: por eso la decisión se toma antes de descargar.'
        ),
        'se_mide': 'Con el plan de calidad de recepción del insumo, lote por lote, antes de ingresarlo.',
    },
    {
        'clave': 'termico_alto',
        'icono': 'fas fa-fire',
        'patron': r'pasteuriz|esterili|escald|cocci|cocc[ií]|horne|termiz|hervor|ebullici',
        'nombre': 'Tratamiento térmico',
        'familia': 'Transferencia de calor',
        'fenomeno': (
            'El calor se transfiere al producto hasta que su punto más frío alcanza la temperatura '
            'objetivo y la sostiene el tiempo necesario. La destrucción de microorganismos depende del '
            'binomio temperatura-tiempo, no de la temperatura sola.'
        ),
        'variable': 'La temperatura del producto en el punto más frío y el tiempo de sostenimiento.',
        'fuera_de_rango': (
            'Por debajo, el tratamiento no cumple su letalidad y el producto no es inocuo. Por encima, '
            'se pierde calidad: proteínas desnaturalizadas de más, color, sabor y nutrientes.'
        ),
        'se_mide': 'Con sonda en el centro geométrico de la pieza o en el tubo de retención, y su registro de curva.',
    },
    {
        'clave': 'acondicionamiento',
        'icono': 'fas fa-thermometer-half',
        'patron': r'calent|atemper|templ|precalent|acondicionamiento|ajuste del mosto|sulfitado del mosto|reducci[oó]n de grado',
        'nombre': 'Acondicionamiento térmico',
        'familia': 'Transferencia de calor',
        'fenomeno': (
            'El producto se lleva a la temperatura que la siguiente operación necesita. No busca '
            'destruir nada: busca que la enzima, el cultivo o la máquina trabajen en su punto.'
        ),
        'variable': 'La temperatura objetivo y la uniformidad de la masa al alcanzarla.',
        'fuera_de_rango': (
            'Fuera del punto, la operación siguiente rinde mal: la enzima se inactiva, el cultivo no '
            'arranca o la grasa se separa.'
        ),
        'se_mide': 'Con termómetro en la masa, con agitación, antes de dar por terminada la etapa.',
    },
    {
        'clave': 'enzimatica',
        'icono': 'fas fa-flask',
        'patron': r'licuefacci|sacarific|hidr[oó]lisis|enzim|alfa-?amilasa|glucoamilasa|^maceraci[oó]n$',
        'nombre': 'Conversión enzimática',
        'familia': 'Transformación bioquímica',
        'fenomeno': (
            'Una enzima rompe las cadenas largas del sustrato en fragmentos más cortos. Trabaja solo '
            'dentro de su ventana de temperatura y de pH, y se inactiva fuera de ella.'
        ),
        'variable': 'La temperatura, el pH, la dosis de enzima y el tiempo de reacción.',
        'fuera_de_rango': (
            'Fuera de su ventana la enzima no convierte o se destruye: la conversión queda incompleta y '
            'el rendimiento cae.'
        ),
        'se_mide': 'Por el avance de la conversión (grados Brix, dextrosa equivalente o prueba de yodo).',
    },
    {
        'clave': 'enfriamiento',
        'icono': 'fas fa-snowflake',
        'patron': r'enfri|duchad|refriger|c[aá]mara|choque t[eé]rmico',
        'nombre': 'Enfriamiento y cadena de frío',
        'familia': 'Transferencia de calor',
        'fenomeno': (
            'El producto cede calor al medio hasta la temperatura de conservación. La velocidad importa '
            'tanto como la temperatura final: el rango entre 60 y 10 °C es donde el producto está más '
            'expuesto y hay que cruzarlo rápido.'
        ),
        'variable': 'La temperatura final y el tiempo que tarda en alcanzarla.',
        'fuera_de_rango': (
            'Un enfriamiento lento deja al producto en la zona de riesgo y acorta su vida útil aunque el '
            'tratamiento térmico haya sido correcto.'
        ),
        'se_mide': 'Con termómetro en la pieza testigo y el registro de la cámara.',
    },
    {
        'clave': 'congelacion',
        'icono': 'fas fa-icicles',
        'patron': r'congel|t[uú]nel',
        'nombre': 'Congelación',
        'familia': 'Transferencia de calor',
        'fenomeno': (
            'El agua del producto cambia de estado. Cuanto más rápido cruza el rango de máxima '
            'cristalización, más pequeños son los cristales y menos daña la estructura al descongelar.'
        ),
        'variable': 'La temperatura del túnel o cámara y el tiempo de congelación.',
        'fuera_de_rango': (
            'Una congelación lenta forma cristales grandes que rompen la pared celular: al descongelar '
            'el producto suelta líquido y pierde textura.'
        ),
        'se_mide': 'Con sonda en el centro del envase y el registro del equipo.',
    },
    {
        'clave': 'fermentacion',
        'icono': 'fas fa-seedling',
        'patron': r'fermenta|incuba|madura|leudad|acidific|refresc|masa madre',
        'nombre': 'Fermentación',
        'familia': 'Transformación biológica',
        'fenomeno': (
            'Un cultivo consume azúcares y produce ácido, gas y compuestos de aroma. La velocidad '
            'depende de la temperatura y de la cantidad de cultivo; el final se reconoce por el pH o la '
            'acidez, no por el reloj.'
        ),
        'variable': 'La temperatura de incubación, la dosis de cultivo y el pH o la acidez final.',
        'fuera_de_rango': (
            'Corta, el producto queda dulce y sin cuerpo; larga, se pasa de ácido y suelta suero. Con '
            'inhibidores en la materia prima, sencillamente no arranca.'
        ),
        'se_mide': 'Con potenciómetro o titulación sobre una muestra, desde antes del final previsto.',
    },
    {
        'clave': 'coagulacion',
        'icono': 'fas fa-cubes',
        'patron': r'coagul|cuaj|gelific',
        'nombre': 'Coagulación',
        'familia': 'Transformación fisicoquímica',
        'fenomeno': (
            'La proteína pasa de estar dispersa a formar una red que atrapa la grasa y el agua. La '
            'enzima o el ácido desestabilizan la micela y el gel se arma sin agitación.'
        ),
        'variable': 'La temperatura, la dosis de cuajo o de ácido y el tiempo de reposo.',
        'fuera_de_rango': (
            'Un gel flojo se rompe al cortar y pierde rendimiento en el suero; uno demasiado firme '
            'retiene mal y endurece el producto.'
        ),
        'se_mide': 'Por el punto de corte limpio: el gel se abre sin desmigajarse sobre el dedo o la espátula.',
    },
    {
        'clave': 'separacion',
        'icono': 'fas fa-filter',
        'patron': r'desuer|descrem|centr[ií]fug|filtr|tamiz|prens|sediment|extracci[oó]n|escurr|separaci[oó]n|destil|rectific|trasieg|clarific|desaponif',
        'nombre': 'Separación',
        'familia': 'Operación mecánica',
        'fenomeno': (
            'Dos fases que estaban juntas se apartan por diferencia de densidad, de tamaño de partícula '
            'o por presión. Una fase sigue al producto y la otra sale como subproducto o residuo.'
        ),
        'variable': 'El rendimiento de la etapa: qué fracción de la masa continúa y cuál se va.',
        'fuera_de_rango': (
            'Separar de más arrastra producto al subproducto; separar de menos deja humedad o impureza '
            'que el proceso ya no quita.'
        ),
        'se_mide': 'Pesando lo que entra y lo que sale de la etapa: el balance de masa lo deja a la vista.',
    },
    {
        'clave': 'reduccion',
        'icono': 'fas fa-blender',
        'patron': r'molien|moler|rall|desintegr|cutter|c[uú]ter|triturad|despulp|licuad|corte|cortar|molino|^pelado$|^pelado qu[ií]mico|despiece|deshues|filete',
        'nombre': 'Reducción de tamaño',
        'familia': 'Operación mecánica',
        'fenomeno': (
            'El sólido se fragmenta y su superficie específica crece. Eso acelera todo lo que venga '
            'después (mezcla, extracción, transferencia de calor), pero también genera calor por '
            'fricción.'
        ),
        'variable': 'El tamaño de partícula (el disco o la malla) y la temperatura del producto al salir.',
        'fuera_de_rango': (
            'Si el producto se calienta de más en el molino o el cúter, la grasa se separa y la mezcla '
            'ya no liga: el defecto aparece recién en el producto terminado.'
        ),
        'se_mide': 'Con el disco o la malla montada y un termómetro de pincho en la bandeja de salida.',
    },
    {
        'clave': 'mezclado',
        'icono': 'fas fa-mortar-pestle',
        'patron': r'mezcl|amasad|amasar|batid|emulsi|homogeneiz|formulaci|masaje|salmuer|salad|dosific|pesaj|pesar|sazon|cobertura|marinad|rebozad|apanad|incorporaci|cremad|l[ií]quido de gobierno|saboriz',
        'nombre': 'Mezclado y formulación',
        'familia': 'Operación mecánica',
        'fenomeno': (
            'Los componentes se distribuyen hasta que cualquier porción de la masa tiene la misma '
            'composición. Aquí se decide la fórmula: lo que se pesa mal en esta etapa no se corrige '
            'después.'
        ),
        'variable': 'Las proporciones de la fórmula, el tiempo de mezcla y la temperatura de la masa.',
        'fuera_de_rango': (
            'Una mezcla corta deja vetas y bolsones; una larga calienta la masa o la sobretrabaja. Un '
            'aditivo mal pesado puede sacar el lote del límite legal.'
        ),
        'se_mide': 'Con la balanza de fórmula, el reloj de la máquina y la temperatura final de la masa.',
    },
    {
        'clave': 'concentracion',
        'icono': 'fas fa-compress-arrows-alt',
        'patron': r'concentr|evapor|reducci[oó]n de agua|cocc[ií]on de',
        'nombre': 'Concentración',
        'familia': 'Transferencia de calor y masa',
        'fenomeno': (
            'Se evapora agua y los sólidos suben. El producto gana cuerpo y vida útil porque baja su '
            'actividad de agua; el punto final se reconoce por los grados Brix, no por el tiempo.'
        ),
        'variable': 'Los grados Brix o los sólidos solubles finales, y la temperatura de la masa.',
        'fuera_de_rango': (
            'Por debajo, el producto queda líquido y se deteriora antes; por encima, cristaliza, se '
            'oscurece y toma sabor a caramelo quemado.'
        ),
        'se_mide': 'Con refractómetro sobre una muestra enfriada, cerca del punto final.',
    },
    {
        'clave': 'secado',
        'icono': 'fas fa-wind',
        'patron': r'secad|deshidrat|lecho fluid|flash|tostad',
        'nombre': 'Secado',
        'familia': 'Transferencia de calor y masa',
        'fenomeno': (
            'El agua migra del interior del sólido a la superficie y de ahí al aire. La temperatura del '
            'aire manda la velocidad, pero el límite lo pone el producto: pasado cierto punto se '
            'degrada.'
        ),
        'variable': 'La temperatura del aire, el tiempo y la humedad final del producto.',
        'fuera_de_rango': (
            'Húmedo de más, el producto se apelmaza y se enmohece; seco de más, se quema, pierde color '
            'y rinde menos.'
        ),
        'se_mide': 'Por pérdida de peso hasta masa constante, o con medidor de humedad sobre el producto molido.',
    },
    {
        'clave': 'conformado',
        'icono': 'fas fa-shapes',
        'patron': r'embutid|molde|formad|hilad|bole|divisi[oó]n|laminad|extrusi|llenad',
        'nombre': 'Conformado',
        'familia': 'Operación mecánica',
        'fenomeno': (
            'La masa toma la forma y el peso de la pieza que se va a vender. De aquí salen el calibre y '
            'la porción, y con ellos el rendimiento comercial del lote.'
        ),
        'variable': 'El peso y el calibre de la pieza, y la temperatura de la masa al conformar.',
        'fuera_de_rango': (
            'Piezas por debajo del peso declarado son un problema legal; por encima, regalan producto. '
            'La dispersión entre piezas es tan importante como el promedio.'
        ),
        'se_mide': 'Pesando piezas al azar a lo largo de la corrida y controlando la dispersión.',
    },
    {
        'clave': 'envasado',
        'icono': 'fas fa-box',
        'patron': r'envas|empaqu|etiquet|sellad|tapad|rebanad|embotell|cierre',
        'nombre': 'Envasado y etiquetado',
        'familia': 'Acondicionamiento',
        'fenomeno': (
            'El producto queda aislado del ambiente y recibe su identidad: el lote, la fecha y la '
            'información que el consumidor lee. El envase es parte de la barrera que conserva.'
        ),
        'variable': 'La integridad del sellado o el vacío, y el contenido de la etiqueta.',
        'fuera_de_rango': (
            'Un sellado defectuoso deja entrar aire y acorta la vida útil; una etiqueta sin lote rompe '
            'la trazabilidad y el producto no se puede recuperar si algo sale mal.'
        ),
        'se_mide': 'Inspeccionando empaques del lote y verificando el código de lote y el vencimiento.',
    },
    {
        'clave': 'transporte',
        'icono': 'fas fa-dolly',
        'patron': r'traslad|transport|carg|llevar',
        'nombre': 'Transporte interno',
        'familia': 'Movimiento',
        'fenomeno': (
            'El producto cambia de sitio sin transformarse. No agrega valor, pero sí tiempo, distancia '
            'y exposición: por eso el cursograma analítico lo mide aparte.'
        ),
        'variable': 'La distancia recorrida y el tiempo fuera de condición controlada.',
        'fuera_de_rango': (
            'Trayectos largos o cruzados entre zona sucia y zona limpia son el camino de la '
            'contaminación cruzada.'
        ),
        'se_mide': 'Con la distancia del cursograma y el tiempo de la etapa.',
    },
    {
        'clave': 'limpieza',
        'icono': 'fas fa-spray-can',
        'patron': r'limpiez|lavad|sanitiz|desinfec|cip|enjuag',
        'nombre': 'Limpieza y sanitización',
        'familia': 'Inocuidad',
        'fenomeno': (
            'La suciedad se despega, se arrastra y la carga microbiana se reduce. Es una operación con '
            'su propia química: concentración, temperatura, tiempo y acción mecánica.'
        ),
        'variable': 'La concentración del detergente o el sanitizante, la temperatura y el tiempo de contacto.',
        'fuera_de_rango': (
            'Una limpieza insuficiente contamina la corrida siguiente; un enjuague insuficiente deja '
            'residuo químico en el producto.'
        ),
        'se_mide': 'Con tiras de concentración, el registro del ciclo y la bitácora de limpieza.',
    },
    {
        'clave': 'espera',
        'icono': 'fas fa-hourglass-half',
        'patron': r'repos|espera|atemper|oreo|estabiliz',
        'nombre': 'Reposo',
        'familia': 'Espera controlada',
        'fenomeno': (
            'El producto no se toca, pero cambia: se estabiliza la estructura, se reparte la humedad o '
            'se completa una reacción empezada antes.'
        ),
        'variable': 'El tiempo y la temperatura del ambiente donde reposa.',
        'fuera_de_rango': 'Cortar el reposo deja el cambio a medias y el defecto aparece en el producto terminado.',
        'se_mide': 'Con el reloj de la corrida y la temperatura del área.',
    },
)

GENERICA = {
    'clave': 'operacion',
    'icono': 'fas fa-cog',
    'nombre': 'Operación de proceso',
    'familia': 'Operación',
    'fenomeno': 'Una transformación del producto que la planta declara en su receta.',
    'variable': 'Los tiempos, las personas y el rendimiento que la etapa declara.',
    'fuera_de_rango': 'Apartarse de lo declarado cambia el rendimiento de la corrida.',
    'se_mide': 'Con el registro de la corrida.',
}

# Lo que el tipo de etapa dice cuando el nombre no alcanza para clasificarla.
POR_TIPO = {
    'inspeccion': 'recepcion',
    'transporte': 'transporte',
    'espera': 'espera',
    'almacenamiento': 'enfriamiento',
}


def _por_clave(clave):
    return next(operacion for operacion in OPERACIONES if operacion['clave'] == clave)


def clasificar_etapa(etapa):
    """La operación unitaria de una etapa: por su nombre, salvo cuando el tipo manda.

    Mover no transforma: «Traslado a la cámara» es transporte aunque su nombre
    mencione la cámara a la que lleva el producto. Para el resto, el nombre es
    más específico que el tipo del cursograma.
    """
    if etapa.get('tipo') == 'transporte':
        return _por_clave('transporte')
    nombre = (etapa.get('nombre') or '').lower()
    for operacion in OPERACIONES:
        if re.search(operacion['patron'], nombre, re.I):
            return operacion
    clave = POR_TIPO.get(etapa.get('tipo'))
    return _por_clave(clave) if clave else GENERICA


def _num(valor):
    return Decimal(str(valor or 0))


def operaciones_del_proceso(datos):
    """Las operaciones unitarias que este proceso usa, con las etapas de cada una."""
    agrupadas = {}
    for etapa in datos.get('etapas', []):
        operacion = clasificar_etapa(etapa)
        entrada = agrupadas.setdefault(operacion['clave'], {**operacion, 'etapas': []})
        entrada['etapas'].append({
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'equipo': etapa.get('equipo') or '',
            'minutos': int(etapa.get('duracion_min') or 0) + int(etapa.get('espera_min') or 0),
            'punto_critico': bool(etapa.get('punto_critico')),
            'punto_control': bool(etapa.get('punto_control')),
            'parametro': etapa.get('parametro') or '',
            'limite': etapa.get('limite') or '',
        })
    # En el orden en que ocurren, no en el del glosario.
    return sorted(agrupadas.values(), key=lambda item: item['etapas'][0]['orden'])


def variables_del_proceso(receta, datos):
    """Lo que se puede mover y qué pasa al moverlo: la materia de los simuladores."""
    variables = [
        {
            'nombre': 'Escala de la corrida',
            'valor': f"{datos['cantidad_base']} {datos['unidad_base']}",
            'de_donde': 'La corrida base de la receta; el factor la multiplica.',
            'efecto': (
                'Todo escala con ella: los insumos, el producto esperado, la masa que entra y la '
                'energía que la corrida pide. Los tiempos de etapa no: una tina tarda lo mismo con '
                'media carga.'
            ),
            'simulador': 'Balance de materia y energía · Requerimiento de materiales',
        },
        {
            'nombre': 'Rendimiento esperado',
            'valor': f"{datos['rendimiento_esperado']} {datos['unidad_producto']} por corrida base",
            'de_donde': 'La receta lo declara; el balance de masa lo contrasta etapa por etapa.',
            'efecto': (
                'La diferencia entre el rendimiento declarado y el que sale del balance es la merma '
                'que el proceso no explica: ahí está lo que se pierde sin registrarse.'
            ),
            'simulador': 'Balance de materia y energía',
        },
    ]
    rendimientos = [
        etapa for etapa in datos.get('etapas', [])
        if _num(etapa.get('rendimiento_pct')) and _num(etapa.get('rendimiento_pct')) != 100
    ]
    if rendimientos:
        variables.append({
            'nombre': 'Rendimiento por etapa',
            'valor': ', '.join(
                f"{etapa['orden']}. {etapa['nombre']}: {etapa['rendimiento_pct']} %"
                for etapa in rendimientos
            ),
            'de_donde': 'Cada etapa declara qué fracción de la masa continúa.',
            'efecto': (
                'Es donde nacen las mermas y los subproductos. Subir un punto en la etapa que más '
                'pierde vale más que subirlo en cualquier otra.'
            ),
            'simulador': 'Balance de materia y energía',
        })
    variables.append({
        'nombre': 'Corridas por jornada',
        'valor': f"{resumen_proceso(datos)['duracion_texto']} por corrida",
        'de_donde': 'La suma de los tiempos de trabajo y espera de las etapas.',
        'efecto': (
            'Define el ritmo que la línea tiene que sostener (el takt) y, con él, cuántas estaciones '
            'hacen falta y cuál es el cuello de botella.'
        ),
        'simulador': 'Balance de línea',
    })
    calientes = [
        etapa for etapa in datos.get('etapas', [])
        if clasificar_etapa(etapa)['clave'] in ('termico_alto', 'concentracion', 'secado')
    ]
    if calientes:
        variables.append({
            'nombre': 'Temperaturas del tratamiento térmico',
            'valor': '; '.join(
                f"{etapa['orden']}. {etapa['nombre']}: {etapa.get('limite') or 'sin límite declarado'}"
                for etapa in calientes
            ),
            'de_donde': 'El límite crítico que la etapa declara, y el plan de calidad que lo vigila.',
            'efecto': (
                'Mueve el calor que la corrida consume y el vapor que hace falta; por debajo del '
                'límite, el tratamiento deja de ser inocuo.'
            ),
            'simulador': 'Balance de materia y energía',
        })
    variables.append({
        'nombre': 'Existencias en bodega',
        'valor': 'Lo que el inventario tenga al correr el simulador',
        'de_donde': 'El stock y el stock de seguridad de cada insumo de la receta.',
        'efecto': 'Decide si el plan de corridas se puede hacer o qué falta comprar y cuándo.',
        'simulador': 'Requerimiento de materiales',
    })
    return variables


def entradas_y_salidas(datos):
    """Qué entra, qué se incorpora, qué sale y qué se pierde, etapa por etapa."""
    balance = balance_de_masa(datos)
    roles = {
        'base': 'Materia prima base: es lo que entra a la corrida.',
        'si': 'Se incorpora al producto: suma a la masa que continúa.',
        'no': 'Auxiliar: se usa en el proceso pero no queda en el producto.',
    }
    entradas = []
    for etapa in datos.get('etapas', []):
        for insumo in etapa.get('insumos', []):
            entradas.append({
                'etapa': etapa['orden'],
                'nombre': insumo['nombre'],
                'cantidad': f"{insumo['cantidad']} {insumo['unidad']}",
                'rol': roles.get(insumo.get('forma_parte'), roles['si']),
                'obligatorio': insumo.get('obligatorio', True),
            })
    for insumo in datos.get('insumos_sin_etapa', []):
        entradas.append({
            'etapa': None,
            'nombre': insumo['nombre'],
            'cantidad': f"{insumo['cantidad']} {insumo['unidad']}",
            'rol': roles.get(insumo.get('forma_parte'), roles['si']),
            'obligatorio': insumo.get('obligatorio', True),
        })
    salidas = []
    for fila in balance['filas']:
        if _num(fila['perdida']) > 0:
            salidas.append({
                'etapa': fila['orden'],
                # Sin bajar a minusculas: «Merma de pasteurizacion htst» no se lee.
                'nombre': f"Merma de {fila['nombre']}",
                'cantidad': f"{fila['perdida']} {datos['unidad_base'].split()[-1]}",
                'tipo': 'Merma',
                'detalle': 'Masa que sale del flujo sin declararse como producto ni subproducto.',
            })
        for texto in fila.get('salidas', []):
            salidas.append({
                'etapa': fila['orden'],
                'nombre': texto,
                'cantidad': '',
                'tipo': 'Salida declarada',
                'detalle': 'La receta la declara: subproducto o residuo del proceso.',
            })
    return {
        'entradas': entradas,
        'salidas': salidas,
        'balance': balance,
        'merma_total': sum((_num(fila['perdida']) for fila in balance['filas']), Decimal('0')),
    }


def balance_general(datos, flujo):
    """Toda la corrida en un bloque: lo que entra por un lado y lo que sale por el otro.

    Es el diagrama con que abre cualquier memoria de proceso, y el que responde
    de un vistazo qué desperdicia una corrida. Los totales no se suman aparte:
    salen del balance por etapa, que ya resolvió las conversiones y sabe qué
    salida pertenece al flujo. Un insumo se muestra en su propia unidad -diez
    mililitros de cuajo son diez mililitros- pero al total entra por su masa.

    Tres cosas quedan fuera del flujo y se dicen aparte, no se disimulan: la
    materia prima ya contada como entrada, los auxiliares que se consumen sin
    quedar en el producto (empaques, paños, salmuera) y las salidas declaradas
    como externas al flujo, como el agua de lavado de la línea. Si aun
    así lo que entra no cuadra con lo que sale, la receta declara de más en
    alguna etapa y el diagrama lo dice.
    """
    balance = flujo['balance']
    unidad_base = datos['unidad_base']
    # Una corrida puede tener varias materias primas base: la carne y la grasa de un embutido.
    bases = [
        insumo
        for etapa in datos.get('etapas', [])
        for insumo in etapa.get('insumos', [])
        if insumo.get('forma_parte') == 'base'
    ]
    entradas = [{
        'nombre': ', '.join(insumo['nombre'] for insumo in bases) if bases else 'Materia prima',
        'detalle': 'materia prima de la corrida',
        'cantidad': balance['entrada'],
        'unidad': unidad_base,
        'clase': 'base',
    }]
    auxiliares = []
    for etapa in datos.get('etapas', []):
        for insumo in etapa.get('insumos', []):
            if any(insumo is materia for materia in bases):
                continue
            incorpora = insumo.get('forma_parte', 'si') == 'si'
            pesa = FACTOR_MASA.get(str(insumo.get('unidad', '')).strip().lower()) is not None
            fila = {
                'nombre': insumo['nombre'],
                'detalle': f"etapa {etapa['orden']}",
                'cantidad': insumo['cantidad'],
                'unidad': unidad_en_plural(insumo['unidad'], insumo['cantidad']),
                'clase': 'insumo' if incorpora and pesa else 'auxiliar',
            }
            (entradas if fila['clase'] == 'insumo' else auxiliares).append(fila)
    for insumo in datos.get('insumos_sin_etapa', []):
        auxiliares.append({
            'nombre': insumo['nombre'],
            'detalle': 'sin etapa declarada',
            'cantidad': insumo['cantidad'],
            'unidad': unidad_en_plural(insumo['unidad'], insumo['cantidad']),
            'clase': 'auxiliar',
        })

    salidas = [{
        'nombre': datos['producto'],
        'detalle': 'producto de la corrida',
        'cantidad': balance['producto_por_balance'],
        'unidad': unidad_en_plural(datos['unidad_producto'], balance['producto_por_balance']),
        'clase': 'producto',
    }]
    externas = []
    for etapa in datos.get('etapas', []):
        for salida in etapa.get('salidas', []):
            fuera_del_flujo = salida.get('externa_al_flujo', False)
            fila = {
                'nombre': salida['nombre'],
                'detalle': f"etapa {etapa['orden']}",
                'cantidad': salida['cantidad'],
                'unidad': unidad_en_plural(salida['unidad'], salida['cantidad']),
                'clase': 'externa' if fuera_del_flujo else 'subproducto',
            }
            (externas if fuera_del_flujo else salidas).append(fila)
    merma = flujo['merma_total']
    if merma > 0:
        salidas.append({
            'nombre': 'Merma del proceso',
            'detalle': 'masa que sale sin declararse',
            'cantidad': _texto_cantidad(merma),
            'unidad': unidad_base,
            'clase': 'merma',
        })

    # Los totales salen del balance por etapa: entra más lo que se incorpora,
    # sale el producto más lo declarado dentro del flujo más lo que se pierde.
    entra_total = _num(balance['entrada']) + sum(
        (_num(fila['agregado']) for fila in balance['filas']), Decimal('0')
    )
    declarado_en_flujo = sum(
        (_num(fila['declarado']) - _num(fila['externo'] or 0) for fila in balance['filas']),
        Decimal('0'),
    )
    sale_total = (
        _num(balance['producto_por_balance'])
        + declarado_en_flujo
        + sum((_num(fila['perdida']) for fila in balance['filas']), Decimal('0'))
    )
    diferencia = entra_total - sale_total
    # Cuando una etapa declara mas salida de la que pierde, el balance no cuadra
    # y la culpa es de la receta, no del dibujo: se nombra la etapa para que la
    # planta la revise.
    descuadres = [
        {
            'orden': fila['orden'],
            'nombre': fila['nombre'],
            'exceso': fila['exceso'],
            'declarado': fila['declarado'],
        }
        for fila in balance['filas']
        if fila.get('exceso')
    ]
    return {
        'descuadres': descuadres,
        'entradas': entradas,
        'auxiliares': auxiliares,
        'salidas': salidas,
        'externas': externas,
        'entra_total': _texto_cantidad(entra_total),
        'sale_total': _texto_cantidad(sale_total),
        'diferencia': _texto_cantidad(abs(diferencia)),
        'cuadra': abs(diferencia) <= Decimal('0.002'),
        'sobra_declarado': diferencia < 0,
        'unidad_base': unidad_base,
        'merma_total': _texto_cantidad(merma),
        'proporcion_merma': _texto_cantidad(
            (merma / entra_total * 100).quantize(Decimal('0.01')) if entra_total else Decimal('0')
        ),
        'etapas': len(balance['filas']),
    }


def flujo_por_etapa(datos, balance):
    """Cada etapa con lo que entra por la izquierda y lo que sale por la derecha.

    Es el diagrama que una planta dibuja a mano: el bloque de la operación, las
    flechas de insumos que entran en esa etapa y las de salidas y mermas que se
    van. Aquí sale de la receta y del balance de masa, así que los números son
    los de la corrida y no un dibujo aparte.
    """
    filas = []
    por_orden = {fila['orden']: fila for fila in balance['filas']}
    for etapa in datos.get('etapas', []):
        masa = por_orden.get(etapa['orden'], {})
        operacion = clasificar_etapa(etapa)
        salidas = [
            {'nombre': texto, 'clase': 'declarada'}
            for texto in masa.get('salidas', [])
        ]
        if _num(masa.get('perdida')) > 0:
            salidas.append({
                'nombre': f"Merma {masa['perdida']}",
                'clase': 'merma',
            })
        filas.append({
            'orden': etapa['orden'],
            'nombre': etapa['nombre'],
            'tipo': etapa['tipo'],
            'operacion': operacion,
            'equipo': etapa.get('equipo') or '',
            'espacio': etapa.get('espacio') or '',
            'minutos': int(etapa.get('duracion_min') or 0) + int(etapa.get('espera_min') or 0),
            'personas': int(etapa.get('personas') or 0),
            'punto_critico': bool(etapa.get('punto_critico')),
            'punto_control': bool(etapa.get('punto_control')),
            'parametro': etapa.get('parametro') or '',
            'limite': etapa.get('limite') or '',
            'insumos': [
                {'nombre': insumo['nombre'], 'cantidad': f"{insumo['cantidad']} {insumo['unidad']}"}
                for insumo in etapa.get('insumos', [])
            ],
            'salidas': salidas,
            'entra': masa.get('entra', ''),
            'continua': masa.get('continua', ''),
            'rendimiento': masa.get('rendimiento_pct', ''),
        })
    return filas


def datos_que_usa(receta, unidad):
    """De dónde sale cada número que la ficha muestra."""
    parametros = ParametroCalidad.objects.filter(
        plan__unidad=unidad, plan__activo=True, activo=True, etapa__receta=receta,
    ).select_related('plan', 'etapa').order_by('etapa__orden', 'orden')
    return [
        {
            'dato': 'Etapas, tiempos, personas y rendimiento',
            'fuente': f'La receta {receta.codigo} cargada en el panel de la unidad.',
            'quien': 'Lo mantiene la coordinación de la planta en la pestaña de producción.',
        },
        {
            'dato': 'Equipos y áreas de cada etapa',
            'fuente': 'El catálogo de equipos y espacios de la unidad.',
            'quien': 'Lo mismo que el asistente de reservas ofrece y bloquea.',
        },
        {
            'dato': 'Insumos por etapa y salidas',
            'fuente': 'Los insumos y las salidas declarados en la receta, con su rol en el balance.',
            'quien': 'De ahí se descuenta el inventario al cerrar la corrida.',
        },
        {
            'dato': 'Puntos críticos y sus límites',
            'fuente': (
                f'Las etapas marcadas como punto crítico en la receta, y los {parametros.count()} '
                'parámetros de los planes de calidad que las vigilan.'
            ),
            'quien': 'Lo mantiene la unidad en la pestaña de calidad e inocuidad.',
        },
        {
            'dato': 'Existencias de cada insumo',
            'fuente': 'El inventario de la unidad, con su stock y su stock de seguridad.',
            'quien': 'Se actualiza con cada entrada y cada consumo registrado.',
        },
    ]


def artefactos_del_proceso(receta, datos):
    """Qué puede publicarse ya y qué debe esperar datos de campo verificables."""
    etapas = list(receta.etapas.select_related('equipo').order_by('orden'))
    equipos = {etapa.equipo_id: etapa.equipo for etapa in etapas if etapa.equipo_id}.values()
    tiene_corrientes = bool(receta.insumos.exists() and etapas)
    tiene_termicas = bool(etapas_termicas(datos)[0] or etapas_termicas(datos)[1])
    tiene_recorrido = bool(equipos) and all(
        equipo.coordenada_x is not None and equipo.coordenada_y is not None for equipo in equipos
    )
    tiene_capacidad = bool(equipos) and all(
        equipo.capacidad_util_max is not None and equipo.modo_operacion
        and equipo.tiempo_setup is not None and equipo.tiempo_limpieza is not None
        for equipo in equipos
    )
    tiene_fallas = bool(equipos) and all(
        equipo.mtbf is not None and equipo.mttr is not None for equipo in equipos
    )
    return (
        {'nombre': 'Diagrama de flujo', 'estado': 'Disponible', 'listo': True,
         'detalle': 'Se genera desde el orden y tipo de las etapas publicadas.'},
        {'nombre': 'Diagrama sinóptico y cursograma', 'estado': 'Disponible', 'listo': True,
         'detalle': 'Clasifica operación, inspección, transporte, espera y almacenamiento desde la receta.'},
        {'nombre': 'Balance total y diagrama de corrientes',
         'estado': 'Disponible' if tiene_corrientes else 'Bloqueado', 'listo': tiene_corrientes,
         'detalle': 'Usa insumos, salidas y rendimientos.' if tiene_corrientes else 'Faltan corrientes o etapas de la receta.'},
        {'nombre': 'Balance térmico de escenario',
         'estado': 'Disponible con supuestos' if tiene_termicas else 'Bloqueado', 'listo': tiene_termicas,
         'detalle': 'Exige revisar densidad, cₚ, temperaturas y eficiencia.' if tiene_termicas else 'El proceso no declara una etapa térmica.'},
        {'nombre': 'Diagrama de recorrido',
         'estado': 'Disponible' if tiene_recorrido else 'Bloqueado', 'listo': tiene_recorrido,
         'detalle': 'Se dibuja en la ficha del proceso con las coordenadas X/Y de los equipos.' if tiene_recorrido else 'Faltan coordenadas X/Y de uno o más equipos.'},
        {'nombre': 'Capacidad efectiva por equipo y línea',
         'estado': 'Disponible' if tiene_capacidad else 'Bloqueado', 'listo': tiene_capacidad,
         'detalle': 'Carga útil, modo, preparación y limpieza completos.' if tiene_capacidad else 'Faltan carga útil, modo, preparación o limpieza.'},
        {'nombre': 'Simulación de fallas y disponibilidad',
         'estado': 'Disponible' if tiene_fallas else 'Bloqueado', 'listo': tiene_fallas,
         'detalle': 'MTBF y MTTR completos.' if tiene_fallas else 'Faltan MTBF o MTTR validados.'},
        {'nombre': 'Balance por componente', 'estado': 'Bloqueado', 'listo': False,
         'detalle': 'Requiere composiciones verificadas por corriente: grasa, sólidos, humedad u otra variable.'},
        {'nombre': 'Supervisión en tiempo real', 'estado': 'Bloqueado', 'listo': False,
         'detalle': 'Requiere señales, unidades, frecuencia, calidad y responsable de cada conexión.'},
    )


def documentacion_de_proceso(receta, unidad, factor=Decimal('1')):
    """Todo lo que la pestaña de documentación de un proceso muestra."""
    datos = datos_de_receta(receta, factor)
    resumen = resumen_proceso(datos)
    flujo = entradas_y_salidas(datos)
    return {
        'receta': receta,
        'proceso': datos,
        'resumen': resumen,
        'operaciones': operaciones_del_proceso(datos),
        'flujo': flujo_por_etapa(datos, flujo['balance']),
        'general': balance_general(datos, flujo),
        'variables': variables_del_proceso(receta, datos),
        'entradas': flujo['entradas'],
        'salidas': flujo['salidas'],
        'balance': flujo['balance'],
        'datos_que_usa': datos_que_usa(receta, unidad),
        'puntos_criticos': [etapa for etapa in datos['etapas'] if etapa.get('punto_critico')],
        'artefactos': artefactos_del_proceso(receta, datos),
        'ruta_aprendizaje': (
            {
                'numero': '01', 'clave': 'Comprender', 'icono': 'fas fa-lightbulb',
                'detalle': 'Reconoce la operación unitaria, el fenómeno y la variable que la gobierna.',
            },
            {
                'numero': '02', 'clave': 'Calcular', 'icono': 'fas fa-calculator',
                'detalle': 'Plantea balances, tiempos y capacidad con unidades y supuestos visibles.',
            },
            {
                'numero': '03', 'clave': 'Aplicar', 'icono': 'fas fa-flask',
                'detalle': 'Cambia un escenario sin alterar la receta validada de la planta.',
            },
            {
                'numero': '04', 'clave': 'Comprobar', 'icono': 'fas fa-check-double',
                'detalle': 'Contrasta cierre, límites críticos y procedencia antes de usar el resultado.',
            },
        ),
        'fundamentos': (
            {
                'nombre': 'Balance total de materia', 'icono': 'fas fa-balance-scale',
                'formula': 'Acumulación = Entrada − Salida + Generación − Consumo',
                'uso': 'En una corrida por lotes sin reacción y al cierre: la suma de entradas debe explicar productos, subproductos y pérdidas.',
                'datos': 'Masa o volumen convertido de cada insumo, salida y rendimiento por etapa.',
                'comprobacion': 'La diferencia de cierre debe quedar dentro de la tolerancia declarada; si no, se señala la etapa que no cuadra.',
            },
            {
                'nombre': 'Balance por componente', 'icono': 'fas fa-tint',
                'formula': 'Σ(mᵢ · xᵢ) entrada = Σ(mⱼ · xⱼ) salida',
                'uso': 'Comprueba grasa, sólidos, humedad, sal, azúcar u otro componente que el proceso deba conservar o transformar.',
                'datos': 'Masa m y fracción x medidas o documentadas para cada corriente.',
                'comprobacion': 'No se calcula mientras la receta no declare composiciones verificadas.',
            },
            {
                'nombre': 'Energía sensible', 'icono': 'fas fa-temperature-high',
                'formula': 'Q = m · cₚ · ΔT',
                'uso': 'Estima el calor que debe entrar o salir cuando cambia la temperatura sin cambio de fase.',
                'datos': 'Masa, calor específico, temperatura inicial, temperatura final y eficiencia.',
                'comprobacion': 'Los valores de cₚ y densidad deben indicar su origen; una referencia editable no equivale a una medición UPEC.',
            },
            {
                'nombre': 'Ritmo y capacidad', 'icono': 'fas fa-stopwatch',
                'formula': 'Takt = tiempo disponible / demanda; capacidad de línea = mínimo de las capacidades efectivas',
                'uso': 'Detecta la etapa que limita la jornada y comprueba si el plan cabe en el tiempo disponible.',
                'datos': 'Trabajo, espera, preparación, limpieza, carga útil y demanda de la jornada.',
                'comprobacion': 'La capacidad nominal se muestra como referencia; la planificación exige capacidad útil y tiempos levantados.',
            },
            {
                'nombre': 'Tiempo estándar', 'icono': 'fas fa-user-clock',
                'formula': 'TN = To · Fv; TE = TN · (1 + S)',
                'uso': 'Convierte el tiempo observado To en tiempo normal TN y luego incorpora suplementos S para obtener un estándar alcanzable.',
                'datos': 'Lecturas del cronometraje, factor de valoración, método aplicado y suplementos documentados.',
                'comprobacion': 'Una duración escrita en la receta orienta el flujo; no reemplaza un estudio con muestra, fecha, operario y vigencia.',
            },
            {
                'nombre': 'Capacidad de equipo por lote', 'icono': 'fas fa-cogs',
                'formula': 'ciclo = setup + carga + proceso + descarga + limpieza; capacidad = carga útil · ciclos/turno',
                'uso': 'Calcula cuánto puede producir una tina, marmita, horno o fermentador dentro de una jornada efectiva.',
                'datos': 'Carga útil mínima y máxima, tiempos del ciclo y minutos efectivos del turno.',
                'comprobacion': 'La carga nominal de placa no sustituye la carga útil validada con el producto real.',
            },
            {
                'nombre': 'Disponibilidad y OEE', 'icono': 'fas fa-chart-line',
                'formula': 'OEE = disponibilidad · rendimiento · calidad',
                'uso': 'Relaciona tiempo operativo, velocidad demostrada y producto conforme para seguir pérdidas del equipo.',
                'datos': 'Paros clasificados, tiempo planificado, producción real, ciclo ideal y unidades conformes.',
                'comprobacion': 'La limpieza obligatoria se trata como actividad planificada y la merma inherente se separa del desperdicio evitable.',
            },
        ),
        'referencias_tecnicas': (
            {
                'nombre': 'FAO · Estudio de sistemas agroalimentarios',
                'uso': 'Diagramas de proceso y balances construidos con información primaria del proceso.',
                'url': 'https://www.fao.org/4/y5788e/y5788e00.pdf',
            },
            {
                'nombre': 'OIT · Introducción al estudio del trabajo',
                'uso': 'Métodos, medición del trabajo y tiempos estándar.',
                'url': 'https://www.ilo.org/publications/introduction-work-study-4th-revised-edition',
            },
            {
                'nombre': 'NIST MEP · Balance de línea en alimentos',
                'uso': 'Takt como tiempo disponible dividido por demanda y detección del cuello de botella.',
                'url': 'https://www.nist.gov/mep/successstories/2023/continuous-improvement-activities-food-processing-line',
            },
            {
                'nombre': 'Codex CXC 1-1969 · Principios generales de higiene',
                'uso': 'Buenas prácticas de higiene y sistema HACCP.',
                'url': 'https://www.fao.org/fao-who-codexalimentarius/publications/en/',
            },
        ),
    }


@xframe_options_sameorigin
def documentacion_proceso_view(request, slug, receta_id):
    """La teoría del proceso: qué es cada etapa, qué la gobierna y qué datos usa."""
    unidad = get_object_or_404(Unidad, slug=slug)
    receta = get_object_or_404(
        Receta.objects.select_related('producto', 'unidad'), pk=receta_id, unidad=unidad, activa=True,
    )
    contexto = documentacion_de_proceso(receta, unidad)
    editorial = metadatos_editoriales(receta, titulo=receta.nombre_publico, codigo=receta.codigo)
    contexto.update({
        'unidad': unidad,
        'generado_en': timezone.localtime(),
        'volver_url': unidad.get_absolute_url(),
        'acciones_proceso': acciones_del_proceso(unidad, receta, 'documentacion'),
        'fichas_relacionadas': fichas_relacionadas_del_proceso(unidad, receta),
        'cita': editorial['cita'],
        **enlaces_de_documento(request),
    })
    from apps.gestion_unidades.presentation.repositorio import contexto_adjuntos
    contexto.update(contexto_adjuntos(receta, unidad, request.user))
    formato = formato_pedido(request)
    if formato:
        return respuesta_pdf(
            documento_de_pagina('documentacion', contexto),
            f'documentacion-{receta.codigo.lower()}.pdf',
            formato,
        )
    return render(request, 'portal/pages/unidades/aula/documentacion.html', contexto)
