"""Las escenas públicas no abren partidas ni exponen datos de prueba o participantes."""

from datetime import date
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.partidas_simulador import PartidaSimulador
from apps.directorio_unidades.models.core import Unidad
from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA


class SimuladoresVistasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre="Logística",
            slug=SLUG_LOGISTICA,
            dependencia="laboratorios",
            fecha_inicio=date(2026, 1, 1),
        )

    def test_escenas_publicas_de_los_seis_casos_sin_mutaciones(self):
        from apps.laboratorios.operacion.presentation.logistica_operaciones_motor import CASOS

        for caso in CASOS:
            with (
                self.subTest(caso=caso),
                CaptureQueriesContext(connection) as consultas,
            ):
                response = self.client.get(
                    reverse("logistica_operaciones", args=[SLUG_LOGISTICA]),
                    {"caso": caso},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["caso_inicial"], caso)
                self.assertEqual(response.context["datos_iniciales"]["caso"], caso)
                self.assertContains(response, "logistica_operaciones.js")
                self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
                self.assertEqual(response["Cache-Control"], "private, no-store")
                self.assertFalse(
                    any(
                        q["sql"]
                        .lstrip()
                        .upper()
                        .startswith(("UPDATE", "INSERT", "DELETE"))
                        for q in consultas
                    )
                )
                self.assertFalse(
                    any(
                        "webcitt_partidasimulador" in q["sql"]
                        or "webcitt_equipo" in q["sql"]
                        for q in consultas
                    )
                )
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_preview_ia_oculta_prueba_y_pallets_ocultan_defectos(self):
        url = reverse("logistica_operaciones", args=[SLUG_LOGISTICA])
        response = self.client.get(url, {"caso": "ia-pronostico"})
        self.assertEqual(
            len(response.context["datos_iniciales"]["estado"]["datos"]["serie"]), 48
        )
        response = self.client.get(url)
        self.assertTrue(
            all(
                "dano" not in p
                for p in response.context["datos_iniciales"]["estado"]["datos"][
                    "pallets"
                ]
            )
        )

    def test_sala_publica_tiene_guia_y_casos_sin_crear_partida(self):
        response = self.client.get(
            reverse("logistica_cerveza_multijugador", args=[SLUG_LOGISTICA])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "logistica_cerveza_multi.js")
        self.assertContains(response, "Datos sintéticos")
        self.assertContains(response, 'data-auth="false"')
        self.assertEqual(len(response.context["catalogo_cerveza"]["casos"]), 3)
        self.assertEqual(PartidaSimulador.objects.count(), 0)

    def test_ocultar_seccion_impide_escenas_y_salas(self):
        AjusteSeccionPlanta.objects.create(
            unidad=self.unidad, numero="4.4", oculta=True
        )
        for nombre in ("logistica_operaciones", "logistica_cerveza_multijugador"):
            self.assertEqual(
                self.client.get(reverse(nombre, args=[SLUG_LOGISTICA])).status_code, 404
            )

    def test_menu_publico_solo_ofrece_catalogo_y_sala_sin_leer_sus_partidas(self):
        with CaptureQueriesContext(connection) as consultas:
            response = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(
            response, reverse("logistica_operaciones", args=[SLUG_LOGISTICA])
        )
        self.assertContains(
            response, reverse("logistica_cerveza_multijugador", args=[SLUG_LOGISTICA])
        )
        self.assertFalse(any("webcitt_partidasimulador" in q["sql"] for q in consultas))
