"""Las miniaturas conservan el control de acceso de la fotografía original."""
from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit, urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.recursos.presentation.miniaturas import recorte_cuadrado
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile


class MiniaturasProtegidasTests(TestCase):
    def setUp(self):
        medios = TemporaryDirectory()
        self.addCleanup(medios.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=medios.name))
        self.unidad = Unidad.objects.create(nombre='Galería QA', slug='galeria-miniaturas-qa',
                                            dependencia='laboratorios', fecha_inicio=date.today())
        self.foto = MedioInterior.objects.create(unidad=self.unidad, titulo='Foto publicada',
            publicado=True, imagen=self.imagen('fotografia.png'))

    @staticmethod
    def imagen(nombre):
        salida = BytesIO()
        Image.new('RGB', (200, 120), (40, 120, 80)).save(salida, 'PNG')
        return SimpleUploadedFile(nombre, salida.getvalue(), content_type='image/png')

    def pedir(self, url, metodo='get', **headers):
        respuesta = getattr(self.client, metodo)(url, **headers)
        contenido = b''.join(respuesta.streaming_content) if respuesta.streaming else respuesta.content
        return respuesta, contenido

    def test_galeria_y_presentacion_entregan_recortes_jpeg_y_reutilizan_el_archivo(self):
        for lado in (160, 480):
            url = recorte_cuadrado(self.foto.imagen, 'interior', lado=lado)
            self.assertEqual(url, recorte_cuadrado(self.foto.imagen, 'interior', lado=lado))
            respuesta, contenido = self.pedir(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta['Content-Type'], 'image/jpeg')
            # Publicada para cualquier visitante: el navegador conserva la copia y
            # revalida en cada uso, de modo que el permiso se vuelve a evaluar.
            self.assertEqual(respuesta['Cache-Control'], 'private, no-cache')
            self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
            vigente, cuerpo = self.pedir(url, HTTP_IF_NONE_MATCH=respuesta['ETag'])
            self.assertEqual((vigente.status_code, cuerpo), (304, b''))
            self.assertEqual(vigente['Cache-Control'], 'private, no-cache')
            with Image.open(BytesIO(contenido)) as imagen:
                self.assertEqual(imagen.size, (lado, lado))
        self.assertEqual(len(list(Path(settings.MEDIA_ROOT, 'miniaturas/interior').glob('*.jpg'))), 2)

    def test_el_mapa_tambien_entrega_la_miniatura_de_la_unidad(self):
        self.unidad.imagen = self.imagen('unidad.png')
        self.unidad.save(update_fields=['imagen'])
        respuesta, _ = self.pedir(recorte_cuadrado(self.unidad.imagen, 'unidades'))
        self.assertEqual(respuesta.status_code, 200)

    def test_sin_sello_alterado_o_destino_distinto_no_se_entrega(self):
        url = recorte_cuadrado(self.foto.imagen, 'interior', lado=160)
        parsed = urlsplit(url)
        sello = parse_qs(parsed.query)['origen'][0]
        mayor = urlsplit(recorte_cuadrado(self.foto.imagen, 'interior', lado=480))
        for destino in (parsed.path, parsed.path + '?' + urlencode({'origen': sello + 'x'}),
                        mayor.path + '?' + parsed.query):
            with self.subTest(destino=destino):
                self.assertEqual(self.pedir(destino)[0].status_code, 404)

    def test_ocultar_eliminar_o_reemplazar_la_foto_revoca_la_miniatura_anterior(self):
        url = recorte_cuadrado(self.foto.imagen, 'interior')
        MedioInterior.objects.filter(pk=self.foto.pk).update(publicado=False)
        self.assertEqual(self.pedir(url)[0].status_code, 404)
        MedioInterior.objects.filter(pk=self.foto.pk).update(publicado=True, imagen='otra-foto.png')
        self.assertEqual(self.pedir(url)[0].status_code, 404)
        self.foto.delete()
        self.assertEqual(self.pedir(url)[0].status_code, 404)

    def test_archivo_original_ausente_no_deja_una_copia_publicada(self):
        url = recorte_cuadrado(self.foto.imagen, 'interior')
        self.foto.imagen.storage.delete(self.foto.imagen.name)
        self.assertEqual(self.pedir(url)[0].status_code, 404)

    def test_una_miniatura_huerfana_no_es_publica_aunque_exista_el_original(self):
        self.foto.delete()
        url = recorte_cuadrado(self.foto.imagen, 'interior')
        self.assertEqual(self.pedir(url)[0].status_code, 404)

    def test_una_foto_privada_no_se_abre_con_la_url_firmada_de_su_recorte(self):
        propietario = get_user_model().objects.create_user('propietario-miniatura')
        ajeno = get_user_model().objects.create_user('ajeno-miniatura')
        perfil, _ = UserProfile.objects.get_or_create(user=propietario)
        perfil.avatar = self.imagen('avatar.png')
        perfil.save(update_fields=['avatar'])
        # force_login guarda el usuario; su señal vuelve a guardar el perfil.
        propietario.refresh_from_db()
        url = recorte_cuadrado(perfil.avatar, 'unidades')
        for usuario in (None, ajeno, propietario):
            self.client.logout()
            if usuario:
                self.client.force_login(usuario)
            for metodo, headers in (('get', {}), ('head', {}), ('get', {'HTTP_RANGE': 'bytes=0-20'})):
                respuesta, _ = self.pedir(url, metodo, **headers)
                self.assertEqual(respuesta.status_code, 200 if usuario == propietario else 404)
