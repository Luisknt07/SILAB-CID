"""La auditoría del portal no debe compilar proyectos Django descargables como propios."""
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import engines
from django.test import SimpleTestCase, override_settings

from apps.integraciones.management.commands.auditar_plantillas import directorios_activos


class AuditoriaPlantillasActivasTests(SimpleTestCase):
    def setUp(self):
        carpeta = TemporaryDirectory(prefix='slcid-plantillas-activas-')
        self.addCleanup(carpeta.cleanup)
        self.raiz = Path(carpeta.name)
        self.archivos = {
            'templates/base.html': '{% block contenido %}{% endblock %}',
            'templates/portal.html': '{% extends "base.html" %}{% block contenido %}'
                                     '{% include "demo/contenido.html" %}{% endblock %}',
            'apps/demo/templates/demo/contenido.html': '<p>Contenido del portal</p>',
            'contenidos_publicos/extra.html': '{% extends "base.html" %}',
            'webcitt/management/curso_kit/contenido/templates/inventario/base.html':
                '{% block contenido %}{% endblock %}',
            'webcitt/management/curso_kit/contenido/templates/inventario/lista.html':
                '{% extends "inventario/base.html" %}',
            'no_instalada/templates/pendiente.html': '{% etiqueta_no_registrada %}',
        }
        for nombre, contenido in self.archivos.items():
            ruta = self.raiz / nombre
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido, encoding='utf-8')
        self.configuracion = [{
            'NAME': 'portal_auditoria',
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [self.raiz / 'templates'],
            'APP_DIRS': False,
            'OPTIONS': {'loaders': [('django.template.loaders.cached.Loader', [
                ('django.template.loaders.filesystem.Loader', [
                    self.raiz / 'templates', self.raiz / 'apps/demo/templates',
                    self.raiz / 'contenidos_publicos',
                ]),
            ])]},
        }]

    def ejecutar(self, fallo=False, configuracion=None):
        salida = StringIO()
        listado = ('\0'.join(self.archivos) + '\0').encode()
        with override_settings(BASE_DIR=self.raiz, TEMPLATES=configuracion or self.configuracion):
            with patch('apps.integraciones.management.commands.auditar_plantillas.subprocess.check_output',
                       return_value=listado):
                if fallo:
                    with self.assertRaises(CommandError):
                        call_command('auditar_plantillas', stdout=salida)
                else:
                    call_command('auditar_plantillas', stdout=salida)
        return json.loads(salida.getvalue())

    def test_solo_audita_raices_activas_incluyendo_directorio_principal_y_loaders(self):
        reporte = self.ejecutar()
        self.assertEqual(reporte['plantillas'], 4)
        self.assertEqual(reporte['errores'], [])

    def test_no_oculta_referencias_invalidas_en_plantillas_activas(self):
        (self.raiz / 'templates/portal.html').write_text('{% include "falta.html" %}', encoding='utf-8')
        reporte = self.ejecutar(fallo=True)
        self.assertEqual(reporte['plantillas'], 4)
        self.assertEqual(len(reporte['errores']), 1)
        self.assertEqual(reporte['errores'][0]['archivo'], 'templates/portal.html')

    def test_no_oculta_estaticos_invalidos_del_portal(self):
        (self.raiz / 'templates/portal.html').write_text(
            '{% load static %}{% static "auditoria/archivo-que-no-existe.css" %}', encoding='utf-8')
        reporte = self.ejecutar(fallo=True)
        self.assertIn('Estático inexistente', reporte['errores'][0]['error'])

    def test_directorios_instalados_de_apps_se_descubren_por_loaders(self):
        carpeta = Path(apps.get_app_config('centros_id').path) / 'templates'
        self.assertIn(carpeta.resolve(), directorios_activos(engines['django']))

    def test_resuelve_referencias_en_el_motor_que_consumira_la_plantilla(self):
        nombre = 'otro_motor/solo_segundo.html'
        self.archivos[nombre] = '<p>Otro motor</p>'
        ruta = self.raiz / nombre
        ruta.parent.mkdir()
        ruta.write_text(self.archivos[nombre], encoding='utf-8')
        (self.raiz / 'templates/portal.html').write_text(
            '{% include "solo_segundo.html" %}', encoding='utf-8')
        segundo = {'NAME': 'otro', 'BACKEND': 'django.template.backends.django.DjangoTemplates',
                   'DIRS': [ruta.parent], 'APP_DIRS': False}
        reporte = self.ejecutar(fallo=True, configuracion=[*self.configuracion, segundo])
        self.assertEqual(reporte['plantillas'], 5)
        self.assertEqual(len(reporte['errores']), 1)
        self.assertEqual(reporte['errores'][0]['motor'], 'portal_auditoria')

    def test_dirs_configurados_sin_loader_filesystem_no_se_consideran_activos(self):
        configuracion = [{'NAME': 'memoria',
                          'BACKEND': 'django.template.backends.django.DjangoTemplates',
                          'DIRS': [self.raiz / 'templates'], 'APP_DIRS': False,
                          'OPTIONS': {'loaders': [('django.template.loaders.locmem.Loader',
                                                   {'base.html': 'Plantilla en memoria'})]}}]
        reporte = self.ejecutar(configuracion=configuracion)
        self.assertEqual(reporte['plantillas'], 0)
        self.assertEqual(reporte['errores'], [])
