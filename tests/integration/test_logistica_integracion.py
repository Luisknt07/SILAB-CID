"""Las entradas nativas usan el visor existente y sus controles de publicación."""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.asignaturas import Asignatura
from apps.directorio_unidades.models.core import Unidad
from apps.laboratorios.operacion.management.laboratorios.logistica_paso1 import SLUG


class IntegracionLogisticaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de Logística', slug=SLUG,
            dependencia='laboratorios', descripcion='Unidad docente', fecha_inicio=date(2025, 1, 1))
        Asignatura.objects.create(unidad=cls.unidad, codigo='LOG-TEST', nombre='Cadena de suministro', carrera='Logística y Transporte')
        cls.otra = Unidad.objects.create(nombre='Otro laboratorio', slug='otro-laboratorio',
            dependencia='laboratorios', descripcion='Otra unidad', fecha_inicio=date(2025, 1, 1))

    def test_portada_nativa_se_carga_bajo_demanda_y_menu_ofrece_simulador_y_matriz(self):
        response = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(response, 'data-initial-src="' + reverse('logistica_identidad', args=[SLUG]) + '"')
        self.assertContains(response, reverse('logistica_identidad', args=[SLUG]) + '#matriz')
        self.assertContains(response, reverse('logistica_juego_cerveza', args=[SLUG]))
        self.assertTrue(response.context['identidad_logistica_visible'])

    def test_ocultar_interior_impide_portada_inicial(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='1.3', oculta=True)
        response = self.client.get(self.unidad.get_absolute_url())
        self.assertFalse(response.context['identidad_logistica_visible'])
        self.assertNotContains(response, 'data-initial-src=')

    def test_ocultar_recursos_quita_el_juego_del_menu(self):
        AjusteSeccionPlanta.objects.create(unidad=self.unidad, numero='4.4', oculta=True)
        response = self.client.get(self.unidad.get_absolute_url())
        self.assertNotContains(response, 'data-id="logistica-juego-cerveza"')
        self.assertEqual(self.client.get(reverse('logistica_juego_cerveza', args=[SLUG])).status_code, 404)

    def test_otras_unidades_conservan_visor_sin_entradas_logisticas(self):
        response = self.client.get(self.otra.get_absolute_url())
        self.assertFalse(response.context['identidad_logistica_visible'])
        self.assertNotContains(response, 'data-id="logistica-identidad"')
        self.assertNotContains(response, 'data-id="logistica-juego-cerveza"')
        self.assertContains(response, 'video_institucional.html')
