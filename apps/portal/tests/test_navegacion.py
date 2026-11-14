"""La cabecera conserva el contexto institucional al navegar dentro de un centro."""
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve

from apps.portal.context_processors import institutional_navigation


class NavegacionInstitucionalTests(SimpleTestCase):
    def activa(self, ruta):
        request = RequestFactory().get(ruta)
        request.resolver_match = resolve(request.path_info)
        return institutional_navigation(request)['institutional_active_page']

    def test_centros_sigue_activo_en_catalogo_ficha_y_secciones(self):
        for ruta in (
            '/centros-id/', '/centros-id/cidt-upec/',
            '/centros-id/cidt-upec/?seccion=presentacion',
            '/centros-id/cidt-upec/?area=ia-datos',
            '/centros-id/cidt-upec/area/ia-datos/',
            '/centros-id/cidt-upec/gestion/', '/centros-id/reportes/',
        ):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.activa(ruta), 'centros')

    def test_todas_las_entradas_del_contexto_centros_mantienen_su_indicador(self):
        from apps.centros_id.presentation.urls import urlpatterns

        for ruta in urlpatterns:
            request = RequestFactory().get('/')
            request.resolver_match = SimpleNamespace(url_name=ruta.name, func=ruta.callback)
            with self.subTest(nombre=ruta.name):
                self.assertEqual(institutional_navigation(request)['institutional_active_page'], 'centros')

    def test_no_se_activa_centros_al_navegar_por_otros_modulos(self):
        for ruta, activa in (
            ('/', 'inicio'), ('/quienes-somos/', 'quienes'),
            ('/laboratorios-unidades/', 'laboratorios'),
            ('/laboratorio/logistica/', 'laboratorios'),
            ('/servicios/', 'servicios'), ('/normativa/', 'normativa'),
        ):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.activa(ruta), activa)

    def test_sin_ruta_resuelta_no_inventa_una_seccion_activa(self):
        self.assertEqual(institutional_navigation(RequestFactory().get('/desconocida/')),
                         {'institutional_active_page': ''})
