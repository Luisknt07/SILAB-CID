"""Un informe no convierte un archivo ajeno en respaldo de su propia unidad."""
from datetime import date
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.mejora import InformeMejora
from apps.documentos.presentation.mejora_seguimiento import (
    contexto_mejora, origen_mejora_coherente, puede_leer_mejora, tramitar_mejora,
)
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from tests.integration.utiles import identificar, pdf_legible_prueba


class InformeMejoraOrigenArchivosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user('mejora-origen-operador', password=None)
        cls.ajeno = get_user_model().objects.create_user('mejora-origen-ajeno', password=None)
        for actor in (cls.actor, cls.ajeno):
            identificar(actor, tipo_usuario='administrativo', carrera='')
        cls.direccion = get_user_model().objects.create_superuser('mejora-origen-direccion', password=None)
        cls.unidad = Unidad.objects.create(nombre='Unidad origen X', slug='mejora-origen-x',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1), administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Unidad origen Y', slug='mejora-origen-y',
            dependencia='observatorios', fecha_inicio=date(2020, 1, 1), administrador=cls.ajeno)

    def setUp(self):
        self.media = self.enterContext(TemporaryDirectory(prefix='citt-mejora-origen-'))
        self.enterContext(override_settings(MEDIA_ROOT=self.media))
        self.pdf = pdf_legible_prueba('Documento privado del informe de mejora.')

    def informe(self, unidad_archivo=None):
        origen = unidad_archivo or self.unidad
        carpeta = CarpetaRecurso.objects.create(unidad=origen, nombre='Mejora interna', visibilidad='interna')
        recurso = Recurso(unidad=origen, carpeta=carpeta, nombre='Informe de mejora protegido',
            tipo_adjunto='informe', visibilidad='interna', descargar=True, estado='vigente')
        recurso.archivo.save('informe-mejora.pdf', ContentFile(self.pdf))
        return InformeMejora.objects.create(unidad=self.unidad, recurso=recurso, anio=2026, corte='A')

    def test_ningun_actor_puede_abrir_un_archivo_ajeno_mediante_el_informe(self):
        informe = self.informe(self.otra)
        self.assertFalse(origen_mejora_coherente(informe))
        ruta = reverse('recurso_unidad', args=[informe.recurso_id])
        for actor in (self.actor, self.ajeno, self.direccion):
            with self.subTest(actor=actor.username):
                self.assertFalse(puede_leer_mejora(actor, informe))
                self.client.force_login(actor)
                self.assertEqual(self.client.get(ruta, {'download': '1'}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_un_informe_valido_vigente_conserva_acceso_operativo_y_de_direccion(self):
        informe = self.informe()
        self.assertTrue(origen_mejora_coherente(informe))
        ruta = reverse('recurso_unidad', args=[informe.recurso_id])
        for actor in (self.actor, self.direccion):
            with self.subTest(actor=actor.username):
                self.assertTrue(puede_leer_mejora(actor, informe))
                self.client.force_login(actor)
                respuesta = self.client.get(ruta, {'download': '1'})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(b''.join(respuesta.streaming_content), self.pdf)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_un_origen_ajeno_no_se_tramita_ni_registra_una_decision(self):
        informe = self.informe(self.otra)
        antes = RegistroAuditoriaUnidad.objects.count()
        for actor in (self.actor, self.direccion):
            with self.subTest(actor=actor.username):
                with self.assertRaisesMessage(ValidationError, 'no pertenece a esta unidad'):
                    tramitar_mejora(self.unidad, informe.pk, actor, 'remitir_mejora')
        informe.refresh_from_db()
        self.assertIsNone(informe.remitido_en)
        self.assertIsNone(informe.decidido_en)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), antes)

    def test_la_bandeja_operativa_no_expone_un_informe_de_origen_incongruente(self):
        self.informe(self.otra)
        self.assertEqual(contexto_mejora(self.unidad, 2026, 'A', self.actor), {})
        self.assertEqual(contexto_mejora(self.unidad, 2026, 'A', self.direccion), {})

    def test_un_informe_sin_origen_aun_asignado_no_concede_acceso(self):
        informe = InformeMejora(unidad=self.unidad, anio=2026, corte='A')
        self.assertFalse(origen_mejora_coherente(informe))
        self.assertFalse(puede_leer_mejora(self.direccion, informe))
