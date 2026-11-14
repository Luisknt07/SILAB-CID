"""Centro de distribución docente: flujo por SKU, pedidos y reloj discreto.

Motor puro y acotado; no modifica inventarios, reservas o notas institucionales.
Las tres variantes comparten catálogo y lotes para la misma semilla. La política
publicada es realizable y reproducible, sin afirmar que sea óptima.
"""

from copy import deepcopy
from math import ceil, isfinite
from random import Random

VERSION = "1.0.0"
VERSION_CASO = "1.0.0"
DATASET_VERSION = "1.0.0"
MAX_DECISIONES = 240
FAMILIA = "centro-distribucion"
AREA_CODIGO = "LOG-ALMACEN"
AREA = "Almacenamiento e intralogística inteligente"
_SUFIJO_ERROR = " No se mueve inventario; el intento consume dos minutos."

PRODUCTOS = [
    {
        "sku": "SKU-A",
        "nombre": "Sensor didáctico",
        "clase": "A",
        "unidad": "caja",
        "peso_kg": 2,
        "dimensiones_cm": [30, 20, 15],
    },
    {
        "sku": "SKU-B",
        "nombre": "Controlador didáctico",
        "clase": "B",
        "unidad": "caja",
        "peso_kg": 3,
        "dimensiones_cm": [30, 20, 15],
    },
    {
        "sku": "SKU-C",
        "nombre": "Módulo didáctico",
        "clase": "C",
        "unidad": "caja",
        "peso_kg": 1,
        "dimensiones_cm": [30, 20, 15],
    },
]
UBICACIONES = [
    {
        "id": "ubicacion-a",
        "codigo": "A-01",
        "zona": "alta rotación",
        "clase": "A",
        "capacidad": 12,
        "posicion": [-4, 0, 0],
    },
    {
        "id": "ubicacion-b",
        "codigo": "B-01",
        "zona": "rotación media",
        "clase": "B",
        "capacidad": 10,
        "posicion": [0, 0, 0],
    },
    {
        "id": "ubicacion-c",
        "codigo": "C-01",
        "zona": "reserva",
        "clase": "C",
        "capacidad": 8,
        "posicion": [4, 0, 0],
    },
]
ACCIONES = [
    ("inspeccionar", "Inspeccionar cantidad y calidad"),
    ("rechazar", "Registrar rechazo parcial"),
    ("recibir", "Recibir unidades conformes"),
    ("ubicar-a", "Ubicar en A-01"),
    ("ubicar-b", "Ubicar en B-01"),
    ("ubicar-c", "Ubicar en C-01"),
    ("preparar-a", "Preparar una unidad de SKU-A"),
    ("preparar-b", "Preparar una unidad de SKU-B"),
    ("preparar-c", "Preparar una unidad de SKU-C"),
    ("embalar", "Verificar y embalar pedido completo"),
    ("despachar", "Registrar salida del pedido"),
    ("reparar", "Restaurar montacargas · 14 min"),
    ("esperar", "Avanzar el reloj · 5 min"),
    ("cerrar", "Cerrar con resultados parciales"),
]
SUPUESTOS = [
    "Datos sintéticos; cada unidad es una caja normalizada de 30 × 20 × 15 cm.",
    "Capacidad en cajas; pesos informativos. No se calculan resistencia de estanterías ni seguridad física.",
    "Las coordenadas representan metros de un plano didáctico; distancia Manhattan y recorridos de ida y regreso.",
    "Cada acción consume tiempo simulado; no hay temporizador real ni recursos operando en paralelo.",
    "Una única carga tiene una o dos cajas defectuosas; la cantidad se revela al inspeccionarla.",
    "FIFO por SKU y antigüedad del lote; se registra toda la recepción antes de preparar pedidos.",
    "La clase ABC es una preferencia de ubicación; los tres SKU caben en cualquier ubicación con capacidad.",
    "No se emiten notas académicas, certificados, servicios prestados ni consumos de inventario real.",
]
_REGLAS = [
    "Inspecciona los seis lotes; registra el rechazo parcial antes de recibir las cajas conformes.",
    "Ubica cada lote sin superar A-01: 12, B-01: 10 y C-01: 8 cajas; la ubicación ABC concordante reduce un minuto de picking por caja.",
    "La recepción completa es previa al picking. Prepara una caja por decisión; el motor toma el lote disponible más antiguo de ese SKU.",
    "Embala únicamente pedidos completos y despáchalos para medir OTIF. El orden de prioridad es una decisión del participante.",
    "OTIF = pedidos despachados completos antes o en su minuto prometido / todos los pedidos comprometidos del escenario.",
    "Esperar avanza cinco minutos. Cerrar finaliza con faltantes explícitos; a las 240 decisiones se cierra automáticamente.",
]
CASOS = {}
for _codigo, _titulo, _descripcion in [
    (
        "cd-normal",
        "Centro de distribución · Operación normal",
        "Tres pedidos, tres SKU y seis lotes: trazabilidad desde recepción hasta despacho.",
    ),
    (
        "cd-pico",
        "Centro de distribución · Pico de demanda",
        "Mismos lotes; un cuarto pedido y promesas más exigentes permiten comparar capacidad y prioridades.",
    ),
    (
        "cd-falla",
        "Centro de distribución · Falla de recurso",
        "Mismos tres pedidos de la operación normal; el montacargas falla al minuto 30 durante 30 minutos.",
    ),
]:
    CASOS[_codigo] = {
        "codigo": _codigo,
        "titulo": _titulo,
        "area": AREA,
        "area_codigo": AREA_CODIGO,
        "escena": "almacen",
        "descripcion": _descripcion,
        "resumen": _descripcion,
        "objetivo": "Despachar todos los pedidos completos y puntuales, conservar el balance por SKU y justificar ubicación, secuencia y contingencias.",
        "reglas": _REGLAS
        + (
            [
                "Al minuto 30 falla el montacargas. La acción iniciada termina; siguientes ubicaciones requieren esperar la recuperación al minuto 60 o reparar durante 14 minutos."
            ]
            if _codigo == "cd-falla"
            else []
        ),
        "acciones": [{"id": a, "titulo": t} for a, t in ACCIONES],
        "fuentes": [
            {
                "titulo": "GS1 · EPCIS, eventos de trazabilidad",
                "url": "https://www.gs1.org/standards/epcis",
            },
            {
                "titulo": "OSHA · Seguridad en almacenes",
                "url": "https://www.osha.gov/warehousing/hazards-solutions",
            },
        ],
        "version": VERSION_CASO,
        "version_dataset": DATASET_VERSION,
        "familia": FAMILIA,
        "datos": "Datos sintéticos reproducibles; modelo docente de operaciones, sin validación física industrial.",
        "supuestos": SUPUESTOS,
    }


def catalogo():
    return [{"id": codigo, **deepcopy(caso)} for codigo, caso in CASOS.items()]


