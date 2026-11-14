"""Guías verificables del Centro de distribución configurable.

Contenido docente versionado, independiente de Django y del motor de simulación.
Las asignaturas conservan los códigos de la matriz académica existente; esta
vinculación no sustituye un sílabo aprobado ni registra una calificación oficial.
"""

from copy import deepcopy

GUIA_VERSION = "1.0.0"

FUENTES = {
    "gs1": {
        "id": "gs1",
        "titulo": "GS1 · EPCIS y Core Business Vocabulary",
        "url": "https://ref.gs1.org/guidelines/epcis-cbv/",
        "consulta": "2026-10-12",
        "alcance": "Identidad, contexto y secuencia de eventos de trazabilidad. El registro docente no afirma conformidad EPCIS ni emite identificadores GS1 reales.",
    },
    "osha": {
        "id": "osha",
        "titulo": "OSHA · Riesgos y soluciones en almacenes",
        "url": "https://www.osha.gov/warehousing/hazards-solutions",
        "consulta": "2026-10-12",
        "alcance": "Referencia técnica para revisar circulación, estabilidad, capacidad y mantenimiento. No sustituye la normativa ecuatoriana, la evaluación local de riesgos ni la autorización de equipos.",
    },
    "mit": {
        "id": "mit",
        "titulo": "MIT OpenCourseWare · Caso de mejora de un almacén",
        "url": "https://ocw.mit.edu/courses/15-057-systems-optimization-spring-2003/aa8dc878d2db465755296f45d8b307f6_peachstatecasestudy.pdf",
        "consulta": "2026-10-12",
        "alcance": "Caso académico que relaciona rotación, ubicación, recorridos y preparación. Los tiempos y clases de este simulador son propios y sintéticos, no datos del caso del MIT.",
    },
    "nist": {
        "id": "nist",
        "titulo": "NIST · Diseño de experimentos",
        "url": "https://www.itl.nist.gov/div898/handbook/pmd/section3/pmd31.htm",
        "consulta": "2026-10-12",
        "alcance": "Formulación de factores, respuestas y comparaciones controladas. Las conclusiones de la práctica se limitan al modelo, los escenarios y las semillas observados.",
    },
}

ASIGNATURAS = [
    {
        "codigo": "LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A",
        "nombre": "Logística de almacenamiento e inventario",
        "relacion": "principal",
        "aplicacion": "Operar recepción, ubicación y preparación manteniendo conciliación por SKU y tabla de indicadores.",
    },
    {
        "codigo": "LOGT-TIC-APLICADAS-A-LA-LOGISTICA",
        "nombre": "TIC aplicadas a la logística",
        "relacion": "apoyo transversal",
        "aplicacion": "Validar el diccionario, consultar eventos y documentar un tablero con respaldo tabular.",
    },
    {
        "codigo": "LOGT-SIMULADORES-LOGISTICOS",
        "nombre": "Simuladores logísticos",
        "relacion": "apoyo transversal",
        "aplicacion": "Diseñar comparaciones reproducibles y distinguir sensibilidad de causalidad.",
    },
]

ETAPAS = [
    {
        "id": "recepcion",
        "nombre": "Recepción",
        "entrada": "Seis lotes identificados con SKU, cantidad y ubicación de llegada; calidad aún desconocida.",
        "operacion": "Identificar el lote y dirigirlo al control. La recepción contable de conformes se confirma después de inspeccionar y, si procede, rechazar la parte dañada.",
        "salida": "Cantidad conforme recibida, con origen conservado; no convertir unidades rechazadas en inventario disponible.",
        "control": "Conciliar unidades de llegada, conformes y rechazadas por SKU, sin contar una unidad en dos estados.",
        "indicador": "Unidades recibidas conformes por SKU [u].",
    },
    {
        "id": "control",
        "nombre": "Control de calidad",
        "entrada": "Lote pendiente de inspección; el daño no está revelado antes de esta acción.",
        "operacion": "Inspeccionar todos los lotes, registrar conformidad y separar el rechazo parcial antes de recibir el resto.",
        "salida": "Trazabilidad de inspección, unidades rechazadas y unidades conformes elegibles para recepción.",
        "control": "No adivinar ni usar una semilla conocida como sustituto de la inspección; no omitir el rechazo registrado.",
        "indicador": "Rechazo = unidades rechazadas / unidades de llegada × 100 [%].",
    },
    {
        "id": "ubicacion",
        "nombre": "Ubicación",
        "entrada": "Lotes conformes recibidos; ubicaciones A-01, B-01 y C-01 con capacidad finita.",
        "operacion": "Asignar ubicación sin exceder su capacidad; contrastar correspondencia ABC y una alternativa factible. Todo SKU puede ocupar cualquier ubicación disponible.",
        "salida": "Existencia disponible por lote y ubicación; ocupación coherente con unidades almacenadas.",
        "control": "Capacidades 12, 10 y 8 cajas normalizadas; un recurso en falla no autoriza intervención física ni sobrecarga.",
        "indicador": "Ocupación = unidades almacenadas / capacidad de ubicación × 100 [%].",
    },
    {
        "id": "picking",
        "nombre": "Preparación de pedidos",
        "entrada": "Pedido y líneas requeridas; lotes disponibles del SKU solicitado.",
        "operacion": "Preparar una unidad por acción respetando FIFO por SKU. Priorizar pedidos con criterio explícito y registrar por qué cambia la secuencia.",
        "salida": "Unidades reservadas y preparadas para un pedido concreto, descontadas de la ubicación de origen.",
        "control": "No preparar más de lo solicitado, no sustituir SKU y no escoger un lote posterior mientras exista uno anterior disponible.",
        "indicador": "Tiempo de preparación [min], unidades preparadas [cajas] y recorrido didáctico [m]; no confundirlo con distancia física medida.",
    },
    {
        "id": "embalaje",
        "nombre": "Embalaje",
        "entrada": "Todas las líneas del pedido completas y conciliadas.",
        "operacion": "Verificar identidad y cantidades; confirmar embalaje sólo cuando todas las líneas estén preparadas.",
        "salida": "Pedido completo embalado, con contenido y evento verificables.",
        "control": "Una línea parcial no habilita embalaje ni despacho; evitar duplicación entre preparado y despachado.",
        "indicador": "Pedidos embalados completos / pedidos totales × 100 [%].",
    },
    {
        "id": "despacho",
        "nombre": "Despacho",
        "entrada": "Pedido completo y embalado; promesa de entrega en minutos simulados.",
        "operacion": "Confirmar salida y conservar el instante del despacho; al terminar, conciliar todos los SKU y comparar cumplimiento con la promesa.",
        "salida": "Pedido despachado con cantidad, momento y cumplimiento; o cierre parcial declarado sin inventar entregas.",
        "control": "OTIF exige simultáneamente pedido completo y despacho dentro de la promesa. Pedido pendiente cuenta en el denominador total.",
        "indicador": "OTIF = pedidos completos despachados a tiempo / pedidos totales × 100 [%].",
    },
]

