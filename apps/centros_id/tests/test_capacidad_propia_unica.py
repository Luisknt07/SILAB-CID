from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.centros_id.models import CentroID, Componente


class CapacidadPropiaUnicaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = CentroID.objects.create(slug="centro-uno", nombre="Centro Uno")
        cls.b = CentroID.objects.create(slug="centro-dos", nombre="Centro Dos")

    def area(self, centro, codigo, **datos):
        return Componente(
            centro=centro,
            codigo=codigo,
            tipo="laboratorio",
            nombre=codigo,
            resumen="Capacidad",
            descripcion="Ensayos",
            **datos,
        )

    def test_no_duplica_propiedad_dentro_ni_entre_centros(self):
        propia = self.area(self.a, "xr", unidad_slug="laboratorio-xr")
        propia.save()
        for centro in (self.a, self.b):
            otra = self.area(centro, "otra", unidad_slug="laboratorio-xr")
            with self.subTest(centro=centro.pk), self.assertRaises(ValidationError):
                otra.clean()

    def test_base_tambien_impide_duplicar_sin_formulario(self):
        self.area(self.a, "xr", unidad_slug="laboratorio-xr").save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.area(self.b, "otra", unidad_slug="laboratorio-xr").save()

    def test_compartir_no_se_convierte_en_propiedad(self):
        self.area(self.a, "xr", unidad_slug="laboratorio-xr").save()
        compartida = self.area(self.b, "xr", unidades_articuladas="laboratorio-xr")
        compartida.clean()
        compartida.save()

    def test_area_sin_laboratorio_no_crea_identidad_adicional(self):
        for c in (self.a, self.b):
            area = self.area(c, "xr")
            area.clean()
            area.save()

    def test_no_admite_propia_y_vinculada_en_la_misma_area(self):
        with self.assertRaises(ValidationError):
            self.area(
                self.a,
                "xr",
                unidad_slug="laboratorio-xr",
                unidades_articuladas="laboratorio-xr",
            ).clean()
