"""Una salida externa no oculta las pérdidas ni los excesos del producto."""

from copy import deepcopy

from django.test import SimpleTestCase

from apps.documentos.presentation.documentacion import balance_general, entradas_y_salidas
from apps.plantas_piloto.operacion.presentation.escenarios import aplicar_escenario
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa


class BalanceConSalidasExternasTests(SimpleTestCase):
    def datos(self, rendimiento='98', interno='1', agua='2500'):
        return {
            'cantidad_base': '100', 'factor': '1', 'rendimiento_esperado': '98',
            'unidad_base': 'kg', 'unidad_producto': 'kg', 'producto': 'Almidón',
            'etapas': [{
                'orden': 1, 'nombre': 'Lavado', 'tipo': 'operacion',
                'rendimiento_pct': rendimiento, 'insumos': [],
                'salidas': [
                    {'nombre': 'Finos', 'cantidad': interno, 'unidad': 'kg', 'externa_al_flujo': False},
                    {'nombre': 'Agua de proceso', 'cantidad': agua, 'unidad': 'litro', 'externa_al_flujo': True},
                ],
            }],
        }

    def test_una_etapa_puede_perder_masa_y_tener_dos_tipos_de_salida(self):
        datos = self.datos()
        fila = balance_de_masa(datos)['filas'][0]
        self.assertEqual((fila['continua'], fila['perdida'], fila['externo'], fila['exceso']), ('98', '1', '2500', ''))
        general = balance_general(datos, entradas_y_salidas(datos))
        self.assertTrue(general['cuadra'])
        self.assertEqual([s['nombre'] for s in general['externas']], ['Agua de proceso'])
        self.assertIn('Finos', [s['nombre'] for s in general['salidas']])
        self.assertIn('salida externa al flujo', fila['salidas'][1])

    def test_no_oculta_el_exceso_interno_aunque_haya_agua_externa(self):
        datos = self.datos(interno='3')
        general = balance_general(datos, entradas_y_salidas(datos))
        self.assertFalse(general['cuadra'])
        self.assertEqual(general['diferencia'], '1')
        self.assertEqual(general['descuadres'][0]['exceso'], '1')

    def test_rendimiento_cien_no_convierte_una_salida_interna_en_externa(self):
        fila = balance_de_masa(self.datos(rendimiento='100'))['filas'][0]
        self.assertEqual(fila['exceso'], '1')
        self.assertEqual(fila['externo'], '2500')

    def test_cambiar_el_agua_en_el_escenario_no_cambia_el_balance_del_producto(self):
        datos = self.datos()
        original = deepcopy(datos)
        escenario = aplicar_escenario(datos, {'salida_1_1': '6000'})
        self.assertEqual(datos, original)
        self.assertTrue(escenario['etapas'][0]['salidas'][1]['externa_al_flujo'])
        general = balance_general(escenario, entradas_y_salidas(escenario))
        self.assertTrue(general['cuadra'])
        self.assertEqual(general['entra_total'], '100')
        self.assertEqual(general['externas'][0]['cantidad'], '6000')

    def test_los_gramos_de_salida_se_convierten_antes_de_comparar_con_la_merma(self):
        datos = self.datos(interno='1000')
        datos['etapas'][0]['salidas'][0]['unidad'] = 'g'
        self.assertEqual(balance_de_masa(datos)['filas'][0]['perdida'], '1')
