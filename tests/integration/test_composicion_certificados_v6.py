"""Composición V6: institución y aliados, firmas protagonistas y emisión junto al QR."""

import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from importlib.util import find_spec
from unittest import skipUnless
from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from PIL import Image
from apps.formacion.presentation.certificados_diseno import DISENOS_V5, _contraste_logo_v6, _crear_diseno_base_v5, crear_diseno, dibujar_certificado
from tests.integration import test_composicion_certificados as fixtures


class ComposicionCertificadoV6Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoTests()
        self.identidad = SimpleNamespace(
            nombre="Universidad de muestra", siglas="UM", paleta={}
        )

    def crear(self, config=None, cert=None):
        with (
            patch(
                "apps.core.presentation.identidad.identidad_actual",
                return_value=(None, self.identidad),
            ),
            patch(
                "apps.core.presentation.identidad.logo_institucional", return_value=None
            ),
        ):
            return crear_diseno(cert or self.base.certificado(), config)

    def test_institucion_separada_cuatro_aliados_y_entidad_sin_archivo(self):
        config = SimpleNamespace(
            logo_1_nombre="Entidad primera",
            logo_2_nombre="Entidad segunda",
            logo_3_nombre="Entidad tercera",
            logo_4_nombre="Organizador sin logo",
            facultad_nombre="Facultad de ciencias",
            carrera_nombre="Logística",
            mostrar_facultad=True,
            mostrar_carrera=False,
        )
        for i in range(1, 4):
            setattr(
                config,
                f"logo_{i}_imagen",
                ContentFile(base64.b64decode(self.base.imagen()), name=f"logo{i}.png"),
            )
        d = self.crear(config)
        self.assertEqual(d["version"], 12)
        self.assertEqual(d["logo_institucional"]["nombre"], "Universidad de muestra")
        self.assertEqual(d["logo_institucional"]["unidad"], "Laboratorio docente")
        self.assertEqual(d["logo_institucional"]["facultad"], "Facultad de ciencias")
        self.assertEqual(d["logo_institucional"]["carrera"], "")
        self.assertEqual(len(d["logos_aliados"]), 4)
        self.assertEqual(d["logos_aliados"][3]["nombre"], "Organizador sin logo")
        self.assertEqual(d["logos_aliados"][3]["imagen"], "")

    def test_contraste_adapta_solo_monocromos_transparentes_y_respeta_original(self):
        def logo(color, alpha=True):
            img = Image.new(
                "RGBA" if alpha else "RGB", (5, 2), (0, 0, 0, 0) if alpha else "white"
            )
            img.putpixel((2, 0), (*color, 180) if alpha else color)
            salida = BytesIO()
            img.save(salida, "PNG")
            return base64.b64encode(salida.getvalue()).decode()

        blanco = logo((255, 255, 255))
        negro = logo((0, 0, 0))
        for original, oscuro, color_final in [
            (blanco, False, (22, 75, 114)),
            (negro, True, (255, 255, 255)),
        ]:
            adaptada = _contraste_logo_v6(original, "auto", oscuro, "#164B72")
            with Image.open(BytesIO(base64.b64decode(adaptada))) as img:
                self.assertEqual(img.getpixel((2, 0)), (*color_final, 180))
                self.assertEqual(img.getpixel((0, 0))[3], 0)
            self.assertEqual(
                _contraste_logo_v6(original, "original", oscuro, "#164B72"), original
            )
        for marca in [logo((220, 70, 35)), logo((255, 255, 255), False)]:
            for modo in ["auto", "claro", "oscuro"]:
                self.assertEqual(
                    _contraste_logo_v6(marca, modo, False, "#164B72"), marca
                )
        self.assertEqual(_contraste_logo_v6(blanco, "oscuro", False, "#164B72"), blanco)
        self.assertEqual(_contraste_logo_v6(negro, "claro", True, "#164B72"), negro)

    def test_organizadores_lista_natural_y_emisor_personalizado_sin_cambios(self):
        config = SimpleNamespace(
            emisor="Unidad organizadora",
            logo_1_nombre="Entidad A",
            logo_2_nombre="Entidad B",
            logo_3_nombre="Entidad A",
            texto_aprobacion="Organización: {organizadores}. Emisor: {emisor}.",
        )
        d = self.crear(config)
        self.assertEqual(
            d["organizadores"], "Unidad organizadora, Entidad A y Entidad B"
        )
        self.assertEqual(d["emisor"], "Unidad organizadora")
        self.assertIn(
            "Organización: Unidad organizadora, Entidad A y Entidad B.", d["texto"]
        )
        custom = self.crear(
            SimpleNamespace(
                logo_1_nombre="Entidad A", texto_aprobacion="Texto propio de {emisor}."
            )
        )
        self.assertIn("Texto propio de Laboratorio docente.", custom["texto"])
        self.assertNotIn("Entidad A", custom["texto"])
        self.assertIn(
            "Entidad A", self.crear(SimpleNamespace(logo_1_nombre="Entidad A"))["texto"]
        )

    def test_muestra_sin_datos_y_fechas_parciales_no_inventan_periodo_ni_horas(self):
        cert = self.base.certificado()
        cert.es_muestra_editor = True
        cert.horas = None
        cert.fecha_inicio = None
        cert.fecha_fin = None
        for tipo in [
            "aprobacion",
            "participacion",
            "asistencia",
            "ponente",
            "organizador",
        ]:
            cert.tipo = tipo
            d = self.crear(cert=cert)
            self.assertEqual(d["periodo"], "Período por definir")
            self.assertEqual(d["horas"], "Duración por definir")
            self.assertIn("período por definir", d["texto"])
            self.assertIn("duración por definir", d["texto"])
            self.assertNotIn("None", d["texto"])
            self.assertNotIn("0 horas", d["texto"])
        from datetime import date

        cert.fecha_inicio = date(2026, 10, 12)
        d = self.crear(
            SimpleNamespace(
                texto_organizador="Actividad: {periodo}. Inicio: {fecha_inicio}; final: {fecha_fin}; {horas} horas."
            ),
            cert,
        )
        self.assertIn("12 de octubre de2026".replace("de2026", "de 2026"), d["texto"])
        self.assertIn("fecha por definir", d["texto"])
        self.assertEqual(d["periodo"], "Período por definir")
        cert.es_muestra_editor = False
        real = self.crear(cert=cert)
        self.assertNotEqual(real.get("periodo"), "Período por definir")

    def test_factory_v5_sin_configuracion_ignora_variables_de_defaults_nuevos(self):
        with (
            patch(
                "apps.core.presentation.identidad.identidad_actual",
                return_value=(None, self.identidad),
            ),
            patch(
                "apps.core.presentation.identidad.logo_institucional", return_value=None
            ),
        ):
            d = _crear_diseno_base_v5(self.base.certificado())
        self.assertEqual(d["version"], 5)
        self.assertNotIn("{organizadores}", d["texto"])
        self.assertIn("Laboratorio docente", d["texto"])

    @skipUnless(find_spec("pymupdf"), "Geometría PDF disponible con PyMuPDF.")
    def test_dieciseis_disenos_cinco_logos_y_tres_firmas_densos_con_emision_junto_qr(
        self,
    ):
        import pymupdf

        for modelo in DISENOS_V5:
            with self.subTest(modelo=modelo):
                cert = self.base.certificado()
                cert.nombre = (
                    "María Fernanda Participante de nombre y apellidos compuestos " * 4
                )[:200]
                d = self.base.diseno(modelo, 4, 3)
                for i, a in enumerate(d["logos"]):
                    a["nombre"] = (
                        (
                            "Entidad aliada de formación y desarrollo profesional número "
                            + str(i + 1)
                            + " "
                        )
                        * 3
                    )[:160]
                d.update(
                    version=6,
                    logo_institucional={
                        "imagen": self.base.imagen(),
                        "nombre": "Universidad de muestra",
                        "unidad": "Laboratorio docente",
                        "facultad": "Facultad de ciencias",
                        "carrera": "Logística",
                    },
                    logos_aliados=d["logos"],
                    formato_contenido="competencias",
                    competencias=[
                        (
                            "Diseña aplicaciones y valida resultados para mejorar decisiones operativas. "
                            * 2
                        )[:99]
                        for _ in range(6)
                    ],
                    tema_fondo="redes",
                    modo_fondo="oscuro"
                    if modelo in ["ia_particulas", "poligonos_digitales"]
                    else "claro",
                    intensidad_fondo="media",
                    preferencias_fondo={"tema": "auto", "modo": "auto"},
                )
                d["texto"] = (
                    (
                        "Participó en el encuentro de actualización profesional sobre aplicaciones de inteligencia artificial para logística, transporte y cadena de suministro; desarrolló actividades guiadas de análisis, simulación, diseño de soluciones y validación de resultados. "
                        * 3
                    )[:700]
                    + " La actividad se desarrolló del 12 al 23 de octubre de2026, con una duración de40,5 horas.".replace(
                        "de2026", "de 2026"
                    ).replace("de40", "de 40")
                )
                for firma in d["firmantes"]:
                    firma["nombre"] = (
                        "Gabriela Alejandra Nombre compuesto de firmante de muestra "
                        * 3
                    )[:160]
                    firma["cargo"] = (
                        "Coordinación académica institucional de formación continua y transferencia del conocimiento "
                        * 3
                    )[:200]
                cert.diseno_certificado = d
                pdf = pymupdf.open(stream=dibujar_certificado(cert), filetype="pdf")
                p = pdf[0]
                self.assertEqual(len(pdf), 1)
                qr = p.get_links()[0]["from"]
                self.assertEqual(p.get_links()[0]["uri"], d["verificacion_url"])
                self.assertEqual(len(p.search_for("Emisión:")), 1)
                self.assertGreater(p.search_for("Emisión:")[0].x0, p.rect.width * 0.7)
                self.assertIn("Facultad de ciencias", p.get_text())
                for b in p.get_text("dict")["blocks"]:
                    for linea in b.get("lines", []):
                        box = pymupdf.Rect(linea["bbox"])
                        self.assertTrue(p.rect.contains(box))
                        self.assertFalse(box.intersects(qr))

    @skipUnless(find_spec("pymupdf"), "Tamaño de firma disponible con PyMuPDF.")
    def test_nombre_firmantes_normal_tiene_11_puntos_y_emision_no_esta_en_centro(self):
        import pymupdf

        for n in (1, 2, 3):
            cert = self.base.certificado()
            d = self.base.diseno("geometrico", 0, n)
            d.update(
                version=6,
                logo_institucional={
                    "nombre": "Universidad de muestra",
                    "unidad": "Laboratorio docente",
                },
                logos_aliados=[],
            )
            cert.diseno_certificado = d
            p = pymupdf.open(stream=dibujar_certificado(cert), filetype="pdf")[0]
            firmas = [
                s
                for b in p.get_text("dict")["blocks"]
                for linea in b.get("lines", [])
                for s in linea["spans"]
                if s["text"] == "Gabriela Montenegro"
            ]
            self.assertEqual(len(firmas), n)
            self.assertTrue(all(s["size"] >= 11 for s in firmas))
            self.assertGreater(p.search_for("Emisión:")[0].x0, p.rect.width * 0.7)
