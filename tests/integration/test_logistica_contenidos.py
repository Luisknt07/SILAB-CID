"""Contrato de publicación, cobertura y seguridad del contenido docente logístico."""

import ast
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import unittest

from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO
from apps.laboratorios.operacion.management.laboratorios import logistica_contenidos
from apps.laboratorios.operacion.management.laboratorios.logistica_contenidos import ALCANCE, FECHA_CONTENIDO, GUIAS, SECCIONES_CUBIERTAS, VERSION
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import FUENTES, documento_html


class DocumentoInspeccionado(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.etiquetas = []
        self.enlaces = []
        self.atributos_activos = []

    def handle_starttag(self, tag, attrs):
        self.etiquetas.append(tag)
        for nombre, valor in attrs:
            if nombre.lower().startswith("on"):
                self.atributos_activos.append(nombre)
            if tag == "a" and nombre == "href":
                self.enlaces.append(valor)


class ContenidosLogisticaTests(unittest.TestCase):
    def test_cubre_las_diecinueve_secciones_que_completa_este_paquete(self):
        esperadas = {
            "1.2",
            "1.5",
            "1.6",
            "2.2",
            "2.4",
            "3.1",
            "3.2",
            "3.3",
            "5.1",
            "5.2",
            "5.3",
            "5.4",
            "5.5",
            "5.6",
            "5.7",
            "6.1",
            "6.2",
            "6.3",
            "6.4",
        }
        self.assertEqual(SECCIONES_CUBIERTAS, esperadas)
        self.assertTrue(SECCIONES_CUBIERTAS.issubset(MAPA_LABORATORIO.secciones))
        # Cursos, guías académicas y simuladores tienen sus propios paquetes.
        self.assertTrue(SECCIONES_CUBIERTAS.isdisjoint({"4.1", "4.3", "4.4"}))

    def test_complemento_editorial_cubre_el_mapa_completo_sin_renumerarlo(self):
        existentes = {"1.1", "1.3", "1.4", "2.1", "2.3", "4.1", "4.2", "4.3", "4.4"}
        self.assertEqual(
            SECCIONES_CUBIERTAS | existentes, set(MAPA_LABORATORIO.secciones)
        )
        self.assertEqual(len(MAPA_LABORATORIO.secciones), 28)

    def test_recursos_tienen_identidad_y_contrato_de_publicacion(self):
        self.assertEqual(len(GUIAS), 19)
        self.assertEqual(len({guia["titulo"] for guia in GUIAS.values()}), len(GUIAS))
        for clave, guia in GUIAS.items():
            with self.subTest(clave=clave):
                self.assertRegex(clave, r"^[a-z][a-z0-9-]+$")
                self.assertEqual(
                    set(guia),
                    {"titulo", "seccion", "carpeta", "fuentes", "objetivo", "bloques"},
                )
                self.assertLessEqual(len(guia["titulo"]), 200)
                self.assertLessEqual(len(guia["carpeta"]), 120)
                self.assertGreater(len(guia["objetivo"]), 60)

    def test_cada_recurso_contiene_procedimiento_entregable_y_controles(self):
        for clave, guia in GUIAS.items():
            with self.subTest(clave=clave):
                self.assertGreaterEqual(len(guia["bloques"]), 3)
                self.assertGreaterEqual(
                    sum(len(pasos) for _, pasos in guia["bloques"]), 8
                )
                textos = []
                for titulo, pasos in guia["bloques"]:
                    self.assertTrue(titulo.strip())
                    self.assertGreaterEqual(len(pasos), 2)
                    textos.extend(pasos)
                completo = " ".join(textos).lower()
                self.assertGreater(len(completo.split()), 250)
                self.assertIn("plantilla", completo)
                self.assertIn("entregar", completo)
                self.assertTrue("responsable" in completo or "coordinación" in completo)

    def test_referencias_existen_y_no_se_duplican_dentro_de_un_documento(self):
        for clave, guia in GUIAS.items():
            with self.subTest(clave=clave):
                self.assertTrue(guia["fuentes"])
                self.assertEqual(len(guia["fuentes"]), len(set(guia["fuentes"])))
                self.assertTrue(set(guia["fuentes"]).issubset(FUENTES))
                for fuente in guia["fuentes"]:
                    self.assertTrue(FUENTES[fuente]["url"].startswith("https://"))

    def test_todos_los_documentos_se_renderizan_sin_codigo_ni_medios_externos(self):
        for clave, guia in GUIAS.items():
            with self.subTest(clave=clave):
                documento = documento_html(clave, guia)
                parser = DocumentoInspeccionado()
                parser.feed(documento)
                self.assertIn("h1", parser.etiquetas)
                self.assertGreaterEqual(parser.etiquetas.count("h2"), 4)
                self.assertFalse(
                    set(parser.etiquetas)
                    & {"script", "iframe", "object", "embed", "img", "video", "form"}
                )
                self.assertFalse(parser.atributos_activos)
                self.assertEqual(
                    parser.enlaces,
                    [FUENTES[fuente]["url"] for fuente in guia["fuentes"]],
                )

    def test_render_escapa_texto_del_editor_sin_convertirlo_en_html(self):
        guia = deepcopy(GUIAS["gobierno-laboratorio"])
        texto = '<script>alert("test")</script><img src=x onerror=alert(1)>'
        guia["titulo"] = texto
        guia["objetivo"] = texto
        guia["bloques"] = [(texto, [texto])]
        documento = documento_html("prueba", guia)
        parser = DocumentoInspeccionado()
        parser.feed(documento)
        self.assertNotIn("script", parser.etiquetas)
        self.assertNotIn("img", parser.etiquetas)
        self.assertFalse(parser.atributos_activos)
        self.assertIn("&lt;script&gt;", documento)

    def test_tarifas_y_capacidades_se_derivan_del_catalogo_autorizado(self):
        servicio = " ".join(
            texto
            for _, pasos in GUIAS["servicios-alcance"]["bloques"]
            for texto in pasos
        )
        self.assertIn("ausencia de tarifa significa por confirmar", servicio)
        self.assertIn("nunca gratuidad", servicio)
        self.assertIn("no una declaración de servicios ya ofertados", servicio)
        equipo = " ".join(
            texto
            for _, pasos in GUIAS["expediente-equipo"]["bloques"]
            for texto in pasos
        )
        self.assertIn(
            "no entran al inventario hasta que se confirme su existencia", equipo
        )

    def test_ejemplos_no_se_convierten_en_logros_o_alianzas(self):
        for clave in (
            "proyectos-formativos",
            "centros-articulacion",
            "resultados-validacion",
            "vinculacion-responsable",
        ):
            with self.subTest(clave=clave):
                texto = " ".join(
                    texto for _, pasos in GUIAS[clave]["bloques"] for texto in pasos
                )
                self.assertIn("sintético", texto.lower())
                self.assertTrue(
                    "no declara" in texto
                    or "no crea" in texto
                    or "no afirma" in texto
                    or "no proyectos institucionales" in texto
                )

    def test_criterios_numericos_del_caso_son_coherentes(self):
        # Comprobación independiente de los balances y comparaciones explicados.
        self.assertEqual(18 + 10 + 2, 30)
        self.assertEqual(5 + 4 + 6, 15)
        self.assertLessEqual(4 + 3, 8)
        self.assertEqual(15 * 2, 30)
        base = sum((120, 132, 108)) / 3
        alternativa = sum((96, 108, 84)) / 3
        self.assertEqual((base - alternativa) / base * 100, 20)
        resultados = " ".join(
            texto
            for _, pasos in GUIAS["resultados-validacion"]["bloques"]
            for texto in pasos
        )
        self.assertIn(
            "se necesita contar pedidos que cumplan ambas condiciones", resultados
        )
        self.assertIn("16/20 = 80 %", resultados)

    def test_modulo_editorial_no_importa_modelos_red_o_archivos_operativos(self):
        arbol = ast.parse(
            Path(logistica_contenidos.__file__).read_text(encoding="utf-8")
        )
        self.assertFalse(
            any(
                isinstance(nodo, (ast.Import, ast.ImportFrom))
                for nodo in ast.walk(arbol)
            )
        )
        self.assertFalse(
            any(
                isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                for nodo in ast.walk(arbol)
            )
        )
        self.assertGreaterEqual(VERSION, 1)
        self.assertEqual(FECHA_CONTENIDO, "2026-10-12")
        self.assertIn("registros autorizados", ALCANCE)

    def test_render_determinista_y_sin_mutacion_de_fuente(self):
        anterior = deepcopy(GUIAS)
        for clave, guia in GUIAS.items():
            self.assertEqual(documento_html(clave, guia), documento_html(clave, guia))
        self.assertEqual(GUIAS, anterior)