TEORIA = [
    {
        "id": "balance",
        "titulo": "Conservación y trazabilidad",
        "contenido": "El flujo cambia el estado y la localización de una unidad, no crea inventario. La conciliación por SKU reparte la entrada entre material pendiente, rechazo pendiente de segregar, existencia disponible, unidades preparadas, unidades despachadas y rechazo confirmado. Un pedido embalado conserva sus unidades preparadas hasta el despacho; sumarlas otra vez duplicaría material. Cada diferencia requiere localizar el primer evento incoherente, no ajustar manualmente el total.",
        "fuentes": ["gs1"],
    },
    {
        "id": "abc",
        "titulo": "ABC, capacidad y FIFO son decisiones diferentes",
        "contenido": "ABC orienta el acceso a productos según su actividad; no impone porcentajes universales ni acredita que una ubicación sea óptima. En este modelo las clases A, B y C ya vienen declaradas y la coincidencia con la zona reduce minutos de picking. La capacidad limita unidades almacenadas, mientras FIFO gobierna qué lote disponible se consume primero dentro de un mismo SKU. Una mejora de ubicación puede cambiar tiempo sin cambiar la regla FIFO.",
        "fuentes": ["mit"],
    },
    {
        "id": "tiempo",
        "titulo": "Reloj de acciones y desempeño",
        "contenido": "Los minutos avanzan al ejecutar acciones: no corresponden al tiempo frente a la pantalla. Una pausa del participante no empeora el resultado. Antes de atribuir una demora a una zona, separar cantidad de trabajo, secuencia, errores, espera y duración de cada acción. La productividad utiliza un numerador y un horizonte explícitos; pedidos por hora y unidades por hora no son intercambiables.",
        "fuentes": [],
    },
    {
        "id": "servicio",
        "titulo": "Servicio y pedidos completos",
        "contenido": "Despachar muchas unidades no garantiza atender pedidos completos ni cumplir promesas. OTIF combina integridad y puntualidad con todos los pedidos del caso en el denominador. La prioridad permite decidir el orden, pero no excluye pedidos difíciles del cálculo. Informar también pedidos despachados, pendientes y minutos de cierre para distinguir velocidad, cobertura y servicio.",
        "fuentes": [],
    },
    {
        "id": "eventos",
        "titulo": "Registro de eventos explicable",
        "contenido": "Un evento útil identifica lo que ocurrió, el momento, el objeto y la etapa. Esas dimensiones permiten reconstruir el tránsito de un lote y justificar una decisión. La bitácora local es un registro docente; relacionar sus campos con las dimensiones de GS1 es un ejercicio de análisis, no una certificación, una API EPCIS ni una conexión con empresas.",
        "fuentes": ["gs1"],
    },
    {
        "id": "comparacion",
        "titulo": "Experimento y alcance de la conclusión",
        "contenido": "Cambiar ubicación y secuencia al mismo tiempo impide atribuir toda diferencia a una sola decisión. Definir primero la respuesta y el factor; comparar base y alternativa con idénticos caso, semilla y versiones. Repetir pares en distintas semillas explora sensibilidad. Contrastar normal, pico y falla caracteriza escenarios distintos y no equivale a demostrar el efecto aislado de una política.",
        "fuentes": ["nist"],
    },
    {
        "id": "seguridad",
        "titulo": "Falla y recuperación responsable",
        "contenido": "Una operación digital puede medir el costo de una avería sin exponer personas. En una maqueta, la revisión previa, las capacidades visibles, la separación de circulación y el retiro de un recurso inseguro deben verificarse localmente. Reparar en la simulación sólo modifica un estado lógico: no autoriza tocar motores, transportadores, tableros ni montacargas reales.",
        "fuentes": ["osha"],
    },
]

COMPARACION = {
    "unidad": "Par de ejecuciones completas o cerradas explícitamente, ambas del mismo caso y semilla.",
    "igualar": [
        "caso",
        "semilla",
        "version_motor",
        "version_caso",
        "version_dataset",
        "version_guia",
    ],
    "control": "Guardar primero la secuencia base. En la alternativa modificar una sola regla deliberada: ubicación, prioridad de pedidos o respuesta a la falla. Mantener las restantes reglas y condiciones; si cambian varias, describir la alternativa como un paquete de cambios.",
    "replicas": "Usar, por ejemplo, semillas 11, 42 y 73 como tres pares base–alternativa; tres pares son una práctica docente, no una garantía de precisión estadística. Mantener todas las réplicas, incluso las que empeoran.",
    "calculos": [
        "Cambio absoluto = indicador_alternativa − indicador_base, conservando unidad y sentido de mejora.",
        "Cambio relativo [%] = 100 × (alternativa − base) / base sólo si base es distinta de cero; si es cero, informar el cambio absoluto y relativo no definido.",
        "Para OTIF expresado en porcentaje, la resta es una diferencia en puntos porcentuales; no llamarla porcentaje de mejora.",
        "Presentar cada par y la media de diferencias. Si se propone una inferencia estadística, justificar el número de réplicas, variabilidad y supuestos antes de usarla.",
    ],
    "entre_variantes": "cd-normal y cd-falla comparten pedidos; cd-pico agrega un pedido y modifica promesas. La misma semilla mantiene el origen aleatorio, pero no iguala la carga ni las condiciones. Mostrar diferencias de demanda y recurso; llamar a esta comparación análisis de escenarios, sin atribuir causalidad exclusiva a ABC o prioridad.",
    "versiones": "Una partida histórica conserva sus versiones. No mezclar resultados de reglas distintas como si fueran el mismo experimento ni reinterpretar una evidencia antigua con un motor actualizado.",
}

