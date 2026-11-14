"""Editar la página de un área desde la propia página: datos, textos de su ficha, fotos y videos, por secciones."""
import shutil
import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar

MEDIOS = tempfile.mkdtemp(prefix='citt-area-')


def foto():
    contenido = BytesIO()
    Image.new('RGB', (8, 8), (40, 120, 80)).save(contenido, format='PNG')
    return SimpleUploadedFile('area.png', contenido.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIOS)
class EdicionDelAreaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-area-edicion', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio con áreas', slug='lab-areas-edicion', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='ARE-AREA-META', nombre='Metaverso', capacidad=12)
        cls.url = reverse('editar_area', args=[cls.unidad.slug, cls.area.codigo])
        cls.pagina = reverse('area_unidad', args=[cls.unidad.slug, cls.area.codigo])

    def test_quien_gestiona_completa_la_pagina_del_area(self):
        self.assertNotContains(self.client.get(self.pagina), self.url)
        ajeno = get_user_model().objects.create_user('ajeno-area-edicion', password='clave')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(self.pagina), 'Completar la página del área')
        respuesta = self.client.post(self.url, {
            'seccion': 'contenido', 'ficha-que_es': 'Mundos virtuales compartidos.', 'ficha-como_funciona': 'Con visores y avatares.',
            'ficha-publicada': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        ficha = FichaArea.objects.get(espacio=self.area)
        self.assertTrue(ficha.publicada)
        self.assertEqual(ficha.que_es, 'Mundos virtuales compartidos.')
        # Otra sección no borra lo ya escrito.
        self.client.post(self.url, {'seccion': 'aplicaciones', 'ficha-aplicaciones': 'Clases colaborativas\nFerias virtuales',
                                    'ficha-conexiones': '', 'ficha-seguridad': 'Pausas cada 20 minutos'})
        ficha.refresh_from_db()
        self.assertEqual((ficha.que_es, ficha.lista_aplicaciones), ('Mundos virtuales compartidos.', ['Clases colaborativas', 'Ferias virtuales']))
        pagina = self.client.get(self.pagina)
        self.assertContains(pagina, 'Mundos virtuales compartidos.')
        self.assertContains(pagina, f'{self.url}?seccion=contenido#contenido')

    def test_fotos_y_videos_del_area(self):
        self.client.force_login(self.gestor)
        self.client.post(self.url, {'seccion': 'fotos', 'foto0-imagen': foto(), 'foto0-titulo': 'Sala con visores'})
        medio = MedioInterior.objects.get(espacio=self.area, tipo='foto')
        self.assertEqual((medio.titulo, medio.unidad), ('Sala con visores', self.unidad))
        malo = self.client.post(self.url, {'seccion': 'videos', 'videos': 'https://vimeo.com/1 | Otro'})
        self.assertContains(malo, 'no es un enlace de YouTube')
        self.client.post(self.url, {'seccion': 'videos', 'videos': 'https://youtu.be/aaaaaaaaaaa | Recorrido | Visita guiada'})
        video = MedioInterior.objects.get(espacio=self.area, tipo='video')
        self.assertEqual((video.titulo, video.descripcion), ('Recorrido', 'Visita guiada'))
        self.assertTrue(MedioInterior.objects.filter(espacio=self.area, tipo='foto').exists(), 'Guardar videos no toca las fotos.')
