"""El archivo conserva los mismos permisos que su contenido, incluso por URL directa."""
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.centros_id.models import CarpetaCentro, CentroID, DocumentoCentro, RecursoCentro
from apps.centros_id.presentation.archivos import descarga_archivo_view


class ArchivosCentroTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}
    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroID.objects.create(nombre='Archivos', slug='centro-archivos', proposito='Investigar')
        cls.otro = CentroID.objects.create(nombre='Otro', slug='centro-archivos-otro', proposito='Investigar')
        cls.gestor = get_user_model().objects.create_user('gestor.archivos')
        cls.ajeno = get_user_model().objects.create_user('ajeno.archivos')
        cls.centro.gestores.add(cls.gestor)
        cls.documento = DocumentoCentro.objects.create(centro=cls.centro, titulo='Acta interna', tipo='acta_comite',
            publico=False, archivo=SimpleUploadedFile('acta.pdf', b'%PDF-1.4\nActa interna'))
        cls.carpeta = CarpetaCentro.objects.create(centro=cls.centro, pestana='conoce', nombre='Expediente', visibilidad='interna')
        cls.recurso = RecursoCentro.objects.create(carpeta=cls.carpeta, tipo='archivo', titulo='Anexo interno',
            archivo=SimpleUploadedFile('anexo.pdf', b'%PDF-1.4\nAnexo interno'))

    def archivo(self, objeto, tipo, centro=None, **parametros):
        return self.client.get(reverse('archivo_centro_id', args=[(centro or self.centro).slug, tipo, objeto.pk]), parametros)

    def test_internos_anonimo_y_gestor_ajeno_no_pueden_abrir_archivo(self):
        for usuario in (None, self.ajeno):
            if usuario:
                self.client.force_login(usuario)
            for objeto, tipo in ((self.documento, 'documento'), (self.recurso, 'recurso')):
                with self.subTest(usuario=usuario, tipo=tipo):
                    self.assertEqual(self.archivo(objeto, tipo).status_code, 404)
                    self.assertEqual(self.client.get(objeto.archivo.url).status_code, 404)

    def test_gestor_descarga_y_url_no_concede_acceso_fuera_de_su_centro(self):
        self.client.force_login(self.gestor)
        for objeto, tipo in ((self.documento, 'documento'), (self.recurso, 'recurso')):
            respuesta = self.archivo(objeto, tipo)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta['Content-Type'], 'application/pdf')
            self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
            self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
            self.assertTrue(b''.join(respuesta.streaming_content).startswith(b'%PDF'))
            self.assertEqual(self.archivo(objeto, tipo, centro=self.otro).status_code, 404)
        self.assertEqual(self.documento.url, reverse('archivo_centro_id', args=[self.centro.slug, 'documento', self.documento.pk]))
        self.assertEqual(self.recurso.archivo_url, reverse('archivo_centro_id', args=[self.centro.slug, 'recurso', self.recurso.pk]))

    def test_publicar_y_retirar_aplica_a_url_nueva_y_media_anterior(self):
        self.documento.publico = True
        self.documento.save()
        self.carpeta.visibilidad = 'publica'
        self.carpeta.save()
        for objeto, tipo in ((self.documento, 'documento'), (self.recurso, 'recurso')):
            respuesta = self.archivo(objeto, tipo)
            self.assertEqual(respuesta.status_code, 200)
            b''.join(respuesta.streaming_content)
        self.documento.estado_documental = 'borrador'
        self.documento.save()
        self.carpeta.visibilidad = 'interna'
        self.carpeta.save()
        for objeto, tipo in ((self.documento, 'documento'), (self.recurso, 'recurso')):
            self.assertEqual(self.archivo(objeto, tipo).status_code, 404)
            self.assertEqual(self.client.get(objeto.archivo.url).status_code, 404)

    def test_muestras_recursos_inactivos_y_metodos_no_se_publican(self):
        self.documento.publico = True
        self.documento.es_muestra = True
        self.documento.save()
        self.assertEqual(self.archivo(self.documento, 'documento').status_code, 404)
        self.recurso.activo = False
        self.recurso.save()
        self.client.force_login(self.gestor)
        self.assertEqual(self.archivo(self.recurso, 'recurso').status_code, 404)
        self.assertEqual(self.client.post(self.documento.url).status_code, 405)
        respuesta = self.archivo(self.documento, 'documento', descargar='1')
        self.assertTrue(respuesta['Content-Disposition'].startswith('attachment;'))
        b''.join(respuesta.streaming_content)

    def test_copia_local_no_concede_permisos_y_no_abre_storage(self):
        from apps.centros_id.identidades import identidad_de
        request = RequestFactory().get(self.documento.url)
        request.user = identidad_de(self.gestor)
        from django.http import Http404
        with patch.object(self.documento.archivo.storage, 'open', side_effect=AssertionError('No abrir sin autorización')):
            with self.assertRaises(Http404):
                descarga_archivo_view(request, self.centro.slug, 'documento', self.documento.pk)

    def test_revocacion_canonica_inmediata_incluso_con_proyeccion_local_activa(self):
        self.client.force_login(self.gestor)
        self.centro.gestores.remove(self.gestor)
        self.assertEqual(self.archivo(self.documento, 'documento').status_code, 404)

    def test_endpoint_no_publica_ni_necesita_la_url_directa_del_storage(self):
        self.client.force_login(self.gestor)
        with patch.object(self.documento.archivo.storage, 'url', side_effect=AssertionError('No generar URL directa')):
            for objeto, tipo in ((self.documento, 'documento'), (self.recurso, 'recurso')):
                respuesta = self.client.get(objeto.url if tipo == 'documento' else objeto.archivo_url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(b''.join(respuesta.streaming_content).startswith(b'%PDF'))
