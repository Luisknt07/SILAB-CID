from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.panel_trabajo import PanelTrabajoMiddleware


@override_settings(ALLOWED_HOSTS=['testserver'], X_FRAME_OPTIONS='DENY')
class PanelTrabajoTests(SimpleTestCase):
    def response(self, path, *, authenticated=True, staff=True, response=None):
        request = RequestFactory().get(path)
        request.user = SimpleNamespace(is_authenticated=authenticated, is_staff=staff)
        result = response if response is not None else HttpResponse('Formulario')
        chain = XFrameOptionsMiddleware(PanelTrabajoMiddleware(lambda request: result))
        return chain(request)

    def test_marco_solo_para_tareas_autenticadas_del_mismo_origen(self):
        for path in ['/gestion/unidades/lab/practicas/83/', '/admin/directorio_unidades/unidad/3/change/',
                     '/reservas/actividades/guias/8/', '/reservas/12/comprobante/',
                     '/laboratorio/lab/procesos/1/ficha/']:
            with self.subTest(path=path):
                self.assertEqual(self.response(path)['X-Frame-Options'], 'DENY')
                self.assertEqual(self.response(path + '?_panel=1')['X-Frame-Options'], 'SAMEORIGIN')
                self.assertEqual(self.response(path + '?_panel=1', authenticated=False)['X-Frame-Options'], 'DENY')

    def test_no_habilita_admin_para_personas_sin_acceso_staff(self):
        self.assertEqual(self.response('/admin/directorio_unidades/unidad/?_panel=1', staff=False)['X-Frame-Options'], 'DENY')

    def test_redireccion_de_guia_conserva_el_modal(self):
        response = self.response('/reservas/actividades/guias/8/estado/?_panel=1',
                                 response=HttpResponseRedirect('/reservas/actividades/guias/8/'))
        self.assertEqual(parse_qs(urlsplit(response['Location']).query), {'_panel': ['1']})

    def test_cliente_y_servidor_comparten_las_rutas_del_panel(self):
        import json
        from django.template.loader import render_to_string
        from apps.core.panel_trabajo import PREFIJOS_TRABAJO
        html = render_to_string('portal/components/panel_trabajo_assets.html')
        self.assertIn(json.dumps(list(PREFIJOS_TRABAJO)), html)

    def test_marcador_no_se_interpreta_como_filtro_del_admin(self):
        request = RequestFactory().get('/admin/directorio_unidades/unidad/?_panel=1&q=lab')
        request.user = SimpleNamespace(is_authenticated=True, is_staff=True)

        def view(req):
            self.assertEqual(dict(req.GET), {'q': ['lab']})
            return HttpResponse('Listado')

        self.assertEqual(PanelTrabajoMiddleware(view)(request).status_code, 200)

    def test_no_habilita_login_o_paginas_publicas(self):
        for path in ['/admin/login/', '/admin/logout/', '/noticias/']:
            self.assertEqual(self.response(path + '?_panel=1')['X-Frame-Options'], 'DENY')

    def test_redireccion_conserva_contexto_y_filtros_repetidos(self):
        response = self.response('/gestion/unidades/lab/practicas/83/?_panel=1',
                                 response=HttpResponseRedirect('/gestion/unidades/lab/?filtro=a&filtro=b#practicas'))
        parsed = urlsplit(response['Location'])
        self.assertEqual(parse_qs(parsed.query), {'filtro': ['a', 'b'], '_panel': ['1']})
        self.assertEqual(parsed.fragment, 'practicas')

    def test_no_reescribe_destinos_externos_ni_login(self):
        for target in ['https://externo.example/gestion/', '//externo.example/admin/', '/admin/login/']:
            response = self.response('/admin/?_panel=1', response=HttpResponseRedirect(target))
            self.assertEqual(response['Location'], target)

    def test_descargas_y_respuestas_json_no_cambian(self):
        for mime in ['application/pdf', 'application/json']:
            response = self.response('/gestion/unidades/lab/?_panel=1', response=HttpResponse('data', content_type=mime))
            self.assertEqual(response['X-Frame-Options'], 'DENY')
            self.assertEqual(response.content, b'data')

    def test_denegacion_de_permiso_se_conserva_visible_dentro_del_panel(self):
        response = self.response('/gestion/unidades/lab/?_panel=1', response=HttpResponse('Sin permiso', status=403))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
