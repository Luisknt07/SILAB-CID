"""Segunda revisión: flujo del beneficiadero, planta y laboratorio de calidad."""

from .cafe import PROCESOS as PROCESOS_V1, proceso, etapa
from .cafe_equipos import EQUIPOS

POR_EQUIPO = {e["clave"]: e for e in EQUIPOS}


def paso(nombre, equipos, texto, *, area=None, alias="", **opciones):
    equipo = POR_EQUIPO[equipos[0]]
    detalle = (
        texto
        + "\nEquipamiento: "
        + "; ".join(POR_EQUIPO[c]["nombre"] for c in equipos)
        + "."
    )
    dato = etapa(nombre, detalle, area=area or equipo["area"], **opciones)
    dato["alias"] = alias
    return dato


def recepcion_cereza():
    return (
        paso(
            "Recepción de finca y apertura del microlote",
            ("BAS-CER", "CALADOR"),
            "Pesar bruto/tara/neto; identificar finca, cosecha, variedad declarada, propietario y ruta. Enviar muestra representativa al laboratorio antes de aceptar.",
            tipo="inspeccion",
            control="Identidad, masa, muestra y estado de aceptación",
            limite="Plan de recepción y criterio acordado",
        ),
        paso(
            "Selección de cereza y separación de flotantes",
            ("SEL-CER", "FLOT"),
            "Retirar cuerpos extraños y fruta no apta; pesar fracciones. El 100 % del ejemplo es una hipótesis de conservación; el rechazo real se registra por separado.",
            minutos=20,
        ),
    )


def secado(ruta):
    natural = ruta == "NATURAL"
    return (
        paso(
            "Selección y disposición de la masa para secado",
            ("SEL-CER", "CAMAS"),
            "Escurrir si corresponde; distribuir por lote y matriz. Registrar masa húmeda, carga por superficie/bandeja y elección solar o mecánica; no mezclar estados de humedad.",
            minutos=15,
        ),
        paso(
            "Secado solar o en horno/secador con control",
            ("CAMAS", "SECADOR", "HORNO", "TEMP"),
            "Elegir la alternativa disponible y probada: camas al sol, horno de producción o secador. Registrar aire/grano, ventilación, volteos, clima y humedad. No ejecutar las alternativas como tres pasos obligatorios ni usar la estufa de análisis como receta productiva.",
            minutos=40,
            espera=10080 if natural else 4320,
            rendimiento="40",
            control="Humedad por matriz, uniformidad y condición",
            limite="Método y especificación del lote; sin rehumectación",
            alias="Secado natural del fruto entero"
            if natural
            else "Secado con seguimiento de la masa y el ambiente",
        ),
        paso(
            "Acondicionamiento y comprobación del lote seco",
            ("HUMEDAD", "CALADOR", "RETENCION"),
            "Enfriar y muestrear distintas posiciones; contrastar método e instrumento. Retener ante diferencias, moho u olor; medir grano del natural con procedimiento apropiado.",
            tipo="inspeccion",
            control="Uniformidad y resultado de muestra",
            limite="Liberación documentada del café seco",
            area="PPCA-BENEFICIO",
        ),
        paso(
            "Almacenamiento del intermedio identificado",
            ("BODEGA-SECO",),
            "Registrar masa seca, envase, ubicación y muestra. El lote se entrega a recepción de la planta con origen y condición, no directamente al tostador.",
            tipo="almacenamiento",
            area="PPCA-BENEFICIO",
        ),
    )


