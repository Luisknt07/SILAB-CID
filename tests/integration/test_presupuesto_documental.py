"""El mismo presupuesto se comprueba antes del envío y al revisar la entrega."""
from copy import deepcopy
from decimal import Decimal

from django.test import SimpleTestCase

from apps.documentos.presentation.presupuesto_documental import analizar_presupuesto


class PresupuestoDocumentalTests(SimpleTestCase):
    def fila(self, **cambios):
        return dict(dict(categoria='equipos', item='Instrumento de medición', cantidad='2',
            justificacion='Mediciones de las actividades previstas', prioridad='alta',
            costo_unitario='100.50', fuente='institucional'), **cambios)

    def test_inversion_semestral_no_exige_trimestre_y_conserva_el_contenido(self):
        contenido = dict(inversion=[self.fila()])
        original = deepcopy(contenido)
        lectura = analizar_presupuesto('planificacion', contenido)
        self.assertTrue(lectura['completo'])
        self.assertEqual(lectura['hallazgos'], [])
        self.assertEqual(lectura['total'], Decimal('201.00'))
        self.assertEqual(contenido, original)

    def test_compras_anuales_exigen_trimestre_agrupado_con_faltantes(self):
        lectura = analizar_presupuesto('compras', dict(compras=[self.fila(fuente='')]))
        self.assertFalse(lectura['completo'])
        self.assertEqual([h['regla'] for h in lectura['hallazgos']], ['compra_incompleta'])
        self.assertIn('fuente de financiamiento, trimestre', lectura['hallazgos'][0]['mensaje'])
        self.assertIn('Compras del año, ítem 1', lectura['hallazgos'][0]['mensaje'])

    def test_costo_cero_numerico_o_texto_es_valido(self):
        for costo in (0, '0', Decimal(0)):
            with self.subTest(costo=costo):
                lectura = analizar_presupuesto('planificacion', dict(inversion=[self.fila(costo_unitario=costo)]))
                self.assertTrue(lectura['completo'])
                self.assertEqual(lectura['total'], Decimal(0))

    def test_fila_inicial_no_es_adquisicion_y_sigue_exigiendo_justificacion(self):
        for fila in ({}, {'categoria': 'equipos'}, {'categoria': 'equipos', 'item': '', 'cantidad': None}):
            with self.subTest(fila=fila):
                contenido = dict(inversion=[fila])
                lectura = analizar_presupuesto('planificacion', contenido)
                self.assertFalse(lectura['completo'])
                self.assertEqual(lectura['filas'], [])
                self.assertEqual([h['regla'] for h in lectura['hallazgos']], ['apartados_incompletos'])
                contenido['sin_inversion_justificacion'] = '<p>Las actividades se cubren con el inventario disponible.</p>'
                lectura = analizar_presupuesto('planificacion', contenido)
                self.assertTrue(lectura['completo'])
                self.assertEqual(lectura['filas'], [])

    def test_fila_parcial_no_se_sustituye_con_justificacion_de_no_compras(self):
        contenido = dict(inversion=[dict(categoria='equipos', item='Instrumento')],
            sin_inversion_justificacion='<p>No se proyectan adquisiciones.</p>')
        lectura = analizar_presupuesto('planificacion', contenido)
        self.assertFalse(lectura['completo'])
        self.assertEqual(len(lectura['filas']), 1)
        self.assertEqual([h['regla'] for h in lectura['hallazgos']], ['compra_incompleta'])
        self.assertIn('Presupuesto del período, ítem 1: completa cantidad', lectura['hallazgos'][0]['mensaje'])

    def test_cantidad_cero_no_desaparece_como_si_fuera_un_campo_vacio(self):
        lectura = analizar_presupuesto('planificacion', dict(inversion=[self.fila(cantidad=0)]))
        self.assertFalse(lectura['completo'])
        self.assertEqual([h['regla'] for h in lectura['hallazgos']], ['importe_invalido'])

    def test_numeros_no_finitos_negativos_y_fuera_de_rango_no_se_aceptan(self):
        for valor in ('Infinity', '-Infinity', 'NaN', '-1', '1e999999', '1000000000001', 'x'):
            for campo in ('cantidad', 'costo_unitario'):
                with self.subTest(valor=valor, campo=campo):
                    lectura = analizar_presupuesto('planificacion', dict(inversion=[self.fila(**{campo: valor})]))
                    self.assertFalse(lectura['completo'])
                    self.assertIn('importe_invalido', [h['regla'] for h in lectura['hallazgos']])

    def test_los_catalogos_invalidos_y_el_trimestre_fuera_de_rango_se_rechazan(self):
        lectura = analizar_presupuesto('compras', dict(compras=[self.fila(categoria='no-existe',
            prioridad='urgente', fuente='sin-definir', trimestre='5')]))
        self.assertFalse(lectura['completo'])
        self.assertEqual([h['regla'] for h in lectura['hallazgos']],
                         ['clasificacion_compra_invalida', 'trimestre_invalido'])

    def test_necesidad_repetida_conserva_revision_sin_invalidar_por_si_sola(self):
        lectura = analizar_presupuesto('planificacion', dict(inversion=[self.fila(),
            self.fila(item=' Instrumento  de MEDICIÓN ')]))
        self.assertTrue(lectura['completo'])
        self.assertEqual([h['regla'] for h in lectura['hallazgos']], ['compra_duplicada'])
        self.assertEqual(lectura['hallazgos'][0]['severidad'], 'revision')
        self.assertEqual(lectura['total'], Decimal('402.00'))

    def test_justificacion_visualmente_vacia_no_cubre_ausencia_de_compras(self):
        for texto in ('', '<p><br></p>', '<p>&nbsp;</p>'):
            with self.subTest(texto=texto):
                lectura = analizar_presupuesto('compras', dict(compras=[], sin_compras_justificacion=texto))
                self.assertFalse(lectura['completo'])

    def test_estructuras_invalidas_devuelven_hallazgo_y_no_interrumpen(self):
        for tabla in ({'item': 'Instrumento'}, 'no-tabla', [None], [5], [dict(categoria='insumos')]):
            with self.subTest(tabla=tabla):
                lectura = analizar_presupuesto('planificacion', dict(inversion=tabla))
                self.assertFalse(lectura['completo'])
                self.assertTrue(lectura['hallazgos'])

    def test_las_filas_iniciales_no_incrementan_items_ni_el_numero_del_error(self):
        lectura = analizar_presupuesto('planificacion', dict(inversion=[{'categoria': 'equipos'},
            self.fila(), {'categoria': 'equipos'}, dict(item='Segundo instrumento')]))
        self.assertEqual(len(lectura['filas']), 2)
        self.assertEqual(lectura['total'], Decimal('201.00'))
        self.assertIn('ítem 2', lectura['hallazgos'][0]['mensaje'])
