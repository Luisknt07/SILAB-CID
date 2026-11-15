"""Vinculación del acceso con Google o Microsoft a una cuenta local existente."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.core.acceso.social import CustomSocialAccountAdapter


class VinculacionSocialTests(TestCase):
    def setUp(self):
        self.adaptador = CustomSocialAccountAdapter()
        self.request = RequestFactory().get('/accounts/google/login/callback/')
        parche = patch('apps.core.acceso.social.messages')
        self.mensajes = parche.start()
        self.addCleanup(parche.stop)

    def acceso(self, correo, proveedor='google', **datos):
        extra = {'email': correo, 'email_verified': True, **datos} if proveedor == 'google' else {
            'userPrincipalName': correo, **datos}
        return SimpleNamespace(is_existing=False, connect=Mock(),
                               account=SimpleNamespace(provider=proveedor, extra_data=extra))

    def test_cuenta_preparada_por_un_tercero_pierde_su_contrasena_al_vincular_al_titular(self):
        cuenta = get_user_model().objects.create_user('titular', 'titular@upec.edu.ec', 'clave-de-un-tercero-2026')
        acceso = self.acceso('titular@upec.edu.ec', proveedor='microsoft')
        self.adaptador.pre_social_login(self.request, acceso)
        cuenta.refresh_from_db()
        acceso.connect.assert_called_once_with(self.request, cuenta)
        self.assertFalse(cuenta.has_usable_password())
        self.assertTrue(EmailAddress.objects.get(user=cuenta, email='titular@upec.edu.ec').verified)

    def test_correo_ya_confirmado_y_cuentas_de_personal_conservan_su_contrasena(self):
        confirmada = get_user_model().objects.create_user('confirmada', 'confirmada@gmail.com', 'clave-propia-2026')
        EmailAddress.objects.create(user=confirmada, email='confirmada@gmail.com', verified=True, primary=True)
        personal = get_user_model().objects.create_user('personal', 'personal@upec.edu.ec', 'clave-propia-2026',
                                                        is_staff=True)
        for cuenta in (confirmada, personal):
            acceso = self.acceso(cuenta.email)
            self.adaptador.pre_social_login(self.request, acceso)
            cuenta.refresh_from_db()
            acceso.connect.assert_called_once_with(self.request, cuenta)
            self.assertTrue(cuenta.check_password('clave-propia-2026'), cuenta.username)

    def test_google_sin_correo_confirmado_no_vincula_ni_crea_acceso(self):
        cuenta = get_user_model().objects.create_user('pendiente', 'pendiente@gmail.com', 'clave-propia-2026')
        acceso = self.acceso('pendiente@gmail.com', email_verified=False)
        with self.assertRaises(ImmediateHttpResponse):
            self.adaptador.pre_social_login(self.request, acceso)
        acceso.connect.assert_not_called()
        cuenta.refresh_from_db()
        self.assertTrue(cuenta.check_password('clave-propia-2026'))

    def test_dominio_no_permitido_se_rechaza_antes_de_buscar_cuentas(self):
        acceso = self.acceso('persona@otro-dominio.example', proveedor='microsoft')
        with self.assertRaises(ImmediateHttpResponse):
            self.adaptador.pre_social_login(self.request, acceso)
        acceso.connect.assert_not_called()
