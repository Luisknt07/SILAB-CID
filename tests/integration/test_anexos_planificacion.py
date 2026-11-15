"""La exigencia y meta elegidas en el plan acompañan a cada evidencia del cierre."""
from copy import deepcopy
from datetime import date

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import SimpleTestCase

from apps.documentos.presentation.evaluacion_cierre import ANEXOS_METAS, detalle_anexo, evaluar_meta
from apps.documentos.presentation.expediente_catalogo import CATALOGO, CATALOGO_PERFILES
from apps.documentos.presentation.expediente_redaccion import (
    filas_del_plan, leer_formulario, pdf_del_documento, obtener_redaccion,
)
from tests.integration.test_expediente_redaccion import BaseDeRedaccion, PLAN_COMPLETO


class ContratoIndicadoresTests(SimpleTestCase):
    def test_todos_los_anexos_del_cierre_tienen_un_indicador_de_planeacion(self):
        anexos = {f[0] for f in (*CATALOGO, *CATALOGO_PERFILES) if f[-1] == 'INFORME-SEMESTRAL'}
        self.assertEqual(anexos, set(ANEXOS_METAS))

    def test_opcional_y_no_aplica_no_se_convierten_en_obligaciones_incumplidas(self):
        fila = dict(codigo='PRESTAMOS', nombre='Préstamos', indicador='Préstamos entregados',
                    contador='prestamos', meta='4', registrado=0, aplica=True, obligatoria=False)
        opcional = evaluar_meta(fila, {})
        self.assertFalse(opcional['exigible'])
        self.assertEqual(opcional['exigencia'], 'Opcional')
        fila['aplica'] = False
        no_aplica = evaluar_meta(fila, {})
        self.assertEqual(no_aplica['estado'], 'No aplica')
        self.assertIsNone(no_aplica['porcentaje'])

    def test_ft02_compara_planificaciones_y_ft03_ejecuciones(self):
        cierre = dict(catalogo=[
            evaluar_meta(dict(codigo='PRACTICAS-PLAN', nombre='Planificaciones', contador='practicas_planificadas',
                              indicador='FT02', meta='6', registrado=6), {}),
            evaluar_meta(dict(codigo='PRACTICAS', nombre='Ejecuciones', contador='practicas',
                              indicador='FT03', meta='6', registrado=3), {}),
        ])
        self.assertEqual(detalle_anexo('PRACTICAS-FT02', cierre)[0]['porcentaje'], 100)
        self.assertEqual(detalle_anexo('PRACTICAS-FT03', cierre)[0]['porcentaje'], 50)


class PlanificaExigenciasTests(BaseDeRedaccion):
    def test_editor_lee_exigencias_y_no_permite_desactivar_requisitos_institucionales(self):
        post = QueryDict(mutable=True)
        post.update({'act__USO__exigencia': 'no_aplica', 'act__GUIAS__exigencia': 'opcional',
                     'act__GUIAS__meta': '2', 'act__PRESTAMOS__exigencia': 'obligatoria',
                     'act__PRESTAMOS__meta': '4', 'act__INSUMOS__exigencia': 'no_aplica'})
        contenido = leer_formulario('planificacion', post, self.unidad)
        filas = {f['codigo']: f for f in filas_del_plan(self.unidad, contenido, date(2026, 3, 9), date(2026, 7, 17))}
        self.assertTrue(filas['USO']['aplica'] and filas['USO']['obligatoria'])
        self.assertTrue(filas['GUIAS']['aplica'])
        self.assertTrue(filas['GUIAS']['obligatoria'])
        self.assertFalse(filas['PRESTAMOS']['obligatoria'])
        self.assertTrue(filas['PRESTAMOS']['solo_anexo'])
        self.assertEqual(filas['PRESTAMOS']['meta'], '')
        self.assertFalse(filas['INSUMOS']['aplica'])
        # Los préstamos son consulta de gestión, no anexo; los insumos viajan en el inventario.
        self.assertEqual(filas['PRESTAMOS']['anexos'], [])
        self.assertEqual(filas['INSUMOS']['anexos'], ['Inventario de equipos, software, espacios e insumos al corte'])
        self.assertEqual(filas['INSUMOS']['nombre_reporte'], filas['INSUMOS']['nombre'])
        self.assertEqual(filas['MANTENIMIENTO']['anexos'],
                         ['Mantenimiento, disponibilidad y funcionalidad del equipamiento'])

    def test_no_se_acepta_una_exigencia_inventada(self):
        post = QueryDict('act__GUIAS__exigencia=aprobar_sin_revisar')
        with self.assertRaises(ValidationError):
            leer_formulario('planificacion', post, self.unidad)

    def test_no_se_genera_plan_definitivo_con_actividad_seleccionada_sin_meta(self):
        d = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(d)
        redaccion.contenido = deepcopy(PLAN_COMPLETO)
        # Una actividad con mínimo usa el mínimo del sistema; una propia sí
        # necesita que la unidad defina una meta verificable.
        redaccion.contenido['actividades']['otras'][0]['meta'] = ''
        with self.assertRaisesMessage(ValidationError, 'Define la meta del período'):
            pdf_del_documento(d, redaccion, date(2026, 3, 9), date(2026, 7, 17))

    def test_planeacion_y_documento_muestran_exigencia_y_no_aplicables(self):
        from apps.documentos.presentation.expediente_redaccion import componer
        d = self.documento('PLANIFICACION')
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(self.ruta_editor(d))
        self.assertNotContains(respuesta, 'act__PRESTAMOS__exigencia')
        self.assertContains(respuesta, 'Anexos automáticos del período')
        self.assertContains(respuesta, 'Obligatoria del período')
        self.assertContains(respuesta, 'Opcional')
        compuesto = componer(d, PLAN_COMPLETO, date(2026, 3, 9), date(2026, 7, 17))
        tabla = next(s for s in compuesto['secciones'] if s['codigo'] == 'plan')['bloques'][0]
        self.assertIn('Exigencia', tabla['cabecera'])
        self.assertTrue(any(f[1] == 'No aplica' for f in tabla['filas']))
        # Un registro sin meta no se presenta como actividad que no aplica, y los préstamos ya no figuran.
        self.assertTrue(any(f[1] == 'Registro del período, sin meta' for f in tabla['filas']))
        self.assertFalse(any('préstamo' in f[0].lower() for f in tabla['filas']))
        self.assertContains(respuesta, 'Disponibilidad del equipamiento')
        self.assertNotContains(respuesta, 'Préstamos de equipos')
