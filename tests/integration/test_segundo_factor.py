"""Entrada al administrador: segundo factor, bloqueo, códigos de respaldo y redes autorizadas."""
import time
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.core.acceso import segundo_factor, totp
from apps.core.checks_despliegue import hardened_production_configuration
from apps.core.models.segundo_factor import SegundoFactor
from config.opcionales import decision, redes_permitidas
from tests.integration.utiles import identificar

# Secreto de los vectores del RFC 6238: «12345678901234567890» en base32.
SECRETO_RFC = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'


class CodigosTemporalesTests(SimpleTestCase):
    def test_vectores_del_rfc_6238(self):
        for instante, esperado in ((59, '287082'), (1111111109, '081804'), (1111111111, '050471'),
                                   (1234567890, '005924'), (2000000000, '279037')):
            self.assertEqual(totp.codigo(SECRETO_RFC, totp.paso_de(instante)), esperado, instante)

    def test_ventana_de_tolerancia_y_codigo_no_reutilizable(self):
        instante = 1111111109
        paso = totp.paso_de(instante)
        actual = totp.codigo(SECRETO_RFC, paso)
        self.assertEqual(totp.paso_valido(SECRETO_RFC, actual, instante), paso)
        self.assertEqual(totp.paso_valido(SECRETO_RFC, f' {actual[:3]} {actual[3:]} ', instante), paso)
        self.assertEqual(totp.paso_valido(SECRETO_RFC, actual, instante + 30), paso)
        self.assertEqual(totp.paso_valido(SECRETO_RFC, actual, instante - 30), paso)
        self.assertIsNone(totp.paso_valido(SECRETO_RFC, actual, instante + 90))
        self.assertIsNone(totp.paso_valido(SECRETO_RFC, actual, instante, ultimo_paso=paso))
        for invalido in ('', None, '12345', '1234567', 'abcdef', '１２３４５６'):
            self.assertIsNone(totp.paso_valido(SECRETO_RFC, invalido, instante), invalido)

    def test_direccion_de_alta_y_secretos_distintos(self):
        direccion = totp.direccion_de_alta(SECRETO_RFC, 'persona@upec.edu.ec', 'SLCID')
        self.assertTrue(direccion.startswith('otpauth://totp/SLCID%3Apersona%40upec.edu.ec?'))
        self.assertIn('secret=' + SECRETO_RFC, direccion)
        self.assertIn('issuer=SLCID', direccion)
        self.assertNotEqual(totp.nuevo_secreto(), totp.nuevo_secreto())
        self.assertEqual(len(totp.nuevo_secreto()), 32)


class DecisionesDelEntornoTests(SimpleTestCase):
    def test_decision_distingue_no_declarada_y_rechaza_valores_ambiguos(self):
        self.assertIsNone(decision('X', {}))
        self.assertIsNone(decision('X', {'X': '  '}))
        self.assertTrue(decision('X', {'X': ' Sí '}))
        self.assertFalse(decision('X', {'X': 'false'}))
        self.assertTrue(decision('NUEVA', {'ANTERIOR': 'true'}, heredada='ANTERIOR'))
        self.assertFalse(decision('NUEVA', {'NUEVA': 'false', 'ANTERIOR': 'true'}, heredada='ANTERIOR'))
        with self.assertRaises(ValueError):
            decision('X', {'X': 'quizá'})

    def test_redes_permitidas(self):
        self.assertEqual(redes_permitidas(''), ())
        redes = redes_permitidas('10.20.0.0/16, 192.168.5.7 ; 2001:db8::/32')
        self.assertEqual([str(red) for red in redes], ['10.20.0.0/16', '192.168.5.7/32', '2001:db8::/32'])
        with self.assertRaises(ValueError):
            redes_permitidas('10.0.0.0/33')

    def test_produccion_exige_declarar_las_decisiones_de_publicacion(self):
        base = {'REQUIRE_STRONG_DEPLOYMENT': True}
        with override_settings(**base, DECISIONES_DE_PUBLICACION={'SLCID_A': None, 'SLCID_B': False}):
            errores = [error for error in hardened_production_configuration(None) if error.id == 'slcid.E014']
            self.assertEqual(len(errores), 1)
            self.assertIn('SLCID_A', errores[0].msg)
            self.assertNotIn('SLCID_B', errores[0].msg)
        with override_settings(**base, DECISIONES_DE_PUBLICACION={'SLCID_A': True, 'SLCID_B': False}):
            self.assertNotIn('slcid.E014', [error.id for error in hardened_production_configuration(None)])


