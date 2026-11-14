"""Fondos tecnológicos V5 autocontenidos, sin base de datos ni recursos externos."""

import base64
from importlib.util import find_spec
from io import BytesIO
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from PIL import Image

from apps.formacion.presentation.certificados_diseno import DISENOS_NUEVOS_V5, DISENOS_V5, _fondo_original_v5, _imagen_encuadrada_v5, _imagen_fondo_v5, crear_diseno, dibujar_certificado
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso, IMAGENES_CERTIFICADO
from tests.integration import test_composicion_certificados as fixtures


class ComposicionCertificadoV5Tests(SimpleTestCase):
    def setUp(self):
        self.base = fixtures.ComposicionCertificadoTests()
        self.identidad = SimpleNamespace(
            nombre="Universidad de muestra", siglas="UM", paleta={}
        )

    def crear(self, config, cert=None):
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

    def test_dieciséis_disenos_y_paleta_por_defecto_solo_si_no_hay_colores_explicitos(
        self,
    ):
        choices = dict(ConfiguracionCertificadoCurso._meta.get_field("diseno").choices)
        self.assertEqual(len(DISENOS_V5), 16)
        self.assertEqual(set(choices), set(DISENOS_V5) | {"formacion_lateral"})
        for modelo in DISENOS_NUEVOS_V5:
            d = self.crear(SimpleNamespace(diseno=modelo))
            self.assertEqual(d["version"], 12)
            self.assertEqual(d["diseno"], modelo)
            self.assertEqual(d["primario"].upper(), "#006633")
            self.assertEqual(d["acento"].upper(), "#FFCE00")
            elegido = self.crear(
                SimpleNamespace(
                    diseno=modelo, color_primario="#713958", color_acento="#E0B54A"
                )
            )
            self.assertEqual(elegido["primario"], "#713958")
            self.assertEqual(elegido["acento"], "#E0B54A")

    def test_tema_automatico_y_preferencias_resueltas_quedan_congelados(self):
        cert = self.base.certificado()
        cert.curso_nombre = "Producción agropecuaria sostenible"
        auto = self.crear(SimpleNamespace(diseno="clasico"), cert)
        self.assertEqual(auto["tema_fondo"], "sostenibilidad")
        manual = self.crear(
            SimpleNamespace(
                diseno="ia_particulas",
                tema_fondo="robotica",
                modo_fondo="claro",
                intensidad_fondo="alta",
                encuadre_fondo="superior",
            )
        )
        self.assertEqual(manual["tema_fondo"], "robotica")
        self.assertEqual(manual["modo_fondo"], "claro")
        self.assertEqual(manual["intensidad_fondo"], "alta")
        self.assertEqual(manual["encuadre_fondo"], "superior")
        self.assertEqual(
            manual["preferencias_fondo"],
            dict(tema="robotica", modo="claro", intensidad="alta"),
        )
        self.assertEqual(
            self.crear(SimpleNamespace(diseno="ia_particulas"))["modo_fondo"], "claro"
        )
        self.assertEqual(
            self.crear(SimpleNamespace(diseno="red_cientifica"))["modo_fondo"], "claro"
        )

    def test_imagen_de_fondo_es_autocontenida_limitada_y_sin_transparencia_ambigua(
        self,
    ):
        salida = BytesIO()
        Image.new("RGBA", (2200, 1500), (20, 80, 200, 90)).save(salida, "PNG")
        origen = ContentFile(salida.getvalue(), name="fondo.png")
        d = self.crear(
            SimpleNamespace(diseno="ondas_tecnologicas", imagen_fondo=origen)
        )
        with Image.open(BytesIO(base64.b64decode(d["imagen_fondo"]))) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.mode, "RGB")
            self.assertLessEqual(img.width, 1600)
            self.assertLessEqual(img.height, 1200)
        self.assertEqual(_imagen_fondo_v5(None), "")
        self.assertNotIn("fondo.png", d["imagen_fondo"])

    def test_formulario_fondo_y_eliminacion_comparten_validacion_de_imagenes(self):
        form = ConfiguracionCertificadoForm()
        grupos = {
            g["clave"]: [b.name for b in g["campos"]] for g in form.secciones_editor
        }
        self.assertEqual(
            grupos["fondo"],
            [
                "tema_fondo",
                "intensidad_fondo",
                "imagen_fondo",
                "encuadre_fondo",
                "quitar_imagen_fondo",
                "mostrar_pie_tecnologico",
                "estilo_pie_tecnologico",
            ],
        )
        self.assertIn("imagen_fondo", IMAGENES_CERTIFICADO)
        self.assertEqual(
            form.fields["imagen_fondo"].widget.attrs["accept"], "image/png,image/jpeg"
        )
        data = BytesIO()
        Image.new("RGB", (2000, 1600), "blue").save(data, "PNG")
        archivo = SimpleUploadedFile(
            "fondo.png", data.getvalue(), content_type="image/png"
        )
        form = ConfiguracionCertificadoForm(files={"imagen_fondo": archivo})
        form.cleaned_data = {"imagen_fondo": form.fields["imagen_fondo"].clean(archivo)}
        normalizado = form._normalizar_imagen("imagen_fondo")
        with Image.open(normalizado) as img:
            self.assertLessEqual(img.width, 1600)
            self.assertLessEqual(img.height, 1200)
        form.cleaned_data["quitar_imagen_fondo"] = True
        with self.assertRaisesMessage(ValidationError, "no ambas opciones"):
            form._normalizar_imagen("imagen_fondo")
        form = ConfiguracionCertificadoForm()
        form.cleaned_data = {"imagen_fondo": False, "quitar_imagen_fondo": True}
        self.assertIs(form._normalizar_imagen("imagen_fondo"), False)

    def test_encuadre_cubre_sin_deformar_y_respeta_el_lado_elegido(self):
        for size, encuadres in [
            (
                (300, 100),
                {"izquierda": (0, 0), "centro": (-100, 0), "derecha": (-200, 0)},
            ),
            (
                (100, 300),
                {"superior": (0, -200), "centro": (0, -100), "inferior": (0, 0)},
            ),
        ]:
            out = BytesIO()
            Image.new("RGB", size, "blue").save(out, "PNG")
            for encuadre, coordenadas in encuadres.items():
                canvas = Mock()
                _imagen_encuadrada_v5(
                    canvas,
                    base64.b64encode(out.getvalue()).decode(),
                    (0, 0, 100, 100),
                    encuadre,
                )
                args = canvas.drawImage.call_args
                self.assertEqual(args.args[1:3], coordenadas)
                self.assertAlmostEqual(
                    args.kwargs["width"] / args.kwargs["height"], size[0] / size[1]
                )
                canvas.clipPath.assert_called_once()

    def test_fondo_personalizado_no_se_descarta_en_los_doce_modelos_previos(self):
        self.assertTrue(
            _fondo_original_v5(
                {
                    "preferencias_fondo": {"tema": "auto", "modo": "auto"},
                    "intensidad_fondo": "media",
                },
                "clasico",
            )
        )
        for ajustes in (
            {"tema": "redes", "modo": "auto"},
            {"tema": "auto", "modo": "oscuro"},
        ):
            self.assertFalse(
                _fondo_original_v5({"preferencias_fondo": ajustes}, "clasico")
            )
        self.assertFalse(_fondo_original_v5({"imagen_fondo": "foto"}, "clasico"))
        self.assertFalse(_fondo_original_v5({"intensidad_fondo": "alta"}, "clasico"))
        for version in (1, 2, 3, 4):
            cert = self.base.certificado()
            cert.diseno_certificado = self.base.diseno()
            cert.diseno_certificado["version"] = version
            with patch(
                "apps.formacion.presentation.certificados_diseno._dibujar_certificado_v"
                + str(version)
                if version > 1
                else "apps.formacion.presentation.certificados_diseno._dibujar_certificado_v1",
                return_value=b"historico",
            ) as renderer:
                self.assertEqual(dibujar_certificado(cert), b"historico")
                renderer.assert_called_once()

    @skipUnless(find_spec("pymupdf"), "Geometría PDF disponible con PyMuPDF.")
    def test_cuatro_nuevos_modelos_claros_oscuros_tres_formatos_densos_sin_solapamientos(
        self,
    ):
        import pymupdf

        for modelo in DISENOS_NUEVOS_V5:
            for modo in ("claro", "oscuro"):
                for formato in ("breve", "institucional", "competencias"):
                    with self.subTest(modelo=modelo, modo=modo, formato=formato):
                        cert = self.base.certificado()
                        cert.nombre = (
                            "María Fernanda Participante de nombre y apellidos compuestos "
                            * 4
                        )[:200]
                        d = self.base.diseno(modelo, 4, 3)
                        d.update(
                            version=5,
                            modo_fondo=modo,
                            tema_fondo="ia_datos"
                            if modelo == "ia_particulas"
                            else "redes",
                            intensidad_fondo="alta",
                            preferencias_fondo={"tema": "redes", "modo": modo},
                            formato_contenido=formato,
                            primario="#164B72",
                            acento="#38B9CF",
                            subtitulo="Formación aplicada e innovación tecnológica",
                            competencias=[
                                (
                                    "Diseña aplicaciones y valida resultados para mejorar decisiones operativas. "
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
                            + " La actividad se desarrolló del 12 al 23 de octubre de 2026, con una duración de40,5 horas."
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
                            side_effect=AssertionError(
                                "Snapshot sin consultas a identidad"
                            ),
                        ):
                            doc = pymupdf.open(
                                stream=dibujar_certificado(cert), filetype="pdf"
                            )
                        self.assertEqual(len(doc), 1)
                        pagina = doc[0]
                        texto = " ".join(pagina.get_text().split())
                        self.assertIn(
                            "12 al 23 de octubre de2026".replace("de2026", "de 2026"),
                            texto,
                        )
                        self.assertNotIn("Calificación", texto)
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
