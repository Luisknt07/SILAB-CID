"""La captura diferenciada conserva el nombre y la matriz universitaria."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from django.http import QueryDict
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.pac_universitario import (
    bloques_pac, datos_editor_pac, leer_pac,
    preparar_pac, render_pac_xlsx, validar_pac,
)
from tests.integration.test_pac_programacion import contenido_v2


class MatrizDetallePacTests(SimpleTestCase):
    def test_guarda_nombre_simple_y_detalle_independiente_sin_sustituirlo_por_el_codigo(self):
        post = QueryDict(mutable=True)
        valores = dict(item='Licencia CAD', clase_bien='software', cantidad='12',
            especificaciones='Licencias nominativas, vigencia de 12 meses.', unidad_medida='usuario/año',
            area_id='unidad', tipo_necesidad='dotacion', mes_compra='2', costo_unitario='90',
            cpc='001234567', partida='530702', fuente_pac='001', equipos_referencia='[]')
        for clave, valor in valores.items():
            post.setlist('compras__' + clave, [valor])
        actual = leer_pac(post, {})
        self.assertEqual(actual['matriz_detalle_version'], 1)
        for clave in ('item', 'especificaciones', 'unidad_medida', 'cpc'):
            self.assertEqual(actual['compras'][0][clave], valores[clave])
        self.assertFalse(any(h['regla'] == 'pac_clase_pendiente' for h in validar_pac(actual)))

    def test_legacy_no_adquiere_detalles_ni_nuevas_etiquetas_al_exportarse(self):
        legado = contenido_v2(clase_bien='software', especificaciones='No reinterpretar copia archivada')
        legado['clases_bien_version'] = 1
        copia = deepcopy(legado)
        libro = load_workbook(BytesIO(render_pac_xlsx(legado, 'Unidad', 2027, borrador=False)))
        self.addCleanup(libro.close)
        self.assertEqual(legado, copia)
        self.assertNotIn('DETALLE POR CLASE', libro.sheetnames)
        self.assertEqual(libro['PROGRAMACION']['K5'].value, 'Software')
        self.assertNotIn('Especificaciones:', libro['CONSOLIDADO']['M5'].value)
        self.assertFalse(any(etiqueta == 'Especificaciones' for b in bloques_pac(legado)
                             for etiqueta, valor in b.get('pares', [])))

    def test_excel_separa_clases_con_cpc_textual_y_nombre_limpio(self):
        actual = preparar_pac(contenido_v2(item='Boquilla para impresora 3D', clase_bien='repuestos',
            especificaciones='Diámetro de 0,4 mm; compatible con el equipo registrado.',
            unidad_medida='unidad', cpc='001234567', partida='530813', fuente_pac='001'))
        libro = load_workbook(BytesIO(render_pac_xlsx(actual, 'Unidad solicitante', 2027)))
        self.addCleanup(libro.close)
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        detalle = libro['Materiales']
        self.assertEqual(detalle['B6'].value, 'Boquilla para impresora 3D')
        self.assertEqual(detalle['C6'].value, 'Repuestos y accesorios')
        self.assertIn('Diámetro de 0,4 mm', detalle['D6'].value)
        self.assertEqual(detalle['I6'].value, '001234567')
        self.assertEqual(detalle['I6'].data_type, 's')
        self.assertEqual(detalle['H6'].value, detalle['H7'].value)
        self.assertEqual(detalle['H7'].value, detalle['H8'].value)

    def test_excel_detalle_no_interpreta_especificaciones_como_formulas(self):
        actual = preparar_pac(contenido_v2(clase_bien='equipos', especificaciones='=HYPERLINK("x")'))
        libro = load_workbook(BytesIO(render_pac_xlsx(actual, 'Unidad', 2027)))
        self.addCleanup(libro.close)
        self.assertEqual(libro['Equipos']['D6'].data_type, 's')
        self.assertTrue(libro['Equipos']['D6'].quotePrefix)

    def test_editor_clase_visible_detalles_separados_y_cpc_aun_pendiente_no_inventado(self):
        contenido = preparar_pac(contenido_v2(clase_bien='reactivos', item='Ácido acético'))
        html = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html', dict(
            dato=datos_editor_pac(contenido), campo={}, documento={'estado': 'generado'}))
        self.assertIn('<span>Clase de bien o servicio <em>*</em></span>', html)
        self.assertIn('name="compras__especificaciones"', html)
        self.assertIn('name="compras__unidad_medida"', html)
        self.assertIn('CPC por confirmar', html)
        self.assertEqual(html.count('name="compras__clase_bien"'), 2)
        self.assertIn('Software y licencias', html)
        self.assertIn('Repuestos y accesorios', html)

    def test_descarga_excel_permanente_en_la_barra_inferior_y_un_solo_control(self):
        plantilla = Path('apps/gestion_unidades/templates/portal/pages/unidades/gestion/expediente_editor.html').read_text(encoding='utf8')
        self.assertEqual(plantilla.count('data-exportar-pac'), 1)
        self.assertIn('Descargar Excel', plantilla.split('<footer class="guide-form__footer')[1])
