"""La portada mantiene una foto inicial y difiere las demás sin consultar datos."""
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import SimpleTestCase, override_settings

from apps.core.presentation.identidad import identidad_de_despliegue
from apps.portal.inicio.defaults import portada_base


class _GaleriaHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.profundidad = 0
        self.imagenes = []
        self.galeria = {}
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == 'div' and 'data-home-hero' in atributos:
            self.profundidad = 1
            self.galeria = atributos
        elif tag == 'div' and self.profundidad:
            self.profundidad += 1
        elif tag == 'img' and self.profundidad:
            self.imagenes.append(atributos)
        elif tag == 'script':
            self.scripts.append(atributos)

    def handle_endtag(self, tag):
        if tag == 'div' and self.profundidad:
            self.profundidad -= 1


class GaleriaInicioTests(SimpleTestCase):
    def renderizar(self, portada=None):
        producto, institucion = identidad_de_despliegue()
        html = render_to_string('portal/pages/inicio/inicio.html', {
            'portada_inicio': portada or portada_base(),
            'identidad_producto': producto,
            'identidad_institucion': institucion,
            'paleta_institucional': dict(institucion.paleta),
        })
        galeria = _GaleriaHTML()
        galeria.feed(html)
        return html, galeria

    def comprobar_carga(self, galeria):
        self.assertEqual(len(galeria.imagenes), 13)
        self.assertEqual(galeria.galeria['aria-hidden'], 'true')
        inicial, *restantes = galeria.imagenes
        self.assertEqual(inicial['src'], static('img/generated/home-hero/hero-laboratorio-conectado.png'))
        self.assertEqual(inicial['fetchpriority'], 'high')
        self.assertEqual(inicial['class'], 'is-active')
        self.assertNotIn('data-src', inicial)
        for imagen in restantes:
            self.assertNotIn('src', imagen)
            self.assertTrue(imagen['data-src'].startswith(settings.STATIC_URL))
        for imagen in galeria.imagenes:
            self.assertEqual(imagen['alt'], '')
            self.assertEqual(imagen['decoding'], 'async')
            ruta = (imagen.get('src') or imagen['data-src']).removeprefix(settings.STATIC_URL)
            self.assertIsNotNone(finders.find(ruta), ruta)
        guion = static('portal/js/pages/inicio/inicio_galeria.js')
        scripts = [s for s in galeria.scripts if s.get('src', '').startswith(guion + '?v=')]
        self.assertEqual(len(scripts), 1)
        self.assertIn('defer', scripts[0])

    def test_respaldo_solo_publica_una_foto_con_src(self):
        html, galeria = self.renderizar()
        self.comprobar_carga(galeria)
        self.assertIn(portada_base().resumen, html)

    @override_settings(STATIC_URL='/recursos-institucionales/')
    def test_textos_configurados_y_prefijo_estatico_conservan_la_carga_diferida(self):
        portada = replace(portada_base(), titulo='Inicio editorial configurado', resumen='Contenido institucional vigente.')
        html, galeria = self.renderizar(portada)
        self.comprobar_carga(galeria)
        self.assertIn(portada.titulo, html)
        self.assertIn(portada.resumen, html)

    @skipUnless(shutil.which('node'), 'Las pruebas del controlador requieren Node.js')
    def test_controlador_real_en_node(self):
        prueba = Path(__file__).with_name('js') / 'test_galeria_inicio.cjs'
        resultado = subprocess.run(['node', '--test', str(prueba)], cwd=settings.BASE_DIR,
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
