"""«Conoce la unidad» y «El laboratorio por dentro» se llenan desde lo registrado, sin pisar lo propio.

El interior toma las fotos y videos de las fichas de área (y la foto de la unidad como vista general); la
presentación, los textos del archivo de presentaciones. Las dos órdenes se repiten sin duplicar y respetan lo
que la unidad subió o escribió a mano.
"""
from datetime import date
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.presentacion import HitoUnidad, LineaAccionUnidad, PresentacionUnidad
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar

PRESENTACION = {
    'lema': 'Prototipos que se tocan', 'que_es': 'Qué es.\nDónde funciona.', 'que_hace': 'Qué hace.', 'capacidades': 'Equipos.',
    'areas_trabajo': 'Líneas.', 'historia': 'Nació.', 'mision': 'Formar.', 'vision': 'Ser.',
    'objetivos': ['Desarrollar prototipos.', 'Formar estudiantes.'], 'beneficiarios': ['Estudiantes'], 'resultados': ['Prototipos'],
    'lineas': [('Docencia práctica', 'fa-graduation-cap', 'Prácticas.'), ('Innovación', 'fa-lightbulb', 'Ideas.')],
    'hitos': [(2026, 'Inicio de operaciones', 'Abre sus puertas.')],
}


class ConoceEInteriorCargadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-interior', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio interior', slug='laboratorio-interior', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2026, 7, 30), administrador=cls.gestor)
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='INT-AREA-IMP3D', nombre='Impresión 3D', capacidad=4)
        ficha = FichaArea.objects.create(espacio=cls.area, que_es='Área de impresión.', publicada=True)
        ElementoFichaArea.objects.create(ficha=ficha, tipo='imagen', nombre='Impresoras trabajando',
                                         imagen_estatica='img/pilares/Estructura_fablab.jpg', orden=1)
        ElementoFichaArea.objects.create(ficha=ficha, tipo='imagen', nombre='No existe', imagen_estatica='img/no-existe.png', orden=2)
        ElementoFichaArea.objects.create(ficha=ficha, tipo='video', nombre='Introducción a la impresión 3D', ejemplo='Fab Lab',
                                         url='https://www.youtube.com/watch?v=LypRoerh81o', orden=3)

    def test_el_interior_toma_las_fotos_y_videos_de_las_areas_sin_duplicar_ni_pisar(self):
        propio = MedioInterior.objects.create(unidad=self.unidad, espacio=self.area, tipo='video', titulo='Nuestro video',
                                              youtube_url='https://youtu.be/abcdefghijk')
        salida = StringIO()
        call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, stdout=salida)
        self.assertIn('1 fotos cargadas', salida.getvalue())
        self.assertIn('1 videos cargados', salida.getvalue())
        self.assertIn('1 imágenes que no existen', salida.getvalue())
        foto = MedioInterior.objects.get(unidad=self.unidad, tipo='foto')
        self.assertTrue(foto.imagen.name.startswith(f'unidades/interior/u{self.unidad.pk}/'))
        self.assertLessEqual(len(foto.imagen.name), 100)
        self.assertTrue(foto.descripcion.startswith('Imagen referencial del área'))
        self.assertTrue(foto.imagen.storage.exists(foto.imagen.name))
        call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, stdout=StringIO())
        self.assertEqual(MedioInterior.objects.filter(unidad=self.unidad).count(), 3)
        pagina = self.client.get(reverse('galeria_interior', args=[self.unidad.slug]))
        self.assertContains(pagina, 'Impresoras trabajando')
        self.assertContains(pagina, 'LypRoerh81o')
        call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, '--eliminar', stdout=StringIO())
        self.assertEqual(list(MedioInterior.objects.filter(unidad=self.unidad)), [propio])

    def test_la_simulacion_no_escribe_ni_copia_archivos(self):
        from django.core.files.storage import default_storage

        from apps.gestion_unidades.management.commands.cargar_interior_unidades import Command

        # Los archivos no se deshacen entre pruebas: se parte sin la copia que otra prueba pudo dejar.
        destino = Command.destino_de(self.unidad, 'img/pilares/Estructura_fablab.jpg')
        if default_storage.exists(destino):
            default_storage.delete(destino)
        call_command('cargar_interior_unidades', '--unidad', self.unidad.slug, '--simular', stdout=StringIO())
        self.assertFalse(MedioInterior.objects.filter(unidad=self.unidad).exists())
        self.assertFalse(default_storage.exists(destino))

    def test_la_presentacion_se_carga_publicada_y_respeta_lo_escrito(self):
        PresentacionUnidad.objects.create(unidad=self.unidad, lema='Nuestro lema', publicada=False)
        with mock.patch('apps.gestion_unidades.management.commands.cargar_presentaciones_unidades.PRESENTACIONES', {self.unidad.slug: PRESENTACION}):
            call_command('cargar_presentaciones_unidades', stdout=StringIO())
            call_command('cargar_presentaciones_unidades', stdout=StringIO())
        presentacion = PresentacionUnidad.objects.get(unidad=self.unidad)
        self.assertEqual(presentacion.lema, 'Nuestro lema', 'Lo que la unidad escribió no se pisa.')
        self.assertEqual(presentacion.que_es, 'Qué es.\nDónde funciona.')
        self.assertEqual(presentacion.lista('objetivos'), ['Desarrollar prototipos.', 'Formar estudiantes.'])
        self.assertTrue(presentacion.publicada)
        self.assertEqual(LineaAccionUnidad.objects.filter(unidad=self.unidad).count(), 2)
        self.assertEqual(HitoUnidad.objects.filter(unidad=self.unidad).count(), 1)
        pagina = self.client.get(reverse('conoce_unidad', args=[self.unidad.slug]))
        self.assertContains(pagina, 'Dónde funciona.')
        self.assertContains(pagina, 'Docencia práctica')
        self.assertNotContains(pagina, 'todavía no publica')
        with mock.patch('apps.gestion_unidades.management.commands.cargar_presentaciones_unidades.PRESENTACIONES', {self.unidad.slug: PRESENTACION}):
            call_command('cargar_presentaciones_unidades', '--reescribir', stdout=StringIO())
        presentacion.refresh_from_db()
        self.assertEqual(presentacion.lema, 'Prototipos que se tocan')