SEGURIDAD_MAQUETA = [
    "Antes de reservar la práctica presencial, el responsable confirma disponibilidad, manuales, capacidades, inducción y evaluación local de riesgos; la existencia en catálogo no acredita instalación ni funcionamiento.",
    "Delimitar circulación y zonas de manipulación; retirar obstáculos y mantener salidas y accesos despejados. No representar un muelle con un borde abierto sin protección.",
    "Comprobar estabilidad de estanterías y cargas simbólicas y respetar las capacidades reales indicadas por el fabricante; las 12, 10 y 8 unidades del caso son parámetros digitales, no límites certificados de la maqueta.",
    "Utilizar cargas didácticas ligeras y condiciones ergonómicas revisadas por el responsable. Evitar alcanzar, atrapar o mover elementos en funcionamiento.",
    "Revisar cableado, alimentación, parada y protecciones antes de activar automatización. Una falla visible exige detener, aislar y avisar; no puentear sensores ni enclavamientos.",
    "Toda intervención en motores, cintas o energía corresponde al personal autorizado y al procedimiento local de aislamiento. La acción digital reparar no es una instrucción de mantenimiento físico.",
    "No operar montacargas, drones, robots ni maquinaria real por haber completado el simulador. Se requiere autorización, formación, supervisión y condiciones específicas de cada recurso.",
    "Registrar incidencias y cerrar la práctica con recuento, orden del puesto y confirmación del responsable. No publicar imágenes, datos personales o información empresarial sin autorización.",
]

LIMITES = [
    "Modelo docente de acciones secuenciales con reloj discreto; no simula colisiones, ergonomía cuantitativa, movimientos concurrentes ni dinámica física de montacargas.",
    "Productos, lotes, pedidos, avería, capacidades y tiempos son sintéticos. No son compras, inventarios ni compromisos reales de UPEC o de empresas colaboradoras.",
    "Las cajas normalizadas miden 30 × 20 × 15 cm; el peso es informativo. El modelo no sustituye comprobaciones de resistencia, compatibilidad, temperatura, caducidad o sustancias peligrosas de un almacén real.",
    "Las clases ABC y el ahorro de picking son reglas declaradas del modelo. No se calcula una clasificación económica ni se demuestra una solución óptima de ubicación.",
    "El puntaje automático orienta la práctica y no registra aprobación académica, competencia profesional ni certificación de seguridad.",
    "Los resultados sólo sustentan conclusiones sobre los casos, versiones, decisiones y semillas utilizados; una aplicación industrial requiere datos autorizados, calibración y validación independiente.",
    "La rúbrica docente y los entregables se aplican por el docente; esta guía no crea automáticamente evaluaciones, matrículas, reservas ni sesiones presenciales.",
]


def _criterio(clave, titulo, puntos, evidencia, completo, parcial, inicial):
    return {
        "id": clave,
        "titulo": titulo,
        "puntos": puntos,
        "evidencia": evidencia,
        "niveles": [
            {"nivel": "logrado", "fraccion": 1, "descriptor": completo},
            {"nivel": "en desarrollo", "fraccion": 0.5, "descriptor": parcial},
            {"nivel": "inicial", "fraccion": 0, "descriptor": inicial},
        ],
    }


RUBRICA_DOCENTE = {
    "total": 100,
    "nota": "Evaluación docente de evidencias, distinta del puntaje automático del servidor. El docente asigna 0%, 50% o 100% de los puntos de cada criterio usando los descriptores; no se guarda como calificación oficial desde el simulador.",
    "criterios": [
        _criterio(
            "trazabilidad",
            "Trazabilidad y procedimiento",
            20,
            "Bitácora y reconstrucción de un lote y un pedido de principio a fin.",
            "Reconstruye identidad, estados y secuencia completa; justifica inspección, rechazo y FIFO con eventos.",
            "Reconstruye parcialmente la secuencia, pero falta enlazar algún estado o justificar una decisión.",
            "No aporta una secuencia verificable o confunde SKU, lote y pedido.",
        ),
        _criterio(
            "balance",
            "Conciliación de materiales",
            20,
            "Tabla por SKU con entrada y todos los estados finales, incluidos rechazo y pendientes.",
            "Todos los SKU concilian sin doble conteo; localiza y explica las discrepancias encontradas durante el proceso.",
            "La tabla existe, pero omite un estado o no explica cómo se verificó un saldo.",
            "No presenta conciliación o encubre diferencias ajustando cantidades sin evidencia.",
        ),
        _criterio(
            "experimento",
            "Comparación reproducible",
            20,
            "Identificadores de dos partidas por semilla, versiones, factor cambiado y secuencias.",
            "Los pares igualan condiciones, conservan réplicas completas y separan cambio de política de cambio de escenario.",
            "Se puede repetir una parte, pero faltan versiones, control de un factor o réplicas declaradas.",
            "Compara condiciones distintas como causalidad aislada o no permite reproducir el análisis.",
        ),
        _criterio(
            "analitica",
            "Indicadores e interpretación",
            20,
            "Tabla de servicio, tiempo, cobertura, errores y balance con unidades y denominadores.",
            "Recalcula correctamente al menos cinco indicadores y distingue porcentajes, puntos porcentuales y cambios absolutos.",
            "Interpreta parte de los indicadores, con alguna unidad, denominador o diferencia mal declarados.",
            "No puede verificar los indicadores o selecciona sólo resultados favorables.",
        ),
        _criterio(
            "decision",
            "Decisión y límites",
            10,
            "Recomendación de una página vinculada a resultados y restricciones.",
            "Propone una decisión factible, reconoce compensaciones y limita la conclusión al modelo observado.",
            "Propone una mejora plausible sin discutir una restricción o un resultado adverso.",
            "Presenta una recomendación incompatible con los datos o afirma eficacia industrial no comprobada.",
        ),
        _criterio(
            "comunicacion",
            "Comunicación y seguridad",
            10,
            "Informe legible, fuentes y lista de comprobación presencial cuando corresponda.",
            "Organiza tablas y gráficos con títulos, fuentes y unidades; distingue simulación de operación física y documenta la seguridad aplicable.",
            "El informe es comprensible, pero falta fuente, unidad o comprobación de seguridad relevante.",
            "No comunica evidencias utilizables o equipara una acción digital con autorización de maquinaria.",
        ),
    ],
}

