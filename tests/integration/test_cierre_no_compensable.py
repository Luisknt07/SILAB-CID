"""Un promedio documental alto no oculta el resultado insuficiente o pendiente del cierre."""
from datetime import date
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.cumplimiento import _nivel_evaluado
from apps.documentos.presentation.mejora_continua import cumplimiento_del_periodo
from apps.documentos.presentation.progreso_general import evaluacion_operativa, progreso_general


class CierreNoCompensableTests(SimpleTestCase):
    def setUp(self):
        for ruta in ('apps.documentos.models.expediente.minimo_vigente',
                'apps.documentos.presentation.cumplimiento.minimo_vigente',
                'apps.documentos.presentation.mejora_continua.minimo_vigente'):
            parche = patch(ruta, return_value=70)
            parche.start()
            self.addCleanup(parche.stop)
        self.unidad = Unidad(nombre='QA documental y operativo', dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        # Este grupo aísla el cálculo: presupone dos planes ya conformes.
        # La evidencia y autorización de esa conformidad se prueban aparte.
        conformidad = patch('apps.documentos.presentation.conformidad_lectura.lectura_conformidad',
            side_effect=lambda d, **kwargs: dict(estado='conforme', etiqueta='Conforme', fuente='Sistema',
                fecha=None, historica={}) if d.exigido.codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL') else None)
        conformidad.start()
        self.addCleanup(conformidad.stop)

    def documentos(self, nota_cierre):
        documentos = []
        for numero, codigo in enumerate(('RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD',
                'PLANIFICACION', 'PLAN-COMPRAS-ANUAL', 'INFORME-SEMESTRAL'), start=1):
            nota = nota_cierre if codigo == 'INFORME-SEMESTRAL' else 100
            documento = DocumentoExpediente(id=numero, unidad=self.unidad,
                exigido=DocumentoExigido(id=numero, codigo=codigo, nombre=codigo),
                anio=2026, corte='B', version=1, evaluacion=nota, evaluacion_version=1,
                estado='pendiente' if nota is None else 'validado', recurso_id=None if nota is None else 100 + numero)
            documento._control_automatico = None
            documentos.append(documento)
        return documentos

    def nivel(self, documentos, hoy=date(2027, 1, 1), registros=None):
        cortes = {'A': (date(2026, 1, 1), date(2026, 6, 30)),
                  'B': (date(2026, 7, 1), date(2026, 12, 31))}
        with patch('apps.documentos.presentation.expediente.leer_expediente', return_value=documentos), \
                patch('apps.documentos.presentation.expediente.cortes_del_anio', return_value=cortes), \
                patch('apps.documentos.presentation.expediente_redaccion.registros_del_periodo',
                    return_value=registros if registros is not None else dict(sesiones=1, atendidas=1)), \
                patch('apps.documentos.presentation.cumplimiento._matriz',
                    side_effect=lambda docs, hoy: [dict(documento=d, enviado=d.estado == 'validado',
                        recibido=d.estado == 'validado') for d in docs]):
            return cumplimiento_del_periodo.__wrapped__(self.unidad, 2026, 'B', hoy)

    def test_administrativos_100_y_cierre_cero_conservan_resultado_cero(self):
        documentos = self.documentos(0)
        progreso = progreso_general(documentos)
        self.assertEqual((progreso['porcentaje'], progreso['resultado_porcentaje']), (100, 0))
        self.assertTrue(progreso['evaluacion_operativa']['no_compensable'])
        self.assertFalse(_nivel_evaluado(documentos, date(2026, 10, 1))['cumple'])
        nivel = self.nivel(documentos)
        self.assertEqual(nivel['total'], 0)
        self.assertEqual(nivel['etiqueta'], 'No cumple')
        self.assertTrue(nivel['requiere_mejora'])
        self.assertTrue(nivel['bajo_minimo'])
        self.assertEqual([d.evaluacion for d in documentos], [100, 100, 100, 100, 0])
        html = render_to_string('portal/pages/unidades/gestion/includes/progreso_general.html',
            dict(progreso_general=progreso))
        self.assertIn('Avance operativo acumulado', html)
        self.assertIn('Nota oficial del cierre', html)
        self.assertIn('Sin medición', html)
        self.assertNotIn('<progress ', html)
        self.assertIn('data-resultado-operativo', html)
        self.assertIn('is-no-cumple', html)
        self.assertIn('los documentos administrativos no lo compensan', html)
        self.assertNotIn('Meta alcanzada', html)

    def test_cierre_60_no_se_compensa_con_documentos_administrativos(self):
        documentos = self.documentos(60)
        self.assertEqual(progreso_general(documentos)['resultado_porcentaje'], 60)
        self.assertFalse(_nivel_evaluado(documentos, date(2026, 10, 1))['cumple'])
        self.assertEqual(self.nivel(documentos)['semaforo'], 'no_cumple')

    def test_cierre_pendiente_conserva_buen_avance_documental_sin_inventar_incumplimiento_evaluado(self):
        documentos = self.documentos(None)
        progreso = progreso_general(documentos)
        self.assertEqual(progreso['porcentaje'], 50)
        self.assertIsNone(progreso['resultado_porcentaje'])
        self.assertTrue(progreso['evaluacion_operativa']['pendiente'])
        self.assertFalse(progreso['evaluacion_operativa']['no_compensable'])
        self.assertIsNone(_nivel_evaluado(documentos, date(2026, 10, 1))['cumple'])
        nivel = self.nivel(documentos)
        self.assertEqual(nivel['etiqueta'], 'Sin cierre operativo evaluado')
        self.assertFalse(nivel['requiere_mejora'])

    def test_cierre_acreditado_al_minimo_si_permite_cumplimiento(self):
        documentos = self.documentos(70)
        self.assertEqual(progreso_general(documentos)['resultado_porcentaje'], 70)
        self.assertTrue(_nivel_evaluado(documentos, date(2026, 10, 1))['cumple'])
        self.assertEqual(self.nivel(documentos)['semaforo'], 'cumple')

    def test_anual_no_compensa_un_cierre_60_con_el_otro_de_100(self):
        documentos = self.documentos(60)
        otro = self.documentos(100)[-1]
        otro.pk, otro.corte = 6, 'A'
        plan_a = self.documentos(100)[2]
        plan_a.pk, plan_a.corte = 7, 'A'
        progreso = progreso_general([*documentos, plan_a, otro])
        self.assertTrue(progreso['evaluacion_operativa']['no_compensable'])
        self.assertEqual(progreso['evaluacion_operativa']['nota_minima'], 60)

    def test_correspondencia_pendiente_no_se_presenta_como_cierre_evaluado_en_cero(self):
        documento = self.documentos(90)[-1]
        operativo = evaluacion_operativa([dict(documento=documento, nota=90,
            nota_acreditable=0, correspondencia_pendiente=True),
            dict(documento=self.documentos(90)[2], conformidad=dict(estado='conforme'))], minimo=70)
        self.assertTrue(operativo['pendiente'])
        self.assertFalse(operativo['no_compensable'])
        self.assertIsNone(operativo['nota_minima'])

    def test_nota_documental_alta_no_sustituye_metas_bajas_ya_archivadas_en_la_misma_version(self):
        documento = self.documentos(100)[-1]
        documento.recurso_id = 12
        documento.automatizacion = dict(vigente=True, resumen=dict(cierre=dict(
            version=documento.version, recurso=12, nota=0)))
        operativo = evaluacion_operativa([dict(documento=documento, nota=100,
            nota_acreditable=100, correspondencia_pendiente=False),
            dict(documento=self.documentos(100)[2], conformidad=dict(estado='conforme'))], minimo=70)
        self.assertTrue(operativo['no_compensable'])
        self.assertEqual(operativo['nota_minima'], 0)
        self.assertEqual(documento.evaluacion, 100)
        documento.automatizacion['vigente'] = False
        self.assertFalse(evaluacion_operativa([dict(documento=documento)], minimo=70)['no_compensable'])

    def test_sin_uso_a_mitad_de_semestre_es_alerta_sin_dictamen_obligatorio(self):
        datos = self.nivel(self.documentos(None), hoy=date(2026, 10, 1), registros=dict(sesiones=0, atendidas=0))
        self.assertTrue(datos['alerta_sin_uso'])
        self.assertFalse(datos['requiere_mejora'])
        self.assertIsNone(datos['total'])

    def test_sin_uso_al_cierre_exige_unidad_existente_todo_el_ciclo(self):
        datos = self.nivel(self.documentos(80), registros=dict(sesiones=0, atendidas=0))
        self.assertTrue(datos['sin_uso_al_cierre'])
        self.assertTrue(datos['requiere_mejora'])
        self.unidad.fecha_inicio = date(2026, 11, 1)
        datos = self.nivel(self.documentos(80), registros=dict(sesiones=0, atendidas=0))
        self.assertTrue(datos['alerta_sin_uso'])
        self.assertFalse(datos['requiere_mejora'])

    def test_ausencia_de_informe_no_oculta_sin_uso_al_final_ni_inventa_nota_cero(self):
        datos = self.nivel(self.documentos(None), registros=dict(sesiones=0, atendidas=0))
        self.assertTrue(datos['sin_uso_al_cierre'])
        self.assertTrue(datos['requiere_mejora'])
        self.assertIsNone(datos['total'])
        self.assertFalse(datos['bajo_minimo'])
        self.assertEqual(datos['semaforo'], 'sin_uso')
        self.unidad.fecha_inicio = None
        datos = self.nivel(self.documentos(None), registros=dict(sesiones=0, atendidas=0))
        self.assertFalse(datos['requiere_mejora'])
        self.assertTrue(datos['alerta_sin_uso'])

    def test_reservas_sin_atencion_no_simulan_uso_y_productos_reales_si_son_actividad(self):
        datos = self.nivel(self.documentos(80), registros=dict(sesiones=5, atendidas=0))
        self.assertTrue(datos['sin_uso'])
        datos = self.nivel(self.documentos(80), registros=dict(sesiones=0, atendidas=0, resultados_reales=1))
        self.assertFalse(datos['sin_uso'])
        self.assertFalse(datos['requiere_mejora'])

    def test_nota_historica_no_supera_un_snapshot_vigente_incompleto(self):
        documentos = self.documentos(100)
        cierre = documentos[-1]
        cierre.automatizacion = dict(vigente=True, resumen=dict(cierre=dict(
            version=cierre.version, recurso=cierre.recurso_id, nota=100, completo=False)))
        datos = progreso_general(documentos)
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(cierre.evaluacion, 100)
        self.assertFalse(datos['evaluacion_operativa']['no_compensable'])

    def test_cierre_no_se_acredita_con_plan_de_otra_unidad_o_alcance_conservado(self):
        cambios = (('unidad_id', 2), ('anio', 2025), ('corte', 'A'),
                   ('marco_periodo', 'academico_legacy'), ('tramo_inicio', date(2026, 8, 17)),
                   ('tramo_fin', date(2026, 12, 8)))
        for campo, valor in cambios:
            with self.subTest(campo=campo):
                documentos = self.documentos(90)
                plan, cierre = documentos[2], documentos[-1]
                for documento in (plan, cierre):
                    documento.unidad_id = 1
                    documento.tramo_inicio, documento.tramo_fin = date(2026, 7, 1), date(2026, 12, 31)
                setattr(plan, campo, valor)
                operativo = evaluacion_operativa([
                    dict(documento=plan, conformidad=dict(estado='conforme')),
                    dict(documento=cierre, nota=90, acreditable=True)], minimo=70)
                self.assertTrue(operativo['pendiente'])
                self.assertEqual(operativo['planes_pendientes'], 1)
                self.assertIsNone(operativo['nota'])
                self.assertFalse(operativo['cierres'][0]['plan_conforme'])
                self.assertEqual(cierre.evaluacion, 90)

    def test_cierre_compatible_acredita_gestion_o_antecedente_en_su_propio_alcance(self):
        for marco, inicio, fin in (
                ('gestion_v1', date(2026, 7, 1), date(2026, 12, 31)),
                ('academico_legacy', date(2026, 8, 17), date(2026, 12, 8))):
            with self.subTest(marco=marco):
                documentos = self.documentos(90)
                plan, cierre = documentos[2], documentos[-1]
                for documento in (plan, cierre):
                    documento.unidad_id = 1
                    documento.marco_periodo = marco
                    documento.tramo_inicio, documento.tramo_fin = inicio, fin
                operativo = evaluacion_operativa([
                    dict(documento=plan, conformidad=dict(estado='conforme')),
                    dict(documento=cierre, nota=90, acreditable=True)], minimo=70)
                self.assertFalse(operativo['pendiente'])
                self.assertEqual(operativo['nota'], 90)
                self.assertEqual(operativo['planes_pendientes'], 0)
