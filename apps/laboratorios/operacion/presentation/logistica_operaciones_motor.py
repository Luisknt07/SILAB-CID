"""Casos operativos reproducibles con balances y evaluación calculados en servidor.

Geometría y animación representan el proceso; no son un motor físico, aduanero
ni un controlador de maquinaria. Todos los datos son sintéticos y adimensionales
salvo las unidades explícitas. Ninguna decisión ejecuta equipos reales.
"""

from copy import deepcopy
from math import hypot, isfinite
from random import Random
from statistics import mean

VERSION = "1.0.0"
VERSION_CASO = "1.0.0"
MAX_DECISIONES = 120
MAX_NODOS = 4096

FUENTES = {
    "trazabilidad": {
        "titulo": "GS1 · Trazabilidad y eventos EPCIS",
        "url": "https://www.gs1.org/standards/epcis",
    },
    "seguridad": {
        "titulo": "OSHA · Riesgos y soluciones en almacenes",
        "url": "https://www.osha.gov/warehousing/hazards-solutions",
    },
    "rutas": {
        "titulo": "OR-Tools · Capacidad y ventanas de tiempo",
        "url": "https://developers.google.com/optimization/routing",
    },
    "simulacion": {
        "titulo": "SimPy · Simulación por eventos discretos",
        "url": "https://simpy.readthedocs.io/en/stable/",
    },
    "aduana": {
        "titulo": "SENAE · Proceso de exportación",
        "url": "https://www.aduana.gob.ec/servicio-al-ciudadano/para-exportar/",
    },
    "robotica": {
        "titulo": "Gazebo · Simulación y sensores para robótica",
        "url": "https://gazebosim.org/libs/sim/",
    },
    "drones": {
        "titulo": "PX4 · Simulación SITL y HITL",
        "url": "https://docs.px4.io/main/en/simulation/",
    },
    "ia": {
        "titulo": "scikit-learn · Validación temporal",
        "url": "https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split",
    },
    "ia_riesgo": {
        "titulo": "NIST · AI Risk Management Framework",
        "url": "https://www.nist.gov/itl/ai-risk-management-framework",
    },
    "xr": {
        "titulo": "MDN · WebXR, permisos y seguridad",
        "url": "https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API/Permissions_and_security",
    },
}


def _caso(titulo, area, escena, resumen, objetivo, reglas, acciones, fuentes):
    return {
        "titulo": titulo,
        "area": area,
        "escena": escena,
        "resumen": resumen,
        "objetivo": objetivo,
        "reglas": reglas,
        "acciones": [{"id": clave, "titulo": valor} for clave, valor in acciones],
        "fuentes": [FUENTES[clave] for clave in fuentes],
        "version": VERSION_CASO,
        "datos": "Datos sintéticos reproducibles; modelo operativo simplificado.",
    }


CASOS = {
    "almacen-trazabilidad": _caso(
        "Almacén · Del muelle al despacho",
        "Almacén e intralogística",
        "almacen",
        "Seis pallets, un rechazo de calidad, dos zonas de almacenamiento y un pedido urgente.",
        "Despachar tres pallets completos respetando calidad, capacidad y FIFO; conservar el balance de existencias.",
        [
            "Inspecciona cada pallet antes de recibirlo; el lote dañado debe rechazarse.",
            "La ubicación cercana admite tres pallets; reserva admite seis. Cada pallet contiene dos unidades.",
            "Se prepara primero el pallet recibido de menor número de lote (FIFO). Empaca antes de despachar.",
            "Las acciones consumen minutos; los intentos inválidos cuestan dos minutos y reducen precisión.",
        ],
        [
            ("inspeccionar", "Inspeccionar calidad"),
            ("recibir", "Registrar recepción"),
            ("rechazar", "Rechazar daño"),
            ("almacenar-cerca", "Ubicar en zona cercana"),
            ("almacenar-reserva", "Ubicar en reserva"),
            ("preparar", "Preparar pedido FIFO"),
            ("empacar", "Verificar y empacar"),
            ("despachar", "Despachar"),
        ],
        ["trazabilidad", "seguridad"],
    ),
    "puerto-contenedores": _caso(
        "Puerto · Terminal de contenedores",
        "Comercio exterior y operaciones portuarias",
        "puerto",
        "Un buque, cuatro contenedores, grúa, patio refrigerado y control documental.",
        "Liberar cuatro contenedores sin romper cadena de frío; comparar permanencia y productividad del terminal.",
        [
            "Atraque antes de descarga; mantenimiento de grúa reduce cada ciclo de cinco a tres minutos.",
            "Valida documentos antes de liberar. El patio refrigerado es obligatorio para contenedores perecederos.",
            "No equivale a una autorización aduanera real. Los tiempos de control son parámetros didácticos.",
            "Permanencia: minutos desde el atraque hasta la salida. Meta de cadena de frío: salida antes de 90 minutos.",
        ],
        [
            ("atracar", "Asignar atraque"),
            ("mantener", "Preparar grúa"),
            ("documentar", "Validar documentos"),
            ("descargar", "Descargar del buque"),
            ("patio-general", "Trasladar a patio general"),
            ("patio-frio", "Trasladar a patio refrigerado"),
            ("liberar", "Liberar control"),
            ("salir", "Despachar por puerta"),
        ],
        ["aduana", "trazabilidad", "simulacion"],
    ),
    "fabrica-flujo": _caso(
        "Smart factory · Flujo y cuello de botella",
        "Producción y gestión de operaciones",
        "fabrica",
        "Una línea de tres estaciones, buffers limitados, robot y control de calidad.",
        "Producir 12 unidades buenas con el menor tiempo de entrega y sin sobrepasar buffers.",
        [
            "Cada avance representa cinco minutos. Tasas iniciales: 4, 2 y 3 unidades por intervalo.",
            "Alimentación admite 12 unidades; cada buffer intermedio ocho. Una unidad solo avanza una estación por intervalo.",
            "Mejorar la estación 2 aumenta su capacidad a cuatro e introduce diez minutos de parada.",
            "Calibrar calidad cuesta cinco minutos y elimina un defecto determinista por cada sexto producto.",
            "OEE = disponibilidad × rendimiento × calidad. Capacidad de diseño: tres unidades por cinco minutos (ciclo ideal 5/3 min/unidad); no es una certificación industrial.",
        ],
        [
            ("abastecer", "Cargar lote de 12"),
            ("mejorar", "Equilibrar estación"),
            ("calibrar", "Calibrar calidad"),
            ("avanzar", "Avanzar cinco minutos"),
        ],
        ["simulacion", "robotica", "trazabilidad"],
    ),
    "transporte-rutas": _caso(
        "Transporte · Última milla y ventanas",
        "Transporte y distribución",
        "transporte",
        "Depósito, cinco clientes y un camión de ocho unidades; ruta sobre una red sintética.",
        "Entregar todos los pedidos, regresar al depósito y reducir kilómetros y retrasos sin exceder capacidad.",
        [
            "Las distancias son euclidianas en kilómetros; velocidad 30 km/h y servicio cinco minutos por cliente.",
            "Carga máxima ocho unidades. Regresa al depósito para recargar; la recarga cuesta diez minutos.",
            "Se espera si se llega antes de abrir una ventana. Llegar después del cierre cuenta como entrega tardía.",
            "Se comparan recorridos; no se afirma encontrar el óptimo global ni se utilizan mapas reales.",
        ],
        [
            ("cargar", "Cargar hasta capacidad"),
            ("entregar", "Visitar y entregar"),
            ("regresar", "Regresar al depósito"),
        ],
        ["rutas"],
    ),
    "robotica-mision": _caso(
        "Robótica y drones · Misión segura",
        "Tecnología y logística inteligente",
        "tecnologia",
        "Un AMR en cuadrícula con obstáculos y una inspección aérea con reserva de batería.",
        "Planificar y ejecutar una ruta libre, identificar tres puntos de inspección y volver con reserva.",
        [
            "A* encuentra una ruta mínima en una cuadrícula 8×6 con cuatro vecinos y costo unitario; obstáculos conocidos.",
            "Cada paso del AMR consume una unidad de batería; primero calibra el sensor.",
            "El dron permanece en entorno simulado: comprobación previa, inspecciones de 12% de batería y regreso de 8%.",
            "Reserva mínima 20%; no se permiten misiones sin energía para regresar ni se ejecutan órdenes sobre hardware.",
        ],
        [
            ("calibrar", "Calibrar sensor"),
            ("planificar", "Planificar ruta A*"),
            ("mover", "Mover un paso del AMR"),
            ("pre-vuelo", "Comprobación previa de dron"),
            ("inspeccionar", "Inspeccionar punto con dron"),
            ("retornar", "Retornar y aterrizar"),
        ],
        ["robotica", "drones", "xr"],
    ),
    "ia-pronostico": _caso(
        "IA aplicada · Pronóstico verificable",
        "Tecnología y logística inteligente",
        "tecnologia",
        "Demanda con tendencia y estacionalidad, tres candidatos y una prueba temporal reservada.",
        "Seleccionar un modelo con validación temporal y evaluar una única vez sobre datos de prueba no utilizados para seleccionar.",
        [
            "Serie de 60 semanas. Entrenamiento 1–36, validación 37–48 y prueba 49–60.",
            "Pronóstico de origen fijo para bloques de 12 semanas: último valor, media de las últimas cuatro semanas del entrenamiento y regresión con tendencia y estacionalidad de período seis.",
            "El modelo se selecciona solo con MAE de validación; luego se vuelve a ajustar con semanas 1–48.",
            "La prueba se revela al evaluar; no vuelve a entrenarse ni cambia la selección después de verla.",
            "No es un LLM ni requiere servicios de pago; son modelos predictivos propios sobre datos sintéticos.",
        ],
        [
            ("entrenar", "Entrenar candidatos"),
            ("seleccionar", "Seleccionar menor MAE"),
            ("evaluar", "Evaluar prueba reservada"),
        ],
        ["ia", "ia_riesgo"],
    ),
}


