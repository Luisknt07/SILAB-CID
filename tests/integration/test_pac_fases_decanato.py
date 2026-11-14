"""La remisión conserva fases y la lectura capturada, sin consultas de operación."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.documentos.presentation.necesidades_decanato import (
    _necesidad, render_necesidades_pdf, render_necesidades_xlsx,
)
from apps.documentos.presentation.pac_universitario import ENCABEZADOS_CONSOLIDADO
from tests.integration.test_pac_fases import contenido_fases


def lectura_transferencia(*, gestion=True, resumen=True):
    contenido = contenido_fases(grupo_fases='Renovación digital', fase_numero='2', mes_compra='9',
        resultado_fase='Habilitar diez puestos para prácticas.',
        condicion_siguiente_fase='Verificar las actividades realizadas y el presupuesto disponible.')
    if not gestion:
        contenido.pop('inversion_gestion_version')
    if not resumen:
        contenido.pop('compras_resumen_version')
    unidad = dict(id=1, nombre='Unidad de prueba', dependencia_nombre='Decanato de prueba',
        centro_costo='Centro de prueba', transferible=True, evaluado=True,
        estado_etiqueta='Necesidades evaluadas por Dirección', total='25.00',
        sin_compras_justificacion='', fuente=dict(fecha_evaluacion='2026-05-20', token='Referencia archivada'),
        necesidades=[_necesidad(contenido['compras'][0], 1, incluir_fases=gestion,
            incluir_detalle=True, incluir_resumen=resumen)], pac_datos=contenido)
    if gestion:
        unidad.update(inversion_gestion_version=1, gestion_inversion=dict(
            label='Compromisos por verificar', explicacion='La unidad debe demostrar el aprovechamiento de sus recursos.',
            motivos=['Sin trazas de uso en el semestre cerrado.'], documentacion=dict(al_dia=False),
            justificacion_uso_existente='<p>El área requiere habilitación eléctrica documentada.</p>',
            acciones_cumplimiento=[dict(accion='Habilitar el área y registrar prácticas.', responsable='Responsable de la unidad',
                plazo='2027-02-15', resultado='Diez puestos habilitados y uso registrado.')]))
    return dict(anio_preparacion=2026, anio_compras=2027, unidades=[unidad], alcance='Alcance de prueba',
        resumen=dict(unidades_total=1, con_compras=1, sin_compras=0, pendientes=0))


class FasesDecanatoTests(SimpleTestCase):
    def test_proyeccion_solo_anade_fases_cuando_la_captura_las_admite(self):
        datos = lectura_transferencia()
        fila = datos['unidades'][0]['pac_datos']['compras'][0]
        actual = _necesidad(fila, 1, incluir_fases=True)
        legado = _necesidad(fila, 1)
        self.assertEqual(actual['grupo_fases'], 'Renovación digital')
        self.assertEqual(actual['fase_numero'], '2')
        self.assertNotIn('grupo_fases', legado)

    def test_excel_agrupa_por_clase_y_conserva_fases_en_respaldo_sin_duplicar_importes(self):
        lectura = lectura_transferencia()
        copia = deepcopy(lectura)
        libro = load_workbook(BytesIO(render_necesidades_xlsx(lectura)))
        self.addCleanup(libro.close)
        self.assertEqual(lectura, copia)
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        hoja = libro['Software']
        self.assertEqual((hoja['H6'].value, hoja['H8'].value, libro['Resumen']['F9'].value), (25, 25, 25))
        self.assertEqual((hoja['J6'].value, hoja['K6'].value), ('Septiembre', 2))
        respaldo = hoja['L6'].comment.text
        self.assertIn('Proyecto por fases: Renovación digital', respaldo)
        self.assertIn('Fase: 2', respaldo)
        self.assertIn('Resultado de fase: Habilitar diez puestos', respaldo)
        self.assertIn('Condición de continuidad: Verificar las actividades realizadas', respaldo)
        self.assertNotIn('<p>', respaldo)

    def test_pdf_incluye_sustento_y_programacion_de_fase_sin_releer_fuentes(self):
        with patch('apps.core.reportes.render_reporte', return_value=b'PDF') as render:
            self.assertEqual(render_necesidades_pdf(lectura_transferencia(), marco_pdf={}), b'PDF')
        reporte = render.call_args.args[0]
        texto = str(reporte['sections'])
        self.assertIn('Renovación digital · fase 2', texto)
        self.assertIn('Habilitar diez puestos para prácticas.', texto)
        self.assertIn('Verificar las actividades realizadas', texto)
        self.assertIn('Diez puestos habilitados y uso registrado.', texto)

    def test_remision_anterior_conserva_columnas_y_no_inventa_revision_nueva(self):
        lectura = lectura_transferencia(gestion=False, resumen=False)
        libro = load_workbook(BytesIO(render_necesidades_xlsx(lectura)))
        self.addCleanup(libro.close)
        self.assertEqual(tuple(c.value for c in libro['CONSOLIDADO'][4]), ENCABEZADOS_CONSOLIDADO)
        self.assertEqual(libro['PROGRAMACION'].max_column, 14)
        self.assertNotIn('CUMPLIMIENTO_Y_USO', libro.sheetnames)
        self.assertNotIn('Fase: 2', libro['CONSOLIDADO']['M5'].value)
        with patch('apps.core.reportes.render_reporte', return_value=b'PDF') as render:
            render_necesidades_pdf(lectura, marco_pdf={})
        texto = str(render.call_args.args[0]['sections'])
        self.assertNotIn('Renovación digital', texto)
        self.assertNotIn('cumplimiento y uso para la inversión', texto)

    def test_captura_faltante_no_se_presenta_como_cumplimiento_conocido(self):
        lectura = lectura_transferencia()
        lectura['unidades'][0]['gestion_inversion'] = None
        libro = load_workbook(BytesIO(render_necesidades_xlsx(lectura)))
        self.addCleanup(libro.close)
        self.assertNotIn('CUMPLIMIENTO_Y_USO', libro.sheetnames)
        self.assertNotIn('Al día', str([list(hoja.values) for hoja in libro]))
        with patch('apps.core.reportes.render_reporte', return_value=b'PDF') as render:
            render_necesidades_pdf(lectura, marco_pdf={})
        texto = str(render.call_args.args[0]['sections'])
        self.assertIn('Sin captura verificable', texto)
        self.assertNotIn('Al día', texto)
