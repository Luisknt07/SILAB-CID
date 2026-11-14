"""Superficie blanca y formato lateral, con PDF real y sin persistencia."""
import hashlib
from importlib.util import find_spec
from unittest import skipUnless

from django.test import SimpleTestCase
from reportlab.lib.units import mm

from apps.formacion.presentation.certificados_diseno import dibujar_certificado
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
from apps.formacion.models.cursos_certificacion import DISENOS_CERTIFICADO
from tests.integration import test_composicion_certificados_v10 as fixtures


class ComposicionCertificadoV12Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoV10Tests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)

    def muestra(self, modelo, modo="claro", aliados=0, denso=False):
        cert = self.base.muestra(modelo, modo, aliados, denso=denso)
        cert.diseno_certificado.update(version=12, primario="#006633", acento="#FFCE00", tipografia="poppins")
        return cert

    def test_preferencias_antiguas_no_oscurecen_nuevos_certificados(self):
        self.assertEqual(len(DISENOS_CERTIFICADO), 17)
        for modelo, _ in DISENOS_CERTIFICADO:
            for modo in ("auto", "oscuro", "claro"):
                with self.subTest(modelo=modelo, modo=modo):
                    snapshot = self.base.crear(modelo, {}, modo_fondo=modo,
                                               color_primario="#125A38", logo_1_nombre="Entidad aliada")
                    self.assertEqual(snapshot["version"], 12)
                    self.assertEqual(snapshot["diseno"], modelo)
                    self.assertEqual(snapshot["modo_fondo"], "claro")
                    self.assertEqual(snapshot["preferencias_fondo"]["modo"], "claro")
                    self.assertEqual(snapshot["primario"], "#125A38")
                    self.assertEqual(snapshot["logos_aliados"][0]["nombre"], "Entidad aliada")

    def test_modo_de_fondo_no_es_un_selector_y_normaliza_el_valor_legado(self):
        form = ConfiguracionCertificadoForm(initial={"modo_fondo": "oscuro"})
        self.assertTrue(form.fields["modo_fondo"].widget.is_hidden)
        self.assertEqual(form.initial["modo_fondo"], "claro")
        fondo = next(g for g in form.secciones_editor if g["clave"] == "fondo")
        self.assertNotIn("modo_fondo", [campo.name for campo in fondo["campos"]])
        self.assertEqual(form.clean_modo_fondo(), "claro")

    @skipUnless(find_spec("pymupdf"), "Se inspecciona el PDF real con PyMuPDF.")
    def test_todos_los_modelos_tienen_papel_blanco_aunque_llegue_modo_oscuro(self):
        import pymupdf
        for modelo, _ in DISENOS_CERTIFICADO:
            huellas = []
            for modo in ("claro", "oscuro"):
                with self.subTest(modelo=modelo, modo=modo):
                    cert = self.muestra(modelo, modo)
                    with pymupdf.open(stream=dibujar_certificado(cert), filetype="pdf") as doc:
                        self.assertEqual(len(doc), 1)
                        pagina = doc[0]
                        self.base.anterior.comprobar_geometria(pagina)
                        self.base.comprobar_qr(pagina, cert.diseno_certificado["verificacion_url"])
                        huellas.append(hashlib.sha256(pagina.get_pixmap().samples).hexdigest())
                        izquierda = 94 if modelo == "formacion_lateral" else 24
                        for altura in (70, 130):
                            pix = pagina.get_pixmap(clip=pymupdf.Rect(izquierda * mm, altura * mm, 275 * mm, (altura + 8) * mm), alpha=False)
                            blancos = sum(all(v > 235 for v in pix.pixel(x, y)[:3])
                                          for x in range(0, pix.width, 3) for y in range(0, pix.height, 3))
                            total = len(range(0, pix.width, 3)) * len(range(0, pix.height, 3))
                            self.assertGreater(blancos / total, .85)
            self.assertEqual(huellas[0], huellas[1], modelo)

    @skipUnless(find_spec("pymupdf"), "Se inspecciona el PDF real con PyMuPDF.")
    def test_lateral_con_competencias_colaboradores_y_tres_firmas(self):
        import pymupdf
        for cantidad in range(5):
            with self.subTest(colaboradores=cantidad):
                cert = self.muestra("formacion_lateral", aliados=cantidad, denso=True)
                with pymupdf.open(stream=dibujar_certificado(cert, vista_previa=True), filetype="pdf") as doc:
                    pagina = doc[0]
                    self.base.anterior.comprobar_geometria(pagina)
                    self.base.comprobar_qr(pagina, cert.diseno_certificado["verificacion_url"])
                    texto = " ".join(pagina.get_text().split())
                    self.assertIn("COMPETENCIAS Y LOGROS", texto)
                    self.assertIn("Organiza inventarios", texto)
                    qr = pagina.get_links()[0]["from"]
                    self.assertLess(qr.x1, 78 * mm)
                    for firma in cert.diseno_certificado["firmantes"]:
                        cajas = pagina.search_for(firma["nombre"])
                        self.assertTrue(cajas, firma["nombre"])
                        self.assertTrue(all(caja.x0 > 94 * mm for caja in cajas))
                    self.assertIn(cert.diseno_certificado["fecha_emision"], texto)

    @skipUnless(find_spec("pymupdf"), "Se inspecciona el PDF real con PyMuPDF.")
    def test_lateral_adapta_texto_y_logo_a_una_franja_personalizada_clara(self):
        import pymupdf
        cert = self.muestra("formacion_lateral")
        cert.diseno_certificado["primario"] = "#FFFFDD"
        with pymupdf.open(stream=dibujar_certificado(cert), filetype="pdf") as doc:
            spans = [s for b in doc[0].get_text("dict")["blocks"] for linea in b.get("lines", []) for s in linea["spans"]]
            laterales = [s for s in spans if s["bbox"][2] < 78 * mm]
            self.assertTrue(laterales)
            self.assertTrue(all(s["color"] == 0 for s in laterales))

    @skipUnless(find_spec("pymupdf"), "Se inspecciona el PDF real con PyMuPDF.")
    def test_foto_lateral_y_pie_opcional_no_invaden_firmas(self):
        import pymupdf
        cert = self.muestra("formacion_lateral", aliados=2)
        cert.diseno_certificado.update(foto=self.base.anterior.logo(), mostrar_pie_tecnologico=True,
                                       estilo_pie_tecnologico="calidad")
        with pymupdf.open(stream=dibujar_certificado(cert, vista_previa=True), filetype="pdf") as doc:
            pagina = doc[0]
            self.base.anterior.comprobar_geometria(pagina)
            self.assertIn("CALIDAD", pagina.get_text())
            # La imagen original puede extenderse fuera del recorte: se verifica
            # el resultado visible, no su caja intrínseca antes de aplicar el clip.
            pix = pagina.get_pixmap(alpha=False)
            pixel = pix.pixel(round(40 * mm), round(120 * mm))
            self.assertGreater(pixel[0], 10)
            self.assertLess(pixel[1], 102)
            self.assertEqual(pix.pixel(round(282 * mm), round(170 * mm))[:3], (255, 255, 255))

    @skipUnless(find_spec("pymupdf"), "Se inspecciona el PDF real con PyMuPDF.")
    def test_fotografias_y_fondo_negro_no_oscurecen_el_bloque_de_logos(self):
        import pymupdf
        from io import BytesIO
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen.canvas import Canvas
        from apps.formacion.presentation.certificados_composicion import _fondo
        negro = self.base.anterior.logo("black", size=(1200, 800))
        for modelo in ("industrial", "editorial", "horizonte", "inmersivo"):
            with self.subTest(modelo=modelo):
                cert = self.muestra(modelo, aliados=4)
                diseno = dict(cert.diseno_certificado, foto=negro, imagen_fondo=negro)
                salida = BytesIO()
                lienzo = Canvas(salida, pagesize=landscape(A4))
                _fondo(lienzo, modelo, diseno, *landscape(A4), HexColor("#006633"), HexColor("#FFCE00"))
                lienzo.showPage()
                lienzo.save()
                with pymupdf.open(stream=salida.getvalue(), filetype="pdf") as doc:
                    pix = doc[0].get_pixmap(alpha=False)
                    for x in (25, 45, 160, 200, 270):
                        for y in (10, 25, 40):
                            self.assertGreaterEqual(min(pix.pixel(round(x * mm), round(y * mm))[:3]), 210)
                    self.assertEqual(pix.pixel(round(145 * mm), round(170 * mm))[:3], (255, 255, 255))