CASOS = {
    "cd-normal": {
        "titulo": "Centro de distribución · Operación normal",
        "resumen": "Recibir e inspeccionar seis lotes, ubicar conformes y completar tres pedidos sin perder trazabilidad.",
        "contexto": "Un turno didáctico atiende productos tecnológicos de tres SKU. Las capacidades y las promesas están publicadas; la calidad se descubre por inspección. La tarea consiste en transformar entradas en pedidos completos, preservando el material rechazado y el saldo disponible.",
        "duracion_minutos": 120,
        "distribucion_tiempo": [
            ("Preparación y diseño", 20),
            ("Ejecución base", 25),
            ("Ejecución alternativa", 25),
            ("Réplicas y conciliación", 25),
            ("Análisis y comunicación", 25),
        ],
        "hipotesis": {
            "enunciado": "Asignar cada SKU a la zona de su clase ABC reduce minutos de picking frente a una ubicación alternativa factible, sin empeorar el balance de inventario.",
            "factor": "Regla de ubicación; no cambiar al mismo tiempo el orden de pedidos.",
            "respuesta": "Minutos simulados, pedidos a tiempo, cobertura y conciliación por SKU.",
            "control": "Mismos caso, semilla, versiones, inspección, rechazo y secuencia de pedidos.",
            "refutacion": "Aceptar una mejora pequeña, nula o adversa si el tiempo total queda dominado por otras acciones; mostrar todos los pares.",
        },
        "foco": "Comprobar primero el proceso completo y luego una modificación de ubicación controlada.",
        "preguntas": [
            "¿Qué evento demuestra que el daño se separó sin desaparecer del balance?",
            "¿Por qué una ubicación ABC favorable no demuestra que el diseño del almacén sea óptimo?",
            "¿Cómo cambia la conclusión si disminuye picking, pero el último despacho ocurre después de su promesa?",
        ],
    },
    "cd-pico": {
        "titulo": "Centro de distribución · Pico de demanda",
        "resumen": "Atender cuatro pedidos con las mismas existencias y promesas ajustadas; justificar prioridades y cobertura.",
        "contexto": "Una cuarta solicitud aumenta la carga sin añadir existencias ni capacidad. Las promesas de los cuatro pedidos son 120, 140, 160 y 180 minutos. El participante debe distinguir inventario suficiente de capacidad temporal, y no mejorar el indicador excluyendo pedidos pendientes.",
        "duracion_minutos": 135,
        "distribucion_tiempo": [
            ("Preparación y diseño", 20),
            ("Ejecución base", 30),
            ("Ejecución alternativa", 30),
            ("Réplicas y conciliación", 30),
            ("Análisis y comunicación", 25),
        ],
        "hipotesis": {
            "enunciado": "Cambiar una secuencia de pedidos declarada por prioridad y promesa puede alterar OTIF bajo pico de demanda, aun cuando el número total despachado sea igual.",
            "factor": "Secuencia de pedidos; conservar la misma regla de ubicación y respuesta operativa.",
            "respuesta": "OTIF, pedidos despachados, pendientes y minutos del último despacho.",
            "control": "Dos ejecuciones cd-pico con misma semilla, versiones y ubicación; publicar ambas secuencias antes de compararlas.",
            "refutacion": "La secuencia no necesariamente mejora todos los pedidos ni el tiempo total; identificar quién gana o pierde y conservar resultados desfavorables.",
        },
        "foco": "Explicar las compensaciones entre prioridad, promesa, cobertura y carga de trabajo.",
        "preguntas": [
            "¿Por qué normal frente a pico no aísla el efecto de una regla de picking?",
            "¿Qué pedidos mejoran y cuáles empeoran al cambiar la secuencia?",
            "¿Puede crecer el número de unidades despachadas mientras baja OTIF? Sustenta con los denominadores del caso.",
        ],
    },
    "cd-falla": {
        "titulo": "Centro de distribución · Falla de recurso",
        "resumen": "Responder a la indisponibilidad temporal del montacargas y comparar reparación, espera y secuenciación segura.",
        "contexto": "El montacargas presenta una falla programada al minuto 30. El trabajo ya iniciado termina; la indisponibilidad afecta la siguiente ubicación. La recuperación natural tarda 30 minutos desde el disparo y la reparación digital consume 14 minutos. El caso conserva los tres pedidos de operación normal para estudiar recuperación sin añadir demanda.",
        "duracion_minutos": 150,
        "distribucion_tiempo": [
            ("Preparación y diseño", 25),
            ("Ejecución base", 30),
            ("Ejecución alternativa", 30),
            ("Réplicas y conciliación", 35),
            ("Análisis y comunicación", 30),
        ],
        "hipotesis": {
            "enunciado": "Reparar al detectar la avería puede reducir el tiempo de cierre respecto a esperar recuperación, pero su ventaja depende del trabajo restante y de las acciones factibles durante la espera.",
            "factor": "Respuesta a la avería: reparación frente a recuperación natural; no cambiar ubicación ni orden de pedidos en el mismo par.",
            "respuesta": "Minutos simulados, OTIF, cobertura, errores y secuencia de recuperación.",
            "control": "Mismo cd-falla, semilla, versiones y decisiones anteriores al disparo; anotar el instante real en que el reloj alcanza el evento.",
            "refutacion": "No afirmar que reparar siempre mejora: si la recuperación está próxima o queda trabajo alternativo, el costo de 14 minutos puede no compensarse.",
        },
        "foco": "Planificar continuidad y recuperación sin sacrificar trazabilidad ni seguridad física.",
        "preguntas": [
            "¿Qué diferencia hay entre el minuto programado de falla y el instante en que una acción cruza ese umbral?",
            "¿Qué tareas pueden continuar con inventario ya ubicado y cuáles dependen del recurso averiado?",
            "¿En qué condición esperar podría ser preferible a reparar, y por qué esta decisión digital no autoriza mantenimiento real?",
        ],
    },
}


def _campo(campo, tipo, unidad, descripcion):
    return {"campo": campo, "tipo": tipo, "unidad": unidad, "descripcion": descripcion}


def _tabla(ruta, descripcion, visibilidad, filas):
    return {
        "ruta": ruta,
        "descripcion": descripcion,
        "visibilidad": visibilidad,
        "campos": [_campo(*fila) for fila in filas],
    }


