"""El editor de una unidad envía en un solo formulario todos sus archivos, bloques y responsables.

Un laboratorio con muchos recursos pasa de los 1000 campos que Django admite por omisión (el del FabLab envía casi
3000) y el guardado fallaba con TooManyFieldsSent antes de llegar a validar nada.
"""
from django.conf import settings
from django.test import SimpleTestCase


class FormulariosGrandesTests(SimpleTestCase):
    def test_el_editor_de_una_unidad_admite_miles_de_campos(self):
        self.assertGreaterEqual(settings.DATA_UPLOAD_MAX_NUMBER_FIELDS, 10000)
