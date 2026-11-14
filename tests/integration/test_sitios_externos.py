from email.message import Message
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse

from apps.recursos.presentation import sitios_externos
from apps.recursos.models.recursos import Recurso
from tests.integration.test_editor_recursos_unidad import EditorRecursosUnidadTests

ORIGEN = 'https://citt.upec.edu.ec'


def cabeceras(**valores):
    mensaje = Message()
    for nombre, valor in valores.items():
        mensaje[nombre.replace('_', '-')] = valor
    return mensaje


class Respuesta:
    def __init__(self, url, **valores):
        self.url, self.headers = url, cabeceras(**valores)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def publica(*args, **kwargs):
    return [(None, None, None, None, ('93.184.216.34', 443))]


class SitiosExternosTests(EditorRecursosUnidadTests):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)

    def test_politica_de_incrustacion_como_la_aplica_el_navegador(self):
        permite = sitios_externos.politica_permite
        self.assertTrue(permite(cabeceras(), ORIGEN))
        self.assertFalse(permite(cabeceras(X_Frame_Options='SAMEORIGIN'), ORIGEN))
        # Caso real de fablabcolmayor.com: solo admite los dominios de su proveedor.
        self.assertFalse(permite(cabeceras(Content_Security_Policy='frame-ancestors *.hostinger.com *.hostinger.io'), ORIGEN))
        self.assertTrue(permite(cabeceras(Content_Security_Policy="default-src 'self'; frame-ancestors *"), ORIGEN))
        self.assertTrue(permite(cabeceras(Content_Security_Policy='frame-ancestors *.upec.edu.ec'), ORIGEN))
        self.assertTrue(permite(cabeceras(Content_Security_Policy='frame-ancestors https://citt.upec.edu.ec'), ORIGEN))
        self.assertFalse(permite(cabeceras(Content_Security_Policy='frame-ancestors http://citt.upec.edu.ec'), ORIGEN))
        self.assertFalse(permite(cabeceras(Content_Security_Policy="frame-ancestors 'self'"), ORIGEN))
        # frame-ancestors prevalece sobre X-Frame-Options.
        self.assertTrue(permite(cabeceras(X_Frame_Options='DENY', Content_Security_Policy='frame-ancestors *'), ORIGEN))

    def test_no_consulta_la_red_interna_ni_mezcla_http_en_https(self):
        with patch.object(sitios_externos, 'urlopen') as abrir:
            with patch('socket.getaddrinfo', return_value=[(None, None, None, None, ('127.0.0.1', 80))]):
                self.assertFalse(sitios_externos.permite_incrustar('https://interno.local/', ORIGEN))
            with patch('socket.getaddrinfo', publica):
                self.assertFalse(sitios_externos.permite_incrustar('http://ejemplo.org/', ORIGEN))
            abrir.assert_not_called()

    def test_consulta_una_vez_y_guarda_el_resultado(self):
        with patch('socket.getaddrinfo', publica), patch.object(
                sitios_externos, 'urlopen', return_value=Respuesta('https://ejemplo.org/')) as abrir:
            self.assertTrue(sitios_externos.permite_incrustar('https://ejemplo.org/', ORIGEN))
            self.assertTrue(sitios_externos.permite_incrustar('https://ejemplo.org/', ORIGEN))
        abrir.assert_called_once()
        with patch('socket.getaddrinfo', publica), patch.object(sitios_externos, 'urlopen', side_effect=OSError):
            self.assertFalse(sitios_externos.permite_incrustar('https://caido.org/', ORIGEN))

    def test_visor_muestra_el_sitio_o_un_acceso_directo(self):
        recurso = Recurso.objects.create(unidad=self.unidad, carpeta=self.carpeta, nombre='Virtual reality',
                                         descripcion='Recorrido virtual', url='https://fablabcolmayor.com/',
                                         seguridad_verificada=True)
        self.assertEqual(recurso.nombre_visualizador, 'sitio-externo.html')
        enlace = reverse('recurso_unidad', args=[recurso.pk])
        # El enlace para compartir sigue llevando directo al sitio.
        self.assertRedirects(self.client.get(enlace), 'https://fablabcolmayor.com/', fetch_redirect_response=False)
        with patch.object(sitios_externos, 'permite_incrustar', return_value=False):
            bloqueado = self.client.get(enlace + '?visor=1')
        self.assertContains(bloqueado, 'fablabcolmayor.com</span> no permite mostrarse')
        self.assertContains(bloqueado, 'href="https://fablabcolmayor.com/" target="_blank" rel="noopener noreferrer"')
        self.assertNotContains(bloqueado, '<iframe')
        with patch.object(sitios_externos, 'permite_incrustar', return_value=True):
            incrustado = self.client.get(enlace + '?visor=1')
        self.assertContains(incrustado, '<iframe src="https://fablabcolmayor.com/"')
        ficha = self.client.get(self.unidad.get_absolute_url())
        # Los argumentos son datos HTML escapados, sin JavaScript inline.
        self.assertContains(ficha, f'data-ui-arg0="{enlace}?visor=1" data-ui-arg1="sitio-externo.html"')
