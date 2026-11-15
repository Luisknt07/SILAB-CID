import importlib
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.recursos.entrega.media import media_no_xframe
from apps.core.checks_despliegue import hardened_production_configuration, transactional_email_configuration
from apps.core.middleware.security import SecurityHeadersMiddleware
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios


@override_settings(ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver'])
class DesarrolloCsrfTests(TestCase):
    def test_login_por_puerto_8000_admite_el_origen_local(self):
        self.assertIn('http://localhost:8000', settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn('http://127.0.0.1:8000', settings.CSRF_TRUSTED_ORIGINS)
        self.assertEqual(settings.CSRF_COOKIE_NAME, 'citt_csrftoken')
        client = Client(enforce_csrf_checks=True)
        login_url = reverse('login')
        pagina = client.get(login_url, HTTP_HOST='localhost:8000')
        token = pagina.cookies[settings.CSRF_COOKIE_NAME].value

        respuesta = client.post(
            login_url,
            {
                'username': 'usuario-inexistente',
                'password': 'clave-inexistente',
                'csrfmiddlewaretoken': token,
            },
            HTTP_HOST='localhost:8000',
            HTTP_ORIGIN='http://localhost:8000',
            HTTP_X_FORWARDED_PROTO='https',
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'La verificación CSRF ha fallado')


    def test_login_renueva_un_token_anterior_sin_mostrar_el_403(self):
        client = Client(enforce_csrf_checks=True)
        login_url = reverse('login')
        pagina = client.get(login_url, HTTP_HOST='localhost:8000')
        token_anterior = pagina.cookies[settings.CSRF_COOKIE_NAME].value
        client.cookies[settings.CSRF_COOKIE_NAME] = 'x' * 32

        respuesta = client.post(
            login_url,
            {
                'username': 'usuario-inexistente',
                'password': 'clave-inexistente',
                'csrfmiddlewaretoken': token_anterior,
            },
            HTTP_HOST='localhost:8000',
            HTTP_ORIGIN='http://localhost:8000',
            HTTP_X_FORWARDED_PROTO='https',
        )

        self.assertRedirects(
            respuesta,
            f'{login_url}?seguridad=renovada',
            fetch_redirect_response=False,
        )
        self.assertIn(settings.CSRF_COOKIE_NAME, respuesta.cookies)
        self.assertNotEqual(
            respuesta.cookies[settings.CSRF_COOKIE_NAME].value,
            'x' * 32,
        )
        pagina_renovada = client.get(
            respuesta['Location'],
            HTTP_HOST='localhost:8000',
        )
        self.assertContains(pagina_renovada, 'Renovamos la sesión de seguridad')
        self.assertIn('no-store', pagina_renovada['Cache-Control'])


class SecurityHeadersTests(SimpleTestCase):
    @override_settings(CONTENT_SECURITY_POLICY="default-src 'self'")
    def test_middleware_publica_csp_y_permisos(self):
        middleware = SecurityHeadersMiddleware(lambda request: HttpResponse("ok"))

        # Sin servicio de clases en vivo conectado no se abre nada más.
        with mock.patch("apps.formacion.presentation.servidor_clases_config.origen_del_servidor", return_value=""):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response["Content-Security-Policy"], "default-src 'self'")
        # Solo el propio sitio puede pedir la cámara (lector de etiquetas); el micrófono sigue cerrado.
        self.assertIn("camera=(self)", response["Permissions-Policy"])
        self.assertIn("microphone=()", response["Permissions-Policy"])

    def test_media_no_registrada_no_es_publica(self):
        from django.http import Http404
        with tempfile.TemporaryDirectory() as media_root:
            Path(media_root, "recurso.html").write_text("<p>Recurso</p>", encoding="utf-8")
            with override_settings(MEDIA_ROOT=media_root), mock.patch(
                'apps.recursos.entrega.archivos_acceso.autorizar_archivo', side_effect=Http404
            ), self.assertRaises(Http404):
                media_no_xframe(RequestFactory().get('/media/recurso.html'), 'recurso.html')

    @override_settings(
        REQUIRE_TRANSACTIONAL_EMAIL=True,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
        SITE_URL="http://127.0.0.1:8000",
    )
    def test_despliegue_rechaza_correo_no_transaccional(self):
        ids = {
            error.id
            for error in transactional_email_configuration(app_configs=None)
        }

        self.assertEqual(
            ids,
            {"webcitt.E001", "webcitt.E002", "webcitt.E003", "webcitt.E004"},
        )

    @override_settings(
        REQUIRE_STRONG_DEPLOYMENT=True,
        DB_NETWORK_ISOLATED=False,
        SOCIALACCOUNT_LOGIN_ON_GET=True,
        CONTENT_SECURITY_POLICY="script-src 'self' 'unsafe-eval'",
        # Una decisión de publicación sin declarar también impide publicar.
        DECISIONES_DE_PUBLICACION={"SLCID_EXIGIR_EQUIPOS_VERIFICADOS": None, "SLCID_MEDICION_METAS_HABILITADA": True},
    )
    def test_despliegue_rechaza_base_y_csp_inseguros(self):
        database = {
            "default": {"HOST": "", "PASSWORD": "postgres", "OPTIONS": {}}
        }
        with mock.patch.object(settings, "DATABASES", database):
            ids = {
                error.id
                for error in hardened_production_configuration(app_configs=None)
            }

        self.assertEqual(
            ids,
            {
                "webcitt.E005",
                "webcitt.E006",
                "webcitt.E007",
                "webcitt.E009",
                "webcitt.E010",
                "slcid.E014",
            },
        )

    @override_settings(
        REQUIRE_STRONG_DEPLOYMENT=True,
        DB_NETWORK_ISOLATED=False,
        SOCIALACCOUNT_LOGIN_ON_GET=False,
        CONTENT_SECURITY_POLICY="script-src 'self'",
        DECISIONES_DE_PUBLICACION={"SLCID_EXIGIR_EQUIPOS_VERIFICADOS": False, "SLCID_MEDICION_METAS_HABILITADA": True},
    )
    def test_despliegue_admite_base_con_tls_verificado(self):
        database = {
            "default": {
                "HOST": "db.internal",
                "PASSWORD": "una-clave-aleatoria-de-mas-de-veinte",
                "OPTIONS": {
                    "sslmode": "verify-full",
                    "sslrootcert": "/run/secrets/postgres-ca.crt",
                },
            }
        }
        with mock.patch.object(settings, "DATABASES", database):
            self.assertEqual(
                hardened_production_configuration(app_configs=None),
                [],
            )


class ProduccionCuentasTests(SimpleTestCase):
    """Producción confirma el correo antes de dejar usar una cuenta nueva."""

    def _ajustes_de_produccion(self):
        entorno = {
            "SECRET_KEY": "x" * 60,
            "ALLOWED_HOSTS": "plataforma.upec.edu.ec",
            "CSRF_TRUSTED_ORIGINS": "https://plataforma.upec.edu.ec",
            "SITE_URL": "https://plataforma.upec.edu.ec",
        }
        with mock.patch.dict(os.environ, entorno):
            import config.settings_production as produccion
            return importlib.reload(produccion)

    def test_el_trabajador_del_visor_pdf_solo_usa_el_origen_de_las_bibliotecas(self):
        """El visor PDF sirve biblioteca y trabajador locales; el worker no
        necesita orígenes externos."""
        politica = self._ajustes_de_produccion().CONTENT_SECURITY_POLICY
        self.assertIn("worker-src 'self' blob:", politica)
        self.assertIn("script-src 'self' 'nonce-{nonce}' https://ajax.googleapis.com "
                      "https://cdnjs.cloudflare.com", politica)
        self.assertNotIn("worker-src *", politica)

    def test_csp_no_se_reabre_con_directivas_alternativas_duplicadas_o_comodines(self):
        from django.core.exceptions import ImproperlyConfigured
        base = "script-src 'self' 'nonce-{nonce}'; script-src-attr 'none'"
        for policy in (base + "; script-src-elem 'unsafe-inline'",
                       base + "; script-src 'unsafe-inline'",
                       base.replace("'self'", 'https:'),
                       base.replace("'self'", 'https://*.example.org')):
            with self.subTest(policy=policy), mock.patch.dict(os.environ, {'CONTENT_SECURITY_POLICY': policy}):
                with self.assertRaises(ImproperlyConfigured):
                    self._ajustes_de_produccion()

    def test_una_cuenta_nueva_confirma_su_correo_y_la_social_no_se_detiene(self):
        ajustes = self._ajustes_de_produccion()
        self.assertEqual(ajustes.ACCOUNT_EMAIL_VERIFICATION, "mandatory")
        self.assertEqual(ajustes.SOCIALACCOUNT_EMAIL_VERIFICATION, "none")
        self.assertTrue(ajustes.ACCOUNT_PREVENT_ENUMERATION)
        self.assertFalse(ajustes.SOCIALACCOUNT_LOGIN_ON_GET)
        self.assertNotIn("'unsafe-eval'", ajustes.CONTENT_SECURITY_POLICY)
        self.assertFalse(ajustes.DEBUG)
        self.assertFalse(ajustes.ALLOW_DEMO_DATA_COMMANDS)


class StoredHtmlSafetyTests(TestCase):
    def test_categoria_de_equipo_escapa_texto_y_limita_el_color(self):
        categoria = CategoriaEquipo.objects.create(
            nombre='<script>alert("x")</script>',
            codigo="SEG-XSS",
            icono='<img src=x onerror="alert(1)">',
            color="red;x:y",
        )
        equipo = EquiposServicios.objects.create(
            codigo="SEG-EQP",
            nombre="Equipo de prueba",
        )
        equipo.categorias.add(categoria)

        html = str(equipo.categorias_html)

        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("red;x:y", html)
        self.assertIn("#007bff", html)
        self.assertIn("&lt;script&gt;", html)
