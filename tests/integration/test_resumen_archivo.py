"""La lectura de metadatos no retiene archivos abiertos ni consume subidas."""
import hashlib
from io import BytesIO
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from django.test import SimpleTestCase

from apps.recursos.models.recursos import _resumen_archivo


class ResumenArchivoTests(SimpleTestCase):
    def archivo_almacenado(self, contenido):
        storage = Mock()
        storage.open.return_value = contenido
        return FieldFile(SimpleNamespace(), SimpleNamespace(storage=storage), 'guia.html')

    def test_archivo_almacenado_abierto_para_inspeccionar_se_cierra(self):
        stream = BytesIO(b'contenido')
        archivo = self.archivo_almacenado(stream)
        self.assertTrue(archivo.closed)
        self.assertEqual(_resumen_archivo(archivo), (9, hashlib.sha256(b'contenido').hexdigest()))
        self.assertTrue(stream.closed)
        self.assertTrue(archivo.closed)

    def test_subida_abierta_conserva_posicion_y_sigue_disponible_para_guardar(self):
        archivo = SimpleUploadedFile('guia.html', b'contenido')
        archivo.seek(3)
        self.assertEqual(_resumen_archivo(archivo)[0], 9)
        self.assertFalse(archivo.closed)
        self.assertEqual(archivo.tell(), 3)
        archivo.close()

    def test_fallo_de_lectura_cierra_solo_el_archivo_abierto_por_la_inspeccion(self):
        stream = BytesIO(b'contenido')
        archivo = self.archivo_almacenado(stream)
        archivo.chunks = Mock(side_effect=OSError('Lectura interrumpida'))
        with self.assertRaisesMessage(OSError, 'Lectura interrumpida'):
            _resumen_archivo(archivo)
        self.assertTrue(stream.closed)

    def test_repetir_inspeccion_reabre_y_cierra_archivo_almacenado(self):
        with TemporaryDirectory() as temporal:
            storage = FileSystemStorage(location=temporal)
            nombre = storage.save('guia.html', ContentFile(b'contenido'))
            archivo = FieldFile(SimpleNamespace(), SimpleNamespace(storage=storage), nombre)
            primero = _resumen_archivo(archivo)
            self.assertTrue(archivo.closed)
            self.assertEqual(_resumen_archivo(archivo), primero)
            self.assertTrue(archivo.closed)
