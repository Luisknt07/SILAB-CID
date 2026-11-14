"""Un solo dataset de capacidad para pantalla, filtros y exportaciones."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace as Dato
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.gestion_unidades.presentation.reportes_capacidad import _seleccionar_presupuesto, reporte_capacidad


class ReportesCapacidadTests(SimpleTestCase):
    inicio, fin, hoy = date(2026, 7, 1), date(2026, 12, 31), date(2026, 10, 18)

    def setUp(self):
        self.unidad = Dato(pk=9, slug='capacidad-reporte-qa')
        self.origen = dict(documento=None, presupuesto=None)
        def medida(pendiente, referencia):
            return dict(theoretical_hours=10, occupied_hours=4, theoretical_person_hours=40,
                actual_person_hours=8, frequency=40, occupancy=50, utilization=20,
                pending=pendiente, frequency_pending=pendiente, utilization_pending=pendiente,
                measured_until=self.hoy, fuentes=dict(horarios=[1], capacidades=[2], bloqueos=[],
                    calendarios=[], atenciones=[referencia]),
                alertas=[dict(codigo='cierre_incompleto', mensaje='Asistencia real pendiente.',
                    cantidad=1, registros=[referencia])] if pendiente else [])
        self.seguimiento = dict(
            meses=[dict(inicio=date(2026, 7, 1), fin=date(2026, 7, 31), etiqueta='07/2026',
                        medida=medida(False, 21), presupuesto=None),
                   dict(inicio=date(2026, 8, 1), fin=date(2026, 8, 31), etiqueta='08/2026',
                        medida=medida(True, 22), presupuesto=None)],
            semanas=[dict(inicio=date(2026, 7, 1), fin=date(2026, 7, 5), etiqueta='01/07 – 05/07',
                          medida=medida(False, 21), presupuesto=None),
                     dict(inicio=date(2026, 8, 3), fin=date(2026, 8, 9), etiqueta='03/08 – 09/08',
                          medida=medida(True, 22), presupuesto=None)],
            presupuesto=dict(alertas=[]))

    def construir(self, **kwargs):
        with patch('apps.gestion_unidades.presentation.reportes_capacidad._presupuesto_del_tramo',
                   return_value=self.origen), patch(
                   'apps.gestion_unidades.presentation.reportes_capacidad.seguimiento_uso_unidad',
                   return_value=deepcopy(self.seguimiento)) as medir, patch(
                   'apps.gestion_unidades.presentation.reportes_capacidad.timezone.localdate', return_value=self.hoy):
            datos = reporte_capacidad(self.unidad, self.inicio, self.fin, **kwargs)
        self.ultima_llamada = medir.call_args
        return datos

    def documento(self, *, unidad=9, inicio=None, fin=None, pk=11, marco='gestion_v1', estado='validado'):
        return Dato(pk=pk, unidad_id=unidad, anio=2026, corte='B', version=2, marco_periodo=marco,
            tramo_inicio=inicio or self.inicio, tramo_fin=fin or self.fin, estado=estado)

    def test_dataset_completo_con_columnas_y_limites_comunes_a_las_exportaciones(self):
        datos = self.construir()
        self.assertEqual(datos['column_count'], len(datos['headers']))
        self.assertTrue(all(len(f) == len(datos['headers']) for f in datos['rows']))
        self.assertTrue(all(len(f) == len(t['headers']) for t in datos['tablas'] for f in t['rows']))
        self.assertEqual(len(datos['tablas']), 3)
        self.assertFalse(datos['matrix'])
        self.assertFalse(datos['structured'])
        self.assertEqual(datos['supporting_documents'], [])
        self.assertEqual(self.ultima_llamada.kwargs['presupuesto'], None)

    def test_porcentajes_incompletos_no_se_exportan_como_cumplimiento(self):
        datos = self.construir(state='pendiente')
        self.assertEqual(len(datos['rows']), 1)
        self.assertIn('Agosto', datos['rows'][0][0])
        self.assertEqual(datos['rows'][0][5:8], ['Pendiente'] * 3)
        self.assertEqual(datos['rows'][0][8], 'Sin meta para este tramo')
        self.assertEqual(datos['rows'][0][-1], 'Pendiente de comprobación')
        self.assertEqual(datos['tablas'][1]['rows'][0][3], '22')

    def test_busqueda_y_estado_se_aplican_a_meses_semanas_alertas_y_fuentes(self):
        datos = self.construir(search='julio', state='comprobable')
        self.assertEqual(len(datos['rows']), 1)
        self.assertEqual(len(datos['tablas'][0]['rows']), 1)
        self.assertEqual(datos['tablas'][1]['rows'], [])
        fuentes_atencion = next(f for f in datos['tablas'][2]['rows'] if f[0] == 'Ejecuciones con datos reales')
        self.assertEqual(fuentes_atencion[2], '21')
        self.assertNotIn('22', fuentes_atencion[2])

    def test_busqueda_sin_resultado_no_deja_detalles_de_otro_mes(self):
        datos = self.construir(search='inexistente')
        self.assertEqual(datos['rows'], [])
        self.assertEqual(datos['tablas'][0]['rows'], [])
        self.assertEqual(datos['tablas'][1]['rows'], [])
        self.assertTrue(all(f[1] == 0 for f in datos['tablas'][2]['rows']))

    def test_estado_invalido_no_filtra_silenciosamente_todos_los_resultados(self):
        self.assertEqual(len(self.construir(state='inexistente')['rows']), 2)

    def test_presupuesto_solo_de_la_unidad_y_tramo_exacto_incluso_si_es_legacy(self):
        presupuesto = dict(horas_comprometidas='8', justificacion='Programa de trabajo real.')
        ajeno = Dato(documento=self.documento(unidad=8), contenido=dict(presupuesto_uso=presupuesto))
        otro_tramo = Dato(documento=self.documento(inicio=date(2026, 8, 17)),
            contenido=dict(presupuesto_uso=presupuesto))
        exacto = Dato(documento=self.documento(marco='academico_legacy'),
            contenido=dict(presupuesto_uso=presupuesto))
        seleccion = _seleccionar_presupuesto(self.unidad, self.inicio, self.fin, [ajeno, otro_tramo, exacto])
        self.assertIs(seleccion['documento'], exacto.documento)
        self.assertEqual(seleccion['presupuesto'], presupuesto)
        self.assertIsNone(_seleccionar_presupuesto(self.unidad, self.inicio, self.fin,
            [ajeno, otro_tramo])['presupuesto'])

    def test_presupuesto_con_fechas_propias_de_otro_tramo_no_se_reutiliza(self):
        redaccion = Dato(documento=self.documento(), contenido=dict(presupuesto_uso=dict(
            horas_comprometidas='8', justificacion='Programa', inicio='2026-08-17', fin='2026-12-08')))
        self.assertIsNone(_seleccionar_presupuesto(self.unidad, self.inicio, self.fin,
            [redaccion])['presupuesto'])

    def test_plan_en_edicion_se_identifica_y_su_meta_no_es_aprobacion(self):
        self.origen = dict(documento=self.documento(estado='pendiente'), presupuesto=dict(
            horas_comprometidas='8', justificacion='Propuesta de programación real.'))
        datos = self.construir()
        self.assertEqual(self.ultima_llamada.kwargs['presupuesto']['horas_comprometidas'], '8')
        self.assertTrue(any('propuesta en edición' in n for n in datos['notes']))
        self.assertTrue(any('no otorga por sí sola una calificación' in n for n in datos['notes']))
        self.assertTrue(any(f[0] == 'Planificación del mismo tramo' for f in datos['tablas'][2]['rows']))

    def test_mas_de_cien_semanas_se_recorta_y_se_informa(self):
        semana = self.seguimiento['semanas'][0]
        self.seguimiento['semanas'] = [deepcopy(semana) for _ in range(105)]
        datos = self.construir()
        self.assertTrue(datos['truncated'])
        self.assertEqual(len(datos['tablas'][0]['rows']), 100)
