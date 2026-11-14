"""Contrato del mini-lenguaje del aula y fronteras de seguridad del HTML."""

from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from apps.formacion.presentation.wiki_curso import es_wiki, html_wiki, parsear_wiki, url_segura
from apps.formacion.templatetags.curso_wiki import video_bienvenida_wiki


class Etiquetas(HTMLParser):
    def __init__(self, contenido):
        super().__init__()
        self.elementos = []
        self.feed(contenido)

    def handle_starttag(self, tag, attrs):
        self.elementos.append((tag, dict(attrs)))


class CursoWikiTests(SimpleTestCase):
    def test_contrato_y_anclas_estables_con_titulos_repetidos(self):
        entrada = '[AULA_WIKI]\n## Tu ruta\nTexto.\n### Detalle\nMás texto.\n## Tu ruta\nCierre.'
        bloques = parsear_wiki(entrada)
        self.assertEqual([b['tipo'] for b in bloques],
                         ['titulo', 'parrafo', 'titulo', 'parrafo', 'titulo', 'parrafo'])
        titulos = [b for b in bloques if b['tipo'] == 'titulo']
        self.assertEqual([b['id'] for b in titulos], ['wiki-tu-ruta-1', 'wiki-detalle-1', 'wiki-tu-ruta-2'])
        html = html_wiki(entrada)
        self.assertIn('aria-label="Índice de esta lección"', html)
        self.assertIn('href="#wiki-tu-ruta-2"', html)
        self.assertIn('id="wiki-tu-ruta-2"', html)

    def test_solo_se_activa_con_prefijo_en_su_primera_linea(self):
        for entrada in ('## Título', '\n[AULA_WIKI]\n## Título', '[AULA_WIKI] texto', 'Texto [AULA_WIKI]'):
            with self.subTest(entrada=entrada):
                self.assertFalse(es_wiki(entrada))
                self.assertEqual(parsear_wiki(entrada), [])
        self.assertTrue(es_wiki('[AULA_WIKI]\r\n## Título'))

    def test_tabla_normaliza_columnas_y_admite_barras_escapadas(self):
        entrada = '[AULA_WIKI]\n| Dato | Regla |\n| --- | --- |\n| Código | Único |\n| A\\|B | | Extra |'
        bloque = parsear_wiki(entrada)[0]
        self.assertEqual(bloque['tipo'], 'tabla')
        self.assertEqual(bloque['cabeceras'], ['Dato', 'Regla', 'Columna 3'])
        self.assertEqual(bloque['filas'], [['Código', 'Único', ''], ['A|B', '', 'Extra']])
        html = html_wiki(entrada)
        self.assertIn('<th scope="col">Dato</th>', html)
        self.assertIn('tabindex="0"', html)
        self.assertIn('role="region"', html)

    def test_listas_codigo_literal_y_avisos_semanticos(self):
        entrada = ('[AULA_WIKI]\n- Observar\n- Comprobar\n\n3. Registrar\n4. Revisar\n\n'
                   '```python\nprint("<producto>")\n## No es un título\n```\n\n'
                   '> [!TIP]\n> Guarda una versión.\n> Prueba **antes** de seguir.\n\n'
                   '> [!NOTE] Usa datos ficticios.\n\n> [!WARNING] No compartas claves.')
        bloques = parsear_wiki(entrada)
        self.assertEqual([b['tipo'] for b in bloques], ['lista', 'lista', 'codigo', 'aviso', 'aviso', 'aviso'])
        self.assertEqual(bloques[1]['inicio'], 3)
        self.assertEqual(bloques[2]['texto'], 'print("<producto>")\n## No es un título')
        self.assertEqual([b['clase'] for b in bloques[3:]], ['tip', 'note', 'warning'])
        html = html_wiki(entrada)
        self.assertIn('<ol start="3">', html)
        self.assertIn('&lt;producto&gt;', html)
        self.assertIn('curso-wiki__aviso--warning', html)
        self.assertNotIn('id="wiki-no-es-un-titulo', html)

    def test_enfasis_codigo_y_enlaces_se_interpretan_sin_html_usuario(self):
        entrada = ('[AULA_WIKI]\n**Dato importante** y `cantidad < 0`. '
                   '[Documento](https://docs.djangoproject.com/es/5.2/) '
                   '[Sección](#wiki-dato-1) [Ruta](/laboratorio/logistica/)')
        html = html_wiki(entrada)
        self.assertIn('<strong>Dato importante</strong>', html)
        self.assertIn('<code>cantidad &lt; 0</code>', html)
        enlaces = [attrs for tag, attrs in Etiquetas(html).elementos if tag == 'a']
        self.assertEqual([a['href'] for a in enlaces],
                         ['https://docs.djangoproject.com/es/5.2/', '#wiki-dato-1', '/laboratorio/logistica/'])
        self.assertEqual(enlaces[0]['rel'], 'noopener noreferrer')
        self.assertEqual(enlaces[0]['target'], '_blank')

    def test_scripts_y_eventos_se_muestran_como_texto_en_todos_los_bloques(self):
        carga = '<script>alert(1)</script><img src=x onerror=alert(2)>'
        entrada = ('[AULA_WIKI]\n## ' + carga + '\n\n' + carga + '\n\n- ' + carga
                   + '\n\n| Campo |\n| --- |\n| ' + carga + ' |\n\n> [!WARNING] ' + carga)
        html = html_wiki(entrada)
        elementos = Etiquetas(html).elementos
        self.assertFalse(any(tag in {'script', 'img', 'iframe', 'style'} for tag, _ in elementos))
        self.assertFalse(any(key.startswith('on') for _, attrs in elementos for key in attrs))
        self.assertIn('&lt;script&gt;', html)

    def test_url_rechaza_esquemas_peligrosos_controles_y_rutas_ambiguas(self):
        peligrosas = [
            'javascript:alert(1)', 'data:text/html,alert', 'vbscript:alert(1)',
            '//servidor.example/a', '/\\servidor.example/a', '/%5c%5cservidor.example/a',
            '/%2e%2e/privado', '/%252e%252e/privado', '/a/../privado',
            'https://usuario:clave@example.com/', 'https://example.com/\nscript',
            'https://example.com/%0d%0aCabecera', 'https://example.com:puerto/',
        ]
        for url in peligrosas:
            with self.subTest(url=url):
                self.assertEqual(url_segura(url), '')
        entrada = '[AULA_WIKI]\n' + ' '.join(f'[Enlace]({url})' for url in peligrosas)
        enlaces = [attrs for tag, attrs in Etiquetas(html_wiki(entrada)).elementos if tag == 'a']
        self.assertEqual(enlaces, [])

    def test_solo_imagen_local_permitida_y_enlaces_para_ampliar(self):
        fuente = '/static/portal/img/cursos/logistica-ia/ruta_aprendizaje.svg'
        entrada = '[AULA_WIKI]\n![Pantalla, reglas y datos](' + fuente + ')'
        bloque = parsear_wiki(entrada)[0]
        self.assertEqual(bloque, {'tipo': 'imagen', 'alt': 'Pantalla, reglas y datos', 'src': fuente})
        html = html_wiki(entrada)
        imagenes = [a for tag, a in Etiquetas(html).elementos if tag == 'img']
        enlaces = [a for tag, a in Etiquetas(html).elementos if tag == 'a']
        self.assertEqual(len(imagenes), 1)
        self.assertEqual(imagenes[0]['src'], fuente)
        self.assertEqual(imagenes[0]['alt'], 'Pantalla, reglas y datos')
        self.assertTrue(all(a['href'] == fuente and a['target'] == '_blank' for a in enlaces))
        self.assertIn('Abrir diagrama', html)
        for fuente_invalida in ('https://example.com/x.svg', '/media/x.svg',
                                '/static/portal/img/cursos/logistica-ia/../x.svg',
                                'data:image/svg+xml,svg'):
            with self.subTest(fuente=fuente_invalida):
                html = html_wiki(f'[AULA_WIKI]\n![Figura]({fuente_invalida})')
                self.assertFalse(any(tag == 'img' for tag, _ in Etiquetas(html).elementos))

    def render_aula(self, contenido, video_propio=False, curso_nombre='Curso de prueba'):
        actual = SimpleNamespace(pk=7, tipo='texto', contenido=contenido, titulo='Lección de prueba',
                                 icono='fas fa-book', publicada=True, obligatoria=True, duracion_min=10,
                                 en_vivo=False, calificada=False, get_tipo_display=lambda: 'Lectura')
        if video_propio:
            actual.tipo = 'video'
            actual.archivo = 'bienvenida.mp4'
            actual.video_id = ''
            actual.titulo = 'Bienvenida: tu ruta para crear una aplicación logística'
        curso = SimpleNamespace(nombre=curso_nombre, codigo='LOG-WIKI',
                                get_clasificacion_display=lambda: 'Curso corto')
        return render_to_string('portal/pages/unidades/aula/curso_aula.html', {
            'actual': actual, 'curso': curso, 'unidad': SimpleNamespace(slug='logistica', nombre='Laboratorio'),
            'curso_url': '/curso/', 'modulos': [], 'completada': True,
            'request': RequestFactory().get('/aula/'),
        })

    def test_plantilla_conserva_el_formato_original_sin_optin(self):
        html = self.render_aula('Texto **literal**\n\nhttps://example.com/referencia\n<script>alert(1)</script>')
        self.assertIn('Texto **literal**', html)
        self.assertIn('href="https://example.com/referencia"', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<article class="curso-wiki">', html)
        self.assertNotIn('<strong>literal</strong>', html)

    def test_plantilla_activa_wiki_solo_en_contenido_marcado(self):
        html = self.render_aula('[AULA_WIKI]\n## Tu ruta\n\nTexto **claro**.')
        self.assertIn('<article class="curso-wiki">', html)
        self.assertIn('<strong>claro</strong>', html)
        self.assertNotIn('[AULA_WIKI]', html)
        self.assertIn('curso_wiki.css', html)

    def test_bienvenida_propia_tiene_poster_y_subtitulos_sin_afectar_otros_cursos(self):
        nombre = 'Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial'
        html = self.render_aula('Transcripción disponible.', video_propio=True, curso_nombre=nombre)
        elementos = Etiquetas(html).elementos
        videos = [attrs for tag, attrs in elementos if tag == 'video']
        tracks = [attrs for tag, attrs in elementos if tag == 'track']
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]['poster'], '/static/portal/img/cursos/logistica-ia/bienvenida-poster.png')
        self.assertTrue(videos[0]['src'].endswith('/7/material/'))
        self.assertEqual(tracks, [{'kind': 'captions', 'src': '/static/portal/img/cursos/logistica-ia/bienvenida-es.vtt',
                                  'srclang': 'es', 'label': 'Español'}])
        otro = self.render_aula('Otro curso.', video_propio=True)
        self.assertNotIn('bienvenida-poster.png', otro)
        self.assertNotIn('bienvenida-es.vtt', otro)
        self.assertFalse(video_bienvenida_wiki(
            SimpleNamespace(titulo='Otra lección', tipo='video', archivo='a.mp4'), SimpleNamespace(nombre=nombre)))