DICCIONARIO_DATOS = {
    "productos": _tabla(
        "observacion.datos.productos",
        "Catálogo sintético de tres SKU; los pesos son informativos, no una restricción de cálculo.",
        "Disponible desde el inicio; CSV público de entradas.",
        [
            (
                "sku",
                "texto",
                "identificador",
                "SKU-A, SKU-B o SKU-C; clave para unir lotes y líneas de pedido.",
            ),
            (
                "nombre",
                "texto",
                "—",
                "Denominación didáctica del producto, no marca ni equipo adquirido.",
            ),
            (
                "clase",
                "texto",
                "A/B/C",
                "Clase declarada que orienta ubicación; no calculada a partir de ventas reales.",
            ),
            ("unidad", "texto", "caja", "Unidad de cantidad: una caja normalizada."),
            (
                "peso_kg",
                "entero",
                "kg/caja",
                "Peso informativo por caja; no valida capacidad de carga física.",
            ),
            (
                "dimensiones_cm",
                "lista de enteros",
                "cm",
                "Largo, ancho y alto de cada caja normalizada: 30, 20 y 15.",
            ),
        ],
    ),
    "lotes": _tabla(
        "observacion.datos.lotes",
        "Seis lotes: dos por SKU, con 12, 10 y 8 cajas de entrada total respectivamente.",
        "La observación oculta defectuosas hasta inspeccionar el lote; el resto es visible. No usar el estado interno como dataset público.",
        [
            (
                "id",
                "texto",
                "identificador",
                "Identidad estable del lote para decisiones y eventos.",
            ),
            (
                "sku",
                "texto",
                "identificador",
                "Producto al que pertenecen las cajas del lote.",
            ),
            (
                "lote",
                "entero",
                "orden FIFO",
                "Antigüedad relativa 1 o 2 dentro de cada SKU; 1 se consume antes que 2.",
            ),
            (
                "cantidad",
                "entero",
                "cajas",
                "Cajas de llegada; no cambia durante la partida.",
            ),
            (
                "defectuosas",
                "entero; campo condicional",
                "cajas",
                "Sólo aparece después de inspeccionar; una carga contiene una o dos cajas defectuosas.",
            ),
            (
                "inspeccionado",
                "booleano",
                "—",
                "Indica si la calidad del lote ya fue comprobada en la práctica.",
            ),
            (
                "recibidas",
                "entero",
                "cajas",
                "Cantidad conforme recibida acumulada; no es el saldo actual.",
            ),
            (
                "rechazadas",
                "entero",
                "cajas",
                "Cantidad segregada mediante rechazo parcial y excluida del stock utilizable.",
            ),
            (
                "saldo",
                "entero",
                "cajas",
                "Existencias conformes disponibles del lote, antes o después de ubicar; disminuyen con picking.",
            ),
            (
                "ubicacion",
                "texto o nulo",
                "identificador",
                "Referencia a ubicación; nulo mientras el lote no se haya ubicado.",
            ),
            (
                "estado",
                "texto",
                "—",
                "Pendiente, inspeccionado, recibido, ubicado o agotado; es una etiqueta derivada de las cantidades.",
            ),
        ],
    ),
    "ubicaciones": _tabla(
        "observacion.datos.ubicaciones",
        "Tres zonas con capacidad en cajas normalizadas; ocupación calculada a partir del saldo de sus lotes.",
        "Disponible desde el inicio; CSV público de entradas con ocupación inicial cero.",
        [
            ("id", "texto", "identificador", "Clave de unión con lotes.ubicacion."),
            ("codigo", "texto", "—", "Código visible A-01, B-01 o C-01."),
            ("zona", "texto", "—", "Nombre de la zona de acceso o reserva."),
            (
                "clase",
                "texto",
                "A/B/C",
                "Clase preferente; no impide ubicar otro SKU si existe capacidad.",
            ),
            (
                "capacidad",
                "entero",
                "cajas",
                "Máximo de cajas: 12, 10 u 8; no es número de pallets ni capacidad real certificada.",
            ),
            (
                "posicion",
                "lista de números",
                "m didácticos",
                "Coordenadas x,y,z del plano; distancia operacional Manhattan en x,z.",
            ),
            (
                "ocupadas",
                "entero",
                "cajas",
                "Suma del saldo aún disponible de los lotes ubicados; se libera al preparar unidades.",
            ),
        ],
    ),
    "pedidos": _tabla(
        "observacion.datos.pedidos",
        "Tres pedidos en normal y falla; pico agrega un cuarto y modifica promesas.",
        "Disponible desde el inicio; CSV público con líneas como JSON dentro de una celda.",
        [
            (
                "id",
                "texto",
                "identificador",
                "Clave estable del pedido para preparar, embalar y despachar.",
            ),
            (
                "prioridad",
                "texto",
                "alta/media/baja",
                "Atributo para justificar la secuencia; no elimina pedidos del denominador.",
            ),
            (
                "prometido_min",
                "entero",
                "min",
                "Último minuto simulado para considerar puntual el despacho completo.",
            ),
            (
                "lineas",
                "lista de objetos",
                "—",
                "Requerimientos por SKU y cantidades preparadas para este pedido.",
            ),
            (
                "lineas[].sku",
                "texto",
                "identificador",
                "Producto requerido; no admite sustituciones implícitas.",
            ),
            ("lineas[].cantidad", "entero", "cajas", "Cantidad solicitada de ese SKU."),
            (
                "lineas[].preparadas",
                "entero",
                "cajas",
                "Cantidad acumulada asignada a la línea; persiste después de despachar como evidencia.",
            ),
            (
                "lineas[].lotes",
                "lista de textos",
                "identificadores",
                "Un ID por caja preparada, en orden de consumo FIFO; puede repetirse un lote.",
            ),
            (
                "estado",
                "texto",
                "—",
                "Pendiente, en preparación, preparado, embalado o despachado.",
            ),
            (
                "embalado",
                "booleano",
                "—",
                "Sólo verdadero después de completar todas las líneas y confirmar embalaje.",
            ),
            (
                "despachado_en",
                "entero o nulo",
                "min",
                "Minuto de salida completa; nulo si aún no se ha despachado.",
            ),
            (
                "otif",
                "booleano",
                "—",
                "Verdadero sólo con despacho completo antes o en prometido_min.",
            ),
        ],
    ),
    "recursos": _tabla(
        "observacion.datos.recursos",
        "Montacargas lógico y puesto de embalaje; no equipos físicos conectados.",
        "Programación de falla conocida al inicio; los eventos registran únicamente sucesos ya ocurridos. CSV público de entradas.",
        [
            (
                "id",
                "texto",
                "identificador",
                "Identidad del montacargas o puesto de embalaje.",
            ),
            ("nombre", "texto", "—", "Nombre didáctico del recurso."),
            (
                "estado",
                "texto",
                "operativo/averiado",
                "Disponibilidad lógica; una falla bloquea siguientes ubicaciones, no revierte la acción iniciada.",
            ),
            (
                "fallo_en",
                "entero o nulo",
                "min",
                "Minuto 30 en cd-falla; nulo en casos sin avería.",
            ),
            (
                "recuperacion_en",
                "entero o nulo",
                "min",
                "Recuperación prevista: inicialmente minuto 60 en cd-falla; "
                "al reparar cambia al final de la reparación. Nulo donde no aplica.",
            ),
            (
                "fallo_activado",
                "booleano",
                "—",
                "Confirma que el reloj alcanzó el umbral y registró la falla.",
            ),
            (
                "reparado",
                "booleano",
                "—",
                "Marca la reparación digital elegida; recuperación natural no equivale a reparación.",
            ),
        ],
    ),
    "eventos": _tabla(
        "observacion.datos.eventos",
        "Bitácora de operaciones y cambios de disponibilidad ya ocurridos; el orden es reproducible desde decisiones.",
        "Visible sólo dentro de una partida accesible al usuario; la evidencia final permite conservarla.",
        [
            (
                "id",
                "texto",
                "identificador",
                "Secuencia evento-1, evento-2... dentro de la partida.",
            ),
            (
                "tipo",
                "texto",
                "—",
                "Recepción, inspección, rechazo, ubicación, picking, embalaje, despacho, falla, recuperación u otro evento declarado.",
            ),
            (
                "minuto",
                "entero",
                "min",
                "Instante simulado del evento; falla y recuperación natural conservan el umbral programado.",
            ),
            (
                "objeto",
                "texto",
                "identificador",
                "ID de lote, pedido o recurso implicado.",
            ),
            (
                "descripcion",
                "texto",
                "—",
                "Explicación del cambio observado; no contiene una orden de maquinaria real.",
            ),
        ],
    ),
    "balances": _tabla(
        "observacion.datos.balances",
        "Partición exhaustiva del material por SKU; una caja ocupa un único estado contable.",
        "Visible durante la partida y repetido en el resultado final; no revela daño aún no inspeccionado.",
        [
            ("sku", "texto", "identificador", "Producto conciliado."),
            (
                "entrada",
                "entero",
                "cajas",
                "Suma fija de cantidad de los dos lotes del SKU.",
            ),
            (
                "pendiente",
                "entero",
                "cajas",
                "Material aún no recibido ni rechazado, excluyendo el daño ya identificado pendiente de rechazo.",
            ),
            (
                "inspeccion_rechazo",
                "entero",
                "cajas",
                "Defectuosas ya detectadas por inspección pero aún no segregadas; no sumarlas también en pendiente.",
            ),
            (
                "disponible",
                "entero",
                "cajas",
                "Saldo conforme aún no preparado, ubicado o pendiente de ubicación.",
            ),
            (
                "preparado",
                "entero",
                "cajas",
                "Cajas asignadas a pedidos todavía no despachados; incluye embalados.",
            ),
            (
                "despachado",
                "entero",
                "cajas",
                "Cajas de pedidos cuya salida completa ya se confirmó.",
            ),
            (
                "rechazado",
                "entero",
                "cajas",
                "Defectuosas segregadas, conservadas en la trazabilidad y fuera de inventario utilizable.",
            ),
            (
                "diferencia",
                "entero",
                "cajas",
                "Entrada menos la suma de los seis estados; debe ser cero.",
            ),
        ],
    ),
    "resultados": _tabla(
        "resultado",
        "Evaluación calculada por el servidor de una partida terminada; mantiene condiciones, política de referencia y saldos.",
        "Sólo al terminar o cerrar explícitamente una partida accesible. No es un dataset público de resultados de otros usuarios.",
        [
            (
                "puntaje",
                "numero",
                "puntos / 100",
                "Suma limitada a 0–100 de cumplimiento, eficiencia y precisión; distinta de la rúbrica docente.",
            ),
            (
                "componentes",
                "objeto",
                "puntos",
                "Contribuciones: cumplimiento hasta 60, eficiencia hasta 25 y precisión hasta 15.",
            ),
            (
                "componentes.cumplimiento",
                "numero",
                "puntos / 60",
                "60 × pedidos OTIF / total de pedidos comprometidos.",
            ),
            (
                "componentes.eficiencia",
                "numero",
                "puntos / 25",
                "25 × min(1, tiempo_referencia / max(1, tiempo_propio)) × despachados / total.",
            ),
            (
                "componentes.precision",
                "numero",
                "puntos / 15",
                "15 × max(0, 1 − intentos inválidos / 10).",
            ),
            (
                "rubrica",
                "texto",
                "—",
                "Descripción del puntaje didáctico; no sustituye la evaluación docente de evidencias.",
            ),
            (
                "criterios",
                "lista de objetos",
                "—",
                "Peso, puntos y fórmula de cada componente automático.",
            ),
            (
                "criterios[].id",
                "texto",
                "identificador",
                "Cumplimiento, eficiencia o precisión.",
            ),
            (
                "criterios[].peso",
                "entero",
                "puntos",
                "Máximo del componente: 60, 25 o 15.",
            ),
            (
                "criterios[].puntos",
                "numero",
                "puntos",
                "Contribución conseguida en el componente.",
            ),
            (
                "criterios[].formula",
                "texto",
                "—",
                "Fórmula explicativa verificable con métricas del cierre.",
            ),
            (
                "metricas",
                "objeto",
                "unidades por campo",
                "Resumen numérico para comprobar puntaje y comparación.",
            ),
            (
                "metricas.otif",
                "numero",
                "%",
                "Porcentaje de pedidos completos despachados a tiempo entre todos los comprometidos.",
            ),
            ("metricas.minutos", "entero", "min", "Tiempo simulado de cierre."),
            (
                "metricas.errores",
                "entero",
                "intentos",
                "Intentos operativos inválidos; no es porcentaje de daño ni diferencia de inventario.",
            ),
            (
                "metricas.distancia_m",
                "entero",
                "m didácticos",
                "Recorrido acumulado de manipulación sobre el plano, ida y regreso.",
            ),
            (
                "metricas.completados",
                "entero",
                "pedidos",
                "Pedidos completos despachados.",
            ),
            (
                "metricas.diferencia_balance",
                "entero",
                "cajas",
                "Suma de diferencias absolutas por SKU; debe ser cero.",
            ),
            (
                "metricas.total_pedidos",
                "entero",
                "pedidos",
                "Todos los comprometidos, incluidos pendientes.",
            ),
            (
                "metricas.unidades_despachadas",
                "entero",
                "cajas",
                "Cantidad total de cajas en pedidos despachados.",
            ),
            (
                "kpis",
                "lista de objetos",
                "unidades por fila",
                "Indicadores con identidad estable; las unidades no se agregan entre métricas distintas.",
            ),
            (
                "kpis[].id",
                "texto",
                "identificador",
                "Clave de la métrica; permite unir resultados comparables.",
            ),
            ("kpis[].titulo", "texto", "—", "Nombre legible de la métrica."),
            ("kpis[].valor", "numero", "según unidad", "Valor numérico del indicador."),
            (
                "kpis[].unidad",
                "texto",
                "—",
                "Unidad declarada: %, min, intentos, m, pedidos o cajas.",
            ),
            (
                "balances",
                "lista de objetos",
                "cajas",
                "Filas por SKU descritas en el dataset balances; conserva todos los saldos finales.",
            ),
            (
                "pedidos",
                "lista de objetos",
                "—",
                "Filas finales con el esquema del dataset pedidos, incluidas las no completadas.",
            ),
            (
                "referencia",
                "objeto",
                "—",
                "Política factible publicada para el mismo caso y semilla; incluye decisiones exactas, no un óptimo probado.",
            ),
            (
                "referencia.nombre",
                "texto",
                "—",
                "Recepción completa, ABC, reparación inmediata y pedidos por promesa/ID.",
            ),
            (
                "referencia.nota",
                "texto",
                "—",
                "Declara que la política no demuestra optimalidad ni desempeño real.",
            ),
            (
                "referencia.minutos",
                "entero",
                "min",
                "Tiempo de la política factible reproducible.",
            ),
            (
                "referencia.distancia_m",
                "entero",
                "m didácticos",
                "Recorrido de manipulación de la referencia.",
            ),
            (
                "referencia.otif",
                "numero",
                "%",
                "OTIF de la política de referencia, con su denominador completo.",
            ),
            (
                "referencia.completados",
                "entero",
                "pedidos",
                "Pedidos despachados por la referencia.",
            ),
            (
                "referencia.errores",
                "entero",
                "intentos",
                "Intentos inválidos de la política de referencia.",
            ),
            (
                "referencia.decisiones",
                "lista de objetos",
                "—",
                "Secuencia {accion, objeto} para repetir la referencia; no comandos de hardware.",
            ),
            (
                "motivo_cierre",
                "texto",
                "—",
                "Objetivos completados, cierre anticipado o límite de decisiones.",
            ),
            (
                "pendientes",
                "entero",
                "pedidos",
                "Total comprometidos menos completos despachados; no ocultarlos del reporte.",
            ),
            (
                "tiempo_objetivo",
                "entero",
                "min",
                "Tiempo de la referencia; es orientación didáctica, no compromiso industrial.",
            ),
            ("minutos", "entero", "min", "Tiempo final, igual a metricas.minutos."),
            (
                "errores",
                "entero",
                "intentos",
                "Intentos inválidos finales, iguales a metricas.errores.",
            ),
            (
                "familia",
                "texto",
                "identificador",
                "centro-distribucion: misma familia metodológica para las tres variantes.",
            ),
            (
                "caso",
                "texto",
                "identificador",
                "cd-normal, cd-pico o cd-falla; debe conservarse para interpretar condiciones.",
            ),
            (
                "semilla",
                "entero",
                "0–2147483647",
                "Origen aleatorio reproducible del daño; misma semilla no iguala la carga entre variantes.",
            ),
            (
                "version_motor",
                "texto",
                "versión",
                "Versión de reglas y cálculo de decisiones.",
            ),
            ("version_caso", "texto", "versión", "Versión del escenario."),
            (
                "version_dataset",
                "texto",
                "versión",
                "Versión de catálogo, entradas y estructura de datos.",
            ),
            (
                "nota_referencia",
                "texto",
                "—",
                "Limitación explícita de la referencia factible utilizada para puntuar.",
            ),
        ],
    ),
}


