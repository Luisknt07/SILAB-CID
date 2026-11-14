from django.test import SimpleTestCase

from apps.plantas_piloto.domain.completitud import (
    estado_cobertura,
    estado_ficha,
    porcentaje_cobertura,
)


class ReglasCompletitudPlantaTests(SimpleTestCase):
    def test_porcentaje_se_acota_y_una_meta_vacia_se_considera_cubierta(self):
        self.assertEqual(porcentaje_cobertura(12, 10), 100)
        self.assertEqual(porcentaje_cobertura(-1, 10), 0)
        self.assertEqual(porcentaje_cobertura(0, 0), 100)

    def test_cobertura_distingue_los_cuatro_estados(self):
        self.assertEqual(estado_cobertura(2, 2), "aprobado")
        self.assertEqual(estado_cobertura(1, 2), "parcial")
        self.assertEqual(estado_cobertura(0, 2), "pendiente")
        self.assertEqual(estado_cobertura(2, 2, bloqueado=True), "bloqueado")

    def test_ficha_solo_se_aprueba_con_publicacion_y_validacion(self):
        self.assertEqual(estado_ficha(100, "publicada", "validada"), "aprobado")
        self.assertEqual(estado_ficha(100, "publicada", "pendiente"), "parcial")
        self.assertEqual(estado_ficha(100, "borrador", "validada"), "pendiente")
        self.assertEqual(
            estado_ficha(100, "publicada", "validada", bloqueado=True),
            "bloqueado",
        )
