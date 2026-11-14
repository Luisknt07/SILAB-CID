"""La guía impresa conserva datos y evita interpretar HTML del contenido docente."""
from io import BytesIO

from django.test import SimpleTestCase
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate

from apps.formacion.presentation.curso_wiki_pdf import bloques_pdf, inline_pdf


class GuiaWikiPdfTests(SimpleTestCase):
    def test_escapa_html_y_descarta_destinos_inseguros(self):
        resultado = inline_pdf('<script>no</script> **Regla** [abrir](javascript:alert) '
                               + chr(96) + 'saldo < 0' + chr(96))
        self.assertNotIn('<script>', resultado)
        self.assertNotIn('href=', resultado)
        self.assertIn('&lt;script&gt;', resultado)
        self.assertIn('<b>Regla</b>', resultado)
        self.assertIn('saldo &lt; 0', resultado)

    def test_guia_conserva_tablas_pasos_y_diagrama_local(self):
        contenido = '''[AULA_WIKI]
## Comprueba una salida
| Operación | Saldo esperado |
| --- | --- |
| Entrada 10 | 10 |
| Salida 3 | 7 |

1. Consulta la existencia.
2. Compara el historial.

> [!TIP] Una salida rechazada no cambia el saldo.

![Regla de stock](/static/portal/img/cursos/logistica-ia/regla-stock.svg)

~~~text
stock = entrada - salida
~~~
'''
        estilos = getSampleStyleSheet()
        flujo = bloques_pdf(contenido, 450, estilos['BodyText'], estilos['Heading2'])
        salida = BytesIO()
        SimpleDocTemplate(salida, pageCompression=0).build(flujo)
        pdf = salida.getvalue()
        self.assertTrue(pdf.startswith(b'%PDF'))
        for fragmento in (b'Saldo esperado', b'Salida 3', b'Una salida rechazada',
                          b'stock', b'entrada', b'salida'):
            self.assertTrue(fragmento in pdf, repr(fragmento))
        self.assertNotIn(b'[AULA_WIKI]', pdf)
        self.assertIn(b'/Subtype /Image', pdf)
