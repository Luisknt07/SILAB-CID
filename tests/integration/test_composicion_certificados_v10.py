"""V10: institución centrada, marcas sobre sus nombres y paleta institucional."""

from importlib.util import find_spec
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase
from reportlab.graphics.barcode.qr import QrCodeWidget

from apps.formacion.presentation.certificados_diseno import DISENOS_V5, crear_diseno
from tests.integration import test_composicion_certificados_v9 as composicion_v9


class ComposicionCertificadoV10Tests(SimpleTestCase):
    def setUp(self):
        self.anterior = composicion_v9.ComposicionCertificadoV9Tests()
        self.anterior.setUp()
        self.addCleanup(self.anterior.doCleanups)

    def muestra(self, modelo="clasico", modo="claro", aliados=0, *, denso=False):
        certificado = self.anterior.muestra(modelo, modo, aliados, denso=denso)
        certificado.diseno_certificado.update(
            version=10, colaboradores_disposicion="logo_sobre_nombre"
        )
        for aliado in certificado.diseno_certificado["logos_aliados"]:
            aliado["posicion"] = "auto"
        if denso:
            certificado.diseno_certificado["logo_institucional"]["carrera"] = (
                "Carrera de Logística y Transporte para la gestión de cadenas de suministro y el desarrollo territorial "
                * 2
            )[:120]
        return certificado

    def renderizar(self, certificado, **kwargs):
        return self.anterior.renderizar(certificado, **kwargs)

    def crear(self, modelo, paleta, **valores):
        identidad = SimpleNamespace(
            nombre="Universidad Politécnica Estatal del Carchi",
            siglas="UPEC",
            paleta=paleta,
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
            return crear_diseno(
                self.anterior.base.certificado(),
                SimpleNamespace(diseno=modelo, **valores),
            )

    def comprobar_logos_sobre_nombres(self, pagina, diseno):
        import pymupdf

        cajas = [
            pymupdf.Rect(imagen["bbox"])
            for imagen in pagina.get_image_info()
            if imagen["bbox"][3] < pagina.rect.height / 2
        ]
        principal = max(cajas, key=lambda caja: caja.get_area())
        secundarias = [caja for caja in cajas if caja != principal]
        self.assertEqual(len(secundarias), len(diseno["logos_aliados"]))
        usadas = set()
        for aliado in diseno["logos_aliados"]:
            partes = pagina.search_for(aliado["nombre"])
            self.assertTrue(partes, aliado["nombre"])
            nombre = pymupdf.Rect(partes[0])
            for parte in partes[1:]:
                nombre |= parte
            candidatas = [
                caja
                for caja in secundarias
                if caja.y1 <= nombre.y0 and caja.x0 < nombre.x1 and caja.x1 > nombre.x0
            ]
            self.assertTrue(candidatas, (aliado["nombre"], nombre, secundarias))
            logo = max(candidatas, key=lambda caja: caja.y1)
            self.assertNotIn(tuple(logo), usadas)
            usadas.add(tuple(logo))
            self.assertFalse(logo.intersects(nombre))
            self.assertLess(logo.get_area(), principal.get_area())

    @staticmethod
    def comprobar_qr(pagina, url):
        import pymupdf

        enlaces = pagina.get_links()
        assert len(enlaces) == 1 and enlaces[0]["uri"] == url
        referencia = QrCodeWidget(url)
        referencia.qr.make()
        matriz = referencia.qr.modules
        pix = pagina.get_pixmap(
            matrix=pymupdf.Matrix(5, 5), clip=enlaces[0]["from"], alpha=False
        )
        dimension = len(matriz) + 8
        for r, fila in enumerate(matriz):
            for c, negro in enumerate(fila):
                x = round((c + 4.5) * pix.width / dimension)
                y = round((r + 4.5) * pix.height / dimension)
                assert (sum(pix.pixel(x, y)[:3]) < 384) == negro, (r, c)

    def test_snapshot_actual_congela_nueva_disposicion_sin_borrar_personalizaciones(
        self,
    ):
        diseno = self.crear(
            "sobrio",
            {},
            color_primario="#234567",
            color_acento="#E1B934",
            texto_aprobacion="Texto personalizado de {emisor}.",
            logo_1_nombre="Aliado registrado",
        )
        self.assertEqual(diseno["version"], 12)
        self.assertEqual(diseno["jerarquia_institucional"], "upec_principal")
        self.assertEqual(diseno["colaboradores_disposicion"], "logo_sobre_nombre")
        self.assertEqual(diseno["primario"], "#234567")
        self.assertEqual(diseno["acento"], "#E1B934")
        self.assertIn("Texto personalizado de Laboratorio docente.", diseno["texto"])
        self.assertEqual(diseno["logos_aliados"][0]["nombre"], "Aliado registrado")

    def test_colores_vacios_usan_identidad_y_respaldo_sin_heredar_paleta_azul_del_modelo(
        self,
    ):
        for modelo in ("clasico", "ia_particulas", "poligonos_digitales"):
            for paleta in ({}, {"primario": "", "acento": ""}):
                with self.subTest(modelo=modelo, paleta=paleta):
                    diseno = self.crear(
                        modelo, paleta, color_primario="", color_acento=""
                    )
                    self.assertEqual(diseno["primario"].upper(), "#006633")
                    self.assertEqual(diseno["acento"].upper(), "#FFCE00")
            institucional = self.crear(
                modelo, {"primario": "#125A38", "acento": "#F4BD28"}
            )
            self.assertEqual(institucional["primario"].upper(), "#125A38")
            self.assertEqual(institucional["acento"].upper(), "#F4BD28")
            parcial = self.crear(
                modelo,
                {"primario": "#125A38", "acento": "#F4BD28"},
                color_acento="#DBB344",
            )
            self.assertEqual(parcial["primario"].upper(), "#125A38")
            self.assertEqual(parcial["acento"], "#DBB344")

    @skipUnless(
        find_spec("pymupdf"), "La alineación se comprueba en el PDF renderizado."
    )
    def test_upec_sola_tiene_logo_y_cada_nivel_centrados(self):
        for modelo in ("clasico", "editorial", "ia_particulas"):
            for modo in ("claro", "oscuro"):
                with self.subTest(modelo=modelo, modo=modo):
                    cert = self.muestra(modelo, modo)
                    pagina = self.renderizar(cert)[0]
                    logos = [
                        i["bbox"]
                        for i in pagina.get_image_info()
                        if i["bbox"][3] < pagina.rect.height / 2
                    ]
                    self.assertEqual(len(logos), 1)
                    self.assertAlmostEqual(
                        (logos[0][0] + logos[0][2]) / 2,
                        pagina.rect.width / 2,
                        delta=0.75,
                    )
                    institucion = cert.diseno_certificado["logo_institucional"]
                    for campo in ("nombre", "unidad", "facultad", "carrera"):
                        cajas = pagina.search_for(institucion[campo])
                        self.assertTrue(cajas, campo)
                        for caja in cajas:
                            self.assertAlmostEqual(
                                (caja.x0 + caja.x1) / 2,
                                pagina.rect.width / 2,
                                delta=0.75,
                            )
                            self.assertGreater(caja.y0, logos[0][3])
                    self.assertNotIn("En colaboración con", pagina.get_text())
                    self.anterior.comprobar_geometria(pagina)
                    self.anterior.comprobar_contraste_cabecera(
                        pagina, cert.diseno_certificado
                    )

    @skipUnless(
        find_spec("pymupdf"), "Las tarjetas se comprueban en el PDF renderizado."
    )
    def test_uno_a_cuatro_colaboradores_muestran_marca_encima_del_nombre(self):
        for cantidad in range(1, 5):
            with self.subTest(aliados=cantidad):
                cert = self.muestra(aliados=cantidad)
                pagina = self.renderizar(cert)[0]
                self.assertEqual(pagina.get_text().count("En colaboración con"), 1)
                self.comprobar_logos_sobre_nombres(pagina, cert.diseno_certificado)
                self.anterior.comprobar_geometria(pagina)

    @skipUnless(find_spec("pymupdf"), "La densidad se comprueba en el PDF renderizado.")
    def test_16_modelos_claros_oscuros_con_4_nombres_largos_y_3_firmas_caben(self):
        for modelo in DISENOS_V5:
            for modo in ("claro", "oscuro"):
                with self.subTest(modelo=modelo, modo=modo):
                    cert = self.muestra(modelo, modo, 4, denso=True)
                    pagina = self.renderizar(cert)[0]
                    self.comprobar_logos_sobre_nombres(pagina, cert.diseno_certificado)
                    self.anterior.comprobar_geometria(pagina)
                    self.anterior.comprobar_contraste_cabecera(
                        pagina, cert.diseno_certificado
                    )
                    texto = " ".join(pagina.get_text().split())
                    self.assertIn("40,5", texto)
                    for i in range(3):
                        self.assertIn(f"Firmante {i + 1}", texto)
                    for campo in ("facultad", "carrera"):
                        self.assertGreaterEqual(
                            len(
                                pagina.search_for(
                                    cert.diseno_certificado["logo_institucional"][campo]
                                )
                            ),
                            2,
                        )
                    self.comprobar_qr(
                        pagina, cert.diseno_certificado["verificacion_url"]
                    )

    @skipUnless(
        find_spec("pymupdf"), "Los colaboradores sin imagen conservan sus nombres."
    )
    def test_colaboracion_solo_texto_no_inventa_marcas_y_conserva_nombres(self):
        cert = self.muestra(aliados=4)
        for aliado in cert.diseno_certificado["logos_aliados"]:
            aliado["imagen"] = ""
        pagina = self.renderizar(cert)[0]
        logos = [
            i for i in pagina.get_image_info() if i["bbox"][3] < pagina.rect.height / 2
        ]
        self.assertEqual(len(logos), 1)
        for aliado in cert.diseno_certificado["logos_aliados"]:
            self.assertEqual(pagina.get_text().count(aliado["nombre"]), 1)
        self.anterior.comprobar_geometria(pagina)

    @skipUnless(
        find_spec("pymupdf"), "La verificación pública preserva la nueva composición."
    )
    def test_salida_publica_oculta_documento_y_preserva_qr_y_colaboracion(self):
        cert = self.muestra("sobrio", "oscuro", 4, denso=True)
        pagina = self.renderizar(cert, mostrar_documento=False)[0]
        self.assertNotIn(cert.documento, pagina.get_text())
        self.assertIn("En colaboración con", pagina.get_text())
        self.comprobar_logos_sobre_nombres(pagina, cert.diseno_certificado)
        self.anterior.comprobar_geometria(pagina)
        self.comprobar_qr(pagina, cert.diseno_certificado["verificacion_url"])
