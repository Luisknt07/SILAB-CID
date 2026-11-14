"""Corridas demostrativas: validan el flujo completo sin cruzarse con la operación real.

Viven en la sesión demostrativa de la planta. Recorren planificación, cierre,
calidad, trazabilidad y despacho, pero no descuentan inventario, sus lotes no
entran a ninguna unidad ni generan ingresos, y ningún indicador ni reporte las
cuenta; la producción real no las lista.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.calidad import indicadores_calidad
from apps.plantas_piloto.operacion.presentation.trazabilidad import consolidado_institucional
from apps.recursos.models.consumibles import EntradaInventario, LoteConsumible
from apps.plantas_piloto.operacion.models.produccion import LoteProducto, MovimientoProducto, OrdenProduccion
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.plantas_piloto.operacion.models.erp import SesionERP
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_trazabilidad import BaseTrazabilidad


class CorridasDemostrativasTests(BaseTrazabilidad):
    def sesion(self):
        return SesionERP.demostrativa_de(self.unidad)

    def planificar_demostrativa(self, **extra):
        return self.orden_de(self.planificar_queso(sesion_erp=self.sesion().codigo, **extra))

    def corrida_demostrativa(self):
        orden = self.planificar_demostrativa(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=(self.hoy + timedelta(days=2)).isoformat(),
        )
        self.assertTrue(orden.demostrativa)
        self.assertEqual(orden.sesion, self.sesion())
        self.assertEqual(self.cerrar_queso(orden, sesion_erp=self.sesion().codigo).status_code, 200)
        orden.refresh_from_db()
        return orden

    def test_no_descuenta_inventario_y_sus_lotes_se_marcan(self):
        leche = LoteConsumible.objects.get(codigo='LAC-LECHE-L1')
        antes = leche.cantidad_actual
        orden = self.corrida_demostrativa()
        leche.refresh_from_db()
        self.assertEqual(leche.cantidad_actual, antes)
        self.assertFalse(EntradaInventario.objects.filter(referencia=orden.codigo).exists())
        self.assertTrue(orden.detalle_cierre['demostrativa'])
        self.assertTrue(all(consumo['simulado'] for consumo in orden.detalle_cierre['consumos']))
        lotes = list(orden.lotes.all())
        self.assertTrue(lotes)
        for lote in lotes:
            self.assertTrue(lote.demostrativo)
            self.assertTrue(lote.codigo.endswith('-DEMO'))

    def test_recorre_calidad_y_despacho_sin_ingresos_ni_indicadores(self):
        def numeros_reales():
            return consolidado_institucional(self.coordinacion, self.hoy, self.hoy + timedelta(days=5),
                                             unidades=[self.unidad])['filas'][0]
        corridas_reales = numeros_reales()['corridas']
        orden = self.corrida_demostrativa()
        lote = orden.lotes.get(producto__codigo='LAC-PRD-QUESO-FRESCO')
        # Por liberar: aparece en la cola de calidad, pero no en su indicador.
        self.assertEqual(indicadores_calidad(self.unidad)['lotes_por_liberar'], 0)
        self.assertEqual(self.controlar(self.plan_queso, f'lote_producto={lote.pk}').status_code, 302)
        lote.refresh_from_db()
        self.assertEqual(lote.estado, 'disponible')
        self.assertEqual(indicadores_calidad(self.unidad)['controles_30'], 0)
        venta = MovimientoProducto.objects.create(
            unidad=self.unidad, lote=lote, tipo='venta', cantidad=Decimal('2'), registrado_por=self.coordinacion,
        )
        self.assertIsNone(venta.movimiento_financiero)
        self.assertFalse(MovimientoFinancieroUnidad.objects.filter(referencia=lote.codigo).exists())
        self.assertFalse(MovimientoProducto.objects.reales().filter(pk=venta.pk).exists())
        numeros = numeros_reales()
        self.assertEqual(numeros['corridas'], corridas_reales)
        self.assertEqual(numeros['lotes'], 0)
        self.assertFalse(OrdenProduccion.objects.reales().filter(pk=orden.pk).exists())
        self.assertFalse(LoteProducto.objects.reales().filter(pk=lote.pk).exists())

    def test_un_lote_demostrativo_no_entra_a_ninguna_unidad(self):
        lote = self.corrida_demostrativa().lotes.get(producto__codigo='LAC-PRD-QUESO-FRESCO')
        lote.aprobar_calidad()
        otra = Unidad.objects.exclude(pk=self.unidad.pk).first()
        with self.assertRaises(ValidationError):
            MovimientoProducto.objects.create(
                unidad=self.unidad, lote=lote, tipo='transferencia', cantidad=Decimal('1'), unidad_destino=otra,
            )

    def test_la_hoja_y_el_panel_la_muestran_marcada(self):
        orden = self.corrida_demostrativa()
        lote = orden.lotes.get(producto__codigo='LAC-PRD-QUESO-FRESCO')
        self.client.force_login(self.coordinacion)
        hoja = self.client.get(reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertContains(hoja, f'Lote de la sesión {self.sesion().codigo}')
        # La sesión demostrativa la lista; la producción real, no.
        abierta = self.planificar_demostrativa()
        self.client.force_login(self.coordinacion)
        erp = reverse('erp_planta', args=[self.unidad.slug])
        self.assertIn(abierta, self.client.get(erp, {'sesion': self.sesion().codigo}).context['ordenes_produccion'])
        self.assertNotIn(abierta, self.client.get(erp).context['ordenes_produccion'])

    def test_no_le_quita_la_linea_a_una_reserva_real(self):
        demostrativa = self.planificar_demostrativa()
        real = self.orden_de(self.planificar_queso(
            fecha_inicio=(self.inicio + timedelta(days=7)).isoformat(),
            fecha_fin=(self.inicio + timedelta(days=8)).isoformat(),
        ))
        self.assertIsNone(demostrativa.bloqueo)
        self.assertIsNotNone(real.bloqueo)

    def test_el_ambito_separa_lo_academico_la_investigacion_y_la_produccion(self):
        self.assertEqual(OrdenProduccion(origen='practica').ambito, 'Académico')
        self.assertEqual(OrdenProduccion(origen='investigacion').ambito, 'Investigación')
        self.assertEqual(OrdenProduccion(origen='maquila').ambito, 'Producción real')
        self.assertEqual(OrdenProduccion(origen='propia', demostrativa=True).ambito, 'Producción real · demostrativa')
