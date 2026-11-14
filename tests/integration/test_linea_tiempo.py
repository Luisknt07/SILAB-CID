"""La línea de tiempo de la historia: cada hito en su año y mes, con su tipo, sin taparse; vertical en angosto."""
from datetime import date
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.linea_tiempo import linea_de_tiempo
from apps.gestion_unidades.models.presentacion import HitoUnidad, PresentacionUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class LineaDeTiempoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-tiempo', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio con historia', slug='laboratorio-historia', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2018, 1, 1), administrador=cls.gestor)
        PresentacionUnidad.objects.create(unidad=cls.unidad, que_es='Qué es.', publicada=True)
        cls.hitos = [
            HitoUnidad.objects.create(unidad=cls.unidad, anio=2018, mes=3, tipo='creacion', titulo='Creación'),
            HitoUnidad.objects.create(unidad=cls.unidad, anio=2019, tipo='equipamiento', titulo='Primeras impresoras'),
            HitoUnidad.objects.create(unidad=cls.unidad, anio=2019, mes=4, tipo='formacion', titulo='Primer taller'),
            HitoUnidad.objects.create(unidad=cls.unidad, anio=2019, mes=5, tipo='certificacion', titulo='Certificación',
                                      enlace='https://ejemplo.org/certificado.pdf'),
            HitoUnidad.objects.create(unidad=cls.unidad, anio=2025, mes=10, tipo='equipamiento', titulo='Estaciones de diseño'),
        ]

    def test_los_hitos_se_ubican_por_fecha_alternan_lado_y_no_se_tapan(self):
        linea = linea_de_tiempo(HitoUnidad.objects.filter(unidad=self.unidad), hoy=date(2026, 10, 3))
        self.assertEqual([a['anio'] for a in linea['anios']], list(range(2018, 2027)))
        posiciones = [item['x'] for item in linea['hitos']]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertEqual([item['lado'] for item in linea['hitos']][:2], ['arriba', 'abajo'])
        por_titulo = {item['hito'].titulo: item for item in linea['hitos']}
        self.assertEqual([item['hito'].titulo for item in linea['hitos']][1:4], ['Primer taller', 'Certificación', 'Primeras impresoras'])
        # Los tres de 2019 quedan juntos (el que no tiene mes va a mitad de año): ningún rótulo pisa a otro del mismo
        # lado y nivel, así que alguno sube a un tallo más largo.
        for uno in linea['hitos']:
            for otro in linea['hitos']:
                if uno is not otro and (uno['lado'], uno['nivel']) == (otro['lado'], otro['nivel']):
                    self.assertTrue(uno['tramo'][1] <= otro['tramo'][0] or otro['tramo'][1] <= uno['tramo'][0],
                                    (uno['hito'].titulo, otro['hito'].titulo))
        self.assertEqual(max(item['nivel'] for item in linea['hitos']), 1)
        self.assertEqual(por_titulo['Estaciones de diseño']['nivel'], 0)
        # Ningún rótulo se sale del eje: cerca del final se escribe a la izquierda del ícono.
        self.assertTrue(all(0 <= item['tramo'][0] and item['tramo'][1] <= 100 for item in linea['hitos']))
        self.assertFalse(por_titulo['Creación']['izquierda'])
        self.assertGreaterEqual(min(posiciones), 3)
        self.assertLessEqual(max(posiciones), 97)
        # Los años cubren la barra de borde a borde, cada uno con su tramo.
        self.assertEqual((linea['anios'][0]['x_css'], linea['anios'][-1]['x_css'][:5]), ('0.00%', '86.56'))
        self.assertEqual(por_titulo['Creación']['fecha'], 'Mar. 2018')
        self.assertEqual(por_titulo['Primeras impresoras']['fecha'], '2019')
        self.assertEqual(por_titulo['Certificación']['icono'], 'fa-certificate')
        self.assertEqual([item['tipo'] for item in linea['leyenda']], ['creacion', 'equipamiento', 'certificacion', 'formacion'])
        self.assertEqual((linea['niveles_arriba'], linea['niveles_abajo']), (2, 2))
        self.assertEqual(linea_de_tiempo([])['hitos'], [])

    def test_la_pagina_dibuja_la_linea_con_leyenda_y_respaldo(self):
        pagina = self.client.get(reverse('conoce_unidad', args=[self.unidad.slug]))
        self.assertContains(pagina, 'class="tiempo"')
        self.assertContains(pagina, 'Certificación y reconocimiento')
        self.assertContains(pagina, 'https://ejemplo.org/certificado.pdf')
        self.assertContains(pagina, 'Mar. 2018')
        self.assertContains(pagina, '--tiempo-anios: 9')
        # Las posiciones van con punto decimal aunque el sitio localice los números a coma.
        self.assertRegex(pagina.content.decode('utf-8'), r'--x: \d+\.\d+%')
        self.assertNotRegex(pagina.content.decode('utf-8'), r'--x: \d+,\d+')

    def test_el_cargador_acepta_hitos_con_mes_tipo_y_enlace(self):
        datos = {self.unidad.slug: {'que_es': 'Qué es.', 'hitos': [
            {'anio': 2020, 'mes': 2, 'tipo': 'convenio', 'titulo': 'Convenio', 'descripcion': 'Con el sector.', 'enlace': 'https://ejemplo.org/c'},
            (2021, 'Terna antigua', 'Sigue valiendo.'),
        ]}}
        with mock.patch('apps.gestion_unidades.management.commands.cargar_presentaciones_unidades.PRESENTACIONES', datos):
            call_command('cargar_presentaciones_unidades', '--reescribir', stdout=StringIO())
        hitos = list(HitoUnidad.objects.filter(unidad=self.unidad).order_by('anio'))
        self.assertEqual([(h.anio, h.mes, h.tipo, h.enlace) for h in hitos],
                         [(2020, 2, 'convenio', 'https://ejemplo.org/c'), (2021, None, 'hito', '')])
