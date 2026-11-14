"""Abuso, orígenes, XSS y verificación de correo sin tocar la base activa."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.core.middleware.entradas import ValidacionEntradaMiddleware
from apps.core.middleware.limites import LimitePeticionesMiddleware
from apps.core.middleware.origenes import OrigenesPermitidosMiddleware
from apps.core.middleware.security import SecurityHeadersMiddleware
from apps.core.presentation.template_loaders import asegurar_scripts
from apps.reservas.presentation.guia_html import DocumentoHtml, sanear


class OrigenesTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = OrigenesPermitidosMiddleware(lambda r: HttpResponse('ok'))

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_rechaza_origen_ajeno_sin_invocar_backend(self):
        with mock.patch.object(self.middleware, 'get_response') as backend:
            response = self.middleware(self.factory.post('/', HTTP_ORIGIN='https://ajeno.example'))
        self.assertEqual(response.status_code, 403)
        backend.assert_not_called()
        self.assertNotIn('Access-Control-Allow-Origin', response)

    @override_settings(CORS_ALLOWED_ORIGINS=['https://app.example'])
    def test_preflight_solo_para_origen_metodo_y_cabeceras_autorizados(self):
        response = self.middleware(self.factory.options('/', HTTP_ORIGIN='https://app.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Content-Type, X-CSRFToken'))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'https://app.example')
        self.assertIn('Origin', response['Vary'])
        response = self.middleware(self.factory.options('/', HTTP_ORIGIN='https://app.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='X-Admin'))
        self.assertEqual(response.status_code, 403)

    def test_mismo_origen_no_necesita_cors(self):
        response = self.middleware(self.factory.post('/', HTTP_ORIGIN='http://testserver'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Access-Control-Allow-Origin', response)


class EntradaYHtmlTests(SimpleTestCase):
    def test_rechaza_json_invalido_no_finito_nulo_y_profundo(self):
        middleware = ValidacionEntradaMiddleware(lambda r: HttpResponse('ok'))
        for data in ['[]', 'null', '42', '{', '{"n": NaN}', '{"n": Infinity}', '{"n": 1e999}', '{"a":"\\u0000"}', '[' * 35 + '0' + ']' * 35]:
            response = middleware(RequestFactory().post('/', data=data, content_type='application/json'))
            self.assertEqual(response.status_code, 400, data)

    def test_preserva_texto_cientifico_y_apostrofes(self):
        request = RequestFactory().post('/', {'texto': "O'Connor: pH < 7 y ΔT > 2"})
        response = ValidacionEntradaMiddleware(lambda r: HttpResponse(r.POST['texto']))(request)
        self.assertEqual(response.content.decode(), "O'Connor: pH < 7 y ΔT > 2")

    def test_html_se_sanea_incluso_si_se_guardaron_datos_fuera_del_editor(self):
        html = DocumentoHtml({'objetivos': '<p onclick="alert(1)">Bien<script>alert(2)</script><a href="javascript:x">mal</a></p>'}).html('objetivos')
        self.assertNotIn('script', html)
        self.assertNotIn('onclick', html)
        self.assertNotIn('javascript:', html)
        self.assertIn('Bien', html)
        with self.assertRaises(ValidationError):
            sanear('<div>' * 100 + 'x' + '</div>' * 100)

    def test_nonce_solo_se_agrega_al_codigo_de_plantilla_no_al_html_guardado(self):
        source = '<head><script>const texto = "<script>";</script></head>{{ contenido|safe }}'
        secured = asegurar_scripts(source)
        self.assertEqual(secured.count('nonce="{{ request.csp_nonce }}"'), 2)
        self.assertIn('const texto = "<script>"', secured)
        self.assertTrue(secured.endswith('{{ contenido|safe }}'))

    @override_settings(CONTENT_SECURITY_POLICY="script-src 'self' 'nonce-{nonce}'; script-src-attr 'none'")
    def test_nonce_cambia_por_peticion_y_no_se_cachea_html(self):
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse(r.csp_nonce))
        with mock.patch('apps.core.middleware.security.politica_de_permisos', return_value='camera=()'):
            first = middleware(RequestFactory().get('/'))
            second = middleware(RequestFactory().get('/'))
        self.assertNotEqual(first.content, second.content)
        self.assertIn(first.content.decode(), first['Content-Security-Policy'])
        self.assertNotIn('unsafe-inline', first['Content-Security-Policy'])
        self.assertEqual(first['Cache-Control'], 'private, no-store')


@override_settings(RATE_LIMIT_ENABLED=True, RATE_LIMIT_AUTH_PER_MINUTE=2, RATE_LIMIT_WRITE_PER_MINUTE=3)
class LimitesTests(TestCase):
    def test_contador_compartido_no_se_elude_con_x_forwarded_for(self):
        factory = RequestFactory()
        one = LimitePeticionesMiddleware(lambda r: HttpResponse('ok'))
        two = LimitePeticionesMiddleware(lambda r: HttpResponse('ok'))
        for index, middleware in enumerate((one, two, one)):
            request = factory.post(reverse('login'), REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR=f'192.0.2.{index + 10}')
            response = middleware(request)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        from apps.core.models.limites import ContadorPeticion
        self.assertEqual(ContadorPeticion.objects.count(), 1)
        self.assertEqual(ContadorPeticion.objects.get().total, 3)
        self.assertNotIn('192.0.2', ContadorPeticion.objects.get().clave)

    def test_limites_no_interfieren_con_lectura_publica(self):
        response = LimitePeticionesMiddleware(lambda r: HttpResponse('ok'))(RequestFactory().get('/'))
        self.assertEqual(response.status_code, 200)


@override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
class VerificacionCuentaTests(TestCase):
    def test_registro_prepara_el_perfil_pero_exige_confirmar_correo_antes_de_sesion(self):
        from allauth.account.models import EmailAddress
        from django.core import mail
        with mock.patch('apps.core.usuarios.views.confirmar_periodo') as confirmar:
            response = self.client.post(reverse('register'), {
                'username': 'registro-seguro', 'first_name': 'Persona', 'last_name': 'Prueba',
                'email': 'registro-seguro@example.org', 'password1': 'Una-clave-larga-2026',
                'password2': 'Una-clave-larga-2026', 'tipo_usuario': 'externo',
                'institucion': 'Instituto de prueba',
            })
        self.assertEqual(response.status_code, 302)
        self.assertIn('confirm-email', response['Location'])
        self.assertNotIn('_auth_user_id', self.client.session)
        user = get_user_model().objects.get(username='registro-seguro')
        confirmar.assert_called_once_with(user)
        self.assertEqual(user.profile.institucion, 'Instituto de prueba')
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_login_propio_no_omite_correo_verificado(self):
        get_user_model().objects.create_user(username='sinverificar', password='Prueba-aleatoria-2026', email='sinverificar@example.org')
        response = self.client.post(reverse('login'), {'username': 'sinverificar', 'password': 'Prueba-aleatoria-2026'})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertIn('confirm-email', response['Location'])


class EjemplosJsonTests(SimpleTestCase):
    def test_ejemplo_editable_no_cierra_script_ni_inyecta_html(self):
        import json
        import re
        from types import SimpleNamespace
        from django.template.loader import render_to_string

        texto = '</script><img src=x onerror="alert(1)"> & ciencia'
        ejemplos = {'servicio': {'ejemplo': texto}}
        html = render_to_string(
            'portal/pages/unidades/detalle/modales/reserva_equipos.html',
            {'ejemplos_solicitud_reserva': ejemplos,
             'unidad': SimpleNamespace(slug='unidad-prueba'),
             'identidad_institucion': SimpleNamespace(imagenes={}, logo='')},
        )
        self.assertNotIn('<img src=x', html)
        bloque = re.search(r'id="ejemplosSolicitudReserva"[^>]*>(.*?)</script>', html, re.S)
        self.assertIsNotNone(bloque)
        self.assertEqual(json.loads(bloque.group(1)), ejemplos)
