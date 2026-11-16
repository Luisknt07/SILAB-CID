"""Programas originales LOG-FOR, completos para revisión pedagógica.

No constituyen convocatorias, matrícula, equipos instalados ni certificación.
Datos sintéticos y contratos compatibles con CURSO/EDICION/MODULOS.
Las siete propuestas de eventos se conservan; no se reemplazan por estos cursos.
"""

from copy import deepcopy
from functools import partial
from html import escape
from io import BytesIO
from textwrap import dedent
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .estandar import deber, evaluacion, guia_pdf, lectura

VERSION = "2026.10.12"
FUENTES = {
    "traza": ("GS1: Traceability", "https://www.gs1.org/standards/traceability"),
    "epcis": ("GS1: EPCIS and CBV", "https://www.gs1.org/standards/epcis"),
    "scor": (
        "ASCM: SCOR Digital Standard",
        "https://www.ascm.org/corporate-solutions/standards-tools/scor-ds/",
    ),
    "ia": (
        "NIST: AI Risk Management Framework",
        "https://www.nist.gov/itl/ai-risk-management-framework",
    ),
    "seguridad": (
        "OSHA: Warehousing hazards and solutions",
        "https://www.osha.gov/warehousing/hazards-solutions",
    ),
}
RUBRICA = """Datos y supuestos (25 puntos): diccionario, unidades y originales conservados.
Método y cálculos (30 puntos): reglas, resultados repetibles y controles consistentes.
Interpretación (25 puntos): decisiones vinculadas a datos y restricciones, sin inventar causas.
Comunicación (20 puntos): versión, pruebas, entregables legibles y límites explícitos.
Total: 100 puntos. Rúbrica pedagógica: no sustituye reglamento ni aprobación institucional.
Las entregas requieren revisión docente; el quiz no califica el proyecto automáticamente."""
DATOS = {
    "trazabilidad-qr": {
        "eventos.csv": """evento_id,lote,sku,tipo,origen,destino,cantidad_ud,minuto
E01,L-A,CAJA,recepcion,PROV,RECEP,100,0
E02,L-A,CAJA,ubicacion,RECEP,A01,100,8
E03,L-A,CAJA,picking,A01,PACK,30,20
E04,L-A,CAJA,despacho,PACK,CLI-A,30,28
E05,L-A,CAJA,picking,A01,PACK,20,35
E06,L-A,CAJA,despacho,PACK,CLI-B,20,43
E07,L-B,CAJA,recepcion,PROV,RECEP,60,45
E08,L-B,CAJA,ubicacion,RECEP,A02,60,52
""",
        "eventos_auditar.csv": """evento_id,lote,sku,tipo,origen,destino,cantidad_ud,minuto
E01,L-A,CAJA,recepcion,PROV,RECEP,100,0
E02,L-A,CAJA,ubicacion,RECEP,A01,100,8
E03,L-A,CAJA,picking,A01,PACK,30,20
E04,L-A,CAJA,despacho,PACK,CLI-A,30,28
E04,L-A,CAJA,despacho,PACK,CLI-A,30,28
E05,L-A,CAJA,picking,A01,PACK,90,35
E06,L-A,CAJA,despacho,PACK,CLI-B,90,34
""",
    },
    "logistica-circular": {
        "retornos.csv": """lote,retorno_ud,reutilizable_ud,reparable_ud,reciclable_ud,rechazo_ud
R01,100,40,30,20,10
R02,80,30,20,20,10
R03,120,50,30,30,10
""",
        "alternativas.csv": """alternativa,distancia_km,carga_kg,costo_usd,factor_sintetico_kgco2e_km
A_individual,120,300,90,0.8
B_consolidada,80,300,75,0.9
C_electrica,95,300,100,0.3
""",
    },
    "analitica-operativa": {
        "pedidos.csv": """pedido,solicitado_ud,entregado_ud,compromiso_min,entrega_min
P01,10,10,60,50
P02,20,20,60,75
P03,15,12,90,80
P04,5,5,90,95
P05,25,25,120,110
P06,10,10,120,115
""",
        "conteos.csv": """ubicacion,sku,sistema_ud,fisico_ud
A01,CAJA,100,100
A02,FUNDA,80,78
B01,CINTA,30,30
B02,ETIQUETA,50,50
""",
        "demanda.csv": """periodo,demanda_ud,pronostico_base_ud,pronostico_alternativo_ud
1,20,20,20
2,22,20,20
3,18,22,21
4,24,18,20
5,26,24,21
6,30,26,23
""",
    },
    "automatizacion-logistica": {
        "eventos_sensor.csv": """evento_id,segundo,sensor,valor,unidad
S01,0,presencia,1,bool
S02,1,presencia,1,bool
S03,2,presencia,0,bool
S04,8,presencia,1,bool
S05,9,presencia,0,bool
S06,15,temperatura,31,C
S07,16,temperatura,34,C
S08,17,temperatura,35,C
S09,18,temperatura,33,C
""",
        "estaciones.csv": """estacion,tiempo_ciclo_s,disponibilidad_fraccion,capacidad_buffer_ud
recepcion,20,1.0,10
inspeccion,30,0.9,5
embalaje,24,1.0,8
""",
    },
    "proyectos-replicables": {
        "ensayos.csv": """par,semilla,politica,tiempo_min,errores_ud,pedidos_total,otif_ud
1,101,base,50,4,20,14
1,101,alternativa,44,2,20,17
2,202,base,60,3,20,13
2,202,alternativa,55,2,20,15
3,303,base,55,5,20,12
3,303,alternativa,48,2,20,16
""",
        "pruebas.csv": """prueba,entrada,esperado,observado
T01,cantidad_cero,rechazar,rechazar
T02,cantidad_negativa,rechazar,rechazar
T03,pedido_valido,aceptar,aceptar
T04,repetir_evento,no_duplicar,duplicado
T05,usuario_sin_permiso,denegar,denegar
""",
    },
    "transformacion-digital": {
        "procesos.csv": """proceso,casos_mes,tiempo_base_min,tiempo_meta_min,error_base_fraccion,error_meta_fraccion
recepcion,100,12,9,0.08,0.03
picking,200,8,6,0.06,0.02
expediente,40,30,25,0.10,0.05
""",
        "iniciativas.csv": """iniciativa,costo_inicial_usd,costo_mensual_usd,valor_hora_sintetico_usd,ahorro_horas_mes
A_captura,300,20,6,20
B_tablero,200,10,6,12
C_robot,5000,150,6,35
""",
        "expediente.csv": """documento,referencia,bultos,peso_kg,moneda,valor
factura,EXP-01,10,120,USD,1000
packing,EXP-01,12,120,USD,1000
transporte,EXP-01,10,125,USD,1000
""",
    },
    "preparacion-segura": {
        "inspeccion.csv": """recurso,estado,guarda,energia_aislada,responsable_confirmado
CINTA-A,disponible,si,no,si
BRAZO-B,bloqueado,no,no,si
PC-C,disponible,no_aplica,no_aplica,si
DRON-D,pendiente,no_aplica,no,no
""",
        "incidencias.csv": """incidencia,instante_min,tipo,estado_inicial,accion_registrada
I01,12,atasco,en_marcha,detener_y_avisar
I02,18,lectura_duplicada,simulacion,marcar_y_conservar_original
I03,24,pieza_faltante,cierre,registrar_y_restringir_recurso
""",
    },
}


def bloque(titulo, lectura_texto, actividad, contraste, preguntas):
    return {
        "titulo": titulo,
        "lectura": dedent(lectura_texto).strip(),
        "actividad": actividad,
        "contraste": contraste,
        "preguntas": preguntas,
    }


# Preguntas originales: enunciado, respuesta correcta, dos distractores y explicación.
TEMARIOS = {}

