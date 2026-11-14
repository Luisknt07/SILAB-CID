"""Asignaturas de grado por laboratorio: salen de las mallas oficiales, dicen dónde se practican, no se duplican al
repetir la carga, respetan lo que la unidad corrigió y aparecen en la pestaña «Asignaturas y carreras que atiende»."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.laboratorios.operacion.management.commands.cargar_asignaturas_laboratorios import codigo_de
from apps.laboratorios.operacion.management.laboratorios.asignaturas import ASIGNATURAS, SIGLAS
from apps.formacion.models.asignaturas import Asignatura
from apps.directorio_unidades.models.core import Unidad


class AsignaturasDeLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('reorganizar_unidades', stdout=StringIO())
        call_command('cargar_asignaturas_laboratorios', stdout=StringIO())
        cls.logistica = Unidad.objects.get(slug='laboratorio-logistica-comercio-internacional')

    def test_cada_laboratorio_recibe_sus_asignaturas_con_carrera_nivel_y_area(self):
        for slug, filas in ASIGNATURAS.items():
            self.assertEqual(Asignatura.objects.filter(unidad__slug=slug).count(), len(filas), slug)
        rutas = Asignatura.objects.get(unidad=self.logistica, codigo=codigo_de('Logística y Transporte', 'Diseño de rutas'))
        self.assertEqual((rutas.carrera, rutas.semestre), ('Logística y Transporte', 'Semestre 6'))
        self.assertIn('«Transporte, distribución y movilidad»', rutas.descripcion)
        self.assertTrue(all(carrera in SIGLAS for filas in ASIGNATURAS.values() for carrera, *_ in filas))

    def test_la_carga_es_repetible_y_respeta_lo_que_la_unidad_corrigio(self):
        rutas = Asignatura.objects.get(unidad=self.logistica, codigo=codigo_de('Logística y Transporte', 'Diseño de rutas'))
        Asignatura.objects.filter(pk=rutas.pk).update(semestre='Sexto semestre', activa=False)
        salida = StringIO()
        call_command('cargar_asignaturas_laboratorios', stdout=salida)
        self.assertIn('0 asignaturas creadas y 0 actualizadas', salida.getvalue())
        rutas.refresh_from_db()
        self.assertEqual((rutas.semestre, rutas.activa), ('Sexto semestre', False))

    def test_codigos_distintos_aunque_el_nombre_largo_se_corte(self):
        primero = codigo_de('Educación Básica', 'Didáctica de las ciencias naturales I')
        segundo = codigo_de('Educación Básica', 'Didáctica de las ciencias naturales II')
        self.assertNotEqual(primero, segundo)
        self.assertTrue(len(primero) <= 40 and len(segundo) <= 40)

    def test_la_pestana_muestra_las_carreras_que_atiende(self):
        respuesta = self.client.get(reverse('asignaturas_unidad', args=[self.logistica.slug]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Comercio Exterior')
        self.assertContains(respuesta, 'Incoterms 2020')
