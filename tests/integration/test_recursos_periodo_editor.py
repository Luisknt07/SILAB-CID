"""Límites entre la edición nueva y la documentación conservada."""
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase

from apps.documentos.presentation.expediente_redaccion import avance, leer_formulario, secciones_de


class RecursosPeriodoEditorTests(SimpleTestCase):
    @patch('apps.documentos.presentation.expediente_redaccion._leer_actividades', return_value={})
    def test_borrar_la_cobertura_no_restaura_una_propuesta_que_parezca_confirmada(self, _actividades):
        post = QueryDict('', mutable=True)
        post.update(cobertura_recursos='', revision_recursos='revisado')
        contenido = leer_formulario('planificacion', post, SimpleNamespace())
        self.assertEqual(contenido['cobertura_recursos'], '')
        self.assertIn('cobertura_recursos', [c.clave for _, c in avance('planificacion', contenido)['faltantes']])

    @patch('apps.documentos.presentation.expediente_redaccion._leer_actividades', return_value={})
    def test_conserva_antecedentes_sin_aceptar_otras_compras_por_post_semestral(self, _actividades):
        anterior = {'inversion': [{'item': 'Necesidad conservada', 'cantidad': '1'}]}
        post = QueryDict('', mutable=True)
        post.update(inversion__item='Otra solicitud', cobertura_recursos='<p>Revisada.</p>', revision_recursos='revisado')
        contenido = leer_formulario('planificacion', post, SimpleNamespace(), contenido_anterior=anterior)
        self.assertEqual(contenido['inversion'], anterior['inversion'])
        self.assertNotIn('Otra solicitud', str(contenido))

    def test_el_titulo_del_informe_legado_no_cambia_sin_el_esquema_nuevo(self):
        def titulo(contenido):
            return next(s.titulo for s in secciones_de('informe', contenido=contenido) if s.codigo == 'presupuesto')
        self.assertEqual(titulo({}), 'Ejecución presupuestal del período')
        self.assertEqual(titulo({'recursos_periodo_version': 1}), 'Uso de recursos y ejecución del período')
