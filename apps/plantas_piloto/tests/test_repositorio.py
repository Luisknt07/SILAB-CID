from datetime import date

from django.test import SimpleTestCase

from apps.plantas_piloto.domain.repositorio import estado_vigencia, esta_vigente


class ReglasVigenciaArtefactoTests(SimpleTestCase):
    def test_distingue_vigencia_programada_actual_y_vencida(self):
        hoy = date(2026, 9, 19)
        self.assertEqual(estado_vigencia(hoy, None, None), "sin_declarar")
        self.assertEqual(estado_vigencia(hoy, date(2026, 10, 1), None), "programado")
        self.assertEqual(estado_vigencia(hoy, date(2026, 1, 1), date(2026, 9, 18)), "vencido")
        self.assertTrue(esta_vigente(hoy, date(2026, 1, 1), None))

    def test_un_cambio_en_la_fuente_exige_revision_aunque_la_fecha_siga_vigente(self):
        self.assertEqual(
            estado_vigencia(
                date(2026, 9, 19),
                date(2026, 1, 1),
                date(2027, 1, 1),
                desactualizado=True,
            ),
            "requiere_revision",
        )
