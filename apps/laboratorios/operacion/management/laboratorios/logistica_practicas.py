"""Doce prácticas docentes completas: datos sintéticos y controles reproducibles.

Contenido original UPEC para las seis áreas y las 23 asignaturas ya registradas.
No crea reservas, inventario, asistencia, autorizaciones ni calificaciones oficiales.
Las tablas de aula son casos analíticos independientes de los motores interactivos;
no se presentan como exportaciones de partidas ni mediciones de equipos físicos.
"""

import csv
import hashlib
import io
import json
from copy import deepcopy
from html import escape
from statistics import mean, pvariance

from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, SLUG
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import MATRIZ_ASIGNATURAS

VERSION = "1.0.0"
FECHA_REFERENCIA = "2026-10-12"
ADVERTENCIA = (
    "Caso docente con datos sintéticos. La duración es una estimación de aprendizaje, "
    "no un horario autorizado. La práctica en pantalla no acredita asistencia, operación "
    "de maquetas ni una prestación empresarial. El uso presencial sigue la guía institucional, "
    "reserva aprobada, inducción, aforo y recursos comprobados de la unidad."
)
FUENTES = {
    "gs1": {
        "entidad": "GS1",
        "titulo": "EPCIS and CBV",
        "url": "https://www.gs1.org/standards/epcis",
        "uso": "Referencia para distinguir objeto, tiempo, ubicación y contexto de un evento; el esquema docente no declara conformidad EPCIS.",
    },
    "mit": {
        "entidad": "MIT Sloan",
        "titulo": "MIT Sloan Beer Game Online",
        "url": "https://mitsloan.mit.edu/teaching-resources-library/mit-sloan-beer-game-online",
        "uso": "Referencia pedagógica para demoras, decisiones y coordinación. El juego UPEC y este material tienen desarrollo propio.",
    },
    "cvrp": {
        "entidad": "Google OR-Tools",
        "titulo": "Capacity Constraints",
        "url": "https://developers.google.com/optimization/routing/cvrp",
        "uso": "Referencia para representar demanda y capacidad vehicular. Las rutas de aula se validan mediante un modelo propio, sin afirmar optimalidad.",
    },
    "vrptw": {
        "entidad": "Google OR-Tools",
        "titulo": "Vehicle Routing Problem with Time Windows",
        "url": "https://developers.google.com/optimization/routing/vrptw",
        "uso": "Referencia de ventanas de servicio y tiempos de viaje; el caso usa coordenadas y compromisos sintéticos.",
    },
    "simpy": {
        "entidad": "SimPy",
        "titulo": "Overview — discrete event simulation",
        "url": "https://simpy.readthedocs.io/en/stable/",
        "uso": "Referencia de procesos, eventos y recursos limitados. Los cálculos tabulares no requieren instalar SimPy.",
    },
    "senae": {
        "entidad": "Servicio Nacional de Aduana del Ecuador",
        "titulo": "Para Exportar",
        "url": "https://www.aduana.gob.ec/servicio-al-ciudadano/para-exportar/",
        "uso": "Consultar el procedimiento oficial al preparar el expediente académico; ningún documento docente se transmite a ECUAPASS ni tiene validez aduanera.",
    },
    "icc": {
        "entidad": "International Chamber of Commerce",
        "titulo": "Incoterms rules",
        "url": "https://iccwbo.org/business-solutions/incoterms-rules/",
        "uso": "Consultar edición y fuente oficial para analizar obligaciones. No se reproduce el texto protegido ni se asigna una regla sin revisar el contrato.",
    },
    "series": {
        "entidad": "scikit-learn",
        "titulo": "TimeSeriesSplit",
        "url": "https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html",
        "uso": "Referencia de evaluación que conserva el orden temporal; declarar horizonte y separación entre entrenamiento y prueba.",
    },
    "mae": {
        "entidad": "scikit-learn",
        "titulo": "mean_absolute_error",
        "url": "https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html",
        "uso": "Referencia de la métrica MAE; en el paquete se calcula con aritmética propia sobre el mismo conjunto de prueba para cada candidato.",
    },
    "nist": {
        "entidad": "NIST",
        "titulo": "AI Risk Management Framework",
        "url": "https://www.nist.gov/itl/ai-risk-management-framework",
        "uso": "Referencia voluntaria para documentar uso, evaluación y riesgos de IA; no equivale a certificación ni instala un servicio externo.",
    },
}
for _fuente in FUENTES.values():
    _fuente["consulta"] = FECHA_REFERENCIA


def _dataset(titulo, campos, filas, descripcion):
    return {
        "titulo": titulo,
        "version": VERSION,
        "procedencia": "sinteticos_upec",
        "descripcion": descripcion,
        "campos": tuple(x[0] for x in campos),
        "diccionario": tuple(
            {"campo": x[0], "unidad": x[1], "descripcion": x[2]} for x in campos
        ),
        "filas": tuple(tuple(x) for x in filas),
    }


DATASETS = {
    "p01-conciliacion": _dataset(
        "Recepción y conteo de seis SKU",
        (
            ("sku", "id", "Producto docente"),
            ("inicial", "cajas", "Saldo verificado al inicio"),
            ("aceptado", "cajas", "Recepción conforme"),
            ("rechazado", "cajas", "Recepción segregada fuera de disponible"),
            ("salida", "cajas", "Despacho confirmado"),
            ("conteo", "cajas", "Conteo ciego final"),
        ),
        (
            ("SKU-A", 20, 10, 2, 8, 22),
            ("SKU-B", 12, 6, 0, 5, 12),
            ("SKU-C", 8, 4, 1, 3, 9),
            ("SKU-D", 30, 0, 0, 10, 20),
            ("SKU-E", 5, 10, 0, 4, 12),
            ("SKU-F", 15, 5, 0, 8, 12),
        ),
        "Una fila por SKU y cierre. Rechazado nunca entra al saldo disponible. Las diferencias son intencionales para la auditoría.",
    ),
    "p02-slotting": _dataset(
        "Frecuencia de acceso y ubicación de picking",
        (
            ("sku", "id", "Producto docente"),
            ("visitas", "visitas/turno", "Accesos previstos, no demanda en unidades"),
            ("distancia_base", "m/visita", "Recorrido completo ida y retorno"),
            (
                "distancia_alternativa",
                "m/visita",
                "Recorrido completo en ubicación alternativa",
            ),
            ("capacidad", "cajas", "Capacidad asignada"),
            ("stock", "cajas", "Ocupación inicial"),
        ),
        (
            ("SKU-A", 40, 30, 10, 25, 22),
            ("SKU-B", 30, 24, 12, 20, 13),
            ("SKU-C", 15, 18, 18, 12, 9),
            ("SKU-D", 8, 12, 24, 24, 20),
            ("SKU-E", 5, 10, 30, 15, 11),
            ("SKU-F", 2, 8, 32, 15, 12),
        ),
        "Mismo catálogo y accesos en ambas políticas. El recorrido ya incluye retorno: no multiplicar por dos.",
    ),
    "p03-demanda": _dataset(
        "Demanda semanal para pronóstico y reposición",
        (
            ("semana", "semana", "Índice temporal consecutivo"),
            ("demanda", "cajas/semana", "Venta sintética sin censura"),
            (
                "particion",
                "categoria",
                "Semanas 1–8 entrenamiento; 9–12 prueba de origen fijo",
            ),
        ),
        tuple(
            (i + 1, x, "entrenamiento" if i < 8 else "prueba")
            for i, x in enumerate((20, 22, 18, 24, 20, 22, 18, 24, 21, 23, 19, 25))
        ),
        "Horizonte de prueba cuatro semanas desde el cierre de la semana 8. No incorporar las observaciones de prueba a los pronósticos base.",
    ),
    "p04-reposicion": _dataset(
        "Fotografía de decisión de cuatro eslabones",
        (
            ("rol", "categoria", "Eslabón de la cadena"),
            ("disponible", "cajas", "Inventario utilizable"),
            ("transito", "cajas", "Pedidos confirmados aún no recibidos"),
            ("pendiente", "cajas", "Demanda atrasada"),
            ("objetivo", "cajas", "Posición objetivo declarada"),
            ("limite_pedido", "cajas/ronda", "Restricción de esta ronda"),
        ),
        (
            ("minorista", 8, 12, 4, 24, 20),
            ("mayorista", 10, 8, 6, 24, 20),
            ("distribuidor", 6, 16, 2, 24, 20),
            ("fabrica", 14, 8, 0, 24, 20),
        ),
        "Caso de una decisión de reposición, no resultado de una partida. Posición = disponible + tránsito − pendiente. No adelantar llegadas.",
    ),
    "p05-nodos": _dataset(
        "Red de distribución con capacidad y ventanas",
        (
            ("nodo", "id", "D es depósito; restantes son clientes"),
            ("x", "km", "Coordenada de red Manhattan"),
            ("y", "km", "Coordenada de red Manhattan"),
            ("demanda", "cajas", "Entrega indivisible"),
            ("abre", "min", "Inicio de ventana desde 08:00"),
            ("cierra", "min", "Último inicio de servicio permitido"),
            ("servicio", "min", "Tiempo de descarga"),
        ),
        (
            ("D", 0, 0, 0, 0, 120, 0),
            ("A", 2, 0, 3, 0, 15, 5),
            ("B", 4, 0, 2, 0, 30, 5),
            ("C", 4, 3, 2, 20, 45, 5),
            ("E", 0, 3, 3, 0, 20, 5),
            ("F", 1, 5, 2, 10, 40, 5),
        ),
        "Dos vehículos, capacidad 8 cajas cada uno, salida simultánea en minuto 0, 2 min/km y retorno obligatorio. Caso de aula diferente del mapa euclidiano del simulador.",
    ),
    "p06-contingencias": _dataset(
        "Incidencias comparables de última milla",
        (
            ("escenario", "id", "Identificador del experimento"),
            ("origen", "id", "Nodo de origen"),
            ("destino", "id", "Nodo de destino"),
            ("demora", "min", "Tiempo adicional por arco en ambos sentidos"),
            (
                "activa_desde",
                "min",
                "Momento conocido antes de salida; sólo 0 en este caso",
            ),
        ),
        (("base", "B", "C", 0, 0), ("congestion", "B", "C", 30, 0)),
        "Incidencia conocida antes de salir. Suma tiempo, no kilómetros. Comparar ruta fija con reordenamiento factible; no modificar demanda ni ventanas.",
    ),
    "p07-estaciones": _dataset(
        "Capacidad determinista de una línea de tres estaciones",
        (
            ("estacion", "id", "Orden de proceso S1 → S2 → S3"),
            (
                "ciclo_base",
                "min/unidad",
                "Un servidor por estación, sin lotes ni fallas",
            ),
            ("ciclo_alternativa", "min/unidad", "Ciclo después de balancear S2"),
        ),
        (("S1", 3, 3), ("S2", 5, 3), ("S3", 4, 4)),
        "Lote de 6 unidades disponible al inicio; transferencia una a una, buffer ilimitado, sin cambio de serie. Es un modelo tabular separado del motor Smart factory de paso fijo.",
    ),
    "p08-recuperacion": _dataset(
        "Clasificación y destino de devoluciones",
        (
            ("lote", "id", "Lote simbólico"),
            ("entrada", "unidades", "Cantidad recibida para inspección"),
            ("reutilizable", "unidades", "Aprobada para volver a disponible"),
            (
                "reproceso",
                "unidades",
                "Retenida para tratamiento, todavía no disponible",
            ),
            ("descarte", "unidades", "Segregada definitivamente"),
            ("costo_inspeccion", "u.m.", "Costo didáctico total por lote"),
        ),
        (
            ("DEV-01", 20, 12, 6, 2, 10),
            ("DEV-02", 15, 9, 3, 3, 8),
            ("DEV-03", 25, 15, 8, 2, 12),
        ),
        "u.m. significa unidad monetaria educativa. Ninguna cantidad de reproceso se suma como producto recuperado antes de verificarlo.",
    ),
    "p09-documentos": _dataset(
        "Cruce de factura y lista de empaque académicas",
        (
            ("linea", "id", "Línea SKU en expediente EXP-DOC-01"),
            ("factura_cantidad", "cajas", "Cantidad declarada en factura docente"),
            ("empaque_cantidad", "cajas", "Cantidad declarada en lista de empaque"),
            ("factura_peso", "kg", "Peso neto en factura docente"),
            ("empaque_peso", "kg", "Peso neto en lista de empaque"),
            (
                "precio_unitario",
                "u.m./caja",
                "Precio sintético, sin impuestos ni tasas reales",
            ),
        ),
        (
            ("SKU-A", 100, 100, 500, 500, 12),
            ("SKU-B", 80, 78, 240, 240, 15),
            ("SKU-C", 60, 60, 120, 125, 20),
        ),
        "Todos los documentos deben rotularse SIMULADO — SIN VALIDEZ. No contiene RUC, personas reales, códigos arancelarios ni declaraciones transmisibles.",
    ),
    "p10-terminal": _dataset(
        "Cola de atención de cuatro contenedores",
        (
            ("contenedor", "id", "Unidad docente, no identificador ISO real"),
            ("llegada", "min", "Arribo a cola"),
            ("servicio_base", "min", "Duración de atención por grúa única"),
            ("servicio_alternativa", "min", "Duración tras preparación previa"),
            ("limite_salida", "min", "Compromiso didáctico de salida"),
        ),
        (
            ("CONT-01", 0, 5, 3, 8),
            ("CONT-02", 2, 5, 3, 10),
            ("CONT-03", 4, 5, 3, 12),
            ("CONT-04", 6, 5, 3, 14),
        ),
        "Disciplina FIFO, una grúa, servicio no interrumpido y sin traslados adicionales. Todos los arribos se conservan al comparar.",
    ),
    "p11-eventos": _dataset(
        "Bitácora con errores de trazabilidad intencionales",
        (
            ("evento_id", "id", "Clave que debe ser única"),
            ("objeto", "id", "Lote docente"),
            ("operacion", "categoria", "recibir, ubicar o despachar"),
            ("cantidad", "cajas", "Cantidad afectada"),
            ("minuto", "min", "Tiempo sintético desde inicio"),
            ("ubicacion", "id", "Punto de registro"),
        ),
        (
            ("EV-01", "L-01", "recibir", 10, 0, "MUELLE"),
            ("EV-02", "L-01", "ubicar", 10, 2, "R-A"),
            ("EV-02", "L-01", "ubicar", 10, 2, "R-A"),
            ("EV-04", "L-01", "despachar", 11, 6, "SALIDA"),
            ("EV-05", "L-02", "recibir", 5, 4, "MUELLE"),
            ("EV-06", "L-02", "despachar", 5, 3, "SALIDA"),
        ),
        "Tres fallos deliberados: identificador repetido, despacho mayor que recepción y despacho anterior a recepción. Ubicar cambia ubicación, no aumenta saldo.",
    ),
    "p12-pronosticos": _dataset(
        "Validación y prueba de candidatos predictivos",
        (
            ("semana", "semana", "Orden de observación"),
            ("particion", "categoria", "validacion o prueba, bloque fijado"),
            ("real", "cajas/semana", "Demanda observada"),
            ("persistencia", "cajas/semana", "Predicción congelada de referencia"),
            (
                "candidato",
                "cajas/semana",
                "Predicción previamente congelada de candidato",
            ),
        ),
        (
            (9, "validacion", 21, 24, 20),
            (10, "validacion", 23, 24, 22),
            (11, "validacion", 19, 24, 20),
            (12, "validacion", 25, 24, 24),
            (13, "prueba", 24, 24, 22),
            (14, "prueba", 26, 24, 24),
            (15, "prueba", 22, 24, 20),
            (16, "prueba", 28, 24, 26),
        ),
        "Ejercicio de auditoría de predicciones ya congeladas, no entrenamiento de IA. La prueba muestra un empate de MAE deliberado: elegir por validación no garantiza mejorar fuera de muestra.",
    ),
}


