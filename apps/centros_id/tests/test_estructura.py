"""La app posee su portada, su dominio, su administracion y sus migraciones."""

from django.apps import apps
from django.template.loader import get_template
from django.test import SimpleTestCase

from apps.centros_id.manifiesto import MANIFIESTO
from apps.centros_id.presentation.views import CentrosIDView


class EstructuraCentrosIDTests(SimpleTestCase):
    def test_app_instalada_descubre_su_portada(self):
        config = apps.get_app_config("centros_id")
        self.assertEqual(config.name, "apps.centros_id")
        template = get_template("centros_id/portada.html")
        self.assertIn("apps/centros_id", template.origin.name.replace("\\", "/"))

    def test_manifiesto_declara_lo_que_la_app_ya_posee(self):
        self.assertEqual(MANIFIESTO.etapa, "propio")
        self.assertEqual(MANIFIESTO.dependencias, ("core",))
        # El directorio enlaza las unidades articuladas si esta en el despliegue; no es una dependencia.
        self.assertEqual(MANIFIESTO.integraciones_opcionales, ("directorio_unidades",))
        self.assertEqual(MANIFIESTO.capacidades,
                         ("portada_publica", "ficha_de_centro", "solicitudes_y_acceso", "reportes"))
        self.assertEqual(MANIFIESTO.administracion, ("apps.centros_id.admin",))
        self.assertEqual(MANIFIESTO.migraciones, ("apps.centros_id.migrations",))
        self.assertEqual(MANIFIESTO.comandos, ("apps.centros_id.management.commands.cargar_centros_id",
                                              "apps.centros_id.management.commands.construir_escenario_centros"))

    def test_vista_usa_la_plantilla_del_contexto(self):
        self.assertEqual(CentrosIDView.template_name, "centros_id/portada.html")
