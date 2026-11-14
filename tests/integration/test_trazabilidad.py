"""Trazabilidad de un lote y reporte institucional.

Sobre la Planta Piloto de Lácteos cargada: la hoja de un lote reconstruye de
dónde salió (la corrida, la sesión, cada lote de insumo y su control de
recepción) y a dónde fue (sus controles de calidad y sus movimientos); el
reporte institucional pone una fila por unidad administrada.
"""

from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.trazabilidad import consolidado_institucional, trazabilidad_de_lote
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, PlanCalidad
from apps.plantas_piloto.operacion.models.produccion import LoteProducto
from tests.integration.test_calidad import BaseCalidad


class BaseTrazabilidad(BaseCalidad):
    def lote_liberado(self):
        """Un lote de queso producido y liberado por su control de calidad."""
        lote = self.lote_de_queso_en_cuarentena()
        self.assertEqual(self.controlar(self.plan_queso, f'lote_producto={lote.pk}').status_code, 302)
        lote.refresh_from_db()
        return lote


class LaHojaDeTrazabilidadTests(BaseTrazabilidad):
    def test_la_cadena_reconstruye_de_donde_salio_el_lote(self):
        lote = self.lote_liberado()
        cadena = trazabilidad_de_lote(lote)
        self.assertEqual(cadena['orden'], lote.orden)
        self.assertEqual(cadena['receta'], self.receta_queso)
        # Los seis insumos que la corrida descontó, con su lote.
        consumidos = {fila['consumible'].codigo for fila in cadena['consumos']}
        self.assertIn('LAC-INS-LECHE', consumidos)
        self.assertIn('LAC-EMP-ETIQUETA', consumidos)
        leche = next(fila for fila in cadena['consumos'] if fila['consumible'].codigo == 'LAC-INS-LECHE')
        self.assertIsNotNone(leche['lote'])
        self.assertEqual(leche['salida'].cantidad, Decimal('200.000'))
        self.assertEqual(leche['salida'].motivo, 'consumo_produccion')
        # Los puntos de control del proceso viajan con la cadena: el PCC de inocuidad y los PC de calidad.
        controles = {etapa.nombre: etapa.punto_critico for etapa in cadena['puntos_de_control']}
        self.assertEqual(controles['Pasteurización'], True)
        self.assertEqual(controles['Recepción y control de la leche'], False)
        self.assertTrue(cadena['equipos'])

    def test_la_cadena_muestra_los_controles_y_las_salidas(self):
        lote = self.lote_liberado()
        cadena = trazabilidad_de_lote(lote)
        self.assertEqual(len(cadena['controles']), 1)
        control = cadena['controles'][0]
        self.assertEqual(control.resultado, 'conforme')
        self.assertEqual(control.mediciones.count(), 5)
        self.assertEqual(cadena['no_conformidades'], [])
        self.assertEqual(cadena['movimientos'], [])
        # Una venta aparece en la cadena hacia adelante.
        respuesta = self.operar(
            modulo='movimiento_producto', lote_id=lote.pk, tipo='venta', cantidad='5',
            destino='Feria agroproductiva', precio_unitario='6.50', referencia='F-001', temperatura_despacho='3',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        cadena = trazabilidad_de_lote(LoteProducto.objects.get(pk=lote.pk))
        self.assertEqual(len(cadena['movimientos']), 1)
        self.assertEqual(cadena['entregado'], Decimal('5.000'))

    def test_la_no_conformidad_queda_en_la_cadena(self):
        lote = self.lote_de_queso_en_cuarentena()
        self.assertEqual(
            self.controlar(self.plan_queso, f'lote_producto={lote.pk}', **{'pH del queso': '5.2'}).status_code,
            302,
        )
        cadena = trazabilidad_de_lote(LoteProducto.objects.get(pk=lote.pk))
        self.assertEqual(len(cadena['no_conformidades']), 1)
        self.assertEqual(cadena['controles'][0].resultado, 'no_conforme')

    def test_la_hoja_se_imprime_y_solo_la_ve_quien_opera_la_produccion(self):
        lote = self.lote_liberado()
        self.client.force_login(self.coordinacion)
        hoja = self.client.get(reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertEqual(hoja.status_code, 200)
        self.assertContains(hoja, f'Lote {lote.codigo}')
        self.assertContains(hoja, 'DE DÓNDE SALIÓ')
        self.assertContains(hoja, 'CON QUÉ SE HIZO')
        self.assertContains(hoja, 'A DÓNDE FUE')
        self.assertContains(hoja, 'Leche cruda')
        self.assertContains(hoja, lote.orden.codigo)
        self.client.force_login(self.estudiante)
        negada = self.client.get(reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertEqual(negada.status_code, 403)

    def test_la_produccion_enlaza_la_trazabilidad_de_cada_lote(self):
        lote = self.lote_liberado()
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertEqual(panel.status_code, 200)
        self.assertContains(panel, reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))


class ElReporteInstitucionalTests(BaseTrazabilidad):
    def test_administrador_integra_reporte_filtros_y_pdf(self):
        from django.contrib.auth import get_user_model
        direccion = get_user_model().objects.create_superuser('reporte-direccion', 'direccion@example.test', 'clave')
        self.client.force_login(direccion)
        url = reverse('admin:reportes-institucional')
        filtros = {'desde': '2026-01-01', 'hasta': '2026-09-25'}
        anterior = self.client.get(reverse('reporte_institucional'), filtros)
        self.assertEqual(anterior.status_code, 302)
        self.assertIn(url, anterior.url)
        self.assertIn('desde=2026-01-01', anterior.url)
        pagina = self.client.get(url, filtros)
        self.assertContains(pagina, 'Reportes e indicadores')
        self.assertContains(pagina, 'data-ver-pdf')
        self.assertContains(pagina, '2026-01-01')
        self.assertNotContains(pagina, 'target="_blank"')
        pdf = self.client.get(url, {**filtros, 'formato': 'pdf'})
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.client.force_login(self.estudiante)
        self.assertNotEqual(self.client.get(url).status_code, 200)

    def test_el_consolidado_cuenta_lo_que_la_unidad_hizo(self):
        self.lote_liberado()
        consolidado = consolidado_institucional(
            self.coordinacion, self.hoy - self.dias(30), self.hoy + self.dias(30),
        )
        fila = next(item for item in consolidado['filas'] if item['unidad'] == self.unidad)
        self.assertEqual(fila['corridas'], 1)
        self.assertGreaterEqual(fila['lotes'], 1)
        self.assertEqual(fila['liberados'], 1)
        self.assertEqual(fila['controles'], 1)
        self.assertEqual(fila['conformes'], 1)
        self.assertEqual(consolidado['totales']['conformidad_pct'], 100)
        self.assertGreaterEqual(consolidado['totales']['unidades'], 1)

    def dias(self, cantidad):
        from datetime import timedelta

        return timedelta(days=cantidad)

    def test_la_hoja_institucional_lista_las_unidades_administradas(self):
        self.lote_liberado()
        self.client.force_login(self.coordinacion)
        hoja = self.client.get(reverse('reporte_institucional'))
        self.assertEqual(hoja.status_code, 200)
        self.assertContains(hoja, 'Reporte institucional')
        self.assertContains(hoja, self.unidad.nombre)
        self.assertContains(hoja, 'UNIDAD POR UNIDAD')
        self.assertEqual(len(hoja.context['filas']), 1)

    def test_quien_no_administra_ninguna_unidad_no_lo_ve(self):
        self.client.force_login(self.estudiante)
        negada = self.client.get(reverse('reporte_institucional'))
        self.assertEqual(negada.status_code, 403)

    def test_la_pestana_de_reportes_ofrece_calidad_y_aula(self):
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=reportes&categoria_reporte=control-calidad')
        self.assertEqual(panel.status_code, 200)
        categorias = dict(panel.context['reporte_gestion']['choices']['categories'])
        self.assertIn('control-calidad', categorias)
        self.assertIn('aula', categorias)
        self.assertContains(panel, reverse('reporte_institucional'))

    def test_el_reporte_de_calidad_lista_los_controles_con_sus_mediciones(self):
        lote = self.lote_liberado()
        self.client.force_login(self.coordinacion)
        reporte = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=reportes&categoria_reporte=control-calidad'
        )
        self.assertEqual(reporte.status_code, 200)
        datos = reporte.context['reporte_gestion']['dataset']
        self.assertEqual(datos['headers'][0], 'Fecha')
        self.assertEqual(len(datos['rows']), 1)
        fila = datos['rows'][0]
        plan = PlanCalidad.objects.get(codigo='LAC-CAL-LIBERACION-QUESO')
        self.assertIn(plan.nombre, fila[1])
        self.assertIn(plan.codigo, fila[1])
        por_columna = dict(zip(datos['headers'], fila))
        self.assertIn(lote.codigo, por_columna['Lote / orden'])
        self.assertEqual(por_columna['Resultado registrado'], 'Conforme')
        mediciones = next(tabla for tabla in datos['tablas']
                          if tabla['titulo'] == 'Métodos, límites y resultados de los controles')
        self.assertTrue(any(fila[1] == 'pH del queso' for fila in mediciones['rows']))
        self.assertEqual(
            dict(datos['cards'])['Registros de origen'], ControlCalidad.objects.reales().filter(unidad=self.unidad).count(),
        )
