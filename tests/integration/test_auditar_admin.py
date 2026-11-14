"""El auditor comprueba el destino de enlaces administrativos conservados."""
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase

from apps.integraciones.management.commands.auditar_admin import Command


class AuditorAdminTests(SimpleTestCase):
    def setUp(self):
        self.comando = Command(stdout=StringIO())
        self.comando.usuario = SimpleNamespace(is_superuser=True)
        self.comando.fabrica = RequestFactory()
        self.comando.fallas, self.comando.abiertas, self.comando.detalle = [], 0, False

    @staticmethod
    def ruta(vista, namespace='admin', url_name='pantalla'):
        return SimpleNamespace(func=vista, args=(), kwargs={}, namespace=namespace, url_name=url_name)

    def test_sigue_el_enlace_conservado_y_comprueba_el_contenido_final(self):
        peticiones = []

        def final(request):
            peticiones.append(request.GET['tipo'])
            return HttpResponse('Contenido autorizado')

        with patch('apps.integraciones.management.commands.auditar_admin.resolve', side_effect=[
            self.ruta(lambda request: HttpResponseRedirect('/admin/final/?tipo=plantas_piloto')),
            self.ruta(final),
        ]):
            self.comando.abrir('/admin/anterior/')
        self.assertEqual(self.comando.fallas, [])
        self.assertEqual(peticiones, ['plantas_piloto'])

    def test_un_destino_roto_sigue_siendo_una_falla(self):
        with patch('apps.integraciones.management.commands.auditar_admin.resolve', side_effect=[
            self.ruta(lambda request: HttpResponseRedirect('/admin/final/')),
            self.ruta(lambda request: HttpResponse(status=500)),
        ]):
            self.comando.abrir('/admin/anterior/')
        self.assertIn('500', self.comando.fallas[0][1])

    def test_no_sigue_redirecciones_externas_ni_puertas_de_login(self):
        for destino, rutas in (
            ('https://example.invalid/admin/', []),
            ('//example.invalid/admin/', []),
            ('/admin/login/', [self.ruta(lambda request: HttpResponse(), url_name='login')]),
            ('/publico/', [self.ruta(lambda request: HttpResponse(), namespace='portal')]),
        ):
            with self.subTest(destino=destino), patch(
                'apps.integraciones.management.commands.auditar_admin.resolve', side_effect=[
                    self.ruta(lambda request: HttpResponseRedirect(destino)), *rutas,
                ],
            ):
                self.comando.fallas = []
                self.comando.abrir('/admin/anterior/')
                self.assertEqual(len(self.comando.fallas), 1)

    def test_detecta_ciclos_sin_repetir_la_solicitud(self):
        with patch('apps.integraciones.management.commands.auditar_admin.resolve', return_value=self.ruta(
            lambda request: HttpResponseRedirect('/admin/anterior/'),
        )) as resolver:
            self.comando.abrir('/admin/anterior/')
        self.assertIn('ciclo', self.comando.fallas[0][1])
        self.assertEqual(resolver.call_count, 1)
