"""La portada de cada pestaña de la ficha, y el documento que no se repite.

Antes, al cambiar de pestaña el visor se quedaba con el documento de la
anterior: quien pasaba de «Procesos y protocolos» a «Calidad e inocuidad»
seguía viendo la ficha del proceso que acababa de abrir, con su nombre en el
encabezado. Ahora cada pestaña trae su portada, que explica qué es la sección,
qué contiene de verdad, de dónde salen sus datos y cómo se lee.
"""

from decimal import Decimal

from apps.formacion.presentation.aula import carpetas_del_aula, procesos_publicos
from apps.gestion_unidades.presentation.portadas import EXPLICACIONES, portadas_de
from apps.plantas_piloto.operacion.presentation.procesos import datos_de_receta
from tests.integration.test_produccion_planta import BasePlantaProduce


class LasPortadasDeLaFichaTests(BasePlantaProduce):
    def portadas(self):
        modulos = list(self.unidad.modulos_contenido.filter(activo=True).order_by('orden'))
        carpetas = carpetas_del_aula(self.unidad, modulos, procesos_publicos(self.unidad))
        return {portada['clave']: portada for portada in portadas_de(self.unidad, modulos, carpetas)}

    def test_cada_pestana_trae_su_portada_con_su_explicacion(self):
        portadas = self.portadas()
        claves = set(portadas)
        self.assertIn('procesos-protocolos', claves)
        self.assertIn('calidad-inocuidad', claves)
        # Una por módulo activo, ni más ni menos.
        self.assertEqual(len(portadas), self.unidad.modulos_contenido.filter(activo=True).count())
        procesos = portadas['procesos-protocolos']
        self.assertEqual(procesos['entrada'], EXPLICACIONES['procesos-protocolos']['entrada'])
        self.assertIn('receta cargada en la planta', procesos['datos'])
        self.assertGreaterEqual(len(procesos['como_leerlo']), 2)

    def test_la_portada_lista_lo_que_la_pestana_publica_de_verdad(self):
        procesos = self.portadas()['procesos-protocolos']
        nombres = [elemento['nombre'] for elemento in procesos['elementos']]
        self.assertFalse(procesos['vacia'])
        # En Plantas Piloto la portada resume las secciones y no repite cada
        # proceso que ya está en el acordeón lateral.
        self.assertIn('Sistemas de producción', nombres)
        self.assertIn('Simuladores y cálculo del proceso', nombres)
        self.assertNotIn('Queso fresco', nombres)
        self.assertTrue(all(not elemento['carpeta'] for elemento in procesos['elementos']))

    def test_una_pestana_sin_contenido_lo_dice(self):
        modulo = self.unidad.modulos_contenido.create(
            clave='pestana-vacia', nombre='Pestaña vacía', orden=99,
        )
        portadas = self.portadas()
        vacia = portadas[modulo.clave]
        self.assertTrue(vacia['vacia'])
        self.assertEqual(vacia['elementos'], [])
        # Sin explicación propia recibe la genérica, no un texto en blanco.
        self.assertTrue(vacia['entrada'])
        self.assertTrue(vacia['datos'])

    def test_la_ficha_publica_lleva_una_portada_por_pestana(self):
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        portadas = pagina.context['portadas_modulo']
        self.assertEqual(len(portadas), self.unidad.modulos_contenido.filter(activo=True).count())
        for portada in portadas:
            with self.subTest(modulo=portada['clave']):
                self.assertContains(pagina, f'data-portada-modulo="{portada["clave"]}"')
        self.assertContains(pagina, 'Qué vas a encontrar')
        self.assertContains(pagina, 'De dónde salen los datos')
        # El encabezado del visor puede cambiar de etiqueta: es archivo o sección.
        self.assertContains(pagina, 'id="viewer-eyebrow"')

    def test_las_unidades_sin_mapa_conservan_el_detalle_de_sus_recursos(self):
        # Una tipología sin mapa numerado (una que cree la institución) conserva las carpetas tal como las publica.
        self.unidad.dependencia = 'tipologia_institucional'
        self.unidad.save(update_fields=['dependencia'])
        modulos = list(self.unidad.modulos_contenido.filter(activo=True).order_by('orden'))
        carpetas = carpetas_del_aula(self.unidad, modulos, procesos_publicos(self.unidad))

        self.assertIn('DocumentacionProcesos', {carpeta['id'] for carpeta in carpetas})
        portadas = {portada['clave']: portada for portada in portadas_de(self.unidad, modulos, carpetas)}
        nombres = [elemento['nombre'] for elemento in portadas['procesos-protocolos']['elementos']]
        self.assertIn('Queso fresco', nombres)
        self.assertIn('Balance de materia y energía', nombres)


class ElDocumentoNoSeRepiteTests(BasePlantaProduce):
    def test_la_pagina_embebible_sabe_que_va_dentro_del_visor(self):
        receta = self.receta_queso
        ficha = self.client.get(
            f'/laboratorio/{self.unidad.slug}/procesos/{receta.pk}/ficha/'
        )
        self.assertEqual(ficha.status_code, 200)
        # El marco le pone la clase al detectar que está dentro de un iframe.
        self.assertContains(ficha, 'esta-incrustado')
        self.assertContains(ficha, 'window.self !== window.top')

    def test_las_cantidades_de_la_receta_no_se_leen_como_miles(self):
        datos = datos_de_receta(self.receta_queso, Decimal('1'))
        # Decimal('100.000') se leía como cien mil en la ficha.
        self.assertEqual(datos['cantidad_base'], '100')
        self.assertEqual(datos['rendimiento_esperado'], '12')
        self.assertEqual(datos['factor'], '1')
        self.assertNotIn('.', datos['cantidad_base'])
        ficha = self.client.get(
            f'/laboratorio/{self.unidad.slug}/procesos/{self.receta_queso.pk}/ficha/'
        )
        self.assertContains(ficha, 'Corrida base de 100 litros de leche')
