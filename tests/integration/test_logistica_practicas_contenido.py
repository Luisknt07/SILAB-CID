"""Verificaciones pedagógicas y matemáticas sin conexión a base de datos."""

import csv
import hashlib
import io
import json
from collections import Counter
from copy import deepcopy
from html.parser import HTMLParser
from unittest import TestCase
from urllib.parse import urlparse

from apps.laboratorios.operacion.management.laboratorios import logistica_practicas as practicas
from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, SLUG
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import MATRIZ_ASIGNATURAS


class Documento(HTMLParser):
    def __init__(self, contenido):
        super().__init__()
        self.etiquetas = []
        self.ids = []
        self.enlaces = []
        self.eventos = []
        self.feed(contenido)

    def handle_starttag(self, tag, attrs):
        self.etiquetas.append(tag)
        for clave, valor in attrs:
            if clave == "id":
                self.ids.append(valor)
            if clave == "href":
                self.enlaces.append(valor)
            if clave.lower().startswith("on"):
                self.eventos.append(clave)


class PracticasLogisticaContenidoTests(TestCase):
    def test_cubre_exactamente_seis_areas_y_veintitres_asignaturas_existentes(self):
        self.assertEqual(len(practicas.GUIAS), 12)
        self.assertEqual(
            Counter(x["area"] for x in practicas.GUIAS.values()),
            Counter({x: 2 for x in AREAS}),
        )
        cobertura = practicas.cobertura_asignaturas()
        self.assertEqual(len(cobertura), 23)
        self.assertEqual({x["codigo"] for x in cobertura}, set(MATRIZ_ASIGNATURAS))
        self.assertTrue(all(x["practicas"] for x in cobertura))
        for guia in practicas.GUIAS.values():
            self.assertTrue(set(guia["asignaturas"]) <= set(MATRIZ_ASIGNATURAS))

    def test_cada_guia_tiene_protocolo_caso_y_evaluacion_completos(self):
        for clave, guia in practicas.GUIAS.items():
            with self.subTest(clave=clave):
                self.assertEqual(guia["seccion"], "4.1")
                self.assertEqual(len(guia["objetivos"]), 3)
                self.assertEqual(len(guia["procedimiento"]), 6)
                self.assertEqual(len(guia["entregables"]), 4)
                self.assertGreaterEqual(len(guia["teoria"]), 3)
                self.assertGreaterEqual(len(guia["preguntas"]), 3)
                self.assertTrue(120 <= guia["duracion_minutos"] <= 180)
                self.assertTrue(set(guia["datasets"]) <= set(practicas.DATASETS))
                self.assertTrue(set(guia["fuentes"]) <= set(practicas.FUENTES))
                self.assertFalse(guia["autoriza_presencial"])
                self.assertEqual(guia["datos"], "sinteticos")
                self.assertEqual(sum(x[1] for x in guia["rubrica"]), 100)
                self.assertEqual([x[1] for x in guia["niveles"]], [1.0, 0.75, 0.5, 0.0])

    def test_dataset_csv_y_diccionario_conservan_filas_y_unidades(self):
        for clave, dataset in practicas.DATASETS.items():
            with self.subTest(clave=clave):
                filas = list(csv.reader(io.StringIO(practicas.dataset_csv(clave))))
                self.assertEqual(tuple(filas[0]), dataset["campos"])
                self.assertEqual(
                    filas[1:], [[str(x) for x in fila] for fila in dataset["filas"]]
                )
                self.assertTrue(
                    all(len(x) == len(dataset["campos"]) for x in dataset["filas"])
                )
                self.assertEqual(
                    {x["campo"] for x in dataset["diccionario"]}, set(dataset["campos"])
                )
                self.assertTrue(
                    all(
                        x["unidad"] and x["descripcion"] for x in dataset["diccionario"]
                    )
                )
                self.assertEqual(dataset["procedencia"], "sinteticos_upec")
                self.assertTrue(
                    all(
                        not str(x).startswith(("=", "+", "@", "\t"))
                        for fila in dataset["filas"]
                        for x in fila
                    )
                )

    def test_exportacion_determinista_tiene_hash_y_no_escribe_archivos(self):
        antes = deepcopy(practicas.DATASETS)
        recursos = practicas.recursos_datasets()
        self.assertEqual(len(recursos), 12)
        self.assertEqual(len({x["nombre"] for x in recursos}), 12)
        for recurso in recursos:
            self.assertEqual(
                recurso["contenido"],
                practicas.dataset_csv(recurso["clave"]).encode("utf-8"),
            )
            self.assertEqual(
                recurso["sha256"], hashlib.sha256(recurso["contenido"]).hexdigest()
            )
            self.assertEqual(recurso["seccion"], "4.4")
            self.assertEqual(recurso["mime"], "text/csv")
            self.assertNotIn(b"\r", recurso["contenido"])
        self.assertEqual(practicas.DATASETS, antes)

    def test_conteo_agregado_correcto_no_oculta_dos_sku_erroneos(self):
        control = practicas.controles_calculados(1)
        self.assertEqual(control["saldo_teorico"], 87)
        self.assertEqual(control["conteo"], 87)
        self.assertEqual(control["rechazado"], 3)
        errores = {k: v for k, v in control["diferencias"].items() if v}
        self.assertEqual(errores, {"SKU-B": -1, "SKU-E": 1})
        self.assertAlmostEqual(control["exactitud_registros_pct"], 100 * 4 / 6)

    def test_slotting_pondera_visitas_y_no_duplica_retorno(self):
        control = practicas.controles_calculados(2)
        self.assertEqual(control["recorrido_base_m"], 2352)
        self.assertEqual(control["recorrido_alternativa_m"], 1436)
        self.assertTrue(control["capacidad_factible"])
        self.assertAlmostEqual(control["reduccion_pct"], 100 * 916 / 2352)

    def test_pronostico_origen_fijo_y_reorden_usan_solo_entrenamiento(self):
        control = practicas.controles_calculados(3)
        self.assertEqual(
            control,
            {
                "persistencia": 24,
                "media4": 21,
                "mae_persistencia": 2.5,
                "mae_media4": 2,
                "punto_reorden_cajas": 48,
            },
        )
        self.assertGreater(control["punto_reorden_cajas"], 43)

    def test_reposicion_resta_pendientes_sin_recibir_transito(self):
        decisiones = practicas.controles_calculados(4)["decisiones"]
        self.assertEqual([x["posicion"] for x in decisiones], [16, 12, 20, 22])
        self.assertEqual([x["pedido"] for x in decisiones], [8, 12, 4, 2])

    def test_amplificacion_declara_constante_no_definido_y_alinea_series(self):
        self.assertIsNone(practicas.amplificacion([2, 4, 6], [5, 5, 5]))
        self.assertEqual(practicas.amplificacion([2, 4, 6], [1, 2, 3]), 4)
        with self.assertRaises(ValueError):
            practicas.amplificacion([1, 2], [1, 2, 3])
        with self.assertRaises(ValueError):
            practicas.amplificacion([1], [1])

    def test_planes_de_ruta_cubren_cinco_clientes_sin_sobrepasar_capacidad(self):
        control = practicas.controles_calculados(5)
        for nombre in ("base", "alternativa"):
            rutas = control[nombre]
            self.assertEqual(
                Counter(x for ruta in rutas for x in ruta["visitas"]),
                Counter({x: 1 for x in ("A", "B", "C", "E", "F")}),
            )
            self.assertEqual(sum(x["carga"] for x in rutas), 12)
            self.assertTrue(all(x["factible_capacidad"] for x in rutas))
            self.assertEqual(sum(x["puntuales"] for x in rutas), 5)
        self.assertEqual(control["base_km"], 26)
        self.assertEqual(control["alternativa_km"], 26)
        self.assertEqual(3 * control["base_km"] + 2 * 10, 98)
        self.assertEqual([x["retorno_min"] for x in control["base"]], [43, 34])
        self.assertEqual([x["retorno_min"] for x in control["alternativa"]], [26, 51])

    def test_contingencia_cambia_tiempo_no_km_y_alternativa_conserva_servicio(self):
        control = practicas.controles_calculados(6)
        self.assertEqual(control["base_km"], 26)
        self.assertEqual(control["alternativa_km"], 26)
        self.assertEqual(control["base_puntuales"], 4)
        self.assertEqual(control["alternativa_puntuales"], 5)
        cliente_c = control["base"][0]["servicios"][-1]
        self.assertEqual(cliente_c, {"nodo": "C", "inicio": 54, "puntual": False})
        self.assertEqual(cliente_c["inicio"] - 45, 9)
        self.assertEqual(control["base"][0]["retorno_min"], 73)

    def test_programacion_conserva_lote_y_evitar_solapamientos_en_unidades_y_estaciones(
        self,
    ):
        control = practicas.controles_calculados(7)
        for nombre in ("base", "alternativa"):
            eventos = control[nombre]["eventos"]
            self.assertEqual(len(eventos), 18)
            for unidad in range(1, 7):
                pasos = [x for x in eventos if x["unidad"] == unidad]
                self.assertEqual([x["estacion"] for x in pasos], [1, 2, 3])
                self.assertTrue(
                    all(b["inicio"] >= a["fin"] for a, b in zip(pasos, pasos[1:]))
                )
            for estacion in range(1, 4):
                cola = [x for x in eventos if x["estacion"] == estacion]
                self.assertTrue(
                    all(b["inicio"] >= a["fin"] for a, b in zip(cola, cola[1:]))
                )
        self.assertEqual(control["base"]["makespan_min"], 37)
        self.assertEqual(control["alternativa"]["makespan_min"], 30)
        self.assertEqual(control["base"]["capacidad_estable_unidades_h"], 12)
        self.assertEqual(control["alternativa"]["capacidad_estable_unidades_h"], 15)

    def test_recuperacion_conserva_destinos_y_excluye_reproceso_pendiente(self):
        control = practicas.controles_calculados(8)
        self.assertTrue(control["balance_correcto"])
        self.assertEqual(control["entrada"], 60)
        self.assertEqual(
            (control["reutilizable"], control["reproceso"], control["descarte"]),
            (36, 17, 7),
        )
        self.assertEqual(control["recuperacion_inmediata_pct"], 60)
        self.assertEqual(control["costo_inspeccion"] / control["entrada"], 0.5)

    def test_exp_aduanero_cruza_lineas_sin_sumar_magnitudes_distintas(self):
        control = practicas.controles_calculados(9)
        self.assertEqual(control["lineas_inconsistentes"], ["SKU-B", "SKU-C"])
        self.assertEqual(
            (control["cantidad_factura"], control["cantidad_empaque"]), (240, 238)
        )
        self.assertEqual(
            (control["peso_factura_kg"], control["peso_empaque_kg"]), (860, 865)
        )
        self.assertEqual(control["valor_factura_um"], 3600)

    def test_cola_fifo_respeta_arribo_y_recurso_y_compromiso_de_fin(self):
        control = practicas.controles_calculados(10)
        for nombre in ("base", "alternativa"):
            eventos = control[nombre]["eventos"]
            self.assertEqual(len(eventos), 4)
            self.assertTrue(
                all(b["inicio"] >= a["fin"] for a, b in zip(eventos, eventos[1:]))
            )
            self.assertTrue(all(x["espera"] >= 0 for x in eventos))
        self.assertEqual(control["base"]["espera_media_min"], 4.5)
        self.assertEqual(control["base"]["permanencia_media_min"], 9.5)
        self.assertEqual(control["base"]["puntuales"], 2)
        self.assertEqual(control["alternativa"]["espera_media_min"], 1.5)
        self.assertEqual(control["alternativa"]["permanencia_media_min"], 4.5)
        self.assertEqual(control["alternativa"]["puntuales"], 4)

    def test_trazabilidad_distingue_duplicado_balance_y_orden_temporal(self):
        control = practicas.controles_calculados(11)
        self.assertEqual(control["filas"], 6)
        self.assertEqual(control["eventos_unicos"], 5)
        self.assertEqual(control["duplicados"], ["EV-02"])
        self.assertEqual(
            control["errores"], ["L-01:sobre_despacho", "L-02:orden_temporal"]
        )

    def test_ia_no_promete_mejora_en_prueba_si_gana_validacion(self):
        control = practicas.controles_calculados(12)
        self.assertEqual(control["validacion"], {"persistencia": 2.5, "candidato": 1})
        self.assertEqual(control["prueba"], {"persistencia": 2, "candidato": 2})

    def test_generacion_tiene_anclas_unicas_y_no_scripts_ni_dependencias_remotas(self):
        for clave in practicas.GUIAS:
            with self.subTest(clave=clave):
                html = practicas.documento_html(clave)
                documento = Documento(html)
                self.assertEqual(len(documento.ids), len(set(documento.ids)))
                self.assertEqual(documento.eventos, [])
                self.assertFalse(
                    {"script", "iframe", "form", "img", "video", "audio"}
                    & set(documento.etiquetas)
                )
                for enlace in documento.enlaces:
                    if enlace.startswith("#"):
                        self.assertIn(enlace[1:], documento.ids)
                    elif enlace.startswith("/"):
                        self.assertTrue(
                            enlace.startswith("/laboratorio/" + SLUG + "/logistica/")
                        )
                    else:
                        self.assertEqual(urlparse(enlace).scheme, "https")
                self.assertIn("Content-Security-Policy", html)
                self.assertIn("Caso docente con datos sintéticos", html)
                self.assertIn("Rúbrica docente de referencia: 100 puntos", html)
                self.assertIn('scope="col"', html)
                for dataset in practicas.GUIAS[clave]["datasets"]:
                    self.assertIn(practicas.checksum_dataset(dataset), html)

    def test_editorial_html_escapa_titulos_y_textos(self):
        guia = deepcopy(practicas.GUIAS["practica-01"])
        guia["titulo"] = '<script>alert("x")</script>'
        guia["contexto"] = '<img src=x onerror="alert(1)">'
        html = practicas.documento_html("practica-01", guia)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(Documento(html).eventos, [])

    def test_lecturas_no_mutan_datasets_guias_ni_controles(self):
        antes = deepcopy((practicas.DATASETS, practicas.GUIAS))
        for clave, guia in practicas.GUIAS.items():
            resultado = practicas.controles_calculados(guia["numero"])
            json.dumps(resultado)
            practicas.documento_html(clave)
            practicas.controles_calculados(guia["numero"])
        self.assertEqual((practicas.DATASETS, practicas.GUIAS), antes)
        cobertura = practicas.cobertura_asignaturas()
        cobertura[0]["practicas"].clear()
        self.assertTrue(practicas.cobertura_asignaturas()[0]["practicas"])

    def test_control_rechaza_numeros_y_tipos_fuera_de_catalogo(self):
        for numero in (0, 13, -1, True, "1", None, 1.0):
            with self.subTest(numero=numero), self.assertRaises(ValueError):
                practicas.controles_calculados(numero)