# Códigos estables de las áreas ya registradas; no se crean áreas paralelas.
AREAS_CASOS = {
    "almacen-trazabilidad": (
        "LOG-ALMACEN",
        "Almacenamiento e intralogística inteligente",
    ),
    "puerto-contenedores": (
        "LOG-AREA-COMERCIO",
        "Logística internacional y operaciones de comercio exterior",
    ),
    "fabrica-flujo": ("LOG-AREA-PRODUCCION", "Logística de producción y operaciones"),
    "transporte-rutas": ("LOG-AREA-TMS", "Transporte, distribución y movilidad"),
    "robotica-mision": ("LOG-AREA-ERP", "Tecnologías aplicadas y simulación logística"),
    "ia-pronostico": ("LOG-AREA-ERP", "Tecnologías aplicadas y simulación logística"),
}
for _clave, (_codigo, _nombre) in AREAS_CASOS.items():
    CASOS[_clave].update(area_codigo=_codigo, area=_nombre)


def catalogo():
    return [{"id": clave, **deepcopy(valor)} for clave, valor in CASOS.items()]


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


def _base(caso, semilla):
    if (
        type(caso) is not str
        or caso not in CASOS
        or type(semilla) is not int
        or not 0 <= semilla <= 2147483647
    ):
        raise ValueError("Caso o semilla inválidos.")
    return {
        "version_motor": VERSION,
        "version_caso": VERSION_CASO,
        "caso": caso,
        "semilla": semilla,
        "paso": 0,
        "minutos": 0,
        "errores": 0,
        "terminada": False,
        "puntaje": None,
        "mensaje": CASOS[caso]["objetivo"],
        "objetos": [],
        "historial": [],
        "kpis": [],
        "series": [],
        "datos": {},
    }


