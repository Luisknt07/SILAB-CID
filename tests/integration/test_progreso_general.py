"""Avance de todas las obligaciones, sin confundirlo con el promedio parcial."""
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.progreso_general import progreso_general
from apps.documentos.presentation.expediente import construir_expediente
from tests.integration.test_cumplimiento_expediente import BaseDeCumplimiento


class ProgresoGeneralTests(SimpleTestCase):
    def setUp(self):
        parche = patch('apps.documentos.models.expediente.minimo_vigente', return_value=70)
        parche.start()
        self.addCleanup(parche.stop)
        def conformidad(d, **kwargs):
            if d.exigido.codigo != 'PLANIFICACION':
                return None
            estado = 'conforme' if d.estado == 'validado' else 'corregir' if d.estado == 'observado' else 'pendiente'
            return dict(estado=estado, etiqueta=estado, fuente='Sistema', historica={})
        parche = patch('apps.documentos.presentation.conformidad_lectura.lectura_conformidad', side_effect=conformidad)
        parche.start()
        self.addCleanup(parche.stop)

    def documento(self, numero, nota=None, codigo=None, **extra):
        exigido = DocumentoExigido(id=numero, codigo=codigo or f'QA-{numero}', nombre=f'Documento {numero}')
        datos = dict(id=numero, exigido=exigido, anio=2026, corte='B', version=1,
                     estado='validado', evaluacion=nota, evaluacion_version=1, recurso_id=900 + numero)
        datos.update(extra)
        d = DocumentoExpediente(**datos)
        d._control_automatico = None
        d._aprobacion_permanente_registro = None
        return d

    def ciclo(self, nota=80, corte='B', offset=0):
        return [self.documento(offset + 1, 100, codigo='PLANIFICACION', corte=corte),
                self.documento(offset + 2, nota, codigo='INFORME-SEMESTRAL', corte=corte)]

    def test_solo_el_cierre_puntua_y_los_administrativos_no_lo_bonifican(self):
        documentos = self.ciclo(80)
        for numero, codigo in enumerate(('RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'PLAN-COMPRAS-ANUAL'), 3):
            d = self.documento(numero, 100, codigo=codigo)
            if numero < 5:
                d.exigido.periodicidad = 'unica'
            documentos.append(d)
        with patch('apps.documentos.presentation.conformidad_permanente.aprobacion_vigente', return_value=dict(vigente=True)):
            datos = progreso_general(documentos)
        self.assertEqual(datos['resultado_porcentaje'], 80)
        self.assertEqual((datos['porcentaje'], datos['total'], datos['completados']), (100, 2, 2))
        self.assertEqual(datos['peso'], 0)
        self.assertEqual(len(datos['sin_ponderacion']), 3)
        self.assertTrue(all(f['aporte'] == f['maximo'] == 0 for f in datos['sin_ponderacion']))
        plan, cierre = datos['desglose']
        self.assertEqual((plan['puntua'], plan['prerrequisito'], plan['aporte']), (False, True, 0))
        self.assertEqual((cierre['aporte'], cierre['maximo']), (80, 100))

    def test_una_resolucion_vigente_no_produce_un_20_por_ciento(self):
        d = self.documento(1, codigo='RESOLUCION-CREACION')
        d.exigido.periodicidad = 'unica'
        with patch('apps.documentos.presentation.conformidad_permanente.aprobacion_vigente', return_value=dict(vigente=True)):
            datos = progreso_general([d])
        self.assertEqual(datos['porcentaje'], 0)
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(datos['sin_ponderacion'][0]['aporte'], 0)

    def test_plan_observado_con_editor_100_no_acredita_el_cierre_ni_cambia_historia(self):
        plan, cierre = self.ciclo(80)
        plan.estado, plan.avance_redaccion = 'observado', 100
        datos = progreso_general([plan, cierre])
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(datos['evaluacion_operativa']['nota_registrada'], 80)
        self.assertEqual(datos['porcentaje'], 0)
        self.assertEqual(datos['desglose'][1]['estado'], 'Planificación pendiente')
        self.assertEqual((plan.evaluacion, cierre.evaluacion, plan.avance_redaccion), (100, 80, 100))

    def test_un_tramite_de_dos_completo_no_es_un_bono_del_50_en_desempeno(self):
        plan, cierre = self.ciclo(None)
        cierre.estado, cierre.recurso_id = 'pendiente', None
        datos = progreso_general([plan, cierre])
        self.assertEqual((datos['porcentaje'], datos['completados']), (50, 1))
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(datos['desglose'][0]['aporte'], 0)

    @patch('apps.documentos.models.expediente.penalizacion_vigente', return_value=20)
    def test_el_ajuste_del_cierre_no_se_promedia_con_el_plan(self, _penalizacion):
        plan, cierre = self.ciclo(100)
        cierre.entregado_tarde = True
        self.assertEqual(progreso_general([plan, cierre])['resultado_porcentaje'], 80)

    def test_cero_provisional_sin_informe_no_es_desempeno_evaluado(self):
        plan, cierre = self.ciclo(0)
        cierre.estado, cierre.recurso_id = 'pendiente', None
        datos = progreso_general([plan, cierre])
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertFalse(datos['evaluacion_operativa']['no_compensable'])
        cierre.estado, cierre.recurso_id = 'validado', 55
        datos = progreso_general([plan, cierre])
        self.assertEqual(datos['resultado_porcentaje'], 0)
        self.assertTrue(datos['evaluacion_operativa']['no_compensable'])

    def test_compras_y_anexos_no_bonifican_ni_castigan_el_desempeno(self):
        compras = self.documento(3, 0, codigo='PLAN-COMPRAS-ANUAL', estado='observado')
        anexo = self.documento(4, 100)
        anexo.exigido.anexo_de_id = 2
        no_aplica = self.documento(5, 0, estado='no_aplica')
        datos = progreso_general([*self.ciclo(80), compras, anexo, anexo, no_aplica])
        self.assertEqual((datos['resultado_porcentaje'], datos['total']), (80, 2))
        self.assertEqual(len(datos['sin_ponderacion']), 3)
        self.assertTrue(all(f['aporte'] == f['maximo'] == 0 for f in datos['sin_ponderacion']))

    def test_anual_conserva_decimales_y_no_publica_promedio_parcial_como_oficial(self):
        documentos = self.ciclo(Decimal('80.25'), 'A') + self.ciclo(Decimal('79.75'), 'B', 2)
        datos = progreso_general([*documentos, documentos[0]])
        self.assertEqual((datos['total'], datos['porcentaje'], datos['resultado_porcentaje']), (4, 100, 80))
        self.assertEqual([f['resultado_porcentaje'] for f in datos['desglose'] if f['puntua']],
                         [Decimal('80.25'), Decimal('79.75')])
        documentos[-1].estado, documentos[-1].recurso_id = 'pendiente', None
        datos = progreso_general(documentos)
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(datos['evaluacion_operativa']['nota_parcial'], Decimal('80.25'))
        self.assertEqual(datos['porcentaje'], 75)

    def test_sin_ciclo_no_inventa_resultado_ni_obligaciones(self):
        datos = progreso_general([])
        self.assertEqual((datos['desglose'], datos['sin_ponderacion'], datos['porcentaje']), ([], [], 0))
        self.assertIsNone(datos['resultado_porcentaje'])


class ProgresoGeneralEnPantallaTests(BaseDeCumplimiento):
    def cierre_evaluado(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from tests.integration.utiles import (
            abrir_entrega, cargar_documento_revisado, recibir_documento_revisado,
            evaluar_documento_revisado, pdf_legible_prueba,
        )
        documentos = construir_expediente(self.laboratorio, 2026)
        plan = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')
        plan.marco_periodo = 'academico_legacy'
        plan.save(update_fields=['marco_periodo'])
        abrir_entrega(plan)
        cargar_documento_revisado(plan, SimpleUploadedFile('plan-qa.pdf', pdf_legible_prueba(firmado=True)),
                                  self.coordinador)
        recibir_documento_revisado(plan, self.direccion)
        # La evaluación queda como antecedente; sin planificación conforme
        # no constituye un resultado operativo acreditado de la unidad.
        evaluar_documento_revisado(plan, self.direccion, 80, 'Resultado del informe revisado.')
        return plan

    def test_direccion_ve_el_mismo_avance_general_que_la_unidad(self):
        self.cierre_evaluado()
        self.client.force_login(self.direccion)
        pagina = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                                 {'anio': 2026, 'corte': 'B', 'unidad': self.laboratorio.slug})
        self.assertContains(pagina, f'id="cumplimiento-general-{self.laboratorio.pk}"')
        self.assertNotContains(pagina, 'No hay documentos obligatorios para este período.')
        fila = next(f for g in pagina.context['grupos'] for f in g['filas']
                    if f['unidad'].pk == self.laboratorio.pk)
        desglose = fila['progreso_general']['desglose']
        self.assertEqual(len(desglose), 2)
        cierre = next(f for f in desglose if f['codigo'] == 'INFORME-SEMESTRAL')
        self.assertEqual((cierre['aporte'], cierre['maximo']), (0, 100))
        self.assertEqual(cierre['estado'], 'Planificación pendiente')
        self.assertIsNone(fila['nivel']['total'])

    def test_la_consola_completa_y_su_fragmento_reciben_la_barra_general(self):
        self.cierre_evaluado()
        self.client.force_login(self.coordinador)
        ruta = reverse('gestion_unidad', args=[self.laboratorio.slug])
        for fragmento in ('', '1'):
            with self.subTest(fragmento=fragmento):
                pagina = self.client.get(ruta, {'view': 'reportes', 'anio': 2026, 'corte': 'B',
                                              'fragment': fragmento, 'modal': '1'})
                self.assertContains(pagina, 'Avance operativo acumulado')
                self.assertContains(pagina, 'Nota oficial del cierre')
                self.assertIsNone(pagina.context['progreso_general']['resultado_porcentaje'])
                self.assertContains(pagina, '<caption>6 documentos obligatorios')
                self.assertNotContains(pagina, 'No hay documentos obligatorios para este período.')

    def test_aportes_barra_y_periodos_se_muestran_sin_cambiar_la_evaluacion(self):
        plan = self.cierre_evaluado()
        self.client.force_login(self.coordinador)
        ruta = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        pagina = self.client.get(ruta, {'anio': 2026, 'corte': 'B'})
        self.assertContains(pagina, 'Avance operativo acumulado')
        self.assertContains(pagina, 'Nota oficial del cierre')
        datos = pagina.context['progreso_general']
        self.assertEqual((datos['total'], datos['porcentaje']), (2, 0))
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(len(datos['desglose']), datos['total'])
        plan.refresh_from_db()
        self.assertEqual(plan.evaluacion, 80)
        anual = self.client.get(ruta, {'anio': 2026, 'corte': ''})
        self.assertEqual(anual.context['progreso_general']['total'], 4)
        self.assertIsNone(anual.context['progreso_general']['resultado_porcentaje'])
        self.assertEqual(len(anual.context['progreso_general']['desglose']), 4)

    def test_obligaciones_previstas_sin_registro_siguen_en_el_denominador(self):
        self.client.force_login(self.coordinador)
        ruta = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        antes = DocumentoExpediente.objects.count()
        pagina = self.client.get(ruta, {'anio': 2027, 'corte': 'B'})
        self.assertEqual(DocumentoExpediente.objects.count(), antes)
        self.assertEqual(pagina.context['progreso_general']['total'], 2)
        self.assertEqual(pagina.context['progreso_general']['porcentaje'], 0)
