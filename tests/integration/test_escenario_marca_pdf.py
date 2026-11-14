"""La copia QA conserva el documento y usa sólo dependencias del proyecto."""
from io import BytesIO

from django.test import SimpleTestCase
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link, Text
from reportlab.pdfgen.canvas import Canvas

from apps.documentos.presentation.escenario_ideal_exportacion import _marcar_copia


class EscenarioMarcaPdfTests(SimpleTestCase):
    aviso = 'PRUEBA INTEGRAL - DATOS SINTETICOS - SIN VALIDEZ INSTITUCIONAL'

    @staticmethod
    def original():
        datos = BytesIO()
        lienzo = Canvas(datos, pagesize=(595, 842), invariant=1)
        lienzo.setTitle('Respaldo de ensayo original')
        for numero in range(1, 4):
            lienzo.drawString(90, 650, f'Contenido original pagina {numero}')
            lienzo.showPage()
        lienzo.save()
        escritor = PdfWriter(clone_from=PdfReader(datos))
        for pagina in range(3):
            escritor.add_annotation(pagina, Link(rect=(90, 640, 280, 670),
                url='http://127.0.0.1:8000/unidad/999/'))
        escritor.add_annotation(0, Text(rect=(100, 500, 130, 530), text='Comentario conservado'))
        salida = BytesIO()
        escritor.write(salida)
        return salida.getvalue()

    def test_tres_paginas_conservan_contenido_y_reciben_marca_sin_enlaces(self):
        original = self.original()
        copia = PdfReader(BytesIO(_marcar_copia(original)))
        self.assertEqual(len(copia.pages), 3)
        self.assertEqual(copia.metadata.title, 'Respaldo de ensayo original')
        for numero, pagina in enumerate(copia.pages, 1):
            with self.subTest(pagina=numero):
                self.assertIn(f'Contenido original pagina {numero}', pagina.extract_text())
                self.assertIn(self.aviso, pagina.extract_text())
                self.assertFalse(any(ref.get_object().get('/Subtype') == '/Link'
                                     for ref in pagina.get('/Annots', [])))
        self.assertEqual(copia.pages[0]['/Annots'][0].get_object()['/Contents'], 'Comentario conservado')
        # La entrada sigue intacta; sólo se eliminan enlaces de la copia.
        self.assertTrue(any(ref.get_object().get('/Subtype') == '/Link'
                            for ref in PdfReader(BytesIO(original)).pages[0]['/Annots']))

    def test_admite_paginas_rotadas_y_recortadas_sin_perder_texto(self):
        escritor = PdfWriter(clone_from=PdfReader(BytesIO(self.original())))
        escritor.pages[1].rotate(90)
        escritor.pages[2].cropbox.lower_left = (40, 60)
        escritor.pages[2].cropbox.upper_right = (560, 800)
        datos = BytesIO()
        escritor.write(datos)
        copia = PdfReader(BytesIO(_marcar_copia(datos.getvalue())))
        for numero, pagina in enumerate(copia.pages, 1):
            with self.subTest(pagina=numero):
                self.assertIn(f'Contenido original pagina {numero}', pagina.extract_text())
                self.assertIn(self.aviso, pagina.extract_text())
                self.assertEqual(pagina.rotation, 0)
        self.assertEqual(tuple(copia.pages[2].cropbox), (40, 60, 560, 800))
