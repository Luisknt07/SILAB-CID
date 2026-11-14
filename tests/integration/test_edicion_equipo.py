"""Editar la ficha de un equipo desde la propia ficha.

Lo hace quien gestiona los recursos de la unidad: la unidad física siempre; el modelo (ficha técnica, componentes,
descripción, imágenes y videos) solo si gestiona todas las unidades que lo tienen. Lo de referencia se precarga para
aprobarlo y una foto propia reemplaza a la de referencia.
"""
import shutil
import tempfile
import re
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo, FotoEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar

MEDIOS = tempfile.mkdtemp(prefix='citt-edicion-')


def foto(nombre='foto.png'):
    contenido = BytesIO()
    Image.new('RGB', (8, 8), (40, 120, 80)).save(contenido, format='PNG')
    return SimpleUploadedFile(nombre, contenido.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIOS)
class EdicionDeLaFichaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-edicion', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio editable', slug='lab-editable', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='EDI-AREA-VR', nombre='Realidad virtual', capacidad=4)
        familia = FamiliaEquipo.objects.create(
            nombre='Visores editables', slug='visores-editables', grupo='Realidad extendida',
            componentes=[{'tipo': 'incluido', 'cantidad': 2, 'nombre': 'Controles táctiles', 'uso': 'Se emparejan al encender.'}])
        cls.tipo = EquiposServicios.objects.create(codigo='EDI-VR-01', nombre='Visor editable', familia=familia,
                                                   imagen_catalogo='img/catalogo/visor.jpg', credito_imagen='Autor · CC BY-SA 4.0')
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='EDI-VR-01-01', equipo=cls.tipo, laboratorio=cls.unidad)
        cls.url = reverse('editar_equipo_ficha', args=[cls.unidad.slug, cls.equipo.codigo_unidad])
        cls.ficha = reverse('ficha_equipo_publica', args=[cls.unidad.slug, cls.equipo.codigo_unidad])

    def datos(self, **extra):
        datos = {'unidad-estado_unidad': 'disponible', 'unidad-criticidad': 'normal', 'unidad-numero_serie': 'SN-123',
                 'unidad-version_sistema': 'v76', 'unidad-espacios_asociados': [self.area.pk],
                 'modelo-nombre': 'Visor editable', 'modelo-marca': 'Meta', 'modelo-modelo': 'Quest 3',
                 'modelo-origen_datos_tecnicos': 'medido', 'modelo-espec_0': 'Inside-out',
                 'modelo-accesorios_incluidos_texto': '2 × Controles táctiles | Se emparejan al encender\nCorrea para la cabeza',
                 'modelo-accesorios_opcionales_texto': '', 'modelo-otras_especificaciones': '',
                 'modelo-descripcion': 'Visor para prácticas.', 'modelo-uso_publico': '', 'modelo-instrucciones_publicas': '',
                 'videos': 'https://youtu.be/aaaaaaaaaaa | Primeros pasos | Canal', 'volver_a': 'unidad'}
        for indice in range(4):
            datos[f'foto{indice}-tipo'] = 'accesorio'
        datos.update(extra)
        return datos

    def test_solo_quien_gestiona_edita_y_la_ficha_ofrece_editar_sin_etiqueta_referencial(self):
        self.assertNotContains(self.client.get(self.ficha), self.url)
        # El visor conserva la procedencia en sus metadatos JSON; la ficha
        # evita una etiqueta visible que tape la fotografía.
        ficha = self.client.get(self.ficha)
        visible = re.sub(r'<script\b[^>]*>.*?</script>', '', ficha.content.decode(), flags=re.S | re.I)
        self.assertNotIn('Imagen referencial', visible)
        ajeno = get_user_model().objects.create_user('ajeno-edicion', password='clave')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(self.ficha), f'{self.url}?seccion=imagenes#imagenes')
        editor = self.client.get(self.url)
        self.assertContains(editor, 'Precargado con la referencia de su tipo de equipo')
        self.assertContains(editor, '2 × Controles táctiles | Se emparejan al encender.')

    def test_guardar_actualiza_unidad_modelo_fotos_y_videos(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.post(self.url, self.datos(**{
            'modelo-imagen': foto('principal.png'), 'foto0-imagen': foto('mandos.png'), 'foto0-titulo': 'Controles táctiles'}))
        self.assertRedirects(respuesta, f'{self.ficha}#unidad', fetch_redirect_response=False)
        self.equipo.refresh_from_db()
        self.tipo.refresh_from_db()
        self.assertEqual((self.equipo.numero_serie, self.equipo.version_sistema), ('SN-123', 'v76'))
        self.assertEqual(list(self.equipo.espacios_asociados.all()), [self.area])
        self.assertEqual((self.tipo.marca, self.tipo.modelo, self.tipo.origen_datos_tecnicos), ('Meta', 'Quest 3', 'medido'))
        self.assertEqual(self.tipo.accesorios_incluidos[0], {'nombre': 'Controles táctiles', 'uso': 'Se emparejan al encender', 'cantidad': 2})
        self.assertTrue(self.tipo.imagen)
        self.assertEqual(self.tipo.credito_imagen, '', 'La foto propia reemplaza a la de referencia y a su crédito.')
        self.assertEqual(FotoEquipo.objects.get(equipo=self.tipo).titulo, 'Controles táctiles')
        self.assertEqual(list(self.tipo.videos.values_list('titulo', flat=True)), ['Primeros pasos'])
        # La foto del componente aparece junto a él en la ficha.
        self.assertContains(self.client.get(self.ficha), 'equipo__componente-foto con-foto')

    def test_un_video_que_no_es_de_youtube_no_guarda_nada(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.post(self.url, self.datos(videos='https://vimeo.com/123 | Otro'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no es un enlace de YouTube')
        self.equipo.refresh_from_db()
        self.assertFalse(self.equipo.numero_serie)

    def test_un_modelo_compartido_con_otra_unidad_solo_deja_editar_la_unidad(self):
        otra = Unidad.objects.create(nombre='Otro laboratorio', slug='otro-lab-edicion', dependencia='laboratorios',
                                     descripcion='.', fecha_inicio=date(2020, 1, 1))
        UnidadEquipo.objects.create(codigo_unidad='OTR-VR-01-01', equipo=self.tipo, laboratorio=otra)
        self.client.force_login(self.gestor)
        editor = self.client.get(self.url)
        self.assertContains(editor, 'solo puedes editar los datos de esta unidad')
        self.assertNotContains(editor, 'name="modelo-marca"')
        self.client.post(self.url, self.datos(**{'modelo-marca': 'Otra marca'}))
        self.tipo.refresh_from_db()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.numero_serie, 'SN-123')
        self.assertNotEqual(self.tipo.marca, 'Otra marca')


@override_settings(MEDIA_ROOT=MEDIOS)
class EdicionPorSeccionTests(TestCase):
    """El visualizador abre y guarda una sección sola, sin tocar las demás."""

    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-secciones', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio por secciones', slug='lab-secciones', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.tipo = EquiposServicios.objects.create(codigo='SEC-VR-01', nombre='Visor por secciones', marca='Meta', modelo='Quest 3',
                                                   especificaciones={'Pantalla': 'LCD'})
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='SEC-VR-01-01', equipo=cls.tipo, laboratorio=cls.unidad)
        cls.url = reverse('editar_equipo_ficha', args=[cls.unidad.slug, cls.equipo.codigo_unidad])

    def test_una_seccion_se_abre_y_se_guarda_sola(self):
        self.client.force_login(self.gestor)
        fragmento = self.client.get(self.url, {'seccion': 'funcionamiento', 'fragmento': '1'})
        self.assertContains(fragmento, 'id="funcionamiento"')
        self.assertNotContains(fragmento, 'id="especificaciones"')
        self.assertNotContains(fragmento, '<html')
        modos = ('## Autónomo | fas fa-vr-cardboard\nFunciona sin cables.\nPara qué:\n- Recorridos\nNecesita:\n- Wi-Fi\n\n'
                 '## Conectado a una PC | fas fa-desktop\nLa computadora procesa la imagen.\nNecesita:\n- RTX 3060')
        respuesta = self.client.post(self.url, {'seccion': 'funcionamiento', 'modelo-modos_texto': modos, 'fragmento': '1'},
                                     HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.tipo.refresh_from_db()
        self.assertEqual([modo['nombre'] for modo in self.tipo.modos_uso], ['Autónomo', 'Conectado a una PC'])
        self.assertEqual(self.tipo.modos_uso[0]['aplicaciones'], ['Recorridos'])
        self.assertEqual(self.tipo.modos_uso[1]['requisitos'], ['RTX 3060'])
        self.assertEqual((self.tipo.marca, self.tipo.especificaciones), ('Meta', {'Pantalla': 'LCD'}), 'Las demás secciones no cambian.')
        self.client.post(self.url, {'seccion': 'componentes', 'modelo-accesorios_incluidos_texto': 'Correa',
                                    'modelo-accesorios_opcionales_texto': '', 'modelo-repuestos_texto': '4 × Almohadillas | Se cambian'})
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.repuestos, [{'nombre': 'Almohadillas', 'uso': 'Se cambian', 'cantidad': 4}])
        ficha = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, self.equipo.codigo_unidad]))
        self.assertContains(ficha, 'data-editar-ficha')
        self.assertContains(ficha, 'Almohadillas')
        self.assertContains(ficha, 'edicion_en_ficha.js')
