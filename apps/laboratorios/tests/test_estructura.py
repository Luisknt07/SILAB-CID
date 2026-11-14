"""La frontera estructural conserva comportamiento sin reabrir la aceptacion."""

from unittest.mock import patch

from django.apps import apps
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.directorio_unidades.contracts import TipoUnidad
from apps.laboratorios.manifiesto import MANIFIESTO
from apps.laboratorios.presentation import views


class EstructuraLaboratoriosTests(SimpleTestCase):
    def test_app_instalada_descubre_su_plantilla_publica(self):
        config = apps.get_app_config("laboratorios")
        self.assertEqual(config.name, "apps.laboratorios")
        template = get_template("laboratorios/experiencia.html")
        self.assertIn("apps/laboratorios", template.origin.name.replace("\\", "/"))

    def test_manifiesto_declara_solo_capacidades_existentes(self):
        self.assertEqual(MANIFIESTO.etapa, "presentacion")
        self.assertEqual(MANIFIESTO.app_django, "apps.laboratorios")
        self.assertEqual(
            MANIFIESTO.capacidades,
            ("catalogo_publico", "detalle_unidad"),
        )
        self.assertEqual(MANIFIESTO.contratos, ("identidad_unidad_v1",))
        self.assertFalse(MANIFIESTO.migraciones)
        self.assertFalse(MANIFIESTO.administracion)

    def test_catalogo_pasa_por_el_adaptador_propio(self):
        request = object()
        with patch(
            "apps.laboratorios.infrastructure.unidades.catalogo_unidades"
        ) as heredado:
            self.assertIs(views.catalogo(request), heredado.return_value)
            heredado.assert_called_once_with(request, TipoUnidad.LABORATORIO)

    def test_detalle_pasa_por_el_adaptador_propio(self):
        request = object()
        with patch(
            "apps.laboratorios.infrastructure.unidades.detalle_unidad"
        ) as heredado:
            self.assertIs(
                views.detalle(request, "laboratorio-prueba"),
                heredado.return_value,
            )
            heredado.assert_called_once_with(request, "laboratorio-prueba")


class ExperienciaPublicaLaboratoriosTests(TestCase):
    """El traslado de la plantilla conserva la superficie publica aceptada."""

    def test_el_catalogo_sigue_incluyendo_la_experiencia_de_la_vertical(self):
        response = self.client.get(reverse("hublab"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="experiencia-laboratorios"')
        self.assertContains(response, "data-unit-experience")
        self.assertContains(response, 'data-obs-step="5"')
        self.assertContains(response, "data-open-resource", count=6)
        self.assertContains(response, "data-obs-resource-dialog")
        self.assertContains(response, "data-obs-coverflow")
