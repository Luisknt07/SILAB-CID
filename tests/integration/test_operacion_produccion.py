"""Contratos de operación: límites reales del servidor y recuperación aislada.

Las herramientas PostgreSQL se sustituyen por ejecutables de prueba. Ninguna
prueba abre, crea, restaura ni elimina una base de datos real.
"""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SHELL = shutil.which('sh')
if os.name == 'nt':
    git_shell = Path('C:/Program Files/Git/bin/bash.exe')
    if git_shell.is_file():
        SHELL = str(git_shell)


class LimitesServidorProduccionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'servidor_auditado', ROOT / 'scripts' / 'servir_produccion.py'
        )
        cls.servidor = importlib.util.module_from_spec(spec)
        with mock.patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'config.settings_production'}):
            spec.loader.exec_module(cls.servidor)

    def argumentos(self, **variables):
        entorno = {'TRUSTED_PROXY_IP': '127.0.0.1', **variables}
        with mock.patch.dict(os.environ, entorno, clear=True):
            return self.servidor.argumentos()

    def test_capacidad_predeterminada_tiene_limites_y_proxy_exacto(self):
        ajustes = self.argumentos()
        self.assertEqual(ajustes['threads'], 8)
        self.assertEqual(ajustes['connection_limit'], 100)
        self.assertEqual(ajustes['channel_timeout'], 60)
        self.assertEqual(ajustes['max_request_header_size'], 32 * 1024)
        self.assertEqual(ajustes['max_request_body_size'], 64 * 1024 * 1024)
        self.assertTrue(ajustes['clear_untrusted_proxy_headers'])
        self.assertFalse(ajustes['expose_tracebacks'])
        self.assertEqual(ajustes['trusted_proxy_count'], 1)

    def test_se_puede_dimensionar_sin_cambiar_codigo(self):
        ajustes = self.argumentos(WEB_THREADS='12', WEB_CONNECTION_LIMIT='160', WEB_CHANNEL_TIMEOUT='90')
        self.assertEqual((ajustes['threads'], ajustes['connection_limit'], ajustes['channel_timeout']), (12, 160, 90))

    def test_argumentos_compatibles_con_la_api_instalada_de_waitress(self):
        from waitress.adjustments import Adjustments

        ajustes = Adjustments(**self.argumentos())
        self.assertEqual(ajustes.connection_limit, 100)
        self.assertEqual(ajustes.max_request_header_size, 32 * 1024)

    def test_rechaza_capacidad_ilimitada_invalida_o_inconsistente(self):
        for variable, valores in {
            'WEB_THREADS': ('0', '65', '-1', 'ocho'),
            'WEB_CONNECTION_LIMIT': ('0', '1025', '-1', 'muchas'),
            'WEB_CHANNEL_TIMEOUT': ('0', '301', '-1', 'largo'),
        }.items():
            for valor in valores:
                with self.subTest(variable=variable, valor=valor), self.assertRaises(SystemExit):
                    self.argumentos(**{variable: valor})
        with self.assertRaises(SystemExit):
            self.argumentos(WEB_THREADS='32', WEB_CONNECTION_LIMIT='16')

    def test_rechaza_proxy_comodin_y_lista_de_proxies(self):
        for proxy in ('', '*', '127.0.0.1,192.0.2.1', 'proxy.interno'):
            with self.subTest(proxy=proxy), self.assertRaises(SystemExit):
                self.argumentos(TRUSTED_PROXY_IP=proxy)


class PrivacidadInventarioTests(unittest.TestCase):
    def test_el_auditor_clasifica_privados_sin_leer_su_contenido(self):
        spec = importlib.util.spec_from_file_location(
            'inventario_auditado', ROOT / 'scripts' / 'auditar_repositorio.py'
        )
        auditor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auditor)
        privados = ('.env', '.env.production', 'clave.key', 'certificado.pem',
                    'datos.dump', 'datos.sqlite3', 'certificado.p12', 'certificado.pfx')
        with tempfile.TemporaryDirectory(prefix='citt-inventario-') as temporal:
            carpeta = Path(temporal)
            fuente = carpeta / 'fuente.py'
            fuente.write_bytes(b'valor = 1\n')
            for nombre in privados:
                (carpeta / nombre).write_bytes(b'contenido ficticio que no debe leerse')
            original = Path.read_bytes

            def leer_solo_fuente(path):
                if path.name in privados:
                    self.fail('El inventario intento leer un archivo privado.')
                return original(path)

            listado = '\0'.join((*privados, 'fuente.py')) + '\0'
            with mock.patch.object(auditor, 'ROOT', carpeta), mock.patch.object(
                auditor.subprocess, 'run', side_effect=[
                    SimpleNamespace(stdout=listado.encode()), SimpleNamespace(stdout=b'')
                ]
            ), mock.patch.object(Path, 'read_bytes', leer_solo_fuente):
                informe = auditor.audit()
            self.assertEqual(informe['bytes'], len(b'valor = 1\n'))
            self.assertEqual({error['archivo'] for error in informe['errores']}, set(privados))
            self.assertEqual(informe['duplicados_exactos'], [])


