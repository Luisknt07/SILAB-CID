"""Compras por clase/área con conciliación entre editor, informe y Excel."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.compras_resumen import resumen_compras
from apps.documentos.presentation.pac_universitario import (
    bloques_pac, datos_editor_pac, preparar_pac, render_pac_xlsx, validar_pac,
)
from tests.integration.test_pac_programacion import contenido_v2


def compras_de_ejemplo():
    contenido = contenido_v2(clase_bien='equipos', item='Microscopio', cantidad='2', costo_unitario='10',
                             area_nombre='Área B', mes_compra='2')
    modelos = [('software', 'Licencia CAD', '1', '10', '4'),
               ('materiales', 'Soporte', '3', '3', '7'),
               ('repuestos', 'Boquilla', '2', '2', '8'),
               ('insumos', 'Filamento PLA', '4', '2', '9'),
               ('reactivos', 'Reactivo de referencia', '5', '3', '10')]
    for clase, nombre, cantidad, costo, mes in modelos:
        fila = deepcopy(contenido['compras'][0])
        fila.pop('id_necesidad', None)
        fila.update(clase_bien=clase, item=nombre, cantidad=cantidad, costo_unitario=costo,
                    area_nombre='Área A', mes_compra=mes)
        contenido['compras'].append(fila)
    return preparar_pac(contenido)


class ResumenComprasTests(SimpleTestCase):
    def libro(self, contenido):
        libro = load_workbook(BytesIO(render_pac_xlsx(contenido, 'Unidad de prueba', 2027)), data_only=True)
        self.addCleanup(libro.close)
        return libro

    def test_cuatro_clases_suman_compras_sin_sumar_activos_existentes_ni_repetir_tipos(self):
        contenido = compras_de_ejemplo()
        contenido['diagnostico_compras_fuentes'] = {'equipos': [{'cantidad': 195, 'costo': 99999}]}
        datos = resumen_compras(contenido)
        self.assertEqual([(c['nombre'], c['total']) for c in datos['clases']],
                         [('Equipos', 20), ('Software', 10), ('Materiales', 13), ('Insumos', 23)])
        self.assertEqual(datos['numero_necesidades'], 6)
        self.assertEqual(datos['total_general'], Decimal('66.00'))
        self.assertEqual((datos['semestre_1'], datos['semestre_2']), (30, 36))
        self.assertEqual({f['clase'] for f in datos['clases'][2]['filas']}, {'Materiales', 'Repuestos y accesorios'})
        self.assertEqual({f['clase'] for f in datos['clases'][3]['filas']}, {'Insumos', 'Reactivos'})

    def test_editor_pdf_y_excel_presentan_los_mismos_cuatro_importes_y_total(self):
        contenido = compras_de_ejemplo()
        datos = resumen_compras(contenido)
        editor = datos_editor_pac(contenido)
        pdf = bloques_pac(contenido)
        libro = self.libro(contenido)
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        self.assertEqual(editor['pac_total'], datos['total_general'])
        for numero, clase in enumerate(datos['clases'], 5):
            self.assertEqual(libro['Resumen'].cell(numero, 1).value, clase['nombre'])
            self.assertEqual(libro['Resumen'].cell(numero, 6).value, clase['total'])
            self.assertEqual(pdf[0]['filas'][numero - 5][-1], f"{clase['total']:,.2f}")
        self.assertEqual(libro['Resumen']['F9'].value, datos['total_general'])
        self.assertEqual(pdf[0]['filas'][-1][-1], '66.00')

    def test_reporte_html_pdf_incluye_mes_y_semestre_por_compra_como_excel(self):
        contenido = compras_de_ejemplo()
        bloques = bloques_pac(contenido)
        detalles = [b for b in bloques if b['tipo'] == 'tabla' and ' · ' in b['titulo']]
        self.assertTrue(detalles)
        programacion = {fila[0]: fila[-1] for b in detalles for fila in b['filas']
                        if fila[0] != 'Subtotal del área'}
        self.assertEqual(programacion['Microscopio'], 'Febrero\nSemestre 1')
        self.assertEqual(programacion['Soporte'], 'Julio\nSemestre 2')
        self.assertTrue(all(b['cabecera'][-1] == 'Mes / semestre' for b in detalles))
        libro = self.libro(contenido)
        self.assertEqual((libro['Equipos']['J6'].value, libro['Equipos']['K6'].value), ('Febrero', 1))
        self.assertEqual((libro['Materiales']['J6'].value, libro['Materiales']['K6'].value), ('Julio', 2))

    def test_equipos_solicitados_por_area_se_ordenan_y_tienen_subtotales_sin_otra_lista_de_inventario(self):
        contenido = compras_de_ejemplo()
        fila = deepcopy(contenido['compras'][0])
        fila.update(id_necesidad='', item='Balanza', area_nombre='Área A', cantidad='1', costo_unitario='6')
        contenido['compras'].append(fila)
        datos = resumen_compras(contenido)
        self.assertEqual([a['nombre'] for a in datos['clases'][0]['grupos_areas']], ['Área A', 'Área B'])
        self.assertEqual([a['total'] for a in datos['clases'][0]['grupos_areas']], [6, 20])
        libro = self.libro(contenido)
        self.assertEqual(libro['Equipos']['A5'].value, 'Área A')
        self.assertEqual(libro['Equipos']['B6'].value, 'Balanza')
        self.assertEqual(libro['Equipos']['A8'].value, 'Área B')
        self.assertEqual(libro['Equipos']['B9'].value, 'Microscopio')
        self.assertEqual(libro['Equipos']['H11'].value, 26)
        titulos = [b['titulo'] for b in bloques_pac(contenido)]
        self.assertIn('Equipos · Área A', titulos)
        self.assertIn('Equipos · Área B', titulos)

    def test_monto_pendiente_no_se_presenta_como_total_parcial_y_mes_no_se_inventa(self):
        contenido = compras_de_ejemplo()
        contenido['compras'][0].update(costo_unitario='', mes_compra='')
        datos = resumen_compras(contenido)
        self.assertIsNone(datos['total_general'])
        self.assertIsNone(datos['clases'][0]['total'])
        self.assertEqual(datos['meses_pendientes'], 1)
        self.assertIsNone(datos_editor_pac(contenido)['pac_total'])
        libro = self.libro(contenido)
        self.assertIsNone(libro['Resumen']['F5'].value)
        self.assertIsNone(libro['Resumen']['F9'].value)
        self.assertIn('No se muestra una suma parcial', libro['Resumen']['F9'].comment.text)
        self.assertIn('Por programar', [c.value for row in libro['Equipos'] for c in row])
        self.assertEqual(bloques_pac(contenido)[1]['tipo'], 'parrafo')

    def test_importes_se_redondean_por_necesidad_y_resumen_coincide_con_detalle(self):
        contenido = preparar_pac(contenido_v2(clase_bien='materiales', cantidad='3', costo_unitario='0.335'))
        segunda = deepcopy(contenido['compras'][0])
        segunda.update(item='Otra presentación', cantidad='1', costo_unitario='0.334')
        contenido['compras'].append(segunda)
        datos = resumen_compras(contenido)
        self.assertEqual([f['total'] for f in datos['filas']], [Decimal('1.01'), Decimal('0.33')])
        self.assertEqual(datos['total_general'], Decimal('1.34'))
        self.assertEqual(self.libro(contenido)['Resumen']['F9'].value, 1.34)

    def test_servicio_no_se_disfraza_de_material_e_invalido_no_desaparece_del_total(self):
        contenido = preparar_pac(contenido_v2(clase_bien='servicios'))
        contenido['compras'].append(dict(contenido['compras'][0], clase_bien='invalido'))
        datos = resumen_compras(contenido)
        self.assertEqual([c['clave'] for c in datos['clases']],
                         ['equipos', 'software', 'materiales', 'insumos', 'servicios', 'por_clasificar'])
        self.assertEqual(datos['numero_necesidades'], 2)
        self.assertEqual(self.libro(contenido).sheetnames[-2:], ['Servicios de soporte', 'Por clasificar'])

    def test_codigos_y_formulas_en_textos_siguen_siendo_texto_y_cpc_no_se_fabrica(self):
        contenido = preparar_pac(contenido_v2(clase_bien='equipos', item='=Equipo',
            area_nombre='=Área', especificaciones='=HYPERLINK("x")', cpc='011200011'))
        original = deepcopy(contenido)
        hoja = self.libro(contenido)['Equipos']
        self.assertEqual(hoja['B6'].value, '=Equipo')
        self.assertEqual(hoja['B6'].data_type, 's')
        self.assertTrue(hoja['D6'].quotePrefix)
        self.assertEqual(hoja['I6'].value, '011200011')
        self.assertEqual(hoja['I6'].data_type, 's')
        self.assertIn('Por validar', hoja['I6'].comment.text)
        self.assertEqual(contenido, original)
        for codigo, invalido in [('', False), ('011200011', False), ('12345678', True), ('1.234.56789', True)]:
            contenido['compras'][0]['cpc'] = codigo
            self.assertEqual(any(h['regla'] == 'pac_cpc_invalido' for h in validar_pac(contenido)), invalido)

    def test_editor_muestra_resumen_filtros_y_busqueda_sin_rellenar_codigos_ni_duplicar_campos(self):
        contenido = compras_de_ejemplo()
        html = render_to_string('portal/pages/unidades/gestion/includes/pac_editor.html',
            dict(dato=datos_editor_pac(contenido), campo={}, documento={'estado': 'generado'}))
        for texto in ('Resumen de compras solicitadas', 'data-pac-filtro-area', 'data-pac-filtro-clase',
                      'data-pac-cpc-buscar', 'CPC por confirmar'):
            self.assertIn(texto, html)
        self.assertEqual(html.count('name="compras__cpc"'), 7)
        self.assertNotIn('añade «Detalle por clase»', html)