def _objetivos(caso):
    return [
        {
            "id": "o1",
            "verbo": "Reconstruir",
            "criterio": "Las seis etapas con identidad de lote, SKU y pedido conservada en eventos.",
            "evidencia": "Diagrama y bitácora de un lote y un pedido completo.",
        },
        {
            "id": "o2",
            "verbo": "Conciliar",
            "criterio": "El 100% de los SKU sin doble conteo, incluyendo rechazo, pendientes y despachados.",
            "evidencia": "Tabla de balance por SKU con diferencia igual a cero.",
        },
        {
            "id": "o3",
            "verbo": "Operar",
            "criterio": "Ubicación sin exceder capacidad, picking FIFO y embalaje sólo de pedidos completos; documentar cada intento inválido.",
            "evidencia": "Secuencia del servidor y análisis de errores, incluso si hubo cierre parcial.",
        },
        {
            "id": "o4",
            "verbo": "Comparar",
            "criterio": "Base y alternativa del mismo caso en tres pares de semillas; declarar el factor modificado y todas las versiones.",
            "evidencia": "Matriz de réplicas con diferencias y limitaciones.",
        },
        {
            "id": "o5",
            "verbo": "Interpretar",
            "criterio": "Al menos cinco indicadores con unidad, denominador y sentido de mejora, sin equiparar puntaje con nota académica.",
            "evidencia": "Tabla de indicadores y recomendación sustentada para "
            + caso
            + ".",
        },
    ]


