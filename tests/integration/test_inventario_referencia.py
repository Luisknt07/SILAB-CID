"""Lo que se deduce de un insumo sin pedirlo y los datos demostrativos de existencias.

La unidad y el contenido salen del texto de la presentación; los niveles básicos, del contenido. Lo demostrativo
crea un lote y consumos trazables (que mueven el saldo como cualquier movimiento), con cantidades enteras para lo
que se cuenta por piezas; repetir la orden no duplica nada.
"""
from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.recursos.presentation.inventario_referencia import completar, inferir_unidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.directorio_unidades.models.core import Unidad


class InventarioDeReferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de insumos', slug='lab-insumos-ref', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.filamento = Consumible.objects.create(unidad=cls.unidad, codigo='REF-PLA', nombre='Filamento PLA', presentacion='Bobina de 1 kg')
        cls.rollo = Consumible.objects.create(unidad=cls.unidad, codigo='REF-ROLLO', nombre='Cinta de transferencia', presentacion='Rollo')

    def test_la_unidad_y_el_contenido_salen_de_la_presentacion(self):
        self.assertEqual(inferir_unidad('Bobina de 1 kg'), ('g', Decimal('1000')))
        self.assertEqual(inferir_unidad('Frasco de 500 mL'), ('mL', Decimal('500')))
        self.assertEqual(inferir_unidad('Paquete de 50 por visor'), ('unidad', Decimal('50')))
        self.assertEqual(inferir_unidad('Rollo para impresora de etiquetas'), ('rollo', Decimal('1')))
        self.assertEqual(inferir_unidad('Sin pista'), ('unidad', Decimal('1')))
        cambiados = completar(self.filamento)
        self.assertIn('unidad_medida', cambiados)
        self.assertEqual((self.filamento.unidad_medida, self.filamento.cantidad_por_presentacion), ('g', Decimal('1000')))
        self.assertEqual((self.filamento.stock_objetivo, self.filamento.minimo, self.filamento.stock_seguridad),
                         (Decimal('4000'), Decimal('2000'), Decimal('1000')))
        self.assertEqual(completar(Consumible(nombre='x', presentacion='y', unidad_medida='g', cantidad_por_presentacion=1,
                                              stock_objetivo=1, minimo=1, stock_seguridad=1, plazo_reposicion_dias=3)), [])

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
    def test_lo_demostrativo_es_trazable_entero_para_piezas_e_idempotente(self):
        salida = StringIO()
        call_command('completar_inventario_de_referencia', '--unidad', self.unidad.slug, '--demostrativo', '--confirmar-datos-demo', stdout=salida)
        self.assertIn('2 insumos completados', salida.getvalue())
        call_command('completar_inventario_de_referencia', '--unidad', self.unidad.slug, '--demostrativo', '--confirmar-datos-demo', stdout=salida)
        self.assertEqual(LoteConsumible.objects.filter(consumible__unidad=self.unidad).count(), 2)
        self.rollo.refresh_from_db()
        self.assertEqual(self.rollo.unidad_medida, 'rollo')
        self.assertGreater(self.rollo.stock_total, 0)
        self.assertEqual(self.rollo.stock_total, self.rollo.stock_total.to_integral_value(), 'Las piezas no quedan fraccionadas.')
        for movimiento in EntradaInventario.objects.filter(consumible=self.rollo):
            self.assertEqual(movimiento.cantidad, movimiento.cantidad.to_integral_value())
        recibido = sum(m.cantidad for m in EntradaInventario.objects.filter(consumible=self.rollo, tipo='ingreso'))
        consumido = sum(m.cantidad for m in EntradaInventario.objects.filter(consumible=self.rollo, tipo='salida'))
        self.assertEqual(self.rollo.stock_total, recibido - consumido)

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=False)
    def test_produccion_rechaza_cantidades_ficticias_antes_de_escribir(self):
        with self.assertRaisesMessage(CommandError, 'deshabilitados'):
            call_command('completar_inventario_de_referencia', unidad=self.unidad.slug,
                         demostrativo=True, confirmar_datos_demo=True, stdout=StringIO())
        self.assertFalse(EntradaInventario.objects.exists())
        self.assertFalse(LoteConsumible.objects.exists())

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
    def test_exige_alcance_y_confirmacion_para_la_carga_ficticia(self):
        for opciones in ({}, {'unidad': self.unidad.slug}, {'confirmar_datos_demo': True}):
            with self.subTest(opciones=opciones), self.assertRaises(CommandError):
                call_command('completar_inventario_de_referencia', demostrativo=True, stdout=StringIO(), **opciones)

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
    def test_no_mezcla_demostrativos_con_saldos_existentes(self):
        self.rollo.stock_total = 5
        self.rollo.save(update_fields=['stock_total'])
        call_command('completar_inventario_de_referencia', unidad=self.unidad.slug,
                     demostrativo=True, confirmar_datos_demo=True, stdout=StringIO())
        self.rollo.refresh_from_db()
        self.assertEqual(self.rollo.stock_total, 5)
        self.assertFalse(self.rollo.lotes_inventario.exists())
