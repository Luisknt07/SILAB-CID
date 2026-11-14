from decimal import Decimal

from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.diagramas import Lienzo, cursograma, diagrama_flujo, diagrama_recorrido, numeros_pcc
from apps.plantas_piloto.operacion.presentation.procesos import cursograma_analitico, datos_de_receta
from apps.recursos.models.equipos import EquiposServicios
from tests.integration.test_produccion_planta import BasePlantaProduce


class DiagramasDelProcesoTests(BasePlantaProduce):
    """Los diagramas siguen ASME Y15.3, ISO 5807 y el Codex, y salen iguales en la web y en el PDF."""

    def setUp(self):
        super().setUp()
        # Una planta sin levantamiento: sus equipos todavía no tienen coordenadas.
        EquiposServicios.objects.filter(unidades__laboratorio=self.unidad).update(
            coordenada_x=None, coordenada_y=None, origen_datos_tecnicos='',
        )

    def test_los_pcc_se_numeran_en_el_orden_del_proceso(self):
        datos = datos_de_receta(self.receta_queso)
        criticas = [e['orden'] for e in datos['etapas'] if e['punto_critico']]
        self.assertEqual(numeros_pcc(datos['etapas']), {orden: f'PCC-{i}' for i, orden in enumerate(criticas, 1)})

    def test_el_pdf_de_la_ficha_lleva_los_diagramas_en_vectores(self):
        import pymupdf
        url = reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]) + '?formato=pdf'
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        texto = ''.join(pagina.get_text() for pagina in pymupdf.open(stream=respuesta.content, filetype='pdf'))
        for rotulo in ('DIAGRAMA DE FLUJO DEL PROCESO', 'DIAGRAMA DE OPERACIONES DEL PROCESO (DOP)',
                       'CURSOGRAMA ANALÍTICO (OIT)', 'PCC-1', 'Fin: producto terminado', 'I-1'):
            self.assertIn(rotulo, texto)
        # Los símbolos son formas, no caracteres que Helvetica no tiene.
        for glifo in ('○', '⇨', '▽'):
            self.assertNotIn(glifo, texto)

    def test_la_pagina_muestra_los_tres_diagramas_y_el_tipo_con_tilde(self):
        pagina = self.client.get(reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertContains(pagina, 'Diagrama de flujo del proceso:')
        self.assertContains(pagina, 'Diagrama de operaciones del proceso:')
        self.assertContains(pagina, 'Cursograma analítico:')
        self.assertContains(pagina, '<td>Inspección</td>')
        self.assertNotContains(pagina, '<td>Inspeccion</td>')
        self.assertNotContains(pagina, 'DIAGRAMA DE RECORRIDO')

    def test_el_plan_haccp_usa_los_mismos_pcc_que_su_diagrama(self):
        pagina = self.client.get(reverse('plan_haccp', args=[self.unidad.slug]))
        self.assertContains(pagina, 'class="haccp-diagrama"')
        self.assertContains(pagina, '<span class="haccp-pcc">PCC-1</span>')
        self.assertContains(pagina, 'Diagrama de flujo del proceso:')

    def test_el_recorrido_solo_se_dibuja_con_todas_las_coordenadas(self):
        datos = datos_de_receta(self.receta_queso)
        self.assertIsNone(diagrama_recorrido(datos))
        equipos = {e.equipo_id for e in self.receta_queso.etapas.all() if e.equipo_id}
        for indice, equipo in enumerate(EquiposServicios.objects.filter(pk__in=equipos)):
            equipo.coordenada_x, equipo.coordenada_y = Decimal(indice * 4), Decimal(indice % 3)
            equipo.save(update_fields=['coordenada_x', 'coordenada_y'])
        recorrido = diagrama_recorrido(datos_de_receta(self.receta_queso))
        self.assertIsNotNone(recorrido)
        self.assertIn('Escala: 1 m', recorrido.svg())
        pagina = self.client.get(reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertContains(pagina, 'DIAGRAMA DE RECORRIDO')

    def test_los_dibujos_largos_se_parten_entre_etapas(self):
        datos = datos_de_receta(self.receta_queso)
        lienzo = diagrama_flujo(datos)
        partes = lienzo.dibujos(700, 300)
        self.assertGreater(len(partes), 1)
        self.assertTrue(all(parte.height <= 300.5 for parte in partes))
        # Ninguna figura se pierde ni se repite al partir.
        self.assertEqual(sum(len(parte.contents[0].contents) for parte in partes), len(lienzo.figuras))
        self.assertTrue(cursograma(datos, cursograma_analitico(datos)).dibujos(800, 400))

    def test_los_colores_cortos_se_leen_bien_en_el_pdf(self):
        lienzo = Lienzo(100, 'Prueba')
        lienzo.circulo(50, 20, 10, relleno='#fff')
        figura = lienzo.dibujos(100, 100)[0].contents[0].contents[0]
        self.assertEqual(figura.fillColor.hexval().lower(), '0xffffff')
