"""La cobertura de patrimonio y personal no depende de identidad ni banderas antiguas."""

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.reservas.presentation.cotizaciones import (
    calcular_costo_referencial_recursos,
    calcular_liquidacion_real,
    politica_cobro_servicios,
)


class PoliticaSoloMaterialesTests(SimpleTestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            tarifa_referencial_hora_espacio=8,
            tarifa_referencial_hora_equipo=18,
            tarifa_referencial_hora_software=3,
            tarifa_referencial_hora_acompanamiento=12,
            aporte_institucional_recursos_pct=0,
            cobrar_tarifa_base=True, cobrar_uso_equipo=True,
            cobrar_uso_equipo_ejecucion=True, cobrar_mano_obra=True, cobrar_diseno=True,
            aplicar_iva=False,
        )
        self.alcohol = SimpleNamespace(pk=1, nombre='Alcohol isopropílico 99 %',
                                       unidad_medida='mL', precio_unitario=Decimal('0.006'))

    def test_caso_reportado_solo_cobra_sesenta_centavos_a_todos_los_segmentos(self):
        for segmento in ('externo', 'estudiante', 'personal'):
            with self.subTest(segmento=segmento), patch(
                'apps.reservas.presentation.cotizaciones.clasificacion_tarifaria_actual',
                return_value=(segmento, segmento, {}),
            ):
                quote = calcular_costo_referencial_recursos(
                    [(self.alcohol, Decimal('100'), 'estimacion')], None,
                    configuracion=self.config, recursos=[1], incluye_espacio=True, duracion_horas=1,
                )
                self.assertEqual(quote['valor_referencial'], '38.60')
                self.assertEqual(quote['aporte_institucional'], '38.00')
                self.assertEqual(quote['valor_estimado_usuario'], '0.60')
                self.assertTrue(all(item['valor_usuario'] == '0.00' for item in quote['componentes_apoyo']))

    def test_banderas_antiguas_no_permiten_cobrar_en_ninguna_modalidad(self):
        for modalidad in ('modelo_listo', 'diseno_asistido', 'diseno_completo', ''):
            with self.subTest(modalidad=modalidad):
                politica = politica_cobro_servicios(self.config, modalidad)
                self.assertTrue(politica.pop('materiales'))
                self.assertFalse(any(politica.values()))

    def test_cierre_conserva_estimacion_original_y_separa_desperdicio(self):
        original = {'segmento': 'externo', 'total': '38.60'}
        reserva = SimpleNamespace(
            pk=1,
            fecha=date(2026, 11, 10), tipo_solicitud='recursos',
            tipo_usuario_solicitante='externo', desglose_cotizacion=original,
            laboratorio=SimpleNamespace(configuracion_operativa=self.config),
            costo_estimado=Decimal('38.60'),
        )
        liquidacion = calcular_liquidacion_real(
            reserva, inicio=time(8), fin=time(9), recursos={'espacios': [1], 'equipos': [1]},
            consumos=[{'costo_consumido': '0.60', 'costo_desperdicio': '0.12'}],
        )
        self.assertEqual(liquidacion['valor_final_usuario'], '0.60')
        self.assertEqual(liquidacion['aporte_institucional_real'], '38.00')
        self.assertEqual(liquidacion['costo_desperdicio_laboratorio'], '0.12')
        self.assertEqual(liquidacion['estimacion_original']['valor_usuario'], '38.60')
        self.assertEqual(original, {'segmento': 'externo', 'total': '38.60'})

    def test_sin_materiales_no_hay_cobro_aunque_existan_licencias_y_guias(self):
        with patch('apps.reservas.presentation.cotizaciones.clasificacion_tarifaria_actual',
                   return_value=('externo', 'externo', {})):
            quote = calcular_costo_referencial_recursos(
                [], None, configuracion=self.config, software=[1, 2], incluye_espacio=True,
                duracion_horas=2, sesiones=3, acompanamiento_visita=(2, Decimal('12')),
            )
        self.assertEqual(quote['aporte_institucional'], quote['valor_referencial'])
        self.assertEqual(quote['total'], '0.00')
        self.assertEqual(quote['aporte_institucional'], '156.00')

    def test_impuestos_solo_sobre_materiales_redondeados_a_centavos(self):
        self.config.aplicar_iva = True
        self.config.porcentaje_iva = Decimal('15')
        self.alcohol.precio_unitario = Decimal('1.499')
        with patch('apps.reservas.presentation.cotizaciones.clasificacion_tarifaria_actual',
                   return_value=('externo', 'externo', {})):
            quote = calcular_costo_referencial_recursos(
                [(self.alcohol, Decimal('1'), 'estimacion')], None,
                configuracion=self.config, recursos=[1], incluye_espacio=True, duracion_horas=1,
            )
        self.assertEqual(quote['subtotal_usuario'], '1.50')
        self.assertEqual(quote['iva']['monto'], '0.23')
        self.assertEqual(quote['total'], '1.73')

    def test_cierre_visita_cubre_los_guias_sin_duplicar_su_referencia_por_horas(self):
        reserva = SimpleNamespace(
            pk=2, fecha=date(2026, 11, 10), tipo_solicitud='recursos',
            tipo_usuario_solicitante='externo', costo_estimado=Decimal('0.80'),
            laboratorio=SimpleNamespace(configuracion_operativa=self.config),
            visita=SimpleNamespace(guias_necesarios=2),
            desglose_cotizacion={
                'segmento': 'externo', 'total': '0.80',
                'componentes_apoyo': [{'precio_por_guia': '12.00'}],
            },
        )
        liquidacion = calcular_liquidacion_real(
            reserva, inicio=time(8), fin=time(10), recursos={'espacios': [1]},
            consumos=[{'costo_consumido': '0.80'}],
        )
        guia = next(item for item in liquidacion['conceptos'] if item['categoria'] == 'acompanamiento')
        self.assertEqual(guia['subtotal'], '24.00')
        self.assertEqual(guia['aporte_institucional'], '24.00')
        self.assertEqual(guia['valor_usuario'], '0.00')
        self.assertIsNone(guia['tarifa_hora'])
        self.assertEqual(liquidacion['aporte_institucional_real'], '40.00')
        self.assertEqual(liquidacion['valor_final_usuario'], '0.80')
