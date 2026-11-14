"""Compras de la planta: proveedores únicos, órdenes de compra y evaluación.

Los pedidos en borrador de un proveedor salen en una sola orden de compra con
número; anularla los devuelve al borrador mientras nada se haya recibido, y al
recibirse todo la orden queda recibida. El proveedor es uno solo aunque se
escriba distinto, y su evaluación sale de las entregas y de los controles de
recepción que la planta ya registra.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.finanzas.presentation.compras import evaluacion_de_proveedores
from apps.plantas_piloto.operacion.presentation.planificacion import recibir_entrega
from apps.recursos.models.consumibles import Consumible
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, PlanCalidad
from apps.finanzas.models.compras import OrdenCompra, Proveedor
from apps.plantas_piloto.operacion.models.planificacion import PedidoAbastecimiento
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration.test_produccion_planta import BasePlantaProduce


class LasComprasDeLaPlantaTests(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        cls.sal = Consumible.objects.get(codigo='LAC-INS-SAL')
        cls.cuajo = Consumible.objects.get(codigo='LAC-INS-CUAJO')
        cls.cuajo.proveedor_referencia = ''
        cls.cuajo.save(update_fields=['proveedor_referencia'])

    def pedir(self, consumible, proveedor='', cantidad='10', **extra):
        datos = {
            'modulo': 'pedido_abastecimiento', 'consumible_id': consumible.pk, 'proveedor': proveedor,
            'cantidad': cantidad, 'costo_unitario': '1.50', 'fecha_pedido': self.hoy.isoformat(),
            'fecha_entrega_prevista': (self.hoy + timedelta(days=2)).isoformat(), 'estado': 'borrador',
        }
        datos.update(extra)
        respuesta = self.operar(**datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return PedidoAbastecimiento.objects.get(pk=respuesta.json()['registro']['id'])

    def emitir(self, **extra):
        return self.operar(modulo='orden_compra', accion='emitir', **extra)

    def test_el_proveedor_es_uno_solo_aunque_se_escriba_distinto(self):
        primero = self.pedir(self.leche, 'Insumos Lácteos del Norte')
        segundo = self.pedir(self.sal, '  insumos lácteos   del norte ')
        self.assertEqual(primero.proveedor_id, segundo.proveedor_id)
        self.assertEqual(Proveedor.objects.filter(nombre__iexact='Insumos Lácteos del Norte').count(), 1)
        # Sin proveedor escrito, el pedido toma el de referencia del insumo.
        self.assertEqual(self.pedir(self.leche).proveedor.nombre, self.leche.proveedor_referencia)

    def test_los_borradores_salen_en_una_orden_por_proveedor_y_sin_proveedor_esperan(self):
        leche = self.pedir(self.leche, 'Lechera del Carchi')
        sal = self.pedir(self.sal, 'Lechera del Carchi')
        otro = self.pedir(self.leche, 'Cultivos Andinos')
        sin_proveedor = self.pedir(self.cuajo)
        self.assertIsNone(sin_proveedor.proveedor)
        respuesta = self.emitir(condiciones='Leche a 4 °C o menos, con guía de remisión.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(
            respuesta.json()['message'],
            '1 pedido sin proveedor sigue en borrador; 2 órdenes de compra emitidas correctamente.',
        )
        for pedido in (leche, sal, otro, sin_proveedor):
            pedido.refresh_from_db()
        self.assertEqual(leche.orden_compra_id, sal.orden_compra_id)
        self.assertNotEqual(leche.orden_compra_id, otro.orden_compra_id)
        self.assertEqual({leche.estado, sal.estado, otro.estado}, {'enviado'})
        self.assertEqual((sin_proveedor.estado, sin_proveedor.orden_compra_id), ('borrador', None))
        orden = leche.orden_compra
        self.assertTrue(orden.codigo.startswith('OC'))
        self.assertEqual(orden.total, leche.costo_total + sal.costo_total)
        # Sin borradores con proveedor no hay nada que emitir.
        self.assertEqual(self.emitir().status_code, 400)

    def test_confirmada_y_recibida_toda_la_orden_queda_recibida(self):
        pedido = self.pedir(self.leche, 'Lechera del Carchi')
        self.emitir()
        orden = OrdenCompra.objects.get(pedidos=pedido)
        self.assertEqual(self.operar(modulo='orden_compra', accion='confirmar', registro_id=orden.pk).status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'confirmado')
        for entrega in pedido.entregas.all():
            recibir_entrega(entrega, {'lote_codigo': f'LAC-OC-{entrega.pk}'}, self.coordinacion)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'recibida')

    def test_anular_devuelve_los_pedidos_al_borrador_salvo_con_entregas_recibidas(self):
        pedido = self.pedir(self.leche, 'Lechera del Carchi', entregas_diarias='2')
        self.emitir()
        orden = OrdenCompra.objects.get(pedidos=pedido)
        self.assertEqual(self.operar(modulo='orden_compra', accion='anular', registro_id=orden.pk).status_code, 200)
        pedido.refresh_from_db()
        orden.refresh_from_db()
        self.assertEqual((pedido.estado, pedido.orden_compra_id, orden.estado), ('borrador', None, 'anulada'))
        self.emitir()
        pedido.refresh_from_db()
        nueva = pedido.orden_compra
        recibir_entrega(pedido.entregas.first(), {}, self.coordinacion)
        respuesta = self.operar(modulo='orden_compra', accion='anular', registro_id=nueva.pk)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('entregas recibidas', respuesta.json()['error'])

    def test_la_hoja_de_la_orden_y_su_pdf_solo_para_quien_abastece(self):
        pedido = self.pedir(self.leche, 'Lechera del Carchi', cantidad='120')
        self.emitir(condiciones='Leche a 4 °C o menos.')
        orden = OrdenCompra.objects.get(pedidos=pedido)
        url = reverse('orden_compra', args=[self.unidad.slug, orden.pk])
        self.client.force_login(self.coordinacion)
        hoja = self.client.get(url)
        self.assertContains(hoja, orden.codigo)
        self.assertContains(hoja, 'Lechera del Carchi')
        self.assertContains(hoja, '120 litro')
        self.assertContains(hoja, '$180.00')
        self.assertContains(hoja, 'Leche a 4 °C o menos.')
        documento = self.client.get(url, {'formato': 'pdf'})
        self.assertTrue(documento.content.startswith(b'%PDF'))
        ajeno = get_user_model().objects.create_user('ajeno.compras', 'ajeno@upec.edu.ec', 'Clave-segura-2026')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_la_evaluacion_mide_puntualidad_y_recepciones(self):
        pedido = self.pedir(self.leche, 'Lechera del Carchi', entregas_diarias='2')
        self.emitir()
        primera, segunda = pedido.entregas.order_by('fecha')
        recibir_entrega(primera, {}, self.coordinacion)
        fila = next(item for item in evaluacion_de_proveedores(self.unidad) if item['proveedor'] == pedido.proveedor)
        self.assertEqual((fila['recibidas'], fila['a_tiempo_pct'], fila['calificacion']), (1, 100, 'confiable'))
        # La segunda se recibe días después de lo previsto y su control de recepción no es conforme.
        recibir_entrega(segunda, {}, self.coordinacion)
        segunda.refresh_from_db()
        segunda.recibida_en = timezone.now() + timedelta(days=10)
        segunda.save(update_fields=['recibida_en'])
        ControlCalidad.objects.create(
            unidad=self.unidad, plan=PlanCalidad.objects.filter(unidad=self.unidad).first(),
            lote_consumible=segunda.entrada.lote_inventario, resultado='no_conforme',
        )
        fila = next(item for item in evaluacion_de_proveedores(self.unidad) if item['proveedor'] == pedido.proveedor)
        self.assertEqual((fila['a_tiempo_pct'], fila['rechazos'], fila['calificacion']), (50, 1, 'critico'))
        self.assertEqual(fila['comprado'], pedido.costo_total)

    def test_la_consola_muestra_compras_y_quien_consulta_no_emite(self):
        pedido = self.pedir(self.leche, 'Lechera del Carchi')
        self.emitir()
        orden = OrdenCompra.objects.get(pedidos=pedido)
        self.client.force_login(self.coordinacion)
        consola = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertContains(consola, reverse('orden_compra', args=[self.unidad.slug, orden.pk]))
        self.assertContains(consola, 'data-agenda-operation-form="orden_compra"')
        self.assertContains(consola, 'Evaluación de proveedores')
        tecnico = get_user_model().objects.create_user('tecnico.compras', 'tc@upec.edu.ec', 'Clave-segura-2026')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=tecnico, nombre='Técnico', rol='tecnico')
        self.client.force_login(tecnico)
        consulta = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertContains(consulta, orden.codigo)
        self.assertNotContains(consulta, 'data-agenda-operation-form="orden_compra"')

    def test_los_datos_del_proveedor_se_corrigen_desde_la_consola(self):
        pedido = self.pedir(self.leche, 'Lechera del Carchi')
        respuesta = self.operar(
            modulo='proveedor', registro_id=pedido.proveedor_id, nombre='Lechera del Carchi',
            ruc='0490012345001', contacto='María Pozo', telefono='062 980 000', email='ventas@lechera.ec',
            rubro='Leche cruda refrigerada',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        proveedor = Proveedor.objects.get(pk=pedido.proveedor_id)
        self.assertEqual((proveedor.ruc, proveedor.contacto), ('0490012345001', 'María Pozo'))
        repetido = self.operar(modulo='proveedor', nombre='lechera del carchi')
        self.assertEqual(repetido.status_code, 400)
        self.assertEqual(Decimal(pedido.costo_unitario), Decimal('1.50'))