TEMARIOS["trazabilidad-qr"] = [
    bloque(
        "Identificación y contrato de eventos",
        """
        Una etiqueta identifica; un historial explica qué ocurrió. CAJA es un SKU y L-A un lote sintético,
        no un GTIN comercial. QR es soporte de lectura y no garantía de exactitud. Conserva identidad del
        objeto mientras cambia de ubicación. GS1 distingue eventos relevantes y datos que los describen;
        nuestro CSV educativo no es EPCIS ni acredita conformidad con ese estándar.

        Define evento_id único, lote/SKU válidos, origen/destino diferentes, cantidad positiva y minuto
        relativo al inicio. El flujo es PROV→RECEP→A01→PACK→CLI-A/CLI-B. Sólo proveedor y clientes quedan
        fuera del sistema. Una transferencia interna no es una nueva recepción. Escribe reglas de captura
        antes de diseñar etiquetas: clave legible a simple vista, referencia estable y permisos de consulta.

        Diccionario mínimo: evento_id identifica la operación; lote agrupa unidades; SKU identifica producto;
        tipo describe recepción/ubicación/picking/despacho; origen y destino describen posiciones; cantidad_ud
        son unidades enteras; minuto es tiempo relativo no negativo. No mezcles fecha de captura con fecha
        efectiva. Si no existe lector, transcribe la misma clave y prueba las mismas reglas con hoja de cálculo.
    """,
        "Dibuja el flujo, crea diccionario de los ocho campos de eventos.csv y dos etiquetas de texto. Entrega tres reglas con ejemplos válidos e inválidos y explica qué permanece estable al reubicar una caja.",
        "Ocho eventos únicos, dos lotes y un SKU. E04 despacha 30 unidades de PACK a CLI-A; la identidad L-A permanece. Se distinguen movimientos internos de cruces de frontera.",
        [
            (
                "¿Qué demuestra por sí solo un QR?",
                "Una clave codificada",
                "Inventario correcto",
                "Certificación GS1",
                "Historial y controles se verifican aparte.",
            ),
            (
                "¿Qué clave no puede repetirse?",
                "evento_id",
                "SKU",
                "Tipo de operación",
                "Un objeto puede tener muchos eventos distintos.",
            ),
            (
                "Al pasar de A01 a PACK, el lote…",
                "Conserva su identidad",
                "Se crea otra vez",
                "Se convierte en un cliente",
                "La ubicación pertenece al evento.",
            ),
            (
                "¿Este CSV acredita EPCIS?",
                "No, requiere validación del estándar",
                "Sí por tener tiempos",
                "Sí por usar QR",
                "El contrato del caso es educativo y propio.",
            ),
        ],
    ),
    bloque(
        "Balance y reconstrucción por ubicación",
        """
        Todas las posiciones internas comienzan vacías. En cada movimiento resta del origen interno y suma
        al destino interno. Recibir aumenta el total; despachar lo reduce. Verifica disponibilidad antes de
        modificar ambas posiciones: guardar sólo una mitad rompe conservación. Reconstruye por evento y
        luego agrega; un saldo final positivo puede ocultar una salida intermedia imposible.

        Balance global: inicial+recepciones−despachos=final. Para L-A: 0+100−50=50; para L-B: 0+60−0=60.
        A01 conserva 50, A02 conserva 60 y PACK queda vacío. CLI-A recibe 30 y CLI-B 20. No sumes unidades en
        todas las posiciones atravesadas como si fueran inventario nuevo. Una reejecución de E04 debe
        reconocer la clave y evitar aplicar un segundo despacho.

        Construye columnas saldo_previo, entrada, salida y saldo_posterior por lote/ubicación. Entrega
        barras de saldos junto con tabla y fórmulas. Los balances son del dataset; no son existencias de UPEC.
    """,
        "Procesa eventos.csv. Entrega saldos por lote/ubicación, balance global y consulta de clientes afectados por un retiro académico de L-A. Repite E04 y demuestra que los saldos no cambian.",
        "Recibidas 160, despachadas 50, saldo 110. L-A/A01=50; L-B/A02=60; PACK=0. Clientes L-A: CLI-A y CLI-B. Repetir E04 sin control produciría saldo ficticio 80.",
        [
            (
                "¿Cuál es el saldo interno?",
                "110",
                "160",
                "210",
                "160 recibidas menos 50 despachadas.",
            ),
            (
                "RECEP→A01…",
                "Conserva total interno",
                "Duplica la compra",
                "Crea stock nuevo",
                "Sólo cambia la ubicación.",
            ),
            (
                "Repetir E04 debe…",
                "Evitar un segundo efecto",
                "Restar otras 30",
                "Cambiar lote",
                "La clave controla idempotencia.",
            ),
            (
                "¿Qué clientes recibieron L-A?",
                "CLI-A y CLI-B",
                "Sólo CLI-A",
                "Ninguno",
                "Los despachos enlazan lote y destino.",
            ),
        ],
    ),
    bloque(
        "Auditoría y pruebas de integridad",
        """
        Conserva eventos_auditar.csv original. E04 se repite; E05 intenta retirar 90 de A01 cuando quedan 70;
        E06 aparece en minuto 34, antes del picking del 35, y pretende despachar sin saldo en PACK. Son tres
        fallos distintos: identidad, disponibilidad y causalidad temporal. Ordenar filas no los resuelve.

        Separa aceptados y rechazados con motivo. No reduzcas cantidades ni inventes recepciones para
        cuadrar un saldo. Una corrección referencia evento original, decisión, autor simbólico y efecto;
        si desconoces el dato verdadero, mantenlo pendiente. Diseña pruebas para duplicado, SKU desconocido,
        cantidad cero/negativa, saldo insuficiente y evento fuera de orden. Cada prueba declara esperado y
        observado. La evidencia incluye entradas, reglas, versión, saldos y límites de captura manual.
    """,
        "Produce aceptados.csv y rechazados.csv con motivo, seis pruebas y un informe con tres hallazgos distintos. Describe una corrección sin borrar procedencia ni sustituir silenciosamente el original.",
        "Tras E01–E04 una vez: 70 unidades en A01. E05 y E06 se rechazan; siete filas y seis claves distintas. Ninguna recepción ficticia cubre las 90 unidades.",
        [
            (
                "Tras E01–E04, A01 tiene…",
                "70",
                "40",
                "100",
                "100 ubicadas menos 30 retiradas.",
            ),
            (
                "¿Cómo tratar E05?",
                "Rechazar por saldo insuficiente",
                "Reducir a 70 sin registro",
                "Inventar recepción",
                "Se conserva el error original.",
            ),
            (
                "¿Qué falla en E06?",
                "Cronología y saldo",
                "Cliente secundario",
                "Minuto impar",
                "Despacha antes del picking y sin disponibilidad.",
            ),
            (
                "¿Qué permite repetir auditoría?",
                "Entradas, reglas, versión y pruebas",
                "Sólo una captura",
                "Sólo conclusión",
                "Otra persona debe reconstruir los saldos.",
            ),
        ],
    ),
]

TEMARIOS["logistica-circular"] = [
    bloque(
        "Retornos y destinos excluyentes",
        """
        Devolución no equivale a reutilización. Clasifica retornos de empaques en reutilizable, reparable,
        reciclable y rechazo. SCOR incluye flujo Return y actividades circulares; el caso adopta un registro
        propio para evitar contar una misma unidad dos veces. Los destinos son excluyentes y deben sumar
        lo recibido. Reparable significa trabajo pendiente, no recuperación demostrada.

        La frontera son empaques sintéticos, sin residuos peligrosos ni evaluación sanitaria. El dataset
        mide unidades; no conviertas a masa sin pesar o justificar una conversión. Define criterio de
        inspección, ubicación, actor simbólico y evidencia para cada destino. Registra retorno, clasificación,
        intervención y salida como etapas diferentes; una transferencia no aumenta entradas globales.
    """,
        "Audita retornos.csv, dibuja el flujo de cuatro destinos y calcula tasas sobre recibido. Explica qué recuperaciones son inmediatas y cuáles requieren intervención verificable.",
        "300 recibidas: 120 reutilizables 40 %,80 reparables 26,67 %,70 reciclables 23,33 %,30 rechazo 10 %. Recuperación inmediata 120, no 270.",
        [
            ("¿Cuántas se reciben?", "300", "270", "120", "100+80+120."),
            (
                "¿Cuántas son reutilizables inicialmente?",
                "120",
                "200",
                "270",
                "Reparables aún no están reparadas.",
            ),
            (
                "¿Qué evita doble conteo?",
                "Destinos excluyentes y balance",
                "Sumar transferencias",
                "Contar reparación como nueva compra",
                "Cada retorno se clasifica una vez.",
            ),
            (
                "¿Puede inferirse masa desde unidades?",
                "No sin peso o conversión",
                "Sí, una unidad es 1 kg",
                "Sí con porcentajes",
                "No se mezclan unidades de medida.",
            ),
        ],
    ),
    bloque(
        "Comparación ambiental y de costo",
        """
        alternativas.csv usa factores sintéticos, no mediciones ni factores oficiales. Compara igual carga
        y frontera. Emisión hipotética=distancia×factor; intensidad por tonelada entregada=emisión/0,3 t.
        No es intensidad por tonelada-km: ese denominador también incluiría distancia. Declara que faltan
        fabricación, infraestructura, retorno vacío y generación eléctrica real.

        A produce 96 kgCO2e, B produce 72 kgCO2e y C produce 28,5 kgCO2e bajo estos supuestos. Compara costo, capacidad y servicio: una ruta
        económica que incumple entregas no representa mejora aceptable. Conserva tabla y gráfico costo–emisión,
        unidades y supuestos. Estos cálculos no sirven como declaración ambiental comercial del laboratorio.
    """,
        "Calcula emisiones hipotéticas e intensidad por tonelada de A/B/C. Grafica costo–emisiones y decide con presupuestos 80 y 110 USD; documenta dos limitaciones y el servicio que falta comprobar.",
        "A: 96 kgCO2e y 320 kgCO2e/t; B: 72 kgCO2e y 240 kgCO2e/t; C: 28,5 kgCO2e y 95 kgCO2e/t. Con 80 USD sólo B es factible; con 110 USD, C minimiza la emisión hipotética y B cuesta menos.",
        [
            (
                "¿Cuál es la emisión de B?",
                "72 kgCO2e",
                "0,9 kgCO2e",
                "240 kgCO2e",
                "80×0,9.",
            ),
            ("300 kg equivalen a…", "0,3 t", "3 t", "300 t", "Se divide entre 1000."),
            ("¿Cuál cabe en 80 USD?", "B", "A y C", "Todas", "A: 90 / B: 75 / C: 100."),
            (
                "¿Qué permiten estos factores?",
                "Resultado hipotético limitado",
                "Huella certificada",
                "Emisiones reales de flota",
                "Son supuestos sintéticos.",
            ),
        ],
    ),
    bloque(
        "Piloto de reparación y seguimiento",
        """
        Diseña un piloto con período, línea base, unidad y criterio de rechazo. Si reparas 60 de las 80
        reparables y 20 pasan a rechazo, finalizas con 180 reutilizadas,70 reciclables y 50 rechazadas.
        No agregues 60 al total 300: reparación cambia destino, no crea nuevas entradas.

        Distingue indicadores de proceso, como tiempo de inspección, y de resultado, como unidades que
        volvieron al uso. Reducir rechazo aparente moviéndolo a reparables no demuestra mejora. Conserva
        evidencia de intervención y verificación; la etiqueta sola no demuestra recuperación. Define
        condición de suspensión si aparecen riesgos o clasificación incierta y derivación a responsable.
    """,
        "Construye seguimiento de 60 reparadas/20 rechazadas, recalcula balance y diseña piloto de cuatro semanas con dos indicadores de proceso, uno de resultado y regla de suspensión.",
        "180+70+50=300. Reutilización final 60 %. La intervención debe comprobarse y no presentarse como realizada sólo por figurar en el plan.",
        [
            ("¿Cuántas vuelven al uso?", "180", "240", "300", "120+60."),
            ("¿Cuál es rechazo final?", "50", "30", "20", "30+20."),
            (
                "Más reparables sin reparación significa…",
                "Trabajo pendiente",
                "Recuperación certificada",
                "Cero residuos",
                "Clasificar no demuestra resultado.",
            ),
            (
                "¿Qué conserva el piloto?",
                "Línea base, unidades y evidencia",
                "Sólo porcentaje",
                "Sólo fotos",
                "El resultado necesita comparación.",
            ),
        ],
    ),
]

