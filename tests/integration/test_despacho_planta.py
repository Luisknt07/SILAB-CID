"""Despacho de producto: cliente único, cadena de frío y guía de despacho.

Un producto con cadena de frío no sale sin su temperatura ni por encima de su
límite (4 °C refrigerado, −18 °C congelado). El cliente se registra una sola
vez aunque se escriba distinto, y cada despacho tiene su guía con PDF. La
trazabilidad del lote dice a quién fue y a qué temperatura salió.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.finanzas.models.ventas import Cliente
from apps.plantas_piloto.operacion.models.produccion import MovimientoProducto, Producto
from apps.plantas_piloto.operacion.models.erp import SesionERP
from tests.integration.test_produccion_planta import BasePlantaProduce


class ElDespachoDeLaPlantaTests(BasePlantaProduce):
    def despachar(self, lote, **extra):
        datos = {'modulo': 'movimiento_producto', 'lote_id': lote.pk, 'tipo': 'venta', 'cantidad': '2'}
        datos.update(extra)
        return self.operar(**datos)

    def test_sin_temperatura_o_por_encima_del_limite_no_sale(self):
        _orden, lote = self.queso_disponible()
        self.assertTrue(lote.producto.requiere_frio)
        sin_dato = self.despachar(lote)
        self.assertEqual(sin_dato.status_code, 400)
        self.assertIn('registra su temperatura al despacho', sin_dato.json()['error'])
        caliente = self.despachar(lote, temperatura_despacho='7.5')
        self.assertEqual(caliente.status_code, 400)
        self.assertIn('sale a 7.5 °C, por encima de su límite de 4 °C', caliente.json()['error'])
        self.assertFalse(MovimientoProducto.objects.filter(lote=lote).exists())
        frio = self.despachar(lote, temperatura_despacho='3,5')
        self.assertEqual(frio.status_code, 200, frio.content)
        self.assertEqual(MovimientoProducto.objects.get(lote=lote).temperatura_despacho, Decimal('3.5'))
        # Una baja no es un despacho: no pide temperatura.
        self.assertEqual(self.despachar(lote, tipo='baja', motivo='Empaque roto.').status_code, 200)

    def test_un_congelado_se_mide_contra_su_propio_limite(self):
        _orden, lote = self.queso_disponible()
        Producto.objects.filter(pk=lote.producto_id).update(temperatura_maxima=Decimal('-18'))
        lote.refresh_from_db()
        self.assertEqual(lote.producto.conservacion, 'Congelado, hasta -18 °C')
        self.assertEqual(self.despachar(lote, temperatura_despacho='-12').status_code, 400)
        self.assertEqual(self.despachar(lote, temperatura_despacho='-20').status_code, 200)

    def test_el_cliente_es_uno_solo_y_la_consola_lo_muestra_con_sus_compras(self):
        _orden, lote = self.queso_disponible()
        self.assertEqual(self.despachar(lote, cliente='Tienda La Esquina', temperatura_despacho='3').status_code, 200)
        self.assertEqual(self.despachar(lote, cliente='  tienda la   esquina', temperatura_despacho='2').status_code, 200)
        cliente = Cliente.objects.get(nombre__iexact='Tienda La Esquina')
        self.assertEqual(MovimientoProducto.objects.filter(cliente=cliente).count(), 2)
        self.client.force_login(self.coordinacion)
        consola = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        fila = next(item for item in consola.context['clientes_planta'] if item.pk == cliente.pk)
        self.assertEqual(fila.ventas, 2)
        self.assertContains(consola, 'Tienda La Esquina')
        self.assertContains(consola, 'salió a 3 °C')
        respuesta = self.operar(
            modulo='cliente', registro_id=cliente.pk, nombre='Tienda La Esquina', tipo='comercio',
            ruc='0401234567001', telefono='062 900 111', activo='on',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        cliente.refresh_from_db()
        self.assertEqual((cliente.tipo, cliente.ruc), ('comercio', '0401234567001'))

    def test_la_guia_de_despacho_y_su_pdf_y_la_trazabilidad(self):
        _orden, lote = self.queso_disponible()
        self.despachar(lote, cliente='Comisariato del Norte', temperatura_despacho='3', referencia='FAC-001-120')
        movimiento = MovimientoProducto.objects.get(lote=lote)
        url = reverse('guia_despacho', args=[self.unidad.slug, movimiento.pk])
        self.client.force_login(self.coordinacion)
        guia = self.client.get(url)
        self.assertContains(guia, 'Comisariato del Norte')
        self.assertContains(guia, lote.codigo)
        self.assertContains(guia, 'Dentro del límite')
        self.assertContains(guia, 'FAC-001-120')
        self.assertTrue(self.client.get(url, {'formato': 'pdf'}).content.startswith(b'%PDF'))
        traza = self.client.get(reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertContains(traza, 'Comisariato del Norte')
        self.assertContains(traza, 'salió a 3 °C')
        self.assertContains(traza, url)
        # Una baja no tiene guía, y quien no opera la planta no la ve.
        self.despachar(lote, tipo='baja', motivo='Empaque roto.')
        baja = MovimientoProducto.objects.get(lote=lote, tipo='baja')
        self.assertEqual(self.client.get(reverse('guia_despacho', args=[self.unidad.slug, baja.pk])).status_code, 404)
        ajeno = get_user_model().objects.create_user('ajeno.despacho', 'ad@upec.edu.ec', 'Clave-segura-2026')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_la_conservacion_se_declara_en_el_producto_y_en_su_ficha(self):
        queso = Producto.objects.get(codigo='LAC-PRD-QUESO-FRESCO')
        self.assertEqual(queso.conservacion, 'Refrigerado, hasta 4 °C')
        respuesta = self.operar(
            modulo='producto', registro_id=queso.pk, codigo=queso.codigo, nombre=queso.nombre,
            familia_id=queso.familia_id or '', tipo=queso.tipo, unidad_medida=queso.unidad_medida,
            presentacion=queso.presentacion, precio_venta=str(queso.precio_venta),
            vida_util_dias=str(queso.vida_util_dias), requiere_frio='on', temperatura_maxima='5',
            publico='on', activo='on',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        queso.refresh_from_db()
        self.assertEqual(queso.conservacion, 'Refrigerado, hasta 5 °C')
        ficha = self.client.get(reverse('ficha_producto_publica', args=[self.unidad.slug, queso.pk]))
        self.assertContains(ficha, 'Refrigerado, hasta 5 °C')

    def test_en_una_sesion_el_cliente_se_elige_entre_los_registrados(self):
        sesion = SesionERP.demostrativa_de(self.unidad)
        orden = self.orden_de(self.planificar_queso(
            sesion_erp=sesion.codigo, fecha_inicio=self.hoy.isoformat(), fecha_fin=self.hoy.isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden, sesion_erp=sesion.codigo).status_code, 200)
        lote = orden.lotes.get(producto__codigo='LAC-PRD-QUESO-FRESCO')
        lote.aprobar_calidad()
        inventado = self.despachar(lote, sesion_erp=sesion.codigo, cliente='Tienda de práctica',
                                   temperatura_despacho='3')
        self.assertEqual(inventado.status_code, 400)
        self.assertFalse(Cliente.objects.filter(nombre='Tienda de práctica').exists())
        # Al consumidor final sí: la venta de la sesión no entra a las finanzas.
        final = self.despachar(lote, sesion_erp=sesion.codigo, temperatura_despacho='3')
        self.assertEqual(final.status_code, 200, final.content)
