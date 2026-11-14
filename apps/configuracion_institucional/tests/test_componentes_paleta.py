"""Superficies derivadas legibles incluso en los limites de contraste."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from html.parser import HTMLParser

from apps.core.paleta import componentes_paleta, contraste, PALETA_SUGERIDA


class ComponentesPaletaTests(SimpleTestCase):
    def test_accion_del_correo_usa_color_principal_solido_sin_css_variables(self):
        class Enlaces(HTMLParser):
            def __init__(self):
                super().__init__()
                self.estilos = []

            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    self.estilos.append(dict(attrs).get('style', ''))

        paleta = {**PALETA_SUGERIDA, 'primario': '#006633',
                  'degradado_primario': 'linear-gradient(135deg, #082b22, #064e3b)'}
        contenido = render_to_string('emails/reservas/_comprobante_contenido.html',
                                    {'paleta_institucional': paleta, 'modo_correo': True})
        enlaces = Enlaces()
        enlaces.feed(contenido)
        self.assertTrue(enlaces.estilos)
        for estilo in enlaces.estilos:
            self.assertIn(f'background:{paleta["primario"]};', estilo)
            self.assertNotIn('var(', estilo)
            self.assertNotIn('gradient(', estilo)

    def test_tintas_y_superficies_derivadas_conservan_contraste(self):
        for principal in ('#163a63', '#493263', '#006633', '#767676'):
            for texto in ('#18312a', '#000000', '#767676'):
                paleta = {**PALETA_SUGERIDA, 'primario': principal, 'texto': texto,
                          'acento': '#ffffff', 'fondo': '#ffffff'}
                with self.subTest(principal=principal, texto=texto):
                    derivados = componentes_paleta(paleta)
                    self.assertGreaterEqual(contraste('#ffffff', derivados['primario_hover']), 4.5)
                    for fondo in ('#ffffff', derivados['primario_suave'], derivados['acento_suave']):
                        self.assertGreaterEqual(contraste(texto, fondo), 4.5)
                        self.assertGreaterEqual(contraste(derivados['acento_tinta'], fondo), 4.5)
                        self.assertGreaterEqual(contraste(derivados['primario_tinta'], fondo), 4.5)
                    self.assertGreaterEqual(contraste(derivados['acento_sobre_oscuro'], principal), 4.5)

    def test_acciones_compartidas_sin_paleta_y_entrada_invalida_no_se_emite(self):
        self.assertEqual(componentes_paleta({}), {})
        original = render_to_string('portal/components/paleta_institucional.html', {'paleta_institucional': {}})
        self.assertNotIn('<style', original)
        self.assertIn('acciones_superficies.css', original)
        self.assertNotIn('paleta_componentes.css', original)
        personalizado = render_to_string('portal/components/paleta_institucional.html',
                                        {'paleta_institucional': PALETA_SUGERIDA})
        self.assertIn('paleta_componentes.css', personalizado)
        self.assertIn('--institucion-primario-suave:', personalizado)
        with self.assertRaises(ValueError):
            render_to_string('portal/components/paleta_institucional.html',
                             {'paleta_institucional': {**PALETA_SUGERIDA, 'primario': '</style><script>'}})

    def test_la_tinta_de_acento_no_se_usa_sobre_fondos_oscuros(self):
        """La tinta de acento es la oscura, para fondos claros.

        Sobre el color principal o el oscuro hay que usar
        `--institucion-acento-sobre-oscuro`; con la tinta el texto desaparece.
        Paso tres veces: el videotutorial del asistente y dos iconos de
        «Quiénes somos» quedaron ilegibles.
        """
        import re
        from pathlib import Path

        from django.conf import settings

        oscuros = ('--institucion-primario', '--institucion-oscuro', '--institucion-degradado',
                   '--unit-green', '--upec-color-green', '--upec-color-navy', '--rw-green')
        culpables = []
        for hoja in sorted(Path(settings.BASE_DIR, 'webcitt', 'static').rglob('*.css')):
            texto = hoja.read_text(encoding='utf-8', errors='ignore')
            for bloque in re.finditer(r'([^{}]+)\{([^{}]*)\}', texto):
                cuerpo = bloque.group(2)
                if 'acento-tinta' not in cuerpo or 'color:' not in cuerpo:
                    continue
                fondo = re.search(r'background[^;]*', cuerpo)
                if fondo and any(token in fondo.group(0) for token in oscuros):
                    linea = texto[:bloque.start()].count(chr(10)) + 1
                    culpables.append(f'{hoja.name}:{linea} {bloque.group(1).strip()[:60]}')
        self.assertEqual(culpables, [], 'Tinta de acento sobre fondo oscuro: ' + '; '.join(culpables))