PROCESOS = []
for clave, producto, salida in (
    ("LAVADO", "PER-LAV", 20),
    ("HONEY", "PER-HON", 20),
    ("NATURAL", "CER-NAT", 40),
):
    pasos = list(recepcion_cereza())
    if clave != "NATURAL":
        pasos.append(
            paso(
                "Despulpado calibrado y separación de pulpa"
                if clave == "LAVADO"
                else "Despulpado sin lavado del mucílago retenido",
                ("DESP", "PULPA"),
                "Calibrar para la cereza; pesar pulpa, daño y café retenido. En honey se conserva el mucílago según tratamiento, sin añadir miel.",
                minutos=20,
                rendimiento="50",
            )
        )
        if clave == "LAVADO":
            pasos.extend(
                (
                    paso(
                        "Remoción de mucílago por fermentación monitorizada",
                        ("FERM", "TEMP", "PH"),
                        "Monitorear la masa y criterio de finalización. El tiempo docente no decide por sí solo; remoción mecánica es una alternativa documentada, no un paso obligatorio extra.",
                        minutos=15,
                        espera=720,
                        control="Temperatura, evolución y punto final del tratamiento",
                        limite="Protocolo probado por matriz y condiciones",
                    ),
                    paso(
                        "Lavado y escurrido del pergamino",
                        ("LAVA", "DESM"),
                        "Para la ruta fermentada usar lavado; en ruta mecánica ajustar equipo y flujos según protocolo. Retirar mucílago, separar fracciones y conducir efluente a tratamiento.",
                        minutos=20,
                    ),
                )
            )
    else:
        pasos.append(
            paso(
                "Disposición de fruto entero en camas de secado",
                ("CAMAS",),
                "Mantener el fruto entero seleccionado; identificar matriz y ruta natural antes de distribuir. No aplicar el factor de pergamino a la posterior trilla.",
                minutos=15,
            )
        )
    pasos.extend(secado(clave))
    PROCESOS.append(
        proceso(
            clave,
            producto,
            "CEREZA",
            100,
            salida,
            tuple(pasos),
            instrucciones="Ruta del beneficiadero con secado alternativo solar o mecánico. Los factores son supuestos docentes: lavado/honey 100 kg cereza → 50 kg de masa antes del secado → 20 kg seco; natural 100 kg cereza → 40 kg fruto seco. Pesar agua, pulpa, rechazos y muestras reales. Mantener origen y entrega documentada a recepción de café seco.",
        )
    )

for ruta, entrada, base, salida in (
    ("LAV", "PER-LAV", 20, 16),
    ("HON", "PER-HON", 20, 16),
    ("NAT", "CER-NAT", 40, 16),
):
    PROCESOS.append(
        proceso(
            "VER-" + ruta,
            "VER-" + ruta,
            entrada,
            base,
            salida,
            (
                paso(
                    "Recepción y pesaje del café seco en planta",
                    ("BAS-SECO",),
                    "Recibir pergamino o fruto natural seco; pesar bruto/tara/neto y conciliar entrega. Registrar propietario, origen, ruta, condición y cuarentena.",
                    tipo="inspeccion",
                    control="Masa, identidad y matriz recibida",
                    limite="Recepción registrada; sin mezcla de lotes",
                    alias="Muestreo y comprobación del lote previo a trilla",
                ),
                paso(
                    "Muestreo y evaluación de recepción en laboratorio",
                    ("CALADOR", "DIVISOR", "BAL-LAB", "HUMEDAD", "DEFECTOS"),
                    "Obtener y dividir muestra representativa; comprobar humedad, integridad, olores y preparación física. Identificar método, custodia y decisión: aceptar, retener o rechazar.",
                    tipo="inspeccion",
                    control="Muestra, condición y criterio de aceptación",
                    limite="Laboratorio documenta aceptación de la matriz",
                ),
                paso(
                    "Descarga a tolva y transporte al silo de alimentación",
                    ("TOLVA", "ELEVADOR"),
                    "Sólo el lote aceptado pasa a la tolva y al silo. Revisar limpieza, flujo, resguardos y café residual del lote previo.",
                    tipo="transporte",
                ),
                paso(
                    "Silo de café seco y dosificación a trilla",
                    ("SILO-SECO",),
                    "Identificar contenido y saldo; dosificar sin sobrecargar la trilladora. Conciliar entrada/salida y remanente del silo.",
                    tipo="almacenamiento",
                ),
                paso(
                    "Trilla o descascarado y aspiración",
                    ("TRILLA", "POLVO"),
                    "Retirar la cubierta con ajuste para pergamino o natural. Pesar almendra, cubierta, finos y quebrados; la función de tamaño la realiza clasificadora integrada o a continuación.",
                    minutos=20,
                    rendimiento="80" if ruta != "NAT" else "40",
                ),
                paso(
                    "Clasificación por tamaños mediante zarandas",
                    ("CLASIF", "TAMIZ-VER"),
                    "Separar tamaños, identificar fracciones y verificar con muestra. Registrar criba y masa por tamaño; tamaño homogéneo no significa libre de defectos.",
                    minutos=15,
                    control="Tamaño y homogeneidad de fracciones",
                    limite="Tamices/método y destino de cada fracción",
                ),
                paso(
                    "Selección por calidad en banda transportadora",
                    ("BANDA", "DESPED", "DEFECTOS"),
                    "Inspeccionar con iluminación y velocidad adecuadas; retirar defectos visibles, piedras y cuerpos extraños. Pesar rechazos y verificar salida con muestreo; no prometer ausencia absoluta de defecto por observación parcial.",
                    minutos=25,
                    control="Defectos, material extraño y muestra de verificación",
                    limite="Criterio de preparación acordado",
                    alias="Clasificación de almendra y retiro de defectos",
                ),
                paso(
                    "Muestra retenida y liberación de café verde",
                    ("CALADOR", "RETENCION", "BODEGA-SECO"),
                    "Documentar preparación, fracciones y aceptación. El café seleccionado se envía al siguiente proceso con lote padre/hijo; el rechazo no se reintegra sin decisión.",
                    tipo="inspeccion",
                ),
            ),
            instrucciones="Secuencia de planta: recepción/peso → laboratorio → tolva/transporte → silo seco → trilla → clasificación por tamaños → banda de selección → verde aceptado. Escala docente: pérdidas reales de selección se miden y corrigen el rendimiento, no se ocultan en el saldo.",
        )
    )