TEMARIOS["analitica-operativa"] = [
    bloque(
        "Calidad de datos y definición de indicadores",
        """
        Cada fila de pedidos.csv es un pedido, no una línea ni una persona. Completo significa entregado≥solicitado;
        puntual significa entrega≤compromiso; OTIF (entrega completa y a tiempo) exige ambas condiciones en el mismo pedido. Mantén el conjunto
        comprometido del corte como denominador: excluir pendientes mejora artificialmente servicio. No promedies
        porcentajes diarios sin ponderar por número de pedidos.

        Declara nivel de fila, unidad, período y tratamiento de faltantes. Conserva columnas completo, puntual y
        OTIF con fórmulas visibles. Fecha faltante se clasifica pendiente de dato, no minuto cero. Para conteos,
        exactitud por posición=posiciones sin diferencia/posiciones contadas; diferencia absoluta=suma de
        |físico−sistema|. Son indicadores distintos y no acreditan existencias no contadas. Guarda originales,
        diccionario, validaciones y copia de trabajo; las correcciones necesitan motivo y referencia.
    """,
        "Construye diccionario para pedidos.csv/conteos.csv. Calcula completo, puntual y OTIF por pedido, exactitud por posición y diferencia absoluta; entrega fórmulas y tablas de respaldo.",
        "Completos 5/6=83,33 %; puntuales 4/6=66,67 %; OTIF P01/P05/P06=3/6=50 %. Posiciones exactas 3/4=75 %; diferencia absoluta 2 unidades en FUNDA.",
        [
            (
                "¿Qué pedido es puntual e incompleto?",
                "P03",
                "P02",
                "P04",
                "Entrega 12 de 15 antes del compromiso.",
            ),
            (
                "¿Cuál es OTIF global?",
                "50 %",
                "66,67 %",
                "83,33 %",
                "Tres de seis cumplen ambas condiciones.",
            ),
            (
                "¿Cuál es exactitud por posición?",
                "75 %",
                "98 %",
                "100 %",
                "Tres de cuatro no tienen diferencia.",
            ),
            (
                "¿Para qué definir nivel de fila?",
                "Evitar dobles conteos",
                "Aumentar tamaño",
                "Ocultar faltantes",
                "Pedido y línea no son equivalentes.",
            ),
        ],
    ),
    bloque(
        "Tablero accesible y tratamiento de excepciones",
        """
        Diseña para una decisión: mejorar servicio sin ocultar faltantes. Muestra volumen, OTIF y unidades pendientes,
        además de tabla de incumplidos. P03 tiene faltante; P02/P04 son completos pero tardíos. Una media de entrega
        no distingue abastecimiento y secuenciación. No inventes la causa: formula hipótesis y el dato que falta.

        Usa barras para categorías, línea para períodos y dispersión para relaciones. Barras comienzan en cero;
        cada eje muestra unidad y escala. Agrega etiquetas/símbolos para que no dependa sólo de rojo/verde y ofrece
        tabla legible. Distingue dato observado, cálculo, interpretación e hipótesis. El tablero no realiza reservas
        ni cambia inventario. Conserva corte y reglas; un cambio de criterio requiere recalcular todas las salidas.
    """,
        "Crea tablero con tres indicadores, gráfico de cumplimiento y tabla de excepciones. Asigna una acción a P02/P03/P04 sin inventar causas y explica qué dato adicional permitiría comprobar cada hipótesis.",
        "Excepciones OTIF: P02/P03/P04. Faltante 3 unidades sólo P03. Retrasos P02=15 min y P04=5 min. El archivo no demuestra avería de máquina ni incumplimiento de proveedor.",
        [
            (
                "¿Cuántas unidades faltan?",
                "3",
                "15",
                "20",
                "P03 solicita 15 y recibe 12.",
            ),
            ("¿Cuánto se retrasa P02?", "15 min", "75 min", "60 min", "75−60."),
            (
                "¿Cuál es una hipótesis?",
                "El retraso podría deberse a congestión",
                "P02 llega en 75",
                "P03 entrega 12",
                "La causa no está registrada.",
            ),
            (
                "¿Qué acompaña gráfico accesible?",
                "Etiquetas, unidades y tabla",
                "Sólo colores",
                "Eje sin escala",
                "Se interpreta sin depender del color.",
            ),
        ],
    ),
    bloque(
        "Pronóstico y prueba temporal sin fuga de información",
        """
        Un pronóstico usa información disponible antes del período. Congela reglas y compara el mismo horizonte.
        demanda.csv contiene pronósticos sintéticos ya calculados. Evalúa sólo períodos 4–6; los anteriores son
        contexto, no parte del promedio final. Ajustar reiteradamente con el conjunto de prueba contamina la
        evaluación. Conserva variables, versión, fecha de corte y decisiones.

        Error absoluto=|demanda−pronóstico|. Error absoluto medio (MAE)=suma de errores absolutos/número de períodos. Sesgo firmado=media
        de pronóstico−demanda; negativo indica subestimación. El error porcentual absoluto medio (MAPE) divide por demanda y necesita tratamiento de
        ceros; MAE conserva unidades. Compara reglas simples antes de atribuir valor a IA. Tres períodos no demuestran
        superioridad universal ni autorizan compras automáticas. Diseña siguiente corte con datos posteriores sin
        usarlo antes para ajustar y declara incertidumbre, frecuencia y horizonte.
    """,
        "Calcula MAE/sesgo de base y alternativa en 4–6. Grafica demanda y pronósticos, selecciona la mejor para este corte y diseña el siguiente sin reutilizar prueba para ajuste.",
        "Base: errores 6, 2 y 4; MAE: 4 y sesgo: −4. Alternativa: errores 4, 5 y 7; MAE: 16/3≈5,33 y sesgo: −5,33. Base gana en este corte; ambas subestiman y la muestra es limitada.",
        [
            (
                "¿MAE base en 4–6?",
                "4 unidades",
                "2 unidades",
                "12 unidades",
                "(6+2+4)/3.",
            ),
            (
                "¿MAE alternativo?",
                "16/3 unidades",
                "3 unidades",
                "16 unidades",
                "(4+5+7)/3.",
            ),
            (
                "¿Qué significa sesgo negativo?",
                "Subestimación media",
                "Sobreestimación",
                "Cero error",
                "Pronóstico−demanda es negativo.",
            ),
            (
                "¿Qué es fuga temporal?",
                "Usar futuro para predecir pasado",
                "Conservar corte",
                "Comparar mismo horizonte",
                "La información no estaba disponible al decidir.",
            ),
        ],
    ),
]

TEMARIOS["automatizacion-logistica"] = [
    bloque(
        "Señales, estados y eventos derivados",
        """
        Presencia=1 en dos lecturas no significa dos cajas. Define regla: transición 0→1 inicia detección, con
        estado inicial 0. La secuencia 1,1,0,1,0 produce dos detecciones. Conserva señal cruda, regla y eventos
        derivados; si cambias filtrado, versiona el resultado sin borrar observaciones. Timestamp de captura y
        timestamp efectivo deben distinguirse si el sistema recibe datos demorados.

        Temperatura tiene otra unidad. Regla sintética: alerta después de dos lecturas consecutivas≥34 °C; se
        restablece por debajo de 34. Se activa en 17 y deja de cumplirse en 18. No es un umbral seguro de maquinaria
        ni una parada física. No observado no equivale a cero: perder conexión exige estado sin dato. Este curso
        procesa CSV y no controla actuadores. No requiere controlador lógico programable (PLC), robot ni servicio de IA instalado.
    """,
        "Transforma eventos_sensor.csv en detecciones y estados de alerta. Entrega tabla, diagrama y pruebas de lectura repetida, ausencia y reinicio; conserva unidades y originales.",
        "Dos detecciones de presencia en 0/8 s. Alerta en 17 s por 34 y 35 °C; 33 °C en 18 rompe condición. Contar cada 1 daría tres detecciones incorrectas.",
        [
            (
                "¿Cuántas detecciones hay?",
                "2",
                "3",
                "5",
                "Transiciones 0→1 con inicial 0.",
            ),
            (
                "¿Cuándo se activa alerta?",
                "17 s",
                "16 s",
                "15 s",
                "Se requieren dos lecturas≥34.",
            ),
            (
                "¿34 °C es especificación industrial?",
                "No, regla sintética",
                "Sí para todo equipo",
                "Sí por usar grados",
                "La seguridad exige validación local.",
            ),
            (
                "¿Por qué conservar señal cruda?",
                "Reconstruir el cálculo",
                "Duplicar cajas",
                "Evitar validación",
                "Separa observación y derivación.",
            ),
        ],
    ),
    bloque(
        "Capacidad, buffers y cuello de botella",
        """
        Capacidad nominal=3600/tiempo_ciclo_s. Capacidad aproximada efectiva=nominal×disponibilidad. En estaciones.csv
        resultan recepción 180, inspección 108 y embalaje 150 unidades/h. La inspección limita el flujo en serie;
        sumar capacidades de estaciones daría una salida imposible. Disponibilidad 0,9 es supuesto, no medición UPEC.

        Los buffers son espacios intermedios de espera; absorben fluctuaciones pero no generan capacidad. Liberación 120/h supera inspección 108/h en 12/h;
        en 30 min acumula aproximadamente 6 unidades, más que buffer 5 partiendo vacío. Este modelo fluido ignora
        variabilidad, discretización y otros bloqueos: no predice tiempo exacto. Entrada 108/h necesita margen para
        variabilidad; 90/h no acumula en media bajo supuestos. Un modelo de eventos y mediciones permiten contrastar.
        Propón mejora que preserve calidad, capacidad espacial y guardas; no escondas cola en otra ubicación.
    """,
        "Calcula capacidades nominales/efectivas y evalúa liberaciones 90/108/120 por hora. Estima cola a 30 min, identifica el cuello de botella y propón una mejora sin exceder buffer ni retirar guardas.",
        "Inspección nominal 120/h, efectiva 108/h. Entrada 120 acumula 6 en media hora: buffer 5 insuficiente. Aumentar buffer no cambia tasa de inspección.",
        [
            (
                "¿Cuál limita el flujo?",
                "Inspección",
                "Recepción",
                "Embalaje",
                "108/h es la menor efectiva.",
            ),
            ("¿Capacidad nominal inspección?", "120/h", "108/h", "30/h", "3600/30."),
            (
                "¿Cola aproximada en media hora?",
                "6 unidades",
                "12 unidades",
                "60 unidades",
                "(120−108)×0,5.",
            ),
            (
                "¿Más buffer aumenta tasa?",
                "No",
                "Sí, la duplica",
                "Elimina ciclo",
                "Permite acumular más, no procesar más.",
            ),
        ],
    ),
    bloque(
        "Contratos y pruebas de integración",
        """
        Separa adquisición, interpretación, simulación y actuadores. El contrato incluye identificador, tiempo,
        origen, unidad, valor, versión y calidad. Un dato vencido no debe presentarse como actual; una lectura
        repetida no genera nueva unidad. Diseña estados normal/sin dato/vencido y límites de almacenamiento.

        Ensaya duplicado, retraso, pérdida, reinicio y fuera de rango sobre copias del CSV. Cada prueba declara
        entrada, esperado y observado. Una futura maqueta exige además validación de interfaces, límites y
        autorización. La referencia OSHA orienta sobre guardas y control de energía en mantenimiento; no sustituye
        normativa ecuatoriana ni instrucciones locales. Un atasco se representa mediante evento sintético;
        no se ensaya metiendo manos, retirando guardas o ejecutando órdenes físicas desde este material.
    """,
        "Diseña contrato JSON de lectura, pantalla con tres estados y cinco pruebas de fallo. Explica qué validaciones faltan antes de conectar una maqueta y entrega tabla esperado/observado sin ejecutar actuadores.",
        "Debe impedir duplicar conteos y convertir señal ausente en cero. Resultado es prototipo documental y de análisis; no se declara control industrial ni parada segura instalada.",
        [
            (
                "¿Qué significa señal ausente?",
                "Dato desconocido",
                "Cero cajas seguro",
                "Equipo seguro",
                "Puede fallar comunicación.",
            ),
            (
                "¿Qué realiza este curso?",
                "Analiza datos sin actuadores",
                "Control certificado",
                "Vuelo real",
                "Alcance educativo verificable.",
            ),
            (
                "¿Qué necesita contrato?",
                "Tiempo, unidad, origen y versión",
                "Sólo color",
                "Sólo nombre de alumno",
                "Permite validar y reconstruir.",
            ),
            (
                "¿Cómo ensayar atasco?",
                "Evento sintético y decisión documentada",
                "Retirar guarda",
                "Introducir mano",
                "No requiere exposición física.",
            ),
        ],
    ),
]

