"""Las horas del cierre requieren fuentes congelables, calidad y tramo propios."""
from datetime import date, time
from copy import deepcopy
import json
from types import SimpleNamespace as Dato
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.documentos.presentation.evaluacion_cierre import (
    detalle_anexo, evaluar_meta, huella_medicion,
)
from apps.documentos.presentation.expediente_redaccion import filas_de_cumplimiento, planificacion_del_periodo
from apps.recursos.presentation.seguimiento_uso import seguimiento_uso_unidad


class CierrePresupuestoUsoTests(SimpleTestCase):
    fecha, hoy = date(2026, 9, 7), date(2026, 9, 30)

    def setUp(self):
        self.unidad = Dato(pk=7, codigo_base='laboratorios', fecha_inicio=date(2020, 1, 1))
        self.presupuesto = dict(version=1, horas_comprometidas='1.5', horas_por_mes={'9': '1.5'},
            justificacion='Práctica programada con recursos disponibles y responsable técnico.')
        reserva = Dato(pk=20, fecha=self.fecha, hora_inicio=time(9), hora_fin=time(11), estado='completada',
            es_efectiva=True, tipo_solicitud='recursos', detalle_ejecucion=dict(
                registrada_en='2026-09-07T12:00:00-05:00', horario_real=dict(inicio='09:00', fin='10:15'),
                asistentes_total=2))
        self.contexto = dict(unit_id=7, inicio=self.fecha, fin=self.fecha, periodo=None,
            horarios=[Dato(pk=1, periodo_id=None, dia_semana=0, hora_inicio=time(9), hora_fin=time(12),
                permite_recursos=True, permite_servicios=True)],
            capacidades=[Dato(pk=2, periodo_id=None, vigente_desde=date(2026, 1, 1), vigente_hasta=None,
                capacidad_efectiva=4, fuente='Acta técnica de aforo y puestos', factor_limitante='Equipos')],
            calendarios=[], bloqueos=[], reservas=[reserva], equipo_total=1, equipo_disponible=1)
        self.fila = dict(codigo='USO-EFECTIVO', nombre='Uso efectivo', contador='horas_uso_efectivo',
            meta='1.5', aplica=True, obligatoria=True, definida=True, politica_metas=3, registrado=1.25)

    def seguimiento(self):
        return seguimiento_uso_unidad(self.unidad, self.fecha, self.fecha,
            presupuesto=self.presupuesto, hoy=self.hoy, context=self.contexto)

    def registros(self):
        seguimiento = self.seguimiento()
        return dict(seguimiento_uso=seguimiento, horas_uso_efectivo=seguimiento['semestre']['occupied_hours'],
            fuentes_gestion={'USO-EFECTIVO': [seguimiento['semestre']['fuentes_medicion']]})

    def lectura(self, registros=None):
        return evaluar_meta(self.fila, registros if registros is not None else self.registros())

    def congelable(self):
        return dict(catalogo=[self.lectura()], plan=dict(documento=4, version=1, recurso=8),
            plan_aprobado=True, completo=True, demostracion=False)

    def documento(self, *, pk=10, marco='gestion_v1', inicio=None, fin=None):
        return Dato(pk=pk, unidad=self.unidad, unidad_id=7, anio=2026, corte='B', marco_periodo=marco,
            tramo_inicio=inicio or self.fecha, tramo_fin=fin or self.fecha, recurso_id=8,
            version=1, firma_verificada=True, estado='validado', cumple=True)

    def test_horas_parciales_con_fuentes_validas_conservan_faltante_decimal(self):
        lectura = self.lectura()
        self.assertEqual(lectura['porcentaje'], 83.33)
        self.assertEqual(lectura['faltante'], 0.25)
        self.assertFalse(lectura['pendiente'])
        self.assertTrue(lectura['fuentes'][0]['huella_sha256'])

    def test_contador_sin_respaldo_no_acredita_aunque_igualase_la_meta(self):
        lectura = self.lectura(dict(horas_uso_efectivo=1.5))
        self.assertTrue(lectura['pendiente'])
        self.assertEqual(lectura['porcentaje'], 0)
        self.assertEqual(lectura['fuentes'], [])

    def test_alerta_calidad_o_programacion_invalida_no_se_convierten_en_cien(self):
        for ambito, clave in [('semestre', 'pending'), ('presupuesto', 'definido')]:
            registros = self.registros()
            registros['horas_uso_efectivo'] = 1.5
            registros['seguimiento_uso'][ambito][clave] = ambito == 'semestre'
            lectura = self.lectura(registros)
            self.assertTrue(lectura['pendiente'])
            self.assertEqual(lectura['porcentaje'], 0)

    def test_cambiar_horario_sin_cambiar_horas_invalida_la_huella_preparada(self):
        antes = self.congelable()
        self.contexto['reservas'][0].detalle_ejecucion['horario_real'] = dict(inicio='09:30', fin='10:45')
        despues = self.congelable()
        self.assertEqual(antes['catalogo'][0]['porcentaje'], despues['catalogo'][0]['porcentaje'])
        self.assertNotEqual(huella_medicion(antes), huella_medicion(despues))

    def test_cambiar_capacidad_o_jornada_aunque_horas_sean_iguales_cambia_la_huella(self):
        antes = self.congelable()
        self.contexto['capacidades'][0].capacidad_efectiva = 5
        despues = self.congelable()
        self.assertEqual(antes['catalogo'][0]['porcentaje'], despues['catalogo'][0]['porcentaje'])
        self.assertNotEqual(huella_medicion(antes), huella_medicion(despues))
        self.contexto['horarios'][0].hora_fin = time(13)
        self.assertNotEqual(huella_medicion(despues), huella_medicion(self.congelable()))

    def test_fuente_modificada_sin_actualizar_huella_queda_pendiente(self):
        registros = self.registros()
        registros['fuentes_gestion']['USO-EFECTIVO'][0]['capacidades'][0]['capacidad'] = 50
        lectura = self.lectura(registros)
        self.assertTrue(lectura['pendiente'])
        self.assertEqual(lectura['fuentes'], [])

    def test_fuente_valida_de_otra_unidad_o_contador_distinto_no_sustituyen_la_medicion(self):
        registros = self.registros()
        otra = Dato(pk=8, codigo_base='laboratorios', fecha_inicio=date(2020, 1, 1))
        contexto = deepcopy(self.contexto)
        contexto['unit_id'] = 8
        seguimiento = seguimiento_uso_unidad(otra, self.fecha, self.fecha,
            presupuesto=self.presupuesto, hoy=self.hoy, context=contexto)
        registros['fuentes_gestion']['USO-EFECTIVO'] = [seguimiento['semestre']['fuentes_medicion']]
        lectura = self.lectura(registros)
        self.assertTrue(lectura['pendiente'])
        self.assertEqual(lectura['porcentaje'], 0)
        registros = self.registros()
        registros['horas_uso_efectivo'] = 1.5
        self.assertTrue(self.lectura(registros)['pendiente'])

    def test_fuentes_y_lectura_no_conservan_objetos_de_modelo_ni_fechas_json_invalidas(self):
        fuente = self.seguimiento()['semestre']['fuentes_medicion']
        serializado = json.dumps(fuente, ensure_ascii=False, allow_nan=False)
        self.assertIn('2026-09-07', serializado)
        self.assertEqual(json.loads(json.dumps(self.congelable(), allow_nan=False)), self.congelable())

    def test_cumplimiento_incluye_fuentes_uso_en_catalogo_y_anexo_de_registro(self):
        plan = Dato(documento=self.documento(pk=4), contenido=dict(presupuesto_uso=self.presupuesto))
        with (patch('apps.documentos.presentation.expediente_redaccion.planificacion_del_periodo', return_value=plan),
                patch('apps.documentos.presentation.expediente_redaccion.filas_del_plan', return_value=[self.fila]),
                patch('apps.recursos.presentation.seguimiento_uso.seguimiento_uso_unidad', return_value=self.seguimiento())):
            cumplimiento = filas_de_cumplimiento(self.documento(), {}, self.fecha, self.fecha, registros={})
        fila = evaluar_meta(cumplimiento['filas'][0], cumplimiento['registros'])
        self.assertEqual(fila['porcentaje'], 83.33)
        detalle = detalle_anexo('REGISTRO-USO', dict(catalogo=[fila], politica_metas=3))
        uso = next(f for f in detalle if f['codigo'] == 'USO-EFECTIVO')
        self.assertEqual(uso['fuentes'], fila['fuentes'])

    def test_plan_de_otro_marco_o_tramo_no_se_usa_para_el_cierre(self):
        documento = self.documento()
        ajeno = Dato(documento=self.documento(pk=4, marco='academico_legacy'), contenido={})
        otro = Dato(documento=self.documento(pk=5, inicio=date(2026, 8, 17)), contenido={})
        propio = Dato(documento=self.documento(pk=6), contenido={})
        with patch('apps.documentos.presentation.expediente_redaccion.DocumentoElaborado.objects') as gestor:
            gestor.filter.return_value.select_related.return_value = [ajeno, otro, propio]
            self.assertIs(planificacion_del_periodo(documento), propio)