def dataset_csv(clave):
    """CSV determinista, con encabezado y finales LF, apto para hoja de cálculo."""
    dataset = DATASETS[clave]
    salida = io.StringIO(newline="")
    writer = csv.writer(salida, lineterminator="\n")
    writer.writerow(dataset["campos"])
    for fila in dataset["filas"]:
        writer.writerow(fila)
    return salida.getvalue()


def checksum_dataset(clave):
    return hashlib.sha256(dataset_csv(clave).encode("utf-8")).hexdigest()


def _filas(clave):
    dataset = DATASETS[clave]
    return [
        dict(zip(dataset["campos"], fila, strict=True)) for fila in dataset["filas"]
    ]


def _ruta(visitas, demora=0):
    """Control de una ruta concreta: no es un solucionador ni afirma optimalidad."""
    nodos = {x["nodo"]: x for x in _filas("p05-nodos")}
    carga = sum(nodos[x]["demanda"] for x in visitas)
    reloj = 0
    distancia = 0
    anterior = "D"
    servicios = []
    for siguiente in [*visitas, "D"]:
        origen, destino = nodos[anterior], nodos[siguiente]
        tramo = abs(origen["x"] - destino["x"]) + abs(origen["y"] - destino["y"])
        distancia += tramo
        reloj += 2 * tramo
        if {anterior, siguiente} == {"B", "C"}:
            reloj += demora
        if siguiente != "D":
            reloj = max(reloj, destino["abre"])
            servicios.append(
                {
                    "nodo": siguiente,
                    "inicio": reloj,
                    "puntual": reloj <= destino["cierra"],
                }
            )
            reloj += destino["servicio"]
        anterior = siguiente
    return {
        "visitas": list(visitas),
        "carga": carga,
        "capacidad": 8,
        "factible_capacidad": carga <= 8,
        "distancia_km": distancia,
        "retorno_min": reloj,
        "servicios": servicios,
        "puntuales": sum(x["puntual"] for x in servicios),
    }


def _linea(campo):
    ciclos = [x[campo] for x in _filas("p07-estaciones")]
    fin_anterior = [0] * len(ciclos)
    eventos = []
    for unidad in range(1, 7):
        fin_previo = 0
        for estacion, ciclo in enumerate(ciclos):
            inicio = max(fin_previo, fin_anterior[estacion])
            fin = inicio + ciclo
            eventos.append(
                {
                    "unidad": unidad,
                    "estacion": estacion + 1,
                    "inicio": inicio,
                    "fin": fin,
                }
            )
            fin_previo = fin
            fin_anterior[estacion] = fin
    return {
        "unidades": 6,
        "makespan_min": fin_anterior[-1],
        "capacidad_estable_unidades_h": 60 / max(ciclos),
        "eventos": eventos,
    }


def _cola(campo):
    fin = 0
    eventos = []
    for fila in _filas("p10-terminal"):
        inicio = max(fila["llegada"], fin)
        fin = inicio + fila[campo]
        eventos.append(
            {
                "contenedor": fila["contenedor"],
                "inicio": inicio,
                "fin": fin,
                "espera": inicio - fila["llegada"],
                "permanencia": fin - fila["llegada"],
                "puntual": fin <= fila["limite_salida"],
            }
        )
    return {
        "eventos": eventos,
        "cierre_min": fin,
        "espera_media_min": mean(x["espera"] for x in eventos),
        "permanencia_media_min": mean(x["permanencia"] for x in eventos),
        "puntuales": sum(x["puntual"] for x in eventos),
    }


def controles_calculados(numero):
    """Soluciones de comprobación para las tablas de aula; nunca resultados reales."""
    if type(numero) is not int or not 1 <= numero <= 12:
        raise ValueError("Práctica no disponible.")
    if numero == 1:
        filas = _filas("p01-conciliacion")
        diferencias = {
            x["sku"]: x["conteo"] - (x["inicial"] + x["aceptado"] - x["salida"])
            for x in filas
        }
        return {
            "saldo_teorico": sum(
                x["inicial"] + x["aceptado"] - x["salida"] for x in filas
            ),
            "conteo": sum(x["conteo"] for x in filas),
            "rechazado": sum(x["rechazado"] for x in filas),
            "diferencias": diferencias,
            "exactitud_registros_pct": 100
            * sum(v == 0 for v in diferencias.values())
            / len(filas),
        }
    if numero == 2:
        filas = _filas("p02-slotting")
        base = sum(x["visitas"] * x["distancia_base"] for x in filas)
        alternativa = sum(x["visitas"] * x["distancia_alternativa"] for x in filas)
        return {
            "recorrido_base_m": base,
            "recorrido_alternativa_m": alternativa,
            "reduccion_pct": 100 * (base - alternativa) / base,
            "capacidad_factible": all(x["stock"] <= x["capacidad"] for x in filas),
        }
    if numero == 3:
        filas = _filas("p03-demanda")
        train = [x["demanda"] for x in filas if x["particion"] == "entrenamiento"]
        test = [x["demanda"] for x in filas if x["particion"] == "prueba"]
        return {
            "persistencia": train[-1],
            "media4": mean(train[-4:]),
            "mae_persistencia": mean(abs(x - train[-1]) for x in test),
            "mae_media4": mean(abs(x - mean(train[-4:])) for x in test),
            "punto_reorden_cajas": 2 * mean(train[-4:]) + 6,
        }
    if numero == 4:
        filas = _filas("p04-reposicion")
        decisiones = []
        for fila in filas:
            posicion = fila["disponible"] + fila["transito"] - fila["pendiente"]
            decisiones.append(
                {
                    "rol": fila["rol"],
                    "posicion": posicion,
                    "pedido": min(
                        fila["limite_pedido"], max(0, fila["objetivo"] - posicion)
                    ),
                }
            )
        return {
            "decisiones": decisiones,
            "advertencia": "Una fotografía no permite calcular efecto látigo: exportar series completas de la partida.",
        }
    if numero in {5, 6}:
        demora = 30 if numero == 6 else 0
        base = [_ruta(("A", "B", "C"), demora), _ruta(("E", "F"), demora)]
        alternativa = [_ruta(("A", "B"), demora), _ruta(("E", "F", "C"), demora)]
        return {
            "base": base,
            "alternativa": alternativa,
            "base_km": sum(x["distancia_km"] for x in base),
            "alternativa_km": sum(x["distancia_km"] for x in alternativa),
            "base_puntuales": sum(x["puntuales"] for x in base),
            "alternativa_puntuales": sum(x["puntuales"] for x in alternativa),
        }
    if numero == 7:
        return {
            "base": _linea("ciclo_base"),
            "alternativa": _linea("ciclo_alternativa"),
        }
    if numero == 8:
        filas = _filas("p08-recuperacion")
        totales = {
            k: sum(x[k] for x in filas)
            for k in (
                "entrada",
                "reutilizable",
                "reproceso",
                "descarte",
                "costo_inspeccion",
            )
        }
        totales["recuperacion_inmediata_pct"] = (
            100 * totales["reutilizable"] / totales["entrada"]
        )
        totales["balance_correcto"] = all(
            x["entrada"] == x["reutilizable"] + x["reproceso"] + x["descarte"]
            for x in filas
        )
        return totales
    if numero == 9:
        filas = _filas("p09-documentos")
        return {
            "cantidad_factura": sum(x["factura_cantidad"] for x in filas),
            "cantidad_empaque": sum(x["empaque_cantidad"] for x in filas),
            "peso_factura_kg": sum(x["factura_peso"] for x in filas),
            "peso_empaque_kg": sum(x["empaque_peso"] for x in filas),
            "valor_factura_um": sum(
                x["factura_cantidad"] * x["precio_unitario"] for x in filas
            ),
            "lineas_inconsistentes": [
                x["linea"]
                for x in filas
                if x["factura_cantidad"] != x["empaque_cantidad"]
                or x["factura_peso"] != x["empaque_peso"]
            ],
        }
    if numero == 10:
        return {
            "base": _cola("servicio_base"),
            "alternativa": _cola("servicio_alternativa"),
        }
    if numero == 11:
        filas = _filas("p11-eventos")
        vistos, duplicados = set(), set()
        unicas = []
        for fila in filas:
            if fila["evento_id"] in vistos:
                duplicados.add(fila["evento_id"])
                continue
            vistos.add(fila["evento_id"])
            unicas.append(fila)
        errores = []
        for objeto in sorted({x["objeto"] for x in unicas}):
            eventos = [x for x in unicas if x["objeto"] == objeto]
            entradas = [x for x in eventos if x["operacion"] == "recibir"]
            salidas = [x for x in eventos if x["operacion"] == "despachar"]
            if sum(x["cantidad"] for x in salidas) > sum(
                x["cantidad"] for x in entradas
            ):
                errores.append(objeto + ":sobre_despacho")
            if entradas and any(
                x["minuto"] < min(e["minuto"] for e in entradas) for x in salidas
            ):
                errores.append(objeto + ":orden_temporal")
        return {
            "filas": len(filas),
            "eventos_unicos": len(unicas),
            "duplicados": sorted(duplicados),
            "errores": errores,
        }
    filas = _filas("p12-pronosticos")
    resultado = {}
    for particion in ("validacion", "prueba"):
        bloque = [x for x in filas if x["particion"] == particion]
        resultado[particion] = {
            modelo: mean(abs(x["real"] - x[modelo]) for x in bloque)
            for modelo in ("persistencia", "candidato")
        }
    return resultado


