"""Períodos y ayuda del panel: cambiar la vista no inventa metas ni ejecución."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import get_template, render_to_string
from django.test import SimpleTestCase

from apps.documentos.templatetags.seguimiento_indicadores import ficha_meta_conservada
from apps.gestion_unidades.presentation.seguimiento_uso_panel import (
    contexto_seguimiento_uso, rango_seguimiento,
)


class SeguimientoUsoInterfazTests(SimpleTestCase):
    hoy = date(2026, 10, 18)
    unidad = SimpleNamespace(pk=11, slug='fablab', codigo_base='laboratorios')

    def plan(self, **cambios):
        plan = dict(documento=SimpleNamespace(pk=3, estado='pendiente'), legado=False,
            contenido={}, presupuesto=dict(horas_por_mes={'7': '5', '10': '10', '12': '20'},
                horas_comprometidas='35', justificacion='Actividad docente y servicios previstos.'))
        plan.update(cambios)
        return plan

    def lectura(self, **cambios):
        medida = dict(theoretical_hours=100, occupied_hours=8, theoretical_person_hours=1000,
            actual_person_hours=80, planned_hours=12, frequency=8, utilization=8, occupancy=100,
            frequency_pending=False, utilization_pending=False, pending=False,
            daily=[dict(fecha=self.hoy, medido=True, jornada_conocida=True,
                capacidad_conocida=True, capacidad_respaldada=True, disponible_segundos=3600)])
        fila = dict(inicio=date(2026, 10, 1), fin=date(2026, 10, 31), etiqueta='10/2026',
            medida=deepcopy(medida), presupuesto=None)
        lectura = dict(semestre=medida, fuentes=dict(horarios=[1, 2], capacidades=[3]),
            semanas=[deepcopy(fila)], meses=[deepcopy(fila), dict(fila, inicio=date(2026, 11, 1))],
            alertas=[], presupuesto=dict(definido=False, cumplimiento=None))
        lectura.update(cambios)
        return lectura

    def contexto(self, seleccion, *, plan=None, lectura=None):
        with patch('apps.gestion_unidades.presentation.seguimiento_uso_panel._plan_para_seguimiento',
                   return_value=plan or self.plan()), patch(
                   'apps.recursos.presentation.seguimiento_uso.seguimiento_uso_unidad',
                   return_value=lectura or self.lectura()) as servicio:
            contexto = contexto_seguimiento_uso(self.unidad, self.hoy,
                parametros=dict(seguimiento=seleccion, modal='1', fragment='1'))
        return contexto, servicio.call_args

    def test_selector_usa_tramos_naturales_hasta_hoy_y_valida_opciones(self):
        esperados = {'semana': date(2026, 10, 12), 'mes': date(2026, 10, 1),
                     'semestre': date(2026, 7, 1), 'anio': date(2026, 1, 1)}
        for seleccion, inicio in esperados.items():
            with self.subTest(seleccion=seleccion):
                self.assertEqual(rango_seguimiento(dict(seguimiento=seleccion), self.hoy),
                                 (seleccion, inicio, self.hoy))
        self.assertEqual(rango_seguimiento(dict(seguimiento='inventado'), self.hoy)[0], 'semestre')
        self.assertEqual(rango_seguimiento({}, date(2027, 1, 1))[1], date(2027, 1, 1))

    def test_semestre_conserva_meta_completa_pero_no_muestra_series_futuras(self):
        contexto, llamada = self.contexto('semestre')
        self.assertEqual(llamada.args, (self.unidad, date(2026, 7, 1), date(2026, 12, 31)))
        self.assertEqual(llamada.kwargs['presupuesto']['horas_por_mes']['12'], '20')
        self.assertEqual(llamada.kwargs['hoy'], self.hoy)
        self.assertEqual(contexto['fin'], self.hoy)
        self.assertEqual(len(contexto['serie']), 1)
        self.assertEqual(contexto['serie'][0]['fin_corte'], self.hoy)
        self.assertTrue(all('modal=1' in opcion['url'] for opcion in contexto['opciones']))
        self.assertIn('Definir', self.contexto('semestre', plan=self.plan(documento=None))[0]['acciones'][0]['etiqueta'])

    def test_mes_solo_toma_compromiso_mensual_explicito(self):
        _, llamada = self.contexto('mes')
        self.assertEqual(llamada.args[-1], date(2026, 10, 31))
        self.assertEqual(llamada.kwargs['presupuesto']['horas_comprometidas'], '10')
        self.assertEqual(llamada.kwargs['presupuesto']['horas_por_mes'], {'10': '10'})
        _, sin_distribucion = self.contexto('mes', plan=self.plan(presupuesto={
            'horas_comprometidas': '35', 'justificacion': 'Total sin distribución.'}))
        self.assertIsNone(sin_distribucion.kwargs['presupuesto'])

    def test_semana_y_anio_no_prorratean_la_meta_del_semestre(self):
        for seleccion in ('semana', 'anio'):
            with self.subTest(seleccion=seleccion):
                contexto, llamada = self.contexto(seleccion)
                self.assertIsNone(llamada.kwargs['presupuesto'])
                if seleccion == 'anio':
                    self.assertTrue(any('anual' in aviso for aviso in contexto['avisos_panel']))

    def test_panel_muestra_pendiente_sin_porcentajes_falsos_y_con_modal(self):
        lectura = self.lectura()
        lectura['semestre'].update(pending=True, frequency_pending=True,
            utilization_pending=True, frequency=0, utilization=0)
        lectura['alertas'] = [dict(codigo='sin_cierre', mensaje='Hay cierres pendientes.', cantidad=1)]
        contexto, _ = self.contexto('semana', lectura=lectura)
        html = render_to_string('portal/pages/unidades/gestion/includes/seguimiento_uso.html',
                                dict(seguimiento_uso=contexto))
        self.assertIn('Sin cuota semanal', html)
        self.assertIn('Origen y cálculo', html)
        self.assertIn('Hay cierres pendientes.', html)
        self.assertIn('Jornadas declaradas: 2', html)
        self.assertNotIn("&#x27;codigo&#x27;", html)
        self.assertNotIn('0,0 %', html)
        self.assertNotIn('<progress', html)
        self.assertNotIn('<details', html)

    def test_ficha_de_meta_conservada_no_consulta_ni_modifica_medicion(self):
        indicador = dict(codigo='PRACTICAS', nombre='Prácticas ejecutadas',
            indicador='Prácticas con respaldo', meta='6', registrado=1, porcentaje=16.67,
            exigencia='Obligatorio del período', denominador=8)
        conservado = deepcopy(indicador)
        ficha = ficha_meta_conservada(indicador)
        self.assertEqual(indicador, conservado)
        self.assertIn(('Meta conservada', '6'), ficha['pares'])
        self.assertIn(('Universo observado', 8), ficha['pares'])
        self.assertFalse(any('Referencia de 2' in str(v) for _, v in ficha['pares']))

    def test_templates_de_panel_y_meta_compilan(self):
        get_template('portal/pages/unidades/gestion/includes/panel_contenido.html')
        get_template('portal/pages/unidades/gestion/includes/anexo_cierre_fila.html')
        get_template('portal/pages/unidades/gestion/includes/expediente_cuerpo.html')

    def test_cien_por_ciento_informativo_pendiente_no_aparece_acreditado(self):
        contexto, _ = self.contexto('semestre')
        contexto['semestre']['pending'] = True
        contexto['presupuesto'] = dict(definido=True, horas_comprometidas=8,
            cumplimiento=100, pendiente_verificacion=True)
        html = render_to_string('portal/pages/unidades/gestion/includes/seguimiento_uso.html',
                                dict(seguimiento_uso=contexto))
        self.assertIn('Uso efectivo registrado', html)
        self.assertNotIn('Uso real acreditado', html)
        self.assertIn('Provisional · Por verificar', html)
        self.assertIn('class="reporte-progreso is-amarillo"', html)
        self.assertIn('value="100"', html)
        self.assertIn('100 % provisional; por verificar', html)
        self.assertNotIn('class="reporte-progreso is-verde"', html)

    def test_tabla_mantiene_cifra_y_ambar_hasta_verificar_su_mes(self):
        contexto, _ = self.contexto('semestre')
        presupuesto = dict(definido=True, horas_comprometidas=8,
            cumplimiento=100, pendiente_verificacion=True)
        contexto['serie'][0]['presupuesto'] = presupuesto
        template = 'portal/pages/unidades/gestion/includes/seguimiento_uso_tabla.html'
        html = render_to_string(template, dict(seguimiento_uso=contexto))
        self.assertIn('Provisional · Por verificar', html)
        self.assertIn('is-amarillo', html)
        self.assertNotIn('is-verde', html)
        self.assertIn('value="100"', html)
        presupuesto['pendiente_verificacion'] = False
        verificado = render_to_string(template, dict(seguimiento_uso=contexto))
        self.assertIn('is-verde', verificado)
        self.assertNotIn('Provisional · Por verificar', verificado)
