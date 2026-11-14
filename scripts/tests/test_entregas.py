"""Regresiones de entrega: secretos, LFS, historial, integridad e inventario."""

import hashlib
import json
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.auditar_almacenamiento import inventario
from scripts.preparar_entrega import archivos_entrega, preparar


class EntregasTests(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(prefix='slcid-entrega-test-')
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        self.repo = self.raiz / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Prueba local')
        self.git('config', 'user.email', 'prueba@example.invalid')
        self.escribir('manage.py', 'print("entrega")\n')
        self.escribir('.env-example', 'SECRET_KEY=\n')
        self.escribir('.gitignore', '/var/\n.env\n')
        self.escribir('apps/portal/static/video.mp4', b'video-binario-para-prueba')
        self.confirmar()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, stderr=subprocess.PIPE)

    def escribir(self, nombre, contenido):
        ruta = self.repo / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido if isinstance(contenido, bytes) else contenido.encode('utf-8'))

    def confirmar(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Versión de prueba')

    def test_entrega_preserva_video_omite_historial_secretos_y_datos_y_verifica_huellas(self):
        self.escribir('.env', 'SECRET_KEY=secreto-privado')
        self.escribir('var/media/privado.pdf', 'dato-operativo')
        self.escribir('no-versionado.txt', 'salida-local')
        self.escribir('output/vista.pdf', 'pdf-versionado-de-qa')
        self.confirmar()
        self.escribir('otro-no-versionado.txt', 'salida')
        resultado = preparar(self.repo, self.raiz / 'entregas')
        with tarfile.open(resultado['paquete']) as tar:
            nombres = tar.getnames()
            self.assertNotIn('slcid/.env', nombres)
            self.assertNotIn('slcid/var/media/privado.pdf', nombres)
            self.assertNotIn('slcid/output/vista.pdf', nombres)
            self.assertNotIn('slcid/otro-no-versionado.txt', nombres)
            self.assertFalse(any('/.git/' in n for n in nombres))
            self.assertEqual(tar.extractfile('slcid/apps/portal/static/video.mp4').read(), b'video-binario-para-prueba')
            manifiesto = json.load(tar.extractfile('slcid/ENTREGA.json'))
            self.assertEqual(manifiesto['commit'], resultado['commit'])
            for fila in manifiesto['archivos']:
                data = tar.extractfile('slcid/' + fila['ruta']).read()
                self.assertEqual(hashlib.sha256(data).hexdigest(), fila['sha256'])
                self.assertEqual(len(data), fila['bytes'])
        digest = hashlib.sha256(Path(resultado['paquete']).read_bytes()).hexdigest()
        self.assertTrue(Path(resultado['sha256']).read_text().startswith(digest))

    def test_entrega_reproducible_y_no_sobrescribe_paquete(self):
        primero = preparar(self.repo, self.raiz / 'uno')
        segundo = preparar(self.repo, self.raiz / 'dos')
        self.assertEqual(Path(primero['paquete']).read_bytes(), Path(segundo['paquete']).read_bytes())
        with self.assertRaises(FileExistsError):
            preparar(self.repo, self.raiz / 'uno')
        self.assertTrue(Path(primero['sha256']).is_file())

    def test_rechaza_cambios_pendientes(self):
        self.escribir('manage.py', '# cambio sin commit')
        with self.assertRaisesRegex(ValueError, 'sin confirmar'):
            preparar(self.repo, self.raiz / 'salida')
        self.assertFalse((self.raiz / 'salida').exists())

    def test_rechaza_secretos_versionados_incluso_si_git_los_admite(self):
        self.escribir('credencial.pem', 'contenido sensible de prueba')
        self.confirmar()
        with self.assertRaisesRegex(ValueError, 'privado'):
            preparar(self.repo, self.raiz / 'salida')

    def test_rechaza_punteros_lfs_sin_descargar(self):
        self.escribir('apps/portal/static/video.mp4', 'version https://git-lfs.github.com/spec/v1\noid sha256:000\nsize 3\n')
        self.confirmar()
        with self.assertRaisesRegex(ValueError, 'Git LFS'):
            preparar(self.repo, self.raiz / 'salida')

    def test_rechaza_submodulos_en_lugar_de_entregar_codigo_incompleto(self):
        commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('update-index', '--add', '--cacheinfo', f'160000,{commit},externo')
        self.git('commit', '-qm', 'Submódulo de ensayo')
        with self.assertRaisesRegex(ValueError, 'regular seguro'):
            archivos_entrega(self.repo.resolve())

    def test_detecta_cambio_de_contenido_entre_inventario_y_compresion(self):
        with patch('scripts.preparar_entrega.huella', return_value='huella-distinta'):
            with self.assertRaisesRegex(ValueError, 'Cambió el archivo'):
                preparar(self.repo, self.raiz / 'salida')
        self.assertEqual(list((self.raiz / 'salida').iterdir()), [])

    def test_retira_paquete_incompleto_si_falla_escritura(self):
        with patch('scripts.preparar_entrega.tarfile.open', side_effect=OSError('disco de prueba')):
            with self.assertRaisesRegex(OSError, 'disco'):
                preparar(self.repo, self.raiz / 'salida')
        self.assertEqual(list((self.raiz / 'salida').iterdir()), [])


class InventarioTests(unittest.TestCase):
    def test_cuenta_bytes_sin_leer_contenidos(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            (raiz / '.env').write_bytes(b'secreto')
            (raiz / 'var').mkdir()
            (raiz / 'var' / 'dato.bin').write_bytes(b'123')
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('No leer secretos')):
                resultado = inventario(raiz)
            self.assertEqual(resultado['bytes'], 10)
            self.assertEqual(resultado['archivos'], 2)
            self.assertTrue(resultado['completo'])

    def test_no_sigue_enlaces_simbolicos_ni_junctions_windows(self):
        enlace = SimpleNamespace(name='enlace', stat=lambda **kw: SimpleNamespace(
            st_mode=stat.S_IFLNK, st_file_attributes=0))
        junction = SimpleNamespace(name='junction', stat=lambda **kw: SimpleNamespace(
            st_mode=stat.S_IFDIR, st_file_attributes=1024))
        with patch('scripts.auditar_almacenamiento.os.scandir') as scan:
            scan.return_value.__enter__.return_value = iter([enlace, junction])
            resultado = inventario(Path.cwd())
        self.assertEqual(resultado['bytes'], 0)
        self.assertEqual(resultado['enlaces_omitidos'], ['enlace', 'junction'])


if __name__ == '__main__':
    unittest.main()
