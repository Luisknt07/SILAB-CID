"""Búsqueda temporal del video privado: rangos exactos y acceso antes de metadatos."""

import hashlib
import io
import shutil
import tempfile
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.formacion.presentation.aula_cursos import archivo_protegido
from apps.formacion.presentation.video_protegido import TAMANO_BLOQUE
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso
from apps.directorio_unidades.models.core import Unidad

DATOS = bytes(range(256)) * 1000


class LecturasRegistradas(io.BytesIO):
    def __init__(self, datos):
        super().__init__(datos)
        self.lecturas = []

    def read(self, tamano=-1):
        self.lecturas.append(tamano)
        return super().read(tamano)


class ArchivoDePrueba:
    name = 'privado/bienvenida.mp4'

    def __init__(self, datos=DATOS):
        self.size = len(datos)
        self.descriptor = LecturasRegistradas(datos)
        self.aperturas = 0

    def open(self, modo):
        self.aperturas += 1
        return self.descriptor


class RangosDeVideoTests(SimpleTestCase):
    def respuesta(self, rango=None, metodo='get', datos=DATOS, if_range=None):
        archivo = ArchivoDePrueba(datos)
        extras = {'HTTP_RANGE': rango} if rango is not None else {}
        if if_range is not None:
            extras['HTTP_IF_RANGE'] = if_range
        request = getattr(RequestFactory(), metodo)('/material/', **extras)
        return archivo_protegido(archivo, request=request), archivo

    def consumir(self, respuesta):
        try:
            return b''.join(respuesta.streaming_content) if respuesta.streaming else respuesta.content
        finally:
            if not respuesta.closed:
                respuesta.close()

    def test_rango_parcial_contenido_y_hash_exactos(self):
        respuesta, archivo = self.respuesta('bytes=1024-101023')
        self.assertEqual(respuesta.status_code, 206)
        self.assertEqual(respuesta['Content-Range'], f'bytes 1024-101023/{len(DATOS)}')
        self.assertEqual(respuesta['Content-Length'], '100000')
        self.assertEqual(respuesta['Accept-Ranges'], 'bytes')
        cuerpo = self.consumir(respuesta)
        self.assertEqual(cuerpo, DATOS[1024:101024])
        self.assertEqual(hashlib.sha256(cuerpo).digest(), hashlib.sha256(DATOS[1024:101024]).digest())
        self.assertTrue(archivo.descriptor.closed)
        self.assertTrue(all(0 < n <= TAMANO_BLOQUE for n in archivo.descriptor.lecturas))
        self.assertEqual(sum(archivo.descriptor.lecturas), 100000)

    def test_rango_abierto_y_sufijo(self):
        for rango, esperado, inicio in (
            ('bytes=255900-', DATOS[255900:], 255900),
            ('bytes=-37', DATOS[-37:], len(DATOS) - 37),
            ('bytes=-999999', DATOS, 0),
        ):
            with self.subTest(rango=rango):
                respuesta, _ = self.respuesta(rango)
                self.assertEqual(respuesta.status_code, 206)
                self.assertEqual(respuesta['Content-Range'], f'bytes {inicio}-{len(DATOS)-1}/{len(DATOS)}')
                self.assertEqual(int(respuesta['Content-Length']), len(esperado))
                self.assertEqual(self.consumir(respuesta), esperado)

    def test_fin_mayor_se_limita_y_un_byte_es_valido(self):
        for rango, esperado, content_range in (
            ('bytes=255999-999999', DATOS[-1:], f'bytes 255999-255999/{len(DATOS)}'),
            ('bytes=0-0', DATOS[:1], f'bytes 0-0/{len(DATOS)}'),
        ):
            with self.subTest(rango=rango):
                respuesta, _ = self.respuesta(rango)
                self.assertEqual(respuesta.status_code, 206)
                self.assertEqual(respuesta['Content-Range'], content_range)
                self.assertEqual(self.consumir(respuesta), esperado)

    def test_rangos_invalidos_no_abren_archivo(self):
        invalidos = ('bytes=256000-', 'bytes=9-2', 'bytes=-0', 'bytes=-',
                     'bytes=0-1,5-6', 'bytes=a-b',
                     'bytes=999999999999999999999999999999-')
        for rango in invalidos:
            with self.subTest(rango=rango):
                respuesta, archivo = self.respuesta(rango)
                self.assertEqual(respuesta.status_code, 416)
                self.assertEqual(respuesta['Content-Range'], f'bytes */{len(DATOS)}')
                self.assertEqual(respuesta['Content-Length'], '0')
                self.assertEqual(self.consumir(respuesta), b'')
                self.assertEqual(archivo.aperturas, 0)
                self.assertEqual(archivo.descriptor.lecturas, [])

    def test_archivo_vacio_no_admite_rango(self):
        respuesta, archivo = self.respuesta('bytes=0-', datos=b'')
        self.assertEqual(respuesta.status_code, 416)
        self.assertEqual(respuesta['Content-Range'], 'bytes */0')
        self.assertEqual(archivo.aperturas, 0)
        if not respuesta.closed:
            respuesta.close()

    def test_sin_rango_devuelve_200_completo_y_conserva_protecciones(self):
        respuesta, _ = self.respuesta()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'video/mp4')
        self.assertEqual(respuesta['Content-Length'], str(len(DATOS)))
        self.assertEqual(respuesta['Accept-Ranges'], 'bytes')
        self.assertNotIn('Content-Range', respuesta)
        self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(respuesta['Content-Security-Policy'], "sandbox; default-src 'none'; img-src 'self'; media-src 'self'")
        self.assertEqual(self.consumir(respuesta), DATOS)

    def test_head_ignora_rango_y_no_abre_archivo(self):
        for rango in (None, 'bytes=40-79', 'bytes=256000-', 'items=0-1'):
            with self.subTest(rango=rango):
                respuesta, archivo = self.respuesta(rango, metodo='head')
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['Content-Length'], str(len(DATOS)))
                self.assertEqual(respuesta['Accept-Ranges'], 'bytes')
                self.assertNotIn('Content-Range', respuesta)
                self.assertEqual(self.consumir(respuesta), b'')
                self.assertEqual(archivo.aperturas, 0)
                self.assertEqual(archivo.descriptor.lecturas, [])

    def test_unidades_desconocidas_ignoran_rango_y_entregan_archivo_completo(self):
        for rango in ('items=0-1', 'seconds=40-79', 'Items=fuera-de-rango'):
            with self.subTest(rango=rango):
                respuesta, archivo = self.respuesta(rango)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['Content-Length'], str(len(DATOS)))
                self.assertNotIn('Content-Range', respuesta)
                self.assertEqual(self.consumir(respuesta), DATOS)
                self.assertEqual(archivo.aperturas, 1)
                self.assertTrue(archivo.descriptor.closed)

    def test_metodos_distintos_de_get_ignoran_rango(self):
        for metodo in ('post', 'put', 'patch', 'options'):
            with self.subTest(metodo=metodo):
                respuesta, _ = self.respuesta('bytes=40-79', metodo=metodo)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['Content-Length'], str(len(DATOS)))
                self.assertNotIn('Content-Range', respuesta)
                self.assertEqual(self.consumir(respuesta), DATOS)

    def test_if_range_sin_validadores_devuelve_archivo_completo(self):
        for condicion in ('"version-anterior"', 'W/"version-anterior"',
                          'Wed, 07 Oct 2026 12:00:00 GMT', ''):
            for rango in ('bytes=40-79', 'bytes=256000-'):
                with self.subTest(condicion=condicion, rango=rango):
                    respuesta, archivo = self.respuesta(rango, if_range=condicion)
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertEqual(respuesta['Content-Length'], str(len(DATOS)))
                    self.assertNotIn('Content-Range', respuesta)
                    self.assertNotIn('ETag', respuesta)
                    self.assertNotIn('Last-Modified', respuesta)
                    self.assertEqual(self.consumir(respuesta), DATOS)
                    self.assertEqual(archivo.aperturas, 1)
                    self.assertTrue(archivo.descriptor.closed)

    def test_cierre_anticipado_libera_descriptor(self):
        respuesta, archivo = self.respuesta('bytes=100-199999')
        next(iter(respuesta.streaming_content))
        self.assertFalse(archivo.descriptor.closed)
        if not respuesta.closed:
            respuesta.close()
        self.assertTrue(archivo.descriptor.closed)

    def test_llamadores_sin_request_conservan_respuesta_original(self):
        archivo = ArchivoDePrueba()
        respuesta = archivo_protegido(archivo)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('Accept-Ranges', respuesta)
        self.assertEqual(self.consumir(respuesta), DATOS)


class AccesoARangosDeVideoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.medios = tempfile.mkdtemp(prefix='citt-video-rangos-')
        cls.configuracion = override_settings(MEDIA_ROOT=cls.medios)
        cls.configuracion.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.configuracion.disable()
            shutil.rmtree(cls.medios, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.estudiante = get_user_model().objects.create_user('rango-estudiante', password='clave-de-prueba')
        cls.cursos, cls.videos = [], []
        for numero in (1, 2):
            unidad = Unidad.objects.create(nombre=f'Laboratorio rangos {numero}', slug=f'lab-rangos-{numero}',
                                           dependencia='laboratorios', descripcion='Prueba',
                                           fecha_inicio=date(2026, 1, 1))
            curso = Curso.objects.create(unidad=unidad, codigo=f'RANGO-CUR-{numero}', nombre='Video protegido',
                                         clasificacion='corto', publicado=True)
            edicion = EdicionCurso.objects.create(curso=curso, nombre='Prueba', anio=2026)
            primera = ModuloCurso.objects.create(curso=curso, orden=1, titulo='Primera unidad libre')
            LeccionCurso.objects.create(modulo=primera, orden=1, titulo='Introducción', tipo='texto', contenido='Inicio')
            segunda = ModuloCurso.objects.create(curso=curso, orden=2, titulo='Videos para inscritos')
            video = LeccionCurso.objects.create(modulo=segunda, orden=1, titulo='Video propio', tipo='video',
                                                archivo=SimpleUploadedFile(f'video-{numero}.mp4', DATOS,
                                                                           content_type='video/mp4'))
            cls.cursos.append(curso)
            cls.videos.append(video)
            if numero == 1:
                InscripcionCurso.objects.create(edicion=edicion, usuario=cls.estudiante, estado='aceptada')
                cls.modulo_propio = segunda

    def url(self, indice=0, leccion=None):
        curso = self.cursos[indice]
        return reverse('material_leccion', args=[curso.unidad.slug, curso.codigo,
                                                (leccion or self.videos[indice]).pk])

    def test_inscrito_recibe_rango_con_bytes_exactos(self):
        self.client.force_login(self.estudiante)
        respuesta = self.client.get(self.url(), HTTP_RANGE='bytes=400-899')
        self.assertEqual(respuesta.status_code, 206)
        self.assertEqual(respuesta['Content-Range'], f'bytes 400-899/{len(DATOS)}')
        try:
            self.assertEqual(b''.join(respuesta.streaming_content), DATOS[400:900])
        finally:
            if not respuesta.closed:
                respuesta.close()

    def test_otra_unidad_denegada_no_expone_bytes_ni_longitud(self):
        self.client.force_login(self.estudiante)
        with patch('apps.formacion.presentation.aula_cursos.archivo_protegido') as servir:
            for metodo in ('get', 'head'):
                respuesta = getattr(self.client, metodo)(self.url(1), HTTP_RANGE='bytes=0-15')
                self.assertEqual(respuesta.status_code, 403)
                self.assertNotIn('Content-Range', respuesta)
                self.assertNotIn('Accept-Ranges', respuesta)
                self.assertFalse(getattr(respuesta, 'streaming', False))
            servir.assert_not_called()

    def test_anonimo_redirigido_sin_servir_archivo(self):
        with patch('apps.formacion.presentation.aula_cursos.archivo_protegido') as servir:
            respuesta = self.client.get(self.url(), HTTP_RANGE='bytes=0-15')
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn('login', respuesta['Location'])
            self.assertNotIn('Content-Range', respuesta)
            servir.assert_not_called()

    def test_id_de_leccion_de_otra_unidad_no_se_resuelve(self):
        self.client.force_login(self.estudiante)
        respuesta = self.client.get(self.url(leccion=self.videos[1]), HTTP_RANGE='bytes=0-15')
        self.assertEqual(respuesta.status_code, 404)
        self.assertNotIn('Content-Range', respuesta)

    def test_pdf_y_zip_con_range_siguen_completos_sin_cambio(self):
        self.client.force_login(self.estudiante)
        for extension, contenido, tipo in (('pdf', b'%PDF contenido completo', 'application/pdf'),
                                           ('zip', b'PK archivo completo', 'application/zip')):
            leccion = LeccionCurso.objects.create(modulo=self.modulo_propio, orden=2 if extension == 'pdf' else 3, titulo='Material', tipo='material',
                                                  archivo=SimpleUploadedFile(f'material.{extension}', contenido,
                                                                             content_type=tipo))
            respuesta = self.client.get(self.url(leccion=leccion), HTTP_RANGE='bytes=0-2')
            self.assertEqual(respuesta.status_code, 200)
            self.assertNotIn('Content-Range', respuesta)
            self.assertNotIn('Accept-Ranges', respuesta)
            try:
                self.assertEqual(b''.join(respuesta.streaming_content), contenido)
            finally:
                if not respuesta.closed:
                    respuesta.close()