def amplificacion(pedidos, demanda):
    """Razón de varianzas poblacionales, series alineadas y de igual longitud."""
    if len(pedidos) != len(demanda) or len(demanda) < 2:
        raise ValueError("Se necesitan series alineadas con al menos dos períodos.")
    varianza = pvariance(demanda)
    return None if varianza == 0 else pvariance(pedidos) / varianza


GUIAS = {}


def _guia(
    numero,
    titulo,
    area,
    asignaturas,
    datasets,
    contexto,
    objetivos,
    teoria,
    pasos,
    decisiones,
    metricas,
    entregables,
    preguntas,
    fuentes,
    simulador,
    duracion=150,
):
    clave = "practica-" + str(numero).zfill(2)
    GUIAS[clave] = {
        "numero": numero,
        "titulo": str(numero).zfill(2) + " · " + titulo,
        "area": area,
        "asignaturas": tuple(asignaturas),
        "datasets": tuple(datasets),
        "seccion": "4.1",
        "carpeta": "Prácticas · " + AREAS[area]["nombre"],
        "fuentes": tuple(fuentes),
        "objetivo": objetivos[0],
        "objetivos": tuple(objetivos),
        "contexto": contexto,
        "teoria": tuple(teoria),
        "procedimiento": tuple(pasos),
        "decisiones": tuple(decisiones),
        "metricas": tuple(metricas),
        "entregables": tuple(entregables),
        "preguntas": tuple(preguntas),
        "simulador": simulador,
        "duracion_minutos": duracion,
        "prerrequisitos": (
            "Leer el diccionario y distinguir cantidad, unidad, identificador y tiempo.",
            "Manejar filtros, sumas, referencias y gráficos en una hoja de cálculo; existe alternativa manual con las tablas incluidas.",
            "Revisar la guía de inducción si se programa una actividad presencial; la modalidad digital no autoriza hardware.",
        ),
    }
    guia = GUIAS[clave]
    guia["bloques"] = [
        ("Contexto", [contexto]),
        ("Resultados de aprendizaje", list(objetivos)),
        ("Fundamentos", [titulo_t + ": " + texto for titulo_t, texto in teoria]),
        ("Procedimiento", [titulo_p + ": " + texto for titulo_p, texto in pasos]),
        ("Decisiones y restricciones", list(decisiones)),
        ("Indicadores", [titulo_m + ": " + formula for titulo_m, formula in metricas]),
        ("Entregables", list(entregables)),
        ("Reflexión y transferencia", list(preguntas)),
    ]


_guia(
    1,
    "Recepción, cuarentena y exactitud de inventario",
    "LOG-ALMACEN",
    ("LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A", "LOGT-INGENIERIA-DE-LA-CALIDAD"),
    ("p01-conciliacion",),
    "Un centro docente recibe seis SKU y debe cerrar el inventario sin esconder diferencias. El equipo audita aceptación, rechazo, despacho y conteo ciego; después reproduce un flujo operativo en el centro de distribución virtual.",
    (
        "Conciliar los seis SKU y localizar cada diferencia sin ajustar el saldo para forzar coincidencia.",
        "Calcular exactitud por registros y justificar por qué el saldo agregado puede ocultar faltantes y excedentes.",
        "Proponer un control preventivo y una acción correctiva trazable para cada discrepancia.",
    ),
    (
        (
            "Estados del material",
            "Una recepción puede quedar aceptada, rechazada o pendiente. Sólo lo aceptado alimenta disponible. El rechazo se segrega y se cuenta como categoría separada; reservar o ubicar cambia estado o lugar, no crea unidades.",
        ),
        (
            "Conciliación",
            "Para cada SKU, saldo teórico = inicial + aceptado − salida. Diferencia = conteo − saldo teórico. El signo distingue exceso de faltante. La suma de diferencias puede ser cero aun cuando existan errores en dos productos.",
        ),
        (
            "Dato y evento",
            "El documento de cierre resume cantidades; la bitácora explica qué movimiento las originó. Una corrección conserva el valor anterior, motivo y responsable de revisión.",
        ),
    ),
    (
        (
            "Preparar",
            "Guardar el CSV con versión y hash; asignar operador, contador y auditor. Verificar seis claves únicas y cantidades no negativas; no editar las observaciones originales.",
        ),
        (
            "Recrear recepción",
            "Crear una tabla de eventos con ID, SKU, operación, cantidad, unidad, origen, destino y minuto. Separar las tres cajas rechazadas; ubicar únicamente lo aceptado.",
        ),
        (
            "Calcular y cotejar",
            "Añadir saldo teórico, diferencia y exacto. El contador registra el conteo sin ver la columna de saldo; el auditor reconcilia después. Mantener rechazado fuera de disponible.",
        ),
        (
            "Investigar",
            "Abrir una incidencia por SKU con diferencia; formular al menos dos causas posibles y la evidencia necesaria para elegir. No atribuir robo, daño o responsabilidad personal sin prueba.",
        ),
        (
            "Experimentar",
            "Abrir el simulador CD, conservar caso y semilla, operar recepción a despacho y exportar. Contrastar sus eventos con la tabla de aula sin fusionar los dos conjuntos de datos.",
        ),
        (
            "Cerrar",
            "Entregar conciliación, diferencias y controles. Registrar qué hipótesis no puede resolverse sólo con el conteo y qué medición presencial requeriría autorización.",
        ),
    ),
    (
        "No corregir conteos originales para mejorar exactitud.",
        "Una discrepancia no autoriza ajustar inventario institucional.",
        "Cada SKU se analiza individualmente antes del agregado.",
    ),
    (
        ("Saldo teórico", "Inicial + aceptado − salida [cajas/SKU]."),
        (
            "Exactitud por registros",
            "SKU sin diferencia / 6 × 100 [%]; no es porcentaje de unidades correctas.",
        ),
        (
            "Diferencia neta y absoluta",
            "Σ diferencias [cajas] y Σ |diferencia| [cajas], informar ambas.",
        ),
    ),
    (
        "CSV original y diccionario con versión/hash.",
        "Conciliación de seis filas con fórmulas y tabla de incidencias por SKU.",
        "Gráfico divergente de faltantes/excedentes con tabla de respaldo.",
        "Exportación del experimento CD, conclusión y dos controles preventivos verificables.",
    ),
    (
        "¿Por qué una diferencia neta cero no demuestra exactitud?",
        "¿Qué evidencia distingue error de recepción de error de picking?",
        "¿Qué cambia al medir físicamente cajas de tamaños diferentes?",
    ),
    ("gs1",),
    "distribucion/?caso=cd-normal&semilla=42",
    120,
)

_guia(
    2,
    "Ubicación por actividad y preparación de pedidos",
    "LOG-ALMACEN",
    ("LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A", "LOGT-TIC-APLICADAS-A-LA-LOGISTICA"),
    ("p02-slotting",),
    "El mismo turno de 100 accesos se atiende con dos distribuciones de ubicaciones. Se necesita reducir desplazamiento sin superar capacidad ni cambiar la demanda para favorecer una política.",
    (
        "Calcular el recorrido total de ambas distribuciones y su reducción relativa con 100 visitas constantes.",
        "Validar capacidad por SKU y explicar al menos una restricción que la distancia no representa.",
        "Diseñar un plano legible y un experimento que cambie una política por vez.",
    ),
    (
        (
            "Actividad y clasificación",
            "La rotación se aproxima aquí por visitas de picking, no por ingresos monetarios. Ordenar SKU por visitas y mostrar su acumulado; no imponer porcentajes ABC universales. Ubicar cerca lo frecuente sólo es factible si capacidad, compatibilidad y seguridad lo permiten.",
        ),
        (
            "Distancia ponderada",
            "Recorrido = Σ visitas × distancia completa por visita. La tabla ya incluye ida y retorno. El indicador no es tiempo: convertirlo exige velocidad, congestión y detenciones medidas.",
        ),
        (
            "Diseño experimental",
            "Comparar las mismas líneas y recursos permite relacionar el cambio con ubicación. Si también cambia el tamaño de lote, separar su efecto con un experimento adicional.",
        ),
    ),
    (
        (
            "Preparar",
            "Verificar que visitas suman 100; conservar catálogo, stock y capacidades. Dibujar seis posiciones docentes y declarar que no constituyen un plano industrial certificado.",
        ),
        (
            "Medir base",
            "Calcular contribución visitas × distancia_base por SKU y recorrido agregado. Graficar las contribuciones con unidades en metros por turno.",
        ),
        (
            "Evaluar alternativa",
            "Repetir con distancia_alternativa. Revisar stock ≤ capacidad para los seis SKU; anotar restricciones de compatibilidad no representadas por el caso.",
        ),
        (
            "Explicar resultados",
            "Calcular diferencia absoluta, porcentaje y metros por visita. Identificar qué SKU mejora más y cuáles empeoran para no ocultar transferencias de esfuerzo.",
        ),
        (
            "Replicar virtualmente",
            "Comparar dos estrategias de ubicación en CD con idéntico caso, semilla y pedidos. Mantener CSV de aula y exportaciones del motor separados; reportar sus reglas de distancia distintas.",
        ),
        (
            "Comunicar",
            "Entregar plano base/alternativa, gráfico pareado y una recomendación condicionada a seguridad, capacidad y esfuerzo de reubicación.",
        ),
    ),
    (
        "No sumar tiempo y distancia en una misma magnitud.",
        "No retirar accesos de SKU lentos del denominador.",
        "Si una alternativa supera capacidad, declararla inviable aunque reduzca metros.",
    ),
    (
        ("Recorrido", "Σ visitas_i × distancia_i [m/turno]."),
        ("Distancia media", "Recorrido / 100 [m/visita]."),
        ("Reducción", "(Recorrido base − alternativa) / base × 100 [%]."),
    ),
    (
        "Tabla de contribuciones, sumas y capacidad verificable.",
        "Dos planos codificados con leyenda y accesos equivalentes.",
        "Gráfico por SKU y comparación experimental exportada.",
        "Recomendación con costo de cambio, riesgos y límites.",
    ),
    (
        "¿Puede una ubicación más corta aumentar congestión?",
        "¿Qué cambia si visitas y unidades por pedido varían?",
        "¿Cuántos turnos compensarían un costo medido de reubicación?",
    ),
    ("gs1",),
    "distribucion/?caso=cd-pico&semilla=42",
)

