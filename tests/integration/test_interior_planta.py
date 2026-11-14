"""«La planta por dentro»: galería de fotos y videos por área, y recorrido 360° en el visor.

Las fotos y los videos de YouTube se cargan en el editor de la planta, cada
uno con su área. El recorrido 360° es el ZIP que exporta su programa, cargado
como recurso «Recorrido 360°»: se abre por su index.html, en la raíz o dentro
de la única carpeta del ZIP, y se publica con las reglas de cualquier recurso.
"""
from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.gestion_unidades.presentation.interior import galeria_por_area, interior_de_la_planta, recorrido_360
from apps.recursos.presentation.tipos_adjunto import entrada_360, inferir
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.interior import MedioInterior
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce


def foto(nombre='foto.png'):
    contenido = BytesIO()
    Image.new('RGB', (240, 160), (40, 120, 80)).save(contenido, 'PNG')
    return SimpleUploadedFile(nombre, contenido.getvalue(), content_type='image/png')


def zip_de_recorrido(*rutas):
    contenido = BytesIO()
    with ZipFile(contenido, 'w') as paquete:
        for ruta in rutas:
            paquete.writestr(ruta, '<html>recorrido</html>' if ruta.endswith('.html') else 'var visor = 1;')
    return SimpleUploadedFile('recorrido.zip', contenido.getvalue())