def _entero(valor, minimo=0, maximo=2147483647):
    return type(valor) is int and minimo <= valor <= maximo


def _configuracion(caso, semilla):
    if type(caso) is not str or caso not in CASOS or not _entero(semilla):
        raise ValueError("Caso o semilla inválidos.")
    rng = Random(semilla)
    danado, defectuosas = rng.randrange(6), 1 + rng.randrange(2)
    lotes = []
    for indice, (letra, cantidad) in enumerate(
        [(a, n) for a, n in [("a", 6), ("b", 5), ("c", 4)] for _ in range(2)]
    ):
        numero = indice % 2 + 1
        lotes.append(
            {
                "id": f"lote-{letra}-{numero}",
                "sku": f"SKU-{letra.upper()}",
                "lote": numero,
                "cantidad": cantidad,
                "defectuosas": defectuosas if indice == danado else 0,
                "inspeccionado": False,
                "recibidas": 0,
                "rechazadas": 0,
                "saldo": 0,
                "ubicacion": None,
                "estado": "pendiente",
            }
        )
    cantidades = [(3, 2, 1), (3, 2, 1), (2, 2, 2)]
    if caso == "cd-pico":
        cantidades.append((2, 2, 2))
    pedidos = []
    for indice, cantidades_pedido in enumerate(cantidades):
        pedidos.append(
            {
                "id": f"pedido-{indice + 1}",
                "prioridad": ["alta", "media", "baja", "alta"][indice],
                "prometido_min": (
                    [120, 140, 160, 180] if caso == "cd-pico" else [120, 160, 200]
                )[indice],
                "lineas": [
                    {"sku": p["sku"], "cantidad": n, "preparadas": 0, "lotes": []}
                    for p, n in zip(PRODUCTOS, cantidades_pedido)
                ],
                "estado": "pendiente",
                "embalado": False,
                "despachado_en": None,
                "otif": False,
            }
        )
    return {
        "productos": deepcopy(PRODUCTOS),
        "lotes": lotes,
        "ubicaciones": [{**deepcopy(u), "ocupadas": 0} for u in UBICACIONES],
        "pedidos": pedidos,
        "recursos": [
            {
                "id": "montacargas",
                "nombre": "Montacargas didáctico",
                "estado": "operativo",
                "fallo_en": 30 if caso == "cd-falla" else None,
                "recuperacion_en": 60 if caso == "cd-falla" else None,
                "fallo_activado": False,
                "reparado": False,
            },
            {
                "id": "empaque",
                "nombre": "Puesto de embalaje",
                "estado": "operativo",
                "fallo_en": None,
                "recuperacion_en": None,
                "fallo_activado": False,
                "reparado": False,
            },
        ],
        "eventos": [],
        "distancia_m": 0,
    }


def _obj(identificador, nombre, tipo, zona, posicion, descripcion, estado="listo"):
    return {
        "id": identificador,
        "nombre": nombre,
        "tipo": tipo,
        "zona": zona,
        "posicion": posicion,
        "descripcion": descripcion,
        "estado": estado,
        "acciones": [],
    }


