"""El comando de corridas demostrativas ejercita el flujo completo de cada planta sin cruzarse con lo real.

Cada proceso de referencia recibe una corrida demostrativa cerrada, con su lote
controlado y despachado; una de cada cinco sale no conforme. Ninguna descuenta
inventario, genera ingresos, bloquea la agenda ni entra en los indicadores. Se
repite sin duplicar y ``--limpiar`` la rehace.
"""
from django.core.management import call_command
from django.test import TestCase

from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad
from apps.recursos.models.consumibles import EntradaInventario
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion, Receta
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.directorio_unidades.models.core import Unidad


class CorridasDemostrativasDeLaPlantaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_laboratorios_institucionales', laboratorio='carnicos')
        cls.unidad = Unidad.objects.get(slug='planta-piloto-carnicos')
        cls.inventario_antes = EntradaInventario.objects.filter(unidad=cls.unidad).count()
        cls.finanzas_antes = MovimientoFinancieroUnidad.objects.filter(unidad=cls.unidad).count()
        call_command('cargar_corridas_demostrativas', planta=cls.unidad.slug)

    def test_cada_proceso_de_referencia_tiene_su_corrida_cerrada_y_una_planificada(self):
        recetas = Receta.objects.filter(unidad=self.unidad, origen='referencia')
        ordenes = OrdenProduccion.objects.filter(unidad=self.unidad, demostrativa=True)
        self.assertEqual(ordenes.filter(estado='terminada').count(), recetas.count())
        self.assertEqual(ordenes.filter(estado='planificada').count(), 1)
        self.assertEqual(set(ordenes.values_list('origen', flat=True)), {'practica', 'investigacion', 'propia'})
        self.assertFalse(OrdenProduccion.objects.reales().filter(unidad=self.unidad).exists())

    def test_los_lotes_se_controlan_y_uno_de_cada_cinco_abre_su_no_conformidad(self):
        lotes = LoteProducto.objects.filter(unidad=self.unidad)
        self.assertTrue(lotes.exists())
        self.assertFalse(lotes.filter(demostrativo=False).exists())
        self.assertTrue(ControlCalidad.objects.filter(lote_producto__in=lotes, resultado='conforme').exists())
        self.assertTrue(NoConformidad.objects.filter(lote_producto__in=lotes).exists())
        self.assertTrue(MovimientoProducto.objects.filter(lote__in=lotes, tipo='venta').exists())

    def test_no_toca_inventario_finanzas_ni_agenda(self):
        self.assertEqual(EntradaInventario.objects.filter(unidad=self.unidad).count(), self.inventario_antes)
        self.assertEqual(MovimientoFinancieroUnidad.objects.filter(unidad=self.unidad).count(), self.finanzas_antes)
        self.assertFalse(BloqueoAgendaUnidad.objects.filter(unidad=self.unidad, tipo='produccion').exists())

    def test_se_repite_sin_duplicar_y_limpiar_la_rehace(self):
        antes = OrdenProduccion.objects.filter(unidad=self.unidad).count()
        call_command('cargar_corridas_demostrativas', planta=self.unidad.slug)
        self.assertEqual(OrdenProduccion.objects.filter(unidad=self.unidad).count(), antes)
        call_command('cargar_corridas_demostrativas', planta=self.unidad.slug, limpiar=True)
        self.assertEqual(OrdenProduccion.objects.filter(unidad=self.unidad).count(), antes)
