"""El compromiso mensual llega al cierre desde fuentes operativas de la unidad."""
from datetime import date, time
import json
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from apps.documentos.models.expediente import (
    DocumentoElaborado, DocumentoExigido, DocumentoExpediente,
)
from apps.documentos.presentation.evaluacion_cierre import evaluar_meta, huella_medicion
from apps.documentos.presentation.expediente_redaccion import metas_del_periodo
from apps.gestion_unidades.models.operaciones import (
    CapacidadOperativaUnidad, HorarioOperacionUnidad,
)
from apps.reservas.models.reservas import Reserva
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class PresupuestoUsoFlujoBDTests(BaseAlcanceReportes):
    inicio, fin, hoy = date(2026, 7, 1), date(2026, 12, 31), date(2026, 10, 18)

    def setUp(self):
        super().setUp()
        self.enterContext(patch('django.utils.timezone.localdate', return_value=self.hoy))
        self.unidad = self.unidades['laboratorios']
        self.plan = self.documentos['laboratorios']
        self.plan.marco_periodo = 'gestion_v1'
        self.plan.tramo_inicio, self.plan.tramo_fin = self.inicio, self.fin
        self.plan.save(update_fields=['marco_periodo', 'tramo_inicio', 'tramo_fin'])

    @staticmethod
    def congelable(lectura):
        return dict(catalogo=[lectura], plan=dict(documento=1, version=1),
                    plan_aprobado=False, completo=False, demostracion=False)

    def test_fuentes_reales_miden_uso_parcial_y_una_anomalia_impide_acreditarlo(self):
        # La unidad inicia con jornadas generales; esta prueba declara una
        # disponibilidad distinta de forma explícita para comprobar el límite.
        HorarioOperacionUnidad.objects.filter(unidad=self.unidad).delete()
        jornada = HorarioOperacionUnidad.objects.create(
            unidad=self.unidad, dia_semana=0, hora_inicio=time(9), hora_fin=time(12),
            permite_recursos=True, permite_servicios=True, activo=True)
        capacidad = CapacidadOperativaUnidad.objects.create(
            unidad=self.unidad, vigente_desde=self.inicio, vigente_hasta=self.fin,
            aforo_seguridad=4, puestos_mobiliario=4, puestos_equipados=4,
            capacidad_personal=4, fuente='Acta técnica de aforo, puestos y personal 2026-07',
            creado_por=self.usuarios['laboratorios'])
        reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.usuarios['laboratorios'],
            fecha=date(2026, 9, 7), hora_inicio=time(9), hora_fin=time(11),
            tipo_solicitud='recursos', equipo_codigo='QA-USO', equipo_nombre='Estación de trabajo',
            estado='completada', resultado_cierre='atendida', detalle_ejecucion=dict(
                registrada_en='2026-09-07T12:00:00-05:00', asistentes_total=2,
                horario_real=dict(inicio='09:00', fin='10:15')))
        DocumentoElaborado.objects.create(documento=self.plan, version=1, contenido=dict(
            firma_nombre='Responsable de la unidad', presupuesto_uso=dict(
                version=1, inicio=self.inicio.isoformat(), fin=self.fin.isoformat(),
                horas_comprometidas='12', horas_por_mes={str(m): '2' for m in range(7, 13)},
                justificacion='Seis sesiones de dos horas con responsable y recursos disponibles.')))
        cierre = DocumentoExpediente.objects.create(
            unidad=self.unidad, exigido=DocumentoExigido.objects.get(codigo='INFORME-SEMESTRAL'),
            anio=2026, corte='B', marco_periodo='gestion_v1',
            tramo_inicio=self.inicio, tramo_fin=self.fin)

        metas = metas_del_periodo(cierre)
        fila = next(f for f in metas['filas'] if f['codigo'] == 'USO-EFECTIVO')
        lectura = evaluar_meta(fila, metas['registros'])
        self.assertTrue(metas['hay_plan'])
        self.assertEqual(lectura['registrado'], 1.25)
        self.assertEqual(lectura['porcentaje'], 10.42)
        self.assertEqual(lectura['faltante'], 10.75)
        self.assertFalse(lectura['pendiente'])
        self.assertEqual(lectura['estado'], 'No cumple')
        fuente = lectura['fuentes'][0]
        self.assertEqual(fuente['unidad'], self.unidad.pk)
        self.assertEqual((fuente['inicio'], fuente['fin'], fuente['corte']),
                         ('2026-07-01', '2026-12-31', '2026-10-18'))
        self.assertEqual([f['id'] for f in fuente['atenciones']], [reserva.pk])
        self.assertIn(jornada.pk, [f['id'] for f in fuente['horarios']])
        self.assertIn(capacidad.pk, [f['id'] for f in fuente['capacidades']])
        self.assertEqual(len(fuente['huella_sha256']), 64)
        huella_preparada = huella_medicion(self.congelable(lectura))
        json.dumps(self.congelable(lectura), allow_nan=False)

        # Conserva la duración y la asistencia, pero parte de la ejecución está
        # fuera de la jornada. El tiempo observado no acredita un cierre conforme.
        reserva.detalle_ejecucion['horario_real'] = dict(inicio='08:00', fin='09:15')
        reserva.save(update_fields=['detalle_ejecucion'])
        nuevas = metas_del_periodo(cierre)
        otra_fila = next(f for f in nuevas['filas'] if f['codigo'] == 'USO-EFECTIVO')
        otra = evaluar_meta(otra_fila, nuevas['registros'])
        self.assertTrue(otra['pendiente'])
        self.assertEqual(otra['porcentaje'], 0)
        self.assertIsNone(otra['registrado'])
        medida = nuevas['registros']['seguimiento_uso']['semestre']
        self.assertTrue(medida['pending'])
        self.assertIn('fuera_jornada', {a['codigo'] for a in medida['alertas']})
        self.assertNotEqual(fuente['huella_sha256'], medida['fuentes_medicion']['huella_sha256'])
        self.assertNotEqual(huella_preparada, huella_medicion(self.congelable(otra)))

    def test_get_del_editor_sin_guardar_muestra_los_seis_meses_del_tramo_de_gestion(self):
        redaccion = DocumentoElaborado.objects.create(documento=self.plan, version=0, contenido={})
        self.client.force_login(self.usuarios['laboratorios'])
        respuesta = self.client.get(reverse('redactar_documento_expediente',
                                           args=[self.unidad.slug, self.plan.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.plan.nombre_documental)
        self.assertContains(respuesta, '01/07/2026 – 31/12/2026')
        self.assertContains(respuesta, 'name="uso_horas__', count=6)
        for numero, nombre in ((7, 'Julio'), (8, 'Agosto'), (9, 'Septiembre'),
                               (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')):
            with self.subTest(mes=numero):
                self.assertContains(respuesta, 'name="uso_horas__' + str(numero) + '"', count=1)
                self.assertContains(respuesta, nombre)
        self.assertNotContains(respuesta, 'name="uso_horas__6"')
        self.assertContains(respuesta, 'Fundamento de la programación')
        redaccion.refresh_from_db()
        self.assertEqual((redaccion.version, redaccion.contenido), (0, {}))
