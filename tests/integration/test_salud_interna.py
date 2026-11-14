"""Sondas operativas aisladas: ninguna prueba abre una base de datos real."""
from contextlib import redirect_stderr, redirect_stdout
import ast
import importlib.util
from io import StringIO
import os
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.db import OperationalError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse

from apps.core.presentation.salud import SaludInternaMiddleware, listo, vivo


@override_settings(
    ALLOWED_HOSTS=['salud.example.edu'],
    SECURE_SSL_REDIRECT=True,
    SECURE_REDIRECT_EXEMPT=[r'^salud/(?:vivo|listo)/$'],
    RLS_ENABLED=True,
    RATE_LIMIT_ENABLED=True,
    CONTENT_SECURITY_POLICY="default-src 'self'; script-src 'nonce-{nonce}'",
)
class SaludInternaTests(SimpleTestCase):
    def test_exencion_de_produccion_y_manifiesto_declaran_solo_salud_interna(self):
        from apps.core.manifiesto import MANIFIESTO

        produccion = Path(__file__).resolve().parents[2] / 'config/settings_production.py'
        arbol = ast.parse(produccion.read_text(encoding='utf-8'))
        excepciones = next(ast.literal_eval(nodo.value) for nodo in arbol.body
                           if isinstance(nodo, ast.Assign) and any(
                               isinstance(destino, ast.Name) and destino.id == 'SECURE_REDIRECT_EXEMPT'
                               for destino in nodo.targets))
        self.assertEqual(excepciones, [r'^salud/(?:vivo|listo)/$'])
        for ruta in ('', 'admin/', 'salud/listo', 'salud/vivo/extra', 'otra/salud/listo/'):
            self.assertFalse(any(re.search(patron, ruta) for patron in excepciones))
        self.assertIn('apps.core.presentation.salud_urls', MANIFIESTO.rutas)
        self.assertEqual(MANIFIESTO.salud, ('apps.core.presentation.salud',))
        self.assertIn('supervision_interna_v1', MANIFIESTO.contratos)

    def test_rutas_propias_y_respuesta_viva_no_consultan_datos(self):
        self.assertEqual(reverse('salud_interna:vivo'), '/salud/vivo/')
        self.assertIs(resolve('/salud/listo/').func, listo)
        for metodo in ('get', 'head'):
            with self.subTest(metodo=metodo), patch('apps.core.presentation.salud.connection') as conexion:
                conexion.cursor.side_effect = AssertionError('SQL inesperado')
                respuesta = getattr(self.client, metodo)('/salud/vivo/', HTTP_HOST='salud.example.edu')
            self.assertEqual(respuesta.status_code, 204)
            self.assertEqual(respuesta.content, b'')
            self.assertIn('no-store', respuesta['Cache-Control'])
            self.assertFalse(respuesta.cookies)

    def test_listo_solo_ejecuta_select_constante_para_get_y_head(self):
        for metodo in ('get', 'head'):
            with self.subTest(metodo=metodo), patch('apps.core.presentation.salud.connection') as conexion:
                cursor = conexion.cursor.return_value.__enter__.return_value
                cursor.fetchone.return_value = (1,)
                respuesta = getattr(self.client, metodo)('/salud/listo/', HTTP_HOST='salud.example.edu')
            self.assertEqual(respuesta.status_code, 204)
            self.assertEqual(respuesta.content, b'')
            cursor.execute.assert_called_once_with('SELECT 1')
            self.assertIn('no-store', respuesta['Cache-Control'])

    def test_caida_de_bd_no_publica_excepcion_ni_datos(self):
        with patch('apps.core.presentation.salud.connection') as conexion:
            conexion.cursor.side_effect = OperationalError('contraseña-ficticia-no-publicable')
            respuesta = self.client.get('/salud/listo/', HTTP_HOST='salud.example.edu')
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.content, b'')
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertNotIn('contraseña-ficticia', str(respuesta.headers))

    def test_resultado_no_valido_no_declara_disponibilidad(self):
        with patch('apps.core.presentation.salud.connection') as conexion:
            conexion.cursor.return_value.__enter__.return_value.fetchone.return_value = None
            self.assertEqual(listo(RequestFactory().get('/salud/listo/')).status_code, 503)

    def test_metodos_distintos_de_get_head_no_consultan_datos(self):
        for ruta in ('/salud/vivo/', '/salud/listo/'):
            for metodo in ('post', 'put', 'patch', 'delete', 'options', 'trace'):
                with self.subTest(ruta=ruta, metodo=metodo), patch('apps.core.presentation.salud.connection') as conexion:
                    conexion.cursor.side_effect = AssertionError('SQL inesperado')
                    respuesta = self.client.generic(metodo.upper(), ruta, HTTP_HOST='salud.example.edu')
                self.assertEqual(respuesta.status_code, 405)
                self.assertEqual(respuesta['Allow'], 'GET, HEAD')
                self.assertIn('no-store', respuesta['Cache-Control'])

    def test_host_rechazado_sin_sql_y_ssl_conservado_fuera_de_sondas(self):
        with patch('apps.core.presentation.salud.connection') as conexion:
            conexion.cursor.side_effect = AssertionError('SQL inesperado')
            rechazada = self.client.get('/salud/vivo/', HTTP_HOST='ajeno.example.edu')
            fuera = self.client.get('/salud/otra/', HTTP_HOST='salud.example.edu')
            portal = self.client.get('/', HTTP_HOST='salud.example.edu')
        self.assertEqual(rechazada.status_code, 400)
        self.assertEqual(rechazada.content, b'')
        self.assertIn('no-store', rechazada['Cache-Control'])
        self.assertEqual(fuera.status_code, 301)
        self.assertEqual(portal.status_code, 301)
        self.assertEqual(portal['Location'], 'https://salud.example.edu/')

    def test_solo_intercepta_rutas_exactas_y_omite_sesion_incluso_con_cookie(self):
        siguiente = MagicMock(return_value=HttpResponse())
        middleware = SaludInternaMiddleware(siguiente)
        factory = RequestFactory()
        for ruta in ('/salud/vivo/extra', '/salud/listo', '/es/salud/vivo/', '/otra/'):
            middleware(factory.get(ruta))
        self.assertEqual(siguiente.call_count, 4)
        self.client.cookies['sessionid'] = 'sesion-no-debe-resolverse'
        respuesta = self.client.get('/salud/vivo/', HTTP_HOST='salud.example.edu')
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(vivo(factory.head('/salud/vivo/')).content, b'')


class ScriptSaludTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruta = Path(__file__).resolve().parents[2] / 'scripts' / 'comprobar_salud.py'
        spec = importlib.util.spec_from_file_location('comprobar_salud_auditado', cls.ruta)
        cls.script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.script)

    def test_importar_sonda_no_inicia_django(self):
        resultado = subprocess.run(
            [sys.executable, '-c', 'import runpy, sys; runpy.run_path(sys.argv[1]); '
             'assert "django" not in sys.modules', str(self.ruta)],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_host_explicitamente_permitido_sin_urls_comodines_o_inyeccion(self):
        for valor, esperado in (('salud.example.edu,otra.example.edu', 'salud.example.edu'),
                                ('.example.edu', 'example.edu'), ('[::1]', '[::1]')):
            self.assertEqual(self.script.host_permitido(valor), esperado)
        for valor in ('', '*', 'https://salud.example.edu', 'host/ruta', 'host:8000',
                      'host\r\nX-Extra: secreto', 'usuario@host', 'host?parametro', '[invalido]'):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.script.host_permitido(valor)

    def test_solo_204_es_saludable_y_no_usa_proxy_ni_forwarded_proto(self):
        for estado in (204, 200, 301, 302, 307, 308, 503):
            with self.subTest(estado=estado), patch.dict(os.environ, {'ALLOWED_HOSTS': 'salud.example.edu'}), patch.object(
                    self.script, 'build_opener') as construir:
                cliente = construir.return_value
                cliente.open.return_value.__enter__.return_value.status = estado
                self.assertEqual(self.script.comprobar(), 0 if estado == 204 else 1)
                solicitud = cliente.open.call_args.args[0]
                self.assertEqual(solicitud.full_url, 'http://127.0.0.1:8000/salud/listo/')
                self.assertEqual(solicitud.get_method(), 'HEAD')
                self.assertEqual(solicitud.get_header('Host'), 'salud.example.edu')
                self.assertIsNone(solicitud.get_header('X-forwarded-proto'))
                self.assertEqual(cliente.open.call_args.kwargs, {'timeout': 3})
                self.assertEqual(construir.call_args.args[0].proxies, {})
                self.assertIsInstance(construir.call_args.args[1], self.script.SinRedirecciones)
        self.assertIsNone(self.script.SinRedirecciones().redirect_request(None, None, 301, '', {}, 'https://otro/'))

    def test_configuracion_invalida_y_fallo_http_no_imprimen_detalles(self):
        salida, errores = StringIO(), StringIO()
        with redirect_stdout(salida), redirect_stderr(errores):
            with patch.dict(os.environ, {'ALLOWED_HOSTS': '*'}), patch.object(self.script, 'build_opener') as construir:
                self.assertEqual(self.script.comprobar(), 2)
                construir.assert_not_called()
            for error in (URLError('dato-privado'), TimeoutError('dato-privado'),
                          HTTPError('http://local/', 302, 'dato-privado', {}, None)):
                with patch.dict(os.environ, {'ALLOWED_HOSTS': 'salud.example.edu'}), patch.object(
                        self.script, 'build_opener') as construir:
                    construir.return_value.open.side_effect = error
                    self.assertEqual(self.script.comprobar(), 1)
        self.assertEqual(salida.getvalue() + errores.getvalue(), '')
