from io import BytesIO, StringIO
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class IntegridadDocumentalArchivosTests(SimpleTestCase):
    def ejecutar(self, datos=b'original', error=None, huella=None):
        storage = Mock()
        storage.open.side_effect = error
        storage.open.return_value = BytesIO(datos)
        recurso = SimpleNamespace(pk=1, archivo=SimpleNamespace(name='documento.pdf', storage=storage),
                                  hash_sha256=huella or sha256(b'original').hexdigest(), tamano_bytes=8)
        modulo = 'apps.documentos.management.commands.verificar_integridad_documental'
        with patch(modulo + '.Recurso') as recursos, patch(modulo + '.GuiaActividadReserva') as guias:
            recursos.objects.exclude.return_value.exclude.return_value.iterator.return_value = [recurso]
            guias.objects.exclude.return_value.exclude.return_value.iterator.return_value = []
            salida = StringIO()
            call_command('verificar_integridad_documental', stdout=salida, stderr=StringIO())
            return salida.getvalue()

    def test_original_conserva_su_huella(self):
        self.assertIn('Verificados: 1; fallos: 0', self.ejecutar())

    def test_detecta_cambio_del_contenido(self):
        with self.assertRaises(CommandError):
            self.ejecutar(b'alterado')

    def test_detecta_archivo_perdido(self):
        with self.assertRaises(CommandError):
            self.ejecutar(error=FileNotFoundError())
