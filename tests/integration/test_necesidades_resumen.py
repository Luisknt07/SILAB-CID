"""Exportación por clases de la demanda evaluada, sin repetir inventario ni unidades."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.necesidades_decanato import render_necesidades_xlsx
from apps.documentos.presentation.necesidades_resumen import contenido_consolidado, lectura_compras_consolidadas


class NecesidadesResumenTests(SimpleTestCase):
    def necesidad(self, nombre, clase, cantidad, unitario, mes='2', area='Área uno', cpc='011200011'):
        return dict(id_necesidad=str(uuid4()), item=nombre, clase_bien=clase, cantidad=str(cantidad),
            costo_unitario=str(unitario), mes_compra=mes, area_id='unidad', area_nombre=area,
            cpc=cpc, especificaciones='Características por confirmar.', unidad_medida='unidad',
            justificacion='Brecha documentada.', tipo_necesidad='dotacion')

    def unidad(self, identificador, nombre, filas=None, transferible=True, estado='Con compras'):
        return dict(id=identificador, nombre=nombre, transferible=transferible, estado_etiqueta=estado,
            sin_compras_justificacion='Los recursos disponibles cubren la programación.' if estado == 'Sin compras' else '',
            pac_datos=dict(pac_version=2, matriz_detalle_version=1, clases_bien_version=1,
                compras_resumen_version=1, compras=filas or []))

    def lectura(self):
        filas = [self.necesidad('Equipo nuevo', 'equipos', 2, '10.05'),
            self.necesidad('Licencia anual', 'software', 3, '7.50', mes='8', cpc='4522000111'),
            self.necesidad('Pieza de reemplazo', 'repuestos', 2, '2.35'),
            self.necesidad('Material de trabajo', 'materiales', 1, '1.10'),
            self.necesidad('Reactivo de análisis', 'reactivos', 1, '3.25', mes='9'),
            self.necesidad('Insumo de práctica', 'insumos', 5, '.10', mes='9')]
        return dict(anio_compras=2027, unidades=[self.unidad(1, 'Unidad uno', filas),
            self.unidad(2, 'Unidad dos', [self.necesidad('Equipo de otra unidad', 'equipos', 1, '20.10')]),
            self.unidad(3, 'Unidad sin compras', estado='Sin compras'),
            self.unidad(4, 'Unidad pendiente', [self.necesidad('NO EXPORTAR PENDIENTE', 'equipos', 999, 900)],
                        transferible=False, estado='Pendiente de evaluación')])

    def libro(self, lectura):
        # SimpleTestCase impide toda consulta a la base de datos.
        salida = render_necesidades_xlsx(lectura)
        libro = load_workbook(BytesIO(salida), data_only=False)
        self.addCleanup(libro.close)
        return libro

    def test_consolida_cuatro_clases_y_total_sin_sumar_inventario_o_solicitudes_pendientes(self):
        lectura = self.lectura()
        original = deepcopy(lectura)
        libro = self.libro(lectura)
        self.assertEqual(lectura, original)
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        # Repuestos se presentan en Materiales y reactivos en Insumos conservando el tipo.
        esperado = {'Equipos': Decimal('40.20'), 'Software': Decimal('22.50'),
                    'Materiales': Decimal('5.80'), 'Insumos': Decimal('3.75')}
        for fila in libro['Resumen'].iter_rows(min_row=5, max_row=8):
            self.assertEqual(Decimal(str(fila[5].value)), esperado[fila[0].value])
        self.assertEqual(libro['Resumen']['F9'].value, 72.25)
        self.assertEqual(libro['Resumen']['B9'].value, 7)
        self.assertEqual(libro['Resumen']['C9'].value, 46)
        self.assertEqual(libro['Resumen']['D9'].value, 26.25)
        self.assertNotIn('NO EXPORTAR PENDIENTE', str([list(hoja.values) for hoja in libro]))
        self.assertFalse(any(celda.data_type == 'f' for hoja in libro for fila in hoja for celda in fila))

    def test_misma_area_en_unidades_distintas_no_funde_solicitudes_ni_duplica_detalles(self):
        lectura = self.lectura()
        libro = self.libro(lectura)
        hoja = libro['Equipos']
        encabezados_areas = [fila[0].value for fila in hoja if fila[0].value in (
            'Unidad uno · Área uno', 'Unidad dos · Área uno')]
        self.assertCountEqual(encabezados_areas, ['Unidad uno · Área uno', 'Unidad dos · Área uno'])
        detalles = [fila[1].value for fila in hoja if isinstance(fila[0].value, int)]
        self.assertCountEqual(detalles, ['Equipo nuevo', 'Equipo de otra unidad'])
        filas = contenido_consolidado(lectura)['compras']
        self.assertEqual(len(filas), 7)
        self.assertEqual(len({f['id_necesidad'] for f in filas}), 7)
        self.assertTrue(all(' · ' in f['area_nombre'] for f in filas))

    def test_codigos_completos_como_texto_y_nombres_libres_de_especificaciones(self):
        libro = self.libro(self.lectura())
        equipo, software = libro['Equipos'], libro['Software']
        self.assertEqual((equipo['B6'].value, equipo['D6'].value),
            ('Equipo de otra unidad', 'Características por confirmar.'))
        self.assertEqual((equipo['I6'].value, equipo['I6'].data_type), ('011200011', 's'))
        self.assertEqual((software['I6'].value, software['I6'].data_type), ('4522000111', 's'))
        self.assertIn('Por validar', software['I6'].comment.text)

    def test_resumen_indica_todas_las_unidades_incluido_sin_compras_y_pendientes(self):
        libro = self.libro(self.lectura())
        hoja = libro['Resumen']
        situacion = [fila for fila in hoja.values if fila[0] in (
            'Unidad uno', 'Unidad dos', 'Unidad sin compras', 'Unidad pendiente')]
        self.assertEqual(len(situacion), 4)
        por_nombre = {fila[0]: fila for fila in situacion}
        self.assertEqual(por_nombre['Unidad sin compras'][1], 'Sin compras')
        self.assertIn('cubren la programación', por_nombre['Unidad sin compras'][2])
        self.assertEqual(por_nombre['Unidad pendiente'][1], 'Pendiente de evaluación')
        self.assertIn('no equivale a ausencia de necesidades', por_nombre['Unidad pendiente'][2])

    def test_textos_de_usuario_se_exportan_como_texto_y_no_como_formulas(self):
        lectura = self.lectura()
        lectura['unidades'][0]['nombre'] = '=UNIDAD()'
        lectura['unidades'][0]['pac_datos']['compras'][0].update(item='=NOMBRE()', cpc='001234567')
        libro = self.libro(lectura)
        fila = next(fila for fila in libro['Equipos'] if len(fila) > 1 and fila[1].value == '=NOMBRE()')
        self.assertEqual(fila[1].data_type, 's')
        self.assertEqual(fila[8].value, '001234567')
        estado = next(fila for fila in libro['Resumen'] if fila[0].value == '=UNIDAD()')
        self.assertEqual(estado[0].data_type, 's')

    def test_consolidado_mixto_conserva_importes_legados_y_misma_suma_en_pdf_excel(self):
        from apps.documentos.presentation.compras_resumen import resumen_compras
        from apps.documentos.presentation.necesidades_decanato import _necesidad, render_necesidades_pdf
        legado = self.unidad(1, 'Unidad legacy', [self.necesidad('Primera antigua', 'equipos', 1, '.005'),
            self.necesidad('Segunda antigua', 'equipos', 1, '.005')])
        legado['pac_datos'].pop('compras_resumen_version')
        nueva = self.unidad(2, 'Unidad nueva', [self.necesidad('Nueva', 'software', 1, '1.00')])
        lectura = dict(anio_preparacion=2026, anio_compras=2027, alcance='Centro de costo de prueba',
            unidades=[legado, nueva])
        for unidad in lectura['unidades']:
            unidad.update(dependencia_nombre='Dependencia de prueba', centro_costo='Centro de prueba',
                          fuente=dict(token='fuente-documentada'))
            unidad['necesidades'] = [_necesidad(fila, numero, incluir_detalle=True,
                incluir_resumen=unidad['pac_datos'].get('compras_resumen_version') == 1)
                for numero, fila in enumerate(unidad['pac_datos']['compras'], 1)]
            unidad['total'] = str(sum((Decimal(n['total']) for n in unidad['necesidades']), Decimal(0)))
        lectura['resumen'] = dict(total='1.010', unidades_total=2, con_compras=2, sin_compras=0, pendientes=0)
        original = deepcopy(lectura)
        contenido, importes = lectura_compras_consolidadas(lectura)
        self.assertEqual(importes, [Decimal('.005'), Decimal('.005'), Decimal('1.00')])
        self.assertEqual(resumen_compras(contenido, importes_documentados=importes)['total_general'], Decimal('1.010'))
        libro = self.libro(lectura)
        self.assertEqual(libro['Resumen']['F9'].value, 1.01)
        self.assertEqual((libro['Equipos']['H6'].value, libro['Equipos']['H7'].value), (.005, .005))
        self.assertEqual(libro['Equipos']['G6'].value, .005)
        self.assertIn('#', libro['Equipos']['G6'].number_format.split('.')[1][2:])
        self.assertIn('#', libro['Equipos']['H6'].number_format.split('.')[1][2:])
        with patch('apps.core.reportes.render_reporte', side_effect=lambda reporte, *_args, **_kwargs: reporte):
            reporte = render_necesidades_pdf(lectura, marco_pdf={})
        resumen_pdf = reporte['sections'][0]
        self.assertEqual(resumen_pdf['rows'][-1][-1], '1.01')
        self.assertNotEqual(resumen_pdf['rows'][-1][-1], '1.02')
        self.assertEqual(lectura, original)

    def test_resumen_documentado_conserva_fracciones_y_no_acepta_override_del_formulario(self):
        from apps.documentos.presentation.compras_resumen import (
            bloques_resumen_compras, formato_monto, resumen_compras,
        )
        contenido = self.unidad(1, 'Unidad', [self.necesidad('Bien nuevo', 'equipos', 1, '.005')])['pac_datos']
        # Esta clave dentro del contenido no puede sustituir un cálculo nuevo.
        contenido['importes_documentados'] = [Decimal('999')]
        self.assertEqual(resumen_compras(contenido)['total_general'], Decimal('.01'))
        self.assertEqual(formato_monto(Decimal('.005'), conservar_precision=True), '0.005')
        tabla = next(b for b in bloques_resumen_compras(contenido) if b.get('cabecera', [None])[0] == 'Nombre del bien')
        self.assertEqual(tabla['filas'][0][3:5], ['0.005', '0.01'])
        for importes in ([Decimal('1'), Decimal('2')], [Decimal('NaN')], ['.005']):
            with self.subTest(importes=importes), self.assertRaises(ValueError):
                resumen_compras(contenido, importes_documentados=importes)
