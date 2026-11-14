"""La frontera estructural conserva comportamiento sin reabrir la aceptacion."""

from unittest.mock import patch

from django.apps import apps
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.directorio_unidades.contracts import TipoUnidad
from apps.plantas_piloto.manifiesto import MANIFIESTO
from apps.plantas_piloto.presentation import views


class EstructuraPlantasPilotoTests(SimpleTestCase):
    def test_app_instalada_descubre_su_plantilla_publica(self):
        config = apps.get_app_config("plantas_piloto")
        self.assertEqual(config.name, "apps.plantas_piloto")
        template = get_template("plantas_piloto/experiencia.html")
        self.assertIn("apps/plantas_piloto", template.origin.name.replace("\\", "/"))

    def test_manifiesto_conserva_las_capacidades_ya_aceptadas(self):
        self.assertEqual(MANIFIESTO.etapa, "presentacion")
        self.assertEqual(MANIFIESTO.app_django, "apps.plantas_piloto")
        self.assertEqual(
            MANIFIESTO.capacidades,
            (
                "catalogo_publico",
                "detalle_unidad",
                "planificacion_demanda",
                "gobierno_completitud",
                "repositorio_trazable",
            ),
        )
        self.assertEqual(MANIFIESTO.contratos, ("identidad_unidad_v1",))
        self.assertFalse(MANIFIESTO.migraciones)
        self.assertFalse(MANIFIESTO.administracion)

    def test_catalogo_pasa_por_el_adaptador_propio(self):
        request = object()
        with patch(
            "apps.plantas_piloto.infrastructure.unidades.catalogo_unidades"
        ) as heredado:
            self.assertIs(views.catalogo(request), heredado.return_value)
            heredado.assert_called_once_with(request, TipoUnidad.PLANTA_PILOTO)

    def test_detalle_pasa_por_el_adaptador_propio(self):
        request = object()
        with patch(
            "apps.plantas_piloto.infrastructure.unidades.detalle_unidad"
        ) as heredado:
            self.assertIs(
                views.detalle(request, "planta-prueba"),
                heredado.return_value,
            )
            heredado.assert_called_once_with(request, "planta-prueba")


class ExperienciaPublicaPlantasPilotoTests(TestCase):
    """El traslado de la plantilla conserva la superficie publica aceptada."""

    def test_el_catalogo_sigue_incluyendo_la_experiencia_de_la_vertical(self):
        response = self.client.get(reverse("plantas-piloto"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="experiencia-plantas-piloto"')
        self.assertContains(response, "data-unit-experience")
        self.assertContains(response, 'data-obs-step="5"')
        self.assertContains(response, "data-open-resource", count=5)
        self.assertContains(response, "data-obs-resource-dialog")
        self.assertContains(response, "data-obs-coverflow")
