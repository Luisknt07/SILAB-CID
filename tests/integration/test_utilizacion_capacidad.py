"""Minutos efectivos, capacidad histórica y metas explícitas sin consultas de BD."""
from datetime import date, time
from types import SimpleNamespace as Dato
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.recursos.presentation.seguimiento_uso import normalizar_presupuesto_uso, seguimiento_uso_unidad
from apps.recursos.presentation.utilizacion import calculate_unit_utilization


class UtilizacionCapacidadTests(SimpleTestCase):
    inicio = date(2026, 9, 7)  # lunes
    hoy = date(2026, 9, 30)

    def setUp(self):
        self.unidad = Dato(pk=7, fecha_inicio=date(2020, 1, 1), capacidad_personas=99)
        self.contexto = dict(unit_id=7, inicio=self.inicio, fin=date(2026, 10, 31),
            horarios=[self.jornada(dia=dia) for dia in range(5)],
            capacidades=[self.capacidad()], bloqueos=[], calendarios=[], reservas=[],
            periodo=None, equipo_total=2, equipo_disponible=1)

    def jornada(self, *, dia=0, inicio=time(9), fin=time(11), periodo=None, servicios=True):
        return Dato(pk=dia + 1 + (periodo or 0) * 10, dia_semana=dia, hora_inicio=inicio, hora_fin=fin,
            periodo_id=periodo, permite_recursos=True, permite_servicios=servicios)

    def capacidad(self, *, desde=None, valor=4, pk=1, fuente='Acta de capacidad contrastada QA', periodo=None):
        return Dato(pk=pk, vigente_desde=desde or date(2026, 1, 1), vigente_hasta=None,
            capacidad_efectiva=valor, factor_limitante='Equipos operativos', fuente=fuente, periodo_id=periodo)

    def reserva(self, *, pk=1, fecha=None, inicio='09:00', fin='10:00', personas=2,
                estado='completada', efectiva=True, tipo='recursos', registrada=None):
        detalle = dict(registrada_en=registrada or '2026-09-07T12:00:00-05:00',
            horario_real=dict(inicio=inicio, fin=fin), asistentes_total=personas)
        return Dato(pk=pk, fecha=fecha or self.inicio, hora_inicio=time(9), hora_fin=time(11),
            detalle_ejecucion=detalle, numero_participantes=99, estado=estado, tipo_solicitud=tipo,
            es_efectiva=efectiva)

    def medir(self, inicio=None, fin=None, **opciones):
        return calculate_unit_utilization(self.unidad, inicio or self.inicio, fin or self.inicio,
            context=self.contexto, hoy=opciones.pop('hoy', self.hoy), **opciones)

    def codigos(self, medida):
        return {a['codigo'] for a in medida['alertas']}

    def test_media_hora_no_se_redondea_a_una_hora(self):
        self.contexto['reservas'] = [self.reserva(inicio='09:15', fin='09:45')]
        medida = self.medir()
        self.assertEqual((medida['occupied_hours'], medida['actual_person_hours']), (0.5, 1))
        self.assertEqual((medida['frequency'], medida['occupancy'], medida['utilization']), (25, 50, 12.5))
        self.assertFalse(medida['pending'])
        self.assertEqual(medida['fuentes']['atenciones'], [1])

    def test_solapamiento_no_duplica_horas_y_sobrecupo_no_infla_porcentaje(self):
        self.contexto['capacidades'] = [self.capacidad(valor=3)]
        self.contexto['reservas'] = [self.reserva(), self.reserva(pk=2, inicio='09:30', fin='10:30')]
        medida = self.medir()
        self.assertEqual(medida['occupied_hours'], 1.5)
        self.assertEqual(medida['actual_person_hours'], 3.5)
        self.assertEqual(medida['actual_person_hours_raw'], 4)
        self.assertEqual(medida['sobrecupo_horas'], 0.5)
        self.assertTrue({'sobrecupo', 'atenciones_simultaneas'} <= self.codigos(medida))
        self.assertTrue(medida['pending'])

    def test_cambio_de_capacidad_se_aplica_desde_su_fecha_no_a_todo_el_semestre(self):
        martes = date(2026, 9, 8)
        self.contexto['capacidades'] = [self.capacidad(valor=2), self.capacidad(desde=martes, valor=4, pk=2)]
        self.contexto['reservas'] = [self.reserva(personas=1), self.reserva(pk=2, fecha=martes, personas=1)]
        medida = self.medir(fin=martes)
        self.assertEqual(medida['theoretical_person_hours'], 12)
        self.assertEqual(medida['actual_person_hours'], 2)
        self.assertEqual(medida['utilization'], 16.7)
        self.assertEqual(medida['fuentes']['capacidades'], [1, 2])

    def test_sin_jornada_no_inventa_lunes_a_viernes_o_aforo_publico(self):
        self.contexto['horarios'], self.contexto['capacidades'] = [], []
        medida = self.medir()
        self.assertEqual((medida['theoretical_hours'], medida['capacity']), (0, 0))
        self.assertTrue(medida['pending'])
        self.assertIn('sin_jornada', self.codigos(medida))

    def test_horas_de_uso_pueden_observarse_sin_fingir_aforo_verificado(self):
        self.contexto['capacidades'] = []
        self.contexto['reservas'] = [self.reserva()]
        medida = self.medir()
        self.assertEqual((medida['occupied_hours'], medida['frequency']), (1, 50))
        self.assertEqual(medida['capacity'], 0)
        self.assertTrue(medida['utilization_pending'])
        self.assertFalse(medida['frequency_pending'])
        self.assertIn('sin_capacidad', self.codigos(medida))

    def test_capacidad_sin_referencia_se_muestra_como_pendiente_de_respaldo(self):
        self.contexto['capacidades'] = [self.capacidad(fuente='')]
        self.assertTrue(self.medir()['pending'])
        self.assertIn('capacidad_sin_fuente', self.codigos(self.medir()))

    def test_sin_asistencia_real_no_se_toman_los_99_solicitados(self):
        reserva = self.reserva(personas=None)
        self.contexto['reservas'] = [reserva]
        medida = self.medir()
        self.assertEqual((medida['occupied_hours'], medida['actual_person_hours']), (0, 0))
        self.assertIn('cierre_incompleto', self.codigos(medida))
        self.assertTrue(medida['pending'])

    def test_sin_horario_real_no_se_acredita_el_horario_reservado(self):
        reserva = self.reserva()
        reserva.detalle_ejecucion.pop('horario_real')
        self.contexto['reservas'] = [reserva]
        self.assertEqual(self.medir()['occupied_hours'], 0)

    def test_reserva_confirmada_vencida_no_acredita_ejecucion(self):
        self.contexto['reservas'] = [self.reserva(estado='confirmada', efectiva=False)]
        medida = self.medir()
        self.assertEqual(medida['occupied_hours'], 0)
        self.assertEqual(medida['planned_hours'], 2)
        self.assertIn('sin_cierre', self.codigos(medida))

    def test_futuro_no_entra_en_denominador_ni_ejecucion_actual(self):
        self.contexto['reservas'] = [self.reserva(fecha=date(2026, 9, 8))]
        medida = self.medir(fin=date(2026, 9, 8), hoy=self.inicio)
        self.assertEqual((medida['theoretical_hours'], medida['occupied_hours']), (2, 0))
        self.assertEqual(medida['available_hours_period'], 4)

    def test_cierre_registrado_despues_del_corte_no_reescribe_retroactivamente_medicion(self):
        self.contexto['reservas'] = [self.reserva(registrada='2026-10-01T12:00:00-05:00')]
        self.assertEqual(self.medir()['occupied_hours'], 0)
        self.assertIn('cierre_incompleto', self.codigos(self.medir()))

    def test_jornada_especifica_solo_reemplaza_general_dentro_de_su_periodo(self):
        martes = date(2026, 9, 8)
        self.contexto['calendarios'] = [Dato(pk=100, periodo_id=5, fecha_inicio_clases=martes,
            fecha_fin_periodo=martes, semanas=[])]
        self.contexto['horarios'].append(self.jornada(dia=1, inicio=time(10), fin=time(11), periodo=5))
        medida = self.medir(fin=date(2026, 9, 9))
        self.assertEqual(medida['theoretical_hours'], 5)  # 2 general + 1 específica + 2 general
        self.assertEqual(medida['fuentes']['calendarios'], [100])

    def test_semana_suspendida_publicada_no_ofrece_horas_ficticias(self):
        self.contexto['calendarios'] = [Dato(pk=100, periodo_id=5, fecha_inicio_clases=self.inicio,
            fecha_fin_periodo=date(2026, 9, 9), semanas=[Dato(fecha_inicio=self.inicio,
                fecha_fin=date(2026, 9, 9), permite_reservas=False)])]
        medida = self.medir()
        self.assertEqual(medida['theoretical_hours'], 0)

    def test_bloqueo_de_recursos_no_cierra_servicios_que_siguen_habilitados(self):
        self.contexto['bloqueos'] = [Dato(pk=50, fecha_inicio=self.inicio, fecha_fin=self.inicio,
            dia_completo=False, hora_inicio=time(9), hora_fin=time(10),
            bloquea_recursos=True, bloquea_servicios=False)]
        self.contexto['reservas'] = [self.reserva(), self.reserva(pk=2, tipo='servicio')]
        medida = self.medir()
        self.assertEqual(medida['theoretical_hours'], 2)
        self.assertEqual(medida['actual_person_hours'], 2)  # sólo el servicio habilitado
        self.assertEqual(medida['fuera_jornada_horas'], 1)
        self.assertIn('fuera_jornada', self.codigos(medida))
        self.assertTrue(medida['pending'])

    def test_simultaneidad_identificada_sin_personas_duplicadas_no_castiga_uso_compatible(self):
        reservas = [self.reserva(personas=1), self.reserva(pk=2, personas=1)]
        for numero, reserva in enumerate(reservas, 1):
            reserva.detalle_ejecucion['participantes'] = [dict(usuario_id=numero, asistencia_codigo='asistio')]
        self.contexto['reservas'] = reservas
        medida = self.medir()
        self.assertFalse(medida['pending'])
        self.assertEqual(medida['occupied_hours'], 1)
        reservas[1].detalle_ejecucion['participantes'][0]['usuario_id'] = 1
        self.assertTrue(self.medir()['pending'])
        self.assertIn('personas_duplicadas', self.codigos(self.medir()))

    def test_almuerzo_de_recursos_se_excluye_y_sesiones_fuera_de_jornada_se_advierten(self):
        self.contexto['horarios'] = [self.jornada(inicio=time(12), fin=time(15), servicios=False)]
        self.contexto['reservas'] = [self.reserva(inicio='12:00', fin='15:00')]
        medida = self.medir()
        self.assertEqual((medida['theoretical_hours'], medida['occupied_hours']), (2, 2))
        self.assertEqual(medida['fuera_jornada_horas'], 1)

    def test_no_exige_capacidad_antes_de_apertura_real_de_unidad(self):
        self.unidad.fecha_inicio = date(2026, 9, 8)
        medida = self.medir(fin=date(2026, 9, 8))
        self.assertEqual(medida['theoretical_hours'], 2)
        self.assertEqual([d['fecha'] for d in medida['daily']], [date(2026, 9, 8)])

    def test_precarga_de_otra_unidad_o_tramo_incompleto_se_rechaza(self):
        self.contexto['unit_id'] = 99
        with self.assertRaises(ValueError):
            self.medir()

    def test_seguimiento_reutiliza_precarga_y_suma_duraciones_no_porcentajes(self):
        self.contexto['reservas'] = [self.reserva()]
        with patch('apps.recursos.presentation.seguimiento_uso.precargar_uso_unidad',
                   return_value=self.contexto) as cargar:
            lectura = seguimiento_uso_unidad(self.unidad, self.inicio, date(2026, 10, 10), hoy=self.hoy)
        cargar.assert_called_once()
        self.assertGreater(len(lectura['semanas']), 4)
        self.assertEqual(lectura['semestre']['occupied_hours'], 1)
        self.assertTrue(all(f['presupuesto'] is None for f in lectura['semanas']))

    def test_metas_mensuales_son_explicitas_y_semanas_no_inventan_cuota(self):
        presupuesto = dict(horas_por_mes={'9': '4', '10': '6'}, horas_comprometidas='10',
            justificacion='Demanda programada con personal y equipos disponibles.')
        lectura = seguimiento_uso_unidad(self.unidad, self.inicio, date(2026, 10, 10),
            presupuesto=presupuesto, hoy=self.hoy, context=self.contexto)
        self.assertEqual(lectura['presupuesto']['horas_comprometidas'], '10')
        self.assertEqual([m['meta'] for m in lectura['meses']], ['4', '6'])
        self.assertTrue(all(s['meta'] is None for s in lectura['semanas']))
        self.assertFalse(lectura['presupuesto']['acredita_cumplimiento_institucional'])

    def test_meta_total_heredada_no_se_reparte_en_meses_sin_compromiso(self):
        presupuesto = dict(horas_comprometidas='8', justificacion='Programa total del semestre sin desagregación anterior.')
        lectura = seguimiento_uso_unidad(self.unidad, self.inicio, date(2026, 10, 10),
            presupuesto=presupuesto, hoy=self.hoy, context=self.contexto)
        self.assertTrue(lectura['presupuesto']['definido'])
        self.assertTrue(all(m['presupuesto'] is None for m in lectura['meses']))

    def test_metas_incoherentes_negativas_o_fuera_del_tramo_no_se_acreditan(self):
        for presupuesto in (
                dict(horas_por_mes={'9': '4'}, horas_comprometidas='5', justificacion='Demanda'),
                dict(horas_por_mes={'9': '-1'}, justificacion='Demanda'),
                dict(horas_por_mes={'7': '4'}, justificacion='Demanda'),
                dict(horas_por_mes={'9': 'NaN'}, justificacion='Demanda'),
                dict(horas_comprometidas='4', justificacion='')):
            with self.subTest(presupuesto=presupuesto), self.assertRaises(ValidationError):
                normalizar_presupuesto_uso(presupuesto, self.inicio, date(2026, 10, 10), estricto=True)

    def test_cero_horas_no_da_cien_y_meta_en_curso_no_se_declara_incumplimiento(self):
        for objetivo, estado in [('0', 'Alcance por justificar'), ('8', 'En curso')]:
            lectura = seguimiento_uso_unidad(self.unidad, self.inicio, date(2026, 10, 10),
                presupuesto=dict(horas_comprometidas=objetivo, justificacion='Puesta en marcha y alcance del plan.'),
                hoy=self.hoy, context=self.contexto)
            self.assertEqual(lectura['presupuesto']['estado'], estado)
            if objetivo == '0':
                self.assertIsNone(lectura['presupuesto']['cumplimiento'])
