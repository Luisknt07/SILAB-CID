"""Los kits ZIP revisados se descargan sin ampliar el acceso a otros recursos."""

from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.formacion.presentation.recursos_publicos import carpetas_publicables
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.directorio_unidades.models.core import Unidad


class DatasetZipDescargaTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))
        self.usuario = get_user_model().objects.create_user('lector-kits', password='clave')
        self.unidad = Unidad.objects.create(
            nombre='Laboratorio de kits', slug='laboratorio-kits', dependencia='laboratorios',
            fecha_inicio=date(2026, 1, 1),
        )
        self.carpeta = CarpetaRecurso.objects.create(
            unidad=self.unidad, nombre='Datos para prácticas',
            modulo_config=ModuloUnidad.objects.filter(unidad=self.unidad).first(), seccion_planta='4.3',
        )
        salida = BytesIO()
        with ZipFile(salida, 'w') as paquete:
            paquete.writestr('index.html', '<!doctype html><title>Kit</title><h1>Datos sintéticos</h1>')
            paquete.writestr('datos.csv', 'pedido,unidades\nP01,12\nP02,18\n')
        self.contenido_zip = salida.getvalue()
        self.indice = '<!doctype html><title>Kit</title><h1>Datos sintéticos</h1>'.encode('utf-8')

    def recurso(self, **cambios):
        datos = {
            'unidad': self.unidad, 'carpeta': self.carpeta, 'nombre': 'Kit de logística',
            'descripcion': 'Datos sintéticos y guía metodológica de práctica.',
            'tipo_adjunto': 'dataset', 'seguridad_verificada': True, 'descargar': True,
            'archivo': SimpleUploadedFile('kit-logistica.zip', self.contenido_zip, 'application/zip'),
        }
        datos.update(cambios)
        recurso = Recurso.objects.create(**datos)
        recurso.archivo.close()
        return recurso

    def leer(self, respuesta):
        # Client agota y cierra el streaming; cerrarlo dos veces emite otra
        # señal request_finished y rompe la conexión atómica del TestCase.
        contenido = b''.join(respuesta.streaming_content)
        self.assertTrue(respuesta.closed)
        return contenido

    def contador(self, recurso):
        recurso.refresh_from_db()
        return recurso.veces_descargado

    def boton(self, recurso, usuario=None):
        arbol = carpetas_publicables(self.unidad, usuario or AnonymousUser())
        return ''.join(render_to_string(
            'portal/pages/unidades/detalle/carpeta_recurso.html',
            {'carpeta': carpeta, 'unidad': self.unidad, 'ediciones': []},
        ) for carpeta in arbol['raices'])

    def test_descarga_es_el_zip_original_y_cuenta_una_vez(self):
        recurso = self.recurso()
        respuesta = self.client.get(recurso.get_url_compartir(), {'download': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/zip')
        self.assertIn('attachment;', respuesta['Content-Disposition'])
        self.assertIn('.zip', respuesta['Content-Disposition'])
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
        contenido = self.leer(respuesta)
        self.assertEqual(contenido, self.contenido_zip)
        with ZipFile(BytesIO(contenido)) as paquete:
            self.assertEqual(set(paquete.namelist()), {'index.html', 'datos.csv'})
            self.assertEqual(paquete.read('datos.csv'), b'pedido,unidades\nP01,12\nP02,18\n')
        self.assertEqual(self.contador(recurso), 1)
        self.assertIn('?download=1', self.boton(recurso))

    def test_apertura_normal_conserva_index_y_no_cuenta_descarga(self):
        recurso = self.recurso()
        for parametros in ({}, {'download': '0'}):
            respuesta = self.client.get(reverse('recurso_unidad', args=[recurso.pk]), parametros)
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn('inline;', respuesta['Content-Disposition'])
            self.assertIn('sandbox', respuesta['Content-Security-Policy'])
            self.assertEqual(self.leer(respuesta), self.indice)
        self.assertEqual(self.contador(recurso), 0)

    def test_descarga_desactivada_mantiene_solo_visor(self):
        recurso = self.recurso(descargar=False)
        respuesta = self.client.get(recurso.get_url_compartir(), {'download': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('inline;', respuesta['Content-Disposition'])
        self.assertEqual(self.leer(respuesta), self.indice)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso))

    def test_sin_revision_no_se_publica_ni_se_descarga(self):
        recurso = self.recurso(seguridad_verificada=False)
        for parametros in ({}, {'download': '1'}):
            self.assertEqual(self.client.get(recurso.get_url_compartir(), parametros).status_code, 404)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso))

    def test_zip_manual_no_habilita_descarga_aunque_el_flag_sea_true(self):
        recurso = self.recurso(tipo_adjunto='manual')
        respuesta = self.client.get(recurso.get_url_compartir(), {'download': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('inline;', respuesta['Content-Disposition'])
        self.assertEqual(self.leer(respuesta), self.indice)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso))

    def test_microproyecto_con_flag_true_no_habilita_descarga(self):
        salida = BytesIO()
        with ZipFile(salida, 'w') as paquete:
            paquete.writestr('manage.py', '# proyecto de prueba')
            paquete.writestr('requirements.txt', 'Django==5.2.17')
        recurso = self.recurso(
            tipo_adjunto='microproyecto_django',
            archivo=SimpleUploadedFile('proyecto.zip', salida.getvalue(), 'application/zip'),
        )
        self.assertEqual(self.client.get(recurso.get_url_compartir(), {'download': '1'}).status_code, 404)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso))

    def test_privacidad_del_recurso_deniega_anonimo_y_persona_sin_permiso(self):
        recurso = self.recurso(visibilidad='interna')
        self.assertEqual(self.client.get(recurso.get_url_compartir(), {'download': '1'}).status_code, 404)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(recurso.get_url_compartir(), {'download': '1'}).status_code, 404)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso, self.usuario))

    def test_carpeta_privada_tambien_deniega_descarga(self):
        recurso = self.recurso()
        CarpetaRecurso.objects.filter(pk=self.carpeta.pk).update(visibilidad='interna')
        self.assertEqual(self.client.get(recurso.get_url_compartir(), {'download': '1'}).status_code, 404)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(recurso.get_url_compartir(), {'download': '1'}).status_code, 404)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso, self.usuario))

    def test_restringido_exige_identificacion_y_luego_permite_el_kit(self):
        recurso = self.recurso(visibilidad='restringida')
        self.assertEqual(self.client.get(recurso.get_url_compartir(), {'download': '1'}).status_code, 302)
        self.assertEqual(self.contador(recurso), 0)
        self.assertNotIn('?download=1', self.boton(recurso))
        self.client.force_login(self.usuario)
        respuesta = self.client.get(recurso.get_url_compartir(), {'download': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.leer(respuesta), self.contenido_zip)
        self.assertEqual(self.contador(recurso), 1)

    def test_descarga_no_acepta_ruta_de_un_miembro_del_zip(self):
        recurso = self.recurso()
        self.assertEqual(self.client.get(
            recurso.get_url_compartir() + 'datos.csv', {'download': '1'},
        ).status_code, 404)
        self.assertEqual(self.contador(recurso), 0)

    def test_archivo_normal_conserva_descarga_existente(self):
        recurso = self.recurso(
            tipo_adjunto='manual', archivo=SimpleUploadedFile('guia.txt', b'Guia de practica'),
        )
        respuesta = self.client.get(recurso.get_url_compartir(), {'download': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment;', respuesta['Content-Disposition'])
        self.assertEqual(self.leer(respuesta), b'Guia de practica')
        self.assertEqual(self.contador(recurso), 1)
        self.assertIn('?download=1', self.boton(recurso))
