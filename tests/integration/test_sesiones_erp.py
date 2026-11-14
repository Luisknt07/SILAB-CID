"""Las sesiones del ERP: docentes y estudiantes practican sin tocar la producción real.

El docente abre una sesión de práctica y dicta la clave; los estudiantes entran
con ella y operan la cadena completa. Lo de una sesión no descuenta el inventario
real, no cuenta en los indicadores y no se ve desde la producción real ni desde
otra sesión; sus existencias parten de una foto del inventario. Un estudiante no
opera la producción real ni los datos maestros, y una sesión cerrada se consulta
pero ya no se opera.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.recursos.models.consumibles import Consumible
from apps.plantas_piloto.operacion.models.erp import ExistenciaSesion, SesionERP
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion
from apps.plantas_piloto.operacion.models.planificacion import PedidoAbastecimiento
from apps.finanzas.models.compras import Proveedor
from tests.integration.test_produccion_planta import BasePlantaProduce
from tests.integration.utiles import identificar


class LasSesionesDelErpTests(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Usuario = get_user_model()
        cls.docente_erp = Usuario.objects.create_user('docente.erp', 'docente.erp@upec.edu.ec', 'Clave-segura-2026')
        identificar(cls.docente_erp, tipo_usuario='docente')
        cls.estudiante = Usuario.objects.create_user('estudiante.erp', 'est.erp@upec.edu.ec', 'Clave-segura-2026')
        identificar(cls.estudiante, tipo_usuario='estudiante')
        cls.otro = Usuario.objects.create_user('otro.erp', 'otro.erp@upec.edu.ec', 'Clave-segura-2026')
        identificar(cls.otro, tipo_usuario='estudiante')
        cls.leche = Consumible.objects.get(codigo='LAC-INS-LECHE')

    def abrir_practica(self, nombre='Quesos frescos, paralelo A'):
        self.client.force_login(self.docente_erp)
        respuesta = self.client.post(reverse('erp_sesion_accion', args=[self.unidad.slug]), {
            'accion': 'crear', 'tipo': 'practica', 'nombre': nombre,
        })
        self.assertEqual(respuesta.status_code, 302)
        return SesionERP.objects.get(nombre=nombre)

    def unirse(self, usuario, sesion):
        self.client.force_login(usuario)
        return self.client.post(reverse('erp_sesion_accion', args=[self.unidad.slug]), {
            'accion': 'unirse', 'clave': sesion.clave_acceso.lower(),
        })

    def erp(self, usuario, sesion=None):
        self.client.force_login(usuario)
        url = reverse('erp_planta', args=[self.unidad.slug])
        return self.client.get(url, {'sesion': sesion.codigo} if sesion else {})

    def planificar_en(self, sesion, usuario, **extra):
        self.client.force_login(usuario)
        return self.planificar_queso(usuario=usuario, sesion_erp=sesion.codigo if sesion else '', **extra)

    def test_un_estudiante_sin_sesion_solo_ve_sus_sesiones(self):
        pagina = self.erp(self.estudiante)
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.context['vista_gestion'], 'sesiones')
        self.assertEqual([seccion['clave'] for seccion in pagina.context['secciones_navegacion']], ['sesiones'])
        self.assertNotContains(pagina, 'data-management-view="produccion"')
        self.assertContains(pagina, 'Unirse a una práctica')
        # Tampoco opera la producción real.
        self.assertEqual(self.planificar_en(None, self.estudiante).status_code, 403)

    def test_el_docente_abre_la_practica_y_el_grupo_entra_con_la_clave(self):
        sesion = self.abrir_practica()
        self.assertEqual((sesion.tipo, sesion.responsable, sesion.estado), ('practica', self.docente_erp, 'abierta'))
        self.assertEqual(len(sesion.clave_acceso), 6)
        foto = ExistenciaSesion.objects.get(sesion=sesion, consumible=self.leche)
        self.assertEqual(foto.cantidad, self.leche.stock_total)
        self.assertEqual(self.unirse(self.estudiante, sesion).status_code, 302)
        self.assertTrue(sesion.miembros.filter(pk=self.estudiante.pk).exists())
        pagina = self.erp(self.estudiante, sesion)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'data-agenda-operation-form="orden_produccion"')
        self.assertContains(pagina, f'data-sesion-erp="{sesion.codigo}"')
        # Quien no entró con la clave no ve la sesión.
        self.assertEqual(self.erp(self.otro, sesion).status_code, 403)

    def test_lo_de_una_sesion_no_toca_la_produccion_real_ni_otra_sesion(self):
        sesion = self.abrir_practica()
        self.unirse(self.estudiante, sesion)
        respuesta = self.planificar_en(sesion, self.estudiante)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        orden = self.orden_de(respuesta)
        self.assertEqual(orden.sesion, sesion)
        self.assertTrue(orden.demostrativa)
        real = self.erp(self.coordinacion)
        self.assertNotIn(orden, real.context['ordenes_produccion'])
        otra = self.abrir_practica('Otro paralelo')
        self.assertNotIn(orden, self.erp(self.docente_erp, otra).context['ordenes_produccion'])
        self.assertIn(orden, self.erp(self.estudiante, sesion).context['ordenes_produccion'])
        # Una orden de la sesión no se edita desde la producción real.
        editar = self.planificar_en(None, self.coordinacion, registro_id=orden.pk)
        self.assertEqual(editar.status_code, 404)

    def test_el_cierre_descuenta_las_existencias_de_la_sesion_y_no_las_reales(self):
        sesion = self.abrir_practica()
        self.unirse(self.estudiante, sesion)
        orden = self.orden_de(self.planificar_en(
            sesion, self.estudiante, fecha_inicio=self.hoy.isoformat(), fecha_fin=self.hoy.isoformat(),
        ))
        stock_real = Consumible.objects.get(pk=self.leche.pk).stock_total
        antes = ExistenciaSesion.objects.get(sesion=sesion, consumible=self.leche).cantidad
        self.client.force_login(self.estudiante)
        cierre = self.cerrar_queso(orden, sesion_erp=sesion.codigo)
        self.assertEqual(cierre.status_code, 200, cierre.content)
        self.assertEqual(Consumible.objects.get(pk=self.leche.pk).stock_total, stock_real)
        self.assertEqual(ExistenciaSesion.objects.get(sesion=sesion, consumible=self.leche).cantidad,
                         antes - Decimal('200'))
        orden.refresh_from_db()
        self.assertTrue(all(lote.demostrativo for lote in orden.lotes.all()))

    def test_el_pedido_recibido_en_la_sesion_suma_a_sus_existencias(self):
        sesion = self.abrir_practica()
        self.unirse(self.estudiante, sesion)
        self.client.force_login(self.estudiante)
        datos = {
            'modulo': 'pedido_abastecimiento', 'sesion_erp': sesion.codigo, 'consumible_id': self.leche.pk,
            'cantidad': '50', 'fecha_pedido': self.hoy.isoformat(),
            'fecha_entrega_prevista': (self.hoy + timedelta(days=1)).isoformat(), 'estado': 'confirmado',
        }
        # Un proveedor inventado en la práctica no entra al maestro de la institución.
        inventado = self.operar(usuario=self.estudiante, proveedor='Lechera de práctica', **datos)
        self.assertEqual(inventado.status_code, 400)
        self.assertFalse(Proveedor.objects.filter(nombre='Lechera de práctica').exists())
        respuesta = self.operar(usuario=self.estudiante, **datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        pedido = PedidoAbastecimiento.objects.get(pk=respuesta.json()['registro']['id'])
        self.assertEqual(pedido.sesion, sesion)
        antes = ExistenciaSesion.objects.get(sesion=sesion, consumible=self.leche).cantidad
        entrega = pedido.entregas.get()
        recibida = self.operar(usuario=self.estudiante, modulo='entrega_pedido', sesion_erp=sesion.codigo,
                               registro_id=entrega.pk, cantidad='50')
        self.assertEqual(recibida.status_code, 200, recibida.content)
        self.assertEqual(ExistenciaSesion.objects.get(sesion=sesion, consumible=self.leche).cantidad,
                         antes + Decimal('50'))
        entrega.refresh_from_db()
        self.assertIsNone(entrega.entrada_id)
        self.assertNotIn(pedido, self.erp(self.coordinacion).context['pedidos_abastecimiento'])

    def test_en_una_sesion_no_se_tocan_los_datos_maestros_y_cerrada_no_se_opera(self):
        sesion = self.abrir_practica()
        self.unirse(self.estudiante, sesion)
        maestro = self.operar(usuario=self.estudiante, modulo='producto', sesion_erp=sesion.codigo,
                              codigo='LAC-PRD-PRUEBA', nombre='Producto de prueba', tipo='terminado',
                              unidad_medida='kg')
        self.assertEqual(maestro.status_code, 403)
        self.client.force_login(self.docente_erp)
        self.client.post(reverse('erp_sesion_accion', args=[self.unidad.slug]),
                         {'accion': 'cerrar', 'sesion_erp': sesion.codigo})
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, 'cerrada')
        self.assertEqual(self.planificar_en(sesion, self.estudiante).status_code, 403)
        consulta = self.erp(self.estudiante, sesion)
        self.assertEqual(consulta.status_code, 200)
        self.assertNotContains(consulta, 'data-agenda-operation-open="orden_produccion"')

    def test_un_estudiante_abre_su_sesion_individual_y_no_una_de_practica(self):
        self.client.force_login(self.estudiante)
        url = reverse('erp_sesion_accion', args=[self.unidad.slug])
        self.assertEqual(self.client.post(url, {'accion': 'crear', 'tipo': 'practica', 'nombre': 'Mía'}).status_code, 403)
        self.assertEqual(self.client.post(url, {'accion': 'crear', 'tipo': 'individual', 'nombre': 'Mía'}).status_code, 302)
        sesion = SesionERP.objects.get(nombre='Mía')
        self.assertEqual((sesion.tipo, sesion.responsable), ('individual', self.estudiante))
        # Una sesión individual no admite que otros entren con su clave.
        self.assertEqual(self.unirse(self.otro, sesion).status_code, 400)

    def test_la_coordinacion_sigue_las_sesiones_desde_la_consola(self):
        sesion = self.abrir_practica()
        self.unirse(self.estudiante, sesion)
        self.orden_de(self.planificar_en(sesion, self.estudiante))
        self.client.force_login(self.coordinacion)
        consola = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'practicas'})
        self.assertContains(consola, sesion.codigo)
        self.assertContains(consola, f'{reverse("erp_planta", args=[self.unidad.slug])}?sesion={sesion.codigo}')
        self.assertEqual(OrdenProduccion.objects.filter(sesion=sesion).count(), 1)
