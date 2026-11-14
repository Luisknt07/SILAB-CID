"""La frontera inicial conserva comportamiento sin adelantar el dominio."""

from unittest.mock import patch

from django.apps import apps
from django.template.loader import get_template
from django.test import SimpleTestCase

from apps.directorio_unidades.contracts import TipoUnidad
from apps.observatorios.manifiesto import MANIFIESTO
from apps.observatorios.presentation import views


class EstructuraObservatoriosTests(SimpleTestCase):
    def test_app_instalada_descubre_su_plantilla_publica(self):
        config = apps.get_app_config("observatorios")
        self.assertEqual(config.name, "apps.observatorios")
        template = get_template("observatorios/experiencia.html")
        self.assertIn("apps/observatorios", template.origin.name.replace("\\", "/"))

    def test_manifiesto_declara_solo_capacidades_existentes(self):
        self.assertEqual(MANIFIESTO.etapa, "presentacion")
        self.assertEqual(
            MANIFIESTO.capacidades,
            ("catalogo_publico", "detalle_unidad"),
        )
        self.assertEqual(MANIFIESTO.contratos, ("identidad_unidad_v1",))

    def test_catalogo_pasa_por_el_adaptador_propio(self):
        request = object()
        with patch(
            "apps.observatorios.infrastructure.unidades.catalogo_unidades"
        ) as heredado:
            self.assertIs(views.catalogo(request), heredado.return_value)
            heredado.assert_called_once_with(request, TipoUnidad.OBSERVATORIO)

    def test_detalle_pasa_por_el_adaptador_propio(self):
        request = object()
        with patch(
            "apps.observatorios.infrastructure.unidades.detalle_unidad"
        ) as heredado:
            self.assertIs(
                views.detalle(request, "observatorio-prueba"),
                heredado.return_value,
            )
            heredado.assert_called_once_with(request, "observatorio-prueba")