TEMARIOS["proyectos-replicables"] = [
    bloque(
        "Hipótesis y comparación por pares",
        """
        Pregunta comprobable: ¿una política reduce tiempo y errores manteniendo servicio bajo las mismas entradas?
        Cada par de ensayos.csv comparte semilla entre base y alternativa. Comparar normal con pico cambia
        entrada y decisión simultáneamente, impidiendo atribuir mejora. Tres pares son aprendizaje, no prueba
        de eficacia general ni de significación estadística no calculada.

        Conserva versión de motor/caso/dataset, semilla, decisiones y denominador. Define antes qué resultado
        refutaría hipótesis y qué restricciones permanecen. Puntaje de simulador resume reglas propias; rúbrica
        docente evalúa método y evidencia. Reducción porcentual usa tiempo base del mismo par, no el de otro.
        Diferencia pareada preserva comparación: 50−44=6,60−55=5,55−48=7 min. Entrega tabla y gráfico por pares,
        sin extrapolar a instalaciones industriales no calibradas.
    """,
        "Escribe hipótesis/protocolo y calcula diferencias por par de tiempo, errores y OTIF. Fija criterios antes de interpretar y explica límites de tres semillas.",
        "Reducción tiempo 6/5/7 min: media 6. Errores 2/1/3: media 2. OTIF base 39/60=65 %, alternativa 48/60=80 %. Mejora circunscrita a estos pares.",
        [
            ("¿Reducción media tiempo?", "6 min", "18 min", "3 min", "(6+5+7)/3."),
            ("¿OTIF alternativo global?", "80 %", "65 %", "48 %", "48 de 60."),
            (
                "¿Para qué compartir semilla?",
                "Conservar entradas comparables",
                "Garantizar victoria",
                "Calibrar equipo físico",
                "Reduce diferencias ajenas a la decisión.",
            ),
            (
                "¿Tres pares prueban superioridad universal?",
                "No",
                "Sí si todos mejoran",
                "Sí con gráfico",
                "Muestra y escenarios limitados.",
            ),
        ],
    ),
    bloque(
        "Pruebas y paquete de reproducción",
        """
        Una demostración favorable muestra que algo puede funcionar; pruebas buscan fallos y límites.
        pruebas.csv tiene cinco comprobaciones: cuatro coinciden, pero T04 duplica evento en vez de conservar
        efecto único. No informes 100 % ni cambies esperado para ocultarlo. Documenta entrada, pasos, impacto,
        observado y corrección propuesta; una propuesta no es una corrección verificada.

        El paquete reproducible incluye README, originales, parámetros, decisiones, versión, salidas,
        pruebas y límites. Usa rutas relativas y diccionario. Excluye claves, información personal y bases
        operativas. Otra persona debe repetir la corrida bajo igual versión. Para T04 la regresión repite
        mismo identificador y comprueba un único efecto, no sólo un mensaje bonito en pantalla.
    """,
        "Audita pruebas.csv, redacta defecto T04 y regresión. Diseña paquete reproducible con estructura, parámetros y tabla de resultados. No marques resuelto sin repetir.",
        "Cuatro de cinco conformes=80 %. T04 falla. La prueba debe conservar un efecto con ID repetido; no se cambia esperado a duplicado.",
        [
            ("¿Tasa de conformidad?", "80 %", "100 %", "20 %", "Cuatro de cinco."),
            (
                "¿Qué muestra T04?",
                "Duplicación no deseada",
                "Éxito",
                "Sin resultado",
                "Esperado difiere de observado.",
            ),
            (
                "¿Qué conserva un defecto?",
                "Entrada, pasos, esperado y observado",
                "Sólo título",
                "Sólo culpable",
                "Debe permitir repetición.",
            ),
            (
                "¿Qué se excluye de paquete público?",
                "Secretos y datos reales personales",
                "Diccionario",
                "Versión",
                "Se usa información sintética o autorizada.",
            ),
        ],
    ),
    bloque(
        "Comunicación técnica y revisión",
        """
        Explica problema, método, resultados y límites. Presenta base/alternativa con misma escala, unidad y
        horizonte. Menor tiempo puede ocultar incumplimiento; acompáñalo con servicio y errores. Una recomendación
        vincula un dato con una restricción. No presenta puntaje como validación física o evaluación industrial.

        Prepara ficha de una página, guion de cinco minutos y anexo reproducible. Declara T04 y el alcance de
        las tres semillas. El siguiente ensayo puede incorporar demanda pico o fallo de recurso por pares,
        conservando versión y controles. Si no ocurrió revisión externa, indícala pendiente; no inventes
        evaluadores, empresas o convenios. Registra observación recibida, cambio propuesto y comprobación,
        sin confundir opinión con mejora demostrada.
    """,
        "Entrega ficha y guion con los tres pares, T04 y siguiente ensayo. Aplica los cuatro criterios de rúbrica a tu propia evidencia y registra una mejora verificable; revisión por terceros sólo si realmente ocurre.",
        "Conclusión válida limita mejora a los pares y reconoce fallo T04. Incluye datos/decisiones/versión/límites; no afirma conexión física ni validación externa.",
        [
            (
                "¿Qué acompaña menor tiempo?",
                "Servicio, errores y restricciones",
                "Sólo puntaje",
                "Promesa sin datos",
                "No debe sacrificar otros resultados.",
            ),
            (
                "¿Qué sostiene recomendación?",
                "Evidencia ligada a restricción",
                "Imagen",
                "Nombre de tecnología",
                "Debe ser contrastable.",
            ),
            (
                "¿Siguiente ensayo válido?",
                "Demanda pico por pares",
                "Cambiar todo sin registro",
                "Borrar base",
                "Amplía escenarios conservando comparación.",
            ),
            (
                "¿Cómo describir revisión no realizada?",
                "Pendiente",
                "Aprobada internacionalmente",
                "Sustituye pruebas",
                "No se inventa evidencia.",
            ),
        ],
    ),
]

