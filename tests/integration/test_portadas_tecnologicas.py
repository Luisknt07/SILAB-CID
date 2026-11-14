"""La portada de cada pestaña se presenta con un fondo tecnológico animado que alude a la pestaña, resume sus
secciones con lo que publican y las abre en el menú; la unidad edita su frase, su texto, el estilo, la imagen o pone
una escena 3D publicada."""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.formacion.presentation.aula import contexto_aula
from apps.gestion_unidades.presentation.portadas import portadas_de
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.recursos import ModuloUnidad
from apps.gestion_unidades.models.portadas import PortadaPestana
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.portadas import validar_escena_3d


class PortadasTecnologicasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-portadas', 'p@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con portadas', slug='lab-portadas', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        EspacioReservable.objects.create(unidad=cls.lab, codigo='POR-AREA-RV', nombre='Realidad virtual', capacidad=8)
        cls.areas = ModuloUnidad.objects.get(unidad=cls.lab, clave='areas-equipos')

    def portadas(self):
        modulos = list(ModuloUnidad.objects.filter(unidad=self.lab, activo=True).order_by('orden'))
        carpetas = contexto_aula(self.lab, modulos)['aula']['carpetas']
        return {portada['clave']: portada for portada in portadas_de(self.lab, modulos, carpetas)}

    def test_cada_pestana_tiene_su_estilo_y_resume_sus_secciones(self):
        portadas = self.portadas()
        self.assertEqual((portadas['informacion-general']['tema'], portadas['areas-equipos']['tema']), ('orbitas', 'cubos'))
        general = {elemento['nombre']: elemento for elemento in portadas['informacion-general']['elementos']}
        self.assertEqual(general['Presentación']['numero'], '1.1')
        self.assertEqual(general['Presentación']['icono'], 'fas fa-play-circle')
        areas = {elemento['nombre']: elemento for elemento in portadas['areas-equipos']['elementos']}
        self.assertEqual(areas['Áreas del laboratorio']['total'], 1)
        self.assertIn(areas['Áreas del laboratorio'], portadas['areas-equipos']['cifras'])
        self.client.force_login(self.admin)
        pagina = self.client.get(self.lab.get_absolute_url()).content.decode()
        for marca in ('tech-portada tema-cubos', 'tech-escena--orbitas', 'data-abrir-seccion="2.1"', 'portada_tecnologica.js',
                      reverse('editar_registro', args=[self.lab.slug, 'portada', self.areas.pk])):
            self.assertIn(marca, pagina)

    def test_la_unidad_edita_la_portada_y_puede_poner_una_escena_3d(self):
        self.client.force_login(self.admin)
        url = reverse('editar_registro', args=[self.lab.slug, 'portada', self.areas.pk])
        self.assertContains(self.client.get(url, {'fragmento': '1'}), 'name="registro-escena_3d"')
        respuesta = self.client.post(url, {'registro-lema': 'Tecnología para aprender haciendo', 'registro-tema': 'molecula',
                                           'registro-descripcion': 'Diez áreas al servicio de cuatro carreras.',
                                           'registro-escena_3d': 'https://my.spline.design/escena-abc/'},
                                     HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        portada = PortadaPestana.objects.get(modulo=self.areas)
        self.assertEqual((portada.lema, portada.tema), ('Tecnología para aprender haciendo', 'molecula'))
        datos = self.portadas()['areas-equipos']
        self.assertEqual((datos['tema'], datos['entrada'], datos['escena']),
                         ('molecula', 'Diez áreas al servicio de cuatro carreras.', 'https://my.spline.design/escena-abc/'))
        pagina = self.client.get(self.lab.get_absolute_url())
        self.assertContains(pagina, 'Tecnología para aprender haciendo')
        self.assertContains(pagina, 'class="tech-portada__escena3d" src="https://my.spline.design/escena-abc/"')
        malo = self.client.post(url, {'registro-escena_3d': 'https://ejemplo.com/escena'})
        self.assertContains(malo, 'Use el enlace público de una escena de Spline')

    def test_solo_se_incrustan_escenas_de_sitios_conocidos(self):
        validar_escena_3d('https://sketchfab.com/models/abc/embed')
        validar_escena_3d('')
        for direccion in ('https://my.spline.design.ejemplo.com/x', 'javascript:alert(1)', 'https://otro.com/spline'):
            with self.subTest(direccion=direccion), self.assertRaises(ValidationError):
                validar_escena_3d(direccion)
