from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from apps.plantas_piloto.domain.planificacion import (
    cantidad_planificada,
    demanda_no_comprometida,
    equivalente_base,
    periodos_demanda,
    promedio_movil,
    ventanas_historicas,
)


class ReglasPlanificacionPlantaTests(SimpleTestCase):
    def test_horizonte_semanal_no_pierde_el_ultimo_periodo_parcial(self):
        periodos = periodos_demanda(date(2026, 9, 1), date(2026, 9, 18), 'semanal')
        self.assertEqual(
            [(periodo.inicio, periodo.fin) for periodo in periodos],
            [
                (date(2026, 9, 1), date(2026, 9, 7)),
                (date(2026, 9, 8), date(2026, 9, 14)),
                (date(2026, 9, 15), date(2026, 9, 18)),
            ],
        )

    def test_ventanas_mensuales_y_promedio_movil_son_reproducibles(self):
        ventanas = ventanas_historicas(date(2026, 4, 10), 'mensual')
        self.assertEqual(ventanas[0].inicio, date(2026, 1, 1))
        self.assertEqual(ventanas[-1].fin, date(2026, 3, 31))
        self.assertEqual(promedio_movil(('10', '20', '30')), Decimal('20.000'))

    def test_demanda_separa_lo_abierto_de_los_compromisos(self):
        self.assertEqual(
            cantidad_planificada('12', '4', '3', '-2'),
            Decimal('17.000'),
        )
        self.assertEqual(demanda_no_comprometida('12', '-2'), Decimal('10.000'))
        self.assertEqual(demanda_no_comprometida('2', '-5'), Decimal('0.000'))

    def test_equivalente_base_convierte_producto_sin_mover_inventario(self):
        self.assertEqual(equivalente_base('24', '12', '100'), Decimal('200.000'))