def _objetos(estado):
    d = estado["datos"]
    objetos = [
        _obj(clave, titulo, clave, clave, [-10 + i * 4, 0, -6], descripcion)
        for i, (clave, titulo, descripcion) in enumerate(
            [
                (
                    "recepcion",
                    "Recepción",
                    "Identifica los seis lotes y sus cantidades antes de liberar la recepción.",
                ),
                (
                    "calidad",
                    "Control de calidad",
                    "Inspección y rechazo parcial; las cajas defectuosas no entran a stock.",
                ),
                (
                    "racks",
                    "Gestión de ubicaciones",
                    "Tres ubicaciones ABC; capacidad por caja normalizada y stock por SKU.",
                ),
                (
                    "picking",
                    "Picking FIFO",
                    "Selecciona un pedido; cada decisión retira una caja del lote más antiguo de su SKU.",
                ),
                (
                    "empaque",
                    "Embalaje",
                    "Verifica que todas las líneas estén completas antes de proteger e identificar el pedido.",
                ),
                (
                    "despacho",
                    "Despacho",
                    "Registra la salida completa y contrasta su minuto prometido.",
                ),
            ]
        )
    ]
    recurso = d["recursos"][0]
    objetos.append(
        _obj(
            "montacargas",
            "Montacargas",
            "camion",
            "recepcion",
            [-7, 0, 0],
            "Traslado de lotes. Falla programada en esta variante: minuto 30; recuperación natural al 60 o reparación de 14 minutos."
            if estado["caso"] == "cd-falla"
            else "Traslado de lotes sin falla en esta variante.",
            recurso["estado"],
        )
    )
    objetos.append(
        _obj(
            "control",
            "Reloj y cierre",
            "sensor",
            "control",
            [10, 0, 1],
            "El reloj solo avanza con decisiones; puedes esperar cinco minutos o cerrar dejando pendientes explícitos.",
        )
    )
    for u in d["ubicaciones"]:
        objetos.append(
            _obj(
                u["id"],
                f"{u['codigo']} · clase {u['clase']}",
                "racks",
                u["codigo"],
                deepcopy(u["posicion"]),
                f"{u['ocupadas']} de {u['capacidad']} cajas ocupadas. Acepta cualquier SKU; clase ABC concordante favorece picking.",
                "capacidad disponible"
                if u["ocupadas"] < u["capacidad"]
                else "completa",
            )
        )
    for i, lote in enumerate(d["lotes"]):
        posicion = [-10 + (i % 3) * 1.8, 0, 3 + (i // 3) * 1.8]
        if lote["ubicacion"]:
            u = next(u for u in d["ubicaciones"] if u["id"] == lote["ubicacion"])
            colocados = sorted(
                fila["id"]
                for fila in d["lotes"]
                if fila["ubicacion"] == lote["ubicacion"]
            )
            indice = colocados.index(lote["id"])
            posicion = [
                u["posicion"][0] + (-0.7 if indice % 2 == 0 else 0.7),
                0,
                u["posicion"][2] + 2.8 + (indice // 2) * 1.8,
            ]
        descripcion = (
            f"{lote['sku']} · lote {lote['lote']} · {lote['cantidad']} cajas. "
        )
        descripcion += (
            f"Conformes recibidas: {lote['recibidas']}; rechazadas: {lote['rechazadas']}; saldo: {lote['saldo']}."
            if lote["inspeccionado"]
            else "Calidad y cantidad por inspeccionar."
        )
        objetos.append(
            _obj(
                lote["id"],
                f"{lote['sku']} · lote {lote['lote']}",
                "pallet",
                lote["ubicacion"] or "recepcion",
                posicion,
                descripcion,
                lote["estado"],
            )
        )
    for i, pedido in enumerate(d["pedidos"]):
        objetos.append(
            _obj(
                pedido["id"],
                f"Pedido {i + 1} · prioridad {pedido['prioridad']}",
                "pedido",
                "picking",
                [6 + (i % 2) * 3, 0, 4 + (i // 2) * 2.5],
                f"Promesa: minuto {pedido['prometido_min']}. "
                + "; ".join(
                    f"{fila['sku']}: {fila['preparadas']}/{fila['cantidad']}"
                    for fila in pedido["lineas"]
                ),
                pedido["estado"],
            )
        )
    acciones = _acciones(estado)
    for objeto in objetos:
        objeto["acciones"] = acciones.get(objeto["id"], [])
    return objetos


def _acciones(estado):
    if estado["terminada"]:
        return {}
    d, acciones = estado["datos"], {"control": ["esperar", "cerrar"]}
    for lote in d["lotes"]:
        if not lote["inspeccionado"]:
            acciones[lote["id"]] = ["inspeccionar"]
        elif not lote["recibidas"]:
            acciones[lote["id"]] = (
                ["rechazar"] if lote["defectuosas"] > lote["rechazadas"] else []
            ) + ["recibir"]
        elif lote["saldo"] and not lote["ubicacion"]:
            acciones[lote["id"]] = ["ubicar-a", "ubicar-b", "ubicar-c"]
    for pedido in d["pedidos"]:
        if pedido["despachado_en"] is not None:
            continue
        if pedido["embalado"]:
            acciones[pedido["id"]] = ["despachar"]
        else:
            acciones[pedido["id"]] = [
                f"preparar-{fila['sku'][-1].lower()}"
                for fila in pedido["lineas"]
                if fila["preparadas"] < fila["cantidad"]
            ] + ["embalar"]
    if d["recursos"][0]["estado"] == "averiado":
        acciones["montacargas"] = ["reparar"]
    return acciones


def _balances(datos):
    balances = []
    for producto in PRODUCTOS:
        sku = producto["sku"]
        lotes = [fila for fila in datos["lotes"] if fila["sku"] == sku]
        filas = [
            (p, fila)
            for p in datos["pedidos"]
            for fila in p["lineas"]
            if fila["sku"] == sku
        ]
        rechazo_pendiente = sum(
            fila["defectuosas"] - fila["rechazadas"]
            for fila in lotes
            if fila["inspeccionado"]
        )
        fila = {
            "sku": sku,
            "entrada": sum(fila["cantidad"] for fila in lotes),
            "pendiente": sum(
                fila["cantidad"] - fila["recibidas"] - fila["rechazadas"]
                for fila in lotes
            )
            - rechazo_pendiente,
            "inspeccion_rechazo": rechazo_pendiente,
            "disponible": sum(fila["saldo"] for fila in lotes),
            "preparado": sum(
                fila["preparadas"] for p, fila in filas if p["despachado_en"] is None
            ),
            "despachado": sum(
                fila["preparadas"]
                for p, fila in filas
                if p["despachado_en"] is not None
            ),
            "rechazado": sum(fila["rechazadas"] for fila in lotes),
        }
        fila["diferencia"] = fila["entrada"] - sum(
            fila[k]
            for k in (
                "pendiente",
                "inspeccion_rechazo",
                "disponible",
                "preparado",
                "despachado",
                "rechazado",
            )
        )
        balances.append(fila)
    return balances


def _etapas(datos):
    lotes, pedidos = datos["lotes"], datos["pedidos"]
    requisitos = [
        (
            "recepcion",
            "Recepción",
            sum(
                fila["recibidas"] + fila["rechazadas"] == fila["cantidad"]
                for fila in lotes
            ),
            len(lotes),
        ),
        (
            "control",
            "Control de calidad",
            sum(
                fila["inspeccionado"] and fila["rechazadas"] == fila["defectuosas"]
                for fila in lotes
            ),
            len(lotes),
        ),
        (
            "ubicacion",
            "Ubicación",
            sum(bool(fila["ubicacion"]) for fila in lotes),
            len(lotes),
        ),
        (
            "picking",
            "Picking",
            sum(
                all(fila["preparadas"] == fila["cantidad"] for fila in p["lineas"])
                for p in pedidos
            ),
            len(pedidos),
        ),
        ("embalaje", "Embalaje", sum(p["embalado"] for p in pedidos), len(pedidos)),
        (
            "despacho",
            "Despacho",
            sum(p["despachado_en"] is not None for p in pedidos),
            len(pedidos),
        ),
    ]
    return [
        {
            "id": clave,
            "titulo": titulo,
            "estado": "completa"
            if hechas == total
            else "en curso"
            if hechas
            else "pendiente",
            "completados": hechas,
            "total": total,
        }
        for clave, titulo, hechas, total in requisitos
    ]


def _actualizar(estado):
    d = estado["datos"]
    for u in d["ubicaciones"]:
        u["ocupadas"] = sum(
            fila["saldo"] for fila in d["lotes"] if fila["ubicacion"] == u["id"]
        )
    for lote in d["lotes"]:
        lote["estado"] = (
            "agotado"
            if lote["recibidas"] and not lote["saldo"]
            else "ubicado"
            if lote["ubicacion"]
            else "recibido"
            if lote["recibidas"]
            else "inspeccionado"
            if lote["inspeccionado"]
            else "pendiente"
        )
    for p in d["pedidos"]:
        p["estado"] = (
            "despachado"
            if p["despachado_en"] is not None
            else "embalado"
            if p["embalado"]
            else "preparado"
            if all(fila["preparadas"] == fila["cantidad"] for fila in p["lineas"])
            else "en preparación"
            if any(fila["preparadas"] for fila in p["lineas"])
            else "pendiente"
        )
    d["balances"] = _balances(d)
    d["etapas"] = _etapas(d)
    total = len(d["pedidos"])
    completados = sum(p["despachado_en"] is not None for p in d["pedidos"])
    otif = sum(p["otif"] for p in d["pedidos"])
    diferencia = sum(abs(b["diferencia"]) for b in d["balances"])
    ocupadas, capacidad = (
        sum(u["ocupadas"] for u in d["ubicaciones"]),
        sum(u["capacidad"] for u in d["ubicaciones"]),
    )
    resumen = {
        "total_pedidos": total,
        "completados": completados,
        "pedidos_otif": otif,
        "unidades_solicitadas": sum(
            fila["cantidad"] for p in d["pedidos"] for fila in p["lineas"]
        ),
        "unidades_preparadas": sum(
            fila["preparadas"] for p in d["pedidos"] for fila in p["lineas"]
        ),
        "unidades_despachadas": sum(b["despachado"] for b in d["balances"]),
        "unidades_disponibles": sum(b["disponible"] for b in d["balances"]),
        "unidades_rechazadas": sum(b["rechazado"] for b in d["balances"]),
        "distancia_m": d["distancia_m"],
        "exactitud_pct": round(100 * max(0, 1 - diferencia / 30), 2),
        "diferencia_balance": diferencia,
        "capacidad_total": capacidad,
        "ocupacion_pct": round(100 * ocupadas / capacidad, 2),
    }
    d["resumen"] = resumen
    if completados == total and all(
        fila["recibidas"] + fila["rechazadas"] == fila["cantidad"]
        and bool(fila["ubicacion"])
        for fila in d["lotes"]
    ):
        estado["terminada"] = True
        estado["motivo_cierre"] = "objetivos completados"
    if estado["paso"] == MAX_DECISIONES and not estado["terminada"]:
        estado["terminada"] = True
        estado["motivo_cierre"] = "límite de decisiones"
    estado["objetos"] = _objetos(estado)
    estado["kpis"] = [
        {
            "id": "otif",
            "titulo": "Pedidos OTIF",
            "valor": round(100 * otif / total, 2),
            "unidad": "%",
        },
        {
            "id": "minutos",
            "titulo": "Tiempo simulado",
            "valor": estado["minutos"],
            "unidad": "min",
        },
        {
            "id": "errores",
            "titulo": "Intentos operativos inválidos",
            "valor": estado["errores"],
            "unidad": "intentos",
        },
        {
            "id": "distancia_m",
            "titulo": "Recorrido de manipulación",
            "valor": d["distancia_m"],
            "unidad": "m",
        },
        {
            "id": "completados",
            "titulo": "Pedidos completos despachados",
            "valor": completados,
            "unidad": "pedidos",
        },
        {
            "id": "diferencia_balance",
            "titulo": "Diferencia de balance",
            "valor": diferencia,
            "unidad": "cajas",
        },
        {
            "id": "unidades",
            "titulo": "Cajas despachadas",
            "valor": resumen["unidades_despachadas"],
            "unidad": "cajas",
        },
        {
            "id": "exactitud",
            "titulo": "Conservación del registro",
            "valor": resumen["exactitud_pct"],
            "unidad": "%",
        },
        {
            "id": "ocupacion",
            "titulo": "Ocupación de ubicaciones",
            "valor": resumen["ocupacion_pct"],
            "unidad": "%",
        },
    ]
    return estado


def _serie(estado):
    for kpi in estado["kpis"]:
        serie = next((s for s in estado["series"] if s["id"] == kpi["id"]), None)
        if serie is None:
            serie = {
                "id": kpi["id"],
                "titulo": kpi["titulo"],
                "unidad": kpi["unidad"],
                "puntos": [],
            }
            estado["series"].append(serie)
        serie["puntos"].append({"paso": estado["paso"], "valor": kpi["valor"]})


def crear_estado(caso="cd-normal", semilla=42):
    datos = _configuracion(caso, semilla)
    estado = {
        "version_motor": VERSION,
        "version_caso": VERSION_CASO,
        "version_dataset": DATASET_VERSION,
        "familia": FAMILIA,
        "caso": caso,
        "semilla": semilla,
        "paso": 0,
        "minutos": 0,
        "errores": 0,
        "terminada": False,
        "motivo_cierre": "",
        "puntaje": None,
        "mensaje": CASOS[caso]["objetivo"],
        "datos": datos,
        "objetos": [],
        "kpis": [],
        "historial": [],
        "series": [],
    }
    _actualizar(estado)
    _serie(estado)
    return estado


def _evento(estado, tipo, objeto, descripcion, minuto=None):
    eventos = estado["datos"]["eventos"]
    eventos.append(
        {
            "id": f"evento-{len(eventos) + 1}",
            "tipo": tipo,
            "minuto": estado["minutos"] if minuto is None else minuto,
            "objeto": objeto,
            "descripcion": descripcion,
        }
    )


def _tiempo(estado, duracion):
    estado["minutos"] += duracion
    recurso = estado["datos"]["recursos"][0]
    if (
        recurso["fallo_en"] is not None
        and not recurso["fallo_activado"]
        and estado["minutos"] >= recurso["fallo_en"]
    ):
        recurso.update(fallo_activado=True, estado="averiado")
        _evento(
            estado,
            "falla",
            recurso["id"],
            "Falla del montacargas; la acción en curso termina y se bloquean los siguientes traslados.",
            recurso["fallo_en"],
        )
    if (
        recurso["estado"] == "averiado"
        and estado["minutos"] >= recurso["recuperacion_en"]
    ):
        recurso["estado"] = "operativo"
        _evento(
            estado,
            "recuperacion",
            recurso["id"],
            "Montacargas disponible tras recuperación natural.",
            recurso["recuperacion_en"],
        )


def _error(estado, mensaje):
    estado["errores"] += 1
    _tiempo(estado, 2)
    return mensaje + _SUFIJO_ERROR


def _recibido_todo(datos):
    return all(
        fila["recibidas"] + fila["rechazadas"] == fila["cantidad"]
        for fila in datos["lotes"]
    )


def _distancia(origen, destino):
    return abs(origen[0] - destino[0]) + abs(origen[2] - destino[2])


def _lote(estado, accion, lote):
    d = estado["datos"]
    if accion == "inspeccionar":
        lote["inspeccionado"] = True
        _tiempo(estado, 2)
        _evento(
            estado,
            "inspeccion",
            lote["id"],
            f"Cantidad cotejada: {lote['cantidad']}; defectuosas: {lote['defectuosas']}.",
        )
        return f"{lote['id']}: {lote['cantidad'] - lote['defectuosas']} cajas conformes y {lote['defectuosas']} defectuosas."
    if accion == "rechazar":
        lote["rechazadas"] = lote["defectuosas"]
        _tiempo(estado, 1)
        _evento(
            estado,
            "rechazo",
            lote["id"],
            f"{lote['rechazadas']} cajas segregadas; no entran al inventario utilizable.",
        )
        return "Rechazo parcial registrado con trazabilidad de lote."
    if accion == "recibir":
        if lote["defectuosas"] != lote["rechazadas"]:
            return _error(
                estado, "Registra primero el rechazo de las cajas defectuosas."
            )
        lote["recibidas"] = lote["cantidad"] - lote["defectuosas"]
        lote["saldo"] = lote["recibidas"]
        _tiempo(estado, 2)
        _evento(
            estado,
            "recepcion",
            lote["id"],
            f"Entrada de {lote['recibidas']} cajas conformes de {lote['sku']}.",
        )
        return "Recepción de unidades conformes registrada."
    if d["recursos"][0]["estado"] != "operativo":
        return _error(estado, "Montacargas averiado: repara o espera antes de ubicar.")
    ubicacion = next(
        u for u in d["ubicaciones"] if u["id"] == "ubicacion-" + accion[-1]
    )
    if ubicacion["ocupadas"] + lote["saldo"] > ubicacion["capacidad"]:
        return _error(
            estado, f"{ubicacion['codigo']} no tiene capacidad para el lote completo."
        )
    distancia = _distancia([-10, 0, -6], ubicacion["posicion"])
    lote["ubicacion"] = ubicacion["id"]
    d["distancia_m"] += 2 * distancia
    _tiempo(estado, 2 + ceil(distancia / 6))
    _evento(
        estado,
        "ubicacion",
        lote["id"],
        f"Ubicado en {ubicacion['codigo']}; recorrido ida y regreso {2 * distancia} m.",
    )
    return f"Lote ubicado en {ubicacion['codigo']}; capacidad y saldo actualizados."


def _pedido(estado, accion, pedido):
    d = estado["datos"]
    if accion.startswith("preparar-"):
        if not _recibido_todo(d):
            return _error(
                estado,
                "Completa la recepción y los rechazos antes de preparar pedidos.",
            )
        sku = "SKU-" + accion[-1].upper()
        linea = next(fila for fila in pedido["lineas"] if fila["sku"] == sku)
        lotes = sorted(
            (fila for fila in d["lotes"] if fila["sku"] == sku and fila["saldo"]),
            key=lambda fila: (fila["lote"], fila["id"]),
        )
        if not lotes:
            return _error(estado, f"No hay existencias disponibles de {sku}.")
        lote = lotes[0]
        if not lote["ubicacion"]:
            return _error(estado, "Ubica primero el lote FIFO más antiguo de ese SKU.")
        ubicacion = next(u for u in d["ubicaciones"] if u["id"] == lote["ubicacion"])
        distancia = _distancia([2, 0, -6], ubicacion["posicion"])
        conforme_abc = ubicacion["clase"] == sku[-1]
        lote["saldo"] -= 1
        linea["preparadas"] += 1
        linea["lotes"].append(lote["id"])
        d["distancia_m"] += 2 * distancia
        _tiempo(estado, 1 + ceil(distancia / 6) - int(conforme_abc))
        _evento(
            estado,
            "picking",
            pedido["id"],
            f"Una caja {sku} del {lote['id']} → {pedido['id']}; FIFO y recorrido {2 * distancia} m.",
        )
        return "Caja asignada al pedido; saldo FIFO y trazabilidad actualizados."
    if accion == "embalar":
        if not all(fila["preparadas"] == fila["cantidad"] for fila in pedido["lineas"]):
            return _error(
                estado, "Completa todas las líneas del pedido antes de embalar."
            )
        pedido["embalado"] = True
        _tiempo(
            estado, 4 + ceil(sum(fila["cantidad"] for fila in pedido["lineas"]) / 4)
        )
        _evento(
            estado,
            "embalaje",
            pedido["id"],
            "Verificación de contenido completo, protección e identificación del pedido.",
        )
        return "Pedido completo embalado y listo para salida."
    _tiempo(estado, 3)
    pedido["despachado_en"] = estado["minutos"]
    pedido["otif"] = estado["minutos"] <= pedido["prometido_min"]
    _evento(
        estado,
        "despacho",
        pedido["id"],
        f"Salida completa al minuto {estado['minutos']}; promesa {pedido['prometido_min']}; OTIF {'sí' if pedido['otif'] else 'no'}.",
    )
    return "Pedido despachado completo " + (
        "dentro de su promesa." if pedido["otif"] else "fuera de su promesa."
    )


def _validar_bitacora(estado):
    """Comprueba el contrato y la cronología sin volver a ejecutar la partida."""
    d = estado["datos"]
    lotes = {fila["id"] for fila in d["lotes"]}
    pedidos = {fila["id"]: fila for fila in d["pedidos"]}
    por_objeto = {
        **{
            identificador: {
                "inspeccionar",
                "rechazar",
                "recibir",
                "ubicar-a",
                "ubicar-b",
                "ubicar-c",
            }
            for identificador in lotes
        },
        **{
            identificador: {
                "preparar-a",
                "preparar-b",
                "preparar-c",
                "embalar",
                "despachar",
            }
            for identificador in pedidos
        },
        "montacargas": {"reparar"},
        "control": {"esperar", "cerrar"},
    }
    tipos = {
        "inspeccionar": "inspeccion",
        "rechazar": "rechazo",
        "recibir": "recepcion",
        "embalar": "embalaje",
        "despachar": "despacho",
        "reparar": "reparacion",
        "cerrar": "cierre",
    }
    efectos = {
        "inspeccionar": {2},
        "rechazar": {1},
        "recibir": {2},
        "ubicar-a": {2, 4},
        "ubicar-b": {2, 5},
        "ubicar-c": {2, 6},
        "preparar-a": {2, 3},
        "preparar-b": {2, 3},
        "preparar-c": {2, 3},
        "despachar": {3},
        "reparar": {14},
        "esperar": {5},
        "cerrar": {0},
    }
    fallable = estado["caso"] == "cd-falla"
    activado = reparado = False
    minutos = errores = 0
    esperados = []
    for numero, fila in enumerate(estado["historial"], 1):
        if (
            type(fila) is not dict
            or set(fila) != {"paso", "accion", "objeto", "mensaje", "efecto", "minutos"}
            or type(fila.get("accion")) is not str
            or type(fila.get("objeto")) is not str
            or fila["accion"] not in por_objeto.get(fila["objeto"], set())
            or not _entero(fila.get("paso"), numero, numero)
            or type(fila.get("mensaje")) is not str
            or not 1 <= len(fila["mensaje"]) <= 1000
            or not _entero(fila.get("efecto"), 0, 20)
            or not _entero(fila.get("minutos"), 0, MAX_DECISIONES * 20)
            or fila["minutos"] != minutos + fila["efecto"]
        ):
            raise ValueError("Decisión registrada o cronología incompatible.")
        accion, objeto = fila["accion"], fila["objeto"]
        duraciones = efectos.get(accion)
        if accion == "embalar":
            duraciones = {
                2,
                4
                + ceil(
                    sum(linea["cantidad"] for linea in pedidos[objeto]["lineas"]) / 4
                ),
            }
        if fila["efecto"] not in duraciones:
            raise ValueError("La duración no corresponde a la acción registrada.")
        if accion == "cerrar" and (
            numero != estado["paso"]
            or not estado["terminada"]
            or estado.get("motivo_cierre") != "cierre anticipado"
        ):
            raise ValueError("No puede haber decisiones después del cierre.")
        if fallable and not activado and fila["minutos"] >= 30:
            activado = True
            esperados.append(("falla", "montacargas", 30))
        if accion == "reparar":
            if not activado or reparado or minutos >= 60:
                raise ValueError("Reparación fuera de la ventana de avería.")
            reparado = True
        elif fallable and not reparado and minutos < 60 <= fila["minutos"]:
            esperados.append(("recuperacion", "montacargas", 60))
        invalida = fila["mensaje"].endswith(_SUFIJO_ERROR)
        if invalida:
            if fila["efecto"] != 2 or accion not in {
                "recibir",
                "ubicar-a",
                "ubicar-b",
                "ubicar-c",
                "preparar-a",
                "preparar-b",
                "preparar-c",
                "embalar",
            }:
                raise ValueError("Intento inválido incompatible con su acción.")
            errores += 1
        elif accion != "esperar":
            tipo = (
                "ubicacion"
                if accion.startswith("ubicar-")
                else "picking"
                if accion.startswith("preparar-")
                else tipos[accion]
            )
            esperados.append((tipo, objeto, fila["minutos"]))
        minutos = fila["minutos"]
    if minutos != estado["minutos"] or errores != estado["errores"]:
        raise ValueError("El reloj o los errores no coinciden con las decisiones.")
    if len(d["eventos"]) != len(esperados):
        raise ValueError("Faltan o sobran eventos para las decisiones registradas.")
    for numero, (evento, esperado) in enumerate(zip(d["eventos"], esperados), 1):
        if (
            type(evento) is not dict
            or set(evento) != {"id", "tipo", "minuto", "objeto", "descripcion"}
            or evento.get("id") != f"evento-{numero}"
            or type(evento.get("descripcion")) is not str
            or not 1 <= len(evento["descripcion"]) <= 1000
            or not _entero(evento.get("minuto"), 0, estado["minutos"])
            or (evento.get("tipo"), evento.get("objeto"), evento["minuto"]) != esperado
        ):
            raise ValueError("Evento incompatible con la cronología registrada.")


def _validar_series(estado):
    kpis = estado["kpis"]
    if len(estado["series"]) != len(kpis):
        raise ValueError("Faltan o sobran series de indicadores.")
    for serie, kpi in zip(estado["series"], kpis):
        if (
            type(serie) is not dict
            or set(serie) != {"id", "titulo", "unidad", "puntos"}
            or any(
                serie.get(clave) != kpi[clave] for clave in ("id", "titulo", "unidad")
            )
            or type(serie.get("puntos")) is not list
            or len(serie["puntos"]) != estado["paso"] + 1
        ):
            raise ValueError("Serie inválida o fuera de límite.")
        for numero, punto in enumerate(serie["puntos"]):
            if (
                type(punto) is not dict
                or set(punto) != {"paso", "valor"}
                or not _entero(punto.get("paso"), numero, numero)
                or type(punto.get("valor")) not in (int, float)
                or not isfinite(punto["valor"])
                or punto["valor"] < 0
            ):
                raise ValueError("Punto de serie inválido o fuera de secuencia.")
        inicial = 100 if kpi["id"] == "exactitud" else 0
        if (
            serie["puntos"][0]["valor"] != inicial
            or serie["puntos"][-1]["valor"] != kpi["valor"]
        ):
            raise ValueError(
                "La serie no concuerda con los indicadores de inicio y cierre."
            )


def validar_estado(estado):
    """Valida límites y conservación; nunca confía en saldos agregados del cliente."""
    if (
        type(estado) is not dict
        or estado.get("version_motor") != VERSION
        or estado.get("version_caso") != VERSION_CASO
        or estado.get("version_dataset") != DATASET_VERSION
    ):
        raise ValueError("Estado o versión incompatible.")
    caso, semilla = estado.get("caso"), estado.get("semilla")
    base = _configuracion(caso, semilla)
    if not _entero(estado.get("paso"), 0, MAX_DECISIONES) or not _entero(
        estado.get("errores"), 0, estado["paso"]
    ):
        raise ValueError("Contadores fuera de rango.")
    if (
        type(estado.get("minutos")) is not int
        or not 0 <= estado["minutos"] <= MAX_DECISIONES * 20
        or type(estado.get("terminada")) is not bool
    ):
        raise ValueError("Reloj o cierre inválidos.")
    if (
        type(estado.get("historial")) is not list
        or len(estado["historial"]) != estado["paso"]
        or type(estado.get("series")) is not list
        or len(estado["series"]) > 9
    ):
        raise ValueError("Historial o series fuera de límite.")
    d = estado.get("datos")
    if type(d) is not dict or d.get("productos") != PRODUCTOS:
        raise ValueError("Dataset incompatible.")
    for clave, longitud in [
        ("lotes", 6),
        ("ubicaciones", 3),
        ("pedidos", len(base["pedidos"])),
        ("recursos", 2),
    ]:
        if (
            type(d.get(clave)) is not list
            or len(d[clave]) != longitud
            or any(type(f) is not dict for f in d[clave])
        ):
            raise ValueError("Filas de dataset inválidas.")
    if (
        type(d.get("eventos")) is not list
        or len(d["eventos"]) > MAX_DECISIONES + 3
        or not _entero(d.get("distancia_m"), 0, MAX_DECISIONES * 60)
    ):
        raise ValueError("Trazabilidad fuera de límite.")
    for lote, inicial in zip(d["lotes"], base["lotes"]):
        if (
            any(
                lote.get(k) != inicial[k]
                for k in ("id", "sku", "lote", "cantidad", "defectuosas")
            )
            or type(lote.get("inspeccionado")) is not bool
        ):
            raise ValueError("Lote incompatible.")
        if not all(
            _entero(lote.get(k), 0, lote["cantidad"])
            for k in ("recibidas", "rechazadas", "saldo")
        ):
            raise ValueError("Cantidades de lote inválidas.")
        if (
            lote["recibidas"] not in (0, lote["cantidad"] - lote["defectuosas"])
            or lote["rechazadas"] not in (0, lote["defectuosas"])
            or lote["saldo"] > lote["recibidas"]
            or (not lote["inspeccionado"] and (lote["recibidas"] or lote["rechazadas"]))
        ):
            raise ValueError("Recepción o rechazo inconsistente.")
        if lote.get("ubicacion") not in (
            None,
            "ubicacion-a",
            "ubicacion-b",
            "ubicacion-c",
        ) or (lote.get("ubicacion") and not lote["recibidas"]):
            raise ValueError("Ubicación de lote inválida.")
    for u, inicial in zip(d["ubicaciones"], base["ubicaciones"]):
        if any(
            u.get(k) != inicial[k]
            for k in ("id", "codigo", "clase", "capacidad", "posicion")
        ):
            raise ValueError("Ubicación incompatible.")
        ocupadas = sum(
            fila["saldo"] for fila in d["lotes"] if fila["ubicacion"] == u["id"]
        )
        if (
            not _entero(u.get("ocupadas"), 0, u["capacidad"])
            or u["ocupadas"] != ocupadas
        ):
            raise ValueError("Capacidad o saldo de ubicación inconsistente.")
    for pedido, inicial in zip(d["pedidos"], base["pedidos"]):
        if (
            any(
                pedido.get(k) != inicial[k]
                for k in ("id", "prioridad", "prometido_min")
            )
            or type(pedido.get("lineas")) is not list
            or len(pedido["lineas"]) != 3
            or type(pedido.get("embalado")) is not bool
            or type(pedido.get("otif")) is not bool
        ):
            raise ValueError("Pedido incompatible.")
        for fila, original in zip(pedido["lineas"], inicial["lineas"]):
            if (
                type(fila) is not dict
                or any(fila.get(k) != original[k] for k in ("sku", "cantidad"))
                or not _entero(fila.get("preparadas"), 0, fila["cantidad"])
                or type(fila.get("lotes")) is not list
                or len(fila["lotes"]) != fila["preparadas"]
            ):
                raise ValueError("Línea de pedido incompatible.")
            if any(
                type(i) is not str
                or i not in {x["id"] for x in d["lotes"] if x["sku"] == fila["sku"]}
                for i in fila["lotes"]
            ):
                raise ValueError("Origen de picking incompatible.")
        completo = all(
            fila["preparadas"] == fila["cantidad"] for fila in pedido["lineas"]
        )
        salida = pedido.get("despachado_en")
        if (
            (pedido["embalado"] and not completo)
            or (
                salida is not None
                and (
                    not _entero(salida, 0, estado["minutos"]) or not pedido["embalado"]
                )
            )
            or pedido["otif"]
            != (salida is not None and salida <= pedido["prometido_min"])
        ):
            raise ValueError("Embalaje, salida o puntualidad inconsistente.")
    for lote in d["lotes"]:
        extraidas = sum(
            fila["lotes"].count(lote["id"])
            for p in d["pedidos"]
            for fila in p["lineas"]
        )
        if lote["recibidas"] - lote["saldo"] != extraidas:
            raise ValueError("Saldo y trazabilidad de picking no coinciden.")
    if any(b["diferencia"] != 0 for b in _balances(d)):
        raise ValueError("No se conserva el balance por SKU.")
    _validar_bitacora(estado)
    for recurso, inicial in zip(d["recursos"], base["recursos"]):
        if (
            recurso.get("id") != inicial["id"]
            or recurso.get("fallo_en") != inicial["fallo_en"]
            or type(recurso.get("estado")) is not str
            or recurso.get("estado") not in {"operativo", "averiado"}
            or not all(
                type(recurso.get(k)) is bool for k in ("fallo_activado", "reparado")
            )
        ):
            raise ValueError("Recurso incompatible.")
        if recurso["fallo_activado"] and recurso["fallo_en"] is None:
            raise ValueError("Falla no prevista en el escenario.")
        if (
            recurso["estado"] == "averiado"
            and not _entero(
                recurso.get("recuperacion_en"),
                estado["minutos"] + 1,
                MAX_DECISIONES * 20,
            )
        ) or (
            recurso.get("recuperacion_en") is not None
            and not _entero(recurso["recuperacion_en"], 0, MAX_DECISIONES * 20)
        ):
            raise ValueError("Recuperación fuera de rango.")
    for recurso in d["recursos"]:
        if recurso["fallo_en"] is None:
            if (
                recurso["estado"] != "operativo"
                or recurso["fallo_activado"]
                or recurso["reparado"]
                or recurso["recuperacion_en"] is not None
            ):
                raise ValueError(
                    "Un recurso sin falla no puede cambiar de disponibilidad."
                )
            continue
        reparaciones = [
            h
            for h in estado["historial"]
            if type(h) is dict
            and h.get("accion") == "reparar"
            and h.get("objeto") == recurso["id"]
        ]
        if len(reparaciones) > 1 or recurso["reparado"] != bool(reparaciones):
            raise ValueError("La reparación necesita una única decisión registrada.")
        recuperacion = reparaciones[0]["minutos"] if reparaciones else 60
        activado = estado["minutos"] >= recurso["fallo_en"]
        disponibilidad = (
            "averiado" if activado and estado["minutos"] < recuperacion else "operativo"
        )
        if (
            recurso["recuperacion_en"] != recuperacion
            or recurso["fallo_activado"] != activado
            or recurso["estado"] != disponibilidad
        ):
            raise ValueError(
                "La disponibilidad del recurso no corresponde al reloj y a su reparación."
            )
    if (
        estado.get("familia") != FAMILIA
        or type(estado.get("motivo_cierre")) is not str
        or estado["motivo_cierre"]
        not in {
            "",
            "objetivos completados",
            "límite de decisiones",
            "cierre anticipado",
        }
    ):
        raise ValueError("Familia o causa de cierre incompatible.")
    if estado["terminada"] != bool(estado["motivo_cierre"]):
        raise ValueError("El cierre necesita una causa explícita.")
    if estado["motivo_cierre"] == "cierre anticipado" and (
        not estado["historial"] or estado["historial"][-1].get("accion") != "cerrar"
    ):
        raise ValueError("El cierre anticipado necesita una decisión registrada.")
    if (
        estado["motivo_cierre"] == "límite de decisiones"
        and estado["paso"] != MAX_DECISIONES
    ):
        raise ValueError("El límite de cierre no se ha alcanzado.")
    derivados = _actualizar({**estado, "datos": deepcopy(d)})
    if (
        any(
            d.get(k) != derivados["datos"][k] for k in ("balances", "resumen", "etapas")
        )
        or estado.get("kpis") != derivados["kpis"]
        or estado.get("objetos") != derivados["objetos"]
        or estado["terminada"] != derivados["terminada"]
        or estado["motivo_cierre"] != derivados["motivo_cierre"]
    ):
        raise ValueError(
            "El resumen, objetos o indicadores no coinciden con los datos operativos."
        )
    _validar_series(estado)
    return True


def actuar(estado, decision):
    validar_estado(estado)
    if (
        type(decision) is not dict
        or set(decision) != {"accion", "objeto"}
        or type(decision.get("accion")) is not str
        or type(decision.get("objeto")) is not str
    ):
        raise ValueError("La decisión acepta únicamente acción y objeto.")
    if estado["terminada"] or estado["paso"] >= MAX_DECISIONES:
        raise ValueError("La partida ha terminado.")
    accion, objeto = decision["accion"], decision["objeto"]
    if accion not in _acciones(estado).get(objeto, []):
        raise ValueError("Acción no disponible para ese objeto.")
    e = deepcopy(estado)
    antes = e["minutos"]
    e["paso"] += 1
    d = e["datos"]
    lote = next((fila for fila in d["lotes"] if fila["id"] == objeto), None)
    pedido = next((p for p in d["pedidos"] if p["id"] == objeto), None)
    if lote:
        mensaje = _lote(e, accion, lote)
    elif pedido:
        mensaje = _pedido(e, accion, pedido)
    elif accion == "esperar":
        _tiempo(e, 5)
        mensaje = "El reloj simulado avanzó cinco minutos; no se movió inventario."
    elif accion == "cerrar":
        e.update(terminada=True, motivo_cierre="cierre anticipado")
        mensaje = "Práctica cerrada; pedidos no despachados permanecen como incumplimientos, sin inventar salidas."
        _evento(e, "cierre", "control", mensaje)
    else:
        recurso = d["recursos"][0]
        # La reparación ocupó 14 minutos completos; evita una recuperación natural
        # simultánea que atribuya dos causas diferentes al mismo evento.
        recurso["recuperacion_en"] = e["minutos"] + 14
        _tiempo(e, 14)
        recurso.update(estado="operativo", reparado=True)
        if d["eventos"] and d["eventos"][-1]["tipo"] == "recuperacion":
            d["eventos"][-1].update(
                tipo="reparacion",
                descripcion="Montacargas restaurado tras reparación didáctica de 14 minutos.",
            )
        mensaje = "Reparación terminada; montacargas disponible."
    e["mensaje"] = mensaje
    e["historial"].append(
        {
            "paso": e["paso"],
            "accion": accion,
            "objeto": objeto,
            "mensaje": mensaje,
            "efecto": e["minutos"] - antes,
            "minutos": e["minutos"],
        }
    )
    _actualizar(e)
    _serie(e)
    validar_estado(e)
    return e


def observacion(estado):
    validar_estado(estado)
    e = deepcopy(estado)
    for lote in e["datos"]["lotes"]:
        if not lote["inspeccionado"]:
            lote.pop("defectuosas", None)
    return e


def datasets(caso="cd-normal", semilla=42):
    """Entradas de aula; nunca revela defectos no inspeccionados ni resultados."""
    e = observacion(crear_estado(caso, semilla))
    return {
        "familia": FAMILIA,
        "caso": caso,
        "semilla": semilla,
        "version_motor": VERSION,
        "version_caso": VERSION_CASO,
        "version_dataset": DATASET_VERSION,
        "supuestos": deepcopy(SUPUESTOS),
        **{
            k: deepcopy(e["datos"][k])
            for k in ("productos", "lotes", "ubicaciones", "pedidos", "recursos")
        },
    }


def referencia(caso="cd-normal", semilla=42):
    """Política realizable: recibir, ABC, reparar y pedidos por promesa/ID.

    No llama resultado(), por lo que puntuar no crea una recursión de políticas.
    Devuelve las decisiones exactas para reproducir y revisar la comparación.
    """
    e = crear_estado(caso, semilla)
    decisiones = []

    def aplicar(accion, objeto):
        nonlocal e
        decision = {"accion": accion, "objeto": objeto}
        e = actuar(e, decision)
        decisiones.append(decision)

    for inicial in e["datos"]["lotes"]:
        identificador = inicial["id"]
        aplicar("inspeccionar", identificador)
        lote = next(fila for fila in e["datos"]["lotes"] if fila["id"] == identificador)
        if lote["defectuosas"]:
            aplicar("rechazar", identificador)
        aplicar("recibir", identificador)
    for inicial in e["datos"]["lotes"]:
        if e["datos"]["recursos"][0]["estado"] == "averiado":
            aplicar("reparar", "montacargas")
        aplicar("ubicar-" + inicial["sku"][-1].lower(), inicial["id"])
    for inicial in sorted(
        e["datos"]["pedidos"], key=lambda p: (p["prometido_min"], p["id"])
    ):
        for linea in inicial["lineas"]:
            for _ in range(linea["cantidad"]):
                aplicar("preparar-" + linea["sku"][-1].lower(), inicial["id"])
        aplicar("embalar", inicial["id"])
        aplicar("despachar", inicial["id"])
    resumen = e["datos"]["resumen"]
    return {
        "nombre": "Recepción completa, ubicación ABC, reparación inmediata y pedidos por promesa/ID",
        "nota": "Política factible de referencia para este dataset; no demuestra optimalidad ni desempeño real.",
        "minutos": e["minutos"],
        "distancia_m": resumen["distancia_m"],
        "otif": round(100 * resumen["pedidos_otif"] / resumen["total_pedidos"], 2),
        "completados": resumen["completados"],
        "errores": e["errores"],
        "decisiones": decisiones,
    }


def resultado(estado):
    validar_estado(estado)
    if not estado["terminada"]:
        raise ValueError("Finaliza el escenario para obtener resultados.")
    resumen = estado["datos"]["resumen"]
    total, completados, otif = (
        resumen["total_pedidos"],
        resumen["completados"],
        resumen["pedidos_otif"],
    )
    ref = referencia(estado["caso"], estado["semilla"])
    partes = {
        "cumplimiento": round(60 * otif / total, 2),
        "eficiencia": round(
            25
            * min(1, ref["minutos"] / max(1, estado["minutos"]))
            * completados
            / total,
            2,
        ),
        "precision": round(15 * max(0, 1 - estado["errores"] / 10), 2),
    }
    metricas = {
        "otif": round(100 * otif / total, 2),
        "minutos": estado["minutos"],
        "errores": estado["errores"],
        "distancia_m": resumen["distancia_m"],
        "completados": completados,
        "diferencia_balance": resumen["diferencia_balance"],
        "total_pedidos": total,
        "unidades_despachadas": resumen["unidades_despachadas"],
    }
    return {
        "puntaje": round(max(0, min(100, sum(partes.values()))), 2),
        "componentes": partes,
        "rubrica": "OTIF 60 + eficiencia temporal ponderada por pedidos despachados 25 + precisión operativa 15. Puntaje didáctico; no es una nota académica automática.",
        "criterios": [
            {
                "id": "cumplimiento",
                "peso": 60,
                "puntos": partes["cumplimiento"],
                "formula": "60 × pedidos OTIF / todos los pedidos comprometidos",
            },
            {
                "id": "eficiencia",
                "peso": 25,
                "puntos": partes["eficiencia"],
                "formula": "25 × mínimo(1, minutos de referencia / máximo(1, minutos propios)) × pedidos despachados / total",
            },
            {
                "id": "precision",
                "peso": 15,
                "puntos": partes["precision"],
                "formula": "15 × máximo(0, 1 − intentos operativos inválidos / 10)",
            },
        ],
        "metricas": metricas,
        "kpis": deepcopy(estado["kpis"]),
        "balances": deepcopy(estado["datos"]["balances"]),
        "pedidos": deepcopy(estado["datos"]["pedidos"]),
        "referencia": ref,
        "motivo_cierre": estado["motivo_cierre"],
        "pendientes": total - completados,
        "tiempo_objetivo": ref["minutos"],
        "minutos": estado["minutos"],
        "errores": estado["errores"],
        "familia": FAMILIA,
        "caso": estado["caso"],
        "semilla": estado["semilla"],
        "version_motor": VERSION,
        "version_caso": VERSION_CASO,
        "version_dataset": DATASET_VERSION,
        "nota_referencia": ref["nota"],
    }
