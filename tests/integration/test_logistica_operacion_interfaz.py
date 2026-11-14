"""Presentación y navegación del seguimiento presencial, sin datos operativos."""

from datetime import date, time
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class Documento(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elementos = []

    def handle_starttag(self, tag, attrs):
        self.elementos.append((tag, dict(attrs)))


class OperacionLogisticaInterfazTests(SimpleTestCase):
    plantilla = "portal/pages/unidades/logistica/operacion.html"

    def contexto(self, *, seleccionado=False):
        contexto = {
            "unidad": SimpleNamespace(nombre="Laboratorio de prueba"),
            "caso": "cd-falla",
            "semilla": 0,
            "volver_url": "/virtual/guia/?caso=cd-falla&semilla=0",
            "simulador_url": "/virtual/3d/?caso=cd-falla&semilla=0",
            "guia_virtual": {"titulo": "Ensayo educativo"},
            "adaptar_url": "/institucional/guia/nueva/",
            "actividad": SimpleNamespace(
                pk=7,
                id=7,
                nombre="Actividad real",
                responsable="Responsable",
                codigo="ACT-7",
            ),
            "actividades": [
                {
                    "id": 7,
                    "nombre": "Actividad real",
                    "codigo": "ACT-7",
                    "responsable": "Responsable",
                    "url": "?actividad=7&caso=cd-falla&semilla=0",
                }
            ],
            "q": "",
            "pagina": SimpleNamespace(
                paginator=SimpleNamespace(num_pages=3),
                number=2,
                has_previous=True,
                previous_page_number=1,
                has_next=True,
                next_page_number=3,
            ),
            "guias": [
                {
                    "id": 12,
                    "titulo": "Borrador reciente",
                    "version": 4,
                    "estado": "revision",
                    "estado_label": "Pendiente de revisión",
                    "url": "/institucional/guia/12/",
                }
            ],
            "guia_publicada": {
                "id": 9,
                "titulo": "Guía publicada anterior",
                "version": 1,
                "url": "/institucional/guia/9/",
            },
            "planes": [
                {
                    "id": 32,
                    "codigo": "PL-26-0032",
                    "tema": "Recepción y picking",
                    "fecha": date(2026, 10, 12),
                    "hora_inicio": time(8),
                    "hora_fin": time(10),
                    "estado": "aprobada",
                    "estado_label": "Aprobada",
                    "url": "/institucional/plan/32/",
                    "ejecucion_url": "/institucional/ejecucion/32/",
                    "reserva_codigo": "RES-32",
                    "reserva_estado_label": "Confirmada",
                    "ejecucion_estado_label": "Pendiente de revisión",
                    "seleccion_url": "?actividad=7&plan=32&caso=cd-falla&semilla=0#expediente",
                    "seleccionado": seleccionado,
                }
            ],
            "controles": [
                {
                    "id": "guia",
                    "titulo": "Guía institucional",
                    "detalle": "Este expediente no requiere guía.",
                    "estado": "no_aplica",
                },
                {
                    "id": "reserva",
                    "titulo": "Reserva",
                    "detalle": "Revisar la reserva vinculada.",
                    "estado": "observado",
                },
            ],
            "enlaces": [
                {
                    "url": "/institucional/gestion/?view=reportes",
                    "titulo": "Reportes institucionales",
                    "descripcion": "Consultar con autorización",
                }
            ],
            "indicadores": [],
            "avisos": [],
            "plan_seleccionado": 32 if seleccionado else None,
            "expediente": None,
        }
        if seleccionado:
            contexto["expediente"] = {
                "id": 32,
                "codigo": "PL-26-0032",
                "tema": "Recepción y picking",
                "fecha": date(2026, 10, 12),
                "hora_inicio": time(8),
                "hora_fin": time(10),
                "estado": "aprobada",
                "estado_label": "Aprobada",
                "vigente": True,
                "url": "/institucional/plan/32/",
                "ejecucion_url": "",
                "guia": {
                    "titulo": "Guía vinculada",
                    "version": 1,
                    "estado_label": "Aprobada y publicada",
                    "url": "/institucional/guia/9/",
                },
                "reserva": {
                    "codigo": "RES-32",
                    "estado": "confirmada",
                    "estado_label": "Confirmada",
                    "resultado_label": "",
                },
                "ejecucion": {
                    "estado": "revision",
                    "estado_label": "Pendiente de revisión",
                    "resultado": "cancelada",
                    "resultado_label": "Cancelada",
                    "fecha": date(2026, 10, 12),
                    "asistentes": 0,
                    "efectiva": False,
                    "incidente": False,
                },
                "evidencias_total": 2,
                "evidencias": [
                    {"titulo": "Bitácora", "total": 1},
                    {"titulo": "Informe", "total": 1},
                ],
                "proxima_accion": {
                    "titulo": "Revisar FT03",
                    "detalle": "Consultar el cierre pendiente de revisión.",
                    "url": "/institucional/plan/32/",
                    "target_top": True,
                },
            }
        return contexto

    def renderizar(self, contexto):
        html = render_to_string(self.plantilla, contexto)
        documento = Documento()
        documento.feed(html)
        return html, documento.elementos

    def test_estado_vacio_no_simula_seguimiento_y_guia_publicada_sigue_visible(self):
        html, elementos = self.renderizar(self.contexto())
        self.assertIn("Selecciona una planificación para continuar", html)
        self.assertIn("Guía publicada anterior", html)
        self.assertIn("Borrador reciente", html)
        self.assertIn("Pendiente de revisión", html)
        self.assertNotIn("Siguiente acción documental", html)
        self.assertFalse(
            any(
                tag == "input" and attrs.get("name") == "plan"
                for tag, attrs in elementos
            )
        )

    def test_expediente_muestra_estados_resultado_real_evidencias_y_cero_asistentes(
        self,
    ):
        html, _ = self.renderizar(self.contexto(seleccionado=True))
        self.assertIn("Revisar FT03", html)
        self.assertIn("Cancelada", html)
        self.assertIn("Asistentes registrados</dt><dd>0</dd>", html)
        self.assertIn("Uso efectivo en reportes</dt><dd>No</dd>", html)
        self.assertIn("No aplica", html)
        self.assertIn("Requiere revisión", html)
        self.assertIn("Bitácora", html)
        self.assertIn("Informe", html)
        self.assertIn("12/10/2026", html)
        self.assertIn("08:00–10:00", html)

    def test_ids_anclas_etiquetas_y_aria_apuntan_a_elementos_unicos(self):
        for seleccionado in (False, True):
            with self.subTest(seleccionado=seleccionado):
                _, elementos = self.renderizar(self.contexto(seleccionado=seleccionado))
                ids = [attrs["id"] for _, attrs in elementos if "id" in attrs]
                self.assertEqual(len(ids), len(set(ids)))
                for tag, attrs in elementos:
                    if tag == "a" and attrs.get("href", "").startswith("#"):
                        self.assertIn(attrs["href"][1:], ids)
                    if tag == "label" and attrs.get("for"):
                        self.assertIn(attrs["for"], ids)
                    for referencia in attrs.get("aria-labelledby", "").split():
                        self.assertIn(referencia, ids)

    def test_busqueda_y_paginacion_conservan_plan_pero_cambio_actividad_lo_descarta(
        self,
    ):
        _, elementos = self.renderizar(self.contexto(seleccionado=True))
        ocultos = {
            attrs.get("name"): attrs.get("value")
            for tag, attrs in elementos
            if tag == "input" and attrs.get("type") == "hidden"
        }
        self.assertEqual(
            ocultos,
            {"caso": "cd-falla", "semilla": "0", "actividad": "7", "plan": "32"},
        )
        busqueda = next(
            attrs
            for tag, attrs in elementos
            if tag == "input" and attrs.get("name") == "q"
        )
        self.assertEqual(busqueda["maxlength"], "100")
        enlaces = [attrs.get("href", "") for tag, attrs in elementos if tag == "a"]
        paginas = [url for url in enlaces if "page=" in url]
        self.assertEqual(len(paginas), 2)
        self.assertTrue(all("plan=32" in url and "semilla=0" in url for url in paginas))
        self.assertIn("?actividad=7&caso=cd-falla&semilla=0", enlaces)

    def test_operacion_institucional_sale_del_iframe_y_navegacion_virtual_permanece(
        self,
    ):
        _, elementos = self.renderizar(self.contexto(seleccionado=True))
        institucionales = [
            attrs
            for tag, attrs in elementos
            if tag == "a" and attrs.get("href", "").startswith("/institucional/")
        ]
        self.assertGreaterEqual(len(institucionales), 6)
        self.assertTrue(all(attrs.get("target") == "_top" for attrs in institucionales))
        virtuales = [
            attrs
            for tag, attrs in elementos
            if tag == "a" and attrs.get("href", "").startswith("/virtual/")
        ]
        self.assertEqual(len(virtuales), 2)
        self.assertTrue(all("target" not in attrs for attrs in virtuales))
        local = next(
            attrs
            for tag, attrs in elementos
            if tag == "a" and attrs.get("aria-current") == "true"
        )
        self.assertNotIn("target", local)
        self.assertTrue(local["href"].endswith("#expediente"))

    def test_contenido_y_busqueda_no_introducen_html_ejecutable(self):
        contexto = self.contexto(seleccionado=True)
        ataque = '<img src=x onerror="alert(1)">'
        contexto["q"] = ataque
        contexto["expediente"]["tema"] = ataque
        contexto["expediente"]["proxima_accion"]["detalle"] = ataque
        contexto["expediente"]["evidencias"][0]["titulo"] = ataque
        html, elementos = self.renderizar(contexto)
        self.assertNotIn(ataque, html)
        self.assertIn("&lt;img", html)
        self.assertFalse(
            any(tag == "img" and "onerror" in attrs for tag, attrs in elementos)
        )
