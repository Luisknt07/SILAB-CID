"""Las fases programan necesidades reales, sin duplicar el presupuesto."""
from copy import deepcopy
from io import BytesIO

from django.http import QueryDict
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.pac_universitario import (
    ENCABEZADOS_PROGRAMACION_CLASES, bloques_pac, datos_editor_pac,
    identidades_formulario_pac, leer_pac, preparar_pac, render_pac_xlsx, validar_pac,
)
from tests.integration.test_pac_programacion import contenido_v2


def contenido_fases(**cambios):
    return preparar_pac(contenido_v2(clase_bien='software', **cambios))


def bloqueos(contenido):
    return {h['regla'] for h in validar_pac(contenido) if h['severidad'] == 'bloqueo'}


class FasesPacTests(SimpleTestCase):
    def test_proyeccion_editable_no_reinterpreta_archivo_sin_marcador(self):
        original = contenido_v2()
        copia = deepcopy(original)
        preparado = preparar_pac(original)
        self.assertEqual(original, copia)
        self.assertNotIn('inversion_gestion_version', original)
        self.assertEqual(preparado['inversion_gestion_version'], 1)
        self.assertEqual(preparado['compras'][0]['grupo_fases'], '')
        self.assertEqual(preparar_pac(preparado), preparado)
        self.assertFalse(bloqueos(contenido_fases()))

    def test_proyecto_por_fases_exige_orden_y_resultado(self):
        contenido = contenido_fases(grupo_fases='Renovación del área digital')
        self.assertEqual(bloqueos(contenido), {'pac_fase_numero_pendiente', 'pac_fase_resultado_pendiente'})
        for numero in ('0', '21', '1.5', 'enero', True):
            contenido['compras'][0].update(fase_numero=numero, resultado_fase='Habilitar diez puestos de trabajo.')
            self.assertIn('pac_fase_numero_pendiente', bloqueos(contenido))
        contenido['compras'][0]['fase_numero'] = '2'
        self.assertFalse(bloqueos(contenido))  # Puede continuar un proyecto de otro año.

    def test_fase_sin_grupo_no_se_guarda_como_adquisicion_unica_silenciosamente(self):
        contenido = contenido_fases(fase_numero='1', resultado_fase='Habilitar diez puestos.')
        self.assertIn('pac_fase_sin_grupo', bloqueos(contenido))
        contenido.pop('inversion_gestion_version')
        self.assertNotIn('pac_fase_sin_grupo', bloqueos(contenido))

    def test_orden_de_meses_y_varios_bienes_por_fase(self):
        contenido = contenido_fases(grupo_fases='Expansión', fase_numero='2',
            resultado_fase='Abrir diez puestos para las prácticas.', mes_compra='5')
        segunda = deepcopy(contenido['compras'][0])
        segunda.update(id_necesidad='b7c8f304-dd8a-48e5-a872-cd09ba62482f', item='Licencias complementarias', mes_compra='6')
        contenido['compras'].append(segunda)
        self.assertFalse(bloqueos(contenido))
        segunda.update(fase_numero='3', mes_compra='4')
        self.assertIn('pac_fases_orden_invalido', bloqueos(contenido))
        segunda['mes_compra'] = '7'
        self.assertFalse(bloqueos(contenido))

    def test_post_conserva_id_fase_y_condicion_sin_filas_vacias_adicionales(self):
        anterior = contenido_fases(grupo_fases='Renovación', fase_numero='1',
            resultado_fase='Habilitar diez puestos.', condicion_siguiente_fase='Verificar su uso y el presupuesto.')
        post = QueryDict(mutable=True)
        for clave, valor in anterior['compras'][0].items():
            post.setlist('compras__' + clave, ['[]' if clave == 'equipos_referencia' else str(valor), ''])
        guardado = leer_pac(post, anterior)
        self.assertEqual(len(guardado['compras']), 1)
        self.assertEqual(guardado['compras'][0]['id_necesidad'], anterior['compras'][0]['id_necesidad'])
        self.assertEqual(guardado['compras'][0]['condicion_siguiente_fase'], 'Verificar su uso y el presupuesto.')
        self.assertEqual(identidades_formulario_pac(post, guardado), [guardado['compras'][0]['id_necesidad'], ''])
        self.assertFalse(bloqueos(guardado))

    def test_pdf_agrupa_sustento_sin_otro_importe_por_fase(self):
        contenido = contenido_fases(grupo_fases='Expansión', fase_numero='1',
            resultado_fase='Habilitar diez puestos.', condicion_siguiente_fase='Comprobar las prácticas ejecutadas.')
        anterior = deepcopy(contenido)
        anterior.pop('inversion_gestion_version')
        actual, legado = bloques_pac(contenido), bloques_pac(anterior)
        self.assertEqual(actual[0]['cabecera'], legado[0]['cabecera'])
        self.assertEqual(actual[0]['filas'], legado[0]['filas'])
        self.assertIn(('Fase', '1'), [par for b in actual for par in b.get('pares', [])])
        self.assertIn(('Resultado verificable de la fase', 'Habilitar diez puestos.'), [par for b in actual for par in b.get('pares', [])])
        self.assertNotIn(('Fase', '1'), [par for b in legado for par in b.get('pares', [])])

    def test_excel_conserva_fases_en_respaldo_sin_duplicar_la_compra(self):
        contenido = contenido_fases(grupo_fases='Renovación', fase_numero='2', mes_compra='9',
            resultado_fase='Operar diez puestos.', condicion_siguiente_fase='Comprobar el uso registrado.')
        libro = load_workbook(BytesIO(render_pac_xlsx(contenido, 'Unidad solicitante', 2027)))
        self.addCleanup(libro.close)
        self.assertNotIn('PROGRAMACION', libro.sheetnames)
        hoja = libro['Software']
        self.assertIn('Proyecto por fases: Renovación', hoja['L6'].comment.text)
        self.assertIn('Fase: 2', hoja['L6'].comment.text)
        self.assertIn('Resultado de fase: Operar diez puestos.', hoja['L6'].comment.text)
        self.assertEqual(hoja['K6'].value, 2)
        self.assertEqual(hoja['H6'].value, hoja['H8'].value)
        anterior = deepcopy(contenido)
        anterior.pop('compras_resumen_version')
        anterior.pop('inversion_gestion_version')
        legado = load_workbook(BytesIO(render_pac_xlsx(anterior, 'Unidad solicitante', 2027)))
        self.addCleanup(legado.close)
        self.assertEqual(tuple(c.value for c in legado['PROGRAMACION'][4]), ENCABEZADOS_PROGRAMACION_CLASES)
        self.assertNotIn('Fase: 2', legado['CONSOLIDADO']['M5'].value)

    def test_editor_fases_visibles_y_no_agrega_columna_operativa(self):
        contenido = contenido_fases(grupo_fases='Expansión', fase_numero='2', resultado_fase='Abrir diez puestos.')
        html = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html', dict(
            dato=datos_editor_pac(contenido), campo=dict(ayuda=''), documento=dict(estado='generado')))
        self.assertEqual(html.count('name="compras__grupo_fases"'), 2)
        self.assertEqual(html.count('name="compras__fase_numero"'), 2)
        self.assertIn('max="20"', html)
        self.assertIn('aria-label="Adquisición por fases opcional"', html)
        self.assertNotIn('<details', html)
        self.assertNotIn('fase_numero', html.split('<thead>')[1].split('</thead>')[0])
        contenido.pop('inversion_gestion_version')
        anterior = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html', dict(
            dato=datos_editor_pac(contenido), campo=dict(ayuda=''), documento=dict(estado='validado')))
        self.assertNotIn('name="compras__grupo_fases"', anterior)
