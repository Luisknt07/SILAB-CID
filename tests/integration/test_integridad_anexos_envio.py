"""Un respaldo inválido no se valida aunque el anexo requiera revisión humana."""
from datetime import date
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.integridad_anexos import exigir_archivo_anexo
from apps.recursos.models.recursos import Recurso


class IntegridadArchivosAnexosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Unidad de anexos QA', slug='unidad-anexos-qa',
            dependencia='laboratorios', descripcion='Pruebas aisladas de integridad',
            fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad de anexos QA', slug='otra-unidad-anexos-qa',
            dependencia='observatorios', descripcion='Otra unidad de prueba',
            fecha_inicio=date(2026, 1, 1))
        padre = DocumentoExigido.objects.create(codigo='INTEGRIDAD-PADRE-QA', nombre='Entrega de prueba QA',
            carpeta='planeacion', origen='ambos', periodicidad='semestral', plazo_regla='ninguno')
        cls.exigido = DocumentoExigido.objects.create(codigo='INTEGRIDAD-ANEXO-QA', nombre='Anexo personalizado QA',
            carpeta='planeacion', origen='unidad', periodicidad='semestral', plazo_regla='ninguno', anexo_de=padre)

    def setUp(self):
        media = TemporaryDirectory(prefix='citt-integridad-anexos-')
        self.addCleanup(media.cleanup)
        ajustes = override_settings(MEDIA_ROOT=media.name)
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.recurso = Recurso(unidad=self.unidad, nombre='Respaldo externo QA',
            descripcion='Anexo externo con contenido real de prueba; sin procedencia nativa.',
            tipo_adjunto='evidencia', visibilidad='interna', version=2)
        self.recurso.archivo.save('respaldo-externo.txt', ContentFile(b'Contenido del anexo externo de prueba.'), save=True)
        self.recurso.archivo.close()
        self.anexo = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=self.exigido,
            anio=2026, corte='B', estado='generado', version=2, recurso=self.recurso)

    def test_respaldo_externo_personalizado_integro_no_exige_origen_nativo_ni_metas(self):
        recurso = exigir_archivo_anexo(self.anexo)
        self.assertEqual(recurso.pk, self.recurso.pk)
        self.anexo.refresh_from_db()
        self.assertEqual(self.anexo.estado, 'generado')
        self.assertIsNone(self.anexo.validado_en)

    def test_falta_recurso_no_admite_revision(self):
        self.anexo.recurso = None
        with self.assertRaisesMessage(ValidationError, 'falta su archivo'):
            exigir_archivo_anexo(self.anexo)

    def test_recurso_de_otra_unidad_no_admite_revision(self):
        Recurso.objects.filter(pk=self.recurso.pk).update(unidad=self.otra)
        with self.assertRaisesMessage(ValidationError, 'otra unidad'):
            exigir_archivo_anexo(self.anexo)

    def test_recurso_retirado_se_detecta_aunque_exista_relacion_en_cache(self):
        self.assertTrue(self.anexo.recurso.activo)
        Recurso.objects.filter(pk=self.recurso.pk).update(activo=False)
        with self.assertRaisesMessage(ValidationError, 'retirado u obsoleto'):
            exigir_archivo_anexo(self.anexo)

    def test_recurso_obsoleto_no_admite_revision(self):
        Recurso.objects.filter(pk=self.recurso.pk).update(estado='obsoleto')
        with self.assertRaisesMessage(ValidationError, 'retirado u obsoleto'):
            exigir_archivo_anexo(self.anexo)

    def test_version_del_recurso_debe_coincidir_con_el_anexo(self):
        Recurso.objects.filter(pk=self.recurso.pk).update(version=1)
        with self.assertRaisesMessage(ValidationError, 'versión del archivo'):
            exigir_archivo_anexo(self.anexo)

    def test_archivo_modificado_no_admite_revision(self):
        with self.recurso.archivo.open('ab') as archivo:
            archivo.write(b'\nCambio posterior al archivo registrado.')
        with self.assertRaisesMessage(ValidationError, 'huella archivada'):
            exigir_archivo_anexo(self.anexo)

    def test_archivo_no_disponible_no_admite_revision(self):
        self.recurso.archivo.storage.delete(self.recurso.archivo.name)
        with self.assertRaisesMessage(ValidationError, 'no está disponible'):
            exigir_archivo_anexo(self.anexo)

    def test_enlace_sin_archivo_no_sustituye_el_respaldo_revisable(self):
        Recurso.objects.filter(pk=self.recurso.pk).update(archivo='', url='https://example.org/respaldo')
        with self.assertRaisesMessage(ValidationError, 'no tiene un archivo'):
            exigir_archivo_anexo(self.anexo)

    def test_archivo_vacio_no_admite_revision_aunque_coincida_la_huella(self):
        import hashlib
        with self.recurso.archivo.open('wb') as archivo:
            archivo.write(b'')
        Recurso.objects.filter(pk=self.recurso.pk).update(hash_sha256=hashlib.sha256(b'').hexdigest())
        with self.assertRaisesMessage(ValidationError, 'está vacío'):
            exigir_archivo_anexo(self.anexo)