_guia(
    3,
    "Pronóstico base y punto de reorden",
    "LOG-AREA-SIM",
    (
        "LOGT-INVESTIGACION-DE-OPERACIONES",
        "LOGT-PLANIFICACION-DE-LA-CADENA-D-38494E",
        "COEX-GESTION-DE-LA-CADENA-DE-SUMINISTROS",
    ),
    ("p03-demanda",),
    "Un planificador debe comprometer existencias durante dos semanas de plazo. Compara persistencia y media de cuatro semanas sin mirar el futuro y documenta una política simple de reorden.",
    (
        "Construir dos pronósticos de origen fijo para semanas 9–12 usando sólo semanas 1–8.",
        "Calcular MAE sobre las mismas cuatro observaciones y justificar la comparación sin fuga temporal.",
        "Calcular punto de reorden con plazo fijo de dos semanas y reserva docente de seis cajas; declarar límites de ese supuesto.",
    ),
    (
        (
            "Origen fijo",
            "Al cierre de semana 8 se emite el bloque de cuatro predicciones. Persistencia usa demanda de semana 8 en todo el bloque; media4 usa el promedio 5–8. La prueba no actualiza esos pronósticos. Un experimento de origen móvil sería distinto y debe etiquetarse.",
        ),
        (
            "Error y servicio",
            "MAE = promedio de |real − predicción|. Un MAE menor no garantiza menor faltante si existen costos asimétricos, sesgo o plazos variables. Conservar también error firmado para detectar subestimación sistemática.",
        ),
        (
            "Reorden",
            "En este ejercicio R = demanda semanal media × plazo + reserva fija. Se supone demanda plenamente observada y plazo constante. La reserva de seis cajas es un parámetro docente, no un nivel estadístico de servicio ni recomendación empresarial.",
        ),
    ),
    (
        (
            "Separar datos",
            "Bloquear semanas 9–12 para selección inicial. Guardar copia con entrenamiento y prueba identificados, unidades y horizonte de cuatro semanas.",
        ),
        (
            "Construir referencia",
            "Emitir persistencia y media4 desde semana 8. Crear cuatro filas futuras con las predicciones congeladas antes de revelar reales.",
        ),
        (
            "Evaluar",
            "Unir las cuatro observaciones, calcular errores absolutos y firmados, MAE y gráfico real/predicción. Usar el mismo conjunto para ambos métodos.",
        ),
        (
            "Formular política",
            "Con media4, plazo 2 y reserva 6, obtener R. Para posición de inventario 43 cajas, decidir si se dispara reorden; distinguir el umbral de la cantidad a pedir.",
        ),
        (
            "Sensibilidad",
            "Recalcular R para plazos 1, 2 y 3 y reservas 0, 6 y 12 sin afirmar nivel de servicio. Registrar una tabla de nueve escenarios.",
        ),
        (
            "Contrastar",
            "Usar el simulador IA para estudiar su separación entrenamiento/validación/prueba; sus 60 semanas son otro dataset y no sustituyen el ensayo tabular de 12 semanas.",
        ),
    ),
    (
        "Ninguna observación de prueba entra al cálculo de los dos pronósticos.",
        "No confundir umbral R con tamaño de pedido.",
        "Si se observa venta censurada por faltantes, declarar que no equivale a demanda total.",
    ),
    (
        ("MAE", "Σ |demanda − pronóstico| / 4 [cajas/semana]."),
        ("Sesgo", "Σ (demanda − pronóstico) / 4 [cajas/semana]."),
        (
            "Punto de reorden",
            "2 × media4 + 6 [cajas]; reordenar cuando posición ≤ R según regla declarada.",
        ),
    ),
    (
        "Predicciones congeladas y tabla de ocho errores absolutos.",
        "Gráfico temporal con línea de corte entrenamiento/prueba.",
        "Matriz de sensibilidad R y decisión para posición 43.",
        "Conclusión sobre error, sesgo y supuestos de servicio.",
    ),
    (
        "¿Qué información adicional permite estimar reserva por nivel de servicio?",
        "¿Qué pasa si el plazo depende de la cantidad pedida?",
        "¿Por qué ajustar el método con la prueba cambia el significado de MAE?",
    ),
    ("series", "mae"),
    "operaciones/?caso=ia-pronostico&semilla=42",
)

_guia(
    4,
    "Juego de la cerveza: coordinación y efecto látigo",
    "LOG-AREA-SIM",
    (
        "COEX-GESTION-DE-LA-CADENA-DE-SUMINISTROS",
        "LOGT-PLANIFICACION-DE-LA-CADENA-D-38494E",
        "LOGT-SIMULADORES-LOGISTICOS",
    ),
    ("p04-reposicion",),
    "Cuatro participantes operan minorista, mayorista, distribuidor y fábrica. Antes de jugar calculan una fotografía de reposición; después comparan partidas con y sin coordinación conservando reglas y demanda.",
    (
        "Calcular posición y pedido factible de los cuatro roles sin contar tránsito como recepción inmediata.",
        "Guardar y comparar dos partidas completas con la misma configuración y serie de demanda.",
        "Explicar costo, servicio y amplificación usando al menos una demora y una decisión registrada.",
    ),
    (
        (
            "Estado de reposición",
            "Posición = disponible + tránsito − pendiente. Una política objetivo pide max(0, objetivo − posición), limitada por la capacidad declarada. La fotografía permite verificar una ronda, no reconstruir la dinámica completa.",
        ),
        (
            "Demoras y coordinación",
            "Los pedidos y envíos se desplazan en sentidos opuestos. Una llegada esperada permanece en tránsito hasta su fecha. La coordinación puede cambiar decisiones, pero no elimina por sí misma plazos ni capacidad.",
        ),
        (
            "Amplificación",
            "Razón de varianzas = Var(pedidos) / Var(demanda) para el mismo período y frecuencia. Usar la misma convención de varianza. Si la demanda es constante, reportar no definido y analizar amplitud de pedidos y costo; nunca dividir entre cero.",
        ),
    ),
    (
        (
            "Preparar roles",
            "Asignar los cuatro roles y un facilitador; leer reglas y completar la fotografía CSV. Acordar tratamiento de desconexiones y mantener un observador sin acceso a decisiones privadas.",
        ),
        (
            "Verificar una ronda",
            "Calcular posición y pedido en cada rol y cotejar los controles. Dibujar flujo de pedidos y productos con las demoras de la configuración real del juego.",
        ),
        (
            "Partida base",
            "Crear sala multijugador, registrar escenario, versión, semilla, plazo, costos y horizonte. Cada rol justifica su pedido antes de confirmar; conservar decisiones y exportación final.",
        ),
        (
            "Partida coordinada",
            "Repetir con el mismo escenario y modificar sólo la regla de información o política acordada. Usar el modo de información realmente disponible; cualquier comunicación adicional se documenta como intervención experimental.",
        ),
        (
            "Analizar",
            "Alinear rondas de las exportaciones; comparar inventario, pendientes, costos y servicio por rol. Calcular amplificación sólo cuando el denominador sea positivo y no descartar rondas difíciles sin declarar un período común.",
        ),
        (
            "Debriefing",
            "Reconstruir un episodio de sobrepedido usando dos decisiones sucesivas y una demora. Separar explicación del sistema de atribuciones personales; entregar costos desagregados, gráfico y propuesta de política.",
        ),
    ),
    (
        "No sustituir personas sin registrar el cambio de rol.",
        "No atribuir los datos de la fotografía a una partida jugada.",
        "Puntaje del simulador y rúbrica docente tienen propósitos distintos.",
    ),
    (
        ("Posición", "Disponible + tránsito − pendiente [cajas/rol]."),
        ("Pedido", "min(límite, max(0, objetivo − posición)) [cajas/ronda]."),
        (
            "Amplificación",
            "Var(pedidos) / Var(demanda) [razón]; no definida para varianza de demanda cero.",
        ),
        (
            "Costo",
            "Sumar mantenimiento y faltantes con tarifas y horizonte de la partida; conservar u.m. y período.",
        ),
    ),
    (
        "Fotografía resuelta de los cuatro roles.",
        "Dos exportaciones completas, configuración y registro de intervención.",
        "Gráficos alineados por ronda, tabla de costos y servicio.",
        "Análisis causal de una demora y reflexión de colaboración por rol.",
    ),
    (
        "¿Compartir información garantiza costo mínimo?",
        "¿Cómo separar el aprendizaje de una persona del efecto de una política?",
        "¿Qué indicador usar si la demanda es constante?",
    ),
    ("mit",),
    "multijugador/",
    180,
)