TEMARIOS["transformacion-digital"] = [
    bloque(
        "Mapa de procesos y beneficios medibles",
        """
        Digitalizar exige usuarios, entradas, pasos y decisiones claros. procesos.csv define volumen mensual
        y tiempo por caso. Ahorro potencial=casos×(base−meta). Diferencia de tasas×casos estima errores evitables.
        La meta es hipótesis, no resultado observado ni ahorro monetario automático. No contabilices como
        servicio ejecutado lo que sólo es planificación.

        Distingue maestros y transacciones. SKU/ubicaciones/permisos describen entidades reutilizables;
        recepción/reserva/despacho registran hechos. Una actualización no recrea maestros ni reescribe historial.
        Define propietario de dato, alta/cambio, acceso, versión y retención. Cada proceso incluye excepciones y
        alternativa manual cuando el servicio falla. El mapa relaciona proceso con una necesidad real, no con
        una tecnología elegida antes de comprenderla.
    """,
        "Modela los tres procesos, calcula minutos potenciales y errores evitables. Elige prioridad, separa maestros/transacciones y diseña alternativa manual trazable sin afirmar ahorro realizado.",
        "Recepción 300, picking 400, expediente 200 min: total 900 min=15 h/mes. Errores evitables 5/8/2, total 15 bajo metas sintéticas. No son resultados reales.",
        [
            (
                "¿Mayor ahorro calculado?",
                "Picking",
                "Recepción",
                "Expediente",
                "200×(8−6)=400 min.",
            ),
            (
                "¿Ahorro potencial total?",
                "900 min/mes",
                "900 h/mes",
                "400 min/mes",
                "300+400+200.",
            ),
            (
                "¿Meta equivale a resultado?",
                "No, falta medir",
                "Sí por estar en CSV",
                "Sí con aprobación",
                "Se separa estimación de observación.",
            ),
            (
                "¿Cuál es dato maestro?",
                "Catálogo SKU",
                "Despacho",
                "Asistencia",
                "Describe entidades reutilizables.",
            ),
        ],
    ),
    bloque(
        "Contratos modulares y consistencia documental",
        """
        Separa catálogo, operación y analítica. Cada pantalla consulta datos necesarios; no carga todas las
        evidencias y módulos al entrar. Contratos definen identificador, versión, campos y permisos. Vincular
        Unidades con Centros I+D requiere referencias y acuerdos sin duplicar propietarios de equipos o reservas.
        Compartir una institución no concede acceso a todo el dominio.

        expediente.csv es académico. Referencia/moneda/valor coinciden, pero packing declara 12 bultos frente 10,
        transporte 125 kg frente 120. Detectar discrepancia no permite decidir cuál documento es verdadero.
        Solicita comprobación y conserva originales. No transmite declaraciones ni fija obligaciones jurídicas.
        Un cambio aditivo describe campos opcionales y faltantes; cambiar significado/unidad exige versión y
        revisión de consumidores. Un error de integración debe conservar la transacción y mensaje interpretable.
    """,
        "Dibuja contratos de catálogo/reserva/ejecución/reportes separados de Centros I+D. Audita expediente.csv con campo, dato cotejado, observado y confirmación pendiente. Diseña evolución compatible del contrato.",
        "Discrepancias: bultos 10/12 y peso 120/125 kg. La referencia EXP-01, la moneda USD y el valor 1000 coinciden. El archivo no determina qué documento corregir; conserva originales y validación pendiente.",
        [
            (
                "¿Qué campos difieren?",
                "Bultos y peso",
                "Referencia y moneda",
                "Valor y moneda",
                "Los otros tres coinciden.",
            ),
            (
                "¿Cuál documento es correcto?",
                "No se sabe sin comprobar",
                "Siempre factura",
                "Siempre transporte",
                "Cotejar no demuestra verdad.",
            ),
            (
                "¿Cómo compartir equipo entre dominios?",
                "Referencia con propietario único",
                "Duplicar reservas",
                "Acceso global por nombre",
                "Colaborar no elimina límites operativos.",
            ),
            (
                "¿Qué exige revisar contrato?",
                "Cambiar significado o unidad",
                "Una errata visual",
                "Añadir descripción",
                "Los consumidores pueden interpretar distinto.",
            ),
        ],
    ),
    bloque(
        "Iniciativas, riesgos e implantación gradual",
        """
        iniciativas.csv usa valoración sintética 6 USD/h. Beneficio neto mensual=horas×valor−costo mensual;
        recuperación simple=inversión/beneficio positivo. Faltan descuentos, impuestos, capacitación y riesgos:
        no es cotización ni evaluación financiera definitiva. A produce 100 USD/mes y recuperación 3 meses;
        B: 62 y 3,23; C: 60 y 83,33. El robot no gana sólo por ahorrar más horas brutas.

        No sumes A+B si afectan el mismo trabajo. Verifica independencia, capacidad y servicio. Un piloto con
        IA conserva evaluación para el uso previsto, supervisión, acceso y retirada; NIST organiza gobierno,
        contexto, medición y gestión de riesgos. Unas respuestas atractivas no acreditan fiabilidad.
        Ruta: piloto aislado→medición→revisión→despliegue gradual→monitoreo/recuperación. Define criterio de
        aceptación y reversión, respaldos y cambios compatibles. Los contenidos se configuran sin recrear tablas.
    """,
        "Calcula beneficios/recuperación A/B/C y elige piloto con 600 USD. Entrega plan gradual, riesgos, métricas y prueba de recuperación. Incluye evaluación de IA opcional sin contratar servicios ni anunciar equipos adquiridos.",
        "A: beneficio neto de 100 USD/mes y recuperación en 3 meses; B: 62 USD/mes y aproximadamente 3,23 meses; C: 60 USD/mes y aproximadamente 83,33 meses. A+B requieren 500 USD de inversión inicial, pero sumar sus ahorros exige comprobar su independencia. C supera el presupuesto de 600 USD.",
        [
            (
                "¿Beneficio neto de A?",
                "100 USD/mes",
                "120 USD/mes",
                "300 USD/mes",
                "20×6−20.",
            ),
            (
                "¿Recuperación simple C?",
                "83,33 meses aprox.",
                "3 meses",
                "35 meses",
                "5000/(35×6−150).",
            ),
            (
                "¿Sumar ahorros A+B sin revisión?",
                "No, puede haber solapamiento",
                "Sí siempre",
                "Sí con tablero",
                "Pueden afectar el mismo trabajo.",
            ),
            (
                "¿Qué exige piloto IA?",
                "Evaluación, supervisión y retirada",
                "Sólo nombre de modelo",
                "Permisos ilimitados",
                "El riesgo se gestiona en su uso previsto.",
            ),
        ],
    ),
]

TEMARIOS["preparacion-segura"] = [
    bloque(
        "Modalidad y comprobación previa",
        """
        Distingue simulación, maqueta sin energía y automatizada. Una pantalla que responde no demuestra recurso
        físico disponible. Presencial requiere guía aprobada, reserva, responsable, participantes, inducción
        específica y condición del recurso. Inventario registrado no equivale a existencia ni seguridad verificadas.
        No conviertas inspección pendiente en sí para permitir avanzar.

        inspeccion.csv es ficticio: BRAZO-B está bloqueado sin guarda; DRON-D no tiene responsable confirmado.
        CINTA-A tiene guarda y responsable, pero el archivo no certifica condición segura ni aislamiento para
        intervención. PC-C es candidato a preparación virtual. La modalidad y evidencia deben aparecer explícitas;
        este curso no habilita uso de drones, robots o maquinaria. Diseña regla de no inicio y evidencia exigida,
        sin inventar nombres ni autorizaciones institucionales.
    """,
        "Clasifica recursos como excluido, pendiente o candidato virtual. Crea checklist con evidencia, rol validador y regla de no inicio; no firmes como técnico ni inventes autorización.",
        "BRAZO-B excluido; DRON-D pendiente/excluido hasta validación; PC-C candidato virtual; CINTA-A necesita evaluación específica. CSV no autoriza operación física.",
        [
            (
                "¿Qué implica bloqueo?",
                "No usar hasta resolver y autorizar",
                "Usar con aceptación del alumno",
                "Editar a disponible",
                "No se elimina restricción con texto.",
            ),
            (
                "¿Inventario prueba disponibilidad?",
                "No, falta comprobación",
                "Sí siempre",
                "Sí con foto",
                "Registro y verificación son distintos.",
            ),
            (
                "¿Qué modalidad usa PC-C sin actuadores?",
                "Virtual",
                "Vuelo",
                "Intervención industrial",
                "Tiene alcance físico diferente.",
            ),
            (
                "¿Responsable sin confirmar?",
                "Mantener inicio pendiente",
                "Inventar nombre",
                "Asignar cualquier alumno",
                "Se confirma institucionalmente.",
            ),
        ],
    ),
    bloque(
        "Incidencias y decisión de detener",
        """
        Registra hechos: instante, recurso, actividad, condición, acción inicial y comunicación. Separa observación
        e hipótesis; no atribuyas causas personales sin investigación. Error de datos y atasco físico requieren
        respuestas diferentes. Lectura duplicada se controla conservando original; atasco se detiene/comunica
        por procedimiento local. Cerrar navegador no aísla energía.

        OSHA destaca guardas y control de energía en mantenimiento; aquí es referencia técnica, no normativa
        ecuatoriana ni autorización de intervención. El estudiante observa, se aparta y comunica conforme al plan;
        personal autorizado interviene. Este material no enseña maniobras mecánicas ni certifica competencia.
        Con incidencias.csv redacta hechos y datos faltantes, sin simular que ocurrió una emergencia real.
    """,
        "Redacta fichas I01/I02/I03 con hechos, acciones y datos faltantes. Diseña preguntas de revisión y un mensaje breve al responsable por rol; no inventes causas ni publiques nombres reales.",
        "I01 detener_y_avisar no acredita aislamiento; I02 conserva original; I03 registra faltante y restricción. No ocultes incidencias para cerrar expediente.",
        [
            (
                "¿Cerrar navegador aísla energía?",
                "No",
                "Sí siempre",
                "Sí en maqueta pequeña",
                "Aislamiento es procedimiento autorizado.",
            ),
            (
                "¿Qué hacer con duplicado?",
                "Conservar original y registrar tratamiento",
                "Borrar historial",
                "Inventar lectura",
                "La corrección mantiene trazabilidad.",
            ),
            (
                "¿Qué se registra primero?",
                "Hechos y acción inicial",
                "Culpable supuesto",
                "Conclusión sin evidencia",
                "Se distingue observación de hipótesis.",
            ),
            (
                "¿Quién interviene atasco?",
                "Personal autorizado",
                "Cualquier participante",
                "Primero que lo vea",
                "El curso no concede habilitación.",
            ),
        ],
    ),
    bloque(
        "Cierre documental y seguimiento",
        """
        Registra lo realmente realizado: estado final, asistencia y consumos. Reserva no significa ejecución;
        cancelación no genera horas atendidas. Reprogramación conserva referencia sin duplicar uso. Un registro
        de ejecución observado puede recibir aclaraciones/evidencias, pero conserva asistencia y consumos ya cerrados.
        Cada corrección indica autor, motivo y procedencia.

        El acta identifica recursos, incidencias, pendientes y receptor cuando exista. En ejercicio virtual usa
        actores simbólicos y declara ausencia de uso físico. Imágenes no reemplazan registro y publicar personas
        exige permisos. Completar y revisar las actividades permite evaluar aprendizaje documental en su alcance; no reemplaza inducción
        específica vigente ni autorización técnica. Un reporte distingue real, simulado, planificado y cancelado.
    """,
        "Crea cierre académico virtual y otro cancelado con los incidentes del caso. Define evidencias y próximos responsables por rol; explica qué puede aclararse y qué datos cerrados se conservan.",
        "Cancelada conserva cero uso ejecutado; no se inventan asistentes/consumos. Aclaración referencia cierre. El informe declara naturaleza educativa sin habilitación técnica.",
        [
            (
                "¿Cancelada cuenta como ejecutada?",
                "No",
                "Sí con reserva",
                "Sí con fotos",
                "Reserva y ejecución son diferentes.",
            ),
            (
                "¿Qué se completa tras cierre?",
                "Aclaraciones conservando hechos operativos",
                "Consumos sin rastro",
                "Participantes para subir indicadores",
                "Documentación no reescribe operación.",
            ),
            (
                "¿Qué permite evaluar este programa?",
                "Aprendizaje documental",
                "Licencia de dron",
                "Todas las maquetas",
                "Autorización institucional es independiente.",
            ),
            (
                "¿Qué declara práctica virtual?",
                "Ausencia de uso físico real",
                "Horas industriales",
                "Equipos inspeccionados sin verificar",
                "Se distingue modalidad de evidencia.",
            ),
        ],
    ),
]


