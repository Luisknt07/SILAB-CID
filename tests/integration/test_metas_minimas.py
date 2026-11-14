"""Mínimos protegidos, reglas por tipología y avance con evidencia verificable."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.documentos.presentation.evaluacion_cierre import medir_meta
from apps.documentos.presentation.expediente_redaccion import (
    ACTIVIDADES_PLAN, _leer_actividades, actividades_para, filas_del_plan, obtener_redaccion,
    pdf_del_documento, plan_inicial,
)
from apps.documentos.presentation.metas_plan import control_meta, meta_con_minimo, obligatoria_por_tipo
from tests.integration.test_expediente_redaccion import BaseDeRedaccion, PLAN_COMPLETO


class MinimosTests(SimpleTestCase):
    actividades = {a.codigo: a for a in ACTIVIDADES_PLAN}

    def test_meta_vacia_recibe_minimo_y_mayor_es_aceptada(self):
        a = self.actividades['PRACTICAS']
        self.assertEqual(meta_con_minimo(a, ''), a.minimo)
        self.assertEqual(meta_con_minimo(a, '8'), '8')
        self.assertEqual(control_meta(a, '5', True)['valor'], '6')
        self.assertEqual(control_meta(a, '5', True, proponer=False)['valor'], '5')
        for valor in ['5', '0', '-1', '5.5', 'sin meta', '6 %']:
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                meta_con_minimo(a, valor)

    def test_porcentaje_no_se_reemplaza_por_un_conteo_ni_excede_cien(self):
        for codigo, valores in [('USO', ['99', '0', '101 %']), ('MANTENIMIENTO', ['79 %', '200'])]:
            for valor in valores:
                with self.subTest(codigo=codigo, valor=valor), self.assertRaises(ValidationError):
                    meta_con_minimo(self.actividades[codigo], valor)
        self.assertEqual(meta_con_minimo(self.actividades['MANTENIMIENTO'], '90'), '90 %')

    def test_cupos_por_tipo_y_demanda_no_reciben_una_cifra_inventada(self):
        comunes = {'USO', 'MANTENIMIENTO', 'INVENTARIO', 'SEGURIDAD', 'CAPACITACION', 'DIFUSION'}
        esperados = {'laboratorios': comunes | {'PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS', 'DESECHOS', 'INSPECCIONES'},
                     'plantas_piloto': comunes | {'PRODUCCION', 'CONTROL-CALIDAD', 'DESECHOS', 'INSPECCIONES'},
                     'centro_experimental': comunes | {'ENSAYOS', 'DESECHOS', 'INSPECCIONES'},
                     'observatorios': {'INVENTARIO', 'CAPACITACION', 'DIFUSION', 'BOLETINES', 'DATOS-ACTUALIZADOS', 'EVENTOS'},
                     'centros_id': comunes | {'EVENTOS', 'PROYECTOS', 'PUBLICACIONES'}}
        for base, codigos in esperados.items():
            self.assertEqual({a.codigo for a in actividades_para(SimpleNamespace(codigo_base=base))
                              if obligatoria_por_tipo(a)}, codigos)
        self.assertEqual(meta_con_minimo(self.actividades['SERVICIOS'], ''), '')

    def test_version_dos_conserva_cupos_y_compromisos_anteriores(self):
        comunes = {'USO', 'MANTENIMIENTO', 'INVENTARIO', 'SEGURIDAD', 'CAPACITACION', 'DIFUSION',
                   'INVESTIGACION', 'TRANSFERENCIA'}
        actividades = actividades_para(SimpleNamespace(codigo_base='laboratorios'), version=2)
        self.assertEqual({a.codigo for a in actividades if obligatoria_por_tipo(a)},
                         comunes | {'PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS', 'DESECHOS', 'INSPECCIONES'})
        self.assertEqual(next(a.minimo for a in actividades if a.codigo == 'PRACTICAS'), '≥ 6 por período')

    def test_version_uno_conserva_obligatoriedad_y_anexos_automaticos_no_sumam_ceros(self):
        from apps.documentos.presentation.evaluacion_cierre import evaluar_meta
        self.assertFalse(obligatoria_por_tipo(self.actividades['CAPACITACION'], version=1))
        self.assertFalse(obligatoria_por_tipo(self.actividades['PRACTICAS-PLAN'], version=1))
        fila = evaluar_meta(dict(codigo='PRESTAMOS', nombre='Préstamos', contador='prestamos', registrado=0,
                                meta='', solo_anexo=True, aplica=False), {})
        self.assertEqual(fila['estado'], 'Anexo automático')
        self.assertFalse(fila['exigible'])
        self.assertIsNone(fila['porcentaje'])

    def test_post_manipulado_no_desactiva_los_requisitos_por_tipo(self):
        post = QueryDict('act__PRACTICAS__exigencia=no_aplica&act__GUIAS__exigencia=opcional')
        # Este caso aísla las exigencias del formulario; el cálculo de capacidad
        # se prueba con unidades persistidas en GuardarMinimosTests.
        capacidad = dict(version=3, nivel='inicial', practicas_minimas=2, practicas_recomendadas=2)
        with patch('apps.documentos.presentation.politica_metas_unidades.capacidad_de', return_value=capacidad):
            plan = _leer_actividades(post, SimpleNamespace(codigo_base='laboratorios'))
        self.assertEqual(plan['capacidad'], capacidad)
        for codigo in ['PRACTICAS', 'GUIAS', 'USO']:
            self.assertTrue(plan['catalogo'][codigo]['aplica'])
            self.assertTrue(plan['catalogo'][codigo]['obligatoria'])
            self.assertTrue(plan['catalogo'][codigo]['meta'])

    def test_lectura_de_plan_anterior_no_reescribe_sus_compromisos(self):
        unidad = SimpleNamespace(codigo_base='laboratorios')
        contenido = dict(actividades=dict(catalogo=dict(GUIAS=dict(aplica=False, meta=''),
                              PRACTICAS=dict(aplica=True, meta='5', meses=[3])), otras=[]))
        antes = deepcopy(contenido)
        with patch('apps.documentos.presentation.expediente_redaccion.meses_por_defecto', return_value={}), \
                patch('apps.documentos.presentation.politica_metas_unidades.capacidad_de',
                      return_value=dict(version=3, practicas_minimas=2, practicas_recomendadas=2)):
            filas = {f['codigo']: f for f in filas_del_plan(unidad, contenido, date(2026, 3, 1), date(2026, 7, 1))}
        self.assertFalse(filas['GUIAS']['aplica'])
        self.assertEqual(filas['PRACTICAS']['meta'], '5')
        self.assertEqual(contenido, antes)

    def test_progreso_parcial_completo_superado_y_pendiente(self):
        for valor, porcentaje, faltante in [(0, 0, 6), (1, 16.67, 5), (6, 100, 0), (8, 100, 0)]:
            fila = medir_meta(dict(codigo='PRACTICAS', nombre='Prácticas', contador='practicas',
                                   meta='6', registrado=valor), {})
            self.assertEqual((fila['porcentaje'], fila['faltante']), (porcentaje, faltante))
        pendiente = medir_meta(dict(codigo='USO', nombre='Uso', contador='sesiones', meta='100 %'), {})
        self.assertIsNone(pendiente['faltante'])
        self.assertIsNone(pendiente['objetivo'])

    def test_barra_usa_decimal_html_y_no_acredita_mediciones_ausentes(self):
        nombre = 'portal/pages/unidades/gestion/includes/progreso_meta.html'
        html = render_to_string(nombre, dict(indicador=dict(porcentaje=16.67, pendiente=False,
                                    estado='No cumple', nombre='Prácticas', faltante=5)))
        self.assertIn('value="16.67"', html)
        self.assertIn('Faltan 5', html)
        self.assertNotIn('<progress', render_to_string(nombre, dict(indicador=dict(
            porcentaje=0, pendiente=True, estado='Pendiente de medición'))))


class GuardarMinimosTests(BaseDeRedaccion):
    def test_editor_reserva_la_ejecucion_para_el_cierre_y_fija_las_metas(self):
        d = self.documento('PLANIFICACION')
        self.client.force_login(self.coordinador)
        r = self.client.get(self.ruta_editor(d))
        self.assertNotContains(r, 'Seguimiento al corte')
        self.assertNotContains(r, 'data-plan-seguimiento')
        self.assertNotContains(r, 'type="number" name="act__')
        self.assertContains(r, 'redaccion__meta-fija')
        self.assertContains(r, 'Origen de la meta')

    def test_inicial_establece_los_cupos_sin_que_la_unidad_los_escriba(self):
        d = self.documento('PLANIFICACION')
        plan = plan_inicial(d, date(2026, 3, 9), date(2026, 7, 17))
        self.assertEqual(plan['minimos_catalogo'], 3)
        self.assertEqual(plan['capacidad']['nivel'], 'limitada')
        self.assertEqual(plan['catalogo']['PRACTICAS']['meta'], '2')
        self.assertTrue(plan['catalogo']['GUIAS']['aplica'])

    def test_ajax_ignora_el_numero_del_cliente_y_conserva_el_estandar(self):
        d = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(d)
        redaccion.save()
        self.client.force_login(self.coordinador)
        r = self.client.post(self.ruta_editor(d), {'version_base': redaccion.version,
                             'act__PRACTICAS__meta': '1'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.contenido['actividades']['catalogo']['PRACTICAS']['meta'], '2')
        self.assertEqual(redaccion.contenido['actividades']['metas_estandar']['version'], 2)

    def test_generacion_directa_tambien_rechaza_cupo_inferior(self):
        d = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(d)
        redaccion.contenido = deepcopy(PLAN_COMPLETO)
        redaccion.contenido['actividades']['catalogo']['PRACTICAS']['meta'] = '5'
        with self.assertRaisesMessage(ValidationError, 'mínimo de referencia del plan'):
            pdf_del_documento(d, redaccion, date(2026, 3, 9), date(2026, 7, 17))
