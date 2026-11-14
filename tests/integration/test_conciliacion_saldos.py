"""Un contador obsoleto se reconstruye sin simular un ingreso de material."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.test import TestCase
from django.core.management import call_command

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.presentation.conciliacion import conciliar_saldo


class ConciliacionSaldosTests(TestCase):
    def setUp(self):
        self.unidad = Unidad.objects.create(nombre='Almacén QA', slug='almacen-conciliacion', descripcion='.', fecha_inicio=date(2020, 1, 1))
        self.articulo = Consumible.objects.create(unidad=self.unidad, codigo='QA-CONCIL', nombre='Material', stock_total=10)
        self.inicial = LoteConsumible.objects.create(consumible=self.articulo, codigo='INICIAL', cantidad_inicial=10, cantidad_actual=10, bodega='Bodega QA')
        self.recibido = LoteConsumible.objects.create(consumible=self.articulo, codigo='RECIBIDO', cantidad_inicial=5, cantidad_actual=0, bodega='Bodega QA')
        EntradaInventario.objects.create(consumible=self.articulo, tipo='ingreso', motivo='recepcion', cantidad=5, lote_inventario=self.recibido)
        EntradaInventario.objects.create(consumible=self.articulo, tipo='salida', motivo='consumo_produccion', cantidad=2, lote_inventario=self.recibido)
        Consumible.objects.filter(pk=self.articulo.pk).update(stock_total=10)

    def test_simulacion_y_aplicacion_idempotente_con_auditoria_y_sin_movimientos_nuevos(self):
        self.assertEqual(conciliar_saldo(self.articulo.pk)['estado'], 'reconstruible')
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_total, 10)
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.assertEqual(conciliar_saldo(self.articulo.pk, aplicar=True)['estado'], 'corregido')
        self.assertEqual(conciliar_saldo(self.articulo.pk, aplicar=True)['estado'], 'sin_diferencia')
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_total, 13)
        self.assertEqual(EntradaInventario.objects.count(), 2)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
        self.assertIsNone(RegistroAuditoriaUnidad.objects.get().usuario_id)

    def test_rechaza_kardex_interrumpido_lote_sin_procedencia_y_material_del_cliente(self):
        for fallo in ('kardex', 'lote', 'cliente'):
            with self.subTest(fallo=fallo):
                if fallo == 'kardex':
                    primero = EntradaInventario.objects.filter(consumible=self.articulo).earliest('pk')
                    EntradaInventario.objects.filter(pk=primero.pk).update(saldo_resultante=14)
                elif fallo == 'lote':
                    LoteConsumible.objects.filter(pk=self.inicial.pk).update(cantidad_inicial=11)
                else:
                    LoteConsumible.objects.filter(pk=self.inicial.pk).update(material_cliente=True)
                self.assertEqual(conciliar_saldo(self.articulo.pk, aplicar=True)['estado'], 'revision_fisica')
                EntradaInventario.objects.filter(consumible=self.articulo, tipo='ingreso').update(saldo_resultante=15)
                LoteConsumible.objects.filter(pk=self.inicial.pk).update(cantidad_inicial=10, material_cliente=False)
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_total, 10)
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())

    def test_error_de_auditoria_revierte_el_contador(self):
        with patch.object(RegistroAuditoriaUnidad.objects, 'create', side_effect=RuntimeError('QA')), self.assertRaises(RuntimeError):
            conciliar_saldo(self.articulo.pk, aplicar=True)
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_total, 10)

    def test_comando_no_muta_sin_aplicar(self):
        salida = StringIO()
        call_command('conciliar_saldos_inventario', stdout=salida)
        self.assertIn('reconstruible', salida.getvalue())
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_total, 10)
