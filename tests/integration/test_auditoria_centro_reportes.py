"""Regresiones de la auditoría: evidencia efectiva y cálculo único de las metas."""
from datetime import time
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from apps.documentos.presentation.expediente_redaccion import actividades_para, registros_del_periodo, veredicto_de_meta
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from tests.integration.test_reportes_evidencias import BaseDeReportes


class EvidenciaEfectivaDelCierreTests(BaseDeReportes):
    def test_meta_ft02_no_acredita_borradores_ni_versiones_sustituidas(self):
        for estado, vigente, eliminado in [('borrador', True, None), ('revision', True, None),
                ('aprobada', False, None), ('aprobada', True, timezone.now()), ('aprobada', True, None)]:
            PlanificacionPractica.objects.create(unidad=self.unidad, fecha=self.desde,
                hora_inicio=time(9), hora_fin=time(10), creado_por=self.coordinador,
                estado=estado, es_version_vigente=vigente, eliminado_en=eliminado)
        registros = registros_del_periodo(self.unidad, self.desde, self.hasta)
        self.assertEqual(registros['practicas_planificadas'], 4)
        self.assertEqual(registros['practicas_planificadas_aprobadas'], 1)
        actividad = next(a for a in actividades_para(self.unidad) if a.codigo == 'PRACTICAS-PLAN')
        self.assertEqual(actividad.contador, 'practicas_planificadas_aprobadas')

    def test_cierre_no_acredita_reservas_completadas_sin_atencion_verificable(self):
        for detalle, resultado in [({}, 'atendida'), (['heredado'], 'atendida'),
                                   ({'registrada_en': '2026-03-04'}, 'no_atendida')]:
            self.reserva(estado='completada', resultado_cierre=resultado,
                         detalle_ejecucion=detalle, proposito_codigo='investigacion_innovacion')
        self.reserva(estado='confirmada', proposito_codigo='investigacion_innovacion')
        self.reserva(estado='completada', resultado_cierre='atendida',
                     proposito_codigo='investigacion_innovacion',
                     detalle_ejecucion={'registrada_en': '2026-03-04',
                                       'horario_real': {'inicio': '09:15', 'fin': '10:45'}})
        cifras = registros_del_periodo(self.unidad, self.desde, self.hasta)
        self.assertEqual(cifras['sesiones'], 5)
        self.assertEqual(cifras['atendidas'], 1)
        self.assertEqual(cifras['investigacion_atendida'], 1)
        self.assertEqual(cifras['horas'], 1.5)

    def test_ejecucion_eliminada_no_aumenta_cumplimiento_del_periodo(self):
        for eliminado in [None, timezone.now()]:
            plan = PlanificacionPractica.objects.create(unidad=self.unidad, fecha=self.desde,
                hora_inicio=time(9), hora_fin=time(10), creado_por=self.coordinador)
            EjecucionPractica.objects.create(planificacion=plan, fecha_ejecucion=self.desde,
                hora_inicio_real=time(9), hora_fin_real=time(10), estado='validada', resultado='ejecutada',
                creado_por=self.coordinador, eliminado_en=eliminado)
        self.assertEqual(registros_del_periodo(self.unidad, self.desde, self.hasta)['practicas'], 1)


class VeredictosConsistentesTests(SimpleTestCase):
    def test_centro_experimental_recibe_actividades_del_codigo_operativo_real(self):
        unidad = SimpleNamespace(codigo_base='centro_experimental')
        codigos = {a.codigo for a in actividades_para(unidad)}
        self.assertTrue({'PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS', 'ENSAYOS', 'DESECHOS'} <= codigos)
        self.assertFalse({'BOLETINES', 'PRODUCCION'} & codigos)

    def test_resumen_de_mantenimiento_usa_solo_programacion_critica(self):
        fila = dict(codigo='MANTENIMIENTO', nombre='Mantenimiento', meta='80 %', registrado=8)
        registros = dict(mantenimientos_programados=10, mantenimientos_criticos_programados=5,
                         mantenimientos_criticos_cumplidos=2)
        self.assertEqual(veredicto_de_meta(fila, registros), 'no_cumple')
        registros['mantenimientos_criticos_cumplidos'] = 4
        self.assertEqual(veredicto_de_meta(fila, registros), 'cumple')
        registros['mantenimientos_criticos_programados'] = 0
        self.assertEqual(veredicto_de_meta(fila, registros), 'sin_medicion')

    def test_inventario_y_reservas_solicitadas_no_autocertifican_el_resumen(self):
        self.assertEqual(veredicto_de_meta(dict(codigo='INVENTARIO', meta='1', registrado=1), {}),
                         'sin_medicion')
        self.assertEqual(veredicto_de_meta(dict(codigo='INVESTIGACION', meta='1', registrado=7),
                                          dict(investigacion_atendida=0)), 'no_cumple')

    def test_resumen_no_interpreta_un_rango_textual_como_meta_alcanzada(self):
        self.assertEqual(veredicto_de_meta(dict(codigo='PRACTICAS', meta='entre 3 y 8', registrado=5), {}),
                         'sin_medicion')
