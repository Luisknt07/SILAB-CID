"""El almacén: cobertura del plan, salida por vencimiento y conteo cíclico.

Sobre la Planta Piloto de Lácteos cargada: la cobertura se mide contra lo que
el plan maestro va a consumir, el lote que antes vence sale primero y el que
ya venció se da de baja entero, y el conteo cíclico convierte cada diferencia
en su ajuste del kardex.
"""

from datetime import timedelta
from decimal import Decimal

from django.urls import reverse

from apps.recursos.presentation.almacen import cobertura_del_plan, lotes_por_vencer, orden_de_salida
from apps.recursos.models.almacen import ConteoInventario, LineaConteo
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from tests.integration.test_planificacion import BasePlanificacion


class BaseAlmacen(BasePlanificacion):
    def lote_de_leche(self, codigo, cantidad, vence_en_dias, bodega='Tanque de recepción'):
        return LoteConsumible.objects.create(
            consumible=self.leche,
            codigo=codigo,
            cantidad_inicial=Decimal(cantidad),
            cantidad_actual=Decimal(cantidad),
            estado='bodega',
            bodega=bodega,
            fecha_ingreso=self.hoy - timedelta(days=1),
            fecha_vencimiento=self.hoy + timedelta(days=vence_en_dias),
        )

    def abrir_conteo(self, **extra):
        datos = {'modulo': 'conteo_inventario', 'nombre': 'Conteo de prueba', 'alcance': 'todo'}
        datos.update(extra)
        respuesta = self.operar(**datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return ConteoInventario.objects.get(pk=respuesta.json()['registro']['id'])

    def contar(self, conteo, lote, cantidad):
        linea = LineaConteo.objects.get(conteo=conteo, lote=lote)
        return self.operar(
            modulo='linea_conteo', registro_id=linea.pk, cantidad_contada=str(cantidad),
            observaciones='Contado en el estante.',
        )

    def cerrar(self, conteo):
        return self.operar(modulo='conteo_inventario', registro_id=conteo.pk, accion_conteo='cerrar')


class LaCoberturaTests(BaseAlmacen):
    def test_la_cobertura_se_mide_contra_lo_que_el_plan_va_a_consumir(self):
        plan = self.plan_con_dos_corridas()
        cobertura = cobertura_del_plan(self.unidad)
        self.assertEqual(cobertura['plan'], plan)
        filas = {fila['consumible'].codigo: fila for fila in cobertura['filas']}
        leche = filas['LAC-INS-LECHE']
        # Cuatro corridas base piden 400 litros y en bodega hay 400.
        self.assertEqual(leche['requerido'], Decimal('400.000'))
        self.assertEqual(leche['stock'], Decimal('400.000'))
        self.assertEqual(leche['cobertura_pct'], 100)
        # Pero el stock de seguridad no se toca: faltan 40 litros.
        self.assertEqual(leche['falta'], Decimal('40.000'))
        self.assertEqual(cobertura['sin_cubrir'], 1)
        # La sal sobra de sobra.
        self.assertGreater(filas['LAC-INS-SAL']['cobertura_pct'], 100)

    def test_sin_plan_no_hay_cobertura_que_medir(self):
        cobertura = cobertura_del_plan(self.unidad)
        self.assertIsNone(cobertura['plan'])
        self.assertEqual(cobertura['filas'], [])
        self.assertEqual(cobertura['sin_cubrir'], 0)


class ElVencimientoTests(BaseAlmacen):
    def test_los_lotes_se_ordenan_por_la_fecha_en_que_vencen(self):
        tarde = self.lote_de_leche('LAC-LECHE-TARDE', '100', 20)
        pronto = self.lote_de_leche('LAC-LECHE-PRONTO', '80', 2)
        vencido = self.lote_de_leche('LAC-LECHE-VENCIDO', '30', -3)
        filas = lotes_por_vencer(self.unidad)
        codigos = [fila['lote'].codigo for fila in filas]
        # La planta ya traía sus propios lotes; lo que importa es el orden relativo.
        self.assertLess(codigos.index(vencido.codigo), codigos.index(pronto.codigo))
        self.assertLess(codigos.index(pronto.codigo), codigos.index(tarde.codigo))
        self.assertTrue(filas[0]['vencido'])
        self.assertEqual(
            next(fila['dias'] for fila in filas if fila['lote'] == pronto), 2,
        )
        # De la leche, el que sale primero es el vencido.
        salida = {fila['consumible'].codigo: fila for fila in orden_de_salida(self.unidad)}
        self.assertEqual(salida['LAC-INS-LECHE']['primero'], vencido)
        self.assertIn(pronto, salida['LAC-INS-LECHE']['siguientes'])

    def test_un_lote_vencido_se_da_de_baja_entero(self):
        vencido = self.lote_de_leche('LAC-LECHE-VENCIDO', '30', -3)
        antes = Consumible.objects.get(pk=self.leche.pk).stock_total
        respuesta = self.operar(
            modulo='baja_lote', registro_id=vencido.pk, observaciones='Estaba cortada.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        vencido.refresh_from_db()
        self.assertEqual(vencido.estado, 'caducado')
        self.assertEqual(vencido.cantidad_actual, Decimal('0.000'))
        salida = EntradaInventario.objects.get(lote_inventario=vencido, motivo='caducidad')
        self.assertEqual(salida.tipo, 'salida')
        self.assertEqual(salida.cantidad, Decimal('30.000'))
        self.assertEqual(
            Consumible.objects.get(pk=self.leche.pk).stock_total, antes - Decimal('30.000'),
        )
        # Ya cerrado, no se da de baja dos veces.
        respuesta = self.operar(modulo='baja_lote', registro_id=vencido.pk)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('ya está cerrado', respuesta.json()['error'])


class ElConteoCiclicoTests(BaseAlmacen):
    def test_el_conteo_congela_lo_que_el_sistema_dice_y_ajusta_las_diferencias(self):
        lote = self.lote_de_leche('LAC-LECHE-CONTEO', '100', 10)
        conteo = self.abrir_conteo()
        self.assertTrue(conteo.codigo.startswith('CI'))
        self.assertEqual(conteo.estado, 'abierto')
        linea = LineaConteo.objects.get(conteo=conteo, lote=lote)
        self.assertEqual(linea.cantidad_sistema, Decimal('100.000'))
        self.assertIsNone(linea.cantidad_contada)
        self.assertGreater(conteo.lineas.count(), 1)
        # Faltan diez litros en el estante.
        self.assertEqual(self.contar(conteo, lote, '90').status_code, 200)
        linea.refresh_from_db()
        self.assertEqual(linea.diferencia, Decimal('-10.000'))
        self.assertFalse(linea.cuadra)
        antes = Consumible.objects.get(pk=self.leche.pk).stock_total
        respuesta = self.cerrar(conteo)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('1 ajustes', respuesta.json()['message'])
        conteo.refresh_from_db()
        self.assertEqual(conteo.estado, 'cerrado')
        self.assertIsNotNone(conteo.cerrado_en)
        linea.refresh_from_db()
        self.assertIsNotNone(linea.ajuste)
        self.assertEqual(linea.ajuste.tipo, 'salida')
        self.assertEqual(linea.ajuste.motivo, 'ajuste_negativo')
        self.assertEqual(linea.ajuste.cantidad, Decimal('10.000'))
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal('90.000'))
        self.assertEqual(
            Consumible.objects.get(pk=self.leche.pk).stock_total, antes - Decimal('10.000'),
        )

    def test_lo_que_aparece_de_mas_sube_el_lote_y_entra_como_ajuste_positivo(self):
        lote = self.lote_de_leche('LAC-LECHE-SOBRA', '100', 10)
        conteo = self.abrir_conteo()
        self.assertEqual(self.contar(conteo, lote, '120').status_code, 200)
        self.assertEqual(self.cerrar(conteo).status_code, 200)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal('120.000'))
        self.assertEqual(lote.cantidad_inicial, Decimal('120.000'))
        ajuste = EntradaInventario.objects.get(lote_inventario=lote, motivo='ajuste_positivo')
        self.assertEqual(ajuste.cantidad, Decimal('20.000'))

    def test_lo_que_no_se_conto_no_se_ajusta(self):
        lote = self.lote_de_leche('LAC-LECHE-CONTEO', '100', 10)
        conteo = self.abrir_conteo()
        self.assertEqual(self.contar(conteo, lote, '100').status_code, 200)
        sin_contar = conteo.lineas.exclude(lote=lote).first()
        respuesta = self.cerrar(conteo)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('0 ajustes', respuesta.json()['message'])
        sin_contar.refresh_from_db()
        self.assertIsNone(sin_contar.cantidad_contada)
        self.assertIsNone(sin_contar.ajuste)
        self.assertFalse(EntradaInventario.objects.filter(referencia=conteo.codigo).exists())

    def test_un_conteo_sin_nada_contado_no_se_cierra(self):
        conteo = self.abrir_conteo()
        respuesta = self.cerrar(conteo)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('no se contó ningún lote', respuesta.json()['error'])
        conteo.refresh_from_db()
        self.assertEqual(conteo.estado, 'abierto')

    def test_un_conteo_cerrado_ya_no_recibe_conteos(self):
        lote = self.lote_de_leche('LAC-LECHE-CONTEO', '100', 10)
        conteo = self.abrir_conteo()
        self.assertEqual(self.contar(conteo, lote, '100').status_code, 200)
        self.assertEqual(self.cerrar(conteo).status_code, 200)
        respuesta = self.contar(conteo, lote, '95')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('ya está cerrado', respuesta.json()['error'])

    def test_el_alcance_acota_los_lotes_que_entran(self):
        propio = self.lote_de_leche('LAC-LECHE-CAMARA', '50', 10, bodega='Cámara de frío')
        conteo = self.abrir_conteo(alcance='bodega', referencia='Cámara de frío')
        self.assertEqual(conteo.alcance, 'bodega')
        self.assertEqual([linea.lote for linea in conteo.lineas.all()], [propio])
        # Sin decir qué bodega, no se abre.
        respuesta = self.operar(modulo='conteo_inventario', nombre='Sin referencia', alcance='bodega')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('qué bodega', respuesta.json()['error'])