def _procedimiento(caso):
    ficha = CASOS[caso]
    return [
        {
            "orden": 1,
            "titulo": "Preparar el experimento",
            "pasos": [
                "Leer reglas, seis etapas, hipótesis y límites; acordar qué acción cambia y qué permanece fijo.",
                "Anotar caso, semilla y versiones antes de operar; guardar la política base y la alternativa.",
                "Revisar productos, capacidades, líneas y promesas. No usar información de daño que la inspección no haya revelado.",
            ],
            "evidencia": "Ficha de experimento y política predefinida.",
        },
        {
            "orden": 2,
            "titulo": "Controlar y recibir",
            "pasos": [
                "Inspeccionar cada lote; separar digitalmente la parte dañada y recibir únicamente conformes.",
                "Conciliar entrada, rechazo y conformes por SKU; comprobar que todos los lotes tengan origen y estado.",
            ],
            "evidencia": "Eventos de inspección, rechazo y recepción; balance inicial.",
        },
        {
            "orden": 3,
            "titulo": "Asignar ubicaciones",
            "pasos": [
                "Aplicar la regla de ubicación declarada respetando 12, 10 y 8 unidades de capacidad.",
                "Comprobar ocupación después de cada ubicación; anotar los eventos de recurso y su efecto sobre la siguiente operación.",
            ],
            "evidencia": "Mapa de SKU por ubicación y ocupación conciliada.",
        },
        {
            "orden": 4,
            "titulo": "Preparar pedidos",
            "pasos": [
                "Seguir la secuencia declarada, seleccionar el SKU correcto y preparar una unidad por acción del lote FIFO disponible.",
                "Verificar cantidad preparada por línea; registrar intentos inválidos y su efecto en tiempo y precisión.",
            ],
            "evidencia": "Tabla pedido–SKU–lote y cronología de picking.",
        },
        {
            "orden": 5,
            "titulo": "Embalar y despachar",
            "pasos": [
                "Confirmar embalaje sólo con todas las líneas completas y luego despachar.",
                "Cotejar minuto de salida con promesa; no retirar pendientes del denominador. Si se cierra anticipadamente, declarar qué pedidos quedan sin completar.",
            ],
            "evidencia": "Pedidos completos, instantes de salida, promesas y pendientes.",
        },
        {
            "orden": 6,
            "titulo": "Comprobar cierre",
            "pasos": [
                "Conciliar todos los SKU incluyendo existencias, preparado, rechazo y despachado.",
                "Consultar resultado y exportar evidencia de una partida terminada; conservar versiones, semilla e historial. La interfaz de consulta histórica no modifica una partida antigua.",
            ],
            "evidencia": "Evidencia final reproducible y conciliación sin diferencias.",
        },
        {
            "orden": 7,
            "titulo": "Ejecutar la alternativa y réplicas",
            "pasos": [
                ficha["foco"],
                "Crear una nueva partida del mismo caso y semilla; modificar únicamente el factor acordado, sin editar un resultado anterior.",
                "Repetir base y alternativa para las demás semillas. Registrar también fallos, cierres parciales y resultados que contradigan la hipótesis.",
            ],
            "evidencia": "Tres pares completos con condiciones y secuencias verificables.",
        },
        {
            "orden": 8,
            "titulo": "Analizar y defender",
            "pasos": [
                "Calcular indicadores y cambios con unidades, denominadores y valores no definidos cuando corresponda.",
                "Separar comparación de políticas de comparación entre normal, pico y falla; explicar restricciones y compensaciones.",
                "Entregar una recomendación que pueda refutarse con los datos y aplicar la rúbrica docente a las evidencias.",
            ],
            "evidencia": "Informe con tablas, gráficos, decisión y límites.",
        },
    ]


