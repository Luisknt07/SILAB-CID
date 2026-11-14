"""La barra general sigue las metas reales, separada de trámites y nota oficial."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.progreso_documento import leer_avance
from apps.documentos.presentation.progreso_general import avance_operativo_actual, progreso_general


class AvanceOperativoAcumuladoTests(SimpleTestCase):
    def documento(self, codigo='INFORME-SEMESTRAL', *, numero=2, corte='B', **cambios):
        datos = dict(pk=numero, version=1, recurso_id=None, estado='pendiente',
            unidad_id=11, anio=2026, corte=corte, marco_periodo='semestral_natural',
            tramo_inicio=date(2026, 7, 1) if corte == 'B' else date(2026, 1, 1),
            tramo_fin=date(2026, 12, 31) if corte == 'B' else date(2026, 6, 30),
            exigido=SimpleNamespace(codigo=codigo, es_anexo=False))
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def fuente(self, documento, porcentajes, **cambios):
        datos = dict(version=documento.version, recurso=documento.recurso_id,
            periodo_documental=dict(marco=documento.marco_periodo,
                inicio=documento.tramo_inicio.isoformat(), fin=documento.tramo_fin.isoformat()),
            filas=[dict(codigo=f'META-{n}', exigible=True, aplica=True,
                definida=True, pendiente=False, porcentaje=p) for n, p in enumerate(porcentajes)])
        datos.update(cambios)
        documento._avance_cierre = datos
        return datos

    def avance(self, *documentos):
        return avance_operativo_actual([dict(documento=d) for d in documentos], {})

    def renderizar(self, avance, *, oficial=None, corte='B'):
        return render_to_string('portal/pages/unidades/gestion/includes/progreso_general.html',
            dict(corte=corte, progreso_general=dict(avance_operativo=avance,
                resultado_porcentaje=oficial, total=2 if corte else 4, completados=1,
                porcentaje=50, desglose=[], sin_ponderacion=[])))

    def test_una_de_trece_metas_al_16_67_aporta_1_28_a_la_barra_general(self):
        cierre = self.documento()
        self.fuente(cierre, ['16.67', *(['0.00'] * 12)])
        datos = self.avance(cierre)
        self.assertEqual(datos['porcentaje'], Decimal('1.28'))
        self.assertEqual(datos['porcentaje'], leer_avance(cierre)['porcentaje'])
        self.assertEqual((datos['indicadores_con_avance'], datos['indicadores_total']), (1, 13))
        self.assertTrue(datos['medido'])
        self.assertTrue(datos['provisional'])
        self.assertEqual(datos['fuente'], 'metas_precargadas')

    def test_promedio_excluye_administrativos_edicion_anexos_y_metas_no_aplicables(self):
        cierre = self.documento(avance_redaccion=100)
        fuente = self.fuente(cierre, [20, 0])
        fuente['filas'] += [dict(exigible=False, aplica=True, porcentaje=100),
                            dict(exigible=True, aplica=False, porcentaje=100)]
        admin = self.documento('RESOLUCION-CREACION', numero=1, avance_redaccion=100)
        compras = self.documento('PLAN-COMPRAS-ANUAL', numero=3, avance_redaccion=100)
        anexo = self.documento('FT02', numero=4, indicadores_cierre=fuente['filas'])
        self.assertEqual(self.avance(admin, cierre, compras, anexo)['porcentaje'], Decimal('10.00'))
        self.assertEqual(self.avance(admin, cierre, compras, anexo)['indicadores_total'], 2)

    def test_pendientes_indefinidas_e_invalidas_conservan_cero_y_denominador(self):
        cierre = self.documento()
        fuente = self.fuente(cierre, [100, 90, 80, 'NaN', None])
        fuente['filas'][1]['pendiente'] = True
        fuente['filas'][2]['definida'] = False
        datos = self.avance(cierre)
        self.assertEqual(datos['porcentaje'], Decimal('20.00'))
        self.assertEqual((datos['indicadores_total'], datos['indicadores_con_avance'], datos['pendientes']), (5, 1, 4))

    def test_sin_fuente_no_toma_nota_historica_ni_porcentaje_de_redaccion(self):
        cierre = self.documento(estado='validado', avance_redaccion=100, nota=90,
            avance_documental=dict(medido=True, porcentaje=90, alcance='metas', etiqueta='Resultado acreditado'))
        datos = self.avance(cierre)
        self.assertFalse(datos['medido'])
        self.assertIsNone(datos['porcentaje'])
        self.assertEqual(datos['semestres_con_fuente'], 0)

    def test_sin_metas_exigibles_no_inventa_una_medicion_cero(self):
        cierre = self.documento()
        self.fuente(cierre, [])
        datos = self.avance(cierre)
        self.assertFalse(datos['medido'])
        self.assertIsNone(datos['porcentaje'])

    def test_fuente_de_otra_version_recurso_o_periodo_no_acredita_avance_actual(self):
        for campo, valor in (('version', 2), ('recurso', 55),
                ('periodo_documental', dict(marco='academico_legacy')),
                ('periodo_documental', dict(inicio='2026-08-17')),
                ('periodo_documental', dict(fin='2026-12-08'))):
            with self.subTest(campo=campo, valor=valor):
                cierre = self.documento()
                self.fuente(cierre, [100], **{campo: valor})
                datos = self.avance(cierre)
                self.assertFalse(datos['medido'])
                self.assertIsNone(datos['porcentaje'])

    def test_referencia_plan_exige_mismo_alcance_y_version_aun_para_el_seguimiento(self):
        for campo, valor in (('unidad_id', 12), ('anio', 2025), ('corte', 'A'),
                ('marco_periodo', 'academico_legacy'), ('tramo_inicio', date(2026, 8, 17)),
                ('tramo_fin', date(2026, 12, 8)), ('version', 2), ('recurso_id', 55)):
            with self.subTest(campo=campo):
                cierre, plan = self.documento(), self.documento('PLANIFICACION', numero=1)
                self.fuente(cierre, [100], plan=dict(documento=plan.pk, version=plan.version, recurso=plan.recurso_id))
                setattr(plan, campo, valor)
                self.assertFalse(self.avance(plan, cierre)['medido'])
        cierre, plan = self.documento(), self.documento('PLANIFICACION', numero=1, estado='observado')
        self.fuente(cierre, [40], plan=dict(documento=plan.pk, version=plan.version, recurso=plan.recurso_id))
        self.assertEqual(self.avance(plan, cierre)['porcentaje'], Decimal('40.00'))

    def test_lectura_no_accede_controles_pdfs_ni_modelos(self):
        class SoloMetas(SimpleNamespace):
            @property
            def automatizacion(self):
                raise AssertionError('El avance general no necesita volver a cargar controles.')

            @property
            def recurso(self):
                raise AssertionError('El avance general no necesita abrir archivos.')
        cierre = SoloMetas(**vars(self.documento()))
        self.fuente(cierre, [50])
        self.assertEqual(self.avance(cierre)['porcentaje'], Decimal('50.00'))

    def test_anual_no_muestra_100_si_un_semestre_no_tiene_fuente(self):
        a, b = self.documento(numero=2, corte='A'), self.documento(numero=4)
        self.fuente(a, [100])
        datos = self.avance(a, b)
        self.assertEqual(datos['porcentaje'], Decimal('50.00'))
        self.assertEqual((datos['semestres_con_fuente'], datos['semestres_total']), (1, 2))
        self.assertTrue(datos['parcial'])
        html = self.renderizar(datos, corte='')
        self.assertIn('Hay medición de 1 de 2 semestres; el resto conserva cero provisional.', html)
        self.assertIn('<progress value="50.00" max="100"', html)
        self.fuente(b, [50, 0])
        datos = self.avance(a, b)
        self.assertEqual(datos['porcentaje'], Decimal('62.50'))
        self.assertFalse(datos['parcial'])
        self.assertIn('Hay medición de 2 de 2 semestres.', self.renderizar(datos, corte=''))

    def test_barra_unica_es_la_de_metas_y_no_el_contador_de_tramites(self):
        cierre = self.documento()
        self.fuente(cierre, [Decimal('16.67'), *([0] * 12)])
        html = self.renderizar(self.avance(cierre))
        self.assertEqual(html.count('<progress '), 1)
        self.assertIn('<progress value="1.28" max="100"', html)
        self.assertIn('1 de 13 metas con avance', html)
        self.assertIn('1 de 2</b> trámites acreditados', html)
        self.assertIn('Nota oficial del cierre', html)
        self.assertIn('El cierre todavía no tiene un resultado acreditado.', html)
        self.assertNotIn('<progress value="50', html)

    def test_sin_medicion_no_dibuja_cero_ni_sustituye_la_nota_oficial(self):
        html = self.renderizar(self.avance(self.documento()), oficial=80)
        self.assertIn('Sin medición', html)
        self.assertNotIn('<progress ', html)
        self.assertIn('80,00 %', html)
        self.assertIn('Nota oficial del cierre', html)

    def test_plan_observado_e_informe_borrador_permiten_avance_sin_calificar(self):
        plan = DocumentoExpediente(id=1, exigido=DocumentoExigido(id=1, codigo='PLANIFICACION'),
            anio=2026, corte='B', estado='observado', version=1, evaluacion=100, evaluacion_version=1)
        cierre = DocumentoExpediente(id=2, exigido=DocumentoExigido(id=2, codigo='INFORME-SEMESTRAL'),
            anio=2026, corte='B', estado='pendiente', version=1)
        for documento in (plan, cierre):
            documento._control_automatico = documento._aprobacion_permanente_registro = None
            documento.avance_redaccion = 100
        cierre._avance_cierre = dict(filas=[dict(exigible=True, aplica=True, definida=True,
            pendiente=False, porcentaje=p) for p in [Decimal('16.67'), *([0] * 12)]])
        with patch('apps.documentos.models.expediente.minimo_vigente', return_value=70), \
                patch('apps.documentos.presentation.conformidad_lectura.lectura_conformidad',
                    side_effect=lambda d, **kw: dict(estado='corregir', fuente='Sistema', historica={})
                        if d.exigido.codigo == 'PLANIFICACION' else None):
            datos = progreso_general([plan, cierre])
        self.assertEqual(datos['avance_operativo']['porcentaje'], Decimal('1.28'))
        self.assertIsNone(datos['resultado_porcentaje'])
        self.assertEqual(datos['porcentaje'], 0)
        self.assertEqual((plan.evaluacion, plan.avance_redaccion, cierre.avance_redaccion), (100, 100, 100))
        self.assertIsNone(cierre.evaluacion)
