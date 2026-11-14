from datetime import date
import csv
from io import BytesIO
from io import StringIO
from unittest.mock import patch

from django.urls import reverse
from django.test import SimpleTestCase
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.gestion_unidades.presentation.gestion_reportes import _periodo_por_defecto
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes
from apps.gestion_unidades.presentation.exportaciones_reportes import descargar_unidad
from types import SimpleNamespace


class ExportacionCsvPrivadaTests(SimpleTestCase):
    def test_incluye_metricas_y_todas_las_tablas_sin_ejecutar_formulas(self):
        reporte = dict(unit=SimpleNamespace(slug='unidad'), start_date=date(2026, 7, 1), end_date=date(2026, 12, 31))
        contrato = dict(title='Uso', scope='Unidad', generated_at='2026-10-18',
            filter_summary=[('Búsqueda', ' =2+2')], metrics=[dict(nombre='Horas', valor=2, periodo='Semestre')],
            notes=['@nota'], sections=[dict(titulo='Mensual', headers=['Mes', 'Horas'], rows=[['Julio', 2]]),
                dict(titulo='Fuentes', headers=['Fuente'], rows=[['\t=HYPERLINK("x")']])])
        with patch('apps.gestion_unidades.presentation.exportaciones_reportes.contrato_unidad', return_value=contrato):
            respuesta = descargar_unidad(reporte, 'csv')
        filas = list(csv.reader(StringIO(respuesta.content.decode('utf-8-sig')), delimiter=';'))
        self.assertIn(['Horas', '2', 'Semestre'], filas)
        self.assertIn(['Búsqueda', "' =2+2"], filas)
        self.assertIn(["'\t=HYPERLINK(\"x\")"], filas)
        self.assertIn(['Nota', "'@nota"], filas)
        self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')


class ReportesCapacidadExportacionesTests(BaseAlcanceReportes):
    def consultar(self, nombre, unidad, **extras):
        return self.client.get(reverse(nombre, args=[unidad.slug]), dict(categoria_reporte='uso-capacidad',
            desde='2026-07-01', hasta='2026-12-31', **extras))

    def test_defecto_cubre_todo_el_semestre_aunque_las_clases_tengan_otras_fechas(self):
        with patch('apps.gestion_unidades.presentation.gestion_reportes._periodo_academico_vigente',
                   return_value=(date(2026, 8, 17), date(2026, 12, 8))) as academico:
            self.assertEqual(_periodo_por_defecto(date(2026, 10, 18)), (date(2026, 7, 1), date(2026, 12, 31)))
            academico.assert_not_called()

    def test_reporte_html_pdf_csv_y_xlsx_publican_el_mismo_alcance_en_los_tres_tipos_fisicos(self):
        for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental'):
            unidad = self.unidades[tipo]
            self.client.force_login(self.usuarios[tipo])
            with self.subTest(tipo=tipo):
                html = self.consultar('gestion_reporte_unidad', unidad)
                self.assertEqual(html.status_code, 200)
                self.assertContains(html, 'Capacidad y aprovechamiento')
                self.assertContains(html, '2026-07-01')
                pdf = self.consultar('gestion_reporte_unidad_pdf', unidad)
                self.assertEqual(pdf.status_code, 200)
                reader = PdfReader(BytesIO(pdf.content))
                texto = '\n'.join(p.extract_text() or '' for p in reader.pages)
                self.assertIn('Capacidad y aprovechamiento', texto)
                self.assertIn('Pendiente', texto)
                csv = self.consultar('gestion_reporte_unidad', unidad, formato='csv')
                self.assertEqual(csv.status_code, 200)
                self.assertIn('Horas', csv.content.decode('utf-8-sig'))
                xlsx = self.consultar('gestion_reporte_unidad_xlsx', unidad)
                self.assertEqual(xlsx.status_code, 200)
                libro = load_workbook(BytesIO(xlsx.content), read_only=True)
                self.assertGreaterEqual(len(libro.sheetnames), 1)
                libro.close()

    def test_reporte_no_atribuye_operacion_a_otra_unidad(self):
        self.client.force_login(self.usuarios['laboratorios'])
        ajena = self.unidades['plantas_piloto']
        for nombre in ('gestion_reporte_unidad', 'gestion_reporte_unidad_pdf', 'gestion_reporte_unidad_xlsx'):
            self.assertEqual(self.consultar(nombre, ajena).status_code, 403)

    def test_observatorio_conserva_informes_de_datos_y_no_recibe_obligacion_fisica(self):
        self.client.force_login(self.usuarios['observatorios'])
        self.assertEqual(self.consultar('gestion_reporte_unidad', self.unidades['observatorios']).status_code, 400)
