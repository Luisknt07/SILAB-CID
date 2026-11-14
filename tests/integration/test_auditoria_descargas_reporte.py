"""La consulta HTML y las descargas exitosas conservan su trazabilidad."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from apps.gestion_unidades.presentation.gestion import (
    gestion_reporte_unidad_pdf_view, gestion_reporte_unidad_view, gestion_reporte_unidad_xlsx_view,
)


class AuditoriaDescargasReporteTests(SimpleTestCase):
    def setUp(self):
        self.unidad = SimpleNamespace(pk=1, slug='unidad-qa')
        self.reporte = {'category_label': 'Formación', 'start_date': date(2026, 8, 17),
                        'end_date': date(2026, 10, 17)}
        self.factory = RequestFactory()

    def peticion(self, formato=''):
        request = self.factory.get('/gestion/unidad-qa/reportes/', {'formato': formato})
        request.user = SimpleNamespace(is_authenticated=True)
        return request

    def test_las_descargas_registran_formato_solo_despues_de_generar_el_archivo(self):
        for formato in ('docx', 'xlsx', 'pdf'):
            with self.subTest(formato=formato):
                orden = []
                respuesta = HttpResponse(b'archivo')
                def generar(reporte, elegido):
                    self.assertIs(reporte, self.reporte)
                    self.assertEqual(elegido, formato)
                    orden.append('generar')
                    return respuesta
                def auditar(*args, **kwargs):
                    orden.append('auditar')
                request = self.peticion(formato)
                with patch('apps.gestion_unidades.presentation.gestion.get_object_or_404', return_value=self.unidad), \
                     patch('apps.gestion_unidades.presentation.gestion.puede_operar_modulo_unidad', return_value=True), \
                     patch('apps.gestion_unidades.presentation.gestion.build_unit_report', return_value=self.reporte), \
                     patch('apps.gestion_unidades.presentation.exportaciones_reportes.descargar_unidad', side_effect=generar), \
                     patch('apps.gestion_unidades.presentation.gestion.registrar_auditoria', side_effect=auditar) as registro:
                    self.assertIs(gestion_reporte_unidad_view(request, self.unidad.slug), respuesta)
                self.assertEqual(orden, ['generar', 'auditar'])
                registro.assert_called_once_with(request, unidad=self.unidad, accion='descargar',
                    objeto=self.unidad, descripcion=f'{formato.upper()}: Formación')

    def test_html_registra_consulta_y_no_una_descarga(self):
        request = self.peticion()
        respuesta = HttpResponse('HTML')
        with patch('apps.gestion_unidades.presentation.gestion.get_object_or_404', return_value=self.unidad), \
             patch('apps.gestion_unidades.presentation.gestion.puede_operar_modulo_unidad', return_value=True), \
             patch('apps.gestion_unidades.presentation.gestion.build_unit_report', return_value=self.reporte), \
             patch('apps.gestion_unidades.presentation.gestion.render', return_value=respuesta), \
             patch('apps.gestion_unidades.presentation.exportaciones_reportes.descargar_unidad') as descargar, \
             patch('apps.gestion_unidades.presentation.gestion.registrar_auditoria') as registro:
            self.assertIs(gestion_reporte_unidad_view(request, self.unidad.slug), respuesta)
        descargar.assert_not_called()
        registro.assert_called_once_with(request, unidad=self.unidad, accion='consultar',
            objeto=self.unidad, descripcion='Vista HTML: Formación')

    def test_generacion_fallida_no_registra_una_descarga_exitosa(self):
        request = self.peticion('docx')
        with patch('apps.gestion_unidades.presentation.gestion.get_object_or_404', return_value=self.unidad), \
             patch('apps.gestion_unidades.presentation.gestion.puede_operar_modulo_unidad', return_value=True), \
             patch('apps.gestion_unidades.presentation.gestion.build_unit_report', return_value=self.reporte), \
             patch('apps.gestion_unidades.presentation.exportaciones_reportes.descargar_unidad', side_effect=ValueError('Fallo de render')), \
             patch('apps.gestion_unidades.presentation.gestion.registrar_auditoria') as registro:
            with self.assertRaisesMessage(ValueError, 'Fallo de render'):
                gestion_reporte_unidad_view(request, self.unidad.slug)
        registro.assert_not_called()

    def test_sin_permiso_no_genera_ni_audita_descargas(self):
        request = self.peticion('xlsx')
        with patch('apps.gestion_unidades.presentation.gestion.get_object_or_404', return_value=self.unidad), \
             patch('apps.gestion_unidades.presentation.gestion.puede_operar_modulo_unidad', return_value=False), \
             patch('apps.gestion_unidades.presentation.gestion.build_unit_report') as construir, \
             patch('apps.gestion_unidades.presentation.exportaciones_reportes.descargar_unidad') as descargar, \
             patch('apps.gestion_unidades.presentation.gestion.registrar_auditoria') as registro:
            with self.assertRaises(PermissionDenied):
                gestion_reporte_unidad_view(request, self.unidad.slug)
        construir.assert_not_called()
        descargar.assert_not_called()
        registro.assert_not_called()

    def test_rutas_dedicadas_auditan_solo_despues_de_renderizar(self):
        for vista, renderer, formato in (
            (gestion_reporte_unidad_pdf_view, 'render_unit_report_pdf', 'PDF'),
            (gestion_reporte_unidad_xlsx_view, 'render_unit_report_xlsx', 'XLSX'),
        ):
            with self.subTest(formato=formato):
                orden = []
                def generar(reporte):
                    self.assertIs(reporte, self.reporte)
                    orden.append('generar')
                    return b'archivo'
                def auditar(*args, **kwargs):
                    orden.append('auditar')
                request = self.peticion()
                with patch('apps.gestion_unidades.presentation.gestion.get_object_or_404', return_value=self.unidad), \
                     patch('apps.gestion_unidades.presentation.gestion.puede_operar_modulo_unidad', return_value=True), \
                     patch('apps.gestion_unidades.presentation.gestion.build_unit_report', return_value=self.reporte), \
                     patch('apps.gestion_unidades.presentation.gestion.' + renderer, side_effect=generar), \
                     patch('apps.gestion_unidades.presentation.gestion.registrar_auditoria', side_effect=auditar) as registro:
                    respuesta = vista(request, self.unidad.slug)
                self.assertEqual(respuesta.content, b'archivo')
                self.assertEqual(orden, ['generar', 'auditar'])
                registro.assert_called_once_with(request, unidad=self.unidad, accion='descargar',
                    objeto=self.unidad, descripcion=f'{formato}: Formación')

    def test_falla_en_renderizador_dedicado_no_deja_descarga_exitosa(self):
        for vista, renderer in ((gestion_reporte_unidad_pdf_view, 'render_unit_report_pdf'),
                                (gestion_reporte_unidad_xlsx_view, 'render_unit_report_xlsx')):
            with self.subTest(ruta=vista.__name__):
                with patch('apps.gestion_unidades.presentation.gestion.get_object_or_404', return_value=self.unidad), \
                     patch('apps.gestion_unidades.presentation.gestion.puede_operar_modulo_unidad', return_value=True), \
                     patch('apps.gestion_unidades.presentation.gestion.build_unit_report', return_value=self.reporte), \
                     patch('apps.gestion_unidades.presentation.gestion.' + renderer, side_effect=ValueError('Fallo de render')), \
                     patch('apps.gestion_unidades.presentation.gestion.registrar_auditoria') as registro:
                    with self.assertRaisesMessage(ValueError, 'Fallo de render'):
                        vista(self.peticion(), self.unidad.slug)
                registro.assert_not_called()