# Secuencia reproducible particular de cada módulo, anterior a la autoevaluación.
PROCEDIMIENTOS = {
    "trazabilidad-qr": (
        (
            "Abra eventos.csv sin modificarlo y anote cantidad de filas y nombres de campos; identifique fronteras PROV/CLI frente a posiciones internas.",
            "Construya diccionario con tipo, unidad, obligatoriedad y regla por campo. Explique por qué evento_id y lote tienen restricciones distintas.",
            "Diseñe etiquetas de L-A/L-B con clave visible y destino de consulta. No use códigos comerciales ajenos ni afirme que el dibujo es un QR escaneable.",
            "En una copia agregue cantidad cero, lote desconocido y origen igual a destino. Escriba mensaje esperado antes de validar; entregue tres rechazos motivados.",
        ),
        (
            "Cree tabla de saldos vacía por lote y posición. Recorra eventos por minuto conservando identidad y referencias.",
            "Antes de cada salida compruebe saldo origen; reste y sume como una sola operación. Para fronteras registre entrada/salida global separada.",
            "Conciliación: suma de saldos internos = recepciones menos despachos. Compruebe por lote y también por ubicación, no sólo el total.",
            "Repita E04 con idéntico ID. Registre esperado/observado y compare saldos antes/después; debe conservar un único efecto. Adjunte tabla de los dos destinos de L-A.",
        ),
        (
            "Compare siete filas con conjunto de claves únicas; marque la segunda E04 como duplicado sin eliminarla del archivo original.",
            "Reconstruya únicamente eventos aceptables. Compare cantidad pedida de E05 con saldo de A01; contraste minuto de E06 con disponibilidad en PACK.",
            "Produzca rechazados.csv con fila original, regla infringida y motivo; una corrección propuesta no entra en aceptados hasta verificarse.",
            "Entregue seis pruebas independientes y cuadre saldo de aceptados. Aceptación: no duplicar efectos, no permitir saldos negativos y conservar procedencia de cada rechazo.",
        ),
    ),
    "logistica-circular": (
        (
            "Abra retornos.csv y valide que los cuatro destinos suman retorno_ud en cada fila. No agregue transferencias como entradas nuevas.",
            "Sume por categoría y divida cada total entre el total de retorno_ud; mantenga unidades y denominador visibles.",
            "Construya barras apiladas por lote y una tabla total. Separe recuperación inmediata y material pendiente de reparación.",
            "Duplique una categoría en una copia para probar detección de sobreclasificación. Aceptación: saldo por lote cero, tasas totales 100 % y reparables sin afirmar recuperación.",
        ),
        (
            "Mantenga carga_kg constante y convierta a toneladas dividiendo entre 1000. Anote frontera y carácter sintético del factor.",
            "Añada emisión=distancia_km×factor y emisión_por_tonelada=emisión/(carga_kg/1000). No use etiqueta tonelada-km para esa segunda columna.",
            "Filtre costo≤presupuesto antes de elegir menor emisión. Compare presupuestos 80/110 con misma carga y restricciones de servicio pendientes.",
            "Repita con factor de C incrementado 25 % y explique si cambia elección; conserve caso base y nuevo supuesto. Aceptación: fórmulas trazables, unidades correctas y ninguna afirmación de huella real.",
        ),
        (
            "Cree registro de intervención con lote, unidades, condición previa, acción y verificación. Distribuya 60 reparadas sin superar reparables de cada lote.",
            "Traslade 60 de reparable a reutilizable y 20 a rechazo; no modifique retorno_ud ni añada una nueva recepción.",
            "Recalcule tasas y compruebe que el balance sigue 300. Declare que el escenario describe una hipótesis hasta existir evidencia de reparación.",
            "Diseñe cuatro cortes semanales con entrada, clasificación, recuperación verificada y pendiente. Aceptación: cada unidad tiene destino único y cada recuperación tiene prueba.",
        ),
    ),
    "analitica-operativa": (
        (
            "Compruebe pedido único, cantidades no negativas y tiempos relativos. Defina cómo tratar pedido abierto al corte o tiempo faltante antes de calcular.",
            "Añada completo=(entregado≥solicitado), puntual=(entrega≤compromiso) y OTIF=ambos. Calcule cada tasa como suma de verdaderos/número total de pedidos.",
            "En conteos calcule diferencia=físico−sistema, absoluta=|diferencia| y exacta=(diferencia=0). No confunda exactitud por posición con porcentaje de unidades.",
            "Introduzca una fecha faltante en copia y documente efecto del tratamiento elegido. Aceptación: seis pedidos en denominador base, fórmulas visibles y discrepancia de FUNDA detectada.",
        ),
        (
            "Cree tabla de excepciones con pedido, faltante=max(solicitado−entregado,0), retraso=max(entrega−compromiso,0) y condición incumplida.",
            "Diseñe volumen/OTIF/faltantes y gráfico de cumplimiento. Cada elemento indica corte, unidad y origen de datos.",
            "Escriba una hipótesis y un dato adicional requerido para cada excepción; no convierta correlación en causa.",
            "Revise legibilidad sin color y con zoom 200 %. Aceptación: tabla y gráfico coinciden, los tres pedidos problemáticos aparecen y ninguna causa no registrada se presenta como hecho.",
        ),
        (
            "Congele filas 4–6 como prueba. Escriba horizonte, columnas y regla antes de calcular; no seleccione después el corte más favorable.",
            "Para cada modelo calcule error=pronóstico−demanda y absoluto=|error|; obtenga media de ambas columnas sólo en prueba.",
            "Grafique demanda y ambos pronósticos en el mismo eje. Anote qué modelo gana y qué riesgo implica subestimación.",
            "Diseñe evaluación posterior con período 7 en adelante sin inventar datos observados. Aceptación: resultados base 4 y alternativo 16/3, misma ventana y ausencia de datos futuros en ajuste.",
        ),
    ),
    "automatizacion-logistica": (
        (
            "Separe series por sensor y unidad; ordene por segundo sin borrar datos originales. Defina estado inicial de presencia 0.",
            "Marque detección sólo si anterior 0 y actual 1. Guarde anterior/nuevo/evento derivado en una tabla de estados.",
            "Cuente consecutivos≥34 en temperatura; active alerta con dos y restablezca por debajo de 34. Declare que es regla sintética, no límite seguro.",
            "Ensaye lectura duplicada, dato perdido y reinicio en copias. Aceptación: dos detecciones y alerta en 17; un dato ausente queda desconocido, nunca cero automático.",
        ),
        (
            "Calcule nominal=3600/ciclo y efectiva=nominal×disponibilidad por estación; señale mínimo efectivo.",
            "Para entradas 90/108/120 calcule crecimiento=max(entrada−capacidad_limitante,0)×0,5 h; compare con el buffer de inspección de 5 unidades.",
            "Muestre tabla de escenarios y diferencie modelo fluido de simulación discreta. No afirme un minuto exacto de bloqueo industrial.",
            "Repita con disponibilidad de inspección 0,8 y preserve otras entradas. Aceptación: se detecta cuello de botella, buffer excedido en caso 120 y mejora no altera guardas ni calidad.",
        ),
        (
            "Escriba contrato con ID, tiempo efectivo/captura, sensor, valor, unidad, calidad y versión; defina error por campo inválido.",
            "Prepare cinco mensajes de fallo sobre datos sintéticos: duplicado, tardío, pérdida, reinicio y valor fuera de rango.",
            "Para cada mensaje registre estado de pantalla y decisión esperada sin accionar hardware. Distinga normal, sin dato y vencido.",
            "Añada matriz de requisitos pendientes para conexión física: interfaz, responsable, límites y prueba autorizada. Aceptación: ningún fallo genera control físico ni inventa una lectura válida.",
        ),
    ),
    "proyectos-replicables": (
        (
            "Agrupe por par y confirme exactamente una base y una alternativa con igual semilla/pedidos. Rechace par incompleto antes de comparar.",
            "Calcule diferencias base−alternativa para tiempo/errores; para OTIF use entregas válidas/pedidos, conservando denominador.",
            "Resuma diferencias pareadas y tasas globales ponderadas. Distinga porcentaje relativo y puntos porcentuales de servicio.",
            "Escriba hipótesis inicial y un resultado que la refutaría. Aceptación: tres pares completos, media de tiempo 6 min y mejora OTIF de 15 puntos porcentuales, con límites de muestra explícitos.",
        ),
        (
            "Compare esperado/observado de pruebas.csv y añada conforme por fila. Conserve T04 fallida en el denominador.",
            "Redacte defecto con entrada, pasos, impacto y evidencia; proponga deduplicación sin afirmar que fue implementada.",
            "Diseñe regresión que repita mismo ID y compruebe un efecto único; incluya datos y salida esperada en paquete.",
            "Pida a otra persona repetir sólo si hay revisión real; de lo contrario haga autoauditoría y declare pendiente. Aceptación: tasa 80 %, defecto no oculto y rutas de archivos relativas.",
        ),
        (
            "Prepare una página con pregunta, diseño por pares, resultados y límites. Anexe tabla y paquetes de datos.",
            "El guion muestra una corrida y contraste contra base sin cambiar escala ni esconder T04. Separe puntaje del simulador de rúbrica docente.",
            "Diseñe siguiente ensayo con escenario pico manteniendo semilla por par y criterio de no deterioro de servicio.",
            "Revise cada recomendación contra dato y restricción. Aceptación: mejora limitada al conjunto, defecto reconocido y ningún convenio/evaluador inventado.",
        ),
    ),
    "transformacion-digital": (
        (
            "Dibuje cada proceso con entrada, actor, decisión, salida y excepción; identifique dato maestro y transacción.",
            "Calcule ahorro_min=casos_mes×(base−meta) y errores_evitables=casos×(tasa_base−tasa_meta). Conserve unidad mensual.",
            "Ordene oportunidades por magnitud y riesgo; meta permanece hipótesis hasta medir después del piloto.",
            "Describa alternativa manual y reingreso con control de duplicados. Aceptación: total 900 min/15 errores potenciales, sin declararlos ejecutados ni monetizarlos sin supuesto.",
        ),
        (
            "Liste entidades y propietarios de catálogo/reserva/ejecución/reporte. Dibuje contratos y permisos separados de Centros I+D.",
            "Coteje expediente.csv por referencia, bultos, peso, moneda y valor; registre discrepancia con los documentos implicados.",
            "Mantenga dato verdadero pendiente cuando no se puede determinar. Diseñe solicitud de comprobación sin modificar original.",
            "Agregue un campo opcional versión 2 y explique compatibilidad con lectores anteriores. Aceptación: dos discrepancias, ninguna corrección adivinada y propietario único por equipo.",
        ),
        (
            "Añada beneficio_bruto=horas×valor_hora, neto=bruto−costo_mensual y recuperación=inicial/neto sólo si neto>0.",
            "Filtre inversión≤600 y compruebe independencia antes de sumar iniciativas. Repita con ahorro de horas reducido 25 %.",
            "Construya plan de piloto, medición, revisión, despliegue y monitoreo con aceptación/reversión; no contrate ni anuncie servicios.",
            "Para IA describa uso previsto, pruebas, revisión humana y retirada. Aceptación: fórmula reproducible, escenarios conservados, costos sintéticos y ningún ahorro garantizado.",
        ),
    ),
    "preparacion-segura": (
        (
            "Lea estado y condiciones del CSV como información ficticia; no convierta disponible en seguridad verificada.",
            "Clasifique BRAZO-B y DRON-D con motivo; distinga candidato PC-C virtual y evaluación física pendiente de CINTA-A.",
            "Diseñe checklist por modalidad con evidencia, rol autorizado y condición de no inicio. Mantenga desconocido cuando no hay comprobación.",
            "Acepte únicamente expediente documental completo del caso; no firme habilitación ni invente inspección, aforo o responsable reales.",
        ),
        (
            "Para cada incidencia separe hecho, acción registrada, hipótesis y dato faltante. No complete una causa por intuición.",
            "Clasifique físico/digital/documental y escriba comunicación por rol, sin datos personales.",
            "Distinga detener/avisar de aislamiento y reparación verificados; registre esos estados pendientes cuando corresponda.",
            "Aceptación: las tres incidencias conservan original, ninguna intervención física se ejecuta por el ejercicio y ninguna persona recibe culpa sin investigación.",
        ),
        (
            "Prepare dos cierres separados: virtual realizado y cancelado. Mantenga recursos, estados e incidencias del caso.",
            "Declare cero uso físico real en ambos; en cancelado tampoco invente ejecución académica ni asistencia.",
            "Añada aclaración posterior con motivo y referencia sin reescribir hechos cerrados; enumere evidencia y pendiente por rol.",
            "Aceptación: se distingue reserva/ejecución/cierre, los indicadores no suman cancelados como ejecutados y el documento no habilita operación de equipos.",
        ),
    ),
}
for _clave, _secuencias in PROCEDIMIENTOS.items():
    for _contenido, _pasos in zip(TEMARIOS[_clave], _secuencias):
        _contenido["actividad"] += (
            "\n\nSecuencia reproducible:\n"
            + "\n".join(
                f"{_numero}. {_paso}" for _numero, _paso in enumerate(_pasos, 1)
            )
            + "\n\nEntregables: copia de datos, tabla de trabajo, método/fórmulas, resultado, prueba y límites. "
        )
        _contenido["actividad"] += (
            "Cotejo específico de aceptación: " + _contenido["contraste"]
        )


