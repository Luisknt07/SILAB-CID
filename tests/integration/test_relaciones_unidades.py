"""Relaciones entre unidades: un centro aloja plantas y les provee materia prima, un laboratorio analiza sus
muestras y un observatorio sigue su producción; cada ficha lo dice desde su punta y la red lo dibuja."""
from datetime import date
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.directorio_unidades.presentation.relaciones import red_de_unidades, relaciones_de
from apps.directorio_unidades.management.commands.cargar_relaciones_unidades import ANALISIS, LACTEOS, SF
from apps.directorio_unidades.models.relaciones import RelacionUnidad
from apps.directorio_unidades.models.core import Unidad


def unidad(slug, dependencia, nombre):
    return Unidad.objects.create(nombre=nombre, slug=slug, dependencia=dependencia, descripcion='Unidad de prueba.',
                                 fecha_inicio=date(2026, 1, 1))


class RelacionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')
        cls.planta = unidad(LACTEOS, 'plantas_piloto', 'Planta Piloto de Procesamiento de Lácteos')
        cls.laboratorio = unidad(ANALISIS, 'laboratorios', 'Laboratorio de Análisis y Calidad')
        cls.observatorio = unidad('observatorio-relaciones', 'observatorios', 'Observatorio de prueba')

    def relacionar(self, origen, tipo, destino, que_fluye=''):
        relacion = RelacionUnidad(origen=origen, tipo=tipo, destino=destino, que_fluye=que_fluye)
        relacion.full_clean()
        relacion.save()
        return relacion

    def test_cada_relacion_la_ejerce_quien_corresponde(self):
        for origen, tipo, destino in ((self.laboratorio, 'aloja', self.planta), (self.centro, 'analiza', self.planta),
                                      (self.planta, 'sigue', self.centro), (self.planta, 'aloja', self.planta)):
            with self.subTest(origen=origen.dependencia, tipo=tipo), self.assertRaises(ValidationError):
                RelacionUnidad(origen=origen, tipo=tipo, destino=destino).full_clean()
        otro_centro = unidad('centro-relaciones', 'centro_experimental', 'Otro centro')
        with self.assertRaises(ValidationError):
            RelacionUnidad(origen=self.centro, tipo='aloja', destino=otro_centro).full_clean()

    def test_cada_punta_lee_la_relacion_a_su_manera(self):
        self.relacionar(self.centro, 'aloja', self.planta)
        self.relacionar(self.centro, 'abastece', self.planta, 'Leche cruda del hato')
        self.relacionar(self.laboratorio, 'analiza', self.planta, 'Leche y productos lácteos')
        desde_planta = {grupo['etiqueta']: [item['unidad'] for item in grupo['unidades']]
                        for grupo in relaciones_de(self.planta)}
        self.assertEqual(list(desde_planta), ['Funciona en', 'Recibe materia prima de', 'Analiza sus muestras'])
        self.assertEqual(desde_planta['Funciona en'], [self.centro])
        desde_centro = [grupo['etiqueta'] for grupo in relaciones_de(self.centro)]
        self.assertEqual(desde_centro, ['Aloja a', 'Provee materia prima a'])
        # Una relación retirada o con una unidad inactiva no se muestra.
        RelacionUnidad.objects.filter(tipo='analiza').update(activa=False)
        self.assertNotIn('Analiza sus muestras', [grupo['etiqueta'] for grupo in relaciones_de(self.planta)])

    def test_la_ficha_muestra_sus_relaciones_con_enlace(self):
        self.relacionar(self.laboratorio, 'analiza', self.planta, 'Leche y productos lácteos')
        pagina = self.client.get(self.laboratorio.get_absolute_url())
        self.assertContains(pagina, 'Unidades relacionadas')
        self.assertContains(pagina, 'Analiza muestras de')
        self.assertContains(pagina, f'href="{self.planta.get_absolute_url()}"')
        self.assertContains(pagina, f'{reverse("red_unidades")}?unidad={self.laboratorio.slug}')
        # Sin relaciones, el panel no aparece.
        self.assertNotContains(self.client.get(self.centro.get_absolute_url()), 'Unidades relacionadas')

    def test_la_red_ordena_por_tipo_y_resalta_la_unidad(self):
        self.relacionar(self.centro, 'abastece', self.planta, 'Leche cruda del hato')
        self.relacionar(self.observatorio, 'sigue', self.centro, 'Producción de leche')
        red = red_de_unidades(self.planta)
        self.assertEqual([columna['titulo'] for columna in red['columnas']],
                         ['Centros experimentales', 'Plantas piloto', 'Laboratorios', 'Observatorios'])
        self.assertEqual(len(red['trazos']), 2)
        self.assertEqual([trazo['atenuado'] for trazo in red['trazos']], [False, True])
        pagina = self.client.get(reverse('red_unidades'), {'unidad': self.planta.slug})
        self.assertContains(pagina, 'is-foco')
        self.assertContains(pagina, 'Leche cruda del hato')
        self.assertContains(pagina, f'href="{self.observatorio.get_absolute_url()}"')
        self.assertEqual(self.client.get(reverse('red_unidades'), {'unidad': 'no-existe'}).status_code, 404)

    def test_el_cargador_registra_lo_que_puede_y_es_idempotente(self):
        salida = StringIO()
        call_command('cargar_relaciones_unidades', stdout=salida)
        self.assertEqual(set(RelacionUnidad.objects.values_list('tipo', flat=True)), {'aloja', 'abastece', 'analiza'})
        self.assertIn('Omitida: centro-experimental-alonso-tadeo no está registrada.', salida.getvalue())
        total = RelacionUnidad.objects.count()
        RelacionUnidad.objects.filter(tipo='abastece').update(que_fluye='Ajustado por la unidad')
        call_command('cargar_relaciones_unidades', stdout=StringIO())
        self.assertEqual(RelacionUnidad.objects.count(), total)
        self.assertEqual(RelacionUnidad.objects.get(tipo='abastece').que_fluye, 'Ajustado por la unidad')
        call_command('cargar_relaciones_unidades', '--reescribir', stdout=StringIO())
        self.assertEqual(RelacionUnidad.objects.get(tipo='abastece').que_fluye, 'Leche cruda del hato del centro')
