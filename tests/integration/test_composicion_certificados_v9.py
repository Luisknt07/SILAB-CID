"""Jerarquia institucional V9: salida PDF real, sin consultas ni escrituras a la BD."""

import base64
from importlib.util import find_spec
from io import BytesIO
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from PIL import Image, ImageDraw
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.lib.colors import HexColor

from apps.formacion.presentation.certificados_diseno import DISENOS_V5, _paleta_v7, crear_diseno, dibujar_certificado
from tests.integration import test_composicion_certificados as fixtures


class ComposicionCertificadoV9Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoTests()
        if find_spec("pymupdf"):
            import pymupdf

            anterior = pymupdf.TOOLS.set_small_glyph_heights()
            pymupdf.TOOLS.set_small_glyph_heights(True)
            self.addCleanup(pymupdf.TOOLS.set_small_glyph_heights, anterior)

    @staticmethod
    def logo(color="#1E5A3D", size=(300, 100)):
        imagen = Image.new("RGBA", size, (0, 0, 0, 0))
        dibujo = ImageDraw.Draw(imagen)
        dibujo.rectangle((8, 8, size[0] - 9, size[1] - 9), fill=color)
        salida = BytesIO()
        imagen.save(salida, "PNG")
        return base64.b64encode(salida.getvalue()).decode()

    def muestra(self, modelo="clasico", modo="claro", aliados=0, *, denso=False):
        certificado = self.base.certificado()
        diseno = self.base.diseno(modelo, 0, 3 if denso else 1)
        marca = self.logo()
        diseno.update(
            version=9,
            jerarquia_institucional="upec_principal",
            modo_fondo=modo,
            tema_fondo="redes",
            intensidad_fondo="alta",
            preferencias_fondo={"modo": modo, "tema": "redes"},
            logo_institucional={
                "imagen": marca,
                "variantes": {"claro": marca, "oscuro": self.logo("white")},
                "nombre": "Universidad Politécnica Estatal del Carchi",
                "unidad": "Laboratorio de Logística, Transporte y Cadena de Suministro",
                "facultad": "Facultad de Comercio Internacional, Integración y Economía Empresarial",
                "carrera": "Carrera de Logística y Transporte",
            },
            logos_aliados=[
                {
                    "nombre": f"Entidad colaboradora {i + 1}",
                    "imagen": self.logo(size=(180 + 30 * i, 90)),
                    "variantes": {},
                    "posicion": ("izquierda", "centro", "derecha", "auto")[i],
                }
                for i in range(aliados)
            ],
            formato_contenido="competencias" if denso else "institucional",
            competencias=[
                "Organiza inventarios y valida decisiones operativas con datos fiables.",
                "Documenta procesos y presenta resultados de aprendizaje verificables.",
            ]
            if denso
            else [],
        )
        if denso:
            diseno["logo_institucional"]["facultad"] = (
                "Facultad de Comercio Internacional, Integración, Administración y Economía Empresarial "
                * 2
            )[:120]
            for i, aliado in enumerate(diseno["logos_aliados"]):
                aliado["nombre"] = (
                    f"Entidad colaboradora {i + 1} de formación continua e investigación aplicada para el desarrollo territorial "
                    * 2
                )[:160]
            certificado.nombre = (
                "María Fernanda Participante de nombres y apellidos compuestos " * 4
            )[:200]
            diseno["texto"] = (
                "Actividad del 12 al 23 de octubre de 2026, con una duración de 40,5 horas. "
                + (
                    "Participó en la formación aplicada de logística, transporte y cadena de suministro; "
                    "resolvió actividades de análisis de datos, diseño de aplicaciones y validación de "
                    "resultados para distintos sectores productivos. " * 3
                )
            )[:700]
            for i, firmante in enumerate(diseno["firmantes"]):
                firmante["nombre"] = (
                    f"Firmante {i + 1} Gabriela Alejandra de apellidos compuestos"
                )
                firmante["cargo"] = (
                    "Coordinación académica de formación continua y transferencia del conocimiento"
                )
        certificado.diseno_certificado = diseno
        return certificado

    @staticmethod
    def lineas(pagina):
        return [
            linea
            for bloque in pagina.get_text("dict")["blocks"]
            for linea in bloque.get("lines", [])
            if any(span["text"].strip() for span in linea["spans"])
        ]

    def renderizar(self, certificado, **kwargs):
        import pymupdf

        with patch(
            "apps.core.presentation.identidad.identidad_actual",
            side_effect=AssertionError(
                "El snapshot emitido no consulta la identidad actual"
            ),
        ):
            contenido = dibujar_certificado(certificado, **kwargs)
        documento = pymupdf.open(stream=contenido, filetype="pdf")
        self.addCleanup(documento.close)
        self.assertEqual(len(documento), 1)
        return documento

    def comprobar_geometria(self, pagina):
        import pymupdf

        links = pagina.get_links()
        self.assertEqual(len(links), 1)
        qr = links[0]["from"]
        lineas = self.lineas(pagina)
        for indice, linea in enumerate(lineas):
            caja = pymupdf.Rect(linea["bbox"])
            self.assertTrue(pagina.rect.contains(caja), linea)
            self.assertFalse(caja.intersects(qr), linea)
            for otra in lineas[indice + 1 :]:
                interseccion = caja & pymupdf.Rect(otra["bbox"])
                # Ignora únicamente el contacto subpíxel entre métricas tipográficas.
                self.assertFalse(
                    interseccion.width > 0.6 and interseccion.height > 0.6,
                    (linea["spans"], otra["spans"], tuple(interseccion)),
                )

    @staticmethod
    def contraste(a, b):
        def luminancia(color):
            canales = [
                v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                for v in (color.red, color.green, color.blue)
            ]
            return sum(v * peso for v, peso in zip(canales, (0.2126, 0.7152, 0.0722)))

        la, lb = luminancia(a), luminancia(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def comprobar_contraste_cabecera(self, pagina, diseno):
        import pymupdf

        fondo = _paleta_v7(diseno, diseno["diseno"])[3]
        for campo in ("nombre", "unidad", "facultad", "carrera"):
            valor = diseno["logo_institucional"].get(campo)
            if not valor:
                continue
            cajas = pagina.search_for(valor)
            self.assertTrue(cajas, campo)
            for linea in self.lineas(pagina):
                for span in linea["spans"]:
                    if any(
                        pymupdf.Rect(span["bbox"]).intersects(caja) for caja in cajas
                    ):
                        self.assertGreaterEqual(
                            self.contraste(HexColor(f"#{span['color']:06x}"), fondo),
                            4.5,
                            (diseno["diseno"], campo, span),
                        )

    def test_snapshot_nuevo_congela_institucion_contexto_y_colaboradores_separados(
        self,
    ):
        identidad = SimpleNamespace(
            nombre="Universidad Politécnica Estatal del Carchi",
            siglas="UPEC",
            paleta={},
        )
        config = SimpleNamespace(
            facultad_nombre="Facultad responsable",
            carrera_nombre="Carrera vinculada",
            mostrar_facultad=True,
            mostrar_carrera=True,
            logo_1_nombre="Entidad colaboradora",
            logo_1_imagen=ContentFile(base64.b64decode(self.logo()), name="aliado.png"),
            logo_2_nombre="Entidad sin archivo",
            color_primario="#123456",
            tema_fondo="redes",
            modo_fondo="claro",
            intensidad_fondo="alta",
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
            diseno = crear_diseno(self.base.certificado(), config)
        self.assertEqual(diseno["version"], 12)
        self.assertEqual(diseno["jerarquia_institucional"], "upec_principal")
        self.assertEqual(diseno["colaboradores_disposicion"], "logo_sobre_nombre")
        self.assertEqual(diseno["logo_institucional"]["nombre"], identidad.nombre)
        self.assertEqual(diseno["logo_institucional"]["unidad"], "Laboratorio docente")
        self.assertEqual(
            diseno["logo_institucional"]["facultad"], "Facultad responsable"
        )
        self.assertEqual(diseno["logo_institucional"]["carrera"], "Carrera vinculada")
        self.assertEqual(
            [a["nombre"] for a in diseno["logos_aliados"]],
            ["Entidad colaboradora", "Entidad sin archivo"],
        )
        self.assertTrue(diseno["logos_aliados"][0]["imagen"])
        self.assertEqual(diseno["logos_aliados"][1]["imagen"], "")
        self.assertEqual(diseno["primario"], "#123456")
        self.assertEqual(diseno["preferencias_fondo"]["tema"], "redes")
        self.assertFalse(diseno["mostrar_nota"])
        certificado = self.base.certificado()
        certificado.diseno_certificado = diseno
        # La salida de la factory debe renderizar, incluida la entradilla predeterminada.
        with patch(
            "apps.core.presentation.identidad.identidad_actual",
            side_effect=AssertionError("Identidad ya congelada"),
        ):
            self.assertTrue(dibujar_certificado(certificado).startswith(b"%PDF"))

    @skipUnless(find_spec("pymupdf"), "La jerarquía PDF requiere PyMuPDF.")
    def test_upec_es_primaria_y_contexto_se_distribuye_en_niveles(self):
        import pymupdf

        for cantidad in range(5):
            with self.subTest(aliados=cantidad):
                cert = self.muestra(aliados=cantidad)
                pagina = self.renderizar(cert)[0]
                institucion = cert.diseno_certificado["logo_institucional"]
                cajas = []
                tamanos = []
                for campo in ("nombre", "unidad", "facultad", "carrera"):
                    partes = pagina.search_for(institucion[campo])
                    self.assertTrue(partes, campo)
                    caja = pymupdf.Rect(partes[0])
                    for parte in partes[1:]:
                        caja |= parte
                    cajas.append(caja)
                    tamanos.append(
                        max(
                            span["size"]
                            for linea in self.lineas(pagina)
                            for span in linea["spans"]
                            if pymupdf.Rect(span["bbox"]).intersects(caja)
                        )
                    )
                self.assertGreater(tamanos[0], max(tamanos[1:]))
                self.assertLess(cajas[0].y1, cajas[1].y0)
                self.assertLess(cajas[1].y1, cajas[2].y0)
                self.assertLess(cajas[2].y1, cajas[3].y0)
                self.assertEqual(pagina.get_text().count(institucion["nombre"]), 1)
                etiqueta = pagina.search_for("En colaboración con")
                self.assertEqual(bool(etiqueta), bool(cantidad))
                if cantidad:
                    for caja in cajas:
                        self.assertFalse(caja.intersects(etiqueta[0]))
                    for aliado in cert.diseno_certificado["logos_aliados"]:
                        self.assertTrue(pagina.search_for(aliado["nombre"]))
                self.comprobar_geometria(pagina)

    @skipUnless(find_spec("pymupdf"), "La comprobación de logos requiere PyMuPDF.")
    def test_logos_aliados_ocupan_una_region_secundaria_separada_de_upec(self):
        import pymupdf

        for cantidad in range(5):
            with self.subTest(aliados=cantidad):
                cert = self.muestra("sobrio", aliados=cantidad)
                pagina = self.renderizar(cert)[0]
                # Las firmas están en el último tercio; la cabecera contiene UPEC y aliados.
                logos = [
                    pymupdf.Rect(info["bbox"])
                    for info in pagina.get_image_info()
                    if info["bbox"][3] < pagina.rect.height / 2
                ]
                self.assertEqual(len(logos), cantidad + 1)
                principal = max(logos, key=lambda caja: caja.get_area())
                secundarios = [caja for caja in logos if caja != principal]
                for caja in secundarios:
                    self.assertFalse(caja.intersects(principal))
                    self.assertLess(caja.get_area(), principal.get_area())
                for indice, caja in enumerate(secundarios):
                    for otra in secundarios[indice + 1 :]:
                        self.assertFalse(caja.intersects(otra))

    @skipUnless(find_spec("pymupdf"), "Los nombres sin logo requieren extracción PDF.")
    def test_colaboradores_sin_imagen_y_contexto_opcional_no_dejan_etiquetas_vacias(
        self,
    ):
        cert = self.muestra(aliados=4)
        for aliado in cert.diseno_certificado["logos_aliados"]:
            aliado["imagen"] = ""
        cert.diseno_certificado["logo_institucional"].update(facultad="", carrera="")
        pagina = self.renderizar(cert)[0]
        self.assertEqual(pagina.get_text().count("En colaboración con"), 1)
        for aliado in cert.diseno_certificado["logos_aliados"]:
            self.assertEqual(pagina.get_text().count(aliado["nombre"]), 1)
        self.assertNotIn("Facultad", pagina.get_text())
        self.assertNotIn("Carrera", pagina.get_text())
        self.comprobar_geometria(pagina)

    @skipUnless(find_spec("pymupdf"), "La matriz de composición requiere PyMuPDF.")
    def test_dieciseis_modelos_claros_oscuros_densos_caben_y_no_solapan(self):
        for modelo in DISENOS_V5:
            for modo in ("claro", "oscuro"):
                with self.subTest(modelo=modelo, modo=modo):
                    cert = self.muestra(modelo, modo, 4, denso=True)
                    pagina = self.renderizar(cert)[0]
                    self.comprobar_geometria(pagina)
                    self.comprobar_contraste_cabecera(pagina, cert.diseno_certificado)
                    self.assertGreaterEqual(
                        len(
                            pagina.search_for(
                                cert.diseno_certificado["logo_institucional"][
                                    "facultad"
                                ]
                            )
                        ),
                        2,
                    )
                    texto = " ".join(pagina.get_text().split())
                    self.assertIn("En colaboración con", texto)
                    self.assertIn("40,5", texto)
                    for i in range(3):
                        self.assertIn(f"Firmante {i + 1}", texto)
                    self.assertEqual(
                        pagina.get_links()[0]["uri"],
                        cert.diseno_certificado["verificacion_url"],
                    )
                    self.assertNotIn("Calificación", texto)

    @skipUnless(find_spec("pymupdf"), "El QR impreso se verifica desde sus píxeles.")
    def test_qr_impreso_es_legible_y_codifica_el_enlace_exacto(self):
        import pymupdf

        for modelo, modo in (
            ("clasico", "claro"),
            ("sobrio", "oscuro"),
            ("editorial", "claro"),
            ("ia_particulas", "oscuro"),
        ):
            with self.subTest(modelo=modelo, modo=modo):
                cert = self.muestra(modelo, modo, 4, denso=True)
                pagina = self.renderizar(cert)[0]
                enlace = pagina.get_links()[0]
                referencia = QrCodeWidget(cert.diseno_certificado["verificacion_url"])
                referencia.qr.make()
                matriz = referencia.qr.modules
                pix = pagina.get_pixmap(
                    matrix=pymupdf.Matrix(5, 5), clip=enlace["from"], alpha=False
                )
                dimension = len(matriz) + 8  # Cuatro módulos de zona blanca por lado.
                for fila, valores in enumerate(matriz):
                    for columna, negro in enumerate(valores):
                        x = round((columna + 4.5) * pix.width / dimension)
                        y = round((fila + 4.5) * pix.height / dimension)
                        observado = sum(pix.pixel(x, y)[:3]) < 384
                        self.assertEqual(observado, negro, (fila, columna))

    @skipUnless(find_spec("pymupdf"), "La salida pública requiere extracción PDF.")
    def test_documento_privado_se_oculta_sin_perder_institucion_o_verificacion(self):
        cert = self.muestra("industrial", "oscuro", 4, denso=True)
        pagina = self.renderizar(cert, mostrar_documento=False)[0]
        self.assertNotIn(cert.documento, pagina.get_text())
        self.assertTrue(
            pagina.search_for(cert.diseno_certificado["logo_institucional"]["nombre"])
        )
        self.assertEqual(
            pagina.get_links()[0]["uri"], cert.diseno_certificado["verificacion_url"]
        )
        self.comprobar_geometria(pagina)
