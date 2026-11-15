"""Estáticos con huella y derivados WebP: generación y entrega negociada."""
import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from PIL import Image

from apps.core.estaticos import AlmacenEstaticos, admite_derivado, derivado_webp, enlazar
from apps.core.middleware.estaticos import EstaticosNegociadosMiddleware


def imagen_png(lado=256):
    # Ruido: un PNG que no comprime bien, como una fotografía.
    imagen = Image.frombytes('RGB', (lado, lado), os.urandom(lado * lado * 3))
    salida = BytesIO()
    imagen.save(salida, 'PNG')
    return salida.getvalue()


class DerivadosTests(SimpleTestCase):
    def test_solo_imagenes_propias_admiten_derivado(self):
        self.assertTrue(admite_derivado('img/generated/portada.PNG'))
        self.assertTrue(admite_derivado('img\\cards\\foto.jpeg'))
        for nombre in ('img/360/lacteos1/tiles/tile_0.jpg', 'js/vendor/leaflet/images/marker.png',
                       'admin/img/icono.png', 'grappelli/images/fondo.png', 'img/logo.svg', 'css/main.css'):
            self.assertFalse(admite_derivado(nombre), nombre)

    def test_derivado_es_webp_y_mas_liviano(self):
        original = imagen_png()
        datos = derivado_webp(original, es_png=True)
        self.assertIsNotNone(datos)
        self.assertLess(len(datos), len(original) * 0.85)
        with Image.open(BytesIO(datos)) as imagen:
            self.assertEqual(imagen.format, 'WEBP')
            self.assertEqual(imagen.size, (256, 256))

    def test_png_pequeno_se_conserva_sin_perdida(self):
        # Fondo semitransparente: WebP no conserva el color de un píxel del todo transparente.
        imagen = Image.new('RGBA', (64, 64), (0, 90, 160, 128))
        imagen.paste((255, 255, 255, 255), (8, 8, 56, 56))
        salida = BytesIO()
        imagen.save(salida, 'PNG', compress_level=0)
        datos = derivado_webp(salida.getvalue(), es_png=True)
        self.assertIsNotNone(datos)
        with Image.open(BytesIO(datos)) as derivada:
            self.assertEqual(derivada.convert('RGBA').tobytes(), imagen.tobytes())

    def test_contenido_que_no_es_imagen_no_produce_derivado(self):
        self.assertIsNone(derivado_webp(b'no es una imagen', es_png=True))

    def test_enlazar_deja_los_mismos_bytes(self):
        with TemporaryDirectory() as carpeta:
            origen, destino = Path(carpeta, 'a.png'), Path(carpeta, 'b.png')
            origen.write_bytes(b'uno')
            destino.write_bytes(b'anterior')
            enlazar(origen, destino)
            enlazar(origen, destino)
            self.assertEqual(destino.read_bytes(), b'uno')


class AlmacenTests(SimpleTestCase):
    def test_sin_manifiesto_conserva_la_direccion_original(self):
        with TemporaryDirectory() as carpeta:
            almacen = AlmacenEstaticos(location=carpeta, base_url='/static/')
            self.assertEqual(almacen.stored_name('img/portada.png'), 'img/portada.png')
            self.assertEqual(almacen.url('img/portada.png'), '/static/img/portada.png')
            # Una referencia a un archivo que no se distribuye no aborta la recopilación.
            self.assertEqual(almacen.hashed_name('js/vendor/leaflet/leaflet.js.map'),
                             'js/vendor/leaflet/leaflet.js.map')

    def test_recopilacion_crea_huella_y_derivado_compartido(self):
        with TemporaryDirectory() as carpeta:
            Path(carpeta, 'img').mkdir()
            Path(carpeta, 'img', 'foto.png').write_bytes(imagen_png())
            Path(carpeta, 'img', 'icono.png').write_bytes(b'x' * 10)
            almacen = AlmacenEstaticos(location=carpeta, base_url='/static/')
            rutas = {'img/foto.png': (almacen, 'img/foto.png'), 'img/icono.png': (almacen, 'img/icono.png')}
            for _nombre, _destino, procesado in almacen.post_process(rutas):
                self.assertNotIsInstance(procesado, Exception)
            con_huella = almacen.stored_name('img/foto.png')
            self.assertRegex(con_huella, r'^img/foto\.[0-9a-f]{12}\.png$')
            derivados = [Path(carpeta, 'img', 'foto.png.webp'), Path(carpeta, con_huella + '.webp')]
            self.assertTrue(all(ruta.is_file() for ruta in derivados))
            self.assertEqual(derivados[0].read_bytes(), derivados[1].read_bytes())
            self.assertEqual(Path(carpeta, con_huella).read_bytes(), Path(carpeta, 'img', 'foto.png').read_bytes())
            self.assertFalse(Path(carpeta, 'img', 'icono.png.webp').exists())