@unittest.skipUnless(SHELL, 'Las pruebas de operación Linux requieren un intérprete POSIX.')
class RecuperacionAisladaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='citt-operacion-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.bin = self.directory / 'bin'
        self.bin.mkdir()
        self.log = self.directory / 'operaciones.log'
        self.backup = self.directory / 'database_prueba.dump'
        self.backup.write_text('respaldo simulado', encoding='utf8')
        Path(str(self.backup) + '.sha256').write_text('checksum simulado', encoding='utf8')
        comandos = {
            'sha256sum': 'exit "${MOCK_CHECKSUM_EXIT:-0}"',
            'createdb': 'exit "${MOCK_CREATEDB_EXIT:-0}"',
            'dropdb': 'exit 0',
            'pg_restore': 'if [ "$1" = --list ]; then exit 0; fi\nexit "${MOCK_RESTORE_EXIT:-0}"',
            'psql': 'printf "1\\n"',
            'pg_dump': 'exit 97',
        }
        for nombre, cuerpo in comandos.items():
            ejecutable = self.bin / nombre
            ejecutable.write_text(
                '#!/bin/sh\nprintf "%s\\n" "' + nombre + ' $*" >> "$MOCK_LOG"\n' + cuerpo + '\n',
                encoding='utf8', newline='\n',
            )
            ejecutable.chmod(0o755)

    def ejecutar(self, script='verify_database_backup.sh', **variables):
        entorno = {
            **os.environ,
            'MOCK_BIN': ('/' + self.bin.drive[0].lower() + self.bin.as_posix()[2:])
            if os.name == 'nt' else self.bin.as_posix(),
            'DB_HOST': 'db.simulada', 'DB_USER': 'rol_simulado',
            'DB_PASSWORD': 'clave-ficticia-solo-para-pruebas', 'DB_NAME': 'citt_simulada',
            'MOCK_LOG': self.log.as_posix(), 'RESTORE_DB_PREFIX': 'citt_qa',
            'BACKUP_DIR': (self.directory / 'destino').as_posix(),
            'MEDIA_ROOT': self.directory.as_posix(),
            **variables,
        }
        # Git Bash reconstruye PATH al arrancar en Windows: establecer el de
        # los dobles dentro del shell asegura que no se ejecuta un cliente real.
        argumentos = [SHELL, '-c', 'PATH="$MOCK_BIN:$PATH"; export PATH; exec sh "$@"',
                      '--', (ROOT / 'scripts' / script).as_posix()]
        if script == 'verify_database_backup.sh':
            argumentos.append(self.backup.as_posix())
        resultado = subprocess.run(argumentos, env=entorno, capture_output=True, text=True, timeout=15)
        operaciones = self.log.read_text(encoding='utf8').splitlines() if self.log.exists() else []
        return resultado, operaciones

    def test_si_createdb_falla_nunca_borra_la_base_preexistente(self):
        resultado, operaciones = self.ejecutar(MOCK_CREATEDB_EXIT='41')
        self.assertEqual(resultado.returncode, 41, resultado.stderr)
        self.assertTrue(any(linea.startswith('createdb ') for linea in operaciones))
        self.assertFalse(any(linea.startswith('dropdb ') for linea in operaciones))

    def test_al_fallar_restauracion_limpia_solo_su_base_temporal(self):
        resultado, operaciones = self.ejecutar(MOCK_RESTORE_EXIT='42')
        self.assertEqual(resultado.returncode, 42, resultado.stderr)
        creada = next(linea.split()[-1] for linea in operaciones if linea.startswith('createdb '))
        eliminadas = [linea.split()[-1] for linea in operaciones if linea.startswith('dropdb ')]
        self.assertEqual(eliminadas, [creada])
        self.assertTrue(creada.startswith('citt_qa_'))

    def test_restauracion_completa_consulta_y_limpia_su_base(self):
        resultado, operaciones = self.ejecutar(RESTORE_DB_PREFIX='c' * 32)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertTrue(any(linea.startswith('psql ') for linea in operaciones))
        creada = next(linea.split()[-1] for linea in operaciones if linea.startswith('createdb '))
        self.assertLessEqual(len(creada), 63)
        self.assertEqual([linea.split()[-1] for linea in operaciones if linea.startswith('dropdb ')], [creada])

    def test_prefijos_invalidos_fallan_antes_de_abrir_conexion(self):
        for prefijo in ('9qa', 'produccion-x', 'QA', 'x' * 33, '../prod'):
            with self.subTest(prefijo=prefijo):
                resultado, operaciones = self.ejecutar(RESTORE_DB_PREFIX=prefijo)
                self.assertEqual(resultado.returncode, 2, resultado.stderr)
                self.assertEqual(operaciones, [])

    def test_checksum_incorrecto_no_crea_ni_borra_bases(self):
        resultado, operaciones = self.ejecutar(MOCK_CHECKSUM_EXIT='43')
        self.assertEqual(resultado.returncode, 43, resultado.stderr)
        self.assertFalse(any(linea.startswith(('createdb ', 'dropdb ')) for linea in operaciones))

    def test_retencion_cero_no_crea_archivos_ni_invoca_postgresql(self):
        for script in ('backup_database.sh', 'backup_media.sh'):
            with self.subTest(script=script):
                resultado, operaciones = self.ejecutar(script=script, BACKUP_RETENTION_DAYS='0')
                self.assertEqual(resultado.returncode, 2, resultado.stderr)
                self.assertEqual(operaciones, [])
                self.assertFalse((self.directory / 'destino').exists())