class ElPanelDelAlmacenTests(BaseAlmacen):
    def test_el_modo_almacen_aparece_con_sus_tarjetas(self):
        self.plan_con_dos_corridas()
        self.lote_de_leche('LAC-LECHE-VENCIDO', '30', -3)
        conteo = self.abrir_conteo()
        self.client.force_login(self.coordinacion)
        panel = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=recursos&modo_recursos=almacen'
        )
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context['modo_recursos'], 'almacen')
        self.assertTrue(panel.context['almacen_habilitado'])
        self.assertContains(panel, 'data-resources-pane="almacen"')
        self.assertContains(panel, 'data-agenda-operation-form="conteo_inventario"')
        self.assertContains(panel, 'data-agenda-operation-form="linea_conteo"')
        self.assertContains(panel, 'data-agenda-operation-form="baja_lote"')
        self.assertContains(panel, 'COBERTURA DESDE EL PLAN')
        self.assertContains(panel, 'LAC-LECHE-VENCIDO')
        self.assertContains(panel, conteo.codigo)
        self.assertEqual(len(panel.context['lotes_vencidos']), 1)
        self.assertEqual(panel.context['cobertura_plan']['sin_cubrir'], 1)

    def test_una_unidad_sin_inventario_no_tiene_almacen(self):
        from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad

        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        configuracion.consumibles = False
        configuracion.save(update_fields=['consumibles'])
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
                                {'view': 'recursos', 'modo_recursos': 'almacen'})
        self.assertEqual(panel.status_code, 200)
        self.assertFalse(panel.context['almacen_habilitado'])
        self.assertNotContains(panel, 'data-resources-pane="almacen"')