PROCESOS.append(
    proceso(
        "MUESTRA",
        "MUE",
        "VER-LAV",
        1,
        ".85",
        (
            paso(
                "Codificación ciega y preparación de la muestra",
                ("CALADOR", "DIVISOR", "BAL-LAB"),
                "Relacionar muestra de recepción con origen; usar submuestra representativa y código ciego, manteniendo correspondencia privada.",
                tipo="inspeccion",
            ),
            paso(
                "Análisis físico previo a evaluación sensorial",
                ("HUMEDAD", "TAMIZ-VER", "DEFECTOS", "DENSIDAD"),
                "Registrar matriz, humedad/método, defectos, tamaños y densidad si corresponde; no sustituir calidad sensorial con una medición física.",
                tipo="inspeccion",
            ),
            paso(
                "Tueste de muestra con protocolo declarado",
                ("TOST-MUE", "COLOR"),
                "Tostar según preparación de evaluación seleccionada; conservar curva y color. La escala de 1 kg es total docente de muestras, no carga impuesta al equipo.",
                minutos=15,
                rendimiento="85",
            ),
            paso(
                "Enfriamiento, identificación y conservación",
                ("RETENCION",),
                "Enfriar con el sistema del tostador, pesar, identificar y preparar evaluación en la condición del protocolo; evitar contaminación/olores.",
            ),
            paso(
                "Molienda y preparación de tazas de evaluación",
                ("MOL-MUE", "BAL-LAB", "AGUA-LAB"),
                "Documentar molienda, purga, dosis, agua, recipientes y tiempos/temperaturas del método. Comparar muestras bajo la misma preparación.",
                minutos=15,
            ),
            paso(
                "Evaluación descriptiva, afectiva y de origen",
                ("CATACION",),
                "Evaluar con códigos ciegos y repeticiones; separar descripción, apreciación y atributos externos verificados. Registrar datos y límites de interpretación.",
                tipo="inspeccion",
                minutos=45,
                control="Preparación y consistencia de evaluación",
                limite="Método/version declarados; resultado interno",
            ),
            paso(
                "Informe de recepción, perfil y decisión",
                ("RETENCION",),
                "Conservar muestra y resultados; emitir aceptación, retención o ajuste. Citar un protocolo no certifica el laboratorio.",
                tipo="inspeccion",
            ),
        ),
        instrucciones="Laboratorio transversal: recepción, preparación física, tueste de muestras y catación; incluye controles de proceso y apoyo a liberación. La pérdida de 15 % sólo es supuesto de masa docente.",
    )
)

