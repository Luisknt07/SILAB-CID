"""Identidad de cursos independiente de la colación de PostgreSQL."""
from datetime import date
from unicodedata import normalize

from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.formacion.management.cursos_precargados.identidad import cursos_por_nombres, nombre_normalizado
from apps.formacion.models.cursos import Curso
from apps.directorio_unidades.models.core import Unidad


class NormalizacionNombreTests(SimpleTestCase):
    def test_mayusculas_acentuadas_se_reconocen(self):
        self.assertEqual(nombre_normalizado('CÓDIGOS Y LOGÍSTICA'), nombre_normalizado('Códigos y logística'))

    def test_unicode_equivalente_y_espaciado_se_reconocen(self):
        texto = normalize('NFD', '  LOGÍSTICA\t Y\u00a0TRAZABILIDAD  ')
        self.assertEqual(nombre_normalizado(texto), nombre_normalizado('Logística y trazabilidad'))

    def test_no_elimina_tildes_que_distinguen_titulos(self):
        self.assertNotEqual(nombre_normalizado('Año'), nombre_normalizado('Ano'))

    def test_no_modifica_el_nombre_original(self):
        texto = '  CÓDIGOS\tQR  '
        nombre_normalizado(texto)
        self.assertEqual(texto, '  CÓDIGOS\tQR  ')


class BusquedaNombreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Unidad de formación', slug='identidad-formacion',
            dependencia='laboratorios', descripcion='QA', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='identidad-formacion-otra',
            dependencia='laboratorios', descripcion='QA', fecha_inicio=date(2026, 1, 1))

    def test_conserva_el_primer_registro_y_no_cruza_unidades(self):
        Curso.objects.create(unidad=self.otra, codigo='AJENO', nombre='Códigos QR')
        primero = Curso.objects.create(unidad=self.unidad, codigo='PREVIO', nombre=' CÓDIGOS QR ')
        Curso.objects.create(unidad=self.unidad, codigo='SEGUNDO', nombre='Códigos QR')
        with CaptureQueriesContext(connection) as consultas:
            resultado = cursos_por_nombres(self.unidad, ['Códigos QR', 'Otro curso'])
        self.assertEqual(resultado, {nombre_normalizado('Códigos QR'): primero.pk})
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in consultas))
        self.assertTrue(all('LIMIT 1000' in q['sql'] for q in consultas))
        self.assertFalse(any('"descripcion"' in q['sql'] for q in consultas))

    def test_busqueda_vacia_no_consulta(self):
        with self.assertNumQueries(0):
            self.assertEqual(cursos_por_nombres(self.unidad, []), {})