def guia(caso="cd-normal"):
    """Devuelve una ficha nueva y serializable; un caso desconocido no se sustituye.

    No lee la base ni toca partidas. Se exige versión de guía junto a la evidencia
    para que posteriores revisiones pedagógicas no reinterpreten informes previos.
    """
    if type(caso) is not str or caso not in CASOS:
        raise ValueError("Caso de centro de distribución desconocido.")
    ficha = CASOS[caso]
    return deepcopy(
        {
            "caso": caso,
            "version_guia": GUIA_VERSION,
            "titulo": ficha["titulo"],
            "resumen": ficha["resumen"],
            "contexto": ficha["contexto"],
            "area": {
                "codigo": "LOG-ALMACEN",
                "nombre": "Almacenamiento e intralogística inteligente",
            },
            "asignaturas": ASIGNATURAS,
            "duracion_minutos": ficha["duracion_minutos"],
            "distribucion_tiempo": [
                {"actividad": nombre, "minutos": minutos}
                for nombre, minutos in ficha["distribucion_tiempo"]
            ],
            "objetivos": _objetivos(caso),
            "prerrequisitos": [
                "Distinguir SKU, lote, ubicación y pedido; sumar cantidades enteras y calcular proporciones.",
                "Interpretar capacidad, FIFO, promesa de entrega y balance de materiales.",
                "Leer tablas y registrar decisiones en una hoja de cálculo o documento; no se requiere programación ni software de pago.",
                "Para guardar partidas se utiliza una cuenta autorizada. La actividad presencial exige inducción y recursos verificados por el responsable.",
            ],
            "teoria": TEORIA,
            "hipotesis": ficha["hipotesis"],
            "etapas": ETAPAS,
            "procedimiento": _procedimiento(caso),
            "comparacion": COMPARACION,
            "rubrica_docente": RUBRICA_DOCENTE,
            "entregables": [
                "Ficha de hipótesis, variable modificada, política base, alternativa, caso, semillas y versiones.",
                "Diagrama de las seis etapas con un lote y un pedido reconstruidos desde eventos.",
                "Tabla de balance por SKU y ocupación por ubicación, sin duplicar unidades embaladas.",
                "Matriz de tres pares de ejecuciones con servicio, cobertura, tiempo, errores y diferencias.",
                "Evidencias finales y secuencias que permiten repetir el cálculo, incluidas partidas cerradas parcialmente.",
                "Informe de decisión con gráficos legibles, tabla de respaldo, limitaciones, fuentes y reflexión de seguridad.",
            ],
            "preguntas_reflexion": ficha["preguntas"]
            + [
                "¿Qué dato real faltaría medir para calibrar este modelo contra una maqueta o una operación empresarial?",
                "¿Qué cambiaría en la conclusión al actualizar reglas o datos y por qué debe conservarse la versión de cada evidencia?",
            ],
            "seguridad_maqueta": SEGURIDAD_MAQUETA,
            "limites": LIMITES,
            "diccionario_datos": DICCIONARIO_DATOS,
            "fuentes": list(FUENTES.values()),
        }
    )
