"""Los formatos descargables conservan el mismo detalle y sus respaldos."""
from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.gestion_unidades.presentation.exportaciones_reportes import contrato_unidad, descargar_unidad, tablas_complementarias
from apps.gestion_unidades.presentation.gestion_reportes import documentos_del_expediente
from apps.gestion_unidades.presentation.reportes_excel import render_workbook


class ExportacionesUnidadParidadTests(SimpleTestCase):
    def reporte(self):
        return dict(unit=SimpleNamespace(slug='unidad-qa'), category='mantenimiento',
            category_label='Mantenimiento', scope_label='Unidad QA',
            start_date=date(2026, 8, 17), end_date=date(2026, 12, 8),
            generated_at=datetime(2026, 10, 17, 9), filter_summary=[], is_generic=True,
            dataset=dict(cards=[('Registros', 1)], headers=['Equipo', 'Cantidad'], rows=[['Equipo QA', 0]],
                supporting_documents=[dict(pk=123, codigo='RESP-001', titulo='Acta QA', recurso=1)]))

    def test_respaldo_del_html_tambien_se_incluye_en_el_contrato(self):
        reporte = self.reporte()
        tabla = tablas_complementarias(reporte)[0]
        self.assertEqual(tabla['rows'], [['RESP-001', 'Acta QA',
            reverse('respaldo_meta_unidad', args=['unidad-qa', 123])]])
        contrato = contrato_unidad(reporte)
        self.assertIn(tabla, contrato['sections'])
        self.assertEqual(contrato['sections'][0]['rows'][0][1], 0)

    def test_campos_de_ficha_estructurada_no_se_pierden_en_word(self):
        reporte = self.reporte()
        reporte['dataset'].update(structured=True, records=[dict(code='REG-001', sections=[
            dict(title='Resultados', fields=[dict(label='Cantidad', value=0),
                dict(label='Observaciones', value='Seguimiento pendiente')])])])
        seccion = contrato_unidad(reporte)['sections'][1]
        self.assertEqual(seccion['rows'], [['Cantidad', 0], ['Observaciones', 'Seguimiento pendiente']])

    def test_descarga_pdf_usa_el_mismo_renderizador_del_visor(self):
        reporte = self.reporte()
        with patch('apps.gestion_unidades.presentation.gestion_reportes.render_unit_report_pdf',
                return_value=b'%PDF-matriz-qa') as render:
            respuesta = descargar_unidad(reporte, 'pdf')
        render.assert_called_once_with(reporte)
        self.assertEqual(respuesta.content, b'%PDF-matriz-qa')
        self.assertIn('private', respuesta['Cache-Control'])
        self.assertIn('no-store', respuesta['Cache-Control'])

    def test_descarga_excel_usa_el_mismo_renderizador_dedicado(self):
        reporte = self.reporte()
        with patch('apps.gestion_unidades.presentation.reportes_excel.render_unit_report_xlsx',
                return_value=b'libro-qa') as render:
            respuesta = descargar_unidad(reporte, 'xlsx')
        render.assert_called_once_with(reporte)
        self.assertEqual(respuesta.content, b'libro-qa')

    def test_tipologia_derivada_conserva_el_vinculo_al_documento_exigido(self):
        unidad = SimpleNamespace(dependencia='observatorio-territorial-qa', codigo_base='observatorios')
        exigido = Mock(fuente_reporte='boletines')
        with patch('apps.gestion_unidades.presentation.gestion_reportes.categorias_para',
                return_value=(('boletines', 'Boletines'),)), \
                patch('apps.documentos.models.expediente.DocumentoExigido.objects') as objetos:
            objetos.filter.return_value.exclude.return_value.select_related.return_value = [exigido]
            self.assertEqual(documentos_del_expediente(unidad), {'boletines': exigido})
        exigido.aplica_a.assert_called_once_with('observatorio-territorial-qa', base='observatorios')

    def test_planilla_admite_comillas_y_controles_de_texto_sin_romper_el_xml(self):
        contenido = render_workbook([('Registro "A"', 'Resultado', ['Campo'], [['Dato\x01 verificado']]),
            ('REGISTRO "A"', 'Otro resultado', ['Campo'], [['Cero', 0]])])
        libro = load_workbook(BytesIO(contenido), data_only=True)
        self.assertEqual(libro.sheetnames, ['Registro "A"', 'REGISTRO "A" 2'])
        self.assertEqual(libro.worksheets[0]['A3'].value, 'Dato verificado')

    def test_subtipo_laboratorio_usa_el_mismo_consolidado_sin_consultar_catalogo(self):
        from apps.formacion.presentation.asignaturas import reporte_asignaturas

        unidad = SimpleNamespace(dependencia='laboratorio-fabricacion-qa', codigo_base='laboratorios')
        esperado = (['Trazabilidad FT02'], [['QA-FT02']], [('Sesiones previstas', 1)], [])
        with patch('apps.formacion.presentation.asignaturas._reporte_asignaturas_laboratorio',
                return_value=esperado) as consolidado:
            self.assertIs(reporte_asignaturas(unidad, date(2026, 8, 17), date(2026, 12, 8)), esperado)
        consolidado.assert_called_once_with(unidad, date(2026, 8, 17), date(2026, 12, 8), '', '')