for perfil in ("FIL", "ESP"):
    PROCESOS.append(
        proceso(
            "TUE-" + perfil,
            "TUE-" + perfil,
            "VER-LAV",
            10,
            "8.5",
            (
                paso(
                    "Liberación de materia prima y pesaje de carga",
                    ("BAS-SECO", "CALADOR"),
                    "Recibir verde seleccionado por tamaños/calidad; verificar finca, ruta, perfil y muestra. Pesar carga real dentro del rango probado de la tostadora.",
                    tipo="inspeccion",
                    control="Identidad, preparación y carga",
                    limite="Lote aceptado y carga aprobada",
                    area="PPCA-TORREFACCION",
                ),
                paso(
                    "Alimentación de verde a la tostadora",
                    ("ELEVADOR", "TOSTADOR"),
                    "Conducir el lote preparado sin mezclar origen ni remanentes; comprobar flujo y resguardos.",
                    tipo="transporte",
                    area="PPCA-TORREFACCION",
                ),
                paso(
                    "Precalentamiento y estabilización del tostador",
                    ("TOSTADOR", "CICLON", "CURVAS"),
                    "Verificar suministro, sondas y extracción; estabilizar según manual y perfil. No aplicar temperatura de otra máquina.",
                    minutos=15,
                ),
                paso(
                    "Tueste con registro de curva y eventos",
                    ("TOSTADOR", "CURVAS"),
                    "Aplicar la versión del perfil para el uso previsto. Registrar carga, sonda, tiempo, aire/energía, eventos y descarga; repetir y contrastar taza.",
                    minutos=12,
                    rendimiento="85",
                    control="Curva, eventos, color y desvíos",
                    limite="Perfil probado por equipo, carga y lote",
                ),
                paso(
                    "Enfriamiento y separación de materia extraña",
                    ("ENFRIADOR", "CICLON"),
                    "Enfriar, pesar y retirar cascarilla/cuerpos extraños según sistema disponible. Revisar limpieza y condición final antes de enviar al silo.",
                    minutos=6,
                ),
                paso(
                    "Control del perfil y liberación hacia empaque",
                    ("BAL-LAB", "COLOR", "CATACION"),
                    "El laboratorio comprueba pérdida de masa, color/método y taza con la preparación prevista, filtro o espresso. Retener desviaciones hasta decisión.",
                    tipo="inspeccion",
                    minutos=20,
                    control="Masa, color y evaluación sensorial",
                    limite="Especificación del perfil y decisión documentada",
                    area="PPCA-CALIDAD",
                ),
                paso(
                    "Transporte a silo de café tostado",
                    ("ENFRIADOR", "SILO-TOST"),
                    "Transferir sólo café enfriado e identificado; registrar masa, origen y perfil y mantener limpieza del recorrido.",
                    tipo="transporte",
                ),
                paso(
                    "Silo de tostado y acondicionamiento",
                    ("SILO-TOST",),
                    "Conservar identidad, saldo y condición; programar permanencia según prueba de perfil/envase. La salida se bifurca: grano directo a empaque o molino para molido.",
                    tipo="almacenamiento",
                ),
            ),
            instrucciones="Planta: alimentación de verde preparado → curva de tostión → enfriamiento → control del laboratorio → silo de café tostado → empaque en grano o molienda. 10 kg verde → 8,5 kg tostado es hipótesis docente, no capacidad o curva de operación universal.",
        )
    )