_guia(
    5,
    "Rutas factibles con capacidad y ventanas",
    "LOG-AREA-TMS",
    (
        "LOGT-DISENO-DE-RUTAS",
        "LOGT-MODELACION-DEL-TRANSPORTE",
        "COEX-LOGISTICA-INTERNACIONAL",
    ),
    ("p05-nodos",),
    "Dos vehículos de ocho cajas deben atender cinco clientes y volver al depósito. La red de aula usa distancia Manhattan y ventanas explícitas; el reto es demostrar factibilidad antes de comparar costo.",
    (
        "Construir la matriz completa de distancias y tiempos para seis nodos sin mezclar kilómetros y minutos.",
        "Validar carga, visitas únicas, inicio de servicio, espera y retorno de dos planes de distribución.",
        "Comparar costo y puntualidad sin afirmar optimalidad por obtener una ruta corta.",
    ),
    (
        (
            "Red y magnitudes",
            "d(i,j) = |x_i − x_j| + |y_i − y_j| en kilómetros. Viaje = 2 × d minutos. Es una red sintética ortogonal, no distancia vial ni geográfica. La matriz debe tener diagonal cero, ser simétrica y no contener costos negativos.",
        ),
        (
            "Propagación del reloj",
            "Llegada = fin del servicio anterior + viaje. Inicio = max(llegada, abre); fin = inicio + servicio. Es puntual si inicio ≤ cierra. El criterio es inicio de atención, no hora de salida del cliente.",
        ),
        (
            "Factibilidad y objetivo",
            "Cada cliente se visita una vez; demanda total por vehículo ≤ 8 y retorno obligatorio. Costo de aula = 3 u.m./km + 10 u.m. por vehículo utilizado. Una solución factible no demuestra que sea mínima.",
        ),
    ),
    (
        (
            "Modelar",
            "Crear la matriz 6×6 y verificar seis ceros diagonales y simetría. Identificar depósito D y demanda total de 12 cajas; registrar dos vehículos independientes.",
        ),
        (
            "Plan base",
            "Asignar vehículo 1 D–A–B–C–D y vehículo 2 D–E–F–D. Calcular carga al salir y después de cada entrega; no realizar entregas parciales.",
        ),
        (
            "Propagar horarios",
            "Partir ambos en minuto 0. Registrar llegada, espera, inicio y fin por cliente; luego retorno. Comprobar cada ventana y capacidad antes de sumar costos.",
        ),
        (
            "Plan alternativo",
            "Evaluar D–A–B–D y D–E–F–C–D con las mismas entradas. Comparar kilómetros, cargas, puntualidad y máximo tiempo de retorno; no escoger sólo un indicador favorable.",
        ),
        (
            "Explorar",
            "Proponer un tercer plan y someterlo a idénticos controles. Probar una asignación de más de ocho cajas y mostrar por qué se rechaza, sin convertirla en una alternativa válida.",
        ),
        (
            "Contrastar virtualmente",
            "Usar Transporte en el simulador de operaciones. Allí la distancia es euclidiana y existe recarga: declarar estas diferencias y guardar su exportación como experimento separado.",
        ),
    ),
    (
        "La ventana limita inicio de servicio en este caso.",
        "Distancia Manhattan del aula y euclidiana del simulador no son intercambiables.",
        "No excluir clientes pendientes del indicador de cobertura.",
    ),
    (
        (
            "Carga inicial",
            "Σ demanda de clientes asignados [cajas/vehículo], máximo 8.",
        ),
        ("Puntualidad", "Clientes cuyo inicio ≤ cierre / 5 × 100 [%]."),
        ("Costo", "3 × km totales + 10 × vehículos utilizados [u.m.]."),
        (
            "Duración",
            "Máximo retorno de ambos vehículos [min] y suma de sus tiempos [vehículo·min], informar por separado.",
        ),
    ),
    (
        "Matriz de distancias/tiempos y diagrama de red con escala docente.",
        "Dos hojas de ruta con carga y horarios por parada.",
        "Tabla de factibilidad y costo de tres planes, incluido un rechazo explicado.",
        "Mapa comparativo, exportación virtual y límites de extrapolación.",
    ),
    (
        "¿Una menor distancia garantiza menor duración?",
        "¿Cómo cambia el criterio si la ventana exige terminar la descarga?",
        "¿Qué datos faltan para usar este modelo en una flota real?",
    ),
    ("cvrp", "vrptw"),
    "operaciones/?caso=transporte-rutas&semilla=42",
    180,
)

_guia(
    6,
    "Contingencias y replanificación de última milla",
    "LOG-AREA-TMS",
    (
        "LOGT-DISENO-DE-RUTAS",
        "LOGT-MODELACION-DEL-TRANSPORTE",
        "COEX-COMERCIO-ELECTRONICO",
    ),
    ("p05-nodos", "p06-contingencias"),
    "Antes de la salida se anuncia una demora de 30 minutos en el arco B–C, en ambos sentidos. El coordinador puede conservar el plan base o reasignar visitas sin aumentar vehículos ni retirar clientes.",
    (
        "Identificar qué compromiso incumple el plan fijo bajo la incidencia y calcular su retraso.",
        "Verificar un plan alternativo que conserve demanda, flota, capacidad y compromisos.",
        "Presentar una decisión de contingencia con impacto en puntualidad, recorrido y horario final.",
    ),
    (
        (
            "Evento y política",
            "La incidencia está disponible antes de salir; no se está modelando información futura revelada durante el recorrido. Suma 30 minutos al arco B–C y C–B, sin cambiar kilómetros ni servicios.",
        ),
        (
            "Restricciones conservadas",
            "El escenario base y el congestionado comparten nodos, ventanas, vehículos y demanda. Una replanificación válida redistribuye clientes y secuencias; ampliar ventanas para esconder retrasos es cambiar el problema.",
        ),
        (
            "Comparación pareada",
            "Medir el plan fijo con y sin incidencia identifica el efecto de la demora. Luego comparar planes bajo la misma demora identifica el efecto de la política. Son contrastes diferentes.",
        ),
    ),
    (
        (
            "Recuperar base",
            "Resolver la práctica 5 y conservar sus hojas de ruta. Guardar archivo de incidencias con identificación y momento conocido.",
        ),
        (
            "Aplicar demora",
            "Recalcular D–A–B–C–D agregando 30 minutos sólo al arco B–C; dejar D–E–F–D intacto. Propagar el retraso a todas las paradas posteriores.",
        ),
        (
            "Diagnosticar",
            "Señalar el primer incumplimiento, su retraso y la hora de retorno. Mostrar qué parte es viaje regular, servicio, espera o demora extraordinaria.",
        ),
        (
            "Reasignar",
            "Evaluar D–A–B–D y D–E–F–C–D sin cruzar B–C. Comprobar cargas 5 y 7 cajas, ventanas y cobertura completa antes de recomendar.",
        ),
        (
            "Comunicar",
            "Preparar avisos docentes por cliente: compromiso original, nuevo inicio previsto y responsable simbólico. No enviar mensajes a personas ni empresas reales.",
        ),
        (
            "Analizar robustez",
            "Repetir demora en 0, 15 y 30 minutos para ambos planes. Graficar puntualidad y retorno; concluir cuándo deja de ser válida cada política y qué información adicional necesita.",
        ),
    ),
    (
        "No retirar del denominador al cliente tardío.",
        "No agregar vehículos ficticios ni alterar capacidad.",
        "La replanificación conocida antes de salir no demuestra capacidad de control en tiempo real.",
    ),
    (
        ("Retraso", "max(0, inicio de servicio − cierre) [min/cliente]."),
        ("Cobertura", "Clientes entregados / 5 × 100 [%]."),
        ("Puntualidad", "Clientes atendidos dentro de ventana / 5 × 100 [%]."),
        (
            "Impacto",
            "Indicador congestionado − mismo indicador base, conservando unidad y plan.",
        ),
    ),
    (
        "Tres hojas de ruta: base, fija con demora y alternativa con demora.",
        "Matriz de cargas/ventanas y descomposición temporal.",
        "Gráfico de sensibilidad 0/15/30 min con tabla fuente.",
        "Plan de comunicación simulado y recomendación razonada.",
    ),
    (
        "¿Qué cambia si la incidencia se conoce después de atender A?",
        "¿Reasignar clientes tiene costo operativo no incluido?",
        "¿Cómo integrar devoluciones sin perder trazabilidad del pedido?",
    ),
    ("cvrp", "vrptw"),
    "operaciones/?caso=transporte-rutas&semilla=42",
    180,
)

_guia(
    7,
    "Abastecimiento, capacidad y balance de estaciones",
    "LOG-AREA-PRODUCCION",
    (
        "ADEM-ADMINISTRACION-DE-OPERACIONES",
        "LOGT-LOGISTICA-DE-PRODUCCION",
        "LOGT-OPTIMIZACION-DE-OPERACIONES",
    ),
    ("p07-estaciones",),
    "Seis unidades atraviesan tres estaciones en orden. El grupo debe explicar el cuello de botella y contrastar una mejora de S2 sin convertir capacidad teórica en producción real del laboratorio.",
    (
        "Construir 18 eventos de procesamiento con inicio/fin factibles y orden conservado.",
        "Calcular makespan del lote y capacidad estable antes y después del cambio.",
        "Explicar por qué mejora de S2 desplaza el cuello de botella y no elimina todas las esperas.",
    ),
    (
        (
            "Dependencias",
            "Una unidad empieza una estación sólo cuando terminó la anterior y el servidor está libre. Inicio(i,j) = max(fin(i−1,j), fin(i,j−1)). Al comienzo las fronteras valen cero. Cada estación tiene un servidor.",
        ),
        (
            "Lote y régimen",
            "Makespan mide el fin de la última unidad del lote desde tiempo cero. Capacidad estable = 60 / mayor ciclo, en unidades/hora, bajo el modelo determinista. El primer lote incluye llenado/vaciado; 6/makespan no es necesariamente la capacidad de régimen.",
        ),
        (
            "Alcance",
            "Buffer ilimitado y ausencia de fallas son supuestos del caso. Suprimirlos exige otra lógica de eventos. Los ciclos no provienen de cronometraje de maquetas.",
        ),
    ),
    (
        (
            "Preparar",
            "Dibujar S1→S2→S3, conservar lote 6 y ciclos. Identificar unidad y estación en cada fila; registrar base y alternativa sin mezclar sus eventos.",
        ),
        (
            "Programar base",
            "Completar inicios/fines de seis unidades por tres estaciones con la recurrencia. Rechazar solapamientos sobre un servidor y saltos de orden de una unidad.",
        ),
        (
            "Visualizar",
            "Construir Gantt con colores por estación y etiquetas de unidad; mostrar esperas e inactividad. Obtener makespan y capacidad estable, cada uno con su unidad.",
        ),
        (
            "Balancear",
            "Cambiar únicamente ciclo S2 de 5 a 3 min/unidad y repetir los 18 eventos. Identificar el nuevo cuello de botella y comprobar que el lote sigue teniendo seis salidas.",
        ),
        (
            "Contrastar",
            "Abrir Smart factory y ejecutar base/alternativa con misma semilla. Su motor avanza por intervalos y limita buffers: explicar por qué sus minutos no deben coincidir con esta recurrencia.",
        ),
        (
            "Concluir",
            "Entregar ahorro de makespan, aumento de capacidad y una propuesta de medición presencial separada. Considerar costo, calidad y parada de implementación no incluidos aquí.",
        ),
    ),
    (
        "Una unidad no puede procesarse en dos estaciones a la vez.",
        "Una estación no atiende dos unidades simultáneas.",
        "No reportar capacidad calculada como disponibilidad instalada.",
    ),
    (
        ("Makespan", "Fin de unidad 6 en S3 − inicio del lote [min]."),
        ("Capacidad estable", "60 / max(ciclos) [unidades/h]."),
        ("Ahorro de lote", "(Makespan base − alternativa) / base × 100 [%]."),
    ),
    (
        "Dos tablas de 18 eventos con dependencias verificables.",
        "Gantt base y alternativa con tiempos de espera.",
        "Tabla de makespan/capacidad y cuello de botella por escenario.",
        "Exportación Smart factory y discusión de diferencias de modelo.",
    ),
    (
        "¿Qué ocurre si mejorar S2 requiere diez minutos de parada?",
        "¿En qué lote se recupera esa parada?",
        "¿Qué cambiaría con buffers finitos y bloqueo de estaciones?",
    ),
    ("simpy",),
    "operaciones/?caso=fabrica-flujo&semilla=42",
    180,
)

