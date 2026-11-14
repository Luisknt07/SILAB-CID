"""Modelos operativos puros: procesos completos, efectos físicos y datos reservados."""

from collections import deque
from copy import deepcopy
import json
from math import hypot, isfinite
import random
from statistics import mean
import unittest

from apps.laboratorios.operacion.presentation import logistica_operaciones_motor as motor


class OperacionesMotorTests(unittest.TestCase):
    def aplicar(self, estado, accion, objeto):
        return motor.actuar(estado, {"accion": accion, "objeto": objeto})

    def completar_almacen(self, semilla=42):
        estado = motor.crear_estado("almacen-trazabilidad", semilla)
        buenos = []
        for pallet in estado["datos"]["pallets"]:
            estado = self.aplicar(estado, "inspeccionar", pallet["id"])
            if pallet["dano"]:
                estado = self.aplicar(estado, "rechazar", pallet["id"])
            else:
                estado = self.aplicar(estado, "recibir", pallet["id"])
                buenos.append(pallet["id"])
        for indice, identificador in enumerate(buenos):
            estado = self.aplicar(
                estado,
                "almacenar-cerca" if indice < 3 else "almacenar-reserva",
                identificador,
            )
        for identificador in buenos[:3]:
            for accion in ("preparar", "empacar", "despachar"):
                estado = self.aplicar(estado, accion, identificador)
        return estado

    def completar_puerto(self, semilla=42, mantenimiento=True, documentos_antes=False):
        estado = motor.crear_estado("puerto-contenedores", semilla)
        if mantenimiento:
            estado = self.aplicar(estado, "mantener", "grua")
        if documentos_antes:
            for contenedor in estado["datos"]["contenedores"]:
                estado = self.aplicar(estado, "documentar", contenedor["id"])
        estado = self.aplicar(estado, "atracar", "buque")
        for contenedor in estado["datos"]["contenedores"]:
            identificador = contenedor["id"]
            if not documentos_antes:
                estado = self.aplicar(estado, "documentar", identificador)
            estado = self.aplicar(estado, "descargar", identificador)
            estado = self.aplicar(
                estado,
                "patio-frio" if contenedor["frio"] else "patio-general",
                identificador,
            )
            estado = self.aplicar(estado, "liberar", identificador)
            estado = self.aplicar(estado, "salir", identificador)
        return estado

    def completar_fabrica(self, semilla=42, calibrar=True, mejorar=False):
        estado = motor.crear_estado("fabrica-flujo", semilla)
        if calibrar:
            estado = self.aplicar(estado, "calibrar", "robot")
        if mejorar:
            estado = self.aplicar(estado, "mejorar", "estacion-2")
        estado = self.aplicar(estado, "abastecer", "cinta")
        for _ in range(20):
            if estado["terminada"]:
                return estado
            estado = self.aplicar(estado, "avanzar", "cinta")
        self.fail("La fábrica no terminó dentro del horizonte esperado.")

    def completar_transporte(self, semilla=42):
        estado = motor.crear_estado("transporte-rutas", semilla)
        for _ in range(20):
            if estado["terminada"]:
                return estado
            d = estado["datos"]
            pendientes = [c for c in d["clientes"] if not c["entregado"]]
            if not pendientes:
                estado = self.aplicar(estado, "regresar", "camion-1")
            elif d["pos"] == [0, 0]:
                estado = self.aplicar(estado, "cargar", "camion-1")
                d = estado["datos"]
                candidatos = [
                    c
                    for c in d["clientes"]
                    if not c["entregado"] and c["demanda"] <= d["carga"]
                ]
                cliente = min(
                    candidatos,
                    key=lambda c: (
                        c["ventana"][1],
                        hypot(c["pos"][0] - d["pos"][0], c["pos"][1] - d["pos"][1]),
                        c["id"],
                    ),
                )
                estado = self.aplicar(estado, "entregar", cliente["id"])
            else:
                candidatos = [c for c in pendientes if c["demanda"] <= d["carga"]]
                if not candidatos:
                    estado = self.aplicar(estado, "regresar", "camion-1")
                else:
                    cliente = min(
                        candidatos,
                        key=lambda c: (
                            c["ventana"][1],
                            hypot(c["pos"][0] - d["pos"][0], c["pos"][1] - d["pos"][1]),
                            c["id"],
                        ),
                    )
                    estado = self.aplicar(estado, "entregar", cliente["id"])
        self.fail("El transporte no concluyó en veinte acciones.")

    def completar_robotica(self, semilla=42):
        estado = motor.crear_estado("robotica-mision", semilla)
        estado = self.aplicar(estado, "calibrar", "sensor")
        estado = self.aplicar(estado, "planificar", "robotica")
        for _ in estado["datos"]["ruta"][:]:
            estado = self.aplicar(estado, "mover", "robotica")
        estado = self.aplicar(estado, "pre-vuelo", "dron-1")
        for indice in range(1, 4):
            estado = self.aplicar(estado, "inspeccionar", f"inspeccion-{indice}")
        return self.aplicar(estado, "retornar", "dron-1")

    def completar_ia(self, semilla=42):
        estado = motor.crear_estado("ia-pronostico", semilla)
        for accion in ("entrenar", "seleccionar", "evaluar"):
            estado = self.aplicar(estado, accion, "pronostico")
        return estado

    def test_seis_casos_completables_repetibles_y_rubricas_coherentes(self):
        completadores = {
            "almacen-trazabilidad": self.completar_almacen,
            "puerto-contenedores": self.completar_puerto,
            "fabrica-flujo": self.completar_fabrica,
            "transporte-rutas": self.completar_transporte,
            "robotica-mision": self.completar_robotica,
            "ia-pronostico": self.completar_ia,
        }
        for caso, completar in completadores.items():
            for semilla in (0, 42, 2147483647):
                with self.subTest(caso=caso, semilla=semilla):
                    estado = completar(semilla)
                    self.assertTrue(estado["terminada"])
                    self.assertEqual(estado, completar(semilla))
                    self.assertEqual(json.loads(json.dumps(estado)), estado)
                    self.assertLessEqual(estado["paso"], motor.MAX_DECISIONES)
                    self.assertEqual(estado["errores"], 0)
                    self.assertTrue(all(not o["acciones"] for o in estado["objetos"]))
                    informe = motor.resultado(estado)
                    self.assertTrue(0 <= informe["puntaje"] <= 100)
                    self.assertEqual(
                        informe["puntaje"],
                        round(sum(informe["componentes"].values()), 2),
                    )
                    self.assertEqual(sum(c["peso"] for c in informe["criterios"]), 100)
                    self.assertTrue(
                        all(0 <= c["puntos"] <= c["peso"] for c in informe["criterios"])
                    )
                    self.assertIn("No certifica", informe["rubrica"])
                    self.assertEqual(len(estado["historial"]), estado["paso"])
                    for serie in estado["series"]:
                        self.assertLessEqual(len(serie["puntos"]), motor.MAX_DECISIONES)
                    json.dumps(motor.observacion(estado), allow_nan=False)
                    with self.assertRaises(ValueError):
                        self.aplicar(estado, "avanzar", "cinta")

    def test_catalogo_clonado_y_acciones_reales(self):
        catalogo = motor.catalogo()
        self.assertEqual(len(catalogo), 6)
        for item in catalogo:
            self.assertTrue(item["reglas"])
            self.assertTrue(item["fuentes"])
            estado = motor.crear_estado(item["id"])
            permitidas = {accion["id"] for accion in item["acciones"]}
            for objeto in estado["objetos"]:
                self.assertTrue(set(objeto["acciones"]) <= permitidas)
        catalogo[0]["reglas"].clear()
        self.assertTrue(motor.catalogo()[0]["reglas"])

    def test_semilla_y_caso_estrictos(self):
        for caso in (None, [], {}, True, 1, "falso"):
            with self.subTest(caso=caso), self.assertRaises(ValueError):
                motor.crear_estado(caso)
        for semilla in (None, True, False, "42", 42.0, -1, 2147483648):
            with self.subTest(semilla=semilla), self.assertRaises(ValueError):
                motor.crear_estado(semilla=semilla)

    def test_decisiones_invalidas_fallan_sin_penalizar_ni_mutar(self):
        estado = motor.crear_estado()
        copia = deepcopy(estado)
        invalidas = (
            None,
            [],
            True,
            {},
            {"accion": "inspeccionar"},
            {"objeto": "pallet-1"},
            {"accion": True, "objeto": "pallet-1"},
            {"accion": "inspeccionar", "objeto": 1},
            {"accion": "inspeccionar", "objeto": "pallet-1", "puntaje": 100},
            {"accion": "despachar", "objeto": "pallet-1"},
            {"accion": "inspeccionar", "objeto": "pallet-99"},
        )
        for decision in invalidas:
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                motor.actuar(estado, decision)
            self.assertEqual(estado, copia)
        nuevo = self.aplicar(estado, "inspeccionar", "pallet-1")
        self.assertEqual(estado, copia)
        nuevo["objetos"][0]["nombre"] = "Otro"
        self.assertEqual(estado, copia)
        for entrada in (None, [], {}, {"version_motor": "otro"}):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                motor.actuar(entrada, {"accion": "inspeccionar", "objeto": "pallet-1"})
            with self.assertRaises(ValueError):
                motor.observacion(entrada)

    def test_observacion_no_muta_estado_y_no_muestra_dano_sin_inspeccion(self):
        estado = motor.crear_estado()
        vista = motor.observacion(estado)
        self.assertTrue(all("dano" not in p for p in vista["datos"]["pallets"]))
        self.assertTrue(any(p["dano"] for p in estado["datos"]["pallets"]))
        vista["objetos"][0]["nombre"] = "Cambio"
        self.assertNotEqual(
            vista["objetos"][0]["nombre"], estado["objetos"][0]["nombre"]
        )
        estado = self.aplicar(estado, "inspeccionar", "pallet-1")
        vista = motor.observacion(estado)
        self.assertIn("dano", vista["datos"]["pallets"][0])
        self.assertTrue(all("dano" not in p for p in vista["datos"]["pallets"][1:]))
        with self.assertRaises(ValueError):
            motor.resultado(estado)

    def test_almacen_no_acepta_pallet_danado_y_balance_correcto(self):
        estado = motor.crear_estado()
        danado = next(p["id"] for p in estado["datos"]["pallets"] if p["dano"])
        estado = self.aplicar(estado, "inspeccionar", danado)
        with self.assertRaises(ValueError):
            self.aplicar(estado, "recibir", danado)
        estado = self.aplicar(estado, "rechazar", danado)
        self.assertEqual(
            next(p for p in estado["datos"]["pallets"] if p["id"] == danado)["estado"],
            "rechazado",
        )
        final = self.completar_almacen()
        conteos = {
            situacion: sum(p["estado"] == situacion for p in final["datos"]["pallets"])
            for situacion in ("rechazado", "despachado", "cerca", "reserva")
        }
        self.assertEqual(conteos["rechazado"], 1)
        self.assertEqual(conteos["despachado"], 3)
        self.assertEqual(sum(conteos.values()), 6)
        self.assertEqual(final["minutos"], 65)
        self.assertEqual(final["puntaje"], 100)

    def test_almacen_capacidad_y_fifo_penalizan_decision_semantica(self):
        estado = motor.crear_estado()
        buenos = []
        for pallet in estado["datos"]["pallets"]:
            estado = self.aplicar(estado, "inspeccionar", pallet["id"])
            estado = self.aplicar(
                estado, "rechazar" if pallet["dano"] else "recibir", pallet["id"]
            )
            if not pallet["dano"]:
                buenos.append(pallet["id"])
        for identificador in buenos[:3]:
            estado = self.aplicar(estado, "almacenar-cerca", identificador)
        previo = estado
        estado = self.aplicar(estado, "almacenar-cerca", buenos[3])
        self.assertEqual(estado["errores"], 1)
        self.assertEqual(estado["minutos"], previo["minutos"] + 2)
        self.assertEqual(
            next(p for p in estado["datos"]["pallets"] if p["id"] == buenos[3])[
                "estado"
            ],
            "recibido",
        )
        for identificador in buenos[3:]:
            estado = self.aplicar(estado, "almacenar-reserva", identificador)
        antes = deepcopy(estado["datos"])
        estado = self.aplicar(estado, "preparar", buenos[1])
        self.assertEqual(estado["datos"], antes)
        self.assertEqual(estado["errores"], 2)
        estado = self.aplicar(estado, "preparar", buenos[0])
        self.assertEqual(
            next(p for p in estado["datos"]["pallets"] if p["id"] == buenos[0])[
                "estado"
            ],
            "preparado",
        )

    def test_limite_ciento_veinte_y_series_acotadas(self):
        estado = motor.crear_estado()
        buenos = []
        for pallet in estado["datos"]["pallets"]:
            estado = self.aplicar(estado, "inspeccionar", pallet["id"])
            estado = self.aplicar(
                estado, "rechazar" if pallet["dano"] else "recibir", pallet["id"]
            )
            if not pallet["dano"]:
                buenos.append(pallet["id"])
        for identificador in buenos[:3]:
            estado = self.aplicar(estado, "almacenar-cerca", identificador)
        while estado["paso"] < 120:
            estado = self.aplicar(estado, "almacenar-cerca", buenos[3])
        self.assertEqual(len(estado["historial"]), 120)
        self.assertTrue(all(len(s["puntos"]) == 120 for s in estado["series"]))
        with self.assertRaises(ValueError):
            self.aplicar(estado, "almacenar-cerca", buenos[3])

    def test_puerto_atraque_documentos_frio_y_mantenimiento(self):
        estado = motor.crear_estado("puerto-contenedores")
        with self.assertRaises(ValueError):
            self.aplicar(estado, "descargar", "contenedor-1")
        estado = self.aplicar(estado, "atracar", "buque")
        self.assertEqual(estado["datos"]["atraque_minutos"], 10)
        estado = self.aplicar(estado, "descargar", "contenedor-2")
        antes = deepcopy(estado["datos"])
        estado = self.aplicar(estado, "patio-general", "contenedor-2")
        self.assertEqual(estado["datos"], antes)
        self.assertEqual(estado["errores"], 1)
        estado = self.aplicar(estado, "patio-frio", "contenedor-2")
        with self.assertRaises(ValueError):
            self.aplicar(estado, "liberar", "contenedor-2")
        estado = self.aplicar(estado, "documentar", "contenedor-2")
        self.assertEqual(estado["datos"]["contenedores"][1]["documentos"], True)
        mantenido = self.completar_puerto(mantenimiento=True)
        sencillo = self.completar_puerto(mantenimiento=False)
        ciclos_m = [
            h["efecto"] for h in mantenido["historial"] if h["accion"] == "descargar"
        ]
        ciclos_s = [
            h["efecto"] for h in sencillo["historial"] if h["accion"] == "descargar"
        ]
        self.assertEqual(ciclos_m, [3] * 4)
        self.assertEqual(ciclos_s, [5] * 4)
        self.assertEqual(mantenido["minutos"], 78)
        self.assertEqual(mantenido["puntaje"], 100)

    def test_puerto_permanencia_desde_atraque_y_productividad(self):
        estado = self.completar_puerto(documentos_antes=True)
        d = estado["datos"]
        self.assertEqual(d["atraque_minutos"], 26)
        permanencias = [c["salida"] - d["atraque_minutos"] for c in d["contenedores"]]
        self.assertEqual(permanencias, [13, 26, 39, 52])
        kpis = {k["id"]: k["valor"] for k in estado["kpis"]}
        self.assertEqual(kpis["permanencia"], 32.5)
        self.assertEqual(kpis["productividad"], round(4 * 60 / 52, 2))
        self.assertEqual(kpis["frio"], 0)

    def test_puerto_retraso_real_incumple_meta_de_frio(self):
        estado = motor.crear_estado("puerto-contenedores")
        estado = self.aplicar(estado, "atracar", "buque")
        estado = self.aplicar(estado, "descargar", "contenedor-2")
        for _ in range(45):
            estado = self.aplicar(estado, "patio-general", "contenedor-2")
        for accion in ("documentar", "patio-frio", "liberar", "salir"):
            estado = self.aplicar(estado, accion, "contenedor-2")
        self.assertGreater(
            estado["datos"]["contenedores"][1]["salida"]
            - estado["datos"]["atraque_minutos"],
            90,
        )
        self.assertEqual(estado["datos"]["cadena_frio"], 1)

    def test_fabrica_transferencias_simultaneas_capacidad_y_conservacion(self):
        estado = self.aplicar(motor.crear_estado("fabrica-flujo"), "abastecer", "cinta")
        self.assertEqual(estado["datos"]["buffers"], [12, 0, 0])
        estado = self.aplicar(estado, "avanzar", "cinta")
        self.assertEqual(estado["datos"]["buffers"], [8, 4, 0])
        self.assertEqual(estado["datos"]["procesadas"], 0)
        estado = self.aplicar(estado, "avanzar", "cinta")
        self.assertEqual(estado["datos"]["buffers"], [4, 6, 2])
        self.assertEqual(estado["datos"]["procesadas"], 0)
        while not estado["terminada"]:
            estado = self.aplicar(estado, "avanzar", "cinta")
            d = estado["datos"]
            self.assertEqual(sum(d["buffers"]) + d["buenas"] + d["defectos"], 12)
            self.assertTrue(0 <= d["buffers"][0] <= 12)
            self.assertTrue(all(0 <= b <= 8 for b in d["buffers"][1:]))
        self.assertEqual(estado["datos"]["defectos"], 2)
        self.assertEqual(estado["datos"]["buenas"], 10)

    def test_fabrica_calibrar_mejorar_y_oee_ideal_tres_por_cinco(self):
        base = self.completar_fabrica(calibrar=False)
        calibrada = self.completar_fabrica(calibrar=True)
        mejorada = self.completar_fabrica(calibrar=True, mejorar=True)
        self.assertEqual(calibrada["datos"]["buenas"], 12)
        self.assertEqual(calibrada["datos"]["defectos"], 0)
        self.assertGreater(calibrada["puntaje"], base["puntaje"])
        self.assertEqual(mejorada["datos"]["capacidades"], [4, 4, 3])
        self.assertLess(mejorada["datos"]["marcha"], calibrada["datos"]["marcha"])
        self.assertEqual(mejorada["datos"]["parada"], 15)
        for estado in (base, calibrada, mejorada):
            d = estado["datos"]
            self.assertAlmostEqual(
                d["disponibilidad"], d["marcha"] / (d["marcha"] + d["parada"])
            )
            self.assertAlmostEqual(
                d["rendimiento"], d["procesadas"] / (d["marcha"] * 3 / 5)
            )
            self.assertAlmostEqual(d["calidad"], d["buenas"] / d["procesadas"])
            self.assertEqual(
                d["oee"], round(100 * d["buenas"] * (5 / 3) / estado["minutos"], 2)
            )
        self.assertEqual(calibrada["minutos"], 45)
        self.assertEqual(calibrada["puntaje"], 100)

    def test_transporte_carga_finita_recarga_parcial_y_balance(self):
        estado = motor.crear_estado("transporte-rutas")
        total = sum(c["demanda"] for c in estado["datos"]["clientes"])
        self.assertEqual(estado["datos"]["inventario_deposito"], total)
        estado = self.aplicar(estado, "cargar", "hub")
        self.assertEqual(estado["datos"]["carga"], 8)
        estado = self.aplicar(estado, "entregar", "cliente-1")
        demanda = estado["datos"]["clientes"][0]["demanda"]
        estado = self.aplicar(estado, "regresar", "camion-1")
        estado = self.aplicar(estado, "cargar", "hub")
        d = estado["datos"]
        self.assertEqual(d["carga"], 8)
        self.assertEqual(d["cargadas"], 8 + demanda)
        self.assertEqual(d["unidades_entregadas"], demanda)
        self.assertEqual(
            d["inventario_deposito"] + d["carga"] + d["unidades_entregadas"], total
        )
        antes = deepcopy(d)
        estado = self.aplicar(estado, "cargar", "hub")
        self.assertEqual(estado["datos"], antes)
        self.assertEqual(estado["errores"], 1)
        final = self.completar_transporte()
        self.assertEqual(final["datos"]["carga"], 0)
        self.assertEqual(final["datos"]["inventario_deposito"], 0)
        self.assertEqual(final["datos"]["cargadas"], total)
        self.assertEqual(final["datos"]["unidades_entregadas"], total)
        self.assertEqual(final["datos"]["pos"], [0, 0])

    def test_transporte_sin_carga_no_teletransporta_ni_entrega(self):
        estado = motor.crear_estado("transporte-rutas")
        antes = deepcopy(estado["datos"])
        estado = self.aplicar(estado, "entregar", "cliente-1")
        self.assertEqual(estado["datos"], antes)
        self.assertEqual(estado["minutos"], 2)
        self.assertEqual(estado["errores"], 1)

    def test_transporte_velocidad_ventana_espera_y_tardanza(self):
        estado = self.aplicar(motor.crear_estado("transporte-rutas"), "cargar", "hub")
        # Cliente 3 abre en20; salida10+distancia*2. Se respeta espera y servicio5.
        cliente = estado["datos"]["clientes"][2]
        esperado = max(10 + hypot(*cliente["pos"]) * 2, cliente["ventana"][0])
        estado = self.aplicar(estado, "entregar", cliente["id"])
        self.assertAlmostEqual(estado["minutos"], esperado + 5, places=5)
        self.assertAlmostEqual(
            estado["datos"]["clientes"][2]["llegada"], esperado, places=5
        )
        final = self.completar_transporte()
        self.assertEqual(
            final["datos"]["tardias"],
            sum(c["tardia"] for c in final["datos"]["clientes"]),
        )
        informe = motor.resultado(final)
        self.assertAlmostEqual(
            informe["minutos"], informe["referencia"]["minutos"], places=5
        )
        self.assertIn("no es el óptimo", informe["referencia"]["nota"])
        self.assertAlmostEqual(
            informe["referencia"]["km"], final["datos"]["km"], places=5
        )

    def bfs(self, inicio, meta, bloqueados, ancho=8, alto=6):
        inicio, meta = tuple(inicio), tuple(meta)
        visitados, cola = {inicio}, deque([(inicio, 0)])
        while cola:
            celda, pasos = cola.popleft()
            if celda == meta:
                return pasos
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                vecino = (celda[0] + dx, celda[1] + dy)
                if (
                    0 <= vecino[0] < ancho
                    and 0 <= vecino[1] < alto
                    and vecino not in bloqueados
                    and vecino not in visitados
                ):
                    visitados.add(vecino)
                    cola.append((vecino, pasos + 1))
        return None

    def test_astar_optimal_con_bfs_y_rutas_sin_colisiones(self):
        rng = random.Random(402)
        for _ in range(30):
            bloqueados = {
                (x, y)
                for x in range(8)
                for y in range(6)
                if (x, y) not in ((0, 0), (7, 5)) and rng.random() < 0.2
            }
            minimo = self.bfs([0, 0], [7, 5], bloqueados)
            if minimo is None:
                with self.assertRaises(ValueError):
                    motor.ruta_astar([0, 0], [7, 5], list(bloqueados))
            else:
                ruta = motor.ruta_astar([0, 0], [7, 5], list(bloqueados))
                self.assertEqual(len(ruta), minimo)
                anterior = (0, 0)
                for punto in ruta:
                    self.assertNotIn(tuple(punto), bloqueados)
                    self.assertEqual(
                        abs(punto[0] - anterior[0]) + abs(punto[1] - anterior[1]), 1
                    )
                    anterior = punto
                self.assertEqual(ruta[-1], [7, 5])
        self.assertEqual(motor.ruta_astar([1, 1], [1, 1], []), [])

    def test_astar_limites_coordenadas_bloqueadas_y_nodos_acotados(self):
        for ancho, alto in (
            (True, 6),
            (8, False),
            (0, 6),
            (8, -1),
            (65, 6),
            (8.0, 6),
            (10000, 10000),
        ):
            with self.subTest(ancho=ancho, alto=alto), self.assertRaises(ValueError):
                motor.ruta_astar([0, 0], [1, 1], [], ancho, alto)
        for inicio, meta, obstaculos in (
            ([True, 0], [7, 5], []),
            ([-1, 0], [7, 5], []),
            ([0, 0], [8, 5], []),
            ([0, 0], [7, 5], [[0, 0]]),
            ([0, 0], [7, 5], [[7, 5]]),
            ([0, 0], [7, 5], [[9, 0]]),
            ([0, 0], [7, 5], [[1, 1]] * 49),
            ("00", [7, 5], []),
        ):
            with (
                self.subTest(inicio=inicio, meta=meta, obstaculos=obstaculos),
                self.assertRaises(ValueError),
            ):
                motor.ruta_astar(inicio, meta, obstaculos)
        self.assertEqual(len(motor.ruta_astar([0, 0], [63, 63], [], 64, 64)), 126)

    def test_robotica_geometria_tres_inspecciones_y_reservas(self):
        estado = motor.crear_estado("robotica-mision")
        with self.assertRaises(ValueError):
            self.aplicar(estado, "planificar", "robotica")
        with self.assertRaises(ValueError):
            self.aplicar(estado, "inspeccionar", "inspeccion-1")
        estado = self.aplicar(estado, "calibrar", "sensor")
        estado = self.aplicar(estado, "planificar", "robotica")
        self.assertEqual(len(estado["datos"]["ruta"]), 12)
        previo = deepcopy(estado)
        estado = self.aplicar(estado, "mover", "robotica")
        self.assertNotEqual(estado["datos"]["posicion"], previo["datos"]["posicion"])
        robot = next(o for o in estado["objetos"] if o["id"] == "robotica")
        x, y = estado["datos"]["posicion"]
        self.assertEqual(robot["posicion"], [x * 1.4 - 7, 0, y * 1.4 - 3.5])
        estado = self.aplicar(estado, "pre-vuelo", "dron-1")
        for indice in range(1, 4):
            estado = self.aplicar(estado, "inspeccionar", f"inspeccion-{indice}")
            punto = next(
                o for o in estado["objetos"] if o["id"] == f"inspeccion-{indice}"
            )
            dron = next(o for o in estado["objetos"] if o["id"] == "dron-1")
            self.assertEqual(
                dron["posicion"], [punto["posicion"][0], 2, punto["posicion"][2]]
            )
            self.assertEqual(punto["estado"], "inspeccionado")
            self.assertGreaterEqual(estado["datos"]["bateria_dron"] - 8, 20)
        self.assertEqual(len(estado["datos"]["eventos_inspeccion"]), 3)
        with self.assertRaises(ValueError):
            self.aplicar(estado, "inspeccionar", "inspeccion-1")
        estado = self.aplicar(estado, "retornar", "dron-1")
        self.assertEqual(estado["datos"]["bateria_dron"], 36)
        self.assertEqual(estado["datos"]["posicion_dron"], [3, 0.5, 1])
        final = self.completar_robotica()
        self.assertEqual(final["datos"]["bateria_amr"], 28)
        self.assertEqual(final["minutos"], 23)
        self.assertEqual(final["puntaje"], 100)

    def test_ia_observacion_reserva_prueba_y_no_publica_resultados_anticipados(self):
        estado = motor.crear_estado("ia-pronostico")
        self.assertEqual(len(estado["datos"]["serie"]), 60)
        for accion in (None, "entrenar", "seleccionar"):
            if accion:
                estado = self.aplicar(estado, accion, "pronostico")
            vista = motor.observacion(estado)
            self.assertEqual(len(vista["datos"]["serie"]), 48)
            self.assertNotIn("mae_prueba", vista["datos"])
            self.assertNotIn("predicciones", vista["datos"])
            self.assertFalse(any(k["id"] == "mae" for k in vista["kpis"]))
            self.assertIsNone(vista["puntaje"])
            with self.assertRaises(ValueError):
                motor.resultado(estado)
        estado = self.aplicar(estado, "evaluar", "pronostico")
        self.assertEqual(len(motor.observacion(estado)["datos"]["serie"]), 60)
        self.assertEqual(len(motor.resultado(estado)["evaluacion_temporal"]), 12)
        with self.assertRaises(ValueError):
            self.aplicar(estado, "evaluar", "pronostico")

    def test_pronosticos_origen_fijo_no_usan_futuro_y_regresion_recupera_senal(self):
        estacional = [0, 8, 4, -3, -6, -2]
        serie = [40 + 0.65 * t + estacional[t % 6] for t in range(60)]
        for modelo in ("ultimo", "media4", "regresion"):
            pred = motor._predecir(serie, 36, 48, modelo)
            alterada = serie[:36] + [999] * 24
            self.assertEqual(pred, motor._predecir(alterada, 36, 48, modelo))
            if modelo == "regresion":
                for esperado, estimado in zip(serie[36:48], pred):
                    self.assertAlmostEqual(esperado, estimado, places=8)
            else:
                esperado = serie[35] if modelo == "ultimo" else mean(serie[32:36])
                self.assertEqual(pred, [esperado] * 12)
        self.assertNotEqual(
            motor._predecir(serie, 36, 48, "ultimo")[0],
            motor._predecir(serie, 48, 60, "ultimo")[0],
        )
        for modelo in ("falso", None):
            with self.assertRaises(ValueError):
                motor._predecir(serie, 36, 48, modelo)
        with self.assertRaises(ValueError):
            motor._predecir([1, 2, float("nan"), 4], 4, 8, "ultimo")
        with self.assertRaises(ValueError):
            motor._resolver([[1, 2], [2, 4]], [1, 2])
        with self.assertRaises(ValueError):
            motor._resolver([[1, 2]], [1])
        solucion = motor._resolver([[2, 1], [1, 3]], [5, 7])
        self.assertAlmostEqual(solucion[0], 1.6)
        self.assertAlmostEqual(solucion[1], 1.8)

    def test_ia_mae_seleccion_validacion_y_reajuste_cuarenta_y_ocho(self):
        estado = self.aplicar(
            motor.crear_estado("ia-pronostico", 99), "entrenar", "pronostico"
        )
        serie = estado["datos"]["serie"]
        for candidato in estado["datos"]["modelos"]:
            pred = motor._predecir(serie, 36, 48, candidato["id"])
            mae = mean(abs(y - p) for y, p in zip(serie[36:48], pred))
            self.assertAlmostEqual(candidato["mae_validacion_exacto"], mae)
        estado = self.aplicar(estado, "seleccionar", "pronostico")
        seleccionado = min(
            estado["datos"]["modelos"],
            key=lambda m: (m["mae_validacion_exacto"], m["id"]),
        )["id"]
        self.assertEqual(estado["datos"]["seleccionado"], seleccionado)
        estado = self.aplicar(estado, "evaluar", "pronostico")
        d = estado["datos"]
        pred = motor._predecir(serie, 48, 60, seleccionado)
        self.assertEqual(d["predicciones"], [round(p, 4) for p in pred])
        self.assertEqual(d["entrenamiento_final"], 48)
        self.assertAlmostEqual(
            d["mae_prueba_exacto"], mean(abs(y - p) for y, p in zip(serie[48:], pred))
        )
        self.assertEqual(d["mae_prueba"], round(d["mae_prueba_exacto"], 4))
        self.assertTrue(isfinite(motor.resultado(estado)["puntaje"]))

    def test_ia_rubrica_mae_referencia_perfecta_igual_mejor_y_peor(self):
        final = self.completar_ia()
        for propio, base, eficiencia in (
            (0, 0, 25),
            (1, 0, 0),
            (2, 2, 0),
            (1, 2, 12.5),
            (4, 2, 0),
        ):
            estado = deepcopy(final)
            estado["datos"]["mae_prueba_exacto"] = propio
            estado["datos"]["mae_referencia_exacto"] = base
            with self.subTest(propio=propio, base=base):
                informe = motor.resultado(estado)
                self.assertEqual(informe["componentes"]["eficiencia"], eficiencia)
                self.assertTrue(0 <= informe["puntaje"] <= 100)


if __name__ == "__main__":
    unittest.main()
