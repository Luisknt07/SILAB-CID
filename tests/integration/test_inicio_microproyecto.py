from pathlib import Path
import runpy
from types import ModuleType
from unittest.mock import patch

from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.urls import path

from apps.recursos.presentation import microproyectos


class InicioMicroproyectoTests(SimpleTestCase):
    def cargar(self, rutas):
        original = ModuleType('proyecto_urls_prueba')
        original.urlpatterns = rutas
        with patch.dict('sys.modules', {original.__name__: original}), override_settings(
                CITT_ORIGINAL_URLCONF=original.__name__, CITT_PROJECT_TITLE='WMS <Prueba>'):
            entorno = runpy.run_path(str(Path(microproyectos.__file__).with_name('runtime_inicio.py')))
            respuesta = entorno['inicio'](RequestFactory().get('/'))
            return entorno['urlpatterns'], respuesta

    def test_agrega_inicio_sin_redireccionar_al_admin(self):
        rutas, respuesta = self.cargar([path('admin/', lambda request: HttpResponse('Admin'))])
        self.assertEqual(len(rutas), 2)
        self.assertEqual(str(rutas[-1].pattern), '')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'WMS &lt;Prueba&gt;')
        self.assertContains(respuesta, 'Acceso administrativo')
        self.assertNotIn('Location', respuesta.headers)

    def test_respeta_la_pagina_original(self):
        inicio = path('', lambda request: HttpResponse('Inicio original'), name='home')
        rutas, _ = self.cargar([inicio])
        self.assertEqual(rutas, [inicio])
