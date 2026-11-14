"""Centro de distribución: conservación, protocolos y comparaciones reproducibles."""

from copy import deepcopy
import json
import unittest

from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor


class DistribucionMotorTests(unittest.TestCase):
    def aplicar(self, estado, accion, objeto):
        return motor.actuar(estado, {"accion": accion, "objeto": objeto})

    def recepcionar(self, estado):
        for inicial in estado["datos"]["lotes"]:
            identificador = inicial["id"]
            estado = self.aplicar(estado, "inspeccionar", identificador)
            lote = next(
                fila for fila in estado["datos"]["lotes"] if fila["id"] == identificador
            )
            if lote["defectuosas"]:
                estado = self.aplicar(estado, "rechazar", identificador)
            estado = self.aplicar(estado, "recibir", identificador)
        return estado

    def completar(self, caso="cd-normal", semilla=42, espera=0):
        referencia = motor.referencia(caso, semilla)
        estado = motor.crear_estado(caso, semilla)
        for _ in range(espera):
            estado = self.aplicar(estado, "esperar", "control")
        for decision in referencia["decisiones"]:
            estado = motor.actuar(estado, decision)
        return estado

    def test_catalogo_identificadores_versiones_y_copia(self):
        catalogo = motor.catalogo()
        self.assertEqual(
            {c["id"] for c in catalogo}, {"cd-normal", "cd-pico", "cd-falla"}
        )
        for c in catalogo:
            self.assertEqual(c["area_codigo"], "LOG-ALMACEN")
            self.assertEqual(c["escena"], "almacen")
            self.assertEqual(c["version"], "1.0.0")
            self.assertEqual(c["familia"], "centro-distribucion")
            self.assertEqual(len(c["acciones"]), 14)
        catalogo[0]["reglas"].clear()
        self.assertTrue(motor.catalogo()[0]["reglas"])

    def test_datasets_comparten_base_y_distinguen_variantes(self):
        normal = motor.datasets("cd-normal", 42)
        pico = motor.datasets("cd-pico", 42)
        falla = motor.datasets("cd-falla", 42)
        for clave in ("productos", "lotes", "ubicaciones"):
            self.assertEqual(normal[clave], pico[clave])
            self.assertEqual(normal[clave], falla[clave])
        self.assertEqual(normal["pedidos"], falla["pedidos"])
        self.assertEqual(normal["recursos"], pico["recursos"])
        self.assertEqual(len(normal["pedidos"]), 3)
        self.assertEqual(len(pico["pedidos"]), 4)
        self.assertEqual(falla["recursos"][0]["fallo_en"], 30)
        self.assertTrue(all("defectuosas" not in fila for fila in normal["lotes"]))
        self.assertEqual(normal["version_dataset"], motor.DATASET_VERSION)
        normal["productos"].clear()
        self.assertEqual(len(motor.datasets()["productos"]), 3)

    def test_semilla_determina_lote_y_defectos_ocultos(self):
        self.assertEqual(
            motor.crear_estado("cd-normal", 123), motor.crear_estado("cd-normal", 123)
        )
        firmas = set()
        for semilla in range(12):
            estado = motor.crear_estado("cd-normal", semilla)
            firma = tuple(fila["defectuosas"] for fila in estado["datos"]["lotes"])
            self.assertIn(sum(firma), (1, 2))
            self.assertEqual(sum(bool(v) for v in firma), 1)
            firmas.add(firma)
        self.assertGreater(len(firmas), 3)

    def test_referencia_completa_todas_variantes_y_semillas(self):
        for caso in motor.CASOS:
            for semilla in (0, 1, 42, 9876, 2147483647):
                with self.subTest(caso=caso, semilla=semilla):
                    ref = motor.referencia(caso, semilla)
                    self.assertLess(len(ref["decisiones"]), motor.MAX_DECISIONES)
                    self.assertEqual(ref["errores"], 0)
                    self.assertEqual(ref["otif"], 100)
                    estado = motor.crear_estado(caso, semilla)
                    for decision in ref["decisiones"]:
                        estado = motor.actuar(estado, decision)
                        self.assertTrue(motor.validar_estado(estado))
                        for balance in estado["datos"]["balances"]:
                            self.assertEqual(balance["diferencia"], 0)
                        for u in estado["datos"]["ubicaciones"]:
                            self.assertLessEqual(u["ocupadas"], u["capacidad"])
                    self.assertTrue(estado["terminada"])
                    resultado = motor.resultado(estado)
                    self.assertEqual(resultado["puntaje"], 100)
                    self.assertEqual(resultado["pendientes"], 0)
                    self.assertEqual(resultado["metricas"]["diferencia_balance"], 0)
                    self.assertEqual(resultado["metricas"]["minutos"], ref["minutos"])

    def test_tiempos_y_recorridos_referencia_publicados(self):
        esperados = {
            "cd-normal": (118, 544, 3),
            "cd-pico": (139, 656, 4),
            "cd-falla": (132, 544, 3),
        }
        for caso, (minutos, distancia, pedidos) in esperados.items():
            ref = motor.referencia(caso, 42)
            self.assertEqual(
                (ref["minutos"], ref["distancia_m"], ref["completados"]),
                (minutos, distancia, pedidos),
            )

    def test_inspeccion_revela_solo_lote_consultado(self):
        estado = motor.crear_estado()
        self.assertTrue(
            all(
                "defectuosas" not in fila
                for fila in motor.observacion(estado)["datos"]["lotes"]
            )
        )
        identificador = estado["datos"]["lotes"][0]["id"]
        estado = self.aplicar(estado, "inspeccionar", identificador)
        vista = motor.observacion(estado)
        self.assertIn("defectuosas", vista["datos"]["lotes"][0])
        self.assertTrue(
            all("defectuosas" not in fila for fila in vista["datos"]["lotes"][1:])
        )
        vista["datos"]["lotes"][0]["saldo"] = 999
        self.assertEqual(estado["datos"]["lotes"][0]["saldo"], 0)

    def test_rechazo_parcial_precede_recepcion_y_conserva_cajas(self):
        estado = motor.crear_estado()
        lote = next(fila for fila in estado["datos"]["lotes"] if fila["defectuosas"])
        identificador, defectos, cantidad = (
            lote["id"],
            lote["defectuosas"],
            lote["cantidad"],
        )
        estado = self.aplicar(estado, "inspeccionar", identificador)
        estado = self.aplicar(estado, "recibir", identificador)
        fila = next(
            fila for fila in estado["datos"]["lotes"] if fila["id"] == identificador
        )
        self.assertEqual(fila["saldo"], 0)
        self.assertEqual(estado["errores"], 1)
        self.assertEqual(estado["minutos"], 4)
        estado = self.aplicar(estado, "rechazar", identificador)
        estado = self.aplicar(estado, "recibir", identificador)
        fila = next(
            fila for fila in estado["datos"]["lotes"] if fila["id"] == identificador
        )
        self.assertEqual(fila["rechazadas"], defectos)
        self.assertEqual(fila["recibidas"], cantidad - defectos)
        self.assertEqual(fila["saldo"], cantidad - defectos)
        self.assertTrue(all(b["diferencia"] == 0 for b in estado["datos"]["balances"]))

    def test_picking_requiere_recepcion_completa(self):
        estado = motor.crear_estado()
        despues = self.aplicar(estado, "preparar-a", "pedido-1")
        self.assertEqual(despues["datos"]["lotes"], estado["datos"]["lotes"])
        self.assertEqual(despues["datos"]["pedidos"], estado["datos"]["pedidos"])
        self.assertEqual(despues["errores"], 1)
        self.assertEqual(despues["minutos"], 2)

    def test_fifo_impide_saltar_lote_antiguo_no_ubicado(self):
        estado = self.recepcionar(motor.crear_estado())
        estado = self.aplicar(estado, "ubicar-a", "lote-a-2")
        despues = self.aplicar(estado, "preparar-a", "pedido-1")
        self.assertEqual(despues["errores"], 1)
        self.assertEqual(despues["datos"]["pedidos"][0]["lineas"][0]["preparadas"], 0)
        despues = self.aplicar(despues, "ubicar-a", "lote-a-1")
        despues = self.aplicar(despues, "preparar-a", "pedido-1")
        self.assertEqual(
            despues["datos"]["pedidos"][0]["lineas"][0]["lotes"], ["lote-a-1"]
        )

    def test_capacidad_lote_completo_y_error_no_mueve_inventario(self):
        estado = self.recepcionar(motor.crear_estado("cd-normal", 42))
        estado = self.aplicar(estado, "ubicar-a", "lote-a-1")
        estado = self.aplicar(estado, "ubicar-a", "lote-a-2")
        self.assertEqual(estado["datos"]["ubicaciones"][0]["ocupadas"], 12)
        despues = self.aplicar(estado, "ubicar-a", "lote-b-1")
        self.assertEqual(despues["datos"]["lotes"], estado["datos"]["lotes"])
        self.assertEqual(
            despues["datos"]["ubicaciones"], estado["datos"]["ubicaciones"]
        )
        self.assertEqual(despues["errores"], estado["errores"] + 1)
        despues = self.aplicar(despues, "ubicar-b", "lote-b-1")
        self.assertIsNotNone(despues["datos"]["lotes"][2]["ubicacion"])

    def test_abc_es_preferencia_y_reduce_tiempo_por_caja(self):
        base = self.recepcionar(motor.crear_estado("cd-normal", 42))
        cercano = self.aplicar(base, "ubicar-b", "lote-b-1")
        otro = self.aplicar(base, "ubicar-c", "lote-b-1")
        correcto = self.aplicar(cercano, "preparar-b", "pedido-1")
        incorrecto = self.aplicar(otro, "preparar-b", "pedido-1")
        self.assertEqual(correcto["minutos"] - cercano["minutos"], 2)
        self.assertEqual(incorrecto["minutos"] - otro["minutos"], 3)
        self.assertEqual(incorrecto["errores"], 0)

    def test_no_embala_ni_despacha_pedido_incompleto(self):
        estado = motor.crear_estado()
        despues = self.aplicar(estado, "embalar", "pedido-1")
        self.assertFalse(despues["datos"]["pedidos"][0]["embalado"])
        self.assertEqual(despues["errores"], 1)
        with self.assertRaises(ValueError):
            self.aplicar(estado, "despachar", "pedido-1")

    def test_falla_programada_y_reparacion_con_coste(self):
        estado = self.recepcionar(motor.crear_estado("cd-falla", 42))
        estado = self.aplicar(estado, "ubicar-a", "lote-a-1")
        estado = self.aplicar(estado, "ubicar-a", "lote-a-2")
        self.assertEqual(estado["minutos"], 33)
        self.assertEqual(estado["datos"]["recursos"][0]["estado"], "averiado")
        self.assertEqual(
            next(
                e["minuto"] for e in estado["datos"]["eventos"] if e["tipo"] == "falla"
            ),
            30,
        )
        bloqueado = self.aplicar(estado, "ubicar-b", "lote-b-1")
        self.assertEqual(bloqueado["datos"]["lotes"], estado["datos"]["lotes"])
        reparado = self.aplicar(estado, "reparar", "montacargas")
        self.assertEqual(reparado["minutos"], 47)
        self.assertEqual(reparado["datos"]["recursos"][0]["estado"], "operativo")
        self.assertTrue(reparado["datos"]["recursos"][0]["reparado"])
        self.assertEqual(reparado["datos"]["eventos"][-1]["tipo"], "reparacion")
        self.assertEqual(reparado["datos"]["eventos"][-1]["minuto"], 47)

    def test_recuperacion_natural_no_repara_ni_mueve_stock(self):
        estado = motor.crear_estado("cd-falla", 42)
        for _ in range(6):
            estado = self.aplicar(estado, "esperar", "control")
        self.assertEqual(estado["minutos"], 30)
        self.assertEqual(estado["datos"]["recursos"][0]["estado"], "averiado")
        lotes = deepcopy(estado["datos"]["lotes"])
        for _ in range(6):
            estado = self.aplicar(estado, "esperar", "control")
        self.assertEqual(estado["datos"]["recursos"][0]["estado"], "operativo")
        self.assertFalse(estado["datos"]["recursos"][0]["reparado"])
        self.assertEqual(estado["datos"]["lotes"], lotes)
        self.assertEqual(
            [e["tipo"] for e in estado["datos"]["eventos"]], ["falla", "recuperacion"]
        )
        self.assertEqual([e["minuto"] for e in estado["datos"]["eventos"]], [30, 60])

    def test_otif_contabiliza_compromisos_no_solo_despachados(self):
        estado = self.completar(espera=30)
        resultado = motor.resultado(estado)
        self.assertEqual(resultado["metricas"]["otif"], 0)
        self.assertEqual(resultado["metricas"]["completados"], 3)
        self.assertEqual(resultado["componentes"]["cumplimiento"], 0)
        self.assertLess(resultado["puntaje"], 40)
        self.assertTrue(all(not p["otif"] for p in resultado["pedidos"]))

    def test_cierre_anticipado_deja_faltantes_y_no_premia_velocidad(self):
        estado = self.aplicar(motor.crear_estado(), "cerrar", "control")
        resultado = motor.resultado(estado)
        self.assertEqual(resultado["pendientes"], 3)
        self.assertEqual(resultado["motivo_cierre"], "cierre anticipado")
        self.assertEqual(resultado["componentes"]["cumplimiento"], 0)
        self.assertEqual(resultado["componentes"]["eficiencia"], 0)
        self.assertEqual(resultado["puntaje"], 15)
        self.assertTrue(all(p["despachado_en"] is None for p in resultado["pedidos"]))

    def test_limite_de_240_decisiones_cierra_con_series_acotadas(self):
        estado = motor.crear_estado("cd-falla", 42)
        for _ in range(motor.MAX_DECISIONES):
            estado = self.aplicar(estado, "esperar", "control")
        self.assertTrue(estado["terminada"])
        self.assertEqual(estado["motivo_cierre"], "límite de decisiones")
        self.assertEqual(estado["minutos"], 1200)
        self.assertEqual(len(estado["historial"]), 240)
        self.assertEqual(len(estado["datos"]["eventos"]), 2)
        self.assertTrue(all(len(s["puntos"]) == 241 for s in estado["series"]))
        self.assertEqual(motor.resultado(estado)["pendientes"], 3)
        with self.assertRaises(ValueError):
            self.aplicar(estado, "esperar", "control")

    def test_replay_decisiones_historial_reproduce_estado_y_resultado(self):
        original = self.completar("cd-falla", 9876)
        repetida = motor.crear_estado("cd-falla", 9876)
        for fila in original["historial"]:
            repetida = self.aplicar(repetida, fila["accion"], fila["objeto"])
        self.assertEqual(repetida, original)
        self.assertEqual(motor.resultado(repetida), motor.resultado(original))
        eventos = original["datos"]["eventos"]
        self.assertEqual(
            [e["minuto"] for e in eventos], sorted(e["minuto"] for e in eventos)
        )
        self.assertTrue(all(e["minuto"] <= original["minutos"] for e in eventos))

    def test_entradas_no_mutables_ni_objetos_aliasados(self):
        estado = motor.crear_estado()
        copia = deepcopy(estado)
        decision = {"accion": "inspeccionar", "objeto": "lote-a-1"}
        despues = motor.actuar(estado, decision)
        self.assertEqual(estado, copia)
        self.assertEqual(decision, {"accion": "inspeccionar", "objeto": "lote-a-1"})
        despues["datos"]["productos"][0]["nombre"] = "otro"
        self.assertEqual(estado["datos"]["productos"][0]["nombre"], "Sensor didáctico")

    def test_entradas_invalidas_y_versiones_no_interpretadas(self):
        for caso, semilla in [
            (None, 42),
            ("otro", 42),
            (True, 42),
            ("cd-normal", True),
            ("cd-normal", -1),
            ("cd-normal", 2**31),
            ("cd-normal", 42.0),
        ]:
            with (
                self.subTest(caso=caso, semilla=semilla),
                self.assertRaises(ValueError),
            ):
                motor.crear_estado(caso, semilla)
        estado = motor.crear_estado()
        for decision in [
            None,
            [],
            {},
            {"accion": "esperar", "objeto": "control", "puntaje": 100},
            {"accion": True, "objeto": "control"},
            {"accion": "esperar", "objeto": "otro"},
            {"accion": "despachar", "objeto": "control"},
        ]:
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                motor.actuar(estado, decision)
        estado["version_motor"] = "0.9.0"
        with self.assertRaises(ValueError):
            motor.observacion(estado)

    def test_estado_alterado_saldos_capacidad_trazas_y_agregados(self):
        base = self.recepcionar(motor.crear_estado())
        cambios = [
            lambda e: e["datos"]["lotes"][0].update(saldo=999),
            lambda e: e["datos"]["ubicaciones"][0].update(capacidad=99),
            lambda e: e["datos"]["pedidos"][0]["lineas"][0].update(
                preparadas=1, lotes=["lote-a-1"]
            ),
            lambda e: e["datos"]["resumen"].update(pedidos_otif=3),
            lambda e: e["datos"]["balances"][0].update(diferencia=1),
            lambda e: e["kpis"][0].update(valor=100),
            lambda e: e.update(terminada=True),
            lambda e: e.update(minutos=float("nan")),
            lambda e: e["series"][0]["puntos"][0].update(valor=float("inf")),
        ]
        for cambiar in cambios:
            estado = deepcopy(base)
            cambiar(estado)
            with self.assertRaises(ValueError):
                motor.validar_estado(estado)

    def test_cierre_automatico_exige_ubicar_stock_restante(self):
        referencia = motor.referencia("cd-normal", 42)
        estado = motor.crear_estado("cd-normal", 42)
        for decision in referencia["decisiones"]:
            if decision == {"accion": "ubicar-c", "objeto": "lote-c-2"}:
                continue
            estado = motor.actuar(estado, decision)
        self.assertFalse(estado["terminada"])
        self.assertEqual(estado["datos"]["resumen"]["completados"], 3)
        estado = self.aplicar(estado, "ubicar-c", "lote-c-2")
        self.assertTrue(estado["terminada"])
        self.assertEqual(estado["motivo_cierre"], "objetivos completados")
        self.assertTrue(
            all(etapa["estado"] == "completa" for etapa in estado["datos"]["etapas"])
        )

    def test_disponibilidad_recurso_no_se_puede_falsificar(self):
        estado = motor.crear_estado("cd-falla", 42)
        for _ in range(6):
            estado = self.aplicar(estado, "esperar", "control")
        for clave, valor in [
            ("estado", "operativo"),
            ("fallo_activado", False),
            ("reparado", True),
            ("recuperacion_en", 90),
        ]:
            falso = deepcopy(estado)
            falso["datos"]["recursos"][0][clave] = valor
            with self.subTest(clave=clave), self.assertRaises(ValueError):
                motor.validar_estado(falso)

    def test_resultados_requieren_cierre_y_son_json_finito(self):
        with self.assertRaises(ValueError):
            motor.resultado(motor.crear_estado())
        estado = self.completar()
        resultado = motor.resultado(estado)
        json.dumps(resultado, allow_nan=False)
        self.assertEqual(
            {c["id"] for c in resultado["criterios"]},
            {"cumplimiento", "eficiencia", "precision"},
        )
        self.assertEqual(sum(c["peso"] for c in resultado["criterios"]), 100)
        self.assertEqual(resultado["puntaje"], sum(resultado["componentes"].values()))
        resultado["balances"].clear()
        self.assertEqual(len(estado["datos"]["balances"]), 3)

    def test_objetos_acciones_y_metricas_tienen_identificadores_estables(self):
        estado = motor.crear_estado()
        objetos = estado["objetos"]
        self.assertEqual(len({o["id"] for o in objetos}), len(objetos))
        self.assertLess(len(objetos), 32)
        declaradas = {a["id"] for a in motor.catalogo()[0]["acciones"]}
        self.assertTrue(all(set(o["acciones"]) <= declaradas for o in objetos))
        self.assertEqual(
            {e["id"] for e in estado["datos"]["etapas"]},
            {"recepcion", "control", "ubicacion", "picking", "embalaje", "despacho"},
        )
        final = self.completar()
        resultado = motor.resultado(final)
        for identificador in (
            "otif",
            "minutos",
            "errores",
            "distancia_m",
            "completados",
            "diferencia_balance",
        ):
            self.assertIn(identificador, resultado["metricas"])
            kpi = next(k for k in final["kpis"] if k["id"] == identificador)
            self.assertEqual(kpi["valor"], resultado["metricas"][identificador])
        for serie in final["series"]:
            kpi = next(k for k in final["kpis"] if k["id"] == serie["id"])
            self.assertEqual(serie["puntos"][-1]["valor"], kpi["valor"])

    def test_historial_malformado_rechaza_siempre_con_valueerror(self):
        base = self.aplicar(motor.crear_estado(), "inspeccionar", "lote-a-1")
        variantes = [None, 42, [], {}, {**base["historial"][0], "extra": True}]
        for campo, valor in [
            ("accion", []),
            ("objeto", {}),
            ("mensaje", None),
            ("paso", True),
            ("efecto", False),
            ("minutos", True),
        ]:
            variantes.append({**base["historial"][0], campo: valor})
        for fila in variantes:
            falso = deepcopy(base)
            falso["historial"][0] = fila
            with self.subTest(fila=fila), self.assertRaises(ValueError):
                motor.validar_estado(falso)
        falso = deepcopy(base)
        falso["historial"][0] = 42
        falso.update(terminada=True, motivo_cierre="cierre anticipado")
        with self.assertRaises(ValueError):
            motor.validar_estado(falso)

    def test_historial_exige_accion_objeto_tiempos_y_errores_coherentes(self):
        base = self.aplicar(motor.crear_estado(), "inspeccionar", "lote-a-1")
        cambios = [
            {"accion": "despachar"},
            {"objeto": "otro"},
            {"minutos": -9},
            {"efecto": 1, "minutos": 1},
            {"paso": 2},
            {"accion": "cerrar", "objeto": "control", "efecto": 0, "minutos": 0},
        ]
        for cambio in cambios:
            falso = deepcopy(base)
            falso["historial"][0].update(cambio)
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                motor.validar_estado(falso)
        falso = deepcopy(base)
        falso["errores"] = 1
        motor._actualizar(falso)
        with self.assertRaises(ValueError):
            motor.validar_estado(falso)

    def test_eventos_exigen_contrato_y_correspondencia_con_decisiones(self):
        base = self.aplicar(motor.crear_estado(), "inspeccionar", "lote-a-1")
        variantes = [None, 42, [], {}, {**base["datos"]["eventos"][0], "extra": 1}]
        for campo, valor in [
            ("id", "evento-2"),
            ("tipo", "despacho"),
            ("objeto", "pedido-3"),
            ("minuto", -1),
            ("minuto", True),
            ("minuto", 1),
            ("descripcion", ""),
            ("descripcion", []),
        ]:
            variantes.append({**base["datos"]["eventos"][0], campo: valor})
        for evento in variantes:
            falso = deepcopy(base)
            falso["datos"]["eventos"][0] = evento
            with self.subTest(evento=evento), self.assertRaises(ValueError):
                motor.validar_estado(falso)
        for eventos in [[], base["datos"]["eventos"] * 2]:
            falso = deepcopy(base)
            falso["datos"]["eventos"] = eventos
            with self.assertRaises(ValueError):
                motor.validar_estado(falso)

    def test_series_no_admiten_ausencias_duplicados_o_puntos_fuera_de_secuencia(self):
        base = self.aplicar(motor.crear_estado(), "inspeccionar", "lote-a-1")
        cambios = [
            lambda e: e.update(series=[]),
            lambda e: e["series"].__setitem__(1, deepcopy(e["series"][0])),
            lambda e: e["series"][0].update(id="otro"),
            lambda e: e["series"][0].update(titulo="otro"),
            lambda e: e["series"][0].update(unidad="otro"),
            lambda e: e["series"][0]["puntos"][0].update(valor=50),
            lambda e: e["series"][0]["puntos"][-1].update(valor=9999),
            lambda e: e["series"][0]["puntos"][-1].update(paso=0),
            lambda e: e["series"][0]["puntos"][-1].update(paso=True),
            lambda e: e["series"][0]["puntos"][-1].update(valor=True),
            lambda e: e["series"][0]["puntos"].__setitem__(0, 42),
        ]
        for cambiar in cambios:
            falso = deepcopy(base)
            cambiar(falso)
            with self.assertRaises(ValueError):
                motor.validar_estado(falso)

    def test_reparacion_tardia_conserva_una_unica_causa_de_recuperacion(self):
        estado = motor.crear_estado("cd-falla", 42)
        for _ in range(11):
            estado = self.aplicar(estado, "esperar", "control")
        estado = self.aplicar(estado, "reparar", "montacargas")
        self.assertEqual(estado["minutos"], 69)
        self.assertEqual(
            [(fila["tipo"], fila["minuto"]) for fila in estado["datos"]["eventos"]],
            [("falla", 30), ("reparacion", 69)],
        )
        self.assertTrue(motor.validar_estado(estado))
        replay = motor.crear_estado("cd-falla", 42)
        for fila in estado["historial"]:
            replay = self.aplicar(replay, fila["accion"], fila["objeto"])
        self.assertEqual(replay, estado)

    def test_intento_invalido_que_cruza_averia_conserva_evento_y_reloj(self):
        estado = motor.crear_estado("cd-falla", 42)
        danado = next(
            fila["id"] for fila in estado["datos"]["lotes"] if fila["defectuosas"]
        )
        for _ in range(5):
            estado = self.aplicar(estado, "esperar", "control")
        estado = self.aplicar(estado, "inspeccionar", danado)
        estado = self.aplicar(estado, "recibir", danado)
        estado = self.aplicar(estado, "recibir", danado)
        self.assertEqual(estado["minutos"], 31)
        self.assertEqual(estado["errores"], 2)
        self.assertEqual(
            [(fila["tipo"], fila["minuto"]) for fila in estado["datos"]["eventos"]],
            [("inspeccion", 27), ("falla", 30)],
        )
        self.assertTrue(motor.validar_estado(estado))

    def test_campos_compuestos_malformados_no_producen_typeerror(self):
        base = self.completar()
        cambios = [
            lambda e: e["datos"]["pedidos"][0]["lineas"][0]["lotes"].__setitem__(0, []),
            lambda e: e["datos"]["recursos"][0].update(estado=[]),
            lambda e: e.update(motivo_cierre=[]),
        ]
        for cambiar in cambios:
            falso = deepcopy(base)
            cambiar(falso)
            with self.assertRaises(ValueError):
                motor.validar_estado(falso)
