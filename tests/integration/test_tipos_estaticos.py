"""Los estáticos salen con su tipo aunque el registro de Windows diga otra cosa.

Con «X-Content-Type-Options: nosniff» (lo agrega el túnel de devtunnels) el
navegador no ejecuta un script servido como text/plain: la página se ve,
pero ningún botón responde.
"""
import mimetypes

from django.contrib.staticfiles.views import serve
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.apps import TIPOS_DE_ESTATICOS


class LosEstaticosLlevanSuTipoTests(SimpleTestCase):
    def test_cada_extension_tiene_su_tipo(self):
        for tipo, extension in TIPOS_DE_ESTATICOS:
            self.assertEqual(mimetypes.guess_type(f'archivo{extension}')[0], tipo)

    @override_settings(DEBUG=True)
    def test_el_servidor_de_desarrollo_entrega_los_scripts_como_javascript(self):
        for ruta in ('js/vendor/jquery-3.7.1.min.js', 'js/vendor/pdfjs/6.4.299/pdf.mjs'):
            with self.subTest(ruta=ruta):
                peticion = RequestFactory().get('/static/' + ruta)
                respuesta = serve(peticion, ruta)
                self.assertEqual(respuesta['Content-Type'], 'text/javascript')
                respuesta.close()