for gramos in (250, 500, 1000):
    for molido in (False, True):
        prefijo = "MOL" if molido else "GRA"
        clave, producto = f"{prefijo}{gramos}", f"{prefijo}-{gramos}"
        rendimiento = "9.9" if molido else "10"
        n = (10000 + gramos - 1) // gramos
        etapas = [
            paso(
                "Verificación de lote tostado y plan de empaque",
                ("SILO-TOST", "BAL-LAB"),
                "Comprobar lote, origen, perfil, masa, presentación, envase y arte. La orden elige grano o molido; grano no pasa por el molino.",
                tipo="inspeccion",
                control="Lote y presentación elegida",
                limite="Grano/molido y 250/500/1.000 g definidos",
            )
        ]
        if molido:
            etapas.extend(
                (
                    paso(
                        "Alimentación de silo tostado al molino",
                        ("SILO-TOST", "MOLINO"),
                        "Dosificar el lote elegido y conciliar saldo del silo; evitar mezcla con café residual.",
                        tipo="transporte",
                    ),
                    paso(
                        "Molienda, purga y comprobación granulométrica",
                        ("MOLINO", "TAMIZ-MOL"),
                        "Elegir ajuste por método de preparación, comprobar granulometría y calentamiento. Pesar purga y remanente; en el ejemplo queda 99 % para empaque.",
                        minutos=15,
                        rendimiento="99",
                        control="Tamaño de molienda y masa retenida/purgada",
                        limite="Especificación por método y registro del ajuste",
                    ),
                    paso(
                        "Tolva de molido y alimentación de empaque",
                        ("SILO-MOL", "EMPACADORA"),
                        "Conducir al dosificador y minimizar espera/exposición; identificar lote y remanente.",
                        tipo="transporte",
                    ),
                )
            )
        else:
            etapas.append(
                paso(
                    "Alimentación directa de grano a empacadora",
                    ("SILO-TOST", "EMPACADORA"),
                    "Conducir café en grano al dosificador sin molienda; conservar lote y perfil.",
                    tipo="transporte",
                    area="PPCA-EMPAQUE",
                )
            )
        etapas.extend(
            (
                paso(
                    "Dosificación y comprobación del peso neto",
                    ("EMPACADORA", "PESO"),
                    f"Configurar {gramos} g de café por bolsa. Tarar y verificar según plan aprobado; contar unidades completas y separar remanente/muestras.",
                    minutos=20,
                ),
                paso(
                    "Sellado, integridad y codificación",
                    ("SELLO", "CODIFICADOR"),
                    "Comprobar cierre, válvula si procede, fuga e identificación del lote; retener defectuosos hasta corregir y revisar.",
                    minutos=20,
                    control="Integridad, lote y correspondencia de formato",
                    limite="Ensayo de sello y orden de empaque",
                ),
                paso(
                    "Etiquetado de la presentación y verificación",
                    ("ETIQUETADORA", "CODIFICADOR"),
                    "Aplicar arte aprobado de la presentación, origen respaldado y datos exigibles. Revisar inicio y cambio de lote/formato; QR no sustituye rotulado.",
                    tipo="inspeccion",
                    minutos=15,
                ),
                paso(
                    "Empaque secundario y conciliación de cajas",
                    ("CAJAS",),
                    "Agrupar por lote/presentación; registrar bolsas, cajas, unidades, masa de alimento y remanente. No mezclar retenido y liberado.",
                ),
                paso(
                    "Liberación, ubicación y disponibilidad de producto",
                    ("BODEGA", "RETENCION"),
                    "El laboratorio/documentación autorizan la disposición; ubicar en bodega, registrar saldo y condición. La venta sólo usa existencia liberada con tarifa/vida útil y requisitos aprobados.",
                    tipo="almacenamiento",
                ),
            )
        )
        bolsas = int(float(rendimiento) * 1000 // gramos)
        resto = float(rendimiento) - bolsas * gramos / 1000
        PROCESOS.append(
            proceso(
                clave,
                producto,
                "TOSTADO",
                10,
                rendimiento,
                tuple(etapas),
                instrucciones=f"Flujo de {'molido' if molido else 'grano'} en {gramos} g. La escala docente de 10 kg permite {bolsas} bolsas completas y {resto:.2f} kg remanente antes de otras muestras/pérdidas. Registrar peso neto, sello, etiqueta, empaque de transporte, liberación y bodega.",
                empaques=((f"BOL{gramos}", str(n)), ("ETIQUETA", str(n))),
            )
        )

ADICIONES_PRODUCTOS = tuple(
    (
        f"{tipo}-{gramos}",
        "EMP",
        f"Café de finca {'molido' if tipo == 'MOL' else 'en grano'} · {gramos} g",
        "terminado",
        f"Bolsa de barrera de {gramos} g; inventario alimentario en kg",
        "Presentación identificada por origen, ruta, perfil y lote. Registrar unidades de envase y kg de café por separado; precio, arte, vida útil y autorización requieren evidencia.",
    )
    for tipo, gramos in (("GRA", 500), ("MOL", 500), ("MOL", 1000))
)
ADICIONES_INSUMOS = (
    (
        "BOL500",
        "Bolsa de barrera alimentaria de 500 g",
        "unidad",
        "empaque",
        "Aptitud alimentaria, barrera, integridad, lote del proveedor y ensayo de sellado con el equipo real; formato de 500 g para grano o molido.",
    ),
)

assert len({p["clave"] for p in PROCESOS}) == len(PROCESOS)
assert {p["clave"] for p in PROCESOS_V1}.issubset({p["clave"] for p in PROCESOS})