_guia(
    8,
    "Calidad, devoluciones y recuperación de materiales",
    "LOG-AREA-PRODUCCION",
    (
        "LOGT-INGENIERIA-DE-LA-CALIDAD",
        "LOGT-OPTIMIZACION-DE-OPERACIONES",
        "LOGT-LOGISTICA-DE-PRODUCCION",
    ),
    ("p08-recuperacion",),
    "Tres lotes devueltos se inspeccionan y clasifican en reutilizable, reproceso o descarte. Se debe conciliar el material y justificar el beneficio inmediato sin contabilizar dos veces lo pendiente de tratar.",
    (
        "Comprobar balance de los tres lotes y separar 60 unidades en destinos mutuamente excluyentes.",
        "Calcular recuperación inmediata y costo de inspección por unidad evaluada.",
        "Diseñar criterios de liberación y un experimento de calidad que no prometa recuperación aún no verificada.",
    ),
    (
        (
            "Estados excluyentes",
            "Una unidad pertenece a un destino a la vez: reutilizable, retenida para reproceso o descarte. Entrada = suma de destinos. Reproceso es una cola de trabajo, no producto liberado.",
        ),
        (
            "Rendimiento",
            "Recuperación inmediata = reutilizable / entrada. Para recuperación posterior se registra una nueva inspección con salidas buenas, rechazadas y aún pendientes, evitando sumar entrada de reproceso otra vez al lote original.",
        ),
        (
            "Costo y decisión",
            "Costo de inspección por unidad = costo total / entrada inspeccionada. No representa costo completo de recuperación: faltan transporte, tratamiento, almacenamiento, disposición y pruebas.",
        ),
    ),
    (
        (
            "Clasificar",
            "Verificar unidades y separar físicamente con fichas simbólicas si se hace en aula. Establecer criterios docentes de aceptación por condición; no aplicar estas reglas a productos reales.",
        ),
        (
            "Conciliar",
            "Calcular entrada − reutilizable − reproceso − descarte por lote. Toda diferencia debe bloquear el cierre del análisis y generar investigación.",
        ),
        (
            "Cuantificar",
            "Sumar destinos, recuperación inmediata y costo de inspección por unidad. Graficar barras apiladas conservando la escala de unidades.",
        ),
        (
            "Diseñar reproceso",
            "Proponer dos escenarios de éxito para las 17 unidades retenidas, por ejemplo 50% y 80%, dejando explícito que son proyecciones. No mezclar proyección con recuperación observada.",
        ),
        (
            "Controlar calidad",
            "Diseñar lista de liberación con criterio, método, evidencia y verificador. Relacionar fallas y calibración de Smart factory como otro experimento virtual, sin atribuirle los lotes DEV.",
        ),
        (
            "Entregar",
            "Presentar balance, decisión costo/beneficio con costos faltantes y mapa de logística inversa. Conservar estado pendiente cuando la evidencia no permite liberar.",
        ),
    ),
    (
        "Reproceso pendiente no aumenta disponibilidad.",
        "Los porcentajes proyectados no se presentan como mediciones.",
        "Una situación insegura se detiene y se comunica; no se compensa con puntaje.",
    ),
    (
        (
            "Balance",
            "Entrada − reutilizable − reproceso − descarte = 0 [unidades/lote].",
        ),
        ("Recuperación inmediata", "Σ reutilizable / Σ entrada × 100 [%]."),
        ("Inspección unitaria", "Σ costo de inspección / Σ entrada [u.m./unidad]."),
    ),
    (
        "Conciliación por lote y agregada con destinos excluyentes.",
        "Diagrama de estados y gráfico de destino de 60 unidades.",
        "Tabla separada de escenarios de reproceso y supuestos.",
        "Lista de liberación, costos faltantes y conclusión trazable.",
    ),
    (
        "¿Qué prueba permite convertir reproceso en material liberado?",
        "¿Cómo evitar doble conteo al recuperar un lote?",
        "¿Qué costo ambiental podría cambiar la decisión económica?",
    ),
    ("gs1",),
    "operaciones/?caso=fabrica-flujo&semilla=42",
)


_guia(
    9,
    "Expediente internacional y conciliación documental",
    "LOG-AREA-COMERCIO",
    (
        "COEX-COMERCIO-EXTERIOR",
        "COEX-GESTION-ESTRATEGICA-DEL-COME-E6C7A3",
        "COEX-INCOTERMS-2020",
        "COEX-NEGOCIACION-COMERCIAL-INTERNACIONAL",
        "COEX-PROCEDIMIENTOS-ELECTRONICOS-5D0EED",
        "COEX-SISTEMAS-DE-VALORACION-Y-CLA-4F6AC6",
        "LOGT-TECNICAS-ADUANERAS",
    ),
    ("p09-documentos",),
    "Una operación académica EXP-DOC-01 contiene tres productos y discrepancias entre factura y empaque. El equipo construye un expediente de revisión y una matriz de responsabilidades sin transmitir información a plataformas aduaneras reales.",
    (
        "Detectar las dos líneas inconsistentes y conciliar cantidad, peso neto y valor de factura con sus unidades.",
        "Preparar un expediente docente rotulado y una matriz de responsabilidades sustentada en fuentes oficiales consultadas.",
        "Explicar qué dato no puede deducirse del caso y debe verificarse antes de un trámite real.",
    ),
    (
        (
            "Consistencia documental",
            "Identificador, descripción, cantidad y peso deben poder cotejarse entre los documentos del caso. La tabla distingue cajas de kilogramos. Una diferencia de peso no se corrige cambiando cantidad sin evidencia.",
        ),
        (
            "Alcance aduanero",
            "SENAE publica el proceso oficial de exportación y la información que acompaña la declaración. La práctica consiste en contrastar esa fuente, registrar fecha y separar requisitos aplicables de supuestos del ejercicio; no genera una DAE ni autorización de salida.",
        ),
        (
            "Responsabilidades comerciales",
            "Las reglas Incoterms se consultan en ICC en la edición aplicable y en conjunto con el contrato. Aquí se prepara una matriz para contrastar tareas, costos y riesgos; no se reproduce su texto ni se presume una regla elegida.",
        ),
    ),
    (
        (
            "Preparar expediente",
            "Crear carpeta EXP-DOC-01 con índice, CSV y hoja de fuentes fechadas. Rotular cada página SIMULADO — SIN VALIDEZ; usar exportador/comprador simbólicos sin RUC o datos personales.",
        ),
        (
            "Cotejar",
            "Cruzar por SKU cantidades y pesos de factura/empaque. Calcular diferencias por línea antes de sumar. Registrar documento de origen y campo en cada hallazgo.",
        ),
        (
            "Valorar caso",
            "Calcular valor de factura como cantidad × precio unitario. Mantener u.m. docentes; no convertir este cálculo en valor aduanero ni agregar tasas no verificadas.",
        ),
        (
            "Consultar fuentes",
            "Abrir SENAE e ICC, identificar fecha y alcance. Construir lista de campos/requisitos del caso y matriz de tareas con la columna fuente o pendiente de contrastar.",
        ),
        (
            "Negociar y corregir",
            "Representar dos equipos con objetivos logísticos distintos; registrar alternativa, criterio y acuerdo simbólico. Emitir versión corregida sólo después de documentar qué evidencia justificaría cada cambio; conservar original.",
        ),
        (
            "Revisar",
            "Un segundo equipo audita índice, consistencia, referencias y rótulos. Entregar pendientes explícitos de clasificación, valoración y documentación que no pueden resolverse con este dataset.",
        ),
    ),
    (
        "No ingresar documentos académicos en ECUAPASS.",
        "No inventar códigos arancelarios, convenios, impuestos ni responsables reales.",
        "No presentar factura sintética como base de asesoría aduanera.",
    ),
    (
        ("Cantidad", "Σ cajas por documento; diferencias por SKU antes del agregado."),
        ("Peso neto", "Σ kg por documento, sin sumar cajas ni peso bruto."),
        ("Valor de factura docente", "Σ cantidad_factura × precio_unitario [u.m.]."),
        ("Consistencia", "Líneas con cantidad y peso coincidentes / 3 × 100 [%]."),
    ),
    (
        "Índice y expediente simulado con originales/versiones corregidas.",
        "Matriz de las dos discrepancias con fuente, impacto y acción.",
        "Hoja de referencias oficiales fechadas y responsabilidades por contrastar.",
        "Acta académica de negociación y lista de datos que faltan para una operación real.",
    ),
    (
        "¿Por qué valor de factura y valor aduanero no deben equipararse automáticamente?",
        "¿Qué documento respalda una corrección de peso?",
        "¿Cómo cambia la asignación de tareas con otra regla comercial?",
    ),
    ("senae", "icc"),
    "operaciones/?caso=puerto-contenedores&semilla=42",
    180,
)

_guia(
    10,
    "Terminal, colas y compromisos transfronterizos",
    "LOG-AREA-COMERCIO",
    (
        "COEX-OPERACIONES-DE-COMERCIO-EXTERIOR",
        "LOGT-DISTRIBUCION-FISICA-INTERNACIONAL",
        "COEX-LOGISTICA-INTERNACIONAL",
    ),
    ("p10-terminal",),
    "Cuatro contenedores docentes llegan a una grúa única. El equipo compara atención FIFO con cinco o tres minutos por unidad y analiza esperas, permanencia y compromisos de salida sin interpretar el reloj como tiempos portuarios reales.",
    (
        "Reconstruir inicio, fin, espera y permanencia de los cuatro contenedores en ambos escenarios.",
        "Calcular promedios y cumplimiento conservando todos los contenedores del caso.",
        "Relacionar una mejora de servicio con la cola sin atribuirle automáticamente una reducción igual de permanencia.",
    ),
    (
        (
            "Cola FIFO",
            "Inicio_i = max(llegada_i, fin_anterior); fin_i = inicio_i + servicio_i. Espera = inicio − llegada y permanencia = fin − llegada. La primera atención no puede empezar antes de su arribo.",
        ),
        (
            "Recurso limitado",
            "Sólo una unidad ocupa la grúa a la vez y el servicio no se interrumpe. El caso no modela atraque, inspección ni transporte de patio. Añadirlos requiere nuevas etapas y recursos, no inflar un único tiempo.",
        ),
        (
            "Compromiso",
            "Aquí se cumple si fin ≤ límite_salida. A diferencia de la práctica de rutas, el compromiso se aplica al fin; la definición debe acompañar cada indicador.",
        ),
    ),
    (
        (
            "Preparar",
            "Ordenar arribos 0, 2, 4 y 6; fijar FIFO, un servidor y unidad minuto. Dibujar el proceso llegada→espera→servicio→salida.",
        ),
        (
            "Programar base",
            "Construir cuatro filas con llegada, inicio, fin, espera y permanencia usando servicio_base. Comprobar ausencia de solapamiento del recurso.",
        ),
        (
            "Comparar",
            "Repetir con servicio_alternativa manteniendo arribos y límites. Crear Gantt y comparar medias, máximo de cola y número de salidas puntuales.",
        ),
        (
            "Añadir sensibilidad",
            "Recalcular servicio de 2, 3 y 5 minutos. Explicar en qué caso desaparece la espera bajo estos arribos y por qué no demuestra ausencia de congestión con otra demanda.",
        ),
        (
            "Experimentar en puerto",
            "Abrir Puerto del simulador y comparar preparación de grúa y secuencia documental conservando semilla. Su lógica incluye otras etapas: exportar separadamente y no exigir coincidencia de resultados.",
        ),
        (
            "Concluir",
            "Proponer indicadores por etapa para una observación real autorizada y un criterio de escalamiento. Identificar qué restricciones fronterizas o de frío quedan fuera del modelo tabular.",
        ),
    ),
    (
        "No iniciar descarga antes de llegada ni ocupar dos veces la grúa.",
        "No excluir unidades pendientes del cumplimiento.",
        "No equiparar compromiso docente con requisito legal de cadena de frío.",
    ),
    (
        ("Espera", "Inicio de servicio − llegada [min/contenedor]."),
        ("Permanencia", "Fin de servicio − llegada [min/contenedor]."),
        ("Cumplimiento", "Contenedores con fin ≤ límite / 4 × 100 [%]."),
        (
            "Utilización del horizonte",
            "Σ servicio / (último fin − primera llegada) × 100 [%] con horizonte explícito.",
        ),
    ),
    (
        "Dos tablas de eventos y dos Gantt sin solapamientos.",
        "Promedios, extremos y tabla de cumplimiento de cuatro unidades.",
        "Sensibilidad de servicio y exportación del caso Puerto.",
        "Mapa de etapas ausentes y protocolo de datos reales por verificar.",
    ),
    (
        "¿Cómo afecta una inspección a un contenedor si la grúa queda libre?",
        "¿Por qué servicio y permanencia disminuyen en cantidades diferentes?",
        "¿Qué cambia si el compromiso mide inicio en vez de fin?",
    ),
    ("simpy",),
    "operaciones/?caso=puerto-contenedores&semilla=42",
)

