"""El cronograma usa fuentes académicas y operativas, sin alterar planes firmados."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase

from apps.documentos.presentation.expediente_redaccion import (
    _aplicar_cronograma, _bloques_del_campo, _calendario_docente, _campos_para_editor, _leer_actividades,
    cronograma_automatico, filas_del_plan, obtener_redaccion, problemas_cronograma,
)
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_expediente_redaccion import BaseDeRedaccion


class CronogramaAutomaticoPlanTests(SimpleTestCase):
    inicio, fin = date(2026, 1, 1), date(2026, 6, 30)

    def setUp(self):
        self.unidad = SimpleNamespace(pk=11, codigo_base='laboratorios')
        self.capacidad = dict(version=3, nivel='inicial', practicas_minimas=2, practicas_recomendadas=2)
        self.calendario = dict(disponible=True, meses=[3, 4, 5, 6], periodo_codigo='2026-A',
            periodo_id=1, version_calendario=9, numero_version=2,
            clases_inicio='2026-03-09', clases_fin='2026-07-10')
        for ruta, valor in (
                ('apps.documentos.presentation.expediente_redaccion._calendario_docente', self.calendario),
                ('apps.documentos.presentation.expediente_redaccion.programacion_mantenimiento', []),
                ('apps.documentos.presentation.metas_estandar.calcular_metas',
                    dict(version=1, metas={}, origenes={}, carga_docente={})),
                ('apps.documentos.presentation.politica_metas_unidades.capacidad_de', self.capacidad)):
            parche = patch(ruta, return_value=valor)
            parche.start()
            self.addCleanup(parche.stop)
        parche = patch('apps.documentos.presentation.expediente_redaccion.equipos_de')
        self.equipos = parche.start()
        self.equipos.return_value.exists.return_value = False
        self.addCleanup(parche.stop)
        parche = patch('apps.documentos.presentation.expediente_redaccion.PlanificacionPractica.objects.filter')
        self.practicas = parche.start()
        self.practicas.return_value.values_list.return_value = []
        self.addCleanup(parche.stop)

    def cronograma(self):
        return cronograma_automatico(self.unidad, self.inicio, self.fin)

    def contenido(self, cronograma):
        return dict(actividades=dict(minimos_catalogo=3, capacidad=self.capacidad,
            catalogo={}, otras=[], cronograma_auto=cronograma))

    def test_docencia_sigue_meses_academicos_y_la_operacion_todo_el_semestre(self):
        datos = self.cronograma()
        for codigo in ('PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS'):
            self.assertEqual(datos['meses_por_actividad'][codigo], [3, 4, 5, 6])
        for codigo in ('USO', 'SEGURIDAD', 'INSPECCIONES', 'DESECHOS'):
            self.assertEqual(datos['meses_por_actividad'][codigo], [1, 2, 3, 4, 5, 6])
        self.assertEqual(datos['meses_por_actividad']['INVENTARIO'], [6])
        self.assertEqual((datos['gestion_inicio'], datos['gestion_fin']), ('2026-01-01', '2026-06-30'))

    def test_practicas_reales_fuera_de_clases_se_conservan_dentro_de_gestion(self):
        self.practicas.return_value.values_list.return_value = [date(2026, 2, 15), date(2026, 5, 10)]
        datos = self.cronograma()
        for codigo in ('PRACTICAS', 'PRACTICAS-PLAN'):
            self.assertEqual(datos['meses_por_actividad'][codigo], [2, 5])
            self.assertIn('fuera de los meses de clases', datos['origenes'][codigo])
        self.assertEqual(datos['meses_por_actividad']['GUIAS'], [3, 4, 5, 6])

    def test_mantenimiento_usa_fechas_reales_incluso_en_interperiodo(self):
        with patch('apps.documentos.presentation.expediente_redaccion.programacion_mantenimiento',
                   return_value=[dict(fechas=[date(2026, 1, 10), date(2026, 5, 10), date(2026, 7, 10)])]):
            datos = self.cronograma()
        self.assertEqual(datos['meses_por_actividad']['MANTENIMIENTO'], [3])
        self.assertEqual(datos['mantenimiento_meses_por_equipo'], [1, 5])
        self.assertEqual(datos['mantenimiento_ventana'], '2026-03-06')
        self.assertTrue(datos['mantenimiento_exigible'])

    def test_no_inventa_mes_medio_y_la_ausencia_de_equipos_no_bloquea_por_fechas(self):
        datos = self.cronograma()
        self.assertEqual(datos['meses_por_actividad']['MANTENIMIENTO'], [])
        self.assertFalse(datos['mantenimiento_exigible'])
        problemas = problemas_cronograma(self.unidad, self.contenido(datos), self.inicio, self.fin)
        self.assertFalse(any('Mantenimiento' in p['mensaje'] for p in problemas))

    def test_equipo_exigible_sin_programacion_presenta_faltante_objetivo(self):
        self.equipos.return_value.exists.return_value = True
        self.calendario.update(clases_inicio='2026-01-01', clases_fin='2026-06-30')
        datos = self.cronograma()
        self.assertEqual(datos['meses_por_actividad']['MANTENIMIENTO'], [])
        self.assertIn('No hay una ventana general', datos['origenes']['MANTENIMIENTO'])
        problemas = problemas_cronograma(self.unidad, self.contenido(datos), self.inicio, self.fin)
        self.assertTrue(any(p['regla'] == 'actividad_incompleta' and p['severidad'] == 'bloqueo'
                            and 'mantenimiento' in p['mensaje'] for p in problemas))

    def test_calendario_ausente_no_inventa_seis_meses_de_docencia(self):
        with patch('apps.documentos.presentation.expediente_redaccion._calendario_docente',
                   return_value=dict(disponible=False, aviso='Calendario académico pendiente de publicar.')):
            datos = self.cronograma()
        self.assertEqual(datos['meses_academicos'], [])
        self.assertEqual(datos['meses_por_actividad']['PRACTICAS'], [])
        self.assertEqual(datos['meses_por_actividad']['USO'], [1, 2, 3, 4, 5, 6])
        problemas = problemas_cronograma(self.unidad, self.contenido(datos), self.inicio, self.fin)
        self.assertTrue(any(p['regla'] == 'calendario_docente_pendiente' and p['severidad'] == 'revision'
                            for p in problemas))

    def test_post_no_altera_meses_del_catalogo_y_preserva_responsable_previo(self):
        post = QueryDict('act__PRACTICAS__meses=12&act__USO__meses=12&act__PRACTICAS__meta=2')
        anterior = dict(catalogo=dict(PRACTICAS=dict(responsable='Responsable técnico vigente')))
        plan = _leer_actividades(post, self.unidad, inicio=self.inicio, fin=self.fin, anterior=anterior)
        self.assertEqual(plan['catalogo']['PRACTICAS']['meses'], [3, 4, 5, 6])
        self.assertEqual(plan['catalogo']['USO']['meses'], [1, 2, 3, 4, 5, 6])
        self.assertEqual(plan['catalogo']['PRACTICAS']['responsable'], 'Responsable técnico vigente')
        self.assertEqual(plan['catalogo']['USO']['responsable'], '')
        self.assertEqual(plan['cronograma_auto']['version'], 1)

    def test_propias_tienen_default_del_tramo_y_admiten_meses_explicitos(self):
        base = 'otra__nombre=Jornada&otra__indicador=Evento&otra__meta=1'
        plan = _leer_actividades(QueryDict(base), self.unidad, inicio=self.inicio, fin=self.fin)
        self.assertEqual(plan['otras'][0]['meses'], [1, 2, 3, 4, 5, 6])
        plan = _leer_actividades(QueryDict(base + '&otra__meses__0=5'), self.unidad,
                                inicio=self.inicio, fin=self.fin)
        self.assertEqual(plan['otras'][0]['meses'], [5])
        plan = _leer_actividades(QueryDict(base + '&otra__meses_presentes__0=1'), self.unidad,
                                inicio=self.inicio, fin=self.fin)
        self.assertEqual(plan['otras'][0]['meses'], [])

    def test_proyeccion_de_borrador_no_muta_historia_ni_responsabilidades(self):
        plan = dict(catalogo=dict(PRACTICAS=dict(aplica=True, meses=[1], responsable='Ana')),
            otras=[dict(nombre='Jornada', meses=[2], responsable='Luis'), dict(nombre='Nueva')])
        anterior = deepcopy(plan)
        propuesto = _aplicar_cronograma(plan, self.cronograma())
        self.assertEqual(plan, anterior)
        self.assertEqual(propuesto['catalogo']['PRACTICAS']['meses'], [3, 4, 5, 6])
        self.assertEqual(propuesto['catalogo']['PRACTICAS']['responsable'], 'Ana')
        self.assertEqual(propuesto['otras'][0]['meses'], [2])
        self.assertEqual(propuesto['otras'][0]['responsable'], 'Luis')
        self.assertEqual(propuesto['otras'][1]['meses'], [1, 2, 3, 4, 5, 6])

    def test_lectura_de_cronograma_guardado_no_reconsulta_fuentes_ni_lo_reescribe(self):
        datos = self.cronograma()
        contenido = self.contenido(datos)
        anterior = deepcopy(contenido)
        with patch('apps.documentos.presentation.expediente_redaccion.cronograma_automatico',
                   side_effect=AssertionError('Un cronograma guardado conserva sus fuentes.')):
            filas = filas_del_plan(self.unidad, contenido, self.inicio, self.fin)
        self.assertEqual(contenido, anterior)
        self.assertEqual(next(f for f in filas if f['codigo'] == 'PRACTICAS')['meses'], [3, 4, 5, 6])

    def test_editor_firmado_conserva_calendario_guardado_y_borrador_propone_nueva_version(self):
        contenido = self.contenido(self.cronograma())
        anterior = deepcopy(contenido)
        campo = SimpleNamespace(tipo='actividades', clave='actividades')
        seccion = SimpleNamespace(campos=[campo])
        documento = SimpleNamespace(estado='validado')
        self.calendario['meses'] = [4, 5, 6]
        with patch('apps.documentos.presentation.expediente_redaccion.secciones_de', return_value=[seccion]), \
                patch('apps.documentos.presentation.expediente_redaccion.cronograma_automatico',
                      side_effect=AssertionError('El plan firmado no vuelve a calcular su calendario.')):
            datos = _campos_para_editor('planificacion', contenido, self.unidad, documento,
                                        self.inicio, self.fin, {})[0]['campos'][0]
        self.assertEqual(next(f for f in datos['filas'] if f['codigo'] == 'PRACTICAS')['meses'], [3, 4, 5, 6])
        documento.estado = 'observado'
        with patch('apps.documentos.presentation.expediente_redaccion.secciones_de', return_value=[seccion]):
            datos = _campos_para_editor('planificacion', contenido, self.unidad, documento,
                                        self.inicio, self.fin, {})[0]['campos'][0]
        self.assertEqual(next(f for f in datos['filas'] if f['codigo'] == 'PRACTICAS')['meses'], [4, 5, 6])
        self.assertEqual(contenido, anterior)


class SeleccionCalendarioDocenteTests(SimpleTestCase):
    def calendario(self, inicio, fin, *, ciclo='A', periodos=None):
        documento = SimpleNamespace(anio=2026, corte=ciclo)
        with patch('apps.core.models.periodos.PeriodoAcademico.objects.operativos') as consulta:
            filtro = consulta.return_value.publicados.return_value.filter
            filtro.return_value.prefetch_related.return_value.order_by.return_value = periodos or []
            resultado = _calendario_docente(inicio, fin, documento)
            filtro.assert_called_once_with(anio_referencia=2026, ciclo=ciclo, tipo='ordinario')
        return resultado

    def periodo(self, inicio, fin, *, codigo='2026-A'):
        version = SimpleNamespace(pk=10, numero=2, fecha_inicio_clases=inicio,
            fecha_fin_clases=fin, fecha_fin_periodo=date(2026, 7, 17))
        return SimpleNamespace(pk=5, codigo=codigo, version_vigente=version)

    def test_calendario_academico_se_intersecta_sin_modificar_semestre_natural(self):
        datos = self.calendario(date(2026, 1, 1), date(2026, 6, 30),
            periodos=[self.periodo(date(2026, 3, 9), date(2026, 7, 10))])
        self.assertEqual(datos['meses'], [3, 4, 5, 6])
        self.assertEqual(datos['clases_fin'], '2026-07-10')

    def test_legacy_conserva_su_tramo_y_usa_fin_de_clases_no_fin_administrativo(self):
        datos = self.calendario(date(2026, 3, 9), date(2026, 7, 17),
            periodos=[self.periodo(date(2026, 3, 9), date(2026, 6, 30))])
        self.assertEqual(datos['meses'], [3, 4, 5, 6])

    def test_segundo_semestre_no_traslada_el_fin_academico_del_anio_siguiente(self):
        datos = self.calendario(date(2026, 7, 1), date(2026, 12, 31), ciclo='B',
            periodos=[self.periodo(date(2026, 8, 17), date(2027, 1, 15), codigo='2026-B')])
        self.assertEqual(datos['meses'], [8, 9, 10, 11, 12])

    def test_calendarios_incompatibles_o_sin_version_no_se_eligen_arbitrariamente(self):
        datos = self.calendario(date(2026, 1, 1), date(2026, 6, 30), periodos=[
            self.periodo(date(2026, 3, 9), date(2026, 7, 10)),
            self.periodo(date(2026, 4, 1), date(2026, 8, 1), codigo='2026-A-OTRO')])
        self.assertFalse(datos['disponible'])
        datos = self.calendario(date(2026, 1, 1), date(2026, 6, 30),
            periodos=[SimpleNamespace(version_vigente=None)])
        self.assertFalse(datos['disponible'])


class TablaPlanEnDocumentoTests(SimpleTestCase):
    def tabla(self, cronograma=None):
        campo = SimpleNamespace(tipo='actividades', clave='actividades')
        documento = SimpleNamespace(unidad=SimpleNamespace(),
            exigido=SimpleNamespace(fuente_reporte='planificacion'))
        actividades = dict(catalogo={})
        if cronograma is not None:
            actividades['cronograma_auto'] = cronograma
        fila = dict(nombre='Prácticas del semestre', aplica=True, institucional=False, por_tipo=True,
            indicador='Prácticas respaldadas', minimo='2 por período', meta='4', responsable='Ana')
        with patch('apps.documentos.presentation.expediente_redaccion.filas_del_plan', return_value=[fila]):
            tabla = _bloques_del_campo(campo, actividades, documento, dict(actividades=actividades),
                date(2026, 1, 1), date(2026, 6, 30), {})[0]
        self.assertEqual(fila['responsable'], 'Ana')
        return tabla

    def test_plan_nuevo_omite_columna_por_fila_sin_borrar_su_asignacion(self):
        tabla = self.tabla(dict(version=1))
        self.assertNotIn('A cargo de', tabla['cabecera'])
        self.assertEqual((len(tabla['cabecera']), len(tabla['filas'][0])), (5, 5))
        self.assertEqual(tabla['filas'][0][-1], '4')

    def test_plan_legacy_conserva_la_tabla_historica_con_responsable(self):
        tabla = self.tabla()
        self.assertEqual(tabla['cabecera'][-1], 'A cargo de')
        self.assertEqual(tabla['filas'][0][-1], 'Ana')
        self.assertEqual((len(tabla['cabecera']), len(tabla['filas'][0])), (6, 6))


class CronogramaAutomaticoGuardadoTests(BaseDeRedaccion):
    def test_get_no_persiste_y_post_calcula_meses_con_version_y_auditoria(self):
        self.client.force_login(self.coordinador)
        documento = self.documento('PLANIFICACION')
        redaccion = obtener_redaccion(documento)
        redaccion.contenido = dict(actividades=dict(catalogo=dict(PRACTICAS=dict(
            aplica=True, meta='2', meses=[1], responsable='Ana Coordinadora')), otras=[]))
        redaccion.version = 4
        redaccion.save()
        anterior = deepcopy(redaccion.contenido)
        respuesta = self.client.get(self.ruta_editor(documento))
        self.assertEqual(respuesta.status_code, 200)
        redaccion.refresh_from_db()
        self.assertEqual((redaccion.version, redaccion.contenido), (4, anterior))
        datos = dict(version_base='4', act__PRACTICAS__meta='2', act__PRACTICAS__meses='12',
                     firma_nombre='Ana Coordinadora', firma_cargo='Responsable')
        respuesta = self.client.post(self.ruta_editor(documento), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200)
        redaccion.refresh_from_db()
        self.assertEqual(redaccion.version, 5)
        self.assertEqual(redaccion.contenido['actividades']['catalogo']['PRACTICAS']['meses'], [3, 4, 5, 6])
        self.assertEqual(redaccion.contenido['actividades']['catalogo']['PRACTICAS']['responsable'], 'Ana Coordinadora')
        cronograma = redaccion.contenido['actividades']['cronograma_auto']
        self.assertEqual(cronograma['periodo_codigo'], '2026-A')
        self.assertEqual(cronograma['gestion_fin'], '2026-06-30')
        auditoria = RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad,
            entidad=redaccion._meta.label, objeto_id=str(redaccion.pk),
            descripcion__contains='borrador guardado').latest('pk')
        self.assertEqual(auditoria.datos_anteriores['contenido'], anterior)
        self.assertEqual(auditoria.datos_nuevos['contenido'], redaccion.contenido)
        guardado = deepcopy(redaccion.contenido)
        respuesta = self.client.post(self.ruta_editor(documento), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 409)
        redaccion.refresh_from_db()
        self.assertEqual((redaccion.version, redaccion.contenido), (5, guardado))
