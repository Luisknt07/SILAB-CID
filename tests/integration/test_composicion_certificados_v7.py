"""V7: la fila institucional y los fondos preservan el modelo seleccionado."""

import hashlib
from importlib.util import find_spec
from io import BytesIO
from itertools import product
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from apps.formacion.presentation.certificados_diseno import DISENOS_V5, _cajas_fila_v7, _crear_diseno_base_v7, _fondo_v7, _paleta_v7, crear_diseno, dibujar_certificado
from tests.integration import test_composicion_certificados as fixtures


class ComposicionCertificadoV7Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoTests()

    def test_snapshot_nuevo_conserva_datos_de_v7_y_agrega_jerarquia(self):
        cert = self.base.certificado()
        config = SimpleNamespace(
            diseno="sobrio",
            tema_fondo="redes",
            modo_fondo="claro",
            intensidad_fondo="alta",
            logo_1_nombre="Entidad colaboradora",
            logo_1_posicion="izquierda",
            color_primario="#1E5A3D",
            color_acento="#D5AC40",
        )
        identidad = SimpleNamespace(
            nombre="Universidad de muestra", siglas="UM", paleta={}
        )
        with (
            patch(
                "apps.core.presentation.identidad.identidad_actual",
                return_value=(None, identidad),
            ),
            patch(
                "apps.core.presentation.identidad.logo_institucional", return_value=None
            ),
        ):
            anterior = _crear_diseno_base_v7(cert, config)
            actual = crear_diseno(cert, config)
        self.assertEqual(anterior.pop("version"), 7)
        self.assertEqual(actual.pop("version"), 12)
        self.assertEqual(actual.pop("jerarquia_institucional"), "upec_principal")
        self.assertEqual(actual.pop("colaboradores_disposicion"), "logo_sobre_nombre")
        for campo in ('color_texto', 'color_titulos', 'tipografia', 'mostrar_pie_tecnologico', 'estilo_pie_tecnologico'):
            actual.pop(campo)
        self.assertEqual(actual, anterior)
        self.assertEqual(actual["diseno"], "sobrio")
        self.assertEqual(actual["preferencias_fondo"]["tema"], "redes")

    def test_fila_dos_a_cinco_logos_no_apila_ni_superpone_y_ajusta_ancho(self):
        posiciones = ("auto", "izquierda", "centro", "derecha")
        for ancho in (179 * mm, 249 * mm):
            for n in range(1, 5):
                for elegidas in product(posiciones, repeat=n):
                    d = dict(
                        logo_institucional={"nombre": "Universidad"},
                        logos_aliados=[{"posicion": p} for p in elegidas],
                    )
                    cajas = _cajas_fila_v7(d, 24 * mm, 191 * mm, ancho, 12 * mm)
                    self.assertEqual(len(cajas), n + 1)
                    self.assertTrue(cajas[0][0]["institucional"])
                    self.assertTrue(
                        all(c[2] == cajas[0][2] and c[4] == cajas[0][4] for c in cajas)
                    )
                    limite = 24 * mm
                    for _, x, _, w, _ in sorted(cajas, key=lambda c: c[1]):
                        self.assertGreaterEqual(x + 0.001, limite)
                        self.assertLessEqual(x + w, 24 * mm + ancho + 0.001)
                        limite = x + w + 6 * mm
                    if n == 1:
                        self.assertAlmostEqual(cajas[0][1], 24 * mm)
                        self.assertAlmostEqual(
                            cajas[1][1] + cajas[1][3], 24 * mm + ancho
                        )
                        self.assertAlmostEqual(cajas[0][3], 56 * mm)

    def fondo(self, modelo, *, modo="claro", intensidad="alta", imagen=""):
        d = self.base.diseno(modelo)
        d.update(
            version=7,
            tema_fondo="redes",
            modo_fondo=modo,
            intensidad_fondo=intensidad,
            imagen_fondo=imagen,
            preferencias_fondo={"tema": "redes", "modo": modo},
        )
        salida = BytesIO()
        ancho, alto = landscape(A4)
        canvas = Canvas(salida, pagesize=(ancho, alto))
        _, cabecera, _, _ = _paleta_v7(d, modelo)
        _fondo_v7(
            canvas,
            modelo,
            d,
            ancho,
            alto,
            HexColor(d["primario"]),
            HexColor(d["acento"]),
            cabecera,
        )
        canvas.showPage()
        canvas.save()
        return salida.getvalue()

    @skipUnless(find_spec("pymupdf"), "Verificación de raster disponible con PyMuPDF.")
    def test_16_modelos_con_fondo_heredado_son_distintos_y_sobrio_retiene_barras(self):
        import pymupdf

        hashes = []
        for modelo in DISENOS_V5:
            page = pymupdf.open(stream=self.fondo(modelo), filetype="pdf")[0]
            hashes.append(hashlib.sha256(page.get_pixmap().samples).hexdigest())
        self.assertEqual(len(set(hashes)), 16)
        for modo in ("claro", "oscuro"):
            page = pymupdf.open(stream=self.fondo("sobrio", modo=modo), filetype="pdf")[
                0
            ]
            pix = page.get_pixmap()
            for y in (30, 55, 165):
                self.assertTrue(
                    all(
                        abs(a - b) <= 1
                        for a, b in zip(
                            pix.pixel(int(5 * mm), int(y * mm)), (30, 90, 61)
                        )
                    )
                )
                self.assertTrue(
                    all(
                        abs(a - b) <= 1
                        for a, b in zip(
                            pix.pixel(int(10.7 * mm), int(y * mm)), (213, 172, 64)
                        )
                    )
                )
            for intensidad in ("discreta", "alta"):
                page = pymupdf.open(
                    stream=self.fondo(
                        "sobrio",
                        modo=modo,
                        intensidad=intensidad,
                        imagen=self.base.imagen(),
                    ),
                    filetype="pdf",
                )[0]
                self.assertEqual(len(page.parent), 1)

    @skipUnless(find_spec("pymupdf"), "Verificación de PDF disponible con PyMuPDF.")
    def test_dos_logos_reales_comparten_altura_y_no_repiten_nombre_institucional(self):
        import pymupdf

        d = self.base.diseno("sobrio", 0, 3)
        d.update(
            version=7,
            modo_fondo="claro",
            tema_fondo="redes",
            intensidad_fondo="alta",
            preferencias_fondo={"tema": "redes", "modo": "claro"},
            logo_institucional={
                "imagen": self.base.imagen(),
                "nombre": "Universidad de muestra",
                "unidad": "Laboratorio docente",
            },
            logos_aliados=[
                {
                    "imagen": self.base.imagen(),
                    "nombre": "Universidad colaboradora Mariana",
                    "posicion": "izquierda",
                }
            ],
        )
        cert = self.base.certificado()
        cert.diseno_certificado = d
        page = pymupdf.open(stream=dibujar_certificado(cert), filetype="pdf")[0]
        logos = sorted(
            (info["bbox"] for info in page.get_image_info() if info["bbox"][3] < 110),
            key=lambda box: box[0],
        )
        self.assertEqual(len(logos), 2)
        self.assertAlmostEqual(
            (logos[0][1] + logos[0][3]) / 2, (logos[1][1] + logos[1][3]) / 2, places=3
        )
        self.assertLess(logos[0][2], logos[1][0])
        self.assertEqual(page.get_text().count("Universidad de muestra"), 1)
        self.assertEqual(page.get_text().count("Universidad colaboradora Mariana"), 1)
        self.assertGreater(page.search_for("Emisión:")[0].x0, page.rect.width * 0.7)
