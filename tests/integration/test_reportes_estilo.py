"""La agrupación visual conserva indicadores, enlaces y condiciones de la entrega."""
from copy import deepcopy
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.documentos.templatetags.reportes_estilo import (
    cantidad_items, clasificacion_meta, estado_meta, evidencias_cierre, exigencia_estilo,
    grupos_anexos, grupos_metas, resumen_metas_cierre,
)


class PresentacionIndicadoresTests(SimpleTestCase):
    def test_resumen_cuenta_metas_obligatorias_unicas_y_conserva_datos(self):
        filas = [dict(codigo='A', porcentaje=100), dict(codigo='B', porcentaje=50),
                 dict(codigo='C', porcentaje=0), dict(codigo='D', porcentaje=0, pendiente=True),
                 dict(codigo='OPT', porcentaje=100, exigencia='Opcional'),
                 dict(codigo='NA', porcentaje=None, exigencia='No aplica')]
        grupos = evidencias_cierre(dict(filas=[], nota=0), [
            dict(nombre='Informe', detalle_indicadores=filas),
            dict(nombre='Otro anexo', detalle_indicadores=[filas[0]])])
        antes = deepcopy(grupos)
        resumen = resumen_metas_cierre(grupos)
        self.assertEqual({k: resumen[k] for k in ('total', 'cumplidas', 'parciales',
                          'sin_acreditar', 'pendientes')},
                         dict(total=4, cumplidas=1, parciales=1, sin_acreditar=2, pendientes=1))
        self.assertEqual(resumen['cumplidas_porcentaje'], 25)
        self.assertEqual(grupos, antes)

    def test_clasificacion_no_acredita_mediciones_pendientes_o_invalidas(self):
        for valor in (None, 'NaN', 'Infinity', -1, 101, 'sin medir'):
            self.assertEqual(clasificacion_meta(dict(porcentaje=valor)), 'pendiente')
        self.assertEqual(clasificacion_meta(dict(porcentaje=100, pendiente=True)), 'pendiente')
        self.assertEqual(clasificacion_meta(dict(porcentaje=100)), 'cumple')
        self.assertEqual(clasificacion_meta(dict(porcentaje=0)), 'sin-avance')
        self.assertEqual(clasificacion_meta(dict(porcentaje='0.1')), 'parcial')
        for estado in ('No aplica', 'Anexo automático', 'Sin definir en planificación'):
            self.assertEqual(clasificacion_meta(dict(estado=estado, porcentaje=None)), 'neutro')
        self.assertEqual(resumen_metas_cierre([])['total'], 0)

    def test_grupos_conservan_todas_las_filas_y_su_instantanea(self):
        filas = [dict(exigencia=exigencia, codigo=str(i), porcentaje=0)
                 for i, exigencia in enumerate([
                     'No aplica', 'Sin definir', 'Opcional', 'Obligatorio del período',
                     'Obligatorio institucional', 'Comprometido en planificación',
                 ])]
        antes = deepcopy(filas)
        grupos = grupos_metas(filas)
        self.assertEqual([g['codigo'] for g in grupos],
                         ['obligatorio', 'opcional', 'sin-definir', 'no-aplica'])
        self.assertEqual([len(g['elementos']) for g in grupos], [3, 1, 1, 1])
        self.assertCountEqual([f['codigo'] for g in grupos for f in g['elementos']],
                              [f['codigo'] for f in filas])
        self.assertEqual(filas, antes)

    def test_anexo_mixto_conserva_sus_dos_indicadores_y_archivo(self):
        detalles = [dict(exigencia='No aplica'), dict(exigencia='Obligatorio del período')]
        for anexo in [SimpleNamespace(indicadores_cierre=detalles, recurso_id=4),
                      dict(detalle_indicadores=detalles, recurso=4)]:
            grupo, = grupos_anexos([anexo])
            self.assertEqual(grupo['codigo'], 'obligatorio')
            self.assertIs(grupo['elementos'][0], anexo)
        self.assertEqual(exigencia_estilo(detalles[0]), 'no-aplica')

    def test_sin_indicador_no_se_oculta_ni_se_declara_obligatorio(self):
        anexo = SimpleNamespace(indicadores_cierre=[], recurso_id=4)
        self.assertEqual(grupos_anexos([anexo])[0]['codigo'], 'sin-definir')
        self.assertEqual(grupos_metas([]), [])

    def test_pendiente_no_se_confunde_con_incumplimiento_y_opcional_no_alerta_rojo(self):
        for estado, exigencia, clase in [
            ('Cumple', 'Obligatorio institucional', 'cumple'),
            ('No cumple', 'Obligatorio del período', 'no-cumple'),
            ('No cumple', 'Opcional', 'opcional'),
            ('Pendiente de medición', 'Obligatorio institucional', 'pendiente'),
            ('Sin definir en planificación', 'Sin definir', 'neutro'),
            ('No aplica', 'No aplica', 'neutro'),
        ]:
            with self.subTest(estado=estado, exigencia=exigencia):
                self.assertEqual(estado_meta(dict(estado=estado, exigencia=exigencia))['clase'], clase)

    def test_meta_historica_sin_exigencia_conserva_su_condicion_previa(self):
        fila = dict(porcentaje=20, estado='No cumple')
        self.assertEqual(exigencia_estilo(fila), 'obligatorio')
        self.assertEqual(estado_meta(fila)['clase'], 'no-cumple')

    def test_unifica_metas_con_documentos_sin_repetir_ni_perder_las_no_asociadas(self):
        uso = dict(codigo='USO', nombre='Sesiones', exigencia='Obligatorio institucional', porcentaje=0)
        capacitacion = dict(codigo='CAPACITACION', nombre='Capacitación', exigencia='Obligatorio del período')
        cierre = dict(filas=[uso, capacitacion], nota=0)
        antes = deepcopy(cierre)
        anexo = SimpleNamespace(exigido=SimpleNamespace(nombre='Registro de uso'), recurso_id=7,
                                indicadores_cierre=[uso])
        grupos = evidencias_cierre(cierre, [anexo])
        filas = [b for g in grupos for b in g['elementos']]
        self.assertEqual([f['nombre'] for f in filas], ['Registro de uso', 'Capacitación'])
        self.assertEqual([i['codigo'] for b in filas for i in b['detalle_indicadores']], ['USO', 'CAPACITACION'])
        self.assertEqual(filas[0]['recurso'], 7)
        self.assertIs(filas[0]['anexo'], anexo)
        self.assertTrue(filas[1]['sin_anexo'])
        self.assertEqual(cierre, antes)

    def test_instantanea_conserva_indicadores_mixtos_archivo_y_anexo_sin_indicador(self):
        anexo = dict(nombre='Transferencia', recurso=10, detalle_indicadores=[
            dict(codigo='TRANSFERENCIA', exigencia='Obligatorio del período', porcentaje=50),
            dict(codigo='SERVICIOS', exigencia='No aplica', porcentaje=None)])
        sin_indicador = dict(nombre='Evidencia histórica', recurso=11)
        antes = deepcopy([anexo, sin_indicador])
        grupos = evidencias_cierre(dict(filas=anexo['detalle_indicadores'], nota=50), [anexo, sin_indicador])
        filas = [b for g in grupos for b in g['elementos']]
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]['detalle_indicadores'], anexo['detalle_indicadores'])
        self.assertEqual([b['recurso'] for b in filas], [10, 11])
        self.assertEqual([anexo, sin_indicador], antes)

    def test_sin_anexos_no_oculta_metas_del_informe_y_vacio_no_falla(self):
        self.assertEqual(evidencias_cierre({}, []), [])
        grupos = evidencias_cierre(dict(filas=[dict(codigo='PROPIA', nombre='Actividad propia',
                                                   porcentaje=20)]), [])
        fila, = grupos[0]['elementos']
        self.assertTrue(fila['sin_anexo'])
        self.assertEqual(fila['detalle_indicadores'][0]['porcentaje'], 20)
        self.assertEqual(fila['detalle_indicadores'][0]['indicador'], 'Actividad propia')
        self.assertEqual(fila['detalle_indicadores'][0]['exigencia'], 'Comprometido en planificación')

    def test_numeracion_continua_entre_grupos_cuenta_documentos_y_no_indicadores(self):
        anexos = [
            dict(nombre='Informativo', recurso=10, detalle_indicadores=[
                dict(codigo='INFO', estado='Anexo automático')]),
            dict(nombre='Dos indicadores', recurso=11, detalle_indicadores=[
                dict(codigo='A', exigencia='Obligatorio institucional'),
                dict(codigo='B', exigencia='No aplica')]),
        ]
        cierre = dict(filas=[dict(codigo='C', nombre='Actividad sin anexo', porcentaje=0)])
        antes = deepcopy((cierre, anexos))
        grupos = evidencias_cierre(cierre, anexos)
        bloques = [b for g in grupos for b in g['elementos']]
        self.assertEqual([b['nombre'] for b in bloques],
                         ['Dos indicadores', 'Actividad sin anexo', 'Informativo'])
        self.assertEqual([b['numero_item'] for b in bloques], [1, 2, 3])
        self.assertEqual(cantidad_items(grupos), 3)
        self.assertEqual(cantidad_items([]), 0)
        self.assertEqual((cierre, anexos), antes)