_guia(
    11,
    "Trazabilidad, calidad de datos e integración de maqueta",
    "LOG-AREA-ERP",
    (
        "LOGT-TIC-APLICADAS-A-LA-LOGISTICA",
        "LOGT-SIMULADORES-LOGISTICOS",
        "COEX-COMERCIO-ELECTRONICO",
    ),
    ("p11-eventos",),
    "Una torre de control recibe seis filas de eventos con tres errores intencionales. El equipo debe detectarlos, conservar originales y proponer un contrato de integración que no envíe órdenes a hardware.",
    (
        "Identificar ID duplicado, sobredespacho y secuencia temporal imposible con evidencia por fila.",
        "Reconstruir cinco eventos únicos sin contar ubicación como creación de inventario.",
        "Diseñar un esquema de importación sólo lectura, idempotente y con cola de rechazos verificable.",
    ),
    (
        (
            "Identidad e idempotencia",
            "Un evento tiene una clave estable. Reintentar la misma captura no debe duplicar el efecto operativo. Duplicado exacto y colisión con contenido diferente son casos distintos y deben conservarse para revisión.",
        ),
        (
            "Dimensiones y contexto",
            "GS1 organiza visibilidad mediante datos del objeto, momento, lugar y contexto. El ejercicio usa un subconjunto educativo; nombrar columnas parecidas no demuestra conformidad EPCIS ni compatibilidad con una API.",
        ),
        (
            "Integración gradual",
            "Comenzar con CSV de sólo lectura y recursos verificados. Un mensaje de sensor es una observación con procedencia y calidad, no autorización para activar un robot. Tiempo del dispositivo, captura y reloj simulado deben ser distintos.",
        ),
    ),
    (
        (
            "Conservar original",
            "Guardar las seis filas con hash. Agregar número de fila sin cambiar ID ni orden. Definir clave, tipos, unidad, categorías permitidas y tratamiento de faltantes.",
        ),
        (
            "Detectar duplicados",
            "Agrupar por evento_id y cotejar contenido; marcar EV-02 repetido exacto. Crear vista única para análisis sin borrar filas del archivo fuente.",
        ),
        (
            "Auditar balance",
            "Agrupar recepción y despacho por objeto. No sumar ubicar como entrada. Encontrar L-01 con 11 despachadas y 10 recibidas; bloquear la aceptación del lote hasta investigar.",
        ),
        (
            "Auditar tiempo",
            "Ordenar eventos por objeto y minuto; comprobar que recepción precede despacho. Localizar L-02 con salida anterior a entrada y conservar el hallazgo aunque el balance de cantidades cierre.",
        ),
        (
            "Diseñar contrato",
            "Definir importación con versión de esquema, identificador de fuente, permisos de lectura, validaciones y cuarentena de errores. Probar reimportar el mismo archivo y exigir cero efectos nuevos; no conectar dispositivos reales.",
        ),
        (
            "Visualizar y transferir",
            "Crear línea temporal por objeto, tabla de rechazos y resumen de calidad. Abrir misión robótica para estudiar ruta/energía virtual y definir qué eventos de observación podrían registrarse, sin convertirla en control de hardware.",
        ),
    ),
    (
        "No eliminar evidencia original para ocultar fallos.",
        "Una cantidad conciliada no demuestra secuencia temporal válida.",
        "El contrato propuesto no instala conectores ni autoriza equipos.",
    ),
    (
        (
            "Duplicados",
            "Filas − eventos_id únicos [filas]; informar colisiones por separado.",
        ),
        (
            "Balance por objeto",
            "Recibido − despachado [cajas], excluyendo ubicar del numerador.",
        ),
        (
            "Integridad temporal",
            "Objetos sin salida anterior a recepción / objetos revisados × 100 [%].",
        ),
    ),
    (
        "Archivo original, vista única y bitácora de transformación.",
        "Tres hallazgos con fila, regla, impacto y acción sin borrar evidencia.",
        "Diagrama de importación, diccionario y prueba de idempotencia documentada.",
        "Cronología por objeto y plan de integración sólo lectura condicionado a verificación.",
    ),
    (
        "¿Cómo distinguir un reintento de dos movimientos legítimos iguales?",
        "¿Qué ocurre si el reloj del sensor está desajustado?",
        "¿Por qué una lectura no autoriza una acción física?",
    ),
    ("gs1",),
    "operaciones/?caso=robotica-mision&semilla=42",
    180,
)

_guia(
    12,
    "Analítica e IA: validar antes de recomendar",
    "LOG-AREA-ERP",
    (
        "LOGT-TIC-APLICADAS-A-LA-LOGISTICA",
        "LOGT-INVESTIGACION-DE-OPERACIONES",
        "ADEM-ADMINISTRACION-DE-OPERACIONES",
    ),
    ("p12-pronosticos",),
    "El candidato predictivo mejora la validación, pero empata con persistencia en prueba. La práctica enseña a auditar recomendaciones, conservar particiones temporales y comunicar incertidumbre sin vender una mejora inexistente.",
    (
        "Calcular cuatro MAE por partición y candidato usando observaciones idénticas.",
        "Seleccionar con validación antes de abrir prueba y conservar la decisión aunque no mejore el resultado final.",
        "Construir un tablero explicable con tabla fuente, limitaciones y criterio de supervisión humana.",
    ),
    (
        (
            "Separación experimental",
            "El CSV contiene predicciones congeladas para auditoría. No permite reconstruir entrenamiento ni demostrar cómo se obtuvo el candidato. La prueba nunca selecciona el método; un empate final se informa sin cambiar retrospectivamente la regla.",
        ),
        (
            "Comparación honesta",
            "MAE promedia magnitudes de error en la unidad de demanda. Comparar siempre el mismo horizonte y filas. Informar error firmado para distinguir sesgo; un empate en MAE no demuestra que las predicciones ni sus costos sean iguales.",
        ),
        (
            "Uso responsable",
            "NIST propone documentar contexto y evaluación de riesgos de IA. En esta práctica se define quién revisa una recomendación, qué evidencia la sostiene y qué límite impide automatizar una decisión; no se certifica el modelo.",
        ),
    ),
    (
        (
            "Congelar protocolo",
            "Registrar particiones, métrica MAE, desempate y decisión prevista antes de observar prueba. Conservar hash y versión de las predicciones.",
        ),
        (
            "Validar",
            "Usar sólo semanas 9–12; calcular errores absolutos y firmados de persistencia y candidato. Seleccionar el menor MAE y registrar hora docente y motivo.",
        ),
        (
            "Abrir prueba",
            "Evaluar semanas 13–16 una sola vez con la selección congelada. Mostrar los cuatro MAE y explicar el empate final; no cambiar de modelo para mejorar la narrativa.",
        ),
        (
            "Explicar",
            "Crear gráfico temporal, tabla de errores y tarjeta de modelo con uso previsto, datos sintéticos, horizonte, limitaciones y responsable de revisión simbólico.",
        ),
        (
            "Entrenar en simulador",
            "Abrir IA de operaciones y seguir sus pasos entrenamiento→selección→prueba con 60 semanas y modelos realmente disponibles. Guardar partida y exportar; no confundirla con el CSV de auditoría.",
        ),
        (
            "Decidir continuidad",
            "Definir condición de rechazo por fuga temporal, alerta por sesgo y revisión humana antes de ordenar existencias. Estimar datos adicionales y una prueba prospectiva; no instalar proveedor externo ni usar credenciales personales.",
        ),
    ),
    (
        "No presentar el candidato del CSV como un modelo instalado.",
        "No seleccionar usando prueba ni retirar semanas adversas.",
        "Una recomendación algorítmica no crea compras o reservas.",
    ),
    (
        (
            "MAE por bloque",
            "Σ |real − predicción| / 4 [cajas/semana] para cada modelo y partición.",
        ),
        ("Sesgo por bloque", "Σ (real − predicción) / 4 [cajas/semana]."),
        (
            "Mejora relativa",
            "(MAE referencia − MAE candidato) / MAE referencia × 100 [%]; no definida si referencia = 0.",
        ),
    ),
    (
        "Protocolo de selección y predicciones congeladas con hash.",
        "Cuatro MAE, errores firmados y gráfico con separación de bloques.",
        "Tarjeta de modelo y matriz de riesgos con acciones de revisión.",
        "Exportación IA propia y conclusión que reconozca empate, límites y siguiente prueba.",
    ),
    (
        "¿Por qué ganar validación no garantiza ganar prueba?",
        "¿Puede un modelo con igual MAE generar distinto costo de inventario?",
        "¿Qué evidencia pedir antes de automatizar una compra?",
    ),
    ("series", "mae", "nist"),
    "operaciones/?caso=ia-pronostico&semilla=42",
    180,
)


RUBRICA = (
    (
        "Preparación y calidad de datos",
        20,
        "CSV original, hash, diccionario y partición/escenario conservados.",
    ),
    (
        "Procedimiento y trazabilidad",
        25,
        "Pasos, decisiones, eventos y correcciones verificables sin alterar evidencia original.",
    ),
    (
        "Cálculo, comparación y restricciones",
        30,
        "Fórmulas con unidades, controles del caso, comparación y análisis de resultados adversos.",
    ),
    (
        "Comunicación y reproducibilidad",
        15,
        "Tablas fuente, gráficos accesibles, conclusión proporcional y paquete de entrega reproducible.",
    ),
    (
        "Colaboración y cuidado",
        10,
        "Roles rotativos, revisión cruzada, accesibilidad, incidencias y límites del trabajo físico.",
    ),
)
NIVELES = (
    (
        "Completo",
        1.0,
        "Cumple todos los elementos del criterio con evidencia verificable y sin errores materiales.",
    ),
    (
        "Suficiente",
        0.75,
        "Demuestra el criterio; presenta una omisión menor que no cambia la decisión ni impide reproducir el cálculo.",
    ),
    (
        "Parcial",
        0.5,
        "Aporta evidencia incompleta o un error que afecta interpretación; identifica la limitación y la corrección necesaria.",
    ),
    (
        "No demostrado",
        0.0,
        "No entrega evidencia, mezcla datos reales/sintéticos o sostiene la conclusión con cálculos que no pueden comprobarse.",
    ),
)
for _clave, _guia_datos in GUIAS.items():
    _guia_datos["rubrica"] = deepcopy(RUBRICA)
    _guia_datos["niveles"] = deepcopy(NIVELES)
    _guia_datos["version"] = VERSION
    _guia_datos["datos"] = "sinteticos"
    _guia_datos["autoriza_presencial"] = False


def cobertura_asignaturas():
    """Matriz de contenidos docentes, sin modificar la malla ni crear asignaturas."""
    return [
        {
            "codigo": codigo,
            "nombre": fila["nombre"],
            "carrera": fila["carrera"],
            "practicas": [
                clave for clave, guia in GUIAS.items() if codigo in guia["asignaturas"]
            ],
        }
        for codigo, fila in MATRIZ_ASIGNATURAS.items()
    ]


def recursos_datasets():
    return [
        {
            "clave": clave,
            "titulo": dataset["titulo"],
            "seccion": "4.4",
            "carpeta": "Datos reproducibles · Prácticas por área",
            "nombre": clave + "-v1.csv",
            "contenido": dataset_csv(clave).encode("utf-8"),
            "mime": "text/csv",
            "descripcion": dataset["descripcion"],
            "sha256": checksum_dataset(clave),
        }
        for clave, dataset in DATASETS.items()
    ]