@override_settings(ADMIN_SEGUNDO_FACTOR=True, ADMIN_REDES_PERMITIDAS=())
class SegundoFactorAdministradorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.administrador = Usuario.objects.create_superuser('admin-general', 'admin-general@upec.edu.ec', 'clave-segura-2026')
        cls.persona = Usuario.objects.create_user('persona-sin-admin', password='clave-segura-2026')
        for usuario in (cls.administrador, cls.persona):
            identificar(usuario, tipo_usuario='administrativo', carrera='')
        cls.inicio = reverse('admin:index')
        cls.url = reverse('segundo_factor')

    def codigo_actual(self, desplazamiento=0):
        secreto = segundo_factor._secreto(SegundoFactor.objects.get(usuario=self.administrador))
        return totp.codigo(secreto, totp.paso_de(time.time()) + desplazamiento)

    def activar(self):
        self.client.force_login(self.administrador)
        self.client.get(self.url)
        respuesta = self.client.post(self.url, {'codigo': self.codigo_actual(), 'next': self.inicio})
        return respuesta.context['codigos_respaldo']

    def test_alta_en_el_primer_ingreso_y_entrada_al_administrador(self):
        self.client.force_login(self.administrador)
        entrada = self.client.get(self.inicio)
        self.assertRedirects(entrada, f'{self.url}?next=%2Fadmin%2F', fetch_redirect_response=False)
        self.assertEqual(self.client.post(self.inicio, {}).status_code, 403)

        pantalla = self.client.get(entrada['Location'])
        self.assertContains(pantalla, 'Activa tu segundo factor')
        self.assertContains(pantalla, 'data:image/svg+xml;base64,')
        factor = SegundoFactor.objects.get(usuario=self.administrador)
        secreto = segundo_factor._secreto(factor)
        self.assertNotIn(secreto, factor.secreto_cifrado)
        self.assertContains(pantalla, ' '.join(secreto[i:i + 4] for i in range(0, 32, 4)))
        # Recargar no cambia el secreto ya escaneado.
        self.client.get(self.url)
        self.assertEqual(segundo_factor._secreto(SegundoFactor.objects.get(usuario=self.administrador)), secreto)

        self.assertEqual(self.client.post(self.url, {'codigo': '000000', 'next': self.inicio}).status_code, 400)
        self.assertFalse(segundo_factor.tiene_alta(self.administrador))
        sesion_anterior = self.client.session.session_key
        activada = self.client.post(self.url, {'codigo': self.codigo_actual(), 'next': self.inicio})
        self.assertContains(activada, 'Segundo factor activado')
        codigos = activada.context['codigos_respaldo']
        self.assertEqual(len(codigos), segundo_factor.CODIGOS_DE_RESPALDO)
        self.assertNotEqual(self.client.session.session_key, sesion_anterior)
        guardado = str(SegundoFactor.objects.get(usuario=self.administrador).codigos_respaldo)
        self.assertFalse(any(codigo in guardado for codigo in codigos))
        self.assertEqual(self.client.get(self.inicio).status_code, 200)
        self.assertRedirects(self.client.get(self.url), self.inicio, fetch_redirect_response=False)

    def test_cada_sesion_presenta_su_codigo_y_no_se_repite(self):
        codigos = self.activar()
        self.client.logout()
        self.client.force_login(self.administrador)
        self.assertEqual(self.client.get(self.inicio).status_code, 302)
        self.assertContains(self.client.get(self.url), 'Código de verificación')
        # El código con el que se hizo el alta ya se usó.
        self.assertEqual(self.client.post(self.url, {'codigo': self.codigo_actual()}).status_code, 400)
        siguiente = self.client.post(self.url, {'codigo': self.codigo_actual(1), 'next': '/admin/auth/user/'})
        self.assertRedirects(siguiente, '/admin/auth/user/', fetch_redirect_response=False)
        self.assertEqual(self.client.get(self.inicio).status_code, 200)

        self.client.logout()
        self.client.force_login(self.administrador)
        respaldo = self.client.post(self.url, {'codigo': codigos[0].upper(), 'next': 'https://otro.example/admin/'})
        self.assertRedirects(respaldo, self.inicio, fetch_redirect_response=False)
        self.client.logout()
        self.client.force_login(self.administrador)
        self.assertEqual(self.client.post(self.url, {'codigo': codigos[0]}).status_code, 400)

    def test_cinco_fallos_bloquean_aunque_despues_el_codigo_sea_correcto(self):
        self.activar()
        self.client.logout()
        self.client.force_login(self.administrador)
        for _ in range(segundo_factor.MAX_FALLOS):
            self.assertEqual(self.client.post(self.url, {'codigo': '000000'}).status_code, 400)
        bloqueada = self.client.post(self.url, {'codigo': self.codigo_actual(1)})
        self.assertEqual(bloqueada.status_code, 429)
        self.assertContains(bloqueada, 'Demasiados intentos', status_code=429)
        self.assertEqual(self.client.get(self.inicio).status_code, 302)
        SegundoFactor.objects.filter(usuario=self.administrador).update(bloqueado_hasta=None)
        self.assertEqual(self.client.post(self.url, {'codigo': self.codigo_actual(1)}).status_code, 302)

    def test_la_verificacion_caduca_y_no_vale_para_otra_cuenta(self):
        self.activar()
        self.assertEqual(self.client.get(self.inicio).status_code, 200)
        sesion = self.client.session
        sesion[segundo_factor.CLAVE_SESION] = {'usuario': self.administrador.pk, 'momento': int(time.time()) - 13 * 3600}
        sesion.save()
        self.assertEqual(self.client.get(self.inicio).status_code, 302)
        sesion = self.client.session
        sesion[segundo_factor.CLAVE_SESION] = {'usuario': self.persona.pk, 'momento': int(time.time())}
        sesion.save()
        self.assertEqual(self.client.get(self.inicio).status_code, 302)

    def test_quien_no_administra_no_recibe_alta_ni_pantalla(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertIn(reverse('login'), self.client.get(self.url)['Location'])
        self.client.force_login(self.persona)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertNotIn(self.url, self.client.get(self.inicio).get('Location', ''))
        self.assertFalse(SegundoFactor.objects.exists())

    def test_restablecer_obliga_a_una_nueva_alta(self):
        self.activar()
        salida = StringIO()
        call_command('restablecer_segundo_factor', 'admin-general@upec.edu.ec', stdout=salida)
        self.assertIn('restablecido', salida.getvalue())
        self.assertFalse(SegundoFactor.objects.exists())
        # Sin alta registrada o sin una cuenta única no hay nada que restablecer.
        for referencia in ('admin-general', 'no-existe'):
            with self.assertRaises(CommandError):
                call_command('restablecer_segundo_factor', referencia, stdout=StringIO())
        self.assertContains(self.client.get(self.url), 'Activa tu segundo factor')

    def test_cambiar_la_clave_del_sistema_sin_conservarla_invalida_el_alta_sin_error(self):
        self.activar()
        with override_settings(SECRET_KEY='otra-clave-del-sistema-para-la-prueba-0123456789'):
            self.assertFalse(segundo_factor.verificar(self.administrador, '123456'))
        with override_settings(SECRET_KEY='otra-clave-del-sistema-para-la-prueba-0123456789',
                               SECRET_KEY_FALLBACKS=[__import__('django.conf').conf.settings.SECRET_KEY]):
            self.assertTrue(segundo_factor.verificar(self.administrador, self.codigo_actual(1)))

    @override_settings(ADMIN_SEGUNDO_FACTOR=False)
    def test_sin_la_exigencia_el_administrador_entra_como_antes(self):
        self.client.force_login(self.administrador)
        self.assertEqual(self.client.get(self.inicio).status_code, 200)
        self.assertFalse(SegundoFactor.objects.exists())


class RedesDelAdministradorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrador = get_user_model().objects.create_superuser('admin-red', 'admin-red@upec.edu.ec', 'clave-segura-2026')
        identificar(cls.administrador, tipo_usuario='administrativo', carrera='')

    @override_settings(ADMIN_SEGUNDO_FACTOR=False, ADMIN_REDES_PERMITIDAS=redes_permitidas('10.20.0.0/16'))
    def test_fuera_de_la_red_el_administrador_no_existe(self):
        self.client.force_login(self.administrador)
        for ruta in (reverse('admin:index'), reverse('admin:login'), '/grappelli/lookup/related/', reverse('segundo_factor')):
            self.assertEqual(self.client.get(ruta).status_code, 404, ruta)
            self.assertEqual(self.client.get(ruta, REMOTE_ADDR='203.0.113.9').status_code, 404, ruta)
        self.assertEqual(self.client.get(reverse('admin:index'), REMOTE_ADDR='10.20.3.4').status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:index'), REMOTE_ADDR='::ffff:10.20.3.4').status_code, 200)
        # El resto del portal no se restringe.
        anonimo = Client()
        self.assertEqual(anonimo.get(reverse('login')).status_code, 200)
        self.assertEqual(anonimo.get('/').status_code, 200)