ESPECIFICACIONES = (
    (
        "trazabilidad-qr",
        1,
        "Trazabilidad digital: identificación, movimientos y auditoría",
        8,
        ("LOG-ALMACEN", "LOG-AREA-ERP"),
        (
            "LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A",
            "LOGT-TIC-APLICADAS-A-LA-LOGISTICA",
        ),
        ("traza", "epcis"),
    ),
    (
        "logistica-circular",
        2,
        "Logística circular: retornos y comparación de alternativas",
        4,
        ("LOG-AREA-TMS", "LOG-AREA-SIM"),
        ("LOGT-DISENO-DE-RUTAS", "COEX-GESTION-DE-LA-CADENA-DE-SUMINISTROS"),
        ("scor",),
    ),
    (
        "analitica-operativa",
        3,
        "Analítica operativa: servicio, inventario y pronóstico",
        12,
        ("LOG-ALMACEN", "LOG-AREA-SIM", "LOG-AREA-ERP"),
        (
            "LOGT-TIC-APLICADAS-A-LA-LOGISTICA",
            "LOGT-PLANIFICACION-DE-LA-CADENA-D-38494E",
        ),
        ("scor", "ia"),
    ),
    (
        "automatizacion-logistica",
        4,
        "Automatización logística: señales, capacidad e integración",
        6,
        ("LOG-AREA-PRODUCCION", "LOG-AREA-ERP"),
        ("ADEM-ADMINISTRACION-DE-OPERACIONES", "LOGT-LOGISTICA-DE-PRODUCCION"),
        ("seguridad",),
    ),
    (
        "proyectos-replicables",
        5,
        "Proyectos logísticos: experimentación y comunicación reproducible",
        4,
        ("LOG-AREA-SIM", "LOG-AREA-ERP"),
        ("LOGT-SIMULADORES-LOGISTICOS", "LOGT-INVESTIGACION-DE-OPERACIONES"),
        ("scor",),
    ),
    (
        "transformacion-digital",
        6,
        "Transformación digital: procesos, contratos y evaluación de inversiones",
        16,
        ("LOG-AREA-COMERCIO", "LOG-AREA-PRODUCCION", "LOG-AREA-ERP"),
        (
            "COEX-OPERACIONES-DE-COMERCIO-EXTERIOR",
            "COEX-PROCEDIMIENTOS-ELECTRONICOS-5D0EED",
            "LOGT-OPTIMIZACION-DE-OPERACIONES",
        ),
        ("ia", "scor"),
    ),
    (
        "preparacion-segura",
        7,
        "Preparación de prácticas: riesgos, incidentes y cierre documental",
        4,
        ("LOG-ALMACEN", "LOG-AREA-PRODUCCION"),
        ("LOGT-INGENIERIA-DE-LA-CALIDAD", "LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A"),
        ("seguridad",),
    ),
)


def _tipografia(valor):
    """Espaciado de prosa sin alterar IDs, decimales ni símbolos científicos."""
    import re

    valor = re.sub(r"([a-záéíóúñ])(?=\d)", r"\1 ", valor)
    valor = re.sub(
        r"(\d)(min|kg|USD|meses|unidades|iniciales|de|por)(?=\b|\d)", r"\1 \2 ", valor
    )
    valor = re.sub(r"(\d)([sh])\b", r"\1 \2", valor)
    valor = re.sub(r"([:;])(?=[\w¿])", r"\1 ", valor)
    valor = re.sub(r",(?=[A-Za-zÁÉÍÓÚáéíóúñ])", ", ", valor)
    valor = re.sub(r"(?<=[a-záéíóúñ])(?=[A-Z])", " ", valor)
    return valor.replace("píloto", "piloto").replace("kg CO2e", "kgCO2e")


for _temario in TEMARIOS.values():
    for _bloque in _temario:
        for _campo in ("lectura", "actividad", "contraste"):
            _bloque[_campo] = _tipografia(_bloque[_campo])
        _bloque["preguntas"] = [
            tuple(_tipografia(campo) for campo in fila) for fila in _bloque["preguntas"]
        ]
RUBRICA = _tipografia(RUBRICA)


