"""V8: contraste de texto y continuidad de cabecera sin alterar paleta decorativa."""

from importlib.util import find_spec
from io import BytesIO
from unittest import skipUnless

from django.test import SimpleTestCase
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from apps.formacion.presentation.certificados_diseno import _color_texto_v8, _fondo_v7, _fondo_v8, _paleta_v7, dibujar_certificado
from tests.integration import test_composicion_certificados as fixtures


class ComposicionCertificadoV8Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoTests()

    @staticmethod
    def contraste(a, b):
        def luminancia(c):
            canales = [
                v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                for v in (c.red, c.green, c.blue)
            ]
            return sum(v * p for v, p in zip(canales, (0.2126, 0.7152, 0.0722)))

        la, lb = luminancia(a), luminancia(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    @skipUnless(find_spec("pymupdf"), "Extracción y raster requieren PyMuPDF.")
    def test_texto_contrasta_sin_cambiar_acento_decorativo(self):
        import pymupdf

        for fondo in ("#081C30", "#888888", "#FFFFFF"):
            tinta = _color_texto_v8(HexColor(fondo), HexColor(fondo))
            self.assertGreaterEqual(self.contraste(tinta, HexColor(fondo)), 4.5)
        tinta = HexColor("#F3F7F8")
        self.assertIs(_color_texto_v8(tinta, HexColor("#081C30")), tinta)
        cert = self.base.certificado()
        d = self.base.diseno("sobrio", 0, 3)
        d.update(
            version=8,
            modo_fondo="oscuro",
            tema_fondo="redes",
            preferencias_fondo={"modo": "oscuro", "tema": "redes"},
            logo_institucional={"nombre": "Universidad", "unidad": "Laboratorio"},
            logos_aliados=[],
            formato_contenido="competencias",
            competencias=["Gestiona inventarios con datos fiables."],
            acento="#000000",
        )
        cert.diseno_certificado = d
        page = pymupdf.open(stream=dibujar_certificado(cert), filetype="pdf")[0]
        span = next(
            s
            for b in page.get_text("dict")["blocks"]
            for linea in b.get("lines", [])
            for s in linea["spans"]
            if "COMPETENCIAS Y LOGROS" in s["text"]
        )
        self.assertEqual(d["acento"], "#000000")
        self.assertGreaterEqual(
            self.contraste(
                HexColor(f"#{span['color']:06x}"), _paleta_v7(d, "sobrio")[2]
            ),
            4.5,
        )

    @skipUnless(find_spec("pymupdf"), "Continuidad visual requiere PyMuPDF.")
    def test_cabecera_oscura_no_sobresale_hacia_cuerpo_y_preserva_franja_sobrio(self):
        import pymupdf

        d = self.base.diseno("sobrio")
        d.update(
            version=8,
            modo_fondo="oscuro",
            tema_fondo="auto",
            preferencias_fondo={"modo": "oscuro", "tema": "auto"},
        )
        ancho, alto = landscape(A4)
        fondos = []
        for dibujar in (_fondo_v7, _fondo_v8):
            salida = BytesIO()
            canvas = Canvas(salida, pagesize=(ancho, alto))
            _, oscuro, _, _ = _paleta_v7(d, "sobrio")
            dibujar(
                canvas,
                "sobrio",
                d,
                ancho,
                alto,
                HexColor(d["primario"]),
                HexColor(d["acento"]),
                oscuro,
            )
            canvas.showPage()
            canvas.save()
            fondos.append(
                pymupdf.open(stream=salida.getvalue(), filetype="pdf")[0].get_pixmap()
            )

        def pixel(pix, x, y):
            return pix.pixel(round(x * mm), round(alto - y * mm))

        self.assertNotEqual(pixel(fondos[0], 18, 149), pixel(fondos[0], 28, 149))
        self.assertEqual(pixel(fondos[1], 18, 149), pixel(fondos[1], 28, 149))
        self.assertEqual(pixel(fondos[0], 5, 149), pixel(fondos[1], 5, 149))
