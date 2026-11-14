"""Referencias aportadas: códigos exactos, búsqueda y guardado sin confirmación falsa."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase

from apps.documentos.presentation.catalogo_cpc import (
    buscar_cpc, fijar_referencia_cpc, fuente_catalogo_cpc, referencia_cpc, validar_codigo_cpc,
)
from apps.documentos.presentation.catalogo_cpc_vistas import buscar_cpc_necesidad_view


class ReferenciasCpcTests(SimpleTestCase):
    def test_fuente_conserva_procedencia_y_no_se_presenta_como_catalogo_vigente(self):
        fuente = fuente_catalogo_cpc()
        self.assertEqual(fuente['registros'], 31932)
        self.assertEqual(fuente['registros_seleccionables'], 31891)
        self.assertEqual(fuente['sha256'], 'e10439fd8706e394ea36a046c75d988183384e41c8bedf01b7f2646e4fae76ad')
        self.assertIn('no certifica vigencia', fuente['alcance'])
        fuente['nombre'] = 'No modifica el catálogo'
        self.assertEqual(fuente_catalogo_cpc()['nombre'], 'CPC_SOLICITUD_GEN.xls')

    def test_preserva_ceros_y_codigos_extendidos_del_archivo(self):
        self.assertEqual(referencia_cpc('011200011')['codigo'], '011200011')
        extendido = referencia_cpc('4522000111')
        self.assertEqual(extendido['descripcion'], 'COMPUTADORAS PORTATILES PERFIL 1.2')
        self.assertEqual(extendido['codigo'], '4522000111')
        self.assertTrue(extendido['seleccionable'])
        self.assertEqual(extendido['estado'], 'por_validar')
        self.assertEqual(referencia_cpc('38912013307')['descripcion'], 'TONER')
        # Estos registros se conservan para el contraste, sin completarlos con ceros.
        self.assertFalse(referencia_cpc('35260411')['seleccionable'])
        self.assertNotIn('35260411', [fila['codigo'] for fila in buscar_cpc('35260411')])

    def test_busca_por_codigo_o_todos_los_terminos_sin_confundir_seleccion_y_revision(self):
        self.assertEqual(buscar_cpc('4522000111')[0]['codigo'], '4522000111')
        filas = buscar_cpc('computadora portatil', limite=5)
        self.assertEqual(len(filas), 5)
        self.assertTrue(all('COMPUTADORA' in fila['descripcion'] and 'PORTATIL' in fila['descripcion'] for fila in filas))
        self.assertTrue(all(fila['estado'] == 'por_validar' for fila in filas))
        self.assertEqual(buscar_cpc('cámara', 2), buscar_cpc('CAMARA', 2))
        self.assertEqual(buscar_cpc('producto-que-no-existe-32435'), [])
        self.assertEqual(buscar_cpc('x'), [])
        self.assertLessEqual(len(buscar_cpc('computador', limite=999999)), 30)

    def test_no_inventa_codigos_ni_requiere_cpc_para_identificar_una_necesidad(self):
        self.assertEqual(validar_codigo_cpc(''), '')
        self.assertEqual(validar_codigo_cpc(' 4522000111 '), '')
        self.assertEqual(validar_codigo_cpc('012345678912'), '')
        self.assertIsNone(referencia_cpc('012345678912'))
        for codigo in ('45.220.001', '12345678', '1234567890123', '00012x345', '１２３４５６７８９', 4522000111):
            with self.subTest(codigo=codigo):
                self.assertTrue(validar_codigo_cpc(codigo))

    def test_guardado_deriva_descripcion_del_servidor_y_descarta_validacion_del_cliente(self):
        original = {'item': 'Computador portátil', 'cpc': '4522000111',
                    'cpc_descripcion': 'Texto alterado', 'cpc_estado': 'validado', 'cpc_fuente': {'nombre': 'falso'}}
        antes = deepcopy(original)
        guardado = fijar_referencia_cpc(original)
        self.assertEqual(original, antes)
        self.assertEqual(guardado['cpc_descripcion'], 'COMPUTADORAS PORTATILES PERFIL 1.2')
        self.assertEqual(guardado['cpc_estado'], 'por_validar')
        self.assertEqual(guardado['cpc_fuente']['nombre'], 'CPC_SOLICITUD_GEN.xls')
        desconocido = fijar_referencia_cpc(dict(original, cpc='012345678912'))
        self.assertNotIn('cpc_descripcion', desconocido)
        self.assertNotIn('cpc_fuente', desconocido)
        self.assertEqual(desconocido['cpc_estado'], 'por_validar')
        vacio = fijar_referencia_cpc(dict(original, cpc=''))
        self.assertNotIn('cpc_descripcion', vacio)
        self.assertNotIn('cpc_estado', vacio)


class ConsultaCpcVistaTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.usuario = SimpleNamespace(is_authenticated=True)
        self.documento = SimpleNamespace(exigido=SimpleNamespace(codigo='PLAN-COMPRAS-ANUAL', fuente_reporte='compras'))

    def peticion(self, **params):
        request = self.factory.get('/gestion/unidades/unidad/expediente/123/cpc/', params)
        request.user = self.usuario
        return request

    def test_consulta_es_get_privada_y_reutiliza_el_permiso_del_documento(self):
        request = self.peticion(q='4522000111')
        with patch('apps.documentos.presentation.expediente_redaccion._documento_redactable',
                   return_value=(SimpleNamespace(), self.documento)) as permiso:
            respuesta = buscar_cpc_necesidad_view(request, 'unidad', 123)
        import json
        datos = json.loads(respuesta.content)
        permiso.assert_called_once_with(request, 'unidad', 123)
        self.assertEqual(datos['resultados'][0]['codigo'], '4522000111')
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertEqual(datos['total'], 31932)

    def test_no_busca_sin_permiso_ni_acepta_post(self):
        with patch('apps.documentos.presentation.expediente_redaccion._documento_redactable',
                   side_effect=PermissionDenied('No autorizado')):
            with self.assertRaises(PermissionDenied):
                buscar_cpc_necesidad_view(self.peticion(q='computador'), 'unidad', 123)
        request = self.factory.post('/cpc/', {'q': 'computador'})
        request.user = self.usuario
        self.assertEqual(buscar_cpc_necesidad_view(request, 'unidad', 123).status_code, 405)

    def test_no_amplia_la_funcion_a_documentos_ajenos_y_limita_busqueda(self):
        from django.http import Http404
        self.documento.exigido.codigo = 'PLANIFICACION'
        with patch('apps.documentos.presentation.expediente_redaccion._documento_redactable',
                   return_value=(SimpleNamespace(), self.documento)):
            with self.assertRaises(Http404):
                buscar_cpc_necesidad_view(self.peticion(q='computador'), 'unidad', 123)
            self.documento.exigido.codigo = 'PLAN-COMPRAS-ANUAL'
            self.assertEqual(buscar_cpc_necesidad_view(self.peticion(q='a' * 121), 'unidad', 123).status_code, 400)
