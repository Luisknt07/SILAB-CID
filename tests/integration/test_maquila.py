"""Servicios y maquila por proceso: producción por encargo, controlada.

El servicio se liga a un proceso y se pide en lotes; sus materiales por lote
son los insumos del proceso; la reserva guarda el proceso, la escala y si el
cliente trae la materia prima; al aprobar nace la orden de maquila; la planta
recibe la leche del cliente como lote propio, produce, libera por calidad y
entrega con acta; el cliente sigue el avance en su comprobante.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.maquila import expediente_maquila
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.plantas_piloto.operacion.models.produccion import MovimientoProducto, OrdenProduccion, Receta
from apps.reservas.models.reservas import Reserva
from tests.integration.test_laboratorios_institucionales import _dia_habil
from tests.integration.test_produccion_planta import BasePlantaProduce


class BaseMaquila(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.maquila = FablabService.objects.get(code='LAC-SRV-MAQUILA')
        cls.yogur = Receta.objects.get(codigo='LAC-REC-YOGUR-100')
        cls.leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        cls.cultivo = Consumible.objects.get(codigo='LAC-INS-CULTIVO-YOG')
        cls.entrega = _dia_habil(cls.inicio + timedelta(days=4))

    def materiales_sin_leche(self):
        return [
            relacion.consumible_id
            for relacion in self.maquila.service_consumibles.all()
            if relacion.consumible_id != self.leche.pk
        ]

    def encargar(self, materiales=None, **extra):
        datos = self._payload(
            tipo_solicitud='servicio',
            modalidad_servicio='modelo_listo',
            servicios_solicitados=[str(self.maquila.pk)],
            cantidad_piezas='2',
            urgencia_servicio='normal',
            detalle_trabajo='Dos lotes de yogur de mora para la feria de la asociación.',
            fecha_entrega_prevista=self.entrega.isoformat(),
            materiales_seleccionados=json.dumps(materiales if materiales is not None else self.materiales_sin_leche()),
            cotizacion_aceptada='true',
            metodo_pago='transferencia',
        )
        datos.update(extra)
        self.client.force_login(self.docente)
        return self.client.post(reverse('crear_reserva'), datos)

    def accion(self, reserva, accion, **extra):
        self.client.force_login(self.coordinacion)
        datos = {'accion': accion, 'observacion': f'{accion} desde la prueba.'}
        datos.update(extra)
        return self.client.post(reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]), datos)


class ElServicioPorProcesoTests(BaseMaquila):
    def test_el_servicio_ligado_al_proceso_toma_sus_materiales_por_lote(self):
        self.assertEqual(self.maquila.receta, self.yogur)
        self.assertTrue(self.maquila.materia_prima_cliente)
        relaciones = {
            relacion.consumible.codigo: relacion
            for relacion in self.maquila.service_consumibles.select_related('consumible')
        }
        self.assertEqual(
            set(relaciones),
            set(self.yogur.insumos.values_list('consumible__codigo', flat=True)),
        )
        self.assertFalse(relaciones['LAC-INS-LECHE'].obligatorio)
        self.assertEqual(relaciones['LAC-INS-LECHE'].cantidad_sugerida, Decimal('100.000'))
        self.assertTrue(relaciones['LAC-INS-PULPA-MORA'].obligatorio)
        self.assertEqual(relaciones['LAC-EMP-ENVASE-1L'].cantidad_sugerida, Decimal('116.000'))
        # La ficha dice con qué proceso trabaja el servicio y qué es un lote.
        self.client.force_login(self.docente)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'cada lote es una corrida base de 100 litros de leche')
        self.assertContains(ficha, 'puedes traer tu materia prima')
        # La cotización escala los insumos del proceso por lote y deja fuera la leche que trae el cliente.
        cotizacion = self.client.get(reverse('cotizar_servicios_reserva'), {
            'unidad_id': self.unidad.pk, 'servicios': [self.maquila.pk], 'modalidad': 'modelo_listo',
            'piezas': '2', 'urgencia': 'normal', 'seleccion': json.dumps(self.materiales_sin_leche()),
        })
        self.assertEqual(cotizacion.status_code, 200, cotizacion.content)
        datos = cotizacion.json()['cotizacion']
        self.assertEqual(datos['piezas'], 2)
        materiales = {item['nombre']: item for item in datos['materiales_planificados']}
        self.assertIn('Pulpa de mora', materiales)
        self.assertEqual(Decimal(str(materiales['Pulpa de mora']['cantidad'])), Decimal('20.000'))
        self.assertNotIn('Leche cruda', materiales)

    def test_el_encargo_guarda_el_proceso_y_nace_la_orden_de_maquila(self):
        respuesta = self.encargar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.receta, self.yogur)
        self.assertEqual(reserva.factor_proceso, Decimal('2.000'))
        self.assertTrue(reserva.materia_prima_cliente)
        self.assertNotIn(self.leche.pk, [pedido.consumible_id for pedido in reserva.consumibles_solicitados.all()])
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertContains(comprobante, 'Tu encargo')
        self.assertContains(comprobante, 'Solicitud recibida')
        self.assertContains(comprobante, 'Traes tu materia prima')
        # Al aprobar nace la corrida de origen maquila con los equipos del proceso.
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        orden = OrdenProduccion.objects.get(reserva=reserva)
        self.assertEqual(orden.origen, 'maquila')
        self.assertEqual(orden.factor, Decimal('2.000'))
        self.assertEqual(orden.receta, self.yogur)
        self.assertEqual(orden.fecha_inicio, reserva.fecha)
        self.assertGreater(orden.equipos.count(), 0)
        expediente = expediente_maquila(reserva)
        self.assertEqual(expediente['etapa'], 'planificada')
        self.assertTrue(expediente['pendiente_recepcion'])
        self.client.force_login(self.docente)
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertContains(comprobante, 'Corrida planificada')
        # Si la leche la pone la planta, el encargo lo dice y la pide al inventario.
        con_leche = self.encargar(
            materiales=[relacion.consumible_id for relacion in self.maquila.service_consumibles.all()],
            fecha_inicio=f'{_dia_habil(self.inicio + timedelta(days=1)).isoformat()}T08:00',
            fecha_fin=f'{_dia_habil(self.inicio + timedelta(days=1)).isoformat()}T12:00',
        )
        self.assertEqual(con_leche.status_code, 200, con_leche.content)
        otra = Reserva.objects.get(pk=con_leche.json()['reserva_id'])
        self.assertFalse(otra.materia_prima_cliente)
        self.assertIn(self.leche.pk, [pedido.consumible_id for pedido in otra.consumibles_solicitados.all()])

    def test_la_planta_recibe_la_leche_del_cliente_produce_y_entrega_con_acta(self):
        respuesta = self.encargar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(self.accion(reserva, 'aprobar').status_code, 200)
        orden = OrdenProduccion.objects.get(reserva=reserva)
        url = reverse('maquila_expediente', args=[self.unidad.slug, reserva.pk])
        # El cliente no opera el expediente; el laboratorista sí.
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.laboratorista)
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Materia prima del cliente')
        self.assertContains(pagina, 'Registrar la recepción')
        stock_antes = Consumible.objects.get(pk=self.leche.pk).stock_total
        sin_control = self.client.post(url, {
            'accion': 'recepcion', 'consumible_id': self.leche.pk, 'cantidad': '200', 'aprobado': '1',
        })
        self.assertContains(sin_control, 'control de recepción')
        recibida = self.client.post(url, {
            'accion': 'recepcion', 'consumible_id': self.leche.pk, 'cantidad': '200',
            'control_recepcion': 'Prueba de alcohol negativa; acidez 16 °D; 6 °C al llegar.', 'aprobado': '1',
            'documento': 'Guía 0451',
        })
        self.assertEqual(recibida.status_code, 302, recibida.content)
        lote_cliente = LoteConsumible.objects.get(reserva=reserva, material_cliente=True)
        self.assertEqual(lote_cliente.consumible, self.leche)
        self.assertEqual(lote_cliente.cantidad_actual, Decimal('200.000'))
        self.assertEqual(lote_cliente.estado, 'en_uso')
        self.assertEqual(lote_cliente.costo_unitario, Decimal('0'))
        self.assertTrue(lote_cliente.codigo.startswith(f'CLI-{reserva.codigo_reserva}'))
        entrada = EntradaInventario.objects.get(lote_inventario=lote_cliente)
        self.assertEqual((entrada.tipo, entrada.motivo, entrada.responsable_costo), ('ingreso', 'recepcion', 'usuario'))
        self.assertEqual(Consumible.objects.get(pk=self.leche.pk).stock_total, stock_antes + Decimal('200'))
        self.assertFalse(expediente_maquila(reserva)['pendiente_recepcion'])
        # La planta produce con la leche del cliente y deja el lote en cuarentena.
        orden.iniciar()
        orden.refresh_from_db()
        orden.cerrar(
            usuario=self.laboratorista,
            consumos=[{'consumible_id': self.leche.pk, 'lote_id': lote_cliente.pk, 'cantidad': '200'}],
            salidas=[{'producto_id': self.yogur.producto_id, 'cantidad': '230'}],
            observaciones='Corrida del encargo.',
        )
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'terminada')
        lote_cliente.refresh_from_db()
        self.assertEqual(lote_cliente.cantidad_actual, Decimal('0.000'))
        lote = orden.lotes.get(producto=self.yogur.producto)
        self.assertEqual(lote.control_calidad, 'pendiente')
        self.assertEqual(expediente_maquila(reserva)['etapa'], 'terminada')
        # Sin control de calidad aprobado no hay entrega.
        pagina = self.client.get(url)
        self.assertNotContains(pagina, 'Registrar la entrega')
        rechazo = self.client.post(url, {'accion': 'entrega', 'lote_id': lote.pk})
        self.assertContains(rechazo, 'aprobado por calidad')
        lote.aprobar_calidad()
        lote.refresh_from_db()
        self.assertEqual(expediente_maquila(reserva)['etapa'], 'lista')
        entregado = self.client.post(url, {'accion': 'entrega', 'lote_id': lote.pk, 'referencia': 'Acta 2026-014'})
        self.assertEqual(entregado.status_code, 302, entregado.content)
        movimiento = MovimientoProducto.objects.get(lote=lote, tipo='venta')
        self.assertEqual(movimiento.cantidad, Decimal('230.000'))
        self.assertEqual(movimiento.valor_total, Decimal('0'))
        self.assertIsNone(movimiento.movimiento_financiero)
        self.assertEqual(movimiento.referencia, 'Acta 2026-014')
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_disponible, Decimal('0.000'))
        expediente = expediente_maquila(reserva)
        self.assertEqual(expediente['etapa'], 'entregada')
        self.assertEqual(expediente['entregado'], '230')
        # El acta y el certificado: para la planta y para el cliente.
        acta = self.client.get(reverse('acta_entrega_maquila', args=[self.unidad.slug, reserva.pk]))
        self.assertContains(acta, 'Acta de entrega y certificado de calidad')
        self.assertContains(acta, lote.codigo)
        self.assertContains(acta, 'Acta 2026-014')
        self.assertContains(acta, lote_cliente.codigo)
        self.client.force_login(self.docente)
        self.assertContains(self.client.get(reverse('acta_entrega_maquila', args=[self.unidad.slug, reserva.pk])), lote.codigo)
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertContains(comprobante, 'Entregada')
        self.assertContains(comprobante, 'Acta de entrega y certificado')
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(reverse('acta_entrega_maquila', args=[self.unidad.slug, reserva.pk])).status_code, 403)
