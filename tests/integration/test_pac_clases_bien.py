"""El objeto solicitado se distingue del motivo sin cambiar matrices emitidas."""
from copy import deepcopy
from io import BytesIO

from django.http import QueryDict
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.pac_universitario import (
    CLASES_BIEN, ENCABEZADOS_CONSOLIDADO, ENCABEZADOS_PROGRAMACION,
    bloques_pac, datos_editor_pac,
    leer_pac, preparar_pac, render_pac_xlsx, validar_pac,
)
from tests.integration.test_pac_programacion import contenido_v2


class ClasesBienPacTests(SimpleTestCase):
    def test_preparar_exige_revision_explicita_sin_deducir_clase_del_nombre(self):
        original = contenido_v2(item='Software y equipos de laboratorio', categoria='equipos')
        copia = deepcopy(original)
        preparado = preparar_pac(original)
        self.assertEqual(preparado['pac_version'], 2)
        self.assertEqual(preparado['clases_bien_version'], 1)
        self.assertEqual(preparado['compras'][0]['clase_bien'], '')
        self.assertEqual(original, copia)
        self.assertIn('pac_clase_pendiente', {h['regla'] for h in validar_pac(preparado)})
        self.assertNotIn('pac_clase_pendiente', {h['regla'] for h in validar_pac(original)})

    def test_cinco_objetos_y_servicio_de_soporte_tienen_etiquetas_independientes(self):
        self.assertEqual(dict(CLASES_BIEN), dict(equipos='Equipos', software='Software y licencias',
            materiales='Materiales', insumos='Insumos', reactivos='Reactivos',
            repuestos='Repuestos y accesorios', servicios='Servicios de soporte'))
        for clase in dict(CLASES_BIEN):
            contenido = preparar_pac(contenido_v2(clase_bien=clase))
            self.assertNotIn('pac_clase_pendiente', {h['regla'] for h in validar_pac(contenido)})
        contenido['compras'][0]['clase_bien'] = 'clase_no_confirmada'
        self.assertIn('pac_clase_pendiente', {h['regla'] for h in validar_pac(contenido)})

    def test_post_conserva_clase_y_rechaza_valor_no_catalogado_antes_de_firmar(self):
        post = QueryDict(mutable=True)
        for clave, valor in contenido_v2(clase_bien='software')['compras'][0].items():
            if clave != 'id_necesidad':
                post.setlist('compras__' + clave, ['[]' if clave == 'equipos_referencia' else str(valor)])
        guardado = leer_pac(post, {})
        self.assertEqual(guardado['clases_bien_version'], 1)
        self.assertEqual(guardado['compras'][0]['clase_bien'], 'software')
        self.assertFalse(any(h['severidad'] == 'bloqueo' for h in validar_pac(guardado)))
        post.setlist('compras__clase_bien', ['no_confirmado'])
        guardado = leer_pac(post, {})
        self.assertIn('pac_clase_pendiente', {h['regla'] for h in validar_pac(guardado)})

    def test_reposicion_software_no_exige_inventario_fisico_que_no_le_corresponde(self):
        for clase in ('software', 'materiales', 'insumos', 'reactivos', 'servicios'):
            contenido = preparar_pac(contenido_v2(clase_bien=clase, tipo_necesidad='reposicion',
                justificacion='Se sustituye la licencia actual por incompatibilidad documentada.'))
            self.assertNotIn('pac_reposicion_sin_equipo', {h['regla'] for h in validar_pac(contenido)})
        contenido['compras'][0]['clase_bien'] = 'equipos'
        self.assertIn('pac_reposicion_sin_equipo', {h['regla'] for h in validar_pac(contenido)})
        contenido.pop('clases_bien_version')
        contenido['compras'][0]['clase_bien'] = 'software'
        self.assertIn('pac_reposicion_sin_equipo', {h['regla'] for h in validar_pac(contenido)})

    def test_pdf_distingue_resumen_nuevo_y_tipo_reactivo_sin_cambiar_archivo(self):
        anterior = contenido_v2(clase_bien='reactivos')
        actual = preparar_pac(anterior)
        bloque_anterior, bloque_actual = bloques_pac(anterior), bloques_pac(actual)
        self.assertEqual(bloque_anterior[0]['cabecera'][0], 'Área')
        self.assertEqual(bloque_actual[0]['titulo'], 'Resumen de compras por clase')
        self.assertIn('Insumos', [fila[0] for fila in bloque_actual[0]['filas']])
        self.assertIn(('Tipo', 'Reactivos'), [par for b in bloque_actual for par in b.get('pares', [])])
        self.assertNotIn('compras_resumen_version', anterior)

    def test_excel_resumen_nuevo_y_matriz_archivada_conservan_su_presentacion(self):
        anterior = contenido_v2(clase_bien='software')
        actual = preparar_pac(anterior)
        libros = [load_workbook(BytesIO(render_pac_xlsx(c, 'Unidad solicitante', 2027)))
                  for c in (anterior, actual)]
        for libro in libros:
            self.addCleanup(libro.close)
        self.assertEqual(tuple(c.value for c in libros[0]['CONSOLIDADO'][4]), ENCABEZADOS_CONSOLIDADO)
        self.assertEqual(tuple(c.value for c in libros[0]['PROGRAMACION'][4]), ENCABEZADOS_PROGRAMACION)
        self.assertNotIn('Resumen', libros[0].sheetnames)
        self.assertNotIn('CONSOLIDADO', libros[1].sheetnames)
        software = libros[1]['Software']
        self.assertEqual(software['C6'].value, 'Software y licencias')
        self.assertEqual(software['B6'].value, actual['compras'][0]['item'])
        self.assertEqual(software['H6'].value, software['H8'].value)
        self.assertEqual(libros[1]['Resumen']['F6'].value, software['H8'].value)

    def test_editor_nuevo_muestra_clase_en_matriz_y_no_la_duplica_en_detalle(self):
        contenido = preparar_pac(contenido_v2(clase_bien='insumos'))
        datos = datos_editor_pac(contenido)
        html = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html', dict(
            dato=datos, campo=dict(ayuda=''), documento=dict(estado='generado')))
        self.assertEqual(html.count('name="compras__clase_bien"'), 2)  # Fila y plantilla.
        self.assertIn('value="insumos" selected', html)
        self.assertNotIn('clase_bien', html.split('<thead>')[1].split('</thead>')[0])
        self.assertLess(html.index('name="compras__clase_bien"'), html.index('Especificaciones y sustento <small'))
        self.assertIn('<span>Clase de bien o servicio <em>*</em></span>', html)
        anterior = datos_editor_pac(contenido_v2())
        html_anterior = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html', dict(
            dato=anterior, campo=dict(ayuda=''), documento=dict(estado='validado')))
        self.assertNotIn('name="compras__clase_bien"', html_anterior)
