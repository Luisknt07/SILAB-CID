"""Contratos de carga selectiva: rutas, configuración y cabeceras."""
import importlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from apps.core.presentation.presentacion_institucional import PresentacionInstitucionalMiddleware
from apps.integraciones.context_processors import reservation_notifications
from apps.core.routing.diferidas import vista_diferida


class CargaSelectivaTests(SimpleTestCase):
    def test_registro_de_rutas_no_importa_dominios_ni_necesita_django_setup(self):
        codigo = '''
import importlib.abc
import sys
class Bloqueo(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        bloques = ('apps.gestion_unidades.presentation', 'apps.formacion.presentation',
                                'apps.reservas.presentation', 'apps.recursos.presentation',
                                'apps.laboratorios.operacion.presentation',
                                'apps.plantas_piloto.operacion.presentation',
                                'apps.observatorios.operacion.presentation',
                                'apps.centros_experimentales.operacion.presentation',
                                'apps.core.usuarios', 'apps.recursos.entrega')
        if fullname.startswith(bloques) and fullname not in bloques and not fullname.endswith('.operativas_urls'):
            raise ImportError('Controlador cargado antes de la petición: ' + fullname)
sys.meta_path.insert(0, Bloqueo())
from config.rutas_operativas import urlpatterns
assert len(urlpatterns) == 274
assert [p.name for p in urlpatterns].count('estado_curso') == 1
assert [p.name for p in urlpatterns].count('logistica_identidad') == 1
assert [p.name for p in urlpatterns].count('logistica_juego_cerveza') == 1
assert [p.name for p in urlpatterns].count('logistica_cerveza_multijugador') == 1
assert [p.name for p in urlpatterns].count('logistica_operaciones') == 1
assert [p.name for p in urlpatterns].count('logistica_distribucion') == 1
assert [p.name for p in urlpatterns].count('gestion_recursos_buscar') == 1
from django.apps import apps
assert not apps.ready
'''
        resultado = subprocess.run([sys.executable, '-X', 'utf8', '-c', codigo], cwd=Path(__file__).resolve().parents[2],
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_auditor_rechaza_direcciones_externas_y_reconoce_ruta_local(self):
        from django.core.management.base import CommandError
        from apps.integraciones.management.commands.auditar_rendimiento_paginas import validar_ruta
        for ruta in ('https://example.com/', '//example.com/', 'pagina/', '/pagina/#fragmento'):
            with self.subTest(ruta=ruta), self.assertRaises(CommandError):
                validar_ruta(ruta)
        self.assertEqual(validar_ruta('/servicios/?q=prueba'), '/servicios/?q=prueba')

    def test_ruta_se_importa_al_invocarla_y_conserva_argumentos(self):
        callback = Mock(return_value=HttpResponse('ok'))
        with patch('apps.core.routing.diferidas.import_string', return_value=callback) as importar:
            vista = vista_diferida('prueba_auditoria.controlador')
            self.assertEqual(vista.__name__, 'controlador')
            self.assertEqual(vista.__module__, 'prueba_auditoria')
            importar.assert_not_called()
            request = RequestFactory().get('/')
            self.assertEqual(vista(request, codigo='a').content, b'ok')
            vista(request, codigo='b')
            importar.assert_called_once_with('prueba_auditoria.controlador')
            callback.assert_called_with(request, codigo='b')

    def test_todas_las_rutas_diferidas_conservan_metadatos_csrf(self):
        from asgiref.sync import iscoroutinefunction
        rutas = importlib.import_module('config.rutas_operativas').urlpatterns
        self.assertEqual(len(rutas), 274)
        self.assertEqual([r.name for r in rutas].count('estado_curso'), 1)
        self.assertEqual([r.name for r in rutas].count('logistica_identidad'), 1)
        self.assertEqual([r.name for r in rutas].count('logistica_juego_cerveza'), 1)
        self.assertEqual([r.name for r in rutas].count('gestion_recursos_buscar'), 1)
        for ruta in rutas:
            vista = ruta.callback
            real = vista.controlador()
            self.assertTrue(callable(real), vista.ruta_diferida)
            self.assertFalse(iscoroutinefunction(real), vista.ruta_diferida)
            self.assertEqual(vista.csrf_exempt, getattr(real, 'csrf_exempt', False), vista.ruta_diferida)
            self.assertFalse(getattr(real, '_non_atomic_requests', set()), vista.ruta_diferida)

    def test_configuracion_no_resuelve_proveedores_si_la_peticion_no_los_usa(self):
        modulos = ['presentacion_institucional', 'catalogo_institucional', 'niveles_institucionales', 'calendario_institucional']
        from contextlib import ExitStack
        with ExitStack() as stack:
            imports = [stack.enter_context(patch('apps.core.presentation.' + modulo + '.import_string')) for modulo in modulos]
            middleware = PresentacionInstitucionalMiddleware(lambda request: HttpResponse('ok'))
            self.assertEqual(middleware(RequestFactory().get('/fragmento/')).status_code, 200)
            for importar in imports:
                importar.assert_not_called()

    def test_catalogo_se_resuelve_una_vez_por_peticion_y_no_se_comparte_entre_usuarios(self):
        from apps.core.presentation.catalogos import catalogo_actual
        from apps.core.presentation.catalogo_institucional import catalogo_en_contexto
        contador = Mock(side_effect=lambda base, **kwargs: base)
        def responder(request):
            self.assertTrue(catalogo_actual().facultades)
            self.assertTrue(catalogo_actual().facultades)
            return HttpResponse('ok')
        with patch('apps.core.presentation.catalogo_institucional.import_string', return_value=contador):
            middleware = PresentacionInstitucionalMiddleware(responder)
            middleware(RequestFactory().get('/a/'))
            middleware(RequestFactory().get('/b/'))
        self.assertEqual(contador.call_count, 2)
        self.assertIsNone(catalogo_en_contexto())

    def test_avisos_no_consultan_la_base_si_la_plantilla_no_usa_cabecera(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True))
        contexto = reservation_notifications(request)
        self.assertIn('reservation_notifications', contexto)
        self.assertIn('reservation_notifications_unread', contexto)

    def test_backend_estatico_vigente_para_django_52(self):
        # El ejecutor de pruebas sustituye el almacén; se comprueba el declarado.
        from config import settings as declarados
        self.assertEqual(declarados.STORAGES['staticfiles']['BACKEND'], 'apps.core.estaticos.AlmacenEstaticos')
        self.assertIn('apps.core.middleware.estaticos.EstaticosNegociadosMiddleware', settings.MIDDLEWARE)
        self.assertNotIn('whitenoise.middleware.WhiteNoiseMiddleware', settings.MIDDLEWARE)

    def test_cabecera_no_importa_controladores_del_aula(self):
        import ast
        from pathlib import Path
        tree = ast.parse(Path('apps/core/middleware/security.py').read_text(encoding='utf-8'))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertNotIn('apps.formacion.presentation.clases_en_vivo', imports)
