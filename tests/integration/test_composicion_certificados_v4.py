"""Nuevas composiciones autocontenidas: doce diseños y formatos reales, sin base de datos."""

import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from importlib.util import find_spec
from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from PIL import Image

from apps.formacion.presentation.certificados_diseno import DISENOS_V4, _logo_institucional_claro_v4, _logos_v4, crear_diseno, dibujar_certificado, _foto_certificado_v4
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from tests.integration import test_composicion_certificados as fixtures


class ComposicionCertificadoV4Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoTests()
        self.identidad = SimpleNamespace(
            nombre="Universidad de muestra", siglas="UM", paleta={}
        )

    def crear(self, configuracion):
        with (
            patch(
                "apps.core.presentation.identidad.identidad_actual",
                return_value=(None, self.identidad),
            ),
            patch(
                "apps.core.presentation.identidad.logo_institucional", return_value=None
            ),
        ):
            return crear_diseno(self.base.certificado(), configuracion)

    def test_doce_modelos_y_nuevas_opciones_quedan_congeladas(self):
        self.assertEqual(len(DISENOS_V4), 12)
        for modelo in DISENOS_V4:
            d = self.crear(
                SimpleNamespace(
                    diseno=modelo,
                    alineacion_contenido="izquierda",
                    formato_contenido="competencias",
                    subtitulo="Actualización profesional",
                    competencias="Gestiona inventarios\nAnaliza datos",
                )
            )
            self.assertEqual(d["version"], 12)
            self.assertEqual(d["diseno"], modelo)
            self.assertEqual(
                d["competencias"], ["Gestiona inventarios", "Analiza datos"]
            )
            self.assertEqual(d["alineacion_contenido"], "izquierda")
            self.assertEqual(d["formato_contenido"], "competencias")
            self.assertFalse(d["mostrar_nota"])

    def test_foto_propia_prevalece_y_foto_unidad_es_optativa_y_autocontenida(self):
        subida = ContentFile(base64.b64decode(self.base.imagen()), name="foto.png")
        foto_unidad = ContentFile(
            base64.b64decode(self.base.imagen()), name="unidad.png"
        )
        curso = SimpleNamespace(unidad=SimpleNamespace(imagen=foto_unidad))
        d = self.crear(
            SimpleNamespace(curso=curso, foto_alusiva=subida, usar_foto_unidad=True)
        )
        self.assertEqual(d["origen_foto"], "personalizada")
        self.assertEqual(d["foto"], _foto_certificado_v4(subida))
        d = self.crear(SimpleNamespace(curso=curso, usar_foto_unidad=True))
        self.assertEqual(d["origen_foto"], "unidad")
        self.assertTrue(d["foto"])
        cert = self.base.certificado()
        cert.curso_origen = curso
        with (
            patch(
                "apps.core.presentation.identidad.identidad_actual",
                return_value=(None, self.identidad),
            ),
            patch(
                "apps.core.presentation.identidad.logo_institucional", return_value=None
            ),
        ):
            externo = crear_diseno(cert, SimpleNamespace(usar_foto_unidad=True))
        self.assertEqual(externo["origen_foto"], "unidad")
        d = self.crear(SimpleNamespace(curso=curso, usar_foto_unidad=False))
        self.assertEqual(d["foto"], "")
        self.assertEqual(d["origen_foto"], "")

    def test_logos_subidos_no_tienen_placas_ni_modificaciones(self):
        logo = self.base.imagen()
        canvas = Mock()
        canvas.rect.side_effect = AssertionError("Un logo no lleva fondo añadido")
        canvas.roundRect.side_effect = AssertionError("Un logo no lleva contenedor")
        datos = {"logos": [{"imagen": logo, "posicion": "auto"}]}
        _logos_v4(canvas, datos, 60, 500, 700, 45, False)
        self.assertEqual(datos["logos"][0]["imagen"], logo)
        self.assertEqual(canvas.drawImage.call_args.kwargs["mask"], "auto")
        self.assertTrue(canvas.drawImage.call_args.kwargs["preserveAspectRatio"])

    def test_adaptacion_blanco_institucional_conserva_alpha_y_colores_del_emblema(self):
        original = Image.new("RGBA", (3, 1), (255, 255, 255, 0))
        original.putpixel((1, 0), (255, 255, 255, 180))
        original.putpixel((2, 0), (220, 171, 51, 255))
        out = BytesIO()
        original.save(out, "PNG")
        b64 = base64.b64encode(out.getvalue()).decode()
        adaptada = Image.open(
            BytesIO(base64.b64decode(_logo_institucional_claro_v4(b64, "#1E5A3D")))
        )
        self.assertEqual(adaptada.getpixel((0, 0))[3], 0)
        self.assertEqual(adaptada.getpixel((1, 0)), (30, 90, 61, 180))
        self.assertEqual(adaptada.getpixel((2, 0)), original.getpixel((2, 0)))
        opaca = Image.new("RGB", (3, 1), "white")
        buffer = BytesIO()
        opaca.save(buffer, "PNG")
        cadena = base64.b64encode(buffer.getvalue()).decode()
        self.assertEqual(_logo_institucional_claro_v4(cadena, "#1E5A3D"), cadena)

    def test_campos_nuevos_y_validacion_de_competencias(self):
        form = ConfiguracionCertificadoForm()
        grupos = {
            g["clave"]: [b.name for b in g["campos"]] for g in form.secciones_editor
        }
        self.assertIn("alineacion_contenido", grupos["diseno"])
        self.assertIn("quitar_foto_alusiva", grupos["fotografia"])
        self.assertEqual(
            form.fields["foto_alusiva"].widget.attrs["accept"], "image/png,image/jpeg"
        )
        for texto in ("", "\n".join("Competencia" for _ in range(7))):
            config = ConfiguracionCertificadoCurso(
                formato_contenido="competencias", competencias=texto
            )
            with self.assertRaises(ValidationError):
                config.clean()

    @skipUnless(find_spec("pymupdf"), "Geometría PDF disponible con PyMuPDF.")
    def test_doce_diseno_densos_con_tres_formatos_y_qr_separado(self):
        import pymupdf

        for modelo in DISENOS_V4:
            for formato in ("breve", "institucional", "competencias"):
                with self.subTest(diseno=modelo, formato=formato):
                    cert = self.base.certificado()
                    cert.nombre = (
                        "María Fernanda Participante de nombre y apellidos compuestos "
                        * 4
                    )[:200]
                    d = self.base.diseno(modelo, 4, 3)
                    d.update(
                        version=4,
                        formato_contenido=formato,
                        alineacion_contenido="centro",
                        subtitulo="Formación aplicada a los procesos de la logística y la cadena de suministro",
                        competencias=[
                            (
                                "Diseña y valida aplicaciones de inteligencia artificial para gestionar inventarios y mejorar decisiones operativas. "
                                * 2
                            )[:99]
                            for _ in range(6)
                        ],
                    )
                    d["texto"] = (
                        (
                            "Participó en el encuentro de actualización profesional sobre aplicaciones de inteligencia artificial para logística, transporte y cadena de suministro; desarrolló actividades guiadas de análisis, simulación, diseño de soluciones y validación de resultados. "
                            * 3
                        )[:700]
                        + " La actividad se desarrolló del 12 al 23 de octubre de 2026, con una duración de 40,5 horas."
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
                    with patch(
                        "apps.core.presentation.identidad.identidad_actual",
                        side_effect=AssertionError("Snapshot congelado"),
                    ):
                        pdf = dibujar_certificado(cert)
                    doc = pymupdf.open(stream=pdf, filetype="pdf")
                    self.assertEqual(len(doc), 1)
                    pagina = doc[0]
                    texto = " ".join(pagina.get_text().split())
                    for dato in (
                        "12 al 23 de octubre de 2026",
                        "40,5 horas",
                        "Emisión: 9 de octubre de 2026",
                    ):
                        self.assertIn(dato, texto)
                    self.assertEqual(
                        "COMPETENCIAS Y LOGROS" in texto, formato == "competencias"
                    )
                    self.assertEqual(
                        "RECONOCIMIENTO DE LA ACTIVIDAD" in texto,
                        formato == "institucional",
                    )
                    self.assertEqual(
                        pagina.get_links()[0]["uri"], d["verificacion_url"]
                    )
                    qr = pagina.get_links()[0]["from"]
                    for bloque in pagina.get_text("dict")["blocks"]:
                        for linea in bloque.get("lines", []):
                            caja = pymupdf.Rect(linea["bbox"])
                            self.assertTrue(pagina.rect.contains(caja))
                            self.assertFalse(caja.intersects(qr))
                    publico = pymupdf.open(
                        stream=dibujar_certificado(cert, False), filetype="pdf"
                    )
                    self.assertNotIn(cert.documento, publico[0].get_text())
