"""5.2 Especificaciones y 4.2 fichas técnicas: cada producto con lo que debe cumplir y cómo se vende.

Todo producto con proceso de referencia tiene su especificación de liberación, y
todo producto del catálogo su presentación, vida útil y descripción. La carga
solo completa lo vacío: lo que la planta edita no se pisa.
"""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.plantas_piloto.operacion.models.calidad import PlanCalidad
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.directorio_unidades.models.core import Unidad

PLANTAS = ('lacteos', 'carnicos', 'hortofruticola', 'almidones', 'panificacion')


class EspecificacionesYFichasTests(TestCase):
    databases = {'default', 'centros'}
    @classmethod
    def setUpTestData(cls):
        for planta in PLANTAS:
            call_command('cargar_laboratorios_institucionales', laboratorio=planta)
        cls.carnicos = Unidad.objects.get(slug='planta-piloto-carnicos')

    def test_cada_producto_de_referencia_tiene_su_especificacion_de_liberacion(self):
        for receta in Receta.objects.filter(unidad__dependencia='plantas_piloto', origen='referencia'):
            with self.subTest(producto=receta.producto.nombre):
                plan = PlanCalidad.objects.filter(producto=receta.producto, momento='liberacion', activo=True).first()
                self.assertIsNotNone(plan)
                parametros = list(plan.parametros.filter(activo=True))
                self.assertGreaterEqual(len(parametros), 4)
                self.assertTrue(any(parametro.critico for parametro in parametros))
                self.assertFalse([p.nombre for p in parametros if p.limite_texto == 'sin límite'])

    def test_cada_producto_del_catalogo_tiene_su_ficha_tecnica(self):
        incompletos = [
            producto.nombre
            for producto in Producto.objects.filter(
                unidad__dependencia='plantas_piloto', activo=True, publico=True, tipo__in=Producto.TIPOS_PUBLICOS,
            )
            if not (producto.descripcion and producto.unidad_medida and producto.presentacion)
        ]
        self.assertEqual(incompletos, [])

    def test_la_carga_no_pisa_lo_que_la_planta_edito(self):
        longaniza = Producto.objects.get(unidad=self.carnicos, nombre='Longaniza')
        longaniza.presentacion = 'Rollo de 1 kg'
        longaniza.save(update_fields=['presentacion'])
        call_command('cargar_laboratorios_institucionales', laboratorio='carnicos')
        longaniza.refresh_from_db()
        self.assertEqual(longaniza.presentacion, 'Rollo de 1 kg')

    def test_la_seccion_5_2_publica_las_especificaciones_por_familia(self):
        salami = Producto.objects.get(unidad=self.carnicos, nombre='Salami')
        url = reverse('especificaciones_producto', args=[self.carnicos.slug])
        pagina = self.client.get(f'{url}?familia={salami.familia.codigo}')
        self.assertContains(pagina, 'SALAMI')
        self.assertContains(pagina, 'Actividad de agua')
        self.assertContains(pagina, 'NTE INEN 1338')
        self.assertNotContains(pagina, 'CORTES DE CERDO')
        documento = self.client.get(f'{url}?formato=pdf')
        self.assertEqual(documento['Content-Type'], 'application/pdf')
        ficha = self.client.get(self.carnicos.get_absolute_url())
        self.assertContains(ficha, f'{url}?familia={salami.familia.codigo}')