class ElInteriorDeLaPlantaTests(BasePlantaProduce):
    def setUp(self):
        super().setUp()
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))
        self.espacios = list(EspacioReservable.objects.filter(unidad=self.unidad, activo=True).order_by('orden', 'nombre')[:2])

    def medio(self, **datos):
        datos.setdefault('titulo', 'Vista de la planta')
        if datos.get('tipo', 'foto') == 'foto':
            datos.setdefault('imagen', foto())
        return MedioInterior.objects.create(unidad=self.unidad, **datos)

    def recorrido(self, *rutas, carpeta=True, verificado=True):
        return Recurso.objects.create(
            unidad=self.unidad, nombre='Recorrido de la planta', tipo_adjunto='recorrido_360', visibilidad='publica',
            seguridad_verificada=verificado, descripcion='Recorrido exportado con Pano2VR.',
            carpeta=CarpetaRecurso.objects.create(
                unidad=self.unidad, nombre=f'Recorridos {CarpetaRecurso.objects.count()}', visibilidad='publica',
            ) if carpeta else None,
            archivo=zip_de_recorrido(*(rutas or ('tour/index.html', 'tour/pano2vr_player.js'))),
        )

    def test_cada_medio_pide_lo_suyo(self):
        otra = Unidad.objects.create(nombre='Otra planta', slug='otra-planta-interior', dependencia='plantas_piloto',
                                     fecha_inicio=date(2026, 1, 1))
        otra_area = EspacioReservable.objects.create(unidad=otra, codigo='OTRA-AREA-INTERIOR', nombre='Área ajena', tipo='area')
        for datos, campo in (
            ({'tipo': 'foto'}, 'imagen'),
            ({'tipo': 'video', 'youtube_url': 'https://vimeo.com/12345'}, 'youtube_url'),
            ({'tipo': 'video', 'youtube_url': 'https://youtu.be/IJxxIxTuMb8', 'espacio': otra_area}, 'espacio'),
        ):
            with self.assertRaises(ValidationError) as error:
                MedioInterior(unidad=self.unidad, titulo='Prueba', **datos).clean()
            self.assertIn(campo, error.exception.message_dict)

    def test_la_galeria_se_ordena_por_area_con_la_vista_general_primero(self):
        primera, segunda = self.espacios
        self.medio(espacio=segunda, titulo='Segunda área')
        self.medio(espacio=primera, tipo='video', youtube_url='https://www.youtube.com/watch?v=IJxxIxTuMb8', titulo='Video')
        self.medio(titulo='Fachada')
        self.medio(titulo='Borrador', publicado=False)
        grupos = galeria_por_area(self.unidad)
        self.assertEqual([grupo['nombre'] for grupo in grupos], ['Vista general', primera.nombre, segunda.nombre])
        self.assertEqual([medio['titulo'] for medio in grupos[0]['medios']], ['Fachada'])
        video = grupos[1]['medios'][0]
        self.assertEqual(video['video'], 'https://www.youtube-nocookie.com/embed/IJxxIxTuMb8?rel=0&modestbranding=1')
        self.assertEqual(video['miniatura'], 'https://i.ytimg.com/vi/IJxxIxTuMb8/hqdefault.jpg')
        fachada = grupos[0]['medios'][0]
        self.assertTrue(fachada['imagen'].startswith('/media/unidades/interior/'))
        from urllib.parse import urlsplit, parse_qs
        miniatura = urlsplit(fachada['miniatura'])
        self.assertTrue(miniatura.path.endswith('.jpg'))
        self.assertTrue(parse_qs(miniatura.query))

    def test_la_pagina_de_la_galeria(self):
        url = reverse('galeria_interior', args=[self.unidad.slug])
        vacia = self.client.get(url)
        self.assertEqual(vacia['X-Frame-Options'], 'SAMEORIGIN')
        self.assertContains(vacia, 'La unidad todavía no publica fotos ni videos de su interior.')
        self.assertNotContains(vacia, 'Cargar fotos y videos')
        self.medio(titulo='Fachada')
        self.assertContains(self.client.get(url), 'id="datosGaleriaInterior"')
        self.client.force_login(self.coordinacion)
        MedioInterior.objects.all().delete()
        self.assertContains(self.client.get(url), 'Cargar fotos y videos')

    def test_el_zip_del_recorrido_se_reconoce_y_se_valida(self):
        self.assertEqual(entrada_360(['index.html', 'tiles/a.jpg']), 'index.html')
        self.assertEqual(entrada_360(['lacteos1/', 'lacteos1/index.html', 'lacteos1/pano.xml']), 'lacteos1/index.html')
        self.assertEqual(entrada_360(['a/index.html', 'b/visor.js']), '')
        self.assertEqual(inferir(zip_de_recorrido('tour/index.html', 'tour/pano2vr_player.js')), 'recorrido_360')
        self.assertEqual(inferir(zip_de_recorrido('index.html', 'js/app.js')), 'multimedia')
        sin_entrada = Recurso(unidad=self.unidad, nombre='Sin entrada', tipo_adjunto='recorrido_360',
                              archivo=zip_de_recorrido('a/index.html', 'b/pano2vr_player.js'))
        with self.assertRaises(ValidationError) as error:
            sin_entrada.clean()
        self.assertIn('archivo', error.exception.message_dict)

    def test_el_recorrido_se_abre_por_su_entrada_si_se_puede_publicar(self):
        anonimo = AnonymousUser()
        oculto = self.recorrido()
        CarpetaRecurso.objects.filter(pk=oculto.carpeta_id).update(activa=False)
        # En una carpeta inactiva la vista del recurso no lo sirve: al público no se le ofrece.
        self.assertIsNone(recorrido_360(self.unidad, anonimo, False))
        self.assertEqual(recorrido_360(self.unidad, self.coordinacion, True), {'pendiente': 'Recorrido de la planta'})
        oculto.delete()
        publicado = self.recorrido()
        datos = recorrido_360(self.unidad, anonimo, False)
        self.assertEqual(datos['url'], f'/recursos-unidad/{publicado.pk}/tour/index.html')
        self.assertTrue(datos['zip'])
        respuesta = self.client.get(datos['url'])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(b''.join(respuesta.streaming_content), b'<html>recorrido</html>')
        # Con nosniff, el reproductor solo corre si sale como JavaScript.
        script = self.client.get(f'/recursos-unidad/{publicado.pk}/tour/pano2vr_player.js')
        self.assertEqual(script['Content-Type'], 'text/javascript')
        # Leerlo entero suelta el archivo; close() cerraría la conexión de la prueba.
        self.assertEqual(b''.join(script.streaming_content), b'var visor = 1;')

    def test_el_recorrido_no_necesita_carpeta_pero_los_demas_recursos_si(self):
        suelto = self.recorrido(carpeta=False)
        datos = recorrido_360(self.unidad, AnonymousUser(), False)
        self.assertEqual(datos['url'], f'/recursos-unidad/{suelto.pk}/tour/index.html')
        respuesta = self.client.get(datos['url'])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(b''.join(respuesta.streaming_content), b'<html>recorrido</html>')
        documento = Recurso.objects.create(unidad=self.unidad, nombre='Manual suelto', visibilidad='publica',
                                           seguridad_verificada=True, descripcion='Manual sin carpeta.',
                                           archivo=SimpleUploadedFile('manual.html', b'<html>manual</html>'))
        self.assertEqual(self.client.get(f'/recursos-unidad/{documento.pk}/').status_code, 404)

    def test_sin_zip_vale_la_ruta_publicada(self):
        self.unidad.recorrido_360_ruta = 'img/360/lacteos1/index.html'
        self.assertEqual(recorrido_360(self.unidad, AnonymousUser(), False),
                         {'url': '/static/img/360/lacteos1/index.html', 'nombre': 'Recorrido 360°', 'zip': False})

    def test_la_ficha_ofrece_galeria_y_recorrido(self):
        self.medio(titulo='Fachada')
        publicado = self.recorrido()
        resumen = interior_de_la_planta(self.unidad, AnonymousUser(), False)
        self.assertEqual((resumen['plano_y_video'], resumen['medios'], resumen['total']), (False, 1, 2))
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, 'data-id="galeria-interior"')
        self.assertContains(ficha, f'data-ui-click="handleZipResource" data-ui-arg0="/recursos-unidad/{publicado.pk}/tour/index.html"')
        self.assertNotContains(ficha, 'data-id="planta-interior"')

    def test_el_editor_de_la_planta_carga_fotos_y_videos(self):
        self.client.force_login(self.coordinacion)
        editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.unidad.pk]))
        self.assertContains(editor, 'La planta por dentro: fotos y videos')
        self.assertContains(editor, 'name="medios_interiores-TOTAL_FORMS"')
