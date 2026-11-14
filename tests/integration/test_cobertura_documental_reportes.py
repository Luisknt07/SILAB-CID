"""Los resultados y pendientes se conservan en pantalla y en las exportaciones."""
from io import BytesIO

from django.test import SimpleTestCase, override_settings
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.documentos.presentation.evaluacion_cierre import medir_meta
from apps.documentos.presentation.medicion_metas import registrar_evidencia
from tests.integration.test_reportes_evidencias import BaseDeReportes


class MetasConRespaldoTests(SimpleTestCase):
    def test_reservas_no_sustituyen_resultados_de_investigacion(self):
        fila = dict(codigo='INVESTIGACION', nombre='Resultados', meta='1', registrado=80, contador='resultados_verificados')
        lectura = medir_meta(fila, dict(investigacion_atendida=80, resultados_verificados=0))
        self.assertEqual(lectura['registrado'], 0)
        self.assertEqual(lectura['porcentaje'], 0)

    def test_guia_publicada_sin_respaldo_no_acredita_syllabus(self):
        fila = dict(codigo='GUIAS', nombre='Guías', meta='1', registrado=4, contador='guias')
        lectura = medir_meta(fila, dict(guias_acreditables=0))
        self.assertEqual(lectura['porcentaje'], 0)
        self.assertEqual(lectura['faltante'], 1)

    def test_transferencia_legacy_sin_aceptacion_no_suma(self):
        fila = dict(codigo='TRANSFERENCIA', nombre='Transferencia', meta='1', registrado=3, contador='gestion_transferencia')
        lectura = medir_meta(fila, dict(gestion_transferencia=3, transferencias_verificadas=0))
        self.assertEqual(lectura['porcentaje'], 0)


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class ExportacionesDocumentalesTests(BaseDeReportes):
    def resultado(self):
        return registrar_evidencia(self.unidad, self.coordinador, dict(tipo='INVESTIGACION',
            codigo='INV-PRODUCTO-1', fecha=self.desde, titulo='Validación de un prototipo',
            descripcion='Ensayo de resistencia y conclusiones del prototipo.', responsable=self.coordinador,
            enlace='https://example.org/informe-prototipo',
            detalle=dict(proyecto='Proyecto materiales', tipo_producto='prototipo', producto='Prototipo validado',
                         beneficiario='Comunidad universitaria')), verificar=True)

    def test_producto_verificado_se_distingue_del_uso_y_se_exporta_completo(self):
        self.resultado()
        self.reserva(codigo_reserva='SOLO-USO-1', proposito_codigo='investigacion_innovacion')
        pagina = self.reporte('investigacion')
        self.assertContains(pagina, 'Prototipo validado')
        self.assertContains(pagina, 'SOLO-USO-1')
        datos = pagina.context['reporte_gestion']['dataset']
        self.assertEqual(len(datos['rows']), 1)
        self.assertEqual(datos['cards'][1][1], 1)
        self.assertContains(pagina, 'Ver respaldo')
        pdf = self.reporte('investigacion', 'pdf')
        texto = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
        self.assertIn('Prototipo validado', texto)
        self.assertIn('SOLO-USO-1', texto)
        self.assertIn('no acreditan un producto', texto)
        libro = load_workbook(BytesIO(self.reporte('investigacion', 'xlsx').content), read_only=True)
        textos = [' '.join(str(v or '') for v in fila) for hoja in libro for fila in hoja.values]
        self.assertTrue(any('Prototipo validado' in f for f in textos))
        self.assertTrue(any('SOLO-USO-1' in f for f in textos))
        self.assertTrue(any('no acreditan un producto' in f for f in textos))

    def test_informe_sin_resultados_no_convierte_reservas_en_productos(self):
        self.reserva(codigo_reserva='USO-SIN-PRODUCTO', proposito_codigo='investigacion_innovacion')
        pagina = self.reporte('investigacion')
        datos = pagina.context['reporte_gestion']['dataset']
        self.assertEqual(datos['rows'], [])
        self.assertEqual(datos['cards'][1][1], 0)
        self.assertContains(pagina, 'USO-SIN-PRODUCTO')

    def test_filtro_verificados_excluye_respaldo_alterado(self):
        evidencia = self.resultado()
        evidencia.detalle['producto'] = 'Otro producto sin verificación'
        type(evidencia).objects.filter(pk=evidencia.pk).update(detalle=evidencia.detalle)
        vigentes = self.reporte('investigacion', estado='validado').context['reporte_gestion']['dataset']
        pendientes = self.reporte('investigacion', estado='pendiente').context['reporte_gestion']['dataset']
        self.assertEqual(vigentes['rows'], [])
        self.assertEqual(len(pendientes['rows']), 1)
        self.assertEqual(pendientes['cards'][1][1], 0)

    def test_pendientes_de_planificacion_no_se_pierden_en_excel(self):
        from apps.formacion.models.practicas import PlanificacionPractica
        from datetime import time
        PlanificacionPractica.objects.create(codigo='PLAN-INCOMPLETO', unidad=self.unidad, fecha=self.desde,
            hora_inicio=time(9), hora_fin=time(10), asignatura='Materiales', docente_tutor='Docente',
            tema='Ensayo', resultado_aprendizaje='Evalúa materiales', creado_por=self.coordinador)
        pagina = self.reporte('planificaciones')
        self.assertContains(pagina, 'Pendientes por completar')
        libro = load_workbook(BytesIO(self.reporte('planificaciones', 'xlsx').content), read_only=True)
        self.assertTrue(any('Comprobación del respaldo' in s for s in libro.sheetnames))
        texto = '\n'.join(' '.join(str(v or '') for v in fila) for hoja in libro for fila in hoja.values)
        self.assertIn('Responsable técnico', texto)