def _p(texto):
    return "<p>" + escape(str(texto), quote=True) + "</p>"


def _lista(elementos, ordenada=False):
    etiqueta = "ol" if ordenada else "ul"
    return (
        "<"
        + etiqueta
        + ">"
        + "".join("<li>" + escape(str(x), quote=True) + "</li>" for x in elementos)
        + "</"
        + etiqueta
        + ">"
    )


def _tabla(cabeceras, filas, titulo):
    return (
        '<div class="tabla"><table><caption>'
        + escape(titulo)
        + "</caption><thead><tr>"
        + "".join('<th scope="col">' + escape(str(x)) + "</th>" for x in cabeceras)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + escape(str(x)) + "</td>" for x in fila) + "</tr>"
            for fila in filas
        )
        + "</tbody></table></div>"
    )


def documento_html(clave, guia=None):
    """Guía accesible sin scripts, dependencias remotas ni acciones operativas."""
    ficha = GUIAS[clave] if guia is None else guia
    secciones = (
        '<section id="objetivos"><h2>Resultados de aprendizaje</h2>'
        + _lista(ficha["objetivos"])
        + "</section>"
    )
    secciones += '<section id="preparacion"><h2>Preparación y roles</h2>' + _lista(
        ficha["prerrequisitos"]
    )
    secciones += _p(
        "Equipo sugerido: operador, analista, auditor y relator; rotar funciones. Un ordenador común y una hoja de cálculo bastan para los casos tabulares. La alternativa manual utiliza las mismas tablas."
    )
    secciones += (
        _tabla(
            ("Código", "Asignatura", "Carrera"),
            [
                (x, MATRIZ_ASIGNATURAS[x]["nombre"], MATRIZ_ASIGNATURAS[x]["carrera"])
                for x in ficha["asignaturas"]
            ],
            "Vinculación académica de referencia",
        )
        + "</section>"
    )
    secciones += '<section id="fundamentos"><h2>Fundamentos y límites</h2>'
    for titulo, texto in ficha["teoria"]:
        secciones += "<h3>" + escape(titulo) + "</h3>" + _p(texto)
    secciones += '</section><section id="datos"><h2>Datos reproducibles</h2>'
    secciones += _p(
        "Tablas sintéticas fijas de aula, distintas de las entradas del simulador interactivo. Copiar el CSV incluido y conservar UTF-8, separador coma y punto decimal. Registrar hash SHA-256 y versión antes de editar una copia. No se requieren macros ni conexión externa."
    )
    for dataset_clave in ficha["datasets"]:
        dataset = DATASETS[dataset_clave]
        secciones += (
            "<h3>" + escape(dataset["titulo"]) + "</h3>" + _p(dataset["descripcion"])
        )
        secciones += _tabla(dataset["campos"], dataset["filas"], dataset["titulo"])
        secciones += _tabla(
            ("Campo", "Unidad", "Significado"),
            [
                (x["campo"], x["unidad"], x["descripcion"])
                for x in dataset["diccionario"]
            ],
            "Diccionario de datos",
        )
        secciones += (
            "<details><summary>CSV completo y huella de "
            + escape(dataset_clave)
            + "</summary><pre>"
            + escape(dataset_csv(dataset_clave))
            + "</pre>"
        )
        secciones += (
            '<p class="hash">SHA-256: '
            + checksum_dataset(dataset_clave)
            + "</p></details>"
        )
    secciones += '</section><section id="procedimiento"><h2>Procedimiento experimental</h2><ol class="pasos">'
    for titulo, texto in ficha["procedimiento"]:
        secciones += "<li><h3>" + escape(titulo) + "</h3>" + _p(texto) + "</li>"
    secciones += (
        "</ol><h3>Decisiones y restricciones</h3>"
        + _lista(ficha["decisiones"])
        + "</section>"
    )
    secciones += '<section id="analisis"><h2>Indicadores y verificación</h2>' + _tabla(
        ("Indicador", "Regla y unidad"), ficha["metricas"], "Definiciones del caso"
    )
    controles = controles_calculados(ficha["numero"])
    secciones += "<details><summary>Comprobar cálculos del caso de aula</summary>" + _p(
        "Comparar después de resolver. Estos valores son controles calculados, no ejecuciones institucionales ni resultados de partidas guardadas."
    )
    secciones += (
        "<pre>"
        + escape(json.dumps(controles, ensure_ascii=False, indent=2))
        + "</pre></details></section>"
    )
    secciones += '<section id="entrega"><h2>Entregables y evaluación</h2>' + _lista(
        ficha["entregables"]
    )
    secciones += _p(
        "Paquete: original CSV, copia de análisis con fórmulas, gráficos con tabla fuente, decisiones, exportación virtual cuando corresponda y conclusión. Nombrar archivos con práctica, versión y equipo simbólico; no publicar nombres, cédulas ni credenciales."
    )
    secciones += _tabla(
        ("Criterio", "Máximo", "Evidencia"),
        ficha["rubrica"],
        "Rúbrica docente de referencia: 100 puntos",
    )
    secciones += _tabla(
        ("Nivel", "Fracción de puntos", "Descriptor"),
        ficha["niveles"],
        "Aplicar cada nivel a cada criterio",
    )
    secciones += (
        _p(
            "Puntos del criterio = máximo × fracción. Total = suma de los cinco criterios. El docente comunica su aplicación antes de la actividad; no es calificación oficial automática. Una condición insegura exige detener y comunicar, no descontar puntos y continuar."
        )
        + "</section>"
    )
    secciones += (
        '<section id="transferencia"><h2>Reflexión y siguiente experimento</h2>'
        + _lista(ficha["preguntas"])
    )
    enlace = "/laboratorio/" + SLUG + "/logistica/" + ficha["simulador"]
    secciones += (
        '<p><a class="accion" href="'
        + escape(enlace, quote=True)
        + '">Abrir el recurso virtual relacionado</a></p>'
    )
    secciones += _p(
        "El enlace depende de que la unidad y su sección docente estén activas. Guardar sesiones requiere autenticación y los permisos del recurso. Si no hay red, completar el análisis tabular; conservar la exportación pendiente como tal."
    )
    secciones += (
        _p(
            "Transferencia presencial: el docente adapta el protocolo mediante la guía institucional, el técnico comprueba recursos y seguridad y se solicita reserva por separado. Registrar tiempos, asistencia, consumos y evidencias reales sólo en el expediente institucional autorizado."
        )
        + "</section>"
    )
    secciones += '<section id="fuentes"><h2>Fuentes primarias y vigencia</h2><ul>'
    for fuente_clave in ficha["fuentes"]:
        fuente = FUENTES[fuente_clave]
        secciones += (
            '<li><a href="'
            + escape(fuente["url"], quote=True)
            + '" rel="noopener noreferrer">'
            + escape(fuente["entidad"] + " · " + fuente["titulo"])
            + "</a>"
            + _p(fuente["uso"] + " Consultada: " + fuente["consulta"] + ".")
            + "</li>"
        )
    secciones += (
        "</ul>"
        + _p(
            "Material original de docencia. Enlaces externos conservan sus condiciones de acceso y uso; no se redistribuyen sus simuladores ni documentos protegidos. Revisar vigencia de requisitos oficiales antes de una actividad profesional."
        )
        + "</section>"
    )
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;; base-uri &apos;none&apos;; form-action &apos;none&apos;">'
        "<title>" + escape(ficha["titulo"]) + " · UPEC</title><style>"
        "*{box-sizing:border-box}body{margin:0;color:#16392b;background:#f3f7f4;font:16px/1.65 system-ui,sans-serif}"
        "main{max-width:1160px;margin:24px auto;background:#fff;border:1px solid #d6e4dc;border-radius:18px;overflow:hidden}"
        "header{padding:clamp(20px,4vw,48px);background:linear-gradient(120deg,#003d24,#006633);color:white;border-bottom:6px solid #ffce00}"
        "h1{font-size:clamp(27px,4vw,43px);line-height:1.2;max-width:950px}h2{color:#006633;font-size:25px}h3{font-size:19px;line-height:1.35}"
        "header .meta{color:#e0f4e6}.meta{font-size:14px}nav{display:flex;flex-wrap:wrap;gap:8px;padding:18px 24px;border-bottom:1px solid #d6e4dc}"
        "a{color:#006633;overflow-wrap:anywhere}nav a,.accion{padding:7px 12px;border:1px solid #bad1c2;border-radius:9px;text-decoration:none}"
        "nav a:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #c99700;outline-offset:3px}section{padding:16px clamp(18px,4vw,48px) 24px;scroll-margin-top:15px}"
        ".aviso{padding:14px 18px;border-left:4px solid #ffce00;background:#f6faf8;color:#173d2c;margin-top:24px}.tabla{overflow-x:auto;margin:18px 0;border:1px solid #d7e4dd;border-radius:8px}"
        "table{border-collapse:collapse;width:100%;min-width:540px}caption{text-align:left;padding:12px;font-weight:700;background:#edf5ef}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #e0e9e3;vertical-align:top}"
        "th{background:#f5f9f6;font-size:14px}tbody tr:nth-child(even){background:#fafcfa}li{margin:9px 0}.pasos{counter-reset:paso;list-style:none;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}"
        ".pasos>li{border:1px solid #cdddce;border-top:4px solid #006633;border-radius:10px;padding:15px;margin:0}.pasos>li h3:before{counter-increment:paso;content:counter(paso) ' · ';color:#006633}"
        "details{background:#f4f8f5;border:1px solid #d7e5dc;border-radius:9px;padding:12px 16px;margin:15px 0}summary{font-weight:700;cursor:pointer}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace;background:white;padding:15px;border:1px solid #dbe6df}.hash{overflow-wrap:anywhere;font-size:13px}"
        "@media(max-width:700px){main{margin:0;border-radius:0}.pasos{grid-template-columns:1fr}nav{padding:14px}section{padding:12px 18px 22px}}"
        "@media print{body{background:white;color:black}main{margin:0;border:0;max-width:none}header{background:white;color:black;border-color:#006633}header .meta{color:black}nav,.accion{display:none}section{break-inside:auto}.pasos{display:block}.pasos>li{break-inside:avoid;margin:10px 0}details{display:block}.tabla{overflow:visible}table{min-width:0;font-size:12px}pre{font-size:11px}}"
        '</style></head><body><main><header><p class="meta">UPEC · Smart Logistics Lab · Prácticas por área</p><h1>'
        + escape(ficha["titulo"])
        + "</h1>"
        + _p(ficha["contexto"])
        + '<p class="meta">'
        + escape(AREAS[ficha["area"]]["nombre"])
        + " · LOG-PR/"
        + escape(clave)
        + " · Versión "
        + VERSION
        + " · Duración orientativa "
        + str(ficha["duracion_minutos"])
        + " min</p>"
        + '<p class="aviso">'
        + escape(ADVERTENCIA)
        + '</p></header><nav aria-label="Secciones de la guía">'
        + "".join(
            '<a href="#' + ancla + '">' + texto + "</a>"
            for ancla, texto in (
                ("objetivos", "Objetivos"),
                ("preparacion", "Preparación"),
                ("fundamentos", "Fundamentos"),
                ("datos", "Datos"),
                ("procedimiento", "Procedimiento"),
                ("analisis", "Análisis"),
                ("entrega", "Entregables y rúbrica"),
                ("transferencia", "Transferencia"),
                ("fuentes", "Fuentes"),
            )
        )
        + "</nav>"
        + secciones
        + "</main></body></html>"
    )
