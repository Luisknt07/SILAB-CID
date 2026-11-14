"""Planificación: qué producir, qué pedir y cuándo.

Sobre la Planta Piloto de Lácteos cargada: el plan maestro reúne las corridas
del período y trae de una vez la demanda ya comprometida; la explosión de
materiales descuenta bodega y lo que viene en camino y deja lo que falta con
su fecha de pedido; la capacidad enciende su semáforo; el plan firme se
convierte en órdenes; y cada entrega recibida entra al inventario como su lote.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.planificacion import carga_por_dia, explosion_de_materiales, resumen_plan_agregado
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.plantas_piloto.operacion.models.planificacion import EntregaPedido, LineaPlanMaestro, LineaPlanVentas, PedidoAbastecimiento, PlanMaestro, PlanVentas
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_maquila import BaseMaquila


class BasePlanificacion(BaseMaquila):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        # Un lunes futuro, para que el período caiga entero en días de jornada.
        cls.lunes = cls.inicio + timedelta(days=(7 - cls.inicio.weekday()) % 7 or 7)

    def encargo_creado(self):
        """Un encargo de maquila aceptado por la planta, con su proceso y su escala."""
        respuesta = self.encargar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return Reserva.objects.get(pk=respuesta.json()['reserva_id'])

    def crear_plan(self, **extra):
        datos = {
            'modulo': 'plan_maestro',
            'nombre': 'Semana de prueba',
            'desde': self.lunes.isoformat(),
            'hasta': (self.lunes + timedelta(days=4)).isoformat(),
            'estado': 'borrador',
            'observaciones': 'Plan de la semana para la prueba.',
        }
        datos.update(extra)
        respuesta = self.operar(**datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return PlanMaestro.objects.get(pk=respuesta.json()['registro']['id'])

    def agregar_corrida(self, plan, receta, dia, factor='2', **extra):
        datos = {
            'modulo': 'linea_plan',
            'plan_id': plan.pk,
            'receta_id': receta.pk,
            'fecha': dia.isoformat(),
            'factor': factor,
            'origen': 'stock',
        }
        datos.update(extra)
        return self.operar(**datos)

    def accion_plan(self, plan, accion):
        return self.operar(modulo='plan_maestro', registro_id=plan.pk, accion_plan=accion)

    def plan_con_dos_corridas(self):
        plan = self.crear_plan()
        self.assertEqual(self.agregar_corrida(plan, self.receta_queso, self.lunes).status_code, 200)
        self.assertEqual(
            self.agregar_corrida(plan, self.receta_queso, self.lunes + timedelta(days=1)).status_code, 200,
        )
        return plan

    def crear_plan_ventas(self, plan_maestro=None, **extra):
        plan_maestro = plan_maestro or self.crear_plan()
        datos = {
            'modulo': 'plan_ventas',
            'nombre': 'Demanda semanal de prueba',
            'desde': plan_maestro.desde.isoformat(),
            'hasta': plan_maestro.hasta.isoformat(),
            'periodicidad': 'semanal',
            'metodo': 'promedio_movil_3',
            'plan_maestro_id': plan_maestro.pk,
            'observaciones': 'Horizonte comercial verificable.',
        }
        datos.update(extra)
        respuesta = self.operar(**datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return PlanVentas.objects.get(pk=respuesta.json()['registro']['id'])

    def accion_plan_ventas(self, plan, accion):
        return self.operar(
            modulo='plan_ventas',
            registro_id=plan.pk,
            accion_plan_ventas=accion,
        )


class ElPlanDeVentasTests(BasePlanificacion):
    def test_pronostico_crea_demanda_por_producto_y_periodo(self):
        plan = self.crear_plan_ventas()
        respuesta = self.accion_plan_ventas(plan, 'pronosticar')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertGreater(plan.lineas.count(), 0)
        queso = plan.lineas.get(producto=self.receta_queso.producto)
        self.assertEqual(queso.receta, self.receta_queso)
        self.assertEqual(queso.periodo_inicio, plan.desde)
        self.assertEqual(queso.periodo_fin, plan.hasta)
        self.assertEqual(queso.cantidad_planificada, Decimal('0.000'))
        self.assertIn('Demanda estimada', respuesta.json()['message'])

    def test_linea_manual_calcula_total_y_plan_agregado_desde_la_receta(self):
        plan = self.crear_plan_ventas(metodo='manual')
        respuesta = self.operar(
            modulo='linea_plan_ventas',
            plan_id=plan.pk,
            receta_id=self.receta_queso.pk,
            periodo_inicio=plan.desde.isoformat(),
            periodo_fin=plan.hasta.isoformat(),
            pronostico='24',
            ajuste_manual='-2',
            observaciones='Ajuste por mantenimiento previsto.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        linea = LineaPlanVentas.objects.get(plan=plan)
        self.assertEqual(linea.cantidad_planificada, Decimal('22.000'))
        self.assertEqual(linea.demanda_no_comprometida, Decimal('22.000'))
        agregado = resumen_plan_agregado(plan)
        self.assertEqual(len(agregado), 1)
        self.assertEqual(agregado[0]['equivalente_base'], Decimal('183.333'))
        self.assertEqual(agregado[0]['productos'], [linea])

    def test_aprobar_e_incorporar_es_idempotente_y_no_duplica_compromisos(self):
        plan_maestro = self.crear_plan()
        plan = self.crear_plan_ventas(plan_maestro=plan_maestro, metodo='manual')
        respuesta = self.operar(
            modulo='linea_plan_ventas',
            plan_id=plan.pk,
            receta_id=self.receta_queso.pk,
            periodo_inicio=plan.desde.isoformat(),
            periodo_fin=plan.hasta.isoformat(),
            pronostico='24',
            ajuste_manual='0',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(self.accion_plan_ventas(plan, 'aprobar').status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'aprobado')
        primera = self.accion_plan_ventas(plan, 'incorporar')
        self.assertEqual(primera.status_code, 200, primera.content)
        linea = plan_maestro.lineas.get(linea_ventas__plan=plan)
        self.assertEqual(linea.origen, 'demanda')
        self.assertEqual(linea.factor, Decimal('2.000'))
        self.assertEqual(linea.cantidad, Decimal('24.000'))
        segunda = self.accion_plan_ventas(plan, 'incorporar')
        self.assertEqual(segunda.status_code, 200, segunda.content)
        self.assertEqual(plan_maestro.lineas.filter(linea_ventas__plan=plan).count(), 1)

    def test_plan_aprobado_no_se_edita_y_no_se_incorpora_en_otro_plan(self):
        plan = self.crear_plan_ventas(metodo='manual')
        self.assertEqual(
            self.operar(
                modulo='linea_plan_ventas',
                plan_id=plan.pk,
                receta_id=self.receta_queso.pk,
                periodo_inicio=plan.desde.isoformat(),
                periodo_fin=plan.hasta.isoformat(),
                pronostico='12',
            ).status_code,
            200,
        )
        self.assertEqual(self.accion_plan_ventas(plan, 'aprobar').status_code, 200)
        respuesta = self.operar(
            modulo='plan_ventas',
            registro_id=plan.pk,
            nombre='Cambio tardio',
            desde=plan.desde.isoformat(),
            hasta=plan.hasta.isoformat(),
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('ya no se edita', respuesta.json()['error'])

    def test_horizonte_con_demanda_no_deja_lineas_fuera_del_periodo(self):
        plan = self.crear_plan_ventas(metodo='manual')
        self.assertEqual(
            self.operar(
                modulo='linea_plan_ventas',
                plan_id=plan.pk,
                receta_id=self.receta_queso.pk,
                periodo_inicio=plan.desde.isoformat(),
                periodo_fin=plan.hasta.isoformat(),
                pronostico='12',
            ).status_code,
            200,
        )
        respuesta = self.operar(
            modulo='plan_ventas',
            registro_id=plan.pk,
            nombre=plan.nombre,
            desde=(plan.desde + timedelta(days=1)).isoformat(),
            hasta=plan.hasta.isoformat(),
            periodicidad=plan.periodicidad,
            metodo=plan.metodo,
            plan_maestro_id=plan.plan_maestro_id,
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('Quita la demanda calculada', respuesta.json()['error'])
        plan.refresh_from_db()
        self.assertEqual(plan.desde, self.lunes)

    def test_panel_presenta_las_tres_capas_de_planificacion(self):
        plan = self.crear_plan_ventas(metodo='manual')
        self.assertEqual(
            self.operar(
                modulo='linea_plan_ventas',
                plan_id=plan.pk,
                receta_id=self.receta_queso.pk,
                periodo_inicio=plan.desde.isoformat(),
                periodo_fin=plan.hasta.isoformat(),
                pronostico='12',
            ).status_code,
            200,
        )
        self.client.force_login(self.coordinacion)
        pagina = self.client.get(reverse('erp_planta', args=[self.unidad.slug]), {'tab': 'planificacion'})
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'DEMANDA Y PLAN DE VENTAS')
        self.assertContains(pagina, 'PLAN AGREGADO')
        self.assertContains(pagina, 'PLAN MAESTRO')


class ElPlanMaestroTests(BasePlanificacion):
    def test_la_carga_declara_el_plazo_y_el_proveedor_de_cada_materia_prima(self):
        self.assertEqual(self.leche.plazo_reposicion_dias, 1)
        self.assertEqual(self.leche.proveedor_referencia, 'Centro Experimental San Francisco')
        cultivo = Consumible.objects.get(codigo='LAC-INS-CULTIVO-YOG')
        self.assertEqual(cultivo.plazo_reposicion_dias, 20)
        self.assertEqual(cultivo.proveedor_referencia, 'Cultivos y Fermentos Andinos')

    def test_el_plan_guarda_sus_corridas_con_el_producto_que_rinde_la_receta(self):
        plan = self.plan_con_dos_corridas()
        self.assertTrue(plan.codigo.startswith('PM'))
        self.assertEqual(plan.estado, 'borrador')
        lineas = list(plan.lineas.all())
        self.assertEqual(len(lineas), 2)
        primera = lineas[0]
        self.assertEqual(primera.producto.codigo, 'LAC-PRD-QUESO-FRESCO')
        # Dos corridas base de queso rinden 24 kg y ocupan doce horas de proceso.
        self.assertEqual(primera.cantidad, Decimal('24.000'))
        self.assertEqual(primera.horas, Decimal('12.000'))

    def test_una_corrida_fuera_del_periodo_no_entra(self):
        plan = self.crear_plan()
        respuesta = self.agregar_corrida(plan, self.receta_queso, self.lunes + timedelta(days=30))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('fuera del período', respuesta.json()['error'])
        self.assertEqual(plan.lineas.count(), 0)

    def test_un_plan_sin_corridas_no_se_firma(self):
        plan = self.crear_plan()
        respuesta = self.accion_plan(plan, 'firmar')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('sin corridas', respuesta.json()['error'])
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'borrador')

    def test_el_plan_trae_la_demanda_ya_comprometida(self):
        encargo = self.encargo_creado()
        plan = self.crear_plan(
            desde=(encargo.fecha - timedelta(days=2)).isoformat(),
            hasta=(encargo.fecha + timedelta(days=2)).isoformat(),
        )
        respuesta = self.accion_plan(plan, 'proponer')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('Demanda llevada al plan: 1 corridas', respuesta.json()['message'])
        linea = plan.lineas.get()
        self.assertEqual(linea.reserva, encargo)
        self.assertEqual(linea.origen, 'maquila')
        self.assertEqual(linea.receta, self.yogur)
        self.assertEqual(linea.factor, Decimal('2.000'))
        self.assertEqual(linea.fecha, encargo.fecha)
        # Traerla otra vez no la duplica.
        self.assertEqual(self.accion_plan(plan, 'proponer').status_code, 200)
        self.assertEqual(plan.lineas.count(), 1)


class LaExplosionDeMaterialesTests(BasePlanificacion):
    def test_descuenta_la_bodega_y_deja_lo_que_falta_con_su_fecha_de_pedido(self):
        plan = self.plan_con_dos_corridas()
        materiales = {item['consumible'].codigo: item for item in explosion_de_materiales(plan)}
        leche = materiales['LAC-INS-LECHE']
        # Cuatro corridas base de queso piden 400 litros: 200 cada día.
        self.assertEqual(leche['requerido_total'], Decimal('400.000'))
        self.assertEqual([fila['requerido'] for fila in leche['filas']], [Decimal('200.000')] * 2)
        # Hay 400 en bodega, pero el stock de seguridad son 40: el segundo día falta.
        self.assertEqual(leche['falta_total'], Decimal('40.000'))
        self.assertEqual(leche['primera_falta'], self.lunes + timedelta(days=1))
        # Con un día de plazo, la leche se pide la víspera.
        self.assertEqual(leche['pedir_antes_de'], self.lunes)
        self.assertEqual(leche['plazo'], 1)
        # Lo que sobra de sobra no aparece como falta.
        self.assertEqual(materiales['LAC-INS-SAL']['falta_total'], Decimal('0.000'))

    def test_lo_que_ya_viene_en_camino_reduce_lo_que_falta(self):
        plan = self.plan_con_dos_corridas()
        pedido = PedidoAbastecimiento.objects.create(
            unidad=self.unidad, consumible=self.leche, cantidad=Decimal('200.000'),
            fecha_pedido=self.hoy, fecha_entrega_prevista=self.lunes + timedelta(days=1),
            estado='confirmado', creado_por=self.coordinacion,
        )
        EntregaPedido.objects.create(
            pedido=pedido, fecha=self.lunes + timedelta(days=1), cantidad=Decimal('200.000'),
        )
        leche = next(
            item for item in explosion_de_materiales(plan) if item['consumible'] == self.leche
        )
        self.assertEqual(leche['en_camino_total'], Decimal('200.000'))
        self.assertEqual(leche['falta_total'], Decimal('0.000'))
        self.assertIsNone(leche['pedir_antes_de'])

    def test_el_plan_sugiere_sus_pedidos_con_una_entrega_el_dia_que_hace_falta(self):
        plan = self.plan_con_dos_corridas()
        respuesta = self.accion_plan(plan, 'pedidos')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('Pedidos de abastecimiento sugeridos: 1', respuesta.json()['message'])
        pedido = PedidoAbastecimiento.objects.get(plan=plan)
        self.assertEqual(pedido.consumible, self.leche)
        self.assertEqual(pedido.cantidad, Decimal('40.000'))
        self.assertEqual(pedido.proveedor.nombre, 'Centro Experimental San Francisco')
        self.assertEqual(pedido.estado, 'borrador')
        self.assertEqual(pedido.costo_unitario, self.leche.precio_unitario)
        self.assertTrue(pedido.codigo.startswith('PA'))
        entrega = pedido.entregas.get()
        self.assertEqual(entrega.fecha, self.lunes + timedelta(days=1))
        self.assertEqual(entrega.cantidad, Decimal('40.000'))
        # Sugerirlos otra vez no duplica el pedido.
        self.assertEqual(self.accion_plan(plan, 'pedidos').status_code, 200)
        self.assertEqual(PedidoAbastecimiento.objects.filter(plan=plan).count(), 1)


class LaCapacidadTests(BasePlanificacion):
    def test_el_semaforo_se_enciende_cuando_el_dia_no_alcanza(self):
        plan = self.crear_plan()
        # La planta abre trece horas: una corrida de queso cabe de sobra, tres no.
        self.assertEqual(self.agregar_corrida(plan, self.receta_queso, self.lunes, factor='1').status_code, 200)
        self.assertEqual(
            self.agregar_corrida(plan, self.receta_queso, self.lunes + timedelta(days=1), factor='3').status_code,
            200,
        )
        filas = {fila['fecha']: fila for fila in carga_por_dia(plan)}
        primer_dia = filas[self.lunes]
        self.assertEqual(primer_dia['corridas'], 1)
        self.assertEqual(primer_dia['horas'], Decimal('6.000'))
        self.assertEqual(primer_dia['disponibles'], Decimal('13.000'))
        self.assertEqual(primer_dia['porcentaje'], 46)
        self.assertEqual(primer_dia['semaforo'], 'holgado')
        segundo_dia = filas[self.lunes + timedelta(days=1)]
        self.assertEqual(segundo_dia['horas'], Decimal('18.000'))
        self.assertEqual(segundo_dia['semaforo'], 'excedido')
        self.assertGreater(segundo_dia['porcentaje'], 100)
        # El sábado no tiene jornada ni corridas: no aparece en el cuadro.
        self.assertNotIn(self.lunes + timedelta(days=5), filas)


class DelPlanALaOrdenTests(BasePlanificacion):
    def test_un_plan_firme_convierte_cada_corrida_en_su_orden(self):
        plan = self.plan_con_dos_corridas()
        self.assertEqual(self.accion_plan(plan, 'ordenes').status_code, 400)
        self.assertEqual(self.accion_plan(plan, 'firmar').status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'firme')
        respuesta = self.accion_plan(plan, 'ordenes')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('Órdenes de producción creadas: 2', respuesta.json()['message'])
        ordenes = [linea.orden for linea in plan.lineas.select_related('orden').all()]
        self.assertTrue(all(orden is not None for orden in ordenes))
        primera = ordenes[0]
        self.assertEqual(primera.origen, 'propia')
        self.assertEqual(primera.receta, self.receta_queso)
        self.assertEqual(primera.factor, Decimal('2.000'))
        self.assertEqual(primera.fecha_inicio, self.lunes)
        self.assertEqual(primera.linea.codigo, 'LAC-LINEA-PROCESO')
        self.assertTrue(primera.equipos.exists())
        self.assertIn(plan.codigo, primera.observaciones)
        # La línea queda bloqueada en la agenda mientras la corrida está abierta.
        self.assertIsNotNone(primera.bloqueo)
        # Repetir la acción no crea órdenes de más.
        self.assertEqual(self.accion_plan(plan, 'ordenes').status_code, 200)
        self.assertEqual(OrdenProduccion.objects.filter(linea_plan__plan=plan).count(), 2)

    def test_la_corrida_de_un_encargo_toma_la_orden_que_ya_nacio_con_el(self):
        encargo = self.encargo_creado()
        self.assertEqual(self.accion(encargo, 'aprobar').status_code, 200)
        plan = self.crear_plan(
            desde=(encargo.fecha - timedelta(days=1)).isoformat(),
            hasta=(encargo.fecha + timedelta(days=1)).isoformat(),
        )
        self.assertEqual(self.accion_plan(plan, 'proponer').status_code, 200)
        self.assertEqual(self.accion_plan(plan, 'firmar').status_code, 200)
        respuesta = self.accion_plan(plan, 'ordenes')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('Órdenes de producción creadas: 0', respuesta.json()['message'])
        linea = plan.lineas.select_related('orden').get()
        self.assertIsNotNone(linea.orden)
        self.assertEqual(linea.orden, encargo.ordenes_produccion.first())
        self.assertEqual(linea.orden.origen, 'maquila')

    def test_una_corrida_con_orden_no_se_quita_del_plan(self):
        plan = self.plan_con_dos_corridas()
        self.assertEqual(self.accion_plan(plan, 'firmar').status_code, 200)
        self.assertEqual(self.accion_plan(plan, 'ordenes').status_code, 200)
        linea = plan.lineas.first()
        respuesta = self.operar(modulo='linea_plan', registro_id=linea.pk, accion='desactivar')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('cancélala desde producción', respuesta.json()['error'])


class LasEntregasTests(BasePlanificacion):
    def pedido_con_entregas(self):
        plan = self.plan_con_dos_corridas()
        self.assertEqual(self.accion_plan(plan, 'pedidos').status_code, 200)
        pedido = PedidoAbastecimiento.objects.get(plan=plan)
        pedido.estado = 'confirmado'
        pedido.save(update_fields=['estado'])
        return pedido

    def test_recibir_una_entrega_crea_su_lote_y_su_entrada_de_inventario(self):
        pedido = self.pedido_con_entregas()
        entrega = pedido.entregas.get()
        antes = Consumible.objects.get(pk=self.leche.pk).stock_total
        respuesta = self.operar(
            modulo='entrega_pedido',
            registro_id=entrega.pk,
            cantidad='40',
            lote_codigo='LAC-LECHE-ENTREGA-1',
            bodega='Tanque de recepción',
            documento='GR-000123',
            observaciones='Llegó a 4 °C.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        entrega.refresh_from_db()
        self.assertTrue(entrega.recibida)
        self.assertIsNotNone(entrega.recibida_en)
        self.assertEqual(entrega.lote_codigo, 'LAC-LECHE-ENTREGA-1')
        lote = LoteConsumible.objects.get(codigo='LAC-LECHE-ENTREGA-1')
        self.assertEqual(lote.consumible, self.leche)
        self.assertEqual(lote.cantidad_actual, Decimal('40.000'))
        self.assertEqual(lote.estado, 'bodega')
        entrada = EntradaInventario.objects.get(pk=entrega.entrada_id)
        self.assertEqual(entrada.tipo, 'ingreso')
        self.assertEqual(entrada.motivo, 'recepcion')
        self.assertEqual(entrada.referencia, pedido.codigo)
        self.assertEqual(
            Consumible.objects.get(pk=self.leche.pk).stock_total, antes + Decimal('40.000'),
        )
        # Con todo entregado, el pedido queda recibido.
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'recibido')
        self.assertEqual(pedido.pendiente, Decimal('0.000'))

    def test_una_entrega_ya_recibida_no_se_recibe_dos_veces(self):
        pedido = self.pedido_con_entregas()
        entrega = pedido.entregas.get()
        self.assertEqual(
            self.operar(modulo='entrega_pedido', registro_id=entrega.pk, cantidad='40').status_code, 200,
        )
        respuesta = self.operar(modulo='entrega_pedido', registro_id=entrega.pk, cantidad='40')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('ya se recibió', respuesta.json()['error'])

    def test_un_pedido_a_mano_se_parte_en_entregas_diarias(self):
        respuesta = self.operar(
            modulo='pedido_abastecimiento',
            consumible_id=self.leche.pk,
            proveedor='Centro Experimental San Francisco',
            cantidad='1000',
            fecha_pedido=self.hoy.isoformat(),
            fecha_entrega_prevista=self.lunes.isoformat(),
            entregas_diarias='5',
            estado='confirmado',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        pedido = PedidoAbastecimiento.objects.get(pk=respuesta.json()['registro']['id'])
        entregas = list(pedido.entregas.all())
        self.assertEqual(len(entregas), 5)
        self.assertEqual([entrega.cantidad for entrega in entregas], [Decimal('200.000')] * 5)
        self.assertEqual(entregas[0].fecha, self.lunes)
        self.assertEqual(entregas[-1].fecha, self.lunes + timedelta(days=4))
        self.assertEqual(pedido.pendiente, Decimal('1000.000'))


class ElPanelDePlanificacionTests(BasePlanificacion):
    def test_la_pestana_es_de_la_planta_y_muestra_el_plan_vigente(self):
        plan = self.plan_con_dos_corridas()
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertEqual(panel.status_code, 200)
        secciones = {item['clave']: item['habilitada'] for item in panel.context['secciones_gestion']}
        self.assertTrue(secciones['planificacion'])
        self.assertContains(panel, 'data-management-view="planificacion"')
        self.assertContains(panel, 'data-agenda-operation-form="plan_maestro"')
        self.assertContains(panel, 'data-agenda-operation-form="plan_accion"')
        self.assertContains(panel, 'data-agenda-operation-form="linea_plan"')
        self.assertContains(panel, 'data-agenda-operation-form="pedido_abastecimiento"')
        self.assertContains(panel, 'data-agenda-operation-form="entrega_pedido"')
        self.assertContains(panel, plan.codigo)
        self.assertContains(panel, 'Explosión de materiales'.upper())
        self.assertEqual(panel.context['plan_vigente'], plan)
        self.assertEqual(len(panel.context['materiales_faltantes']), 1)

    def test_un_laboratorio_no_tiene_la_pestana_de_planificacion(self):
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin plan', descripcion='Solo reserva.',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
            slug='laboratorio-sin-plan', administrador=self.coordinacion,
        )
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[laboratorio.slug]))
        self.assertEqual(panel.status_code, 200)
        claves = {item['clave'] for item in panel.context['secciones_gestion']}
        self.assertNotIn('planificacion', claves)
        self.assertNotContains(panel, 'data-management-view="planificacion"')

    def test_la_hoja_del_plan_se_imprime_con_sus_tres_cuentas(self):
        plan = self.plan_con_dos_corridas()
        self.client.force_login(self.coordinacion)
        hoja = self.client.get(reverse('plan_maestro', args=[self.unidad.slug, plan.pk]))
        self.assertEqual(hoja.status_code, 200)
        self.assertContains(hoja, f'Plan maestro {plan.codigo}')
        self.assertContains(hoja, 'PROGRAMA DE PRODUCCIÓN')
        self.assertContains(hoja, 'CARGA DE LA CAPACIDAD')
        self.assertContains(hoja, 'EXPLOSIÓN DE MATERIALES')
        self.assertContains(hoja, 'Leche cruda')
        self.assertContains(hoja, 'Queso fresco por 100 litros de leche')

    def test_la_hoja_del_plan_solo_la_ve_quien_opera_la_produccion(self):
        plan = self.plan_con_dos_corridas()
        self.client.force_login(self.estudiante)
        hoja = self.client.get(reverse('plan_maestro', args=[self.unidad.slug, plan.pk]))
        self.assertEqual(hoja.status_code, 403)

    def test_un_plan_cerrado_ya_no_admite_corridas(self):
        plan = self.plan_con_dos_corridas()
        respuesta = self.operar(modulo='plan_maestro', registro_id=plan.pk, accion='desactivar')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, 'cerrado')
        respuesta = self.agregar_corrida(plan, self.yogur, self.lunes)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('cerrado ya no se edita', respuesta.json()['error'])
        self.assertEqual(LineaPlanMaestro.objects.filter(plan=plan).count(), 2)
