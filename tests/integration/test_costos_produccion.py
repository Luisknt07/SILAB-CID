"""El costo de una corrida: insumos, energía de los equipos y mano de obra.

El estándar sale de la receta; el real, de lo que la orden cerrada consumió al
costo de cada lote. Lo que no tiene precio o tarifa queda sin dato, a la vista,
y el costo se declara parcial. La ficha interna del proceso y su PDF traen la
misma tabla; la ficha pública del aula no muestra costos.
"""
from decimal import Decimal
from unittest.mock import patch

from django.http import HttpResponse
from django.urls import reverse

from apps.finanzas.presentation.costos import costo_estandar, costo_real
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, InsumoReceta, Producto, Receta
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_produccion_planta import BasePlantaProduce


class CostoDeLaCorridaTests(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.configuracion = cls.unidad.configuracion_operativa
        cls.configuracion.tarifa_energia_kwh = Decimal('0.1000')
        cls.configuracion.costo_hora_persona = Decimal('5.00')
        cls.configuracion.save(update_fields=['tarifa_energia_kwh', 'costo_hora_persona'])
        cls.sal = Consumible.objects.get(codigo='LAC-INS-SAL')
        cls.sal.precio_unitario = Decimal('2.00')
        cls.sal.save(update_fields=['precio_unitario'])
        cls.pasteurizador = UnidadEquipo.objects.get(codigo_unidad='LAC-EQP-PAST-01').equipo
        cls.pasteurizador.potencia_kw = Decimal('2.000')
        cls.pasteurizador.save(update_fields=['potencia_kw'])
        cls.receta = Receta.objects.create(
            unidad=cls.unidad, producto=Producto.objects.get(codigo='LAC-PRD-QUESO-FRESCO'),
            codigo='LAC-REC-PRUEBA-COSTO', nombre='Receta para probar el costo',
            cantidad_base=Decimal('10'), unidad_base='kg', rendimiento_esperado=Decimal('8'),
        )
        InsumoReceta.objects.create(receta=cls.receta, consumible=cls.sal, cantidad=Decimal('10'))
        EtapaReceta.objects.create(
            receta=cls.receta, orden=1, nombre='Mezclado en caliente', equipo=cls.pasteurizador,
            duracion_min=30, espera_min=30, personas=2,
        )

    def test_el_costo_estandar_suma_insumos_energia_y_mano_de_obra(self):
        costo = costo_estandar(self.receta, self.configuracion)
        # 10 kg × $2 + 2 kW × 1 h × $0,10 + 2 personas × 0,5 h × $5.
        self.assertEqual(costo['insumos_total'], Decimal('20.00'))
        self.assertEqual(costo['kwh'], Decimal('2.00'))
        self.assertEqual(costo['energia'], Decimal('0.20'))
        self.assertEqual(costo['horas_persona'], Decimal('1.00'))
        self.assertEqual(costo['mano_de_obra'], Decimal('5.00'))
        self.assertEqual(costo['total'], Decimal('25.20'))
        self.assertEqual(costo['unitario'], Decimal('3.1500'))
        self.assertTrue(costo['completo'])
        self.assertEqual(costo['avisos'], [])
        # Dos corridas base cuestan el doble y dejan el mismo costo por kilo, como el plan maestro.
        doble = costo_estandar(self.receta, self.configuracion, factor=2)
        self.assertEqual(doble['total'], Decimal('50.40'))
        self.assertEqual(doble['unitario'], Decimal('3.1500'))

    def test_sin_precio_ni_tarifas_el_costo_queda_parcial_y_lo_dice(self):
        self.sal.precio_unitario = None
        self.sal.save(update_fields=['precio_unitario'])
        self.pasteurizador.potencia_kw = None
        self.pasteurizador.save(update_fields=['potencia_kw'])
        self.configuracion.tarifa_energia_kwh = None
        self.configuracion.costo_hora_persona = None
        self.configuracion.save(update_fields=['tarifa_energia_kwh', 'costo_hora_persona'])
        costo = costo_estandar(Receta.objects.get(pk=self.receta.pk), self.configuracion)
        self.assertFalse(costo['completo'])
        self.assertIsNone(costo['energia'])
        self.assertIsNone(costo['mano_de_obra'])
        self.assertEqual(costo['total'], Decimal('0.00'))
        self.assertEqual(costo['filas'][0][2], 'sin precio')
        self.assertIn('Total parcial de la corrida', [fila[0] for fila in costo['filas']])
        self.assertIn(['Nota', costo['avisos'][0], ''], costo['filas'])
        self.assertIn(self.sal.nombre, ' '.join(costo['avisos']))
        self.assertIn(self.pasteurizador.nombre, ' '.join(costo['avisos']))

    def test_la_orden_cerrada_cuesta_lo_que_consumio_al_costo_de_cada_lote(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=self.hoy.isoformat(),
        ))
        self.assertIsNone(costo_real(orden, self.configuracion))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        orden.refresh_from_db()
        costo = costo_real(orden, self.configuracion)
        salidas = EntradaInventario.objects.filter(referencia=orden.codigo, tipo='salida')
        esperado = sum(
            (Decimal(salida.cantidad * salida.costo_unitario).quantize(Decimal('0.01')) for salida in salidas),
            Decimal('0'),
        )
        self.assertEqual(costo['insumos_total'], esperado)
        self.assertEqual(costo['cantidad_producto'], Decimal('22'))
        self.assertEqual(costo['unitario'], (costo['total'] / 22).quantize(Decimal('0.0001')))

    def test_la_consola_muestra_el_costo_de_recetas_y_de_ordenes_cerradas(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=self.hoy.isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        self.client.force_login(self.coordinacion)
        pagina = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        cerrada = next(item for item in pagina.context['ordenes_produccion'] if item.pk == orden.pk)
        # En la consola los montos siguen su formato: coma decimal, como el resto de sus cifras.
        self.assertContains(pagina, 'Costo real $' + str(cerrada.costo['total']).replace('.', ','))
        receta = next(item for item in pagina.context['recetas_unidad'] if item.pk == self.receta.pk)
        self.assertEqual(receta.costo['total'], Decimal('25.20'))
        self.assertContains(pagina, 'Costo estándar $25,20 · $3,1500/kg')

    def test_la_ficha_interna_y_su_pdf_traen_el_costo_y_la_publica_no(self):
        self.client.force_login(self.coordinacion)
        url = reverse('ficha_proceso', args=[self.unidad.slug, self.receta.pk])
        pagina = self.client.get(url)
        self.assertContains(pagina, 'COSTO ESTÁNDAR DE LA CORRIDA BASE')
        self.assertContains(pagina, '$25.20')
        capturado = {}

        def capturar(reporte, nombre, formato):
            capturado['reporte'] = reporte
            return HttpResponse(b'%PDF')

        with patch('apps.documentos.presentation.documentos.respuesta_pdf', side_effect=capturar):
            self.client.get(url, {'formato': 'pdf'})
        tabla = next(
            t for t in capturado['reporte']['dataset']['tablas'] if t['titulo'] == 'COSTO ESTÁNDAR DE LA CORRIDA BASE'
        )
        self.assertEqual(tabla['rows'], pagina.context['costo']['filas'])
        publica = self.client.get(reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertEqual(publica.status_code, 200)
        self.assertNotContains(publica, 'COSTO ESTÁNDAR')

    def test_las_tarifas_se_fijan_en_los_permisos_operativos(self):
        respuesta = self.operar(
            modulo='configuracion', registra_produccion='on', tarifa_referencial_hora_espacio='0',
            tarifa_referencial_hora_equipo='0', tarifa_referencial_hora_software='0',
            tarifa_referencial_hora_acompanamiento='0', aporte_institucional_recursos_pct='100',
            tarifa_energia_kwh='0.0925', costo_hora_persona='',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.configuracion.refresh_from_db()
        self.assertEqual(self.configuracion.tarifa_energia_kwh, Decimal('0.0925'))
        # Vacío es «sin dato», no cero: la mano de obra queda por fijar.
        self.assertIsNone(self.configuracion.costo_hora_persona)
