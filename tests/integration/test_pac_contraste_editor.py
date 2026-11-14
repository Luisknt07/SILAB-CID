"""El editor reutiliza el diagnóstico leído, sin alterar las rutas de exportación."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.documentos.presentation.expediente_redaccion import _campos_para_editor, _unir_sugerencias_compra
from apps.documentos.presentation.pac_universitario import bloques_pac, datos_editor_pac


class ContrasteEditorPacTests(SimpleTestCase):
    def contenido(self):
        return dict(pac_version=2, compras=[dict(
            id_necesidad='145ceaf6-7c17-4eaf-a256-c1b3e98fd477',
            item='Microscopio', area_id='unidad', area_nombre='Toda la unidad',
            tipo_necesidad='dotacion', clase_bien='equipos', cantidad='2',
            costo_unitario='15.00', mes_compra='2', equipos_referencia=[],
            justificacion='Revisar la dotación disponible antes de adquirir.')])

    def test_sin_lectura_no_construye_contraste_ni_consulta_fuentes_para_el_pdf(self):
        contenido = self.contenido()
        original = deepcopy(contenido)
        with patch('apps.documentos.presentation.compras_contraste.contrastar_compras',
                   side_effect=AssertionError('El contraste requiere una lectura ya disponible.')):
            for diagnostico in (None, {}, [], ''):
                self.assertNotIn('contraste_pac', datos_editor_pac(contenido, diagnostico=diagnostico))
            self.assertTrue(bloques_pac(contenido))
        self.assertEqual(contenido, original)

    def test_lectura_disponible_se_reutiliza_y_conserva_los_importes_del_editor(self):
        contenido = self.contenido()
        diagnostico = dict(version=1, fecha_corte='2026-10-21', areas=[], fuentes={})
        originales = deepcopy((contenido, diagnostico))
        esperado = dict(version=1, disponible=True, areas=[], necesidades=[])
        with patch('apps.documentos.presentation.compras_contraste.contrastar_compras',
                   return_value=esperado) as contraste:
            datos = datos_editor_pac(contenido, diagnostico=diagnostico)
        contraste.assert_called_once_with(contenido, diagnostico)
        self.assertIs(contraste.call_args.args[1], diagnostico)
        self.assertIs(datos['contraste_pac'], esperado)
        self.assertEqual(datos['pac_total'], 30)
        self.assertEqual((contenido, diagnostico), originales)

    def test_campos_recibe_lectura_opcional_sin_romper_llamadas_anteriores(self):
        contenido = self.contenido()
        diagnostico = dict(version=1, fecha_corte='2026-10-21', areas=[], fuentes={})
        seccion = SimpleNamespace(campos=[SimpleNamespace(tipo='tabla', clave='compras')])
        documento = SimpleNamespace(estado='pendiente')
        args = ('compras', contenido, None, documento, date(2026, 1, 1), date(2026, 12, 31), {})
        with patch('apps.documentos.presentation.expediente_redaccion.secciones_de', return_value=[seccion]), \
                patch('apps.documentos.presentation.compras_contraste.contrastar_compras',
                      return_value={'disponible': True}) as contraste:
            anterior = _campos_para_editor(*args)[0]['campos'][0]
            self.assertNotIn('contraste_pac', anterior)
            actual = _campos_para_editor(*args, diagnostico_compra=diagnostico)[0]['campos'][0]
        contraste.assert_called_once_with(contenido, diagnostico)
        self.assertTrue(actual['pac'])
        self.assertTrue(actual['contraste_pac']['disponible'])
        self.assertEqual(actual['filas_pac'], anterior['filas_pac'])

    def test_union_preserva_indices_y_anade_cada_referencia_una_sola_vez_sin_mutar_fuentes(self):
        originales = [dict(clave='diagnostico:8', item='Repuesto'),
                      dict(clave='diagnostico:2', item='Equipo')]
        nueva = dict(clave='referencia-area:4:ficha:12', item='Microscopio', cantidad='',
                     estado='por_verificar', carencia_confirmada=False)
        contraste = dict(areas=[dict(sugerencias=[originales[1], nueva]),
                               dict(sugerencias=[nueva, originales[0]])])
        fuentes = deepcopy((originales, contraste))
        unidas = _unir_sugerencias_compra(originales, contraste)
        self.assertEqual([p['clave'] for p in unidas],
                         ['diagnostico:8', 'diagnostico:2', 'referencia-area:4:ficha:12'])
        self.assertEqual(unidas[:2], originales)
        self.assertEqual(unidas[2]['cantidad'], '')
        self.assertFalse(unidas[2]['carencia_confirmada'])
        self.assertEqual((originales, contraste), fuentes)
        self.assertEqual(_unir_sugerencias_compra(originales, None), originales)
