"""Coherencia docente y contratos públicos de las guías de distribución."""

import ast
import inspect
import json
import unittest
from urllib.parse import urlsplit

from apps.laboratorios.operacion.presentation import logistica_distribucion_guia as contenido
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import MATRIZ_ASIGNATURAS


class GuiaDistribucionTests(unittest.TestCase):
    def test_tres_fichas_completas_serializables_y_duracion_conciliada(self):
        self.assertEqual(set(contenido.CASOS), {"cd-normal", "cd-pico", "cd-falla"})
        for caso in contenido.CASOS:
            with self.subTest(caso=caso):
                ficha = contenido.guia(caso)
                self.assertEqual(ficha["caso"], caso)
                self.assertEqual(ficha["version_guia"], contenido.GUIA_VERSION)
                self.assertEqual(json.loads(json.dumps(ficha, allow_nan=False)), ficha)
                self.assertEqual(
                    sum(p["minutos"] for p in ficha["distribucion_tiempo"]),
                    ficha["duracion_minutos"],
                )
                self.assertEqual(len(ficha["objetivos"]), 5)
                self.assertEqual(
                    [p["orden"] for p in ficha["procedimiento"]], list(range(1, 9))
                )
                self.assertGreaterEqual(len(ficha["entregables"]), 6)
                self.assertGreaterEqual(len(ficha["preguntas_reflexion"]), 5)
                self.assertTrue(
                    all(o["criterio"] and o["evidencia"] for o in ficha["objetivos"])
                )
                self.assertTrue(
                    all(p["pasos"] and p["evidencia"] for p in ficha["procedimiento"])
                )

    def test_rechaza_casos_invalidos_sin_sustituir_por_normal(self):
        for caso in (None, True, 42, [], {}, "", "cd-inventado", "CD-NORMAL"):
            with self.subTest(caso=caso):
                self.assertRaises(ValueError, contenido.guia, caso)

    def test_no_comparte_mutaciones_entre_visitas_ni_variantes(self):
        primera = contenido.guia("cd-normal")
        esperada = contenido.guia("cd-normal")
        primera["etapas"][0]["nombre"] = "alterado"
        primera["rubrica_docente"]["criterios"][0]["puntos"] = 999
        primera["fuentes"].clear()
        primera["asignaturas"][0]["codigo"] = "inventado"
        primera["comparacion"]["igualar"].clear()
        self.assertEqual(contenido.guia("cd-normal"), esperada)
        self.assertEqual(contenido.guia("cd-pico")["etapas"], esperada["etapas"])

    def test_seis_etapas_y_control_parcial_sin_doble_conteo(self):
        ficha = contenido.guia()
        self.assertEqual(
            [e["id"] for e in ficha["etapas"]],
            ["recepcion", "control", "ubicacion", "picking", "embalaje", "despacho"],
        )
        for etapa in ficha["etapas"]:
            self.assertEqual(
                set(etapa),
                {
                    "id",
                    "nombre",
                    "entrada",
                    "operacion",
                    "salida",
                    "control",
                    "indicador",
                },
            )
            self.assertTrue(
                all(isinstance(v, str) and v.strip() for v in etapa.values())
            )
        self.assertIn("después de inspeccionar", ficha["etapas"][0]["operacion"])
        self.assertIn("rechazo parcial", ficha["etapas"][1]["operacion"])
        self.assertIn("FIFO por SKU", ficha["etapas"][3]["operacion"])
        self.assertIn("denominador", ficha["etapas"][5]["control"])
        self.assertIn("duplicaría", ficha["teoria"][0]["contenido"])

    def test_area_y_asignaturas_reutilizan_catalogo_existente(self):
        ficha = contenido.guia()
        self.assertEqual(ficha["area"]["codigo"], "LOG-ALMACEN")
        self.assertEqual(ficha["area"]["nombre"], AREAS["LOG-ALMACEN"]["nombre"])
        principales = []
        for asignatura in ficha["asignaturas"]:
            existente = MATRIZ_ASIGNATURAS[asignatura["codigo"]]
            self.assertEqual(asignatura["nombre"], existente["nombre"])
            if asignatura["relacion"] == "principal":
                principales.append(asignatura["codigo"])
                self.assertIn(ficha["area"]["codigo"], existente["areas"])
        self.assertEqual(principales, ["LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A"])

    def test_rubrica_docente_suma_cien_y_es_distinta_de_puntaje_automatico(self):
        rubrica = contenido.guia()["rubrica_docente"]
        self.assertEqual(rubrica["total"], 100)
        self.assertEqual(sum(c["puntos"] for c in rubrica["criterios"]), 100)
        self.assertEqual(len({c["id"] for c in rubrica["criterios"]}), 6)
        self.assertIn("distinta del puntaje automático", rubrica["nota"])
        self.assertIn("no se guarda como calificación oficial", rubrica["nota"])
        for criterio in rubrica["criterios"]:
            self.assertEqual([n["fraccion"] for n in criterio["niveles"]], [1, 0.5, 0])
            self.assertEqual(
                criterio["puntos"] * criterio["niveles"][0]["fraccion"],
                criterio["puntos"],
            )
            self.assertTrue(criterio["evidencia"])
            self.assertEqual(len({n["descriptor"] for n in criterio["niveles"]}), 3)

    def test_fuentes_primarias_resueltas_y_limites_explicitos(self):
        ficha = contenido.guia()
        fuentes = {f["id"]: f for f in ficha["fuentes"]}
        self.assertEqual(set(fuentes), {"gs1", "osha", "mit", "nist"})
        for fuente in fuentes.values():
            self.assertEqual(urlsplit(fuente["url"]).scheme, "https")
            self.assertIn(
                urlsplit(fuente["url"]).hostname,
                {"ref.gs1.org", "www.osha.gov", "ocw.mit.edu", "www.itl.nist.gov"},
            )
            self.assertRegex(fuente["consulta"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(fuente["alcance"])
        for teoria in ficha["teoria"]:
            self.assertLessEqual(set(teoria["fuentes"]), set(fuentes))
        self.assertGreaterEqual(len(ficha["seguridad_maqueta"]), 8)
        self.assertGreaterEqual(len(ficha["limites"]), 7)
        self.assertIn("normativa ecuatoriana", fuentes["osha"]["alcance"])
        self.assertIn("no afirma conformidad EPCIS", fuentes["gs1"]["alcance"])

    def test_comparacion_no_confunde_politicas_escenarios_o_versiones(self):
        ficha = contenido.guia()
        comparacion = ficha["comparacion"]
        self.assertEqual(
            set(comparacion["igualar"]),
            {
                "caso",
                "semilla",
                "version_motor",
                "version_caso",
                "version_dataset",
                "version_guia",
            },
        )
        self.assertIn("no iguala la carga", comparacion["entre_variantes"])
        self.assertIn(
            "sin atribuir causalidad exclusiva", comparacion["entre_variantes"]
        )
        self.assertTrue(
            any("puntos porcentuales" in c for c in comparacion["calculos"])
        )
        self.assertTrue(
            any("base es distinta de cero" in c for c in comparacion["calculos"])
        )
        self.assertIn("No mezclar resultados", comparacion["versiones"])
        self.assertEqual(
            len({contenido.guia(c)["hipotesis"]["factor"] for c in contenido.CASOS}), 3
        )

    def test_modulo_puro_sin_django_red_ni_base(self):
        arbol = ast.parse(inspect.getsource(contenido))
        imports = [n.module for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom)]
        imports += [
            a.name
            for n in ast.walk(arbol)
            if isinstance(n, ast.Import)
            for a in n.names
        ]
        self.assertEqual(imports, ["copy"])

    def test_diccionario_resuelve_campos_y_unidades_contra_motor_real(self):
        from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor

        def resolver(valor, ruta):
            if not ruta:
                return [valor]
            cabeza, *resto = ruta
            es_lista = cabeza.endswith("[]")
            clave = cabeza[:-2] if es_lista else cabeza
            if type(valor) is not dict or clave not in valor:
                return []
            contenido_campo = valor[clave]
            if es_lista:
                return [v for fila in contenido_campo for v in resolver(fila, resto)]
            return resolver(contenido_campo, resto)

        def tipo_valido(valor, tipo):
            if valor is None:
                return "nulo" in tipo
            if tipo.startswith("entero"):
                return type(valor) is int
            if tipo.startswith("numero"):
                return type(valor) in (int, float)
            if tipo.startswith("texto"):
                return type(valor) is str
            if tipo.startswith("booleano"):
                return type(valor) is bool
            if tipo.startswith("lista"):
                return type(valor) is list
            if tipo.startswith("objeto"):
                return type(valor) is dict
            return False

        esperadas = {
            "productos",
            "lotes",
            "ubicaciones",
            "pedidos",
            "recursos",
            "eventos",
            "balances",
            "resultados",
        }
        for caso in contenido.CASOS:
            with self.subTest(caso=caso):
                inicial = motor.observacion(motor.crear_estado(caso, 42))
                final = motor.crear_estado(caso, 42)
                for decision in motor.referencia(caso, 42)["decisiones"]:
                    final = motor.actuar(final, decision)
                final = motor.observacion(final)
                resultado = motor.resultado(final)
                diccionario = contenido.guia(caso)["diccionario_datos"]
                self.assertEqual(set(diccionario), esperadas)
                for nombre, tabla in diccionario.items():
                    muestras = (
                        [resultado]
                        if nombre == "resultados"
                        else [inicial["datos"][nombre], final["datos"][nombre]]
                    )
                    filas = [
                        m
                        for muestra in muestras
                        for m in (muestra if type(muestra) is list else [muestra])
                    ]
                    columnas_reales = {k for fila in filas for k in fila}
                    columnas_documentadas = {
                        c["campo"].split(".")[0].replace("[]", "")
                        for c in tabla["campos"]
                    }
                    self.assertEqual(columnas_reales, columnas_documentadas, nombre)
                    self.assertEqual(
                        len({c["campo"] for c in tabla["campos"]}),
                        len(tabla["campos"]),
                        nombre,
                    )
                    for campo in tabla["campos"]:
                        valores = [
                            v
                            for fila in filas
                            for v in resolver(fila, campo["campo"].split("."))
                        ]
                        self.assertTrue(valores, (nombre, campo["campo"]))
                        self.assertTrue(
                            all(tipo_valido(v, campo["tipo"]) for v in valores),
                            (nombre, campo["campo"], valores),
                        )
                        self.assertTrue(campo["unidad"] and campo["descripcion"])
                self.assertEqual(
                    [e["id"] for e in inicial["datos"]["etapas"]],
                    [e["id"] for e in contenido.guia(caso)["etapas"]],
                )
                self.assertEqual(
                    contenido.guia(caso)["area"]["codigo"], motor.AREA_CODIGO
                )
                self.assertEqual(set(contenido.CASOS), set(motor.CASOS))

    def test_documenta_visibilidad_calidad_y_puntaje_sin_fingir_resultados(self):
        from apps.laboratorios.operacion.presentation import logistica_distribucion_motor as motor

        ficha = contenido.guia("cd-falla")
        self.assertIn(
            "oculta defectuosas", ficha["diccionario_datos"]["lotes"]["visibilidad"]
        )
        self.assertIn(
            "Sólo al terminar", ficha["diccionario_datos"]["resultados"]["visibilidad"]
        )
        inicial = motor.datasets("cd-falla", 42)
        self.assertTrue(all("defectuosas" not in lote for lote in inicial["lotes"]))
        campos = {
            c["campo"]: c for c in ficha["diccionario_datos"]["resultados"]["campos"]
        }
        self.assertIn(
            "despachados / total", campos["componentes.eficiencia"]["descripcion"]
        )
        self.assertIn("no un óptimo probado", campos["referencia"]["descripcion"])
        self.assertIn(
            "misma semilla no iguala la carga", campos["semilla"]["descripcion"]
        )
