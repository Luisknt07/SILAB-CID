"""V11: capas fotográficas, paleta, fuentes y pie opcional en el PDF real."""

import base64
from importlib.util import find_spec
from io import BytesIO
from unittest import skipUnless

from django.test import SimpleTestCase
from PIL import Image, ImageDraw
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

from apps.formacion.presentation.certificados_diseno import DISENOS_V5, _paleta_v11
from tests.integration import test_composicion_certificados_v10 as anterior


@skipUnless(find_spec("pymupdf"), "Requiere inspección del PDF real.")
class FondosCertificadosV11Tests(SimpleTestCase):
    def setUp(self):
        self.base = anterior.ComposicionCertificadoV10Tests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)

    def muestra(self, modelo="clasico", modo="claro", aliados=0, denso=False):
        cert = self.base.muestra(modelo, modo, aliados, denso=denso)
        cert.diseno_certificado.update(
            version=11, tipografia="poppins", primario="#006633", acento="#FFCE00"
        )
        return cert

    @staticmethod
    def foto():
        imagen = Image.new("RGB", (900, 600), "#d8d8d8")
        dibujo = ImageDraw.Draw(imagen)
        for x in range(0, 900, 50):
            dibujo.rectangle((x, 0, x + 24, 600), fill="#bf5025")
            dibujo.line((x, 0, 900 - x, 600), fill="#19775d", width=8)
        salida = BytesIO()
        imagen.save(salida, "PNG")
        return base64.b64encode(salida.getvalue()).decode()

    def test_todos_los_modelos_con_densidad_colaboradores_y_pie_conservan_geometria_qr_y_contraste(
        self,
    ):
        for modelo in DISENOS_V5:
            for modo in ("claro", "oscuro"):
                with self.subTest(modelo=modelo, modo=modo):
                    cert = self.muestra(modelo, modo, 4, True)
                    cert.diseno_certificado.update(
                        mostrar_pie_tecnologico=True,
                        estilo_pie_tecnologico="fabricacion",
                    )
                    pagina = self.base.renderizar(cert)[0]
                    self.base.anterior.comprobar_geometria(pagina)
                    self.base.comprobar_qr(
                        pagina, cert.diseno_certificado["verificacion_url"]
                    )
                    _, fondo = _paleta_v11(cert.diseno_certificado)
                    for linea in self.base.anterior.lineas(pagina):
                        for span in linea["spans"]:
                            if span["bbox"][1] < 420:
                                self.assertGreaterEqual(
                                    self.base.anterior.contraste(
                                        HexColor(f"#{span['color']:06x}"), fondo
                                    ),
                                    4.5,
                                )
                    self.assertIn("FABRICACIÓN DIGITAL", pagina.get_text())
                    self.assertTrue(any("Poppins" in f[3] for f in pagina.get_fonts()))

    def test_fondo_oscuro_es_derivado_del_color_y_no_del_azul_fijo(self):
        for color in ("#006633", "#71391D", "#163D5C"):
            cert = self.muestra("sobrio", "oscuro")
            cert.diseno_certificado["primario"] = color
            pagina = self.base.renderizar(cert)[0]
            pix = pagina.get_pixmap()
            observado = pix.pixel(round(145 * mm), round((210 - 70) * mm))[:3]
            esperado = tuple(round(int(color[i : i + 2], 16) * 0.30) for i in (1, 3, 5))
            for a, b in zip(observado, esperado):
                self.assertAlmostEqual(a, b, delta=2)

    def test_fotografias_y_fondo_propio_siguen_visibles_tras_dibujar_logos(self):
        import pymupdf
        from PIL import ImageChops

        foto = self.foto()
        for modelo in ("industrial", "editorial", "horizonte", "inmersivo"):
            for modo in ("claro", "oscuro"):
                with self.subTest(modelo=modelo, modo=modo):
                    cert = self.muestra(modelo, modo)
                    limpio = self.base.renderizar(cert)[0].get_pixmap().pil_image()
                    cert.diseno_certificado["foto"] = foto
                    pagina = self.base.renderizar(cert)[0]
                    nuevo = pagina.get_pixmap().pil_image()
                    # Cambia de forma visible la zona fotográfica sin cubrir el cuerpo.
                    diferencia = ImageChops.difference(limpio, nuevo).convert("L")
                    cabecera = diferencia.crop((0, 0, nuevo.width, round(48 * mm)))
                    self.assertGreater(
                        sum(1 for v in cabecera.getdata() if v > 12)
                        / len(list(cabecera.getdata())),
                        0.08,
                    )
                    self.base.anterior.comprobar_geometria(pagina)
        cert = self.muestra()
        cert.diseno_certificado["imagen_fondo"] = foto
        pagina = self.base.renderizar(cert)[0]
        imagenes = pagina.get_image_info()
        self.assertTrue(any(pymupdf.Rect(i["bbox"]).width > 700 for i in imagenes))
        self.base.anterior.comprobar_geometria(pagina)

    def test_colores_de_texto_y_titulos_no_cambian_el_diseno_y_se_adaptan_al_contraste(
        self,
    ):
        cert = self.muestra()
        cert.diseno_certificado.update(color_texto="#321234", color_titulos="#71391D")
        pagina = self.base.renderizar(cert)[0]
        spans = [
            s for linea in self.base.anterior.lineas(pagina) for s in linea["spans"]
        ]
        self.assertTrue(any(s["color"] == 0x321234 for s in spans))
        self.assertTrue(any(s["color"] == 0x71391D for s in spans))
        self.assertEqual(cert.diseno_certificado["primario"], "#006633")
        cert.diseno_certificado.update(color_texto="#FFFFFF", color_titulos="#FFFFFF")
        pagina = self.base.renderizar(cert)[0]
        self.assertTrue(
            all(
                s["color"] != 0xFFFFFF
                for linea in self.base.anterior.lineas(pagina)
                for s in linea["spans"]
            )
        )

    def test_fuentes_y_pie_son_opcionales_y_no_desplazan_firmas(self):
        for tipografia, familia in (
            ("poppins", "Poppins"),
            ("nunito", "Nunito"),
            ("clasica", "Times"),
        ):
            cert = self.muestra()
            cert.diseno_certificado["tipografia"] = tipografia
            pagina = self.base.renderizar(cert)[0]
            self.assertTrue(any(familia in f[3] for f in pagina.get_fonts()))
            antes = pagina.search_for(cert.diseno_certificado["firmantes"][0]["nombre"])
            self.assertNotIn("INNOVACIÓN · TECNOLOGÍA", pagina.get_text())
            for estilo, texto in (
                ("circuitos", "CONEXIONES"),
                ("fabricacion", "FABRICACIÓN DIGITAL"),
                ("calidad", "CALIDAD"),
            ):
                cert.diseno_certificado.update(
                    mostrar_pie_tecnologico=True, estilo_pie_tecnologico=estilo
                )
                pagina = self.base.renderizar(cert)[0]
                self.assertIn(texto, pagina.get_text())
                self.assertEqual(
                    antes,
                    pagina.search_for(
                        cert.diseno_certificado["firmantes"][0]["nombre"]
                    ),
                )
                self.base.anterior.comprobar_geometria(pagina)

    def test_snapshot_congela_tipografia_colores_y_pie_para_emisiones_nuevas(self):
        opciones = dict(
            color_texto="#321234",
            color_titulos="#71391D",
            tipografia="nunito",
            mostrar_pie_tecnologico=True,
            estilo_pie_tecnologico="calidad",
        )
        snapshot = self.base.crear("horizonte", {}, **opciones)
        self.assertEqual(snapshot["version"], 12)
        for clave, valor in opciones.items():
            self.assertEqual(snapshot[clave], valor)
        automatico = self.base.crear("ia_particulas", {})
        self.assertFalse(automatico["mostrar_pie_tecnologico"])
        self.assertEqual(automatico["tipografia"], "poppins")
        self.assertEqual(automatico["primario"], "#006633")

    def test_opciones_claro_y_oscuro_representan_el_logo_y_no_el_fondo(self):
        from django.core.files.base import ContentFile

        for contraste, esperado in (
            ("claro", (255, 255, 255)),
            ("oscuro", (0, 102, 51)),
        ):
            snapshot = self.base.crear(
                "horizonte",
                {},
                logo_1_nombre="Colaborador",
                logo_1_imagen=ContentFile(
                    base64.b64decode(self.base.anterior.logo("white")), name="logo.png"
                ),
                logo_1_contraste=contraste,
            )
            for modo in ("claro", "oscuro"):
                datos = snapshot["logos_aliados"][0]["variantes"][modo]
                with Image.open(BytesIO(base64.b64decode(datos))) as imagen:
                    visibles = [
                        rgb[:3]
                        for rgb in imagen.convert("RGBA").getdata()
                        if rgb[3] > 200
                    ]
                self.assertTrue(visibles)
                self.assertEqual(visibles[len(visibles) // 2], esperado)