def _construir(fila):
    clave, numero, nombre, horas, areas, asignaturas, fuentes = fila
    bloques = TEMARIOS[clave]
    curso = {
        "nombre": nombre,
        "lema": bloques[0]["titulo"],
        "clasificacion": "corto",
        "modalidad": "autoguiado",
        "duracion_horas": horas,
        "inscripcion": "aprobacion",
        "emite_certificado": False,
        "descripcion": (
            "Programa del Laboratorio de Logística, Transporte y Cadena de Suministro. "
            + "; ".join(b["titulo"].lower() for b in bloques)
            + ".\n\n"
            + "Tres módulos con lecturas, datos sintéticos descargables, actividades, contraste de resultados, "
            + "rúbrica y doce preguntas. Estudio autónomo con entregas que requieren revisión docente. "
            + "Material completo para revisión pedagógica; no anuncia convocatoria, docentes, equipos, matrícula "
            + "o certificación aprobados. Presentación y materiales pueden consultarse sin una edición abierta."
        ),
        "aprendizajes": "\n".join(b["titulo"] for b in bloques),
        "dirigido_a": "Estudiantes, docentes y profesionales de logística, transporte, comercio exterior y operaciones.",
        "requisitos": "Manejo de archivos y hojas de cálculo. Navegador o lector PDF. Datos sintéticos del kit. No requiere adquirir equipos, servicios de IA o licencias comerciales.",
        "instructores": "",
        "activo": True,
        "publicado": False,
    }
    edicion = {
        "nombre": "Programa metodológico " + VERSION,
        "anio": 2026,
        "activa": False,
        "lugar": "Aula virtual del Laboratorio de Logística, Transporte y Cadena de Suministro",
        "horario": f"{horas} horas de estudio y práctica; acompañamiento sólo en edición autorizada.",
    }
    total = horas * 60
    presupuestos = [total // 3, total // 3, total - 2 * (total // 3)]
    modulos = []
    for indice, b in enumerate(bloques):
        estudio = "Estudio: " + b["titulo"]
        actividad = "Actividad: " + b["titulo"]
        contraste = "Contraste: " + b["titulo"]
        tiempo = presupuestos[indice] // 3
        entrega = presupuestos[indice] - tiempo - 25 - (10 if indice == 0 else 0)
        lecciones = [lectura(estudio, b["lectura"], tiempo)]
        if indice == 0:
            lecciones.append(
                (
                    "material",
                    "Kit reproducible: " + nombre,
                    {
                        "contenido": "Datos sintéticos, guía, contraste, rúbrica y fuentes. Descarga el ZIP y conserva originales. Incluye index.html legible sin instalar ni ejecutar programas.",
                        "duracion_min": 10,
                        "archivo_generado": (
                            clave + "-" + VERSION + ".zip",
                            partial(build_kit, clave),
                        ),
                    },
                )
            )
        lecciones.extend(
            [
                deber(actividad, b["actividad"] + "\n\n" + RUBRICA, entrega),
                lectura(contraste, b["contraste"], 10),
                guia_pdf(
                    "Guía: " + b["titulo"],
                    "Estudio, actividad, contraste y rúbrica.",
                    (estudio, actividad, contraste),
                ),
                evaluacion(
                    "Evaluación final: " + nombre
                    if indice == 2
                    else "Comprobación: " + b["titulo"],
                    [
                        ("unica", q, "\n".join(("*" + correcta, a, c)), explicacion)
                        for q, correcta, a, c, explicacion in b["preguntas"]
                    ],
                    intentos=3,
                    minutos=10,
                ),
            ]
        )
        lecciones[-2][2]["duracion_min"] = 5
        modulos.append(
            (
                f"{indice + 1}. {b['titulo']}",
                "Caso con datos sintéticos: "
                + b["titulo"]
                + ". Método, actividad, contraste y evaluación con evidencia.",
                lecciones,
            )
        )
    return {
        "clave": clave,
        "numero_propuesta": numero,
        "codigo_contenido": f"LOG-FOR-{numero:02d}",
        "version": VERSION,
        "estado_pedagogico": "completo_para_revision",
        "areas": areas,
        "asignaturas": asignaturas,
        "fuentes": fuentes,
        "CURSO": curso,
        "EDICION": edicion,
        "MODULOS": modulos,
    }


def _parrafos(valor):
    return "".join(
        "<p>" + escape(parrafo).replace("\n", " ") + "</p>"
        for parrafo in valor.split("\n\n")
    )


def programa_documento_html(clave):
    """Documento completo y accesible, sin scripts, iframes o llamadas a red."""
    import csv
    from io import StringIO
    from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import MATRIZ_ASIGNATURAS

    p = PROGRAMAS[clave]
    nombre = escape(p["CURSO"]["nombre"])
    cuerpo = [
        f"<header><p class='marca'>UPEC · Smart Logistics Lab</p><h1>{nombre}</h1>",
        f"<p>{p['CURSO']['duracion_horas']} horas de estudio · Versión {VERSION}</p>",
        "<p>Datos sintéticos y contenido metodológico. Este material no abre matrícula, no confirma equipos y no autoriza operaciones físicas.</p></header>",
        "<nav aria-label='Índice del programa'><ol>",
    ]
    for i, b in enumerate(TEMARIOS[clave], 1):
        cuerpo.append(f"<li><a href='#modulo-{i}'>{escape(b['titulo'])}</a></li>")
    cuerpo.append(
        "<li><a href='#datos'>Datos y diccionario</a></li><li><a href='#rubrica'>Rúbrica</a></li></ol></nav>"
    )
    cuerpo.append(
        "<section><h2>Ruta académica</h2><ul>"
        + "".join(
            "<li>"
            + escape(MATRIZ_ASIGNATURAS[codigo]["nombre"])
            + " — "
            + escape(MATRIZ_ASIGNATURAS[codigo]["carrera"])
            + "</li>"
            for codigo in p["asignaturas"]
        )
        + "</ul><p>Orientación complementaria: no reemplaza sílabos ni modifica relaciones oficiales de la carrera.</p></section>"
    )
    for i, b in enumerate(TEMARIOS[clave], 1):
        cuerpo.extend(
            [
                f"<section id='modulo-{i}'><p class='marca'>Módulo {i} de 3</p><h2>{escape(b['titulo'])}</h2>",
                _parrafos(b["lectura"]),
                "<h3>Actividad y evidencia</h3>",
                _parrafos(b["actividad"]),
                "<details><summary>Contrastar resultados después de resolver</summary>"
                + _parrafos(b["contraste"])
                + "</details>",
                "<h3>Autoevaluación formativa</h3><ol>",
            ]
        )
        for q, correcta, a, c, explicacion in b["preguntas"]:
            cuerpo.append(
                "<li><p>"
                + escape(q)
                + "</p><ul>"
                + "".join("<li>" + escape(x) + "</li>" for x in (a, correcta, c))
                + "</ul><details><summary>Comprobar</summary><p>"
                + escape(correcta)
                + ". "
                + escape(explicacion)
                + "</p></details></li>"
            )
        cuerpo.append("</ol></section>")
    cuerpo.append(
        "<section id='datos'><h2>Datos y diccionario de lectura</h2><p>CSV UTF-8, coma como separador. ud: unidades; min: minutos; s: segundos; kg: kilogramos; fraccion: proporción de 0 a 1. Tiempos relativos al inicio. Factores y precios son supuestos del caso. Conserve originales y trabaje con copia.</p>"
    )
    for archivo, contenido in DATOS[clave].items():
        filas = list(csv.reader(StringIO(contenido)))
        cuerpo.append(
            "<h3>"
            + escape(archivo)
            + "</h3><div class='tabla'><table><caption>Datos sintéticos: "
            + escape(archivo)
            + "</caption><thead><tr>"
            + "".join("<th scope='col'>" + escape(c) + "</th>" for c in filas[0])
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join("<td>" + escape(c) + "</td>" for c in fila) + "</tr>"
                for fila in filas[1:]
            )
            + "</tbody></table></div>"
        )
    cuerpo.append(
        "</section><section id='rubrica'><h2>Rúbrica y entrega</h2>"
        + _parrafos(RUBRICA)
        + "<p>Entregue originales, copia de trabajo, fórmulas o método, resultados, pruebas y límites. Contraste por sí mismo antes de solicitar revisión docente. El quiz del aula y la autoevaluación de este documento no acreditan una entrega revisada.</p></section>"
    )
    cuerpo.append(
        "<section><h2>Fuentes primarias</h2><p>Consultadas el 12 de octubre de 2026. Referencias enlazadas, sin reproducción del estándar, afiliación o certificación.</p><ul>"
        + "".join(
            "<li><a href='"
            + escape(FUENTES[codigo][1], quote=True)
            + "' rel='noopener noreferrer'>"
            + escape(FUENTES[codigo][0])
            + "</a></li>"
            for codigo in p["fuentes"]
        )
        + "</ul></section>"
    )
    estilo = "body{margin:0;background:#f3f7f5;color:#14312b;font:17px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:clamp(12px,3vw,40px)}header,section,nav{background:white;padding:clamp(18px,3vw,36px);margin:18px 0;border-radius:14px;border:1px solid #d6e3dc}header{border-top:8px solid #006633}h1{font-size:clamp(28px,4vw,44px);line-height:1.2}h2{color:#006633}a{color:#005b3d;text-underline-offset:4px}.marca{font-weight:750;letter-spacing:.08em;color:#006633}details{padding:14px;background:#eef6f0;border-left:4px solid #d3a900;margin:12px 0}summary{cursor:pointer;font-weight:700}.tabla{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #c9dad1;padding:9px;text-align:left}th{background:#e7f1eb}caption{text-align:left;font-weight:700}p{overflow-wrap:anywhere}@media print{body{background:white;font-size:11pt}main{padding:0}section,header,nav{border:0;page-break-inside:auto}details{display:block}details>*{display:block}a{color:inherit}}"
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"
        + nombre
        + "</title><style>"
        + estilo
        + "</style></head><body><main>"
        + "".join(cuerpo)
        + "</main></body></html>"
    )


def build_kit(clave):
    """ZIP determinista con entrada index.html; sin ejecutables, red o datos privados."""
    p = PROGRAMAS[clave]
    archivos = {
        **DATOS[clave],
        "index.html": programa_documento_html(clave),
        "LEEME.txt": p["CURSO"]["nombre"]
        + "\nVersión "
        + VERSION
        + "\nDatos sintéticos. Abra index.html; lea los CSV con UTF-8/coma. Conserve originales. No requiere instalar aplicaciones.\n",
        "rubrica.txt": RUBRICA,
        "fuentes.txt": "Consulta: 2026-10-12\n"
        + "\n".join(" — ".join(FUENTES[x]) for x in p["fuentes"]),
    }
    salida = BytesIO()
    with ZipFile(salida, "w", compression=ZIP_DEFLATED) as archivo:
        for nombre, valor in sorted(archivos.items()):
            info = ZipInfo(nombre, date_time=(2026, 10, 12, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archivo.writestr(info, valor.encode("utf-8"))
    return salida.getvalue()


PROGRAMAS = {fila[0]: _construir(fila) for fila in ESPECIFICACIONES}


def programa_para(clave):
    """Copia independiente; la edición del consumidor no muta contenido fuente."""
    return deepcopy(PROGRAMAS[clave])
