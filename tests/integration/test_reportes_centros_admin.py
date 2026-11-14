"""Integración del hub administrativo con los reportes privados de Centros."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.centros_id.models import CentroID
from apps.core.admin.site import _enlaces_visibles


class EntradaReportesCentrosAdminTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}

    def test_entrada_admin_tambien_verifica_asignacion_canonica(self):
        Usuario = get_user_model()
        gestor = Usuario.objects.create_user('gestor-hub-reportes', is_staff=True)
        ajeno = Usuario.objects.create_user('staff-hub-reportes-ajeno', is_staff=True)
        CentroID.objects.create(nombre='Centro del hub QA', slug='centro-hub-reportes-qa',
                                proposito='Investigar', responsable=gestor)
        enlace = ({'nombre': 'Centros', 'descripcion': 'Reportes', 'ruta': 'reportes_centros_id',
                   'acceso_centros': True},)
        request = RequestFactory().get('/admin/')
        request.user = gestor
        self.assertEqual(len(_enlaces_visibles(request, enlace)), 1)
        request.user = ajeno
        self.assertEqual(_enlaces_visibles(request, enlace), [])
        Usuario.objects.filter(pk=gestor.pk).update(is_active=False)
        request.user = gestor
        self.assertEqual(_enlaces_visibles(request, enlace), [])
