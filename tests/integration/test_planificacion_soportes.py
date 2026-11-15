"""Un anexo que la institución agregue a la planificación la acompaña sin duplicar metas ni puntos.

El catálogo distribuido ya no da anexos a la planificación (documentos.0024): la carga por asignatura y los
mantenimientos previstos son secciones de su PDF. El mecanismo de soporte sigue disponible para un catálogo
institucional, y estas pruebas lo ejercitan con documentos propios de la institución.
"""
from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.documentos.presentation.cumplimiento import categorias_de_matriz, filtrar_bandeja_automatizacion
from apps.documentos.presentation.expediente_catalogo import CATALOGO
from apps.documentos.presentation.organizacion_expediente import contextualizar_soportes_planificacion

SOPORTE = 'SOPORTE-PLAN-PROPIO'
SOPORTE_ANUAL = 'SOPORTE-ANUAL-PROPIO'


class PlanificacionSoportesTests(SimpleTestCase):
    def test_el_catalogo_distribuido_no_da_anexos_a_la_planificacion(self):
        self.assertFalse([f[0] for f in CATALOGO if f[-1] == 'PLANIFICACION'])

    def test_bandeja_de_faltantes_mantiene_el_soporte_en_anexos_sin_reinsertar_el_plan(self):
        plan = self.documento()
        anexo = self.documento(SOPORTE, estado='generado',
            automatizacion=dict(vigente=True, estado='revision'))
        contextualizar_soportes_planificacion([plan, anexo])
        progreso = dict(total=2, porcentaje=50)
        fila = dict(matriz=[dict(documento=plan)],
            anexos_seguimiento=[dict(documento=anexo, es_soporte_planificacion=True,
                soporte_planificacion=anexo.soporte_planificacion)], progreso_general=progreso, total=2)
        filtrada = filtrar_bandeja_automatizacion([fila], 'unidad')[0]
        self.assertEqual(filtrada['matriz'], [])
        self.assertEqual(filtrada['categorias_matriz'], [])
        self.assertEqual([a['documento'] for a in filtrada['anexos_seguimiento']], [anexo])
        self.assertIn('revisar=10', filtrada['anexos_seguimiento'][0]['soporte_planificacion']['url_director'])
        self.assertIs(filtrada['progreso_general'], progreso)
        self.assertEqual(filtrada['total'], 2)

    def documento(self, codigo='PLANIFICACION', **cambios):
        es_anexo = codigo in (SOPORTE, 'PRACTICAS-FT02', SOPORTE_ANUAL)
        exigido_id = {'PLANIFICACION': 10, 'INFORME-SEMESTRAL': 20,
                      SOPORTE: 11, 'PRACTICAS-FT02': 21, SOPORTE_ANUAL: 12}[codigo]
        exigido = SimpleNamespace(codigo=codigo, es_anexo=es_anexo, orden=exigido_id,
            periodicidad='anual' if codigo == SOPORTE_ANUAL else 'semestral',
            anexo_de_id=10 if codigo in (SOPORTE, SOPORTE_ANUAL) else 20 if es_anexo else None)
        datos = dict(pk=exigido_id, exigido=exigido, exigido_id=exigido_id,
            unidad_id=1, unidad=SimpleNamespace(slug='unidad-uno'), anio=2026, corte='B',
            marco_periodo='gestion_v1', tramo_inicio=date(2026, 7, 1), tramo_fin=date(2026, 12, 31),
            nombre_documental=codigo, estado='validado', resumen_interfaz={}, etiqueta_corte='2026-B')
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def test_soporte_propio_tiene_padre_y_no_suma_meta_ni_puntos(self):
        plan = self.documento()
        anexo = self.documento(SOPORTE)
        ft02 = self.documento('PRACTICAS-FT02')
        informe = self.documento('INFORME-SEMESTRAL')
        contextualizar_soportes_planificacion([plan, anexo, ft02, informe])
        soporte = anexo.soporte_planificacion
        self.assertEqual(plan.anexos_integrados, [anexo])
        self.assertIs(soporte['documento'], plan)
        self.assertEqual(soporte['meta_codigo'], '')
        self.assertEqual(soporte['unidad_medida'], 'Documento de respaldo')
        self.assertFalse(soporte['aporta_puntos'])
        self.assertIn('gestionar=10', soporte['url'])
        self.assertIn('revisar=10', soporte['url_director'])
        self.assertIn('una meta ni puntos', soporte['descripcion'])
        self.assertIsNone(ft02.soporte_planificacion)

    def test_no_vincula_otra_unidad_periodo_marco_o_fechas_historicas(self):
        for cambios in (dict(unidad_id=2), dict(anio=2025), dict(corte='A'),
                        dict(marco_periodo='academico_legacy'), dict(tramo_inicio=date(2026, 8, 17)),
                        dict(estado='no_aplica')):
            with self.subTest(cambios=cambios):
                plan = self.documento()
                anexo = self.documento(SOPORTE, **cambios)
                contextualizar_soportes_planificacion([plan, anexo])
                self.assertEqual(plan.anexos_integrados, [])
                self.assertIsNone(anexo.soporte_planificacion)

    def test_soporte_anual_conserva_su_alcance_y_el_parent_real_del_catalogo(self):
        plan = self.documento(corte='A', tramo_inicio=date(2026, 1, 1), tramo_fin=date(2026, 6, 30))
        anual = self.documento(SOPORTE_ANUAL, corte='A',
            tramo_inicio=date(2026, 1, 1), tramo_fin=date(2026, 12, 31))
        contextualizar_soportes_planificacion([plan, anual])
        self.assertEqual(plan.anexos_integrados, [anual])
        self.assertEqual(anual.tramo_fin, date(2026, 12, 31))
        self.assertFalse(anual.soporte_planificacion['meta_codigo'])
        anual.exigido.anexo_de_id = 20
        contextualizar_soportes_planificacion([plan, anual])
        self.assertIsNone(anual.soporte_planificacion)

    def test_director_intercala_soporte_sin_contarlo_como_obligacion_o_recibido(self):
        plan = self.documento()
        anexo = self.documento(SOPORTE)
        informe = self.documento('INFORME-SEMESTRAL')
        contextualizar_soportes_planificacion([plan, anexo, informe])
        matriz = [dict(documento=plan, enviado=True), dict(documento=informe, enviado=False)]
        categorias = categorias_de_matriz(matriz, [dict(documento=anexo)])
        self.assertEqual(len(categorias), 1)
        categoria = categorias[0]
        self.assertEqual([c['documento'] for c in categoria['casillas']], [plan, anexo, informe])
        self.assertEqual(categoria['total_obligaciones'], 2)
        self.assertEqual(categoria['soportes'], 1)
        self.assertEqual(categoria['recibidos'], 1)
        self.assertEqual([c['categoria_flujo'] for c in categoria['casillas']],
                         ['planificacion', 'planificacion', 'cierre'])
        self.assertTrue(categoria['casillas'][1]['es_soporte_planificacion'])
        self.assertIs(categoria['casillas'][1]['documento_padre'], plan)
        self.assertEqual(len(matriz), 2)

    def test_excepcion_solo_en_soporte_conserva_enlace_al_plan_sin_reinsertarlo(self):
        plan = self.documento()
        anexo = self.documento(SOPORTE)
        contextualizar_soportes_planificacion([plan, anexo])
        categoria = categorias_de_matriz([], [dict(documento=anexo)])[0]
        self.assertEqual(categoria['codigo'], 'semestre-B')
        self.assertEqual(categoria['total_obligaciones'], 0)
        self.assertEqual(categoria['recibidos'], 0)
        self.assertEqual([c['documento'] for c in categoria['casillas']], [anexo])
        self.assertIn('revisar=10', categoria['casillas'][0]['soporte_planificacion']['url_director'])
