"""Excepciones precisas para fuentes docentes distribuidas sin referencias literales."""
from io import BytesIO, StringIO
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from apps.integraciones.management.commands.auditar_huerfanos import JUSTIFICADOS
from apps.formacion.management.cursos_precargados.aplicaciones_logisticas_kit import builder


class AuditoriaHuerfanosKitTests(SimpleTestCase):
    paquete = 'apps/formacion/management/cursos_precargados/aplicaciones_logisticas_kit/contenido/'
    fuentes = ('guias/unidad_02.md', 'guias/unidad_04.md', 'templates/403.html')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='slcid-huerfanos-kit-')
        self.addCleanup(carpeta.cleanup)
        self.raiz = Path(carpeta.name)
        self.contenido = self.raiz / self.paquete
        for nombre in self.fuentes:
            ruta = self.contenido / nombre
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text('Contenido docente de ensayo', encoding='utf-8')

    def test_las_tres_excepciones_se_distribuyen_en_el_paquete_y_tienen_motivo(self):
        for nombre in self.fuentes:
            self.assertIn('builder.source_files', JUSTIFICADOS[self.paquete + nombre])
        with patch.object(builder, 'SOURCE_DIR', self.contenido):
            with ZipFile(BytesIO(builder.build_zip())) as archivo:
                self.assertEqual(set(archivo.namelist()), {
                    *(builder.KIT_DIRNAME + '/' + nombre for nombre in self.fuentes),
                    builder.KIT_DIRNAME + '/MANIFIESTO_SHA256.txt',
                })

    def test_los_filtros_del_empaquetador_no_extienden_la_excepcion_a_otras_fuentes(self):
        excluidos = ('.qa/ignorado.md', '.secreto-local', 'db.sqlite3', 'archivo.bin')
        for nombre in excluidos:
            ruta = self.contenido / nombre
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text('Solo fixture; sin datos reales', encoding='utf-8')
            self.assertNotIn(self.paquete + nombre, JUSTIFICADOS)
        with patch.object(builder, 'SOURCE_DIR', self.contenido):
            self.assertEqual({nombre for nombre, datos in builder.source_files()}, set(self.fuentes))

    def test_excepciones_no_ocultan_un_archivo_realmente_sin_referencias(self):
        sobrante = 'apps/ejemplo/archivo_fuera_del_paquete_sin_consumidor.py'
        (self.raiz / sobrante).parent.mkdir(parents=True, exist_ok=True)
        (self.raiz / sobrante).write_text('VALOR = 1\n', encoding='utf-8')
        lista = [*(self.paquete + nombre for nombre in self.fuentes), sobrante]
        resultado = CompletedProcess([], 0, stdout='\n'.join(lista) + '\n')
        salida = StringIO()
        with override_settings(BASE_DIR=self.raiz):
            with patch('apps.integraciones.management.commands.auditar_huerfanos.subprocess.run', return_value=resultado):
                with self.assertRaises(CommandError):
                    call_command('auditar_huerfanos', estricto=True, stdout=salida)
        self.assertIn('sin referencia: ' + sobrante, salida.getvalue())
        self.assertIn('1 archivos sin referencia de 4', salida.getvalue())