class CatalogoTraduccionesTests(SimpleTestCase):
    def test_la_recopilacion_publica_un_catalogo_con_huella_por_idioma(self):
        from django.template import Context, Template
        from unittest.mock import patch

        plantilla = Template('{% load idiomas %}{% catalogo_javascript_url idioma %}')
        # Sin recopilar (desarrollo y pruebas) se usa la vista que lo calcula.
        self.assertEqual(plantilla.render(Context({'idioma': 'en-us'})), '/i18n/catalogo.js?language=en')
        with TemporaryDirectory() as carpeta:
            almacen = AlmacenEstaticos(location=carpeta, base_url='/static/')
            for _nombre, _destino, procesado in almacen.post_process({}):
                self.assertNotIsInstance(procesado, Exception)
            for idioma in ('es', 'en'):
                con_huella = almacen.stored_name(f'i18n/catalogo.{idioma}.js')
                self.assertRegex(con_huella, rf'^i18n/catalogo\.{idioma}\.[0-9a-f]{{12}}\.js$')
                contenido = Path(carpeta, con_huella).read_text(encoding='utf-8')
                self.assertIn('django.gettext', contenido)
                self.assertTrue(Path(carpeta, con_huella + '.gz').is_file())
            # Un manifiesto leído de nuevo conserva las entradas del catálogo.
            self.assertIn('i18n/catalogo.es.js', AlmacenEstaticos(location=carpeta, base_url='/static/').hashed_files)
            with patch('apps.core.templatetags.idiomas.staticfiles_storage', almacen):
                self.assertEqual(plantilla.render(Context({'idioma': 'es'})),
                                 '/static/' + almacen.stored_name('i18n/catalogo.es.js'))


class EntregaNegociadaTests(SimpleTestCase):
    def setUp(self):
        self.carpeta = TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        raiz = Path(self.carpeta.name, 'img')
        raiz.mkdir()
        (raiz / 'foto.png').write_bytes(b'P' * 400)
        (raiz / 'foto.png.webp').write_bytes(b'W' * 100)
        (raiz / 'sola.png').write_bytes(b'S' * 50)
        ajustes = override_settings(STATIC_ROOT=self.carpeta.name, STATIC_URL='/static/', DEBUG=False,
                                    WHITENOISE_MAX_AGE=600)
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.middleware = EstaticosNegociadosMiddleware(lambda request: HttpResponse('aplicacion'))

    def pedir(self, ruta, **cabeceras):
        respuesta = self.middleware(RequestFactory().get(ruta, **cabeceras))
        self.addCleanup(respuesta.close)
        return respuesta

    def test_navegador_que_acepta_webp_recibe_el_derivado(self):
        respuesta = self.pedir('/static/img/foto.png', HTTP_ACCEPT='image/avif,image/webp,*/*',
                               HTTP_SEC_FETCH_DEST='image')
        self.assertEqual(respuesta['Content-Type'], 'image/webp')
        self.assertEqual(respuesta['Content-Length'], '100')
        self.assertIn('Accept', respuesta['Vary'])

    def test_sin_webp_o_al_abrir_el_archivo_se_entrega_el_original(self):
        for cabeceras in ({'HTTP_ACCEPT': 'image/png'}, {},
                          {'HTTP_ACCEPT': 'text/html,image/webp,*/*', 'HTTP_SEC_FETCH_DEST': 'document'}):
            respuesta = self.pedir('/static/img/foto.png', **cabeceras)
            self.assertEqual(respuesta['Content-Type'], 'image/png', cabeceras)
            self.assertEqual(respuesta['Content-Length'], '400')
            self.assertIn('Accept', respuesta['Vary'])

    def test_imagen_sin_derivado_y_otras_rutas_no_cambian(self):
        respuesta = self.pedir('/static/img/sola.png', HTTP_ACCEPT='image/webp')
        self.assertEqual(respuesta['Content-Type'], 'image/png')
        self.assertNotIn('Accept', respuesta.get('Vary', ''))
        self.assertEqual(self.pedir('/reservas/', HTTP_ACCEPT='image/webp').content, b'aplicacion')

    def test_derivado_de_un_nombre_con_huella_es_inmutable(self):
        with override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}):
            self.assertFalse(self.middleware.immutable_file_test('', '/static/img/foto.png.webp'))
        almacen = type('Almacen', (), {'url': staticmethod(lambda nombre: '/static/img/foto.0123456789ab.png')})()
        from unittest.mock import patch
        with patch('whitenoise.middleware.staticfiles_storage', almacen):
            self.assertTrue(self.middleware.immutable_file_test('', '/static/img/foto.0123456789ab.png.webp'))
            self.assertTrue(self.middleware.immutable_file_test('', '/static/img/foto.0123456789ab.png'))