def crear_estado(caso="almacen-trazabilidad", semilla=42):
    e, rng = _base(caso, semilla), Random(semilla)
    d, o = e["datos"], e["objetos"]
    if caso == "almacen-trazabilidad":
        d.update(
            pallets=[
                {"id": f"pallet-{i}", "lote": i, "estado": "pendiente", "dano": False}
                for i in range(1, 7)
            ],
            enviados=0,
        )
        d["pallets"][rng.randrange(6)]["dano"] = True
        for i, (clave, titulo) in enumerate(
            [
                ("recepcion", "Recepción"),
                ("calidad", "Calidad"),
                ("racks", "Racks y reserva"),
                ("picking", "Picking"),
                ("empaque", "Empaque"),
                ("despacho", "Despacho"),
            ]
        ):
            o.append(
                _obj(
                    clave,
                    titulo,
                    clave,
                    clave,
                    [-9 + i * 3.6, 0, -4],
                    "Zona de "
                    + titulo.lower()
                    + ". Selecciona los pallets para operar.",
                )
            )
        for i in range(1, 7):
            o.append(
                _obj(
                    f"pallet-{i}",
                    f"Pallet {i} · lote {i}",
                    "pallet",
                    "recepcion",
                    [-8 + (i % 3) * 2, 0, 2 + (i // 3) * 2],
                    "Dos unidades. FIFO por número de lote; calidad por verificar.",
                    "pendiente",
                )
            )
    elif caso == "puerto-contenedores":
        d.update(
            atracado=False,
            atraque_minutos=None,
            grua_lista=False,
            contenedores=[
                {
                    "id": f"contenedor-{i}",
                    "frio": i % 2 == 0,
                    "documentos": False,
                    "estado": "buque",
                    "salida": None,
                }
                for i in range(1, 5)
            ],
        )
        for clave, nombre, pos in [
            ("buque", "Buque de carga", [-8, 0, -3]),
            ("muelle", "Muelle", [-4, 0, -3]),
            ("grua", "Grúa de pórtico", [-2, 0, -3]),
            ("patio", "Patio de contenedores", [3, 0, 0]),
            ("puerta", "Puerta y control", [9, 0, 3]),
        ]:
            o.append(
                _obj(
                    clave,
                    nombre,
                    clave,
                    "puerto",
                    pos,
                    "Operación portuaria: " + nombre,
                )
            )
        for i, c in enumerate(d["contenedores"]):
            o.append(
                _obj(
                    c["id"],
                    f"Contenedor {i + 1}"
                    + (" · refrigerado" if c["frio"] else " · seco"),
                    "contenedor",
                    "buque",
                    [-8 + i * 1.8, 1, -2],
                    "Cadena de frío obligatoria."
                    if c["frio"]
                    else "Carga seca. Trazabilidad documental requerida.",
                    "buque",
                )
            )
    elif caso == "fabrica-flujo":
        d.update(
            cargado=False,
            capacidades=[4, 2, 3],
            buffers=[0, 0, 0],
            procesadas=0,
            buenas=0,
            defectos=0,
            calibrada=False,
            mejorada=False,
            marcha=0,
            parada=0,
        )
        for i in range(3):
            o.append(
                _obj(
                    f"estacion-{i + 1}",
                    f"Estación {i + 1}",
                    "maquina",
                    "produccion",
                    [-7 + i * 6, 0, 0],
                    f"Capacidad inicial {d['capacidades'][i]} unidades cada cinco minutos. Buffer de {12 if i == 0 else 8} unidades.",
                )
            )
        o.extend(
            [
                _obj(
                    "cinta",
                    "Cinta y alimentación",
                    "cinta",
                    "produccion",
                    [0, 0, 3],
                    "Lote único de 12 unidades; transferencias simultáneas.",
                ),
                _obj(
                    "robot",
                    "Robot y control de calidad",
                    "robot",
                    "produccion",
                    [7, 0, 3],
                    "Calibra para prevenir defectos; no controla maquinaria real.",
                ),
            ]
        )
    elif caso == "transporte-rutas":
        puntos = [(-6, -4), (1, -5), (7, -2), (6, 5), (-4, 5)]
        d.update(
            pos=[0, 0],
            carga=0,
            km=0.0,
            entregas=0,
            tardias=0,
            clientes=[
                {
                    "id": f"cliente-{i + 1}",
                    "pos": list(p),
                    "demanda": 2 + rng.randrange(2),
                    "ventana": [0 if i < 2 else 20, 45 + i * 18],
                    "entregado": False,
                }
                for i, p in enumerate(puntos)
            ],
        )
        d.update(
            total_unidades=sum(c["demanda"] for c in d["clientes"]),
            cargadas=0,
            unidades_entregadas=0,
            recargas=0,
        )
        d["inventario_deposito"] = d["total_unidades"]
        o.extend(
            [
                _obj(
                    "hub",
                    "Depósito",
                    "hub",
                    "transporte",
                    [0, 0, 0],
                    "Capacidad del camión ocho unidades. Recarga diez minutos.",
                ),
                _obj(
                    "camion-1",
                    "Camión de reparto",
                    "camion",
                    "transporte",
                    [0, 0, 1],
                    "Velocidad sintética 30 km/h; regresa para recargar.",
                ),
            ]
        )
        for c in d["clientes"]:
            o.append(
                _obj(
                    c["id"],
                    c["id"].replace("-", " ").title(),
                    "cliente",
                    "transporte",
                    [c["pos"][0], 0, c["pos"][1]],
                    f"Pedido {c['demanda']} unidades. Ventana {c['ventana'][0]}–{c['ventana'][1]} min.",
                )
            )
    elif caso == "robotica-mision":
        d.update(
            calibrado=False,
            ruta=[],
            posicion=[0, 0],
            meta=[7, 5],
            obstaculos=[[3, y] for y in range(5)] + [[5, 3]],
            bateria_amr=40,
            pre_vuelo=False,
            bateria_dron=80,
            inspecciones=[],
            eventos_inspeccion=[],
            aterrizado=False,
            posicion_dron=[3, 0.5, 1],
            ancho=8,
            alto=6,
        )
        o.extend(
            [
                _obj(
                    "sensor",
                    "Sensor de seguridad",
                    "sensor",
                    "tecnologia",
                    [-8, 0, -4],
                    "Calibración previa al movimiento; obstáculos conocidos.",
                ),
                _obj(
                    "robotica",
                    "AMR y planificador A*",
                    "robot",
                    "tecnologia",
                    [-7, 0, -3],
                    "Cuadrícula 8×6; cuatro vecinos, costo unitario y distancia Manhattan.",
                ),
                _obj(
                    "dron-1",
                    "Dron de inspección",
                    "dron",
                    "tecnologia",
                    [3, 0.5, 1],
                    "Batería inicial 80%. Reserva 20% + retorno 8%. Cada inspección modela un trayecto abstracto; no hay física de vuelo.",
                ),
            ]
        )
        for i in range(3):
            o.append(
                _obj(
                    f"inspeccion-{i + 1}",
                    f"Punto de inspección {i + 1}",
                    "sensor",
                    "tecnologia",
                    [i * 3 - 2, 0, 4],
                    "Inspección consume 12% de batería; muestra un evento sintético.",
                )
            )
    else:
        # Ruido independiente; el juego del usuario no altera la prueba.
        serie = [
            round(40 + 0.65 * t + [0, 8, 4, -3, -6, -2][t % 6] + rng.uniform(-2, 2), 2)
            for t in range(60)
        ]
        d.update(
            serie=serie,
            modelos=[],
            seleccionado=None,
            evaluado=False,
            particiones={
                "entrenamiento": [1, 36],
                "validacion": [37, 48],
                "prueba": [49, 60],
            },
        )
        o.extend(
            [
                _obj(
                    "sensor",
                    "Datos y calidad",
                    "sensor",
                    "tecnologia",
                    [-6, 0, 0],
                    "60 semanas sintéticas: partición temporal36/12/12.",
                ),
                _obj(
                    "pronostico",
                    "Modelos de pronóstico",
                    "servidor",
                    "tecnologia",
                    [0, 0, 0],
                    "Último valor, media móvil4 y regresión tendencia+estacionalidad.",
                ),
                _obj(
                    "robotica",
                    "Aplicación a inventario",
                    "robot",
                    "tecnologia",
                    [6, 0, 0],
                    "Evalúa errores antes de automatizar decisiones de abastecimiento.",
                ),
            ]
        )
    return _actualizar(e)


def _puntos(e):
    return {o["id"]: o for o in e["objetos"]}


def _acciones(e):
    d, caso = e["datos"], e["caso"]
    mapa = {}
    if caso == "almacen-trazabilidad":
        for p in d["pallets"]:
            s = p["estado"]
            mapa[p["id"]] = {
                "pendiente": ["inspeccionar"],
                "inspeccionado": ["rechazar"] if p["dano"] else ["recibir"],
                "recibido": ["almacenar-cerca", "almacenar-reserva"],
                "cerca": ["preparar"],
                "reserva": ["preparar"],
                "preparado": ["empacar"],
                "empacado": ["despachar"],
            }.get(s, [])
    elif caso == "puerto-contenedores":
        mapa["buque"] = [] if d["atracado"] else ["atracar"]
        mapa["grua"] = [] if d["grua_lista"] else ["mantener"]
        for c in d["contenedores"]:
            a = [] if c["documentos"] or c["estado"] == "salida" else ["documentar"]
            a += {
                "buque": ["descargar"] if d["atracado"] else [],
                "muelle": ["patio-frio", "patio-general"],
                "patio": ["liberar"] if c["documentos"] else [],
                "liberado": ["salir"],
            }.get(c["estado"], [])
            mapa[c["id"]] = a
    elif caso == "fabrica-flujo":
        mapa.update(
            {
                "cinta": ["avanzar"] if d["cargado"] else ["abastecer"],
                "estacion-2": [] if d["mejorada"] else ["mejorar"],
                "robot": [] if d["calibrada"] else ["calibrar"],
            }
        )
    elif caso == "transporte-rutas":
        mapa["hub"] = ["cargar"] if d["pos"] == [0, 0] else ["regresar"]
        mapa["camion-1"] = mapa["hub"]
        for c in d["clientes"]:
            mapa[c["id"]] = [] if c["entregado"] else ["entregar"]
    elif caso == "robotica-mision":
        mapa["sensor"] = [] if d["calibrado"] else ["calibrar"]
        mapa["robotica"] = (
            ["planificar"]
            if d["calibrado"] and not d["ruta"] and d["posicion"] != d["meta"]
            else (["mover"] if d["ruta"] else [])
        )
        mapa["dron-1"] = (
            ["retornar"]
            if len(d["inspecciones"]) == 3 and not d["aterrizado"]
            else ([] if d["pre_vuelo"] else ["pre-vuelo"])
        )
        for i in range(1, 4):
            mapa[f"inspeccion-{i}"] = (
                ["inspeccionar"]
                if d["pre_vuelo"] and i not in d["inspecciones"] and not d["aterrizado"]
                else []
            )
    else:
        mapa["pronostico"] = (
            ["entrenar"]
            if not d["modelos"]
            else (["seleccionar"] if d["seleccionado"] is None else ["evaluar"])
        )
    return mapa


def _actualizar(e):
    d, caso, objs = e["datos"], e["caso"], _puntos(e)
    if caso == "almacen-trazabilidad":
        lugares = {
            "pendiente": (-8, 3),
            "inspeccionado": (-5, 3),
            "rechazado": (-5, -5),
            "recibido": (-3, 3),
            "cerca": (0, -2),
            "reserva": (2, -3),
            "preparado": (4, 2),
            "empacado": (6, 2),
            "despachado": (9, 2),
        }
        for i, p in enumerate(d["pallets"]):
            x, z = lugares[p["estado"]]
            objs[p["id"]].update(
                estado=p["estado"], posicion=[x + (i % 2) * 0.8, 0, z + (i // 2) * 0.9]
            )
        rechazo = sum(p["estado"] == "rechazado" for p in d["pallets"])
        inventario = 6 - rechazo - d["enviados"]
        e["terminada"] = d["enviados"] >= 3 and all(
            p["estado"] not in ("pendiente", "inspeccionado", "recibido")
            for p in d["pallets"]
        )
        metricas = [
            ("enviados", "Pallets despachados", d["enviados"], "/3"),
            ("inventario", "Existencias físicas", inventario * 2, "unidades"),
            ("rechazos", "Rechazos de calidad", rechazo, "pallets"),
            (
                "balance",
                "Balance inicial = stock + rechazo + salida",
                inventario + rechazo + d["enviados"],
                "/6",
            ),
        ]
        assert inventario >= 0 and inventario + rechazo + d["enviados"] == 6
    elif caso == "puerto-contenedores":
        salidas = sum(c["estado"] == "salida" for c in d["contenedores"])
        for i, c in enumerate(d["contenedores"]):
            x, z = {
                "buque": (-8, -2),
                "muelle": (-3, -2),
                "patio": (3, 0),
                "liberado": (6, 2),
                "salida": (10, 3),
            }[c["estado"]]
            objs[c["id"]].update(
                estado=c["estado"], posicion=[x + (i % 2) * 1.5, 0, z + (i // 2) * 1.8]
            )
        permanencias = [
            c["salida"] - d["atraque_minutos"]
            for c in d["contenedores"]
            if c["salida"] is not None
        ]
        d["cadena_frio"] = sum(
            c["frio"]
            and c["salida"] is not None
            and c["salida"] - d["atraque_minutos"] > 90
            for c in d["contenedores"]
        )
        e["terminada"] = salidas == 4
        metricas = [
            ("salidas", "Contenedores despachados", salidas, "/4"),
            (
                "permanencia",
                "Permanencia media de salidas",
                round(mean(permanencias), 1) if permanencias else 0,
                "min",
            ),
            (
                "productividad",
                "Productividad del terminal",
                round(salidas * 60 / max(1, e["minutos"] - d["atraque_minutos"]), 2)
                if d["atracado"]
                else 0,
                "contenedores/h",
            ),
            ("frio", "Incumplimientos de frío", d["cadena_frio"], "contenedores"),
        ]
    elif caso == "fabrica-flujo":
        inicial = 12 if d["cargado"] else 0
        assert sum(d["buffers"]) + d["buenas"] + d["defectos"] == inicial
        e["terminada"] = d["cargado"] and sum(d["buffers"]) == 0
        total = d["marcha"] + d["parada"]
        disponibilidad = d["marcha"] / total if total else 0
        rendimiento = d["procesadas"] / (d["marcha"] * 3 / 5) if d["marcha"] else 0
        calidad = d["buenas"] / d["procesadas"] if d["procesadas"] else 0
        d.update(
            disponibilidad=disponibilidad,
            rendimiento=min(1, rendimiento),
            calidad=calidad,
            ciclo_ideal_minutos=5 / 3,
        )
        d["oee"] = round(100 * disponibilidad * min(1, rendimiento) * calidad, 2)
        metricas = [
            ("buenas", "Unidades conformes", d["buenas"], "/12"),
            ("wip", "Trabajo en proceso", sum(d["buffers"]), "unidades"),
            ("defectos", "Defectos", d["defectos"], "unidades"),
            ("oee", "OEE didáctico", d["oee"], "%"),
        ]
        for i in range(3):
            objs[f"estacion-{i + 1}"]["estado"] = (
                f"{d['buffers'][i]} en buffer · capacidad {d['capacidades'][i]}/5 min"
            )
    elif caso == "transporte-rutas":
        if not (
            0 <= d["carga"] <= 8
            and d["inventario_deposito"] >= 0
            and d["cargadas"] == d["unidades_entregadas"] + d["carga"]
            and d["inventario_deposito"] + d["unidades_entregadas"] + d["carga"]
            == d["total_unidades"]
            and d["unidades_entregadas"]
            == sum(c["demanda"] for c in d["clientes"] if c["entregado"])
        ):
            raise ValueError("No se conserva el balance de carga y entregas.")
        e["terminada"] = d["entregas"] == len(d["clientes"]) and d["pos"] == [0, 0]
        objs["camion-1"]["posicion"] = [d["pos"][0], 0, d["pos"][1]]
        for c in d["clientes"]:
            objs[c["id"]]["estado"] = "entregado" if c["entregado"] else "pendiente"
        metricas = [
            ("entregas", "Clientes atendidos", d["entregas"], "/5"),
            ("km", "Distancia", round(d["km"], 2), "km"),
            ("carga", "Carga actual", d["carga"], "/8 unidades"),
            ("tardias", "Entregas tardías", d["tardias"], "clientes"),
            ("entregadas", "Unidades entregadas", d["unidades_entregadas"], "unidades"),
            (
                "deposito",
                "Inventario del depósito",
                d["inventario_deposito"],
                "unidades",
            ),
            (
                "balance",
                "Depósito + carga + entregas",
                d["inventario_deposito"] + d["carga"] + d["unidades_entregadas"],
                f"/{d['total_unidades']} unidades",
            ),
        ]
    elif caso == "robotica-mision":
        e["terminada"] = (
            d["posicion"] == d["meta"]
            and len(d["inspecciones"]) == 3
            and d["aterrizado"]
        )
        objs["robotica"]["posicion"] = [
            d["posicion"][0] * 1.4 - 7,
            0,
            d["posicion"][1] * 1.4 - 3.5,
        ]
        objs["dron-1"]["posicion"] = d["posicion_dron"][:]
        objs["dron-1"]["estado"] = (
            "aterrizado"
            if d["aterrizado"]
            else ("en misión" if d["pre_vuelo"] else "pendiente de comprobación")
        )
        for i in range(1, 4):
            objs[f"inspeccion-{i}"]["estado"] = (
                "inspeccionado" if i in d["inspecciones"] else "pendiente"
            )
        metricas = [
            ("pasos", "Ruta AMR pendiente", len(d["ruta"]), "celdas"),
            ("bateria-amr", "Batería AMR", d["bateria_amr"], "%"),
            ("inspecciones", "Inspecciones aéreas", len(d["inspecciones"]), "/3"),
            ("bateria-dron", "Batería dron", d["bateria_dron"], "%"),
        ]
    else:
        e["terminada"] = d["evaluado"]
        metricas = [
            ("entrenamiento", "Entrenamiento", 36, "semanas"),
            ("validacion", "Validación", 12, "semanas"),
            ("prueba", "Prueba reservada", 12, "semanas"),
        ]
        if d["evaluado"]:
            metricas.append(("mae", "MAE en prueba", d["mae_prueba"], "unidades"))
        # La prueba nunca se publica antes de evaluar, ni en datos_iniciales.
    e["kpis"] = [
        {"id": clave, "titulo": titulo, "valor": valor, "unidad": unidad}
        for clave, titulo, valor, unidad in metricas
    ] + [
        {
            "id": "tiempo",
            "titulo": "Tiempo de operación",
            "valor": round(e["minutos"], 2),
            "unidad": "min",
        },
        {
            "id": "errores",
            "titulo": "Intentos inválidos",
            "valor": e["errores"],
            "unidad": "intentos",
        },
    ]
    acciones = _acciones(e)
    for o in e["objetos"]:
        o["acciones"] = [] if e["terminada"] else acciones.get(o["id"], [])
    if e["terminada"]:
        e["puntaje"] = resultado(e)["puntaje"]
        e["mensaje"] = (
            "Caso concluido. Revisa la evidencia y compara una nueva partida con la misma semilla."
        )
    return e


def _fallo(e, mensaje):
    e["errores"] += 1
    e["minutos"] += 2
    return mensaje


def _almacen(e, a, identificador):
    d = e["datos"]
    p = next(p for p in d["pallets"] if p["id"] == identificador)
    if a == "inspeccionar":
        p["estado"] = "inspeccionado"
        e["minutos"] += 2
        return (
            "Inspección: daño detectado; corresponde rechazo."
            if p["dano"]
            else "Calidad conforme; registra la recepción."
        )
    if a == "rechazar":
        p["estado"] = "rechazado"
        e["minutos"] += 1
    elif a == "recibir":
        p["estado"] = "recibido"
        e["minutos"] += 2
    elif a.startswith("almacenar-"):
        destino = "cerca" if a == "almacenar-cerca" else "reserva"
        if sum(x["estado"] == destino for x in d["pallets"]) >= (
            3 if destino == "cerca" else 6
        ):
            return _fallo(
                e,
                "Capacidad de la ubicación agotada. Usa la reserva o libera un espacio.",
            )
        p["estado"] = destino
        e["minutos"] += 3 if destino == "cerca" else 6
    elif a == "preparar":
        disponibles = [x for x in d["pallets"] if x["estado"] in ("cerca", "reserva")]
        sin_recibir = [
            x
            for x in d["pallets"]
            if x["estado"] in ("pendiente", "inspeccionado", "recibido")
        ]
        if sin_recibir:
            return _fallo(
                e,
                "Finaliza recepción y ubicación de todos los pallets antes de preparar el pedido.",
            )
        if (
            d["enviados"]
            + sum(x["estado"] in ("preparado", "empacado") for x in d["pallets"])
            >= 3
        ):
            return _fallo(e, "El pedido ya tiene sus tres pallets preparados.")
        if p["lote"] != min(x["lote"] for x in disponibles):
            return _fallo(
                e, "FIFO: prepara primero el menor número de lote disponible."
            )
        e["minutos"] += 3 if p["estado"] == "cerca" else 6
        p["estado"] = "preparado"
    elif a == "empacar":
        p["estado"] = "empacado"
        e["minutos"] += 2
    else:
        p["estado"] = "despachado"
        d["enviados"] += 1
        e["minutos"] += 2
    return f"{p['id']}: {p['estado']}. Balance de existencias conservado."


def _puerto(e, a, identificador):
    d = e["datos"]
    if a == "atracar":
        d["atracado"] = True
        e["minutos"] += 10
        d["atraque_minutos"] = e["minutos"]
        return "Buque atracado; grúa habilitada para descarga."
    if a == "mantener":
        d["grua_lista"] = True
        e["minutos"] += 8
        return "Grúa preparada: ciclo de descarga reducido a tres minutos."
    c = next(c for c in d["contenedores"] if c["id"] == identificador)
    if a == "documentar":
        c["documentos"] = True
        e["minutos"] += 2
    elif a == "descargar":
        c["estado"] = "muelle"
        e["minutos"] += 3 if d["grua_lista"] else 5
    elif a.startswith("patio-"):
        if c["frio"] and a != "patio-frio":
            return _fallo(
                e, "Contenedor perecedero: requiere conexión en patio refrigerado."
            )
        c["estado"] = "patio"
        e["minutos"] += 3
    elif a == "liberar":
        c["estado"] = "liberado"
        e["minutos"] += 4
    else:
        c["estado"] = "salida"
        e["minutos"] += 3
        c["salida"] = e["minutos"]
    return f"{c['id']}: {c['estado']}; evento de trazabilidad registrado."


def _fabrica(e, a):
    d = e["datos"]
    if a == "abastecer":
        d["cargado"] = True
        d["buffers"][0] = 12
        # El buffer de alimentación tiene capacidad12; buffers intermedios8.
        return (
            "Lote cargado: doce unidades en alimentación y buffers intermedios vacíos."
        )
    if a == "mejorar":
        d["mejorada"] = True
        d["capacidades"][1] = 4
        d["parada"] += 10
        e["minutos"] += 10
        return "Estación2 equilibrada. Evalúa si la parada compensa el aumento de capacidad."
    if a == "calibrar":
        d["calibrada"] = True
        d["parada"] += 5
        e["minutos"] += 5
        return "Calidad calibrada; no habrá defectos en este lote sintético."
    b, cap = d["buffers"], d["capacidades"]
    salida = min(b[2], cap[2])
    transferencia2 = min(b[1], cap[1], 8 - b[2] + salida)
    transferencia1 = min(b[0], cap[0], 8 - b[1] + transferencia2)
    b[0] -= transferencia1
    b[1] += transferencia1 - transferencia2
    b[2] += transferencia2 - salida
    for _ in range(salida):
        d["procesadas"] += 1
        if not d["calibrada"] and d["procesadas"] % 6 == 0:
            d["defectos"] += 1
        else:
            d["buenas"] += 1
    d["marcha"] += 5
    e["minutos"] += 5
    assert b[1] <= 8 and b[2] <= 8
    return f"Avance de cinco minutos. {salida} unidades salieron de la línea."


def _transporte(e, a, identificador):
    d = e["datos"]
    if a == "cargar":
        cantidad = min(8 - d["carga"], d["inventario_deposito"])
        if cantidad <= 0:
            return _fallo(e, "El camión ya tiene carga suficiente o está completo.")
        d["carga"] += cantidad
        d["cargadas"] += cantidad
        d["inventario_deposito"] -= cantidad
        d["recargas"] += 1
        e["minutos"] += 10
        return f"Camión cargado con {d['carga']} unidades."
    if a == "regresar":
        distancia = hypot(*d["pos"])
        d["km"] += distancia
        e["minutos"] += distancia * 2
        d["pos"] = [0, 0]
        return "Camión de regreso al depósito; puede recargar o concluir la ruta."
    c = next(c for c in d["clientes"] if c["id"] == identificador)
    if d["carga"] < c["demanda"]:
        return _fallo(e, "Carga insuficiente. Regresa y recarga en el depósito.")
    distancia = hypot(c["pos"][0] - d["pos"][0], c["pos"][1] - d["pos"][1])
    d["km"] += distancia
    e["minutos"] += distancia * 2
    e["minutos"] = max(e["minutos"], c["ventana"][0])
    if e["minutos"] > c["ventana"][1]:
        d["tardias"] += 1
    c["llegada"] = e["minutos"]
    c["tardia"] = e["minutos"] > c["ventana"][1]
    e["minutos"] += 5
    d["pos"] = c["pos"][:]
    d["carga"] -= c["demanda"]
    d["unidades_entregadas"] += c["demanda"]
    d["entregas"] += 1
    c["entregado"] = True
    return f"{identificador}: pedido entregado. Ruta {d['km']:.2f} km."


def ruta_astar(inicio, meta, obstaculos, ancho=8, alto=6):
    """A* sin diagonales, heurística Manhattan admisible; resultado excluye inicio."""
    from heapq import heappop, heappush

    if (
        type(ancho) is not int
        or type(alto) is not int
        or not 1 <= ancho <= 64
        or not 1 <= alto <= 64
        or ancho * alto > MAX_NODOS
    ):
        raise ValueError("Cuadrícula inválida: máximo 4096 nodos y 64 celdas por eje.")

    def celda(valor):
        if (
            type(valor) not in (list, tuple)
            or len(valor) != 2
            or any(type(v) is not int for v in valor)
        ):
            raise ValueError("Cada celda requiere dos coordenadas enteras.")
        if not 0 <= valor[0] < ancho or not 0 <= valor[1] < alto:
            raise ValueError("Coordenadas fuera de la cuadrícula.")
        return tuple(valor)

    if type(obstaculos) not in (list, tuple) or len(obstaculos) > ancho * alto:
        raise ValueError("Lista de obstáculos inválida o demasiado larga.")
    inicio, meta = celda(inicio), celda(meta)
    bloqueados = {celda(p) for p in obstaculos}
    if inicio in bloqueados or meta in bloqueados:
        raise ValueError("Inicio y meta deben estar libres.")
    cola, costos, anterior = [(0, inicio)], {inicio: 0}, {}
    while cola:
        _, nodo = heappop(cola)
        if nodo == meta:
            ruta = []
            while nodo != inicio:
                ruta.append(list(nodo))
                nodo = anterior[nodo]
            return list(reversed(ruta))
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            vecino = (nodo[0] + dx, nodo[1] + dy)
            if (
                not 0 <= vecino[0] < ancho
                or not 0 <= vecino[1] < alto
                or vecino in bloqueados
            ):
                continue
            costo = costos[nodo] + 1
            if costo < costos.get(vecino, 10**9):
                costos[vecino] = costo
                anterior[vecino] = nodo
                heappush(
                    cola,
                    (
                        costo + abs(vecino[0] - meta[0]) + abs(vecino[1] - meta[1]),
                        vecino,
                    ),
                )
    raise ValueError("No hay ruta libre hacia la meta.")


def _robotica(e, a, identificador):
    d = e["datos"]
    if a == "calibrar":
        d["calibrado"] = True
        e["minutos"] += 2
    elif a == "planificar":
        d["ruta"] = ruta_astar(d["posicion"], d["meta"], d["obstaculos"])
        e["minutos"] += 1
    elif a == "mover":
        if d["bateria_amr"] - 1 < 20:
            return _fallo(e, "Reserva AMR insuficiente.")
        d["posicion"] = d["ruta"].pop(0)
        d["bateria_amr"] -= 1
        e["minutos"] += 0.5
    elif a == "pre-vuelo":
        d["pre_vuelo"] = True
        e["minutos"] += 3
    elif a == "inspeccionar":
        if d["bateria_dron"] - 12 - 8 < 20:
            return _fallo(
                e, "La misión no deja batería suficiente para retorno y reserva20%."
            )
        d["inspecciones"].append(int(identificador.rsplit("-", 1)[1]))
        d["bateria_dron"] -= 12
        e["minutos"] += 3
        punto = _puntos(e)[identificador]["posicion"]
        d["posicion_dron"] = [punto[0], 2, punto[2]]
        d["eventos_inspeccion"].append(
            {
                "punto": identificador,
                "minutos": e["minutos"],
                "resultado": "Zona inspeccionada sin incidencia en este escenario sintético.",
            }
        )
    else:
        d["bateria_dron"] -= 8
        d["aterrizado"] = True
        d["posicion_dron"] = [3, 0.5, 1]
        e["minutos"] += 2
    return "Operación simulada completada. Se mantienen las reservas de seguridad."


def _resolver(matriz, vector):
    """Eliminación gaussiana con pivoteo para regresión pequeña sin dependencias."""
    if (
        not 1 <= len(matriz) <= 8
        or len(vector) != len(matriz)
        or any(len(fila) != len(matriz) for fila in matriz)
    ):
        raise ValueError(
            "Sistema lineal inválido: matriz cuadrada de hasta ocho filas."
        )
    if any(
        type(v) not in (int, float) or not isfinite(v) for fila in matriz for v in fila
    ) or any(type(v) not in (int, float) or not isfinite(v) for v in vector):
        raise ValueError("El sistema lineal requiere números finitos.")
    a = [list(map(float, fila)) + [float(y)] for fila, y in zip(matriz, vector)]
    n = len(a)
    for i in range(n):
        pivote = max(range(i, n), key=lambda j: abs(a[j][i]))
        a[i], a[pivote] = a[pivote], a[i]
        if abs(a[i][i]) < 1e-10:
            raise ValueError("Datos insuficientes para ajustar regresión.")
        divisor = a[i][i]
        a[i] = [v / divisor for v in a[i]]
        for j in range(n):
            if j != i:
                factor = a[j][i]
                a[j] = [x - factor * y for x, y in zip(a[j], a[i])]
    return [fila[-1] for fila in a]


def _predecir(serie, limite, hasta, modelo):
    if (
        type(serie) not in (list, tuple)
        or len(serie) > 60
        or any(type(v) not in (int, float) or not isfinite(v) for v in serie)
    ):
        raise ValueError("Serie inválida: hasta sesenta observaciones finitas.")
    if (
        type(limite) is not int
        or type(hasta) is not int
        or not 4 <= limite <= hasta <= 60
        or limite > len(serie)
        or modelo not in ("ultimo", "media4", "regresion")
    ):
        raise ValueError("Modelo u horizonte de pronóstico inválido.")
    train = serie[:limite]
    if modelo == "ultimo":
        return [train[-1]] * (hasta - limite)
    if modelo == "media4":
        return [mean(train[-4:])] * (hasta - limite)

    # Intercepto, tendencia y cinco variables indicadoras: sexta es referencia.
    def variables(t):
        return [1, t] + [int(t % 6 == j) for j in range(5)]

    x = [variables(t) for t in range(limite)]
    beta = _resolver(
        [[sum(f[i] * f[j] for f in x) for j in range(7)] for i in range(7)],
        [sum(f[i] * y for f, y in zip(x, train)) for i in range(7)],
    )
    return [
        sum(v * b for v, b in zip(variables(t), beta)) for t in range(limite, hasta)
    ]


def _ia(e, a):
    d = e["datos"]
    serie = d["serie"]
    if a == "entrenar":
        titulos = {
            "ultimo": "Último valor observado",
            "media4": "Media de últimas cuatro semanas (origen fijo)",
            "regresion": "Regresión con tendencia y estacionalidad",
        }
        d["modelos"] = []
        for modelo in ("ultimo", "media4", "regresion"):
            pred = _predecir(serie, 36, 48, modelo)
            mae = mean(abs(y - p) for y, p in zip(serie[36:48], pred))
            d["modelos"].append(
                {
                    "id": modelo,
                    "titulo": titulos[modelo],
                    "mae_validacion": round(mae, 4),
                    "mae_validacion_exacto": mae,
                    "predicciones_validacion": pred,
                }
            )
        e["minutos"] += 1
        return "Tres candidatos ajustados con 1–36. Validación 37–48 calculada; prueba 49–60 aún reservada."
    if a == "seleccionar":
        d["seleccionado"] = min(
            d["modelos"], key=lambda m: (m["mae_validacion_exacto"], m["id"])
        )["id"]
        e["minutos"] += 1
        return "Seleccionado por menor MAE de validación: " + d["seleccionado"]
    pred = _predecir(serie, 48, 60, d["seleccionado"])
    referencia = _predecir(serie, 48, 60, "ultimo")
    mae = mean(abs(y - p) for y, p in zip(serie[48:], pred))
    mae_referencia = mean(abs(y - p) for y, p in zip(serie[48:], referencia))
    d.update(
        mae_prueba=round(mae, 4),
        mae_referencia=round(mae_referencia, 4),
        mae_prueba_exacto=mae,
        mae_referencia_exacto=mae_referencia,
        predicciones=[round(p, 4) for p in pred],
        predicciones_referencia=referencia,
        evaluado=True,
        entrenamiento_final=48,
    )
    e["minutos"] += 1
    return f"Prueba temporal final: MAE {d['mae_prueba']:.4f}. Comparar con último valor {d['mae_referencia']:.4f}."


def _validar_cabecera(estado):
    if (
        type(estado) is not dict
        or estado.get("version_motor") != VERSION
        or estado.get("version_caso") != VERSION_CASO
        or type(estado.get("caso")) is not str
        or estado["caso"] not in CASOS
        or type(estado.get("datos")) is not dict
        or type(estado.get("objetos")) is not list
        or len(estado["objetos"]) > 32
        or type(estado.get("paso")) is not int
        or not 0 <= estado["paso"] <= MAX_DECISIONES
        or type(estado.get("minutos")) not in (int, float)
        or not isfinite(estado["minutos"])
        or estado["minutos"] < 0
        or type(estado.get("errores")) is not int
        or not 0 <= estado["errores"] <= MAX_DECISIONES
        or type(estado.get("terminada")) is not bool
        or type(estado.get("historial")) is not list
        or len(estado["historial"]) > MAX_DECISIONES
        or type(estado.get("series")) is not list
        or len(estado["series"]) > 16
    ):
        raise ValueError("Estado incompatible o fuera de los límites del motor.")


def actuar(estado, decision):
    _validar_cabecera(estado)
    if type(decision) is not dict or set(decision) != {"accion", "objeto"}:
        raise ValueError("La decisión acepta únicamente acción y objeto.")
    a, identificador = decision.get("accion"), decision.get("objeto")
    if type(a) is not str or type(identificador) is not str:
        raise ValueError("Selecciona una acción y un objeto.")
    if estado.get("terminada") or estado["paso"] >= MAX_DECISIONES:
        raise ValueError("La partida terminó o alcanzó el límite de120 decisiones.")
    if identificador not in _puntos(estado) or a not in _acciones(estado).get(
        identificador, []
    ):
        raise ValueError("Acción no disponible para este objeto en su estado actual.")
    e = deepcopy(estado)
    antes = e["minutos"]
    e["paso"] += 1
    caso = e["caso"]
    if caso == "almacen-trazabilidad":
        mensaje = _almacen(e, a, identificador)
    elif caso == "puerto-contenedores":
        mensaje = _puerto(e, a, identificador)
    elif caso == "fabrica-flujo":
        mensaje = _fabrica(e, a)
    elif caso == "transporte-rutas":
        mensaje = _transporte(e, a, identificador)
    elif caso == "robotica-mision":
        mensaje = _robotica(e, a, identificador)
    else:
        mensaje = _ia(e, a)
    e["minutos"] = round(e["minutos"], 6)
    e["mensaje"] = mensaje
    e["historial"].append(
        {
            "paso": e["paso"],
            "accion": a,
            "objeto": identificador,
            "mensaje": mensaje,
            "efecto": round(e["minutos"] - antes, 2),
            "minutos": round(e["minutos"], 2),
        }
    )
    e = _actualizar(e)
    # Series pequeñas y acotadas a120: no descargamos tablas de toda la plataforma.
    for kpi in e["kpis"]:
        serie = next((s for s in e["series"] if s["id"] == kpi["id"]), None)
        if serie is None:
            serie = {
                "id": kpi["id"],
                "titulo": kpi["titulo"],
                "unidad": kpi["unidad"],
                "puntos": [],
            }
            e["series"].append(serie)
        serie["puntos"].append({"paso": e["paso"], "valor": kpi["valor"]})
    return e


def _referencia_transporte(datos):
    """Ruta factible de prioridad por cierre de ventana; no afirma optimalidad."""
    pendientes = deepcopy(datos["clientes"])
    posicion, carga, minutos, kilometros, tardias = [0, 0], 0, 0.0, 0.0, 0
    while pendientes:
        if posicion == [0, 0]:
            carga = min(8, sum(c["demanda"] for c in pendientes))
            minutos += 10
        candidatos = [c for c in pendientes if c["demanda"] <= carga]
        if not candidatos:
            distancia = hypot(*posicion)
            kilometros += distancia
            minutos += distancia * 2
            posicion = [0, 0]
            continue
        cliente = min(
            candidatos,
            key=lambda c: (
                c["ventana"][1],
                hypot(c["pos"][0] - posicion[0], c["pos"][1] - posicion[1]),
                c["id"],
            ),
        )
        distancia = hypot(
            cliente["pos"][0] - posicion[0], cliente["pos"][1] - posicion[1]
        )
        kilometros += distancia
        minutos = max(minutos + distancia * 2, cliente["ventana"][0])
        tardias += minutos > cliente["ventana"][1]
        minutos += 5
        carga -= cliente["demanda"]
        posicion = cliente["pos"][:]
        pendientes.remove(cliente)
    distancia = hypot(*posicion)
    return {
        "nombre": "Prioridad por cierre de ventana, recarga al no poder atender otro pedido",
        "minutos": round(minutos + distancia * 2, 6),
        "km": round(kilometros + distancia, 6),
        "tardias": tardias,
        "nota": "Heurística factible con los mismos clientes, carga, servicio y ventanas; no es el óptimo global.",
    }


def resultado(estado):
    _validar_cabecera(estado)
    if not estado["terminada"]:
        raise ValueError("Concluye el caso para obtener la evaluación.")
    caso, d = estado["caso"], estado["datos"]
    formulas = {
        "fabrica-flujo": "unidades conformes / 12",
        "puerto-contenedores": "1 − contenedores con incumplimiento de frío / 4",
        "transporte-rutas": "1 − entregas tardías / 5",
    }
    if caso == "fabrica-flujo":
        cumplimiento = d["buenas"] / 12
    elif caso == "puerto-contenedores":
        cumplimiento = 1 - d["cadena_frio"] / 4
    elif caso == "transporte-rutas":
        cumplimiento = 1 - d["tardias"] / 5
    else:
        cumplimiento = 1
    objetivos = {
        "almacen-trazabilidad": 65,
        "puerto-contenedores": 78,
        "fabrica-flujo": 45,
        "transporte-rutas": 140,
        "robotica-mision": 23,
        "ia-pronostico": 3,
    }
    referencia = _referencia_transporte(d) if caso == "transporte-rutas" else None
    objetivo = referencia["minutos"] if referencia else objetivos[caso]
    eficiencia = min(1, objetivo / max(1, estado["minutos"]))
    formula_eficiencia = "mínimo(1, tiempo de referencia / tiempo real)"
    if caso == "ia-pronostico":
        mae = d["mae_prueba_exacto"]
        mae_base = d["mae_referencia_exacto"]
        eficiencia = (
            max(0, min(1, 1 - mae / mae_base)) if mae_base else (1 if mae == 0 else 0)
        )
        formula_eficiencia = "máximo(0, 1 − MAE prueba / MAE último valor); referencia perfecta: 1 si MAE propio=0, de lo contrario 0"
    precision = max(0, 1 - estado["errores"] / 10)
    partes = {
        "cumplimiento": round(60 * cumplimiento, 2),
        "eficiencia": round(25 * eficiencia, 2),
        "precision": round(15 * precision, 2),
    }
    informe = {
        "puntaje": max(0, min(100, round(sum(partes.values()), 2))),
        "componentes": partes,
        "rubrica": "Cumplimiento 60 + eficiencia 25 + precisión 15. Referencias realizables de este modelo. "
        "IA: mejora relativa de MAE en prueba frente al último valor. No certifica competencias ni procesos reales.",
        "criterios": [
            {
                "id": "cumplimiento",
                "peso": 60,
                "puntos": partes["cumplimiento"],
                "formula": "60 × "
                + formulas.get(caso, "1 al completar todos los objetivos obligatorios"),
            },
            {
                "id": "eficiencia",
                "peso": 25,
                "puntos": partes["eficiencia"],
                "formula": "25 × " + formula_eficiencia,
            },
            {
                "id": "precision",
                "peso": 15,
                "puntos": partes["precision"],
                "formula": "15 × máximo(0, 1 − errores/10)",
            },
        ],
        "tiempo_objetivo": objetivo,
        "minutos": estado["minutos"],
        "errores": estado["errores"],
        "kpis": deepcopy(estado["kpis"]),
        "version_motor": VERSION,
        "version_caso": VERSION_CASO,
        "nota_referencia": "Las referencias son partidas conocidas realizables o una heurística declarada, no óptimos universales.",
    }
    if referencia:
        informe["referencia"] = referencia
    if caso == "ia-pronostico":
        informe["evaluacion_temporal"] = [
            {
                "semana": i + 49,
                "real": real,
                "prediccion": pred,
                "referencia": base,
                "error_absoluto": abs(real - pred),
            }
            for i, (real, pred, base) in enumerate(
                zip(d["serie"][48:], d["predicciones"], d["predicciones_referencia"])
            )
        ]
    return informe


def observacion(estado):
    """Oculta prueba IA y defectos no inspeccionados, incluso en la exploración pública."""
    _validar_cabecera(estado)
    e = deepcopy(estado)
    if e["caso"] == "ia-pronostico" and not e["terminada"]:
        e["datos"]["serie"] = e["datos"]["serie"][:48]
    if e["caso"] == "almacen-trazabilidad":
        for p in e["datos"]["pallets"]:
            if p["estado"] == "pendiente":
                p.pop("dano", None)
    return e
